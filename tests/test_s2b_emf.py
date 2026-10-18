"""Local EMF schema, privacy, and API/worker opt-in tests only."""
from __future__ import annotations

import io
import json

import pytest

from geolife.serving.emf import EmfRecorder, NAMESPACE, serialize
from geolife.serving.lifecycle_metrics import Event, METRICS, metric_series

MODEL = "cp2-v2-complete-link-200m"


def metric_names(obj):
    return {metric["Name"] for group in obj["_aws"]["CloudWatchMetrics"]
            for metric in group["Metrics"]}


def test_emf_schema_dimensions_and_one_flushed_json_line():
    class TrackedStream(io.StringIO):
        flushes = 0

        def flush(self):
            self.flushes += 1
            super().flush()

    stream = TrackedStream()
    recorder = EmfRecorder(stream=stream, clock_ms=lambda: 1_000_000_125)
    recorder.record(Event("accepted", MODEL, duration_ms=7))
    assert stream.flushes == 1
    assert stream.getvalue().endswith("\n") and stream.getvalue().count("\n") == 1
    assert len(stream.getvalue().encode("utf-8")) < 1024
    obj = json.loads(stream.getvalue())
    assert obj["_aws"]["Timestamp"] == 1_000_000_125
    assert set(obj) == {"_aws", "model", "Accepted", "SubmitPersistAndSend"}
    assert obj["_aws"]["CloudWatchMetrics"] == [{
        "Namespace": NAMESPACE, "Dimensions": [["model"]],
        "Metrics": [{"Name": "Accepted", "Unit": "Count"},
                    {"Name": "SubmitPersistAndSend", "Unit": "Milliseconds"}],
    }]
    assert set(metric_series()) == {
        (name, model, *outcome)
        for name in METRICS for model in (MODEL, "cp2-v2-dbscan-100m")
        for outcome in (("succeeded",), ("failed",)) if name == "Terminal"
    } | {(name, model) for name in METRICS if name != "Terminal"
         for model in (MODEL, "cp2-v2-dbscan-100m")}


def test_missing_lease_duration_skips_line_without_error():
    stream = io.StringIO()
    recorder = EmfRecorder(stream=stream, clock_ms=lambda: 1_000_000_125)
    recorder.record(Event("leased", MODEL))
    assert stream.getvalue() == ""


def test_worker_terminal_dimensions_and_missing_durations():
    event = Event("failed", MODEL, duration_ms=None, outcome="failed", worker_ms=6)
    obj = json.loads(serialize(event, 1_000_000_125))
    assert metric_names(obj) == {"Terminal"}
    assert obj["_aws"]["CloudWatchMetrics"] == [
        {"Namespace": NAMESPACE, "Dimensions": [["model", "outcome"]],
         "Metrics": [{"Name": "Terminal", "Unit": "Count"}]},
    ]
    assert "WorkerAttempt" not in obj
    assert "TerminalDuration" not in obj
    assert metric_names(json.loads(serialize(Event("attempt_failed", MODEL, 2,
                                                 error_class="payload_read"), 1_000_000_125))) == {
        "AttemptFailed", "WorkerAttempt",
    }


@pytest.mark.parametrize("event,timestamp", [
    (Event("accepted", "owner_id", 1), 1000),
    (Event("attempt_failed", MODEL, -1), 1000),
    (Event("attempt_failed", MODEL, float("nan")), 1000),
    (Event("leased", MODEL, float("inf")), 1000),
    (Event("leased", MODEL, True), 1000),
    (Event("failed", MODEL, outcome="failed", worker_ms=float("nan")), 1000),
    (Event("failed", MODEL, outcome="unexpected"), 1000),
    (Event("accepted", MODEL, 1), -1),
])
def test_emf_refuses_unbounded_or_invalid_values(event, timestamp):
    with pytest.raises(ValueError):
        serialize(event, timestamp)


def test_emf_output_does_not_copy_exception_text_or_sensitive_fields():
    obj = serialize(Event("attempt_failed", MODEL, duration_ms=3,
                          error_class="payload_read"), 1_000_000_125)
    assert all(word not in obj for word in ("job_id", "owner_id", "token", "password",
                                            "latitude", "longitude", "payload_read"))
