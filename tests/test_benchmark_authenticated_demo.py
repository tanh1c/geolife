"""Synthetic-only unit tests for the authenticated benchmark CLI."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

PATH = Path(__file__).resolve().parents[1] / "scripts" / "benchmark_authenticated_demo.py"
SPEC = importlib.util.spec_from_file_location("bench_auth", PATH)
assert SPEC and SPEC.loader
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class FakeHttpResponse:
    def __init__(self, data: dict):
        self.data = data
        self.status = 200
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc, tb):
        return False
    def read(self, _n: int = -1):
        return json.dumps(self.data).encode("utf-8")


def test_rejects_unsafe_http_and_authority_bypass():
    for url in (
        "http://example.com:8000",
        "http://127.0.0.1:18000@evil.example",
        "http://localhost:18000@evil.example",
        "ftp://127.0.0.1",
        "http://127.0.0.1:18000/path",
        "http://127.0.0.1:18000#fragment",
    ):
        with pytest.raises(ValueError):
            mod.validate_endpoint(url)
    assert mod.validate_endpoint("http://127.0.0.1:18000/") == "http://127.0.0.1:18000"
    assert mod.validate_endpoint("https://example.com") == "https://example.com"


def test_authenticated_measurement_never_discloses_password_or_token(monkeypatch):
    seen = []
    def fake_open(req, timeout=None):
        seen.append((req.full_url, req.get_header("Authorization"), req.data))
        if req.full_url.endswith("/v2/auth/login"):
            return FakeHttpResponse({"access_token": "synthetic-test-secret-token"})
        if req.full_url.endswith("/v2/auth/logout"):
            return FakeHttpResponse({"logged_out": True})
        return FakeHttpResponse({"model_version": "cp2-v2-dbscan-100m"})

    monkeypatch.setattr(mod, "urlopen", fake_open)
    result = mod.benchmark(
        "http://127.0.0.1:18000", "demo_000",
        "synthetic-test-password", count=3, warmup=1, timeout=5
    )
    assert result["requests"] == 3
    assert result["success_rate"] == 1.0
    assert result["model_counts"] == {"cp2-v2-dbscan-100m": 3}
    assert len(seen) == 6  # login + 4 inference + logout
    assert seen[1][1] == "Bearer synthetic-test-secret-token"
    assert seen[-1][1] == "Bearer synthetic-test-secret-token"
    assert "synthetic-test-secret-token" not in str(result)
    assert "synthetic-test-password" not in str(result)
    assert all("39.9042" in str(row[2]) for row in seen[1:-1])
    assert "p99" in result["latency_ms"]


def test_requires_positive_benchmark_sizes():
    with pytest.raises(ValueError):
        mod.benchmark("http://127.0.0.1:18000", "demo_000", "pass", 0, 0, 5)
    with pytest.raises(ValueError):
        mod.benchmark("http://127.0.0.1:18000", "demo_000", "pass", 5, -1, 5)
