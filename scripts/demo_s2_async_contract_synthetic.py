"""Offline contract smoke — does NOT connect to or create AWS SQS resources."""
from __future__ import annotations

import json
from datetime import datetime, timezone

from geolife.serving import SyntheticAsyncQueue, synthetic_worker


def main() -> None:
    now = datetime(2026, 10, 16, 10, tzinfo=timezone.utc)
    sim = SyntheticAsyncQueue(ttl_seconds=900, max_attempts=3)
    jid = sim.submit(
        owner_id="synthetic_account_a",
        payload_ref="private-test://dummy-001",
        model_version="cp2-v2-complete-link-200m",
        idempotency_key="synthetic_request_001",
        now=now,
    )
    sim.inject_duplicate()
    while sim.process_one(now=now, processor=synthetic_worker):
        pass
    state = sim.read_for_owner(owner_id="synthetic_account_a", job_id=jid, now=now)
    report = {
        "mode": "offline_sqs_contract_simulation_NOT_REAL_AWS",
        "synthetic_only": True,
        "attempts": sim.processor_invocations,
        "jobs_succeeded": int(state is not None and state["state"] == "succeeded"),
        "dead_letter_count": len(sim.dead_letter),
        "queue_pointer_only": True,
        "live_sqs_provisioned": False,
        "sync_async_latency_benchmark": None,
        "production_ready": False,
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
