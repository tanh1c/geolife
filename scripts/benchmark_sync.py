"""Privacy-safe synchronous serving latency benchmark with synthetic GeoLife-like GPS.

Run against an explicitly started development service. This is not an accuracy
benchmark and does not upload real user location data.
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def percentile(values: list[float], fraction: float) -> float:
    if not values:
        raise ValueError("No latency samples")
    if not 0.0 <= fraction <= 1.0:
        raise ValueError("fraction must be 0..1")
    ordered = sorted(values)
    pos = (len(ordered) - 1) * fraction
    low = int(pos)
    high = min(low + 1, len(ordered) - 1)
    return float(ordered[low] * (1 - (pos - low)) + ordered[high] * (pos - low))


def synthetic_points() -> list[dict[str, object]]:
    return [
        {
            "timestamp_utc": f"2009-01-{day:02d}T13:{minute:02d}:00Z",
            "latitude": 39.9042,
            "longitude": 116.4074,
        }
        for day in (5, 6, 7)
        for minute in (0, 5, 10, 15, 20)
    ]


def benchmark(base_url: str, n: int, warmup: int, timeout: float) -> dict[str, object]:
    if n <= 0 or warmup < 0:
        raise ValueError("requests must be positive; warmup cannot be negative")
    if not base_url.startswith(("http://127.0.0.1:", "http://localhost:", "https://")):
        raise ValueError("Use local HTTP or an explicitly secured HTTPS endpoint")

    endpoint = base_url.rstrip("/") + "/v2/inferences"
    latencies_ms = []
    status_codes = Counter()
    variants = Counter()
    for ix in range(-warmup, n):
        # Opaque, synthetic token only. No GeoLife identity or real GPS.
        body = json.dumps({
            "client_request_id": f"synthetic-bench-{ix+warmup:05d}",
            "points": synthetic_points(),
        }).encode()
        request = Request(
            endpoint,
            method="POST",
            data=body,
            headers={"Content-Type": "application/json"},
        )
        started = time.perf_counter()
        code = None
        variant = None
        try:
            with urlopen(request, timeout=timeout) as response:
                code = response.status
                data = json.load(response)
                variant = data.get("model", {}).get("model_version", "unknown")
        except HTTPError as error:
            code = error.code
        except (URLError, TimeoutError, ValueError):
            code = "transport_error"
        duration_ms = (time.perf_counter() - started) * 1000
        if ix < 0:
            continue
        latencies_ms.append(duration_ms)
        status_codes[str(code)] += 1
        if variant is not None:
            variants[variant] += 1
    return {
        "benchmark": "synthetic_v2_sync",
        "requests": n,
        "warmup": warmup,
        "success_rate": round(status_codes["200"] / n, 6),
        "status_counts": dict(status_codes),
        "model_counts": dict(variants),
        "latency_ms": {
            "p50": round(percentile(latencies_ms, .50), 3),
            "p95": round(percentile(latencies_ms, .95), 3),
            "p99": round(percentile(latencies_ms, .99), 3),
            "mean": round(statistics.mean(latencies_ms), 3),
        },
        "notes": "Synthetic GPS; client-observed sync request/response; no ground truth.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.url, args.requests, args.warmup, args.timeout), indent=2))
