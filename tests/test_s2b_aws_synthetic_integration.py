"""Moto-only S2b AWS integration; no network, no real resources or GPS."""
from __future__ import annotations

import json
from datetime import datetime, timezone

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws

from geolife.api.app import app
from geolife.api.demo_auth import provision_account
from geolife.serving.aws_s2b import AwsAsyncJobs


@pytest.fixture
def cloud(monkeypatch, tmp_path):
    with mock_aws():
        region = "ap-southeast-1"
        resource = boto3.resource("dynamodb", region_name=region)
        table = resource.create_table(
            TableName="geolife-s2b-test",
            KeySchema=[{"AttributeName": "job_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "job_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        s3 = boto3.client("s3", region_name=region)
        bucket = "geolife-s2b-example-test-bucket"
        s3.create_bucket(
            Bucket=bucket,
            CreateBucketConfiguration={"LocationConstraint": region},
        )
        sqs = boto3.client("sqs", region_name=region)
        qurl = sqs.create_queue(QueueName="geolife-s2b-test")["QueueUrl"]
        secret = "test-only-s2b-hmac-secret-32-character-minimum"
        monkeypatch.setenv("AWS_REGION", region)
        monkeypatch.setenv("GEOLIFE_S2B_ENABLE", "1")
        monkeypatch.setenv("GEOLIFE_S2B_TABLE", table.table_name)
        monkeypatch.setenv("GEOLIFE_S2B_BUCKET", bucket)
        monkeypatch.setenv("GEOLIFE_S2B_QUEUE_URL", qurl)
        monkeypatch.setenv("GEOLIFE_S2B_HMAC_SECRET", secret)

        db = tmp_path / "private_demo.sqlite3"
        provision_account(db, "demo_000", "000", "only-for-moto-test-long-password-000")
        provision_account(db, "demo_001", "001", "only-for-moto-test-long-password-001")
        monkeypatch.setenv("GEOLIFE_DEMO_AUTH_DB", str(db))
        yield AwsAsyncJobs(
            table=table, s3=s3, sqs=sqs,
            bucket=bucket, queue_url=qurl, hmac_secret=secret,
        )


def _token(client: TestClient, account: str, password: str) -> dict[str, str]:
    r = client.post("/v2/auth/login", json={"account_id": account, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_aws_mock_end_to_end_real_cp1_cp2_synthetic_only(cloud):
    client = TestClient(app)
    a = _token(client, "demo_000", "only-for-moto-test-long-password-000")
    b = _token(client, "demo_001", "only-for-moto-test-long-password-001")
    hdr = dict(a, **{"Idempotency-Key": "try-001-synthetic"})
    req = {"fixture": "three_night_home"}
    submit = client.post("/v2/jobs", json=req, headers=hdr)
    assert submit.status_code == 202, submit.text
    job = submit.json()
    assert job["status"] == "pending"
    assert len(job["job_id"]) == 64
    assert submit.headers["Location"] == "/v2/jobs/" + job["job_id"]
    assert "dataset_user_id" not in submit.text
    assert "confidence" not in submit.text
    assert client.get(f"/v2/jobs/{job['job_id']}", headers=b).status_code == 404
    assert client.get("/v2/jobs/" + "a" * 64, headers=a).status_code == 404
    assert client.get(f"/v2/jobs/{job['job_id']}").status_code == 401

    repeated = client.post("/v2/jobs", json=req, headers=hdr)
    assert repeated.status_code == 202
    assert repeated.json()["job_id"] == job["job_id"]
    conflict = client.post(
        "/v2/jobs", json={"fixture": "short_observation"}, headers=hdr
    )
    assert conflict.status_code == 409

    messages = cloud.sqs.receive_message(
        QueueUrl=cloud.queue_url, MaxNumberOfMessages=10,
    )["Messages"]
    for msg in messages:
        assert json.loads(msg["Body"]) == {"job_id": job["job_id"]}
        assert "000" not in msg["Body"]
        assert "39.9042" not in msg["Body"]
        cloud.sqs.change_message_visibility(
            QueueUrl=cloud.queue_url,
            ReceiptHandle=msg["ReceiptHandle"], VisibilityTimeout=0,
        )
    # The real model is executed on fixture-generated timestamps/coordinates;
    # it does not access GeoLife research files or production data.
    assert cloud.process_once()
    final = client.get(f"/v2/jobs/{job['job_id']}", headers=a)
    assert final.status_code == 200, final.text
    assert final.json()["status"] == "succeeded"
    result = final.json()["result"]
    assert result["source"] == "synthetic_fixture"
    assert result["detected_stays"] >= 1
    assert result["home_status"] in ("emitted", "abstained")
    assert result["office_status"] in ("emitted", "abstained")
    for forbidden in ("evidence", "score", "latitude", "longitude", "dataset_user_id"):
        assert forbidden not in final.text.lower()


def test_moto_duplicate_delivery_and_expired_owner(scaffold=None):
    # Pure contract simulator owns TTL/duplicate-negative tests independently.
    from geolife.serving import SyntheticAsyncQueue, synthetic_worker
    from datetime import timedelta

    now = datetime(2026, 10, 16, tzinfo=timezone.utc)
    q = SyntheticAsyncQueue(ttl_seconds=60)
    jid = q.submit(
        owner_id="demo_a", payload_ref="private-test://fixture",
        model_version="cp2-v2-complete-link-200m", idempotency_key="replay001",
        now=now,
    )
    q.inject_duplicate()
    while q.process_one(now=now, processor=synthetic_worker):
        pass
    assert q.processor_invocations == 1
    assert q.read_for_owner(owner_id="demo_b", job_id=jid, now=now) is None
    assert q.read_for_owner(
        owner_id="demo_a", job_id=jid, now=now + timedelta(seconds=60)
    ) is None


def test_default_off_authenticated_endpoint_and_invalid_contract(cloud, monkeypatch):
    client = TestClient(app)
    auth = _token(client, "demo_000", "only-for-moto-test-long-password-000")
    monkeypatch.setenv("GEOLIFE_S2B_ENABLE", "0")
    submit = client.post("/v2/jobs", json={"fixture": "short_observation"}, headers={
        **auth, "Idempotency-Key": "another-request-1",
    })
    assert submit.status_code == 404
    monkeypatch.setenv("GEOLIFE_S2B_ENABLE", "1")
    invalid = client.post("/v2/jobs", json={"fixture": "actual-gps", "points": []},
                          headers={**auth, "Idempotency-Key": "another-request-2"})
    assert invalid.status_code == 422
    missing_key = client.post(
        "/v2/jobs", json={"fixture": "three_night_home"}, headers=auth,
    )
    assert missing_key.status_code == 422
    malformed = client.get("/v2/jobs/non-uuid", headers=auth)
    assert malformed.status_code == 404


def test_lifecycle_events_ignore_retries_and_duplicate_delivery(cloud):
    from geolife.serving.lifecycle_metrics import InMemoryRecorder

    recorder = InMemoryRecorder()
    cloud.recorder = recorder
    start = 1_000_000_000_125_000_000
    cloud.clock_ns = lambda: start
    job = cloud.create(
        owner="demo_000", key="lifecycle-001", fixture="short_observation",
        variant="cp2-v2-complete-link-200m", now=start // 1_000_000_000,
    )
    assert [event.name for event in recorder.events] == ["accepted"]
    item = cloud.table.get_item(Key={"job_id": job["job_id"]})["Item"]
    assert item["created_at_ms"] == 1000000000125
    assert item["expires_at"] == 1000000900
    cloud.create(
        owner="demo_000", key="lifecycle-001", fixture="short_observation",
        variant="cp2-v2-complete-link-200m", now=start // 1_000_000_000,
    )
    assert [event.name for event in recorder.events] == ["accepted"]
    cloud.clock_ns = lambda: start + 150_000_000
    assert cloud.process_once(now=start // 1_000_000_000)
    item = cloud.table.get_item(Key={"job_id": job["job_id"]})["Item"]
    assert item["state"] == "succeeded"
    assert item["first_lease_at_ms"] == 1000000000275
    assert item["terminal_at_ms"] == 1000000000275
    assert [event.name for event in recorder.events] == ["accepted", "leased", "succeeded"]
    assert recorder.events[1].duration_ms == 150
    cloud._send(job["job_id"])
    assert cloud.process_once(now=start // 1_000_000_000)
    assert [event.name for event in recorder.events] == ["accepted", "leased", "succeeded"]


def test_first_lease_timestamp_excludes_receive_wait_and_skew_is_unavailable(cloud, monkeypatch):
    from geolife.serving.lifecycle_metrics import InMemoryRecorder

    recorder = InMemoryRecorder()
    cloud.recorder = recorder
    start = 1_000_000_000_125_000_000
    cloud.clock_ns = lambda: start
    job = cloud.create(
        owner="demo_000", key="lifecycle-receive-001", fixture="short_observation",
        variant="cp2-v2-complete-link-200m", now=start // 1_000_000_000,
    )
    original_receive = cloud.sqs.receive_message

    def receive_after_wait(**kwargs):
        message = original_receive(**kwargs)
        cloud.clock_ns = lambda: start - 10_000_000
        return message

    monkeypatch.setattr(cloud.sqs, "receive_message", receive_after_wait)
    assert cloud.process_once(now=start // 1_000_000_000)
    item = cloud.table.get_item(Key={"job_id": job["job_id"]})["Item"]
    assert item["first_lease_at_ms"] == item["created_at_ms"] - 10
    assert recorder.events[1].name == "leased"
    assert recorder.events[1].duration_ms is None
    assert recorder.events[2].duration_ms is None


def test_receive_wait_is_excluded_from_worker_execution(cloud, monkeypatch):
    from geolife.serving.lifecycle_metrics import InMemoryRecorder

    recorder = InMemoryRecorder()
    cloud.recorder = recorder
    start = 1_000_000_000_000_000_000
    cloud.clock_ns = lambda: start
    ticks = iter((0, 5_000_000, 10_000_000, 35_000_000))
    cloud.monotonic_ns = lambda: next(ticks)
    cloud.create(
        owner="demo_000", key="lifecycle-wait-001", fixture="short_observation",
        variant="cp2-v2-complete-link-200m", now=start // 1_000_000_000,
    )
    original_receive = cloud.sqs.receive_message

    def receive_after_wait(**kwargs):
        message = original_receive(**kwargs)
        cloud.clock_ns = lambda: start + 5_000_000_000
        return message

    monkeypatch.setattr(cloud.sqs, "receive_message", receive_after_wait)
    assert cloud.process_once(now=start // 1_000_000_000)
    assert recorder.events[0].duration_ms == 5
    assert recorder.events[1].duration_ms == 5000
    assert recorder.events[2].worker_ms == 25


def test_send_failure_retry_undercount_is_explicit(cloud, monkeypatch):
    from geolife.serving.lifecycle_metrics import InMemoryRecorder

    recorder = InMemoryRecorder()
    cloud.recorder = recorder
    original_send = cloud.sqs.send_message
    failed = False

    def fail_first(**kwargs):
        nonlocal failed
        if not failed:
            failed = True
            raise RuntimeError("synthetic send failure")
        return original_send(**kwargs)

    monkeypatch.setattr(cloud.sqs, "send_message", fail_first)
    request = dict(owner="demo_000", key="lifecycle-send-001", fixture="short_observation",
                   variant="cp2-v2-complete-link-200m")
    with pytest.raises(RuntimeError):
        cloud.create(**request)
    assert recorder.events == []
    job = cloud.create(**request)
    assert job["status"] == "pending"
    assert recorder.events == []


def test_lifecycle_failure_and_telemetry_unavailability(cloud):
    from geolife.serving.lifecycle_metrics import InMemoryRecorder, duration_ms

    recorder = InMemoryRecorder()
    cloud.recorder = recorder
    job = cloud.create(
        owner="demo_000", key="lifecycle-002", fixture="short_observation",
        variant="cp2-v2-complete-link-200m",
    )
    cloud.s3.delete_object(Bucket=cloud.bucket, Key=f"synthetic/{job['job_id']}.json")
    assert cloud.process_once()
    assert cloud.table.get_item(Key={"job_id": job["job_id"]})["Item"]["state"] == "pending"
    assert [event.name for event in recorder.events][-2:] == ["leased", "attempt_failed"]
    assert recorder.events[-1].error_class == "payload_read"
    assert duration_ms(1000, 1001) is None
    assert duration_ms(1001, 1000) == 1


def test_terminal_failure_once_after_retries_and_recorder_failure_is_best_effort(cloud, monkeypatch):
    receive_count = iter((1, 2, 3))
    original_receive = cloud.sqs.receive_message

    def receive_once(**kwargs):
        response = original_receive(**kwargs)
        for message in response.get("Messages", []):
            message["Attributes"] = {"ApproximateReceiveCount": str(next(receive_count))}
            cloud.sqs.change_message_visibility(
                QueueUrl=cloud.queue_url, ReceiptHandle=message["ReceiptHandle"],
                VisibilityTimeout=0,
            )
        return response

    monkeypatch.setattr(cloud.sqs, "receive_message", receive_once)
    from geolife.serving.lifecycle_metrics import InMemoryRecorder

    recorder = InMemoryRecorder()
    cloud.recorder = recorder
    job = cloud.create(
        owner="demo_000", key="lifecycle-terminal-001", fixture="short_observation",
        variant="cp2-v2-complete-link-200m",
    )
    cloud.s3.delete_object(Bucket=cloud.bucket, Key=f"synthetic/{job['job_id']}.json")
    for attempt in range(3):
        assert cloud.process_once()
        if attempt < 2:
            assert cloud.table.get_item(Key={"job_id": job["job_id"]})["Item"]["state"] == "pending"
            cloud.sqs.send_message(
                QueueUrl=cloud.queue_url, MessageBody=json.dumps({"job_id": job["job_id"]}),
            )
    assert cloud.table.get_item(Key={"job_id": job["job_id"]})["Item"]["state"] == "failed"
    item = cloud.table.get_item(Key={"job_id": job["job_id"]})["Item"]
    assert item["state"] == "failed" and item["terminal_at_ms"] >= item["created_at_ms"]
    assert [event.name for event in recorder.events].count("failed") == 1
    assert [event.name for event in recorder.events].count("attempt_failed") == 3

    class BrokenRecorder:
        def record(self, event):
            raise RuntimeError("telemetry-only failure")

    cloud.recorder = BrokenRecorder()
    another = cloud.create(
        owner="demo_000", key="lifecycle-telemetry-001", fixture="short_observation",
        variant="cp2-v2-complete-link-200m",
    )
    assert another["status"] == "pending" and cloud.telemetry_failures == 1


def test_failed_terminal_write_does_not_emit_completion(cloud, monkeypatch):
    from geolife.serving.lifecycle_metrics import InMemoryRecorder

    recorder = InMemoryRecorder()
    cloud.recorder = recorder
    job = cloud.create(
        owner="demo_000", key="lifecycle-conditional-001", fixture="short_observation",
        variant="cp2-v2-complete-link-200m",
    )
    real_update = cloud.table.update_item

    def reject_terminal(**kwargs):
        if ":done" in kwargs.get("ExpressionAttributeValues", {}):
            raise RuntimeError("synthetic conditional-write failure")
        return real_update(**kwargs)

    monkeypatch.setattr(cloud.table, "update_item", reject_terminal)
    assert cloud.process_once()
    assert not any(e.name in ("succeeded", "failed") for e in recorder.events)
    assert [e.name for e in recorder.events].count("attempt_failed") == 1
    assert recorder.events[-1].error_class == "storage"
    assert cloud.table.get_item(Key={"job_id": job["job_id"]})["Item"]["state"] == "pending"


def test_failed_fallback_update_still_records_attempt_not_terminal(cloud, monkeypatch):
    from geolife.serving.lifecycle_metrics import InMemoryRecorder

    recorder = InMemoryRecorder()
    cloud.recorder = recorder
    job = cloud.create(
        owner="demo_000", key="lifecycle-fallback-001", fixture="short_observation",
        variant="cp2-v2-complete-link-200m",
    )
    cloud.s3.delete_object(Bucket=cloud.bucket, Key=f"synthetic/{job['job_id']}.json")
    original_update = cloud.table.update_item

    def reject_fallback(**kwargs):
        if ":next" in kwargs.get("ExpressionAttributeValues", {}):
            raise RuntimeError("synthetic fallback write failure")
        return original_update(**kwargs)

    monkeypatch.setattr(cloud.table, "update_item", reject_fallback)
    assert cloud.process_once()
    assert [e.name for e in recorder.events] == ["accepted", "leased", "attempt_failed"]
    assert recorder.events[-1].error_class == "payload_read"
    assert cloud.table.get_item(Key={"job_id": job["job_id"]})["Item"]["state"] == "running"
    assert "terminal_at_ms" not in cloud.table.get_item(Key={"job_id": job["job_id"]})["Item"]


def test_cardinality_budget_and_worker_metrics_not_in_api(cloud):
    from geolife.serving.lifecycle_metrics import Event, InMemoryRecorder, METRICS, metric_series

    assert len(metric_series()) == 16
    assert ("Terminal", "cp2-v2-dbscan-100m", "failed") in metric_series()
    assert ("Accepted", "cp2-v2-complete-link-200m") in metric_series()
    assert {dimensions for _, dimensions in METRICS.values()} == {
        ("model",), ("model", "outcome"),
    }
    assert METRICS == {
        "Accepted": ("Count", ("model",)),
        "SubmitPersistAndSend": ("Milliseconds", ("model",)),
        "FirstLeaseWait": ("Milliseconds", ("model",)),
        "WorkerAttempt": ("Milliseconds", ("model",)),
        "AttemptFailed": ("Count", ("model",)),
        "Terminal": ("Count", ("model", "outcome")),
        "TerminalDuration": ("Milliseconds", ("model",)),
    }
    assert metric_series() == {
        (name, model, *outcome)
        for name in METRICS
        for model in ("cp2-v2-complete-link-200m", "cp2-v2-dbscan-100m")
        for outcome in (("succeeded",), ("failed",)) if name == "Terminal"
    } | {
        (name, model)
        for name in METRICS if name != "Terminal"
        for model in ("cp2-v2-complete-link-200m", "cp2-v2-dbscan-100m")
    }
    recorder = InMemoryRecorder()
    with pytest.raises(ValueError):
        recorder.record(Event("accepted", "user-000"))
    with pytest.raises(ValueError):
        recorder.record(Event("failed", "cp2-v2-dbscan-100m", outcome="raw-exception"))
    with pytest.raises(ValueError):
        recorder.record(Event("attempt_failed", "cp2-v2-dbscan-100m", error_class="raw-exception"))
    assert recorder.events == []


def test_expired_idempotency_key_cannot_resurrect_old_ttl_record(cloud):
    old = cloud.create(
        owner="demo_000", key="expired-request-001",
        fixture="short_observation",
        variant="cp2-v2-complete-link-200m", now=1000,
    )
    assert cloud.get(owner="demo_000", jid=old["job_id"], now=2000) is None
    from geolife.serving.aws_s2b import IdempotencyConflict
    with pytest.raises(IdempotencyConflict, match="Expired"):
        cloud.create(
            owner="demo_000", key="expired-request-001",
            fixture="short_observation",
            variant="cp2-v2-complete-link-200m", now=2000,
        )
    fresh = cloud.create(
        owner="demo_000", key="fresh-request-002",
        fixture="short_observation",
        variant="cp2-v2-complete-link-200m", now=2000,
    )
    assert fresh["job_id"] != old["job_id"]
