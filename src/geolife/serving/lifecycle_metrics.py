"""Local-only, best-effort synthetic job lifecycle observations."""
from __future__ import annotations

from dataclasses import dataclass, field
from itertools import product

VARIANTS = frozenset({"cp2-v2-complete-link-200m", "cp2-v2-dbscan-100m"})
OUTCOMES = frozenset({"succeeded", "failed"})
ERROR_CLASSES = frozenset({"payload_read", "payload_contract", "inference", "storage", "other"})
METRICS = {
    "Accepted": ("Count", ("model",)),
    "SubmitPersistAndSend": ("Milliseconds", ("model",)),
    "FirstLeaseWait": ("Milliseconds", ("model",)),
    "WorkerAttempt": ("Milliseconds", ("model",)),
    "AttemptFailed": ("Count", ("model",)),
    "Terminal": ("Count", ("model", "outcome")),
    "TerminalDuration": ("Milliseconds", ("model",)),
}


def metric_series() -> set[tuple[str, ...]]:
    return {(name, *values) for name, (_, dimensions) in METRICS.items()
            for values in product(*(VARIANTS if key == "model" else OUTCOMES
                                    for key in dimensions))}


assert len(metric_series()) == 16



def duration_ms(end: int, start: int) -> int | None:
    delta = end - start
    return delta if delta >= 0 else None


@dataclass(frozen=True)
class Event:
    name: str
    model: str
    duration_ms: int | None = None
    outcome: str | None = None
    worker_ms: int | None = None
    error_class: str | None = None


@dataclass
class InMemoryRecorder:
    events: list[Event] = field(default_factory=list)

    def record(self, event: Event) -> None:
        if event.name not in {"accepted", "leased", "attempt_failed", "succeeded", "failed"}:
            raise ValueError("Unknown lifecycle event")
        if event.model not in VARIANTS:
            raise ValueError("Unbounded model dimension")
        if event.outcome != (event.name if event.name in {"succeeded", "failed"} else None):
            raise ValueError("Invalid outcome dimension")
        if event.duration_ms is not None and event.duration_ms < 0:
            raise ValueError("Negative duration")
        if event.worker_ms is not None and event.worker_ms < 0:
            raise ValueError("Negative worker duration")
        if event.name not in {"succeeded", "failed"} and event.worker_ms is not None:
            raise ValueError("Worker duration only on terminal event")
        if event.name == "accepted" and event.duration_ms is None:
            raise ValueError("Accepted event requires ACK duration")
        if event.error_class is not None and (event.name != "attempt_failed" or
                                              event.error_class not in ERROR_CLASSES):
            raise ValueError("Invalid error class")
        self.events.append(event)
