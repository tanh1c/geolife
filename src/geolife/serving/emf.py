"""Opt-in synthetic S2b lifecycle events as bounded CloudWatch EMF JSON lines."""
from __future__ import annotations

import json
import sys
import time
from typing import TextIO

from .lifecycle_metrics import Event, METRICS, metric_series, validate_event

NAMESPACE = "GeoLife/SyntheticS2b"


def serialize(event: Event, timestamp_ms: int) -> str:
    validate_event(event)
    if not isinstance(timestamp_ms, int) or isinstance(timestamp_ms, bool) or timestamp_ms < 0:
        raise ValueError("Expected UTC epoch milliseconds")
    names = {
        "accepted": (("Accepted", 1), ("SubmitPersistAndSend", event.duration_ms)),
        "leased": (("FirstLeaseWait", event.duration_ms),),
        "attempt_failed": (("AttemptFailed", 1), ("WorkerAttempt", event.duration_ms)),
        "succeeded": (("Terminal", 1), ("TerminalDuration", event.duration_ms),
                      ("WorkerAttempt", event.worker_ms)),
        "failed": (("Terminal", 1), ("TerminalDuration", event.duration_ms)),
    }[event.name]
    fields = {name: value for name, value in names if value is not None}
    dimensions = {"model": event.model}
    if event.outcome:
        dimensions["outcome"] = event.outcome
    definitions = []
    for name, value in fields.items():
        if not isinstance(value, (int, float)) or isinstance(value, bool) or not 0 <= value < float("inf"):
            raise ValueError("Invalid metric value")
        metric_dimensions = METRICS[name][1]
        if (name, *(dimensions[key] for key in metric_dimensions)) not in metric_series():
            raise ValueError("Unbounded metric dimensions")
        definitions.append({"Name": name, "Unit": METRICS[name][0]})
    if not definitions:
        raise ValueError("Event has no publishable metrics")
    if event.name in {"succeeded", "failed"}:
        # Terminal and durations require different dimension sets in EMF.
        groups = [["model", "outcome"], ["model"]] if len(definitions) > 1 else [["model", "outcome"]]
        metrics = [definitions[:1], definitions[1:]] if len(definitions) > 1 else [definitions]
    else:
        groups, metrics = [["model"]], [definitions]
    metadata = {"Timestamp": timestamp_ms, "CloudWatchMetrics": [
        {"Namespace": NAMESPACE, "Dimensions": [keys], "Metrics": items}
        for keys, items in zip(groups, metrics) if items
    ]}
    return json.dumps({"_aws": metadata, **dimensions, **fields}, separators=(",", ":"), allow_nan=False)


class EmfRecorder:
    def __init__(self, stream: TextIO | None = None, clock_ms=None):
        self.stream = stream if stream is not None else sys.stdout
        self.clock_ms = clock_ms if clock_ms is not None else lambda: time.time_ns() // 1_000_000

    def record(self, event: Event) -> None:
        if event.name == "leased" and event.duration_ms is None:
            validate_event(event)
            return
        self.stream.write(serialize(event, self.clock_ms()) + "\n")
        self.stream.flush()
