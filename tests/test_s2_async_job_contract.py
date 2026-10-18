"""S2a synthetic-only contract tests: no boto3, no real GPS/GeoLife data."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from geolife.serving import SyntheticAsyncQueue, synthetic_worker


NOW = datetime(2026, 10, 16, 10, 0, tzinfo=timezone.utc)
BASE = "cp2-v2-complete-link-200m"


def send(queue: SyntheticAsyncQueue, *, owner: str = "acct_a", key: str = "request_1",
         payload: str = "private-test://object-001") -> str:
    return queue.submit(
        owner_id=owner, payload_ref=payload, model_version=BASE,
        idempotency_key=key, now=NOW,
    )


def test_pointer_only_message_no_gps_or_user_ids():
    q = SyntheticAsyncQueue()
    jid = send(q)
    wire = q.next_message()
    assert wire == {"job_id": jid}
    assert "private-test://" not in repr(wire)
    assert "acct_a" not in repr(wire)
    assert "latitude" not in repr(wire)
    assert "longitude" not in repr(wire)


def test_owner_isolation_and_expired_lookup_are_indistinguishable():
    q = SyntheticAsyncQueue(ttl_seconds=60)
    jid = send(q)
    assert q.read_for_owner(owner_id="acct_b", job_id=jid, now=NOW) is None
    assert q.read_for_owner(owner_id="acct_a", job_id="no-such-job", now=NOW) is None
    own = q.read_for_owner(owner_id="acct_a", job_id=jid, now=NOW)
    assert own == {
        "job_id": jid, "state": "pending",
        "model_version": BASE, "result": None,
    }
    assert q.read_for_owner(
        owner_id="acct_a", job_id=jid, now=NOW + timedelta(seconds=60)
    ) is None


def test_idempotency_same_owner_request_and_mismatch_rejected():
    q = SyntheticAsyncQueue()
    one = send(q)
    assert send(q) == one
    assert q.queue_depth() == 1
    two = send(q, owner="acct_b")
    assert two != one
    assert q.queue_depth() == 2
    with pytest.raises(ValueError, match="Idempotency-key reuse"):
        send(q, payload="private-test://different")


def test_at_least_once_duplicate_does_not_reexecute_completed_job():
    q = SyntheticAsyncQueue()
    jid = send(q)
    q.inject_duplicate()
    assert q.queue_depth() == 2
    assert q.process_one(now=NOW, processor=synthetic_worker)
    assert q.process_one(now=NOW, processor=synthetic_worker)
    assert q.processor_invocations == 1
    assert q.read_for_owner(owner_id="acct_a", job_id=jid, now=NOW)["state"] == "succeeded"
    assert q.dead_letter == []


def test_retry_and_dead_letter_simulation_only():
    q = SyntheticAsyncQueue(max_attempts=2)
    jid = send(q)

    def broken(_ref: str, _version: str) -> dict[str, object]:
        raise RuntimeError("PRIVATE GPS must never be logged or surfaced")

    assert q.process_one(now=NOW, processor=broken)
    assert q.read_for_owner(owner_id="acct_a", job_id=jid, now=NOW)["state"] == "pending"
    assert q.process_one(now=NOW, processor=broken)
    status = q.read_for_owner(owner_id="acct_a", job_id=jid, now=NOW)
    assert status["state"] == "failed"
    assert status["result"] == {"synthetic_result": "worker_failed"}
    assert q.dead_letter == [{"job_id": jid}]
    assert "PRIVATE GPS" not in repr(status)


def test_expired_queue_message_does_not_reopen_job():
    q = SyntheticAsyncQueue(ttl_seconds=60)
    jid = send(q)
    assert q.process_one(now=NOW + timedelta(seconds=61), processor=synthetic_worker)
    assert q.processor_invocations == 0
    assert q.read_for_owner(
        owner_id="acct_a", job_id=jid, now=NOW + timedelta(seconds=61)
    ) is None


def test_validation_and_untrusted_result_shape():
    q = SyntheticAsyncQueue()
    with pytest.raises(ValueError, match="Timezone-aware"):
        q.submit(
            owner_id="a", payload_ref="private-test://ok", model_version=BASE,
            idempotency_key="x", now=datetime(2026, 10, 16),
        )
    with pytest.raises(ValueError, match="Unrecognized"):
        q.submit(
            owner_id="a", payload_ref="private-test://ok", model_version="unknown",
            idempotency_key="x", now=NOW,
        )
    with pytest.raises(ValueError, match="Synthetic-only"):
        synthetic_worker("https://real-gps.example/private", BASE)
    jid = send(q)
    q.process_one(now=NOW, processor=lambda _ref, _version: {"coordinates": "sensitive"})
    assert q.read_for_owner(owner_id="acct_a", job_id=jid, now=NOW)["state"] == "pending"
