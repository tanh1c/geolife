"""Transfer the pinned, admin-trusted CP1 cache from Modal to private versioned S3."""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from typing import Iterable

import boto3
import modal
from botocore.exceptions import ClientError

# ponytail: this transfer handles one pinned 536 KB artifact; use multipart upload if the approved cache grows beyond memory.

MODAL_VOLUME = "geolife-data"
MODAL_ENVIRONMENT = "main"
SOURCE = "cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl"
KEY = "approved/cp1/stays_baseline_v1.pkl"
MANIFEST_KEY = "approved/cp1/stays_baseline_v1.sha256.json"
SIZE = 536002
SHA256 = "94d6904ae834468a7615d1165678b00ae374c54d500d2167c1fe4af58b828e58"


class Stream(io.RawIOBase):
    def __init__(self, chunks: Iterable[bytes]):
        self.chunks = iter(chunks)
        self.pending = memoryview(b"")
        self.hash = hashlib.sha256()
        self.size = 0

    def readable(self) -> bool:
        return True

    def readinto(self, buffer) -> int:
        result = memoryview(buffer)
        written = 0
        while written < len(result):
            if not self.pending:
                try:
                    self.pending = memoryview(next(self.chunks))
                except StopIteration:
                    break
            count = min(len(result) - written, len(self.pending))
            result[written:written + count] = self.pending[:count]
            self.hash.update(self.pending[:count])
            self.size += count
            self.pending = self.pending[count:]
            written += count
        return written


def digest(chunks: Iterable[bytes]) -> tuple[int, str]:
    h = hashlib.sha256()
    size = 0
    for chunk in chunks:
        h.update(chunk)
        size += len(chunk)
    return size, h.hexdigest()


def create_or_verify(s3, bucket: str, key: str, payload: bytes) -> tuple[str, bool]:
    for attempt in range(3):
        try:
            put = s3.put_object(
                Bucket=bucket, Key=key, Body=payload, IfNoneMatch="*",
                ServerSideEncryption="AES256",
            )
            version = put["VersionId"]
            created = True
            break
        except ClientError as exc:
            status = exc.response["ResponseMetadata"]["HTTPStatusCode"]
            if status == 409 and attempt < 2:
                continue
            if status != 412:
                raise
            version = s3.head_object(Bucket=bucket, Key=key)["VersionId"]
            created = False
            break
    else:
        raise AssertionError("S3 create-only write did not complete")
    assert version, "Bucket versioning must be enabled"
    response = s3.get_object(Bucket=bucket, Key=key, VersionId=version)
    try:
        assert response.get("ServerSideEncryption") == "AES256" and response["ContentLength"] == len(payload) and (len(payload), hashlib.sha256(payload).hexdigest()) == digest(response["Body"].iter_chunks()), "Existing S3 object differs"
    finally:
        response["Body"].close()
    return version, created


def transfer(volume, s3, bucket: str, *, execute: bool) -> dict:
    assert (SIZE, SHA256) == digest(volume.read_file(SOURCE)), "Trusted Modal cache fingerprint changed"
    if not execute:
        return {"status": "READY", "source_bytes": SIZE, "source_sha256": SHA256, "transfer_executed": False}

    stream = Stream(volume.read_file(SOURCE))
    payload = stream.read(SIZE + 1)
    assert (stream.size, stream.hash.hexdigest()) == (SIZE, SHA256), "Upload stream fingerprint mismatch"
    version, cache_created = create_or_verify(s3, bucket, KEY, payload)
    manifest = {
        "modal_environment": MODAL_ENVIRONMENT,
        "modal_volume": MODAL_VOLUME,
        "source": SOURCE,
        "bucket": bucket,
        "key": KEY,
        "bytes": SIZE,
        "sha256": SHA256,
        "s3_version_id": version,
        "model_version": "cp2-v2-complete-link-200m",
    }
    content = json.dumps(manifest, sort_keys=True, indent=2).encode()
    manifest_version, manifest_created = create_or_verify(s3, bucket, MANIFEST_KEY, content)
    return {"status": "TRANSFERRED" if cache_created or manifest_created else "ALREADY_VERIFIED", **manifest, "s3_manifest_version_id": manifest_version}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--profile", required=True, help="Approved short-lived or named AWS profile")
    parser.add_argument("--execute-approved-transfer", action="store_true")
    args = parser.parse_args()
    session = boto3.Session(profile_name=args.profile, region_name="ap-southeast-1")
    account = session.client("sts").get_caller_identity()["Account"]
    expected = f"geolife-private-research-{account}-ap-southeast-1"
    if args.bucket != expected:
        raise SystemExit("Bucket does not match approved private research naming")
    volume = modal.Volume.from_name(MODAL_VOLUME, environment_name=MODAL_ENVIRONMENT)
    s3 = session.client("s3")
    if args.execute_approved_transfer:
        assert s3.get_public_access_block(Bucket=args.bucket)["PublicAccessBlockConfiguration"] == {
            "BlockPublicAcls": True, "IgnorePublicAcls": True,
            "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
        }, "Bucket public access block is incomplete"
        assert s3.get_bucket_versioning(Bucket=args.bucket).get("Status") == "Enabled", "Bucket versioning is disabled"
    try:
        result = transfer(volume, s3, args.bucket, execute=args.execute_approved_transfer)
    except Exception as exc:
        raise SystemExit("Transfer failed: " + type(exc).__name__) from None
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
