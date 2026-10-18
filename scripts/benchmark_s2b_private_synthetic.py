"""Manual private SSM tunnel benchmark for S2b, never part of CI.

Runs the same synthetic GPS fixture synchronously and via real AWS SQS jobs.
No account token, raw location, response body or private key is printed.
Counts only complete final results; async HTTP 202 acknowledgment is a separate
metric and never compared as if it were the completed model response.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import time
import uuid
from urllib.parse import urlparse

import httpx

from geolife.serving.aws_s2b import synthetic_points


def quantile_ms(data: list[float], q: float) -> float | None:
    if not data:
        return None
    values = sorted(data)
    position = (len(values) - 1) * q
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    return round(values[lower] + (values[upper] - values[lower]) * (position - lower), 2)


def summary(data: list[float]) -> dict[str, float | None]:
    return {
        "p50_ms": quantile_ms(data, 0.5),
        "p95_ms": quantile_ms(data, 0.95),
        "p99_ms": quantile_ms(data, 0.99),
    }


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--samples", type=int, default=5)
    p.add_argument("--timeout-seconds", type=int, default=120)
    a = p.parse_args()
    parsed = urlparse(a.base_url)
    if parsed.hostname not in {"localhost", "127.0.0.1", "::1"}:
        p.error("Benchmark requires private localhost/SSM tunnel, never a public API URL")
    if not 1 <= a.samples <= 50 or not 10 <= a.timeout_seconds <= 300:
        p.error("Bounds: 1..50 samples and 10..300 timeout seconds")
    token = os.getenv("GEOLIFE_DEMO_TOKEN", "")
    if not token:
        p.error("Set GEOLIFE_DEMO_TOKEN in the current private shell")
    sync_durations: list[float] = []
    ack_durations: list[float] = []
    full_async_durations: list[float] = []
    failures: dict[str, int] = {"sync": 0, "async": 0}
    headers = {"Authorization": f"Bearer {token}"}
    points = synthetic_points("three_night_home")
    with httpx.Client(base_url=a.base_url, timeout=15, headers=headers) as client:
        for _ in range(a.samples):
            started = time.monotonic()
            try:
                sync = client.post("/v2/me/inferences", json={"points": points})
                sync.raise_for_status()
                sync_durations.append((time.monotonic() - started) * 1000)
            except (httpx.HTTPError, ValueError):
                failures["sync"] += 1
            request_headers = {"Idempotency-Key": "s2b-" + uuid.uuid4().hex}
            started = time.monotonic()
            try:
                queued = client.post(
                    "/v2/jobs", json={"fixture": "three_night_home"},
                    headers=request_headers,
                )
                queued.raise_for_status()
                ack_durations.append((time.monotonic() - started) * 1000)
                jid = queued.json()["job_id"]
                deadline = started + a.timeout_seconds
                while time.monotonic() < deadline:
                    result = client.get("/v2/jobs/" + jid)
                    result.raise_for_status()
                    obj = result.json()
                    if obj["status"] == "succeeded":
                        full_async_durations.append((time.monotonic() - started) * 1000)
                        break
                    if obj["status"] == "failed":
                        failures["async"] += 1
                        break
                    time.sleep(0.4)
                else:
                    failures["async"] += 1
            except (httpx.HTTPError, ValueError, KeyError):
                failures["async"] += 1
    print(json.dumps({
        "dataset": "hardcoded_fictional_synthetic_fixture",
        "endpoint": "localhost_or_ssm_tunnel_only",
        "samples_requested": a.samples,
        "sync_completed": len(sync_durations),
        "async_completed": len(full_async_durations),
        "sync_result_latency": summary(sync_durations),
        "async_enqueue_ack_latency": summary(ack_durations),
        "async_full_time_to_result": summary(full_async_durations),
        "errors": failures,
        "worker_duration_breakdown_available": False,
        "concurrent_load_test": False,
        "production_ready": False,
        "notice": "Sequential synthetic requests; client-observed SSM timings, not public production SLOs.",
    }, indent=2))


if __name__ == "__main__":
    main()
