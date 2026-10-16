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
from geolife.serving.aws_s2b import AwsAsyncJobs, FIXTURES, run_synthetic_inference


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
