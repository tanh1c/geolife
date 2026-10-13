from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


MODULE = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_sync.py"
SPEC = importlib.util.spec_from_file_location("bench_sync", MODULE)
assert SPEC is not None and SPEC.loader is not None
bench = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(bench)


def test_percentile_interpolation_is_deterministic():
    assert bench.percentile([10, 20, 30, 40, 50], .5) == 30
    assert bench.percentile([1, 9], .95) == pytest.approx(8.6)
    with pytest.raises(ValueError):
        bench.percentile([], .95)


def test_benchmark_payload_is_synthetic_and_non_identifying():
    points = bench.synthetic_points()
    assert len(points) == 15
    assert all(p["timestamp_utc"].endswith("Z") for p in points)
    assert all(p["latitude"] == 39.9042 for p in points)
    assert not any("user_id" in p for p in points)


def test_benchmark_rejects_unsecured_public_http_url():
    with pytest.raises(ValueError, match="secured HTTPS"):
        bench.benchmark("http://example.com:8000", 1, 0, 1)
