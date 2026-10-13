"""Security regression checks for restricted internal GeoLife demo.

No real GPS or dataset is needed. Private Demo mode intentionally hides
legacy/stateless inference, while normal Python model-parity mode remains
unchanged for frozen v1 contract tests.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from geolife.api.app import app
from geolife.api.security import DEFAULT_MAX_BODY_BYTES, restricted_demo_mode

client = TestClient(app)


def one_point() -> dict:
    return {"points": [
        {"timestamp_utc": "2009-01-05T13:00:00Z",
         "latitude": 39.9042, "longitude": 116.4074}
    ]}


def test_default_python_compatibility_still_operates(monkeypatch):
    monkeypatch.delenv("GEOLIFE_DEMO_AUTH_DB", raising=False)
    monkeypatch.delenv("GEOLIFE_PRIVATE_DEMO", raising=False)
    assert not restricted_demo_mode()
    assert client.post("/v1/classify/synthetic", json=one_point()).status_code == 200
    assert client.post("/v2/inferences", json=one_point()).status_code == 200


def test_private_profile_blocks_anonymous_inference_paths(monkeypatch):
    monkeypatch.setenv("GEOLIFE_PRIVATE_DEMO", "1")
    monkeypatch.delenv("GEOLIFE_DEMO_AUTH_DB", raising=False)
    assert restricted_demo_mode()
    for path in (
        "/v1/classify/000",
        "/v1/home-office/infer",
        "/v2/inferences",
    ):
        resp = client.post(path, json=one_point())
        assert resp.status_code == 404, (path, resp.text)
        assert resp.json() == {"detail": "Not found"}
        assert resp.headers["cache-control"] == "no-store"
    # The genuine scoped authenticated dataset API remains auth-gated.
    assert client.post("/v2/me/dataset-inferences").status_code == 401
    assert client.post("/v2/me/inferences", json=one_point()).status_code == 401
    assert client.get("/health").status_code == 200
    assert client.get("/v2/model-info").status_code == 200


def test_auth_db_environment_also_activates_restriction(monkeypatch):
    monkeypatch.delenv("GEOLIFE_PRIVATE_DEMO", raising=False)
    monkeypatch.setenv("GEOLIFE_DEMO_AUTH_DB", "/tmp/does-not-exist-auth-db.sqlite3")
    assert restricted_demo_mode()
    assert client.post("/v2/inferences", json=one_point()).status_code == 404
    assert client.post("/v1/classify/000", json=one_point()).status_code == 404


def test_no_store_and_clickjacking_controls_on_demo(monkeypatch):
    monkeypatch.setenv("GEOLIFE_PRIVATE_DEMO", "1")
    resp = client.get("/demo")
    assert resp.status_code == 200
    assert resp.headers["cache-control"] == "no-store"
    assert resp.headers["pragma"] == "no-cache"
    assert resp.headers["x-frame-options"] == "DENY"
    assert resp.headers["x-content-type-options"] == "nosniff"
    assert resp.headers["referrer-policy"] == "no-referrer"
    csp = resp.headers["content-security-policy"]
    assert "frame-ancestors 'none'" in csp
    assert "default-src 'self'" in csp
    assert "https://unpkg.com" in csp
    assert "*.tile.openstreetmap.org" in csp


def test_body_size_limit_returns_sanitized_413(monkeypatch):
    monkeypatch.delenv("GEOLIFE_DEMO_AUTH_DB", raising=False)
    monkeypatch.delenv("GEOLIFE_PRIVATE_DEMO", raising=False)
    payload = b"x" * (DEFAULT_MAX_BODY_BYTES + 1)
    response = client.post(
        "/v2/inferences",
        content=payload,
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 413
    assert response.json() == {"detail": "Request body too large"}
    assert "x" * 10 not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_invalid_json_does_not_reflect_coordinate_or_password(monkeypatch):
    monkeypatch.delenv("GEOLIFE_DEMO_AUTH_DB", raising=False)
    monkeypatch.delenv("GEOLIFE_PRIVATE_DEMO", raising=False)
    payload = {
        "points": [
            {"timestamp_utc": "2009-01-05T13:00:00Z",
             "latitude": 999.444555, "longitude": 116.4074}
        ]
    }
    response = client.post("/v2/inferences", json=payload)
    assert response.status_code == 422
    assert "999.444555" not in response.text
    assert "116.4074" not in response.text
