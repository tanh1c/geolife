"""S2b: AWS SQS + DynamoDB + encrypted S3, synthetic-fixture jobs ONLY.

No calls occur on import. Clients are created only with explicit opt-in config.
No GeoLife private GPS or dataset cache enters this path; input is a named,
hardcoded synthetic fixture. This module is deliberately not deployed by PR.
"""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from .job_simulation import MODEL_VARIANTS

_ID = re.compile(r"^[a-f0-9]{64}$")
_KEY = re.compile(r"^[A-Za-z0-9._-]{8,64}$")
FIXTURES = frozenset(("three_night_home", "short_observation"))
TTL_SECONDS = 900


def enabled() -> bool:
    return os.getenv("GEOLIFE_S2B_ENABLE", "") == "1"


class ConfigurationError(RuntimeError):
    pass


class IdempotencyConflict(ValueError):
    pass


class AwsAsyncJobs:
    def __init__(self, *, table: Any, s3: Any, sqs: Any, bucket: str,
                 queue_url: str, hmac_secret: str):
        if len(hmac_secret.encode("utf-8")) < 32 or not bucket or not queue_url:
            raise ConfigurationError("Missing restricted S2b credentials or resources")
        self.table, self.s3, self.sqs = table, s3, sqs
        self.bucket, self.queue_url = bucket, queue_url
        self.hmac_secret = hmac_secret.encode("utf-8")

    @classmethod
    def from_environment(cls) -> "AwsAsyncJobs":
        if not enabled():
            raise ConfigurationError("S2b disabled")
        values = [os.getenv(n, "") for n in (
            "GEOLIFE_S2B_TABLE", "GEOLIFE_S2B_BUCKET",
            "GEOLIFE_S2B_QUEUE_URL", "GEOLIFE_S2B_HMAC_SECRET",
        )]
        if not all(values):
            raise ConfigurationError("S2b private backend not configured")
        # AWS SDK only imported after opt-in / config checks.
        import boto3

        region = os.getenv("AWS_REGION", "ap-southeast-1")
        session = boto3.Session(region_name=region)
        return cls(
            table=session.resource("dynamodb").Table(values[0]),
            s3=session.client("s3"), sqs=session.client("sqs"),
            bucket=values[1], queue_url=values[2], hmac_secret=values[3],
        )

    def _opaque_id(self, owner: str, key: str) -> str:
        # HMAC binds idempotency to server-derived owner (no client user ID).
        raw = json.dumps([owner, key], separators=(",", ":")).encode("utf-8")
        return hmac.new(self.hmac_secret, raw, hashlib.sha256).hexdigest()

    @staticmethod
    def _check_fixture(fixture: str, variant: str) -> None:
        if fixture not in FIXTURES or variant not in MODEL_VARIANTS:
            raise ValueError("Unrecognized synthetic fixture or model variant")

    def create(self, *, owner: str, key: str, fixture: str, variant: str,
               now: int | None = None) -> dict[str, object]:
        if not owner or not re.fullmatch(r"[A-Za-z0-9_-]{3,64}", owner):
            raise ValueError("Invalid server-derived account")
        if not _KEY.fullmatch(key):
            raise ValueError("Invalid Idempotency-Key")
        self._check_fixture(fixture, variant)
        now = int(time.time()) if now is None else now
        jid = self._opaque_id(owner, key)
        existing = self.table.get_item(
            Key={"job_id": jid}, ConsistentRead=True
        ).get("Item")
        fingerprint = hashlib.sha256(f"{fixture}|{variant}".encode()).hexdigest()
        if existing is not None and int(existing["expires_at"]) > now:
            if (existing["owner_id"] != owner or existing["fingerprint"] != fingerprint):
                raise IdempotencyConflict("Idempotency-Key reused with different request")
            # Safe to retry enqueue: Standard SQS may deliver duplicates anyway.
            if existing["state"] == "pending":
                self._send(jid)
            return self._view(existing)
        # Deterministic synthetic payload only. No GPS or person identifiers.
        key_s3 = f"synthetic/{jid}.json"
        document = json.dumps(
            {"fixture": fixture, "variant": variant},
            separators=(",", ":"),
        ).encode("utf-8")
        self.s3.put_object(
            Bucket=self.bucket, Key=key_s3, Body=document,
            ContentType="application/json", ServerSideEncryption="AES256",
        )
        item = {
            "job_id": jid, "owner_id": owner, "state": "pending",
            "fingerprint": fingerprint, "fixture": fixture,
            "model_version": variant, "created_at": now,
            "expires_at": now + TTL_SECONDS, "payload_key": key_s3,
        }
        try:
            self.table.put_item(
                Item=item, ConditionExpression="attribute_not_exists(job_id)",
            )
        except Exception as exc:
            if not _conditional_failed(exc):
                raise
            current = self.table.get_item(
                Key={"job_id": jid}, ConsistentRead=True
            ).get("Item")
            if not current or current["fingerprint"] != fingerprint or current["owner_id"] != owner:
                raise IdempotencyConflict("Idempotency-Key conflict") from None
            item = current
        if item["state"] == "pending":
            self._send(jid)
        return self._view(item)

    def _send(self, jid: str) -> None:
        # Absolutely no raw GPS / owner / S3 key on the wire.
        self.sqs.send_message(
            QueueUrl=self.queue_url,
            MessageBody=json.dumps({"job_id": jid}, separators=(",", ":")),
        )

    @staticmethod
    def _view(item: dict[str, Any]) -> dict[str, object]:
        view: dict[str, object] = {
            "job_id": item["job_id"], "status": item["state"],
            "model_version": item["model_version"],
        }
        if item["state"] == "succeeded":
            view["result"] = json.loads(item["result_json"])
        return view

    def get(self, *, owner: str, jid: str, now: int | None = None) -> dict[str, object] | None:
        if not _ID.fullmatch(jid):
            return None
        now = int(time.time()) if now is None else now
        item = self.table.get_item(
            Key={"job_id": jid}, ConsistentRead=True
        ).get("Item")
        if (not item or int(item["expires_at"]) <= now or
                not hmac.compare_digest(item["owner_id"], owner)):
            return None
        return self._view(item)

    def process_once(self, *, now: int | None = None) -> bool:
        now = int(time.time()) if now is None else now
        response = self.sqs.receive_message(
            QueueUrl=self.queue_url, MaxNumberOfMessages=1,
            WaitTimeSeconds=5, VisibilityTimeout=120,
            AttributeNames=["ApproximateReceiveCount"],
        )
        messages = response.get("Messages", [])
        if not messages:
            return False
        msg = messages[0]
        receipt = msg["ReceiptHandle"]
        try:
            obj = json.loads(msg["Body"])
            if not isinstance(obj, dict) or set(obj) != {"job_id"}:
                return True  # poison message -> SQS DLQ after retry budget
            jid = obj["job_id"]
            if not isinstance(jid, str) or not _ID.fullmatch(jid):
                return True
        except (ValueError, TypeError, KeyError):
            return True
        item = self.table.get_item(Key={"job_id": jid}, ConsistentRead=True).get("Item")
        if not item or int(item["expires_at"]) <= now:
            self._ack(receipt)
            return True
        if item["state"] == "succeeded":
            self._ack(receipt)
            return True
        if item["state"] == "failed":
            return True  # preserve for SQS redrive to DLQ
        lease = secrets.token_hex(16)
        try:
            self.table.update_item(
                Key={"job_id": jid},
                UpdateExpression="SET #st=:running, lease_id=:lease, lease_until=:until",
                ConditionExpression=(
                    "expires_at > :now AND "
                    "(#st=:pending OR (#st=:running AND lease_until < :now))"
                ),
                ExpressionAttributeNames={"#st": "state"},
                ExpressionAttributeValues={
                    ":running": "running", ":pending": "pending",
                    ":now": now, ":lease": lease, ":until": now + 110,
                },
            )
        except Exception as exc:
            if _conditional_failed(exc):
                return True  # another worker owns the lease; let visibility expire
            raise
        try:
            response_s3 = self.s3.get_object(
                Bucket=self.bucket, Key=item["payload_key"],
            )
            request = json.loads(response_s3["Body"].read())
            if not isinstance(request, dict) or set(request) != {"fixture", "variant"}:
                raise ValueError("Unsupported synthetic payload")
            self._check_fixture(request["fixture"], request["variant"])
            if request["variant"] != item["model_version"] or request["fixture"] != item["fixture"]:
                raise ValueError("Payload differs from persisted contract")
            result = run_synthetic_inference(
                fixture=request["fixture"], variant=request["variant"]
            )
            self.table.update_item(
                Key={"job_id": jid},
                UpdateExpression=(
                    "SET #st=:done, result_json=:result, completed_at=:now "
                    "REMOVE lease_id, lease_until"
                ),
                ConditionExpression="#st=:running AND lease_id=:lease",
                ExpressionAttributeNames={"#st": "state"},
                ExpressionAttributeValues={
                    ":done": "succeeded", ":running": "running",
                    ":lease": lease, ":result": json.dumps(result), ":now": now,
                },
            )
            # Best-effort erasure after atomic success. One-day S3 lifecycle
            # is a backstop, not an exact fifteen-minute deletion guarantee.
            try:
                self.s3.delete_object(Bucket=self.bucket, Key=item["payload_key"])
            except Exception:
                pass
            self._ack(receipt)
        except Exception:
            # Never log exception text: SDK and payload errors may expose data.
            attempts = int(msg.get("Attributes", {}).get("ApproximateReceiveCount", "1"))
            terminal = attempts >= 3
            try:
                self.table.update_item(
                    Key={"job_id": jid},
                    UpdateExpression=(
                        "SET #st=:next REMOVE lease_id, lease_until"
                    ),
                    ConditionExpression="#st=:running AND lease_id=:lease",
                    ExpressionAttributeNames={"#st": "state"},
                    ExpressionAttributeValues={
                        ":next": "failed" if terminal else "pending",
                        ":running": "running", ":lease": lease,
                    },
                )
            except Exception:
                pass
            # Do not ack failure: AWS SQS redrive sends repeated failures to DLQ.
        return True

    def _ack(self, receipt: str) -> None:
        self.sqs.delete_message(QueueUrl=self.queue_url, ReceiptHandle=receipt)


def _conditional_failed(exc: Exception) -> bool:
    return (
        isinstance(getattr(exc, "response", None), dict) and
        exc.response.get("Error", {}).get("Code") ==
        "ConditionalCheckFailedException"
    )


def synthetic_points(fixture: str) -> list[dict[str, object]]:
    if fixture not in FIXTURES:
        raise ValueError("Unrecognized fixture")
    if fixture == "short_observation":
        moments = [(5, 0), (5, 1)]
    else:
        moments = [(day, minute) for day in (5, 6, 7) for minute in (0, 5, 10, 15, 20)]
    # Fictional synthetic coordinates, NOT Microsoft GeoLife observations.
    return [
        {
            "timestamp_utc": f"2026-01-{day:02d}T13:{minute:02d}:00Z",
            "latitude": 39.9042, "longitude": 116.4074,
        }
        for day, minute in moments
    ]


def run_synthetic_inference(*, fixture: str, variant: str) -> dict[str, object]:
    """Execute the *existing* CP1/CP2 path, return safe aggregate status only."""
    from geolife.api.schemas import ClassifyRequest
    from geolife.api.service import raw_request_to_stay_frame
    from geolife.api.v2 import model_config
    from geolife.model import infer_home_office
    points = synthetic_points(fixture)
    request = ClassifyRequest(points=points)
    stays = raw_request_to_stay_frame("synthetic", request)
    selected = infer_home_office(stays, config=model_config(variant)) if not stays.empty else None
    labels = set(selected["label"].tolist()) if selected is not None and not selected.empty else set()
    return {
        "source": "synthetic_fixture",
        "detected_stays": int(len(stays)),
        "home_status": "emitted" if "HOME" in labels else "abstained",
        "office_status": "emitted" if "OFFICE" in labels else "abstained",
        "model_version": variant,
        "note": "Synthetic aggregate; no raw GPS, Evidence Score or participant linkage.",
    }
