"""Offline-only async Track B1 contract simulator; deliberately no AWS/boto3.

Run as pure test code. A real implementation must replace this in-memory
ledger/queue with encrypted private TTL storage and SQS pointer-only messages.
No GPS payload, user identifier, token, or inferred HOME/OFFICE coordinates
may enter SQS messages or logs.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Callable
from uuid import uuid4


MODEL_VARIANTS = frozenset(
    ("cp2-v2-complete-link-200m", "cp2-v2-dbscan-100m")
)


@dataclass
class Job:
    job_id: str
    owner_id: str
    payload_ref: str
    model_version: str
    idempotency_key: str
    created_at: datetime
    expires_at: datetime
    state: str = "pending"
    attempts: int = 0
    result: dict[str, object] | None = None


class SyntheticAsyncQueue:
    """Minimal at-least-once job/worker shape with owner-bound reads.

    Messages are dicts with *only* job_id. Worker fetches private payload_ref
    server-side; it is NEVER serialized into the queue.
    """

    def __init__(self, *, ttl_seconds: int = 900, max_attempts: int = 3):
        if not 60 <= ttl_seconds <= 86400 or not 1 <= max_attempts <= 10:
            raise ValueError("Invalid TTL or retry policy")
        self.ttl_seconds = ttl_seconds
        self.max_attempts = max_attempts
        self._jobs: dict[str, Job] = {}
        self._idempotency: dict[tuple[str, str], str] = {}
        self._queue: deque[dict[str, str]] = deque()
        self.dead_letter: list[dict[str, str]] = []
        self.processor_invocations = 0

    def submit(
        self,
        *,
        owner_id: str,
        payload_ref: str,
        model_version: str,
        idempotency_key: str,
        now: datetime,
    ) -> str:
        self._validate_time(now)
        if not owner_id or not idempotency_key or not payload_ref:
            raise ValueError("Owner, private payload reference and idempotency key required")
        if model_version not in MODEL_VARIANTS:
            raise ValueError("Unrecognized model variant")
        if len(owner_id) > 128 or len(payload_ref) > 256 or len(idempotency_key) > 128:
            raise ValueError("Input identifier exceeds maximum length")
        self.purge(now=now)
        existing = self._idempotency.get((owner_id, idempotency_key))
        if existing:
            job = self._jobs[existing]
            if job.payload_ref != payload_ref or job.model_version != model_version:
                raise ValueError("Idempotency-key reuse with different job")
            return job.job_id
        jid = uuid4().hex
        self._jobs[jid] = Job(
            job_id=jid,
            owner_id=owner_id,
            payload_ref=payload_ref,
            model_version=model_version,
            idempotency_key=idempotency_key,
            created_at=now,
            expires_at=now + timedelta(seconds=self.ttl_seconds),
        )
        self._idempotency[(owner_id, idempotency_key)] = jid
        self._queue.append({"job_id": jid})
        return jid

    @staticmethod
    def _validate_time(now: datetime) -> None:
        if now.tzinfo is None or now.utcoffset() is None:
            raise ValueError("Timezone-aware UTC clock required")

    def read_for_owner(self, *, owner_id: str, job_id: str, now: datetime) -> dict[str, object] | None:
        """Return None for unknown/expired/foreign jobs, avoiding ID enumeration."""
        self._validate_time(now)
        self.purge(now=now)
        job = self._jobs.get(job_id)
        if job is None or job.owner_id != owner_id:
            return None
        return {
            "job_id": job.job_id,
            "state": job.state,
            "model_version": job.model_version,
            "result": job.result,
        }

    def purge(self, *, now: datetime) -> None:
        self._validate_time(now)
        for jid, job in list(self._jobs.items()):
            if job.expires_at <= now:
                self._jobs.pop(jid)
                self._idempotency.pop((job.owner_id, job.idempotency_key), None)

    def inject_duplicate(self) -> None:
        """Simulate SQS Standard at-least-once delivery."""
        if self._queue:
            self._queue.append(dict(self._queue[0]))

    def next_message(self) -> dict[str, str] | None:
        return self._queue.popleft() if self._queue else None

    def process_one(
        self,
        *,
        now: datetime,
        processor: Callable[[str, str], dict[str, object]],
    ) -> bool:
        """Process one queue pointer, retry on failure or send to simulated DLQ."""
        self._validate_time(now)
        message = self.next_message()
        if message is None:
            return False
        if set(message) != {"job_id"}:
            raise ValueError("SQS message violates pointer-only schema")
        self.purge(now=now)
        job = self._jobs.get(message["job_id"])
        if job is None or job.state in {"succeeded", "failed"}:
            return True
        job.state = "running"
        job.attempts += 1
        try:
            self.processor_invocations += 1
            outcome = processor(job.payload_ref, job.model_version)
            if not isinstance(outcome, dict) or set(outcome) != {"synthetic_result"}:
                raise ValueError("Worker result outside approved synthetic-only contract")
            job.result = {"synthetic_result": str(outcome["synthetic_result"])[:80]}
            job.state = "succeeded"
        except Exception:
            # An actual worker must log only fixed diagnostic codes, never
            # payload_ref or exception text that could contain GPS.
            if job.attempts >= self.max_attempts:
                job.state = "failed"
                job.result = {"synthetic_result": "worker_failed"}
                self.dead_letter.append({"job_id": job.job_id})
            else:
                job.state = "pending"
                self._queue.append({"job_id": job.job_id})
        return True

    def queue_depth(self) -> int:
        return len(self._queue)


def synthetic_worker(payload_ref: str, model_version: str) -> dict[str, object]:
    """A mock worker: no GPS classification and no external data access."""
    if not payload_ref.startswith("private-test://") or model_version not in MODEL_VARIANTS:
        raise ValueError("Synthetic-only payload required")
    return {"synthetic_result": "completed_without_gps"}
