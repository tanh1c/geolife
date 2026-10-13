"""Authenticated synthetic-GPS sync benchmark for SSM-only private demo.

Examples:
  python scripts/benchmark_authenticated_demo.py --url http://127.0.0.1:18000 \
      --account demo_000 --requests 40 --warmup 5

The password is prompted securely (never CLI argv). This script never sends
GeoLife historical user coordinates and never prints the session bearer token.
Use a local SSM tunnel or HTTPS only. No AWS deployment is implied.
"""
from __future__ import annotations

import argparse
import getpass
import json
import statistics
import time
from collections import Counter
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


def validate_endpoint(url: str) -> str:
    parsed = urlsplit(url)
    if (parsed.scheme not in {"http", "https"} or not parsed.hostname
        or parsed.username or parsed.password or parsed.query or parsed.fragment
        or parsed.path not in ("", "/")):
        raise ValueError("An explicit local SSM URL or HTTPS origin is required")
    if parsed.scheme == "http" and parsed.hostname not in {"127.0.0.1", "localhost"}:
        raise ValueError("Unencrypted HTTP must be localhost/SSM only")
    return url.rstrip("/")


def synthetic_points() -> list[dict[str, object]]:
    return [
        {"timestamp_utc": f"2009-01-{day:02d}T13:{minute:02d}:00Z",
         "latitude": 39.9042, "longitude": 116.4074}
        for day in (5, 6, 7) for minute in (0, 5, 10, 15, 20)
    ]


def percentile(values: list[float], p: float) -> float:
    if not values or not (0 <= p <= 1):
        raise ValueError("Nonempty latency samples and percentile in [0,1] required")
    vals = sorted(values)
    rank = (len(vals) - 1) * p
    lo = int(rank)
    hi = min(lo + 1, len(vals) - 1)
    return vals[lo] * (1 - (rank - lo)) + vals[hi] * (rank - lo)


def _post_json(endpoint: str, data: dict, timeout: float, token: str | None = None) -> dict:
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    req = Request(
        endpoint, data=json.dumps(data).encode("utf-8"),
        headers=headers, method="POST"
    )
    with urlopen(req, timeout=timeout) as response:
        return json.load(response)


def benchmark(
    url: str, account: str, password: str,
    count: int, warmup: int, timeout: float,
) -> dict[str, object]:
    base = validate_endpoint(url)
    if count <= 0 or warmup < 0 or timeout <= 0:
        raise ValueError("Positive count/timeout and nonnegative warmup required")
    if not account or not password:
        raise ValueError("Explicit synthetic demo account + password required")
    auth = _post_json(
        base + "/v2/auth/login",
        {"account_id": account, "password": password}, timeout
    )
    token = auth["access_token"]
    data = {"points": synthetic_points()}
    times: list[float] = []
    status_codes: Counter[str] = Counter()
    models: Counter[str] = Counter()
    try:
        for index in range(-warmup, count):
            req = Request(
                base + "/v2/me/inferences",
                method="POST", data=json.dumps(data).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": "Bearer " + token,
                },
            )
            start = time.perf_counter()
            status = "transport_error"
            model = None
            try:
                with urlopen(req, timeout=timeout) as response:
                    status = str(response.status)
                    result = json.load(response)
                    model = result.get("model_version")
            except HTTPError as error:
                status = str(error.code)
            except (URLError, TimeoutError, ValueError):
                pass
            elapsed = (time.perf_counter() - start) * 1000
            if index < 0:
                continue
            times.append(elapsed)
            status_codes[status] += 1
            if model:
                models[str(model)] += 1
    finally:
        # Best effort revoke; never expose token in printed reports.
        try:
            _post_json(base + "/v2/auth/logout", {}, timeout, token)
        except (HTTPError, URLError, TimeoutError, ValueError):
            pass

    return {
        "benchmark": "authenticated_synthetic_gps_sync",
        "requests": count,
        "warmup": warmup,
        "success_rate": round(status_codes["200"] / count, 6),
        "status_counts": dict(status_codes),
        "model_counts": dict(models),
        "latency_ms": {
            "p50": round(percentile(times, 0.50), 3),
            "p95": round(percentile(times, 0.95), 3),
            "p99": round(percentile(times, 0.99), 3),
            "mean": round(statistics.mean(times), 3),
        },
        "notes": "Synthetic points only; client-observed sync latency; includes network/SSM tunnel.",
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:18000")
    parser.add_argument("--account", default="demo_000")
    parser.add_argument("--requests", type=int, default=50)
    parser.add_argument("--warmup", type=int, default=5)
    parser.add_argument("--timeout", type=float, default=30)
    args = parser.parse_args()
    pwd = getpass.getpass("Synthetic demo password (not logged): ")
    print(json.dumps(
        benchmark(args.url, args.account, pwd, args.requests, args.warmup, args.timeout),
        indent=2,
    ))
