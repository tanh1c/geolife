from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path

import boto3
import pytest
from botocore.exceptions import ClientError
from moto import mock_aws

PATH = Path(__file__).resolve().parents[1] / "scripts" / "modal_to_s3_research_cache.py"
SPEC = importlib.util.spec_from_file_location("modal_to_s3_research_cache", PATH)
assert SPEC and SPEC.loader
transfer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(transfer)


BUCKET = "geolife-private-research-123456789012-ap-southeast-1"


class S3WithoutList:
    def __init__(self, client, *, errors=None):
        self.client = client
        self.errors = list(errors or [])
        self.calls = []

    def put_object(self, **kwargs):
        assert kwargs["IfNoneMatch"] == "*"
        assert kwargs["ServerSideEncryption"] == "AES256"
        assert kwargs["Key"] in {transfer.KEY, transfer.MANIFEST_KEY}
        self.calls.append(("put", kwargs["Key"]))
        if self.errors:
            code, status = self.errors.pop(0)
            raise ClientError({"Error": {"Code": code}, "ResponseMetadata": {"HTTPStatusCode": status}}, "PutObject")
        return self.client.put_object(**kwargs)

    def get_object(self, **kwargs):
        assert "VersionId" in kwargs
        self.calls.append(("get", kwargs["Key"], kwargs["VersionId"]))
        return self.client.get_object(**kwargs)

    def head_object(self, **kwargs):
        assert kwargs["Key"] in {transfer.KEY, transfer.MANIFEST_KEY}
        assert "VersionId" not in kwargs
        self.calls.append(("head", kwargs["Key"]))
        return self.client.head_object(**kwargs)


@pytest.fixture
def setup(monkeypatch):
    payload = b"synthetic-cache-fixture-only"
    monkeypatch.setattr(transfer, "SIZE", len(payload))
    monkeypatch.setattr(transfer, "SHA256", hashlib.sha256(payload).hexdigest())
    with mock_aws():
        client = boto3.client("s3", region_name="ap-southeast-1")
        client.create_bucket(Bucket=BUCKET, CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"})
        client.put_bucket_versioning(Bucket=BUCKET, VersioningConfiguration={"Status": "Enabled"})
        yield payload, client, S3WithoutList(client)


class Volume:
    def __init__(self, payload: bytes):
        self.payload = payload
        self.reads = 0

    def read_file(self, path: str):
        assert path == transfer.SOURCE
        self.reads += 1
        yield self.payload


def test_first_upload_and_rerun_without_list_bucket(setup):
    payload, client, s3 = setup
    volume = Volume(payload)
    assert transfer.transfer(volume, s3, BUCKET, execute=False)["transfer_executed"] is False
    assert client.list_objects_v2(Bucket=BUCKET).get("KeyCount") == 0
    first = transfer.transfer(volume, s3, BUCKET, execute=True)
    assert first["status"] == "TRANSFERRED"
    repeated = transfer.transfer(volume, s3, BUCKET, execute=True)
    assert repeated["status"] == "ALREADY_VERIFIED"
    assert (first["s3_version_id"], first["s3_manifest_version_id"]) == (repeated["s3_version_id"], repeated["s3_manifest_version_id"])
    assert len(client.list_object_versions(Bucket=BUCKET)["Versions"]) == 2
    assert not any(call[0] == "head" for call in s3.calls[:2])
    assert all(call[0] != "get" or call[2] for call in s3.calls)


def test_restart_after_cache_written_without_manifest(setup):
    payload, client, s3 = setup
    cached = client.put_object(Bucket=BUCKET, Key=transfer.KEY, Body=payload, IfNoneMatch="*", ServerSideEncryption="AES256")
    result = transfer.transfer(Volume(payload), s3, BUCKET, execute=True)
    assert result["status"] == "TRANSFERRED"
    assert result["s3_version_id"] == cached["VersionId"]
    manifest = client.get_object(Bucket=BUCKET, Key=transfer.MANIFEST_KEY, VersionId=result["s3_manifest_version_id"])
    assert manifest["ServerSideEncryption"] == "AES256"
    assert json.loads(manifest["Body"].read())["s3_version_id"] == cached["VersionId"]
    assert len(client.list_object_versions(Bucket=BUCKET)["Versions"]) == 2


@pytest.mark.parametrize("key", [transfer.KEY, transfer.MANIFEST_KEY])
def test_rejects_write_access_denied_without_treating_403_as_missing(setup, key):
    payload, client, _ = setup
    if key == transfer.MANIFEST_KEY:
        client.put_object(Bucket=BUCKET, Key=transfer.KEY, Body=payload, IfNoneMatch="*", ServerSideEncryption="AES256")
    s3 = S3WithoutList(client, errors=[("AccessDenied", 403)] if key == transfer.KEY else [("PreconditionFailed", 412), ("AccessDenied", 403)])
    with pytest.raises(ClientError) as error:
        transfer.transfer(Volume(payload), s3, BUCKET, execute=True)
    assert error.value.response["ResponseMetadata"]["HTTPStatusCode"] == 403
    assert ("put", key) in s3.calls
    assert client.list_objects_v2(Bucket=BUCKET).get("KeyCount") == (1 if key == transfer.MANIFEST_KEY else 0)


def test_rejects_mismatched_manifest_encryption(setup):
    payload, client, s3 = setup
    first = transfer.transfer(Volume(payload), s3, BUCKET, execute=True)
    client.delete_object(Bucket=BUCKET, Key=transfer.MANIFEST_KEY)
    original = client.get_object(Bucket=BUCKET, Key=transfer.MANIFEST_KEY, VersionId=first["s3_manifest_version_id"])
    client.put_object(Bucket=BUCKET, Key=transfer.MANIFEST_KEY, Body=original["Body"].read())
    with pytest.raises(AssertionError, match="Existing S3 object differs"):
        transfer.transfer(Volume(payload), s3, BUCKET, execute=True)
    assert len(client.list_object_versions(Bucket=BUCKET)["Versions"]) == 3


def test_rejects_changed_source_before_writing(setup):
    _, client, s3 = setup
    with pytest.raises(AssertionError, match="fingerprint changed"):
        transfer.transfer(Volume(b"changed"), s3, BUCKET, execute=True)
    assert not s3.calls
    assert client.list_objects_v2(Bucket=BUCKET).get("KeyCount") == 0


def test_restart_after_manifest_write_failure_preserves_cache_version(setup):
    payload, client, _ = setup

    class ManifestFailure(S3WithoutList):
        def put_object(self, **kwargs):
            if kwargs["Key"] == transfer.MANIFEST_KEY:
                raise ClientError({"Error": {"Code": "AccessDenied"}, "ResponseMetadata": {"HTTPStatusCode": 403}}, "PutObject")
            return super().put_object(**kwargs)

    with pytest.raises(ClientError):
        transfer.transfer(Volume(payload), ManifestFailure(client), BUCKET, execute=True)
    cache_version = client.head_object(Bucket=BUCKET, Key=transfer.KEY)["VersionId"]
    assert client.list_objects_v2(Bucket=BUCKET).get("KeyCount") == 1
    restarted = transfer.transfer(Volume(payload), S3WithoutList(client), BUCKET, execute=True)
    assert restarted["status"] == "TRANSFERRED"
    assert restarted["s3_version_id"] == cache_version
    assert len(client.list_object_versions(Bucket=BUCKET)["Versions"]) == 2


def test_precondition_failure_verifies_matching_cache_and_manifest_versions(setup):
    payload, client, s3 = setup
    first = transfer.transfer(Volume(payload), s3, BUCKET, execute=True)
    retry = S3WithoutList(client, errors=[("PreconditionFailed", 412), ("PreconditionFailed", 412)])
    repeated = transfer.transfer(Volume(payload), retry, BUCKET, execute=True)
    assert repeated["status"] == "ALREADY_VERIFIED"
    assert repeated["s3_version_id"] == first["s3_version_id"]
    assert repeated["s3_manifest_version_id"] == first["s3_manifest_version_id"]
    assert ("get", transfer.KEY, first["s3_version_id"]) in retry.calls
    assert ("get", transfer.MANIFEST_KEY, first["s3_manifest_version_id"]) in retry.calls


@pytest.mark.parametrize("variant", ["bytes", "size", "encryption"])
def test_precondition_failure_rejects_mismatched_existing_cache(setup, variant):
    payload, client, s3 = setup
    body = b"X" * len(payload) if variant == "bytes" else payload[:-1] if variant == "size" else payload
    put = {"Bucket": BUCKET, "Key": transfer.KEY, "Body": body, "IfNoneMatch": "*"}
    if variant != "encryption":
        put["ServerSideEncryption"] = "AES256"
    client.put_object(**put)
    with pytest.raises(AssertionError, match="Existing S3 object differs"):
        transfer.transfer(Volume(payload), s3, BUCKET, execute=True)
    assert client.list_objects_v2(Bucket=BUCKET).get("KeyCount") == 1


def test_conflict_retries_then_succeeds_without_overwriting(setup):
    payload, client, _ = setup
    s3 = S3WithoutList(client, errors=[("ConditionalRequestConflict", 409)])
    result = transfer.transfer(Volume(payload), s3, BUCKET, execute=True)
    assert result["status"] == "TRANSFERRED"
    assert s3.calls[:2] == [("put", transfer.KEY), ("put", transfer.KEY)]
    assert len(client.list_object_versions(Bucket=BUCKET)["Versions"]) == 2


def test_conflict_retries_are_bounded(setup):
    payload, client, _ = setup
    s3 = S3WithoutList(client, errors=[("ConditionalRequestConflict", 409)] * 4)
    with pytest.raises(ClientError) as error:
        transfer.transfer(Volume(payload), s3, BUCKET, execute=True)
    assert error.value.response["ResponseMetadata"]["HTTPStatusCode"] == 409
    assert len(s3.calls) == 3
    assert client.list_objects_v2(Bucket=BUCKET).get("KeyCount") == 0

def test_existing_manifest_must_bind_exact_verified_cache_version(setup):
    payload, client, s3 = setup
    first = transfer.transfer(Volume(payload), s3, BUCKET, execute=True)
    original = client.get_object(Bucket=BUCKET, Key=transfer.MANIFEST_KEY, VersionId=first["s3_manifest_version_id"])
    manifest = json.loads(original["Body"].read())
    client.delete_object(Bucket=BUCKET, Key=transfer.MANIFEST_KEY)
    manifest["s3_version_id"] = "different-version"
    client.put_object(Bucket=BUCKET, Key=transfer.MANIFEST_KEY, Body=json.dumps(manifest).encode(), ServerSideEncryption="AES256")
    with pytest.raises(AssertionError, match="Existing S3 object differs"):
        transfer.transfer(Volume(payload), s3, BUCKET, execute=True)
    assert first["s3_version_id"] == client.head_object(Bucket=BUCKET, Key=transfer.KEY)["VersionId"]


def test_verified_transfer_is_private_versioned_and_idempotent(monkeypatch):
    payload = b"synthetic-cache-fixture-only"
    monkeypatch.setattr(transfer, "SIZE", len(payload))
    monkeypatch.setattr(transfer, "SHA256", __import__("hashlib").sha256(payload).hexdigest())
    volume = Volume(payload)
    bucket = "geolife-private-research-123456789012-ap-southeast-1"
    with mock_aws():
        s3 = boto3.client("s3", region_name="ap-southeast-1")
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"})
        s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
        assert transfer.transfer(volume, s3, bucket, execute=False)["transfer_executed"] is False
        assert s3.list_objects_v2(Bucket=bucket).get("KeyCount") == 0
        first = transfer.transfer(volume, s3, bucket, execute=True)
        assert first["status"] == "TRANSFERRED" and first["s3_version_id"] and first["s3_manifest_version_id"]
        assert first["sha256"] == transfer.SHA256
        obj = s3.get_object(Bucket=bucket, Key=transfer.KEY, VersionId=first["s3_version_id"])
        assert obj["Body"].read() == payload
        assert obj["ServerSideEncryption"] == "AES256"
        repeated = transfer.transfer(volume, s3, bucket, execute=True)
        assert repeated["status"] == "ALREADY_VERIFIED"
        assert repeated["s3_version_id"] == first["s3_version_id"]
        assert repeated["s3_manifest_version_id"] == first["s3_manifest_version_id"]
        versions = s3.list_object_versions(Bucket=bucket)["Versions"]
        assert len(versions) == 2 and {item["Key"] for item in versions} == {transfer.KEY, transfer.MANIFEST_KEY}
        assert volume.reads == 5


def test_changed_or_existing_mismatched_cache_is_never_uploaded(monkeypatch):
    payload = b"synthetic-cache-fixture-only"
    monkeypatch.setattr(transfer, "SIZE", len(payload))
    monkeypatch.setattr(transfer, "SHA256", __import__("hashlib").sha256(payload).hexdigest())
    with mock_aws():
        s3 = boto3.client("s3", region_name="ap-southeast-1")
        bucket = "geolife-private-research-123456789012-ap-southeast-1"
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"})
        s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
        with pytest.raises(AssertionError, match="fingerprint changed"):
            transfer.transfer(Volume(b"modified"), s3, bucket, execute=True)
        assert s3.list_objects_v2(Bucket=bucket).get("KeyCount") == 0
        s3.put_object(Bucket=bucket, Key=transfer.KEY, Body=b"different")
        with pytest.raises(AssertionError, match="Existing S3 object differs"):
            transfer.transfer(Volume(payload), s3, bucket, execute=True)
