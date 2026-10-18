"""Authenticated, opt-in synthetic-only destination route acceptance."""
from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

from geolife.api.app import app
from geolife.api.demo_auth import provision_account


client = TestClient(app)
URL = "/v2/me/destination-suggestions"
WHEN = "2026-09-24T08:00:00+07:00"


@pytest.fixture()
def auth_fixture(tmp_path, monkeypatch):
    path = tmp_path / "private_auth.sqlite"
    provision_account(path, "demo_000", "000", "test-only-long-secret-for-000")
    provision_account(path, "demo_001", "001", "test-only-long-secret-for-001")
    monkeypatch.setenv("GEOLIFE_DEMO_AUTH_DB", str(path))
    monkeypatch.delenv("GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER", raising=False)
    yield monkeypatch


def _bearer(account: str, pw: str) -> dict[str, str]:
    token = client.post("/v2/auth/login", json={
        "account_id": account, "password": pw,
    })
    assert token.status_code == 200
    return {"Authorization": "Bearer " + token.json()["access_token"]}


def test_recommender_requires_auth_and_explicit_flag(auth_fixture):
    anon = client.get(URL, params={"when": WHEN})
    assert anon.status_code == 401
    owner = _bearer("demo_000", "test-only-long-secret-for-000")
    disabled = client.get(URL, params={"when": WHEN}, headers=owner)
    assert disabled.status_code == 404
    auth_fixture.setenv("GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER", "1")
    live = client.get(URL, params={"when": WHEN}, headers=owner)
    assert live.status_code == 200, live.text
    assert live.json()["source"] == "synthetic_fixture"
    assert live.json()["status"] == "suggested"
    assert 1 <= len(live.json()["suggestions"]) <= 3
    assert all(1 <= x["rank"] <= 3 for x in live.json()["suggestions"])


def test_cannot_request_another_users_history_or_score(auth_fixture):
    auth_fixture.setenv("GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER", "1")
    owner_a = _bearer("demo_000", "test-only-long-secret-for-000")
    owner_b = _bearer("demo_001", "test-only-long-secret-for-001")
    a = client.get(URL, params={"when": WHEN, "account_id": "demo_001"},
                   headers=owner_a)
    b = client.get(URL, params={"when": WHEN}, headers=owner_b)
    assert a.status_code == b.status_code == 200
    assert a.json()["status"] == b.json()["status"] == "suggested"
    assert {x["place_ref"] for x in a.json()["suggestions"]}.isdisjoint(
        {x["place_ref"] for x in b.json()["suggestions"]}
    )
    assert all(x["place_ref"].startswith("s0_") for x in a.json()["suggestions"])
    assert all(x["place_ref"].startswith("s1_") for x in b.json()["suggestions"])
    for forbidden in ("evidence", "score", "confidence", "latitude", "longitude",
                      "dataset_user_id"):
        assert forbidden not in str(a.json()).lower()
    assert a.headers["Cache-Control"] == "no-store"


def test_missing_history_and_input_validation(auth_fixture):
    auth_fixture.setenv("GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER", "1")
    owner = _bearer("demo_000", "test-only-long-secret-for-000")
    before_observations = client.get(
        URL, params={"when": "2026-08-01T08:00:00+07:00"}, headers=owner
    )
    assert before_observations.status_code == 200
    assert before_observations.json()["status"] == "abstained"
    assert before_observations.json()["suggestions"] == []
    assert client.get(URL, params={"when": "2026-09-10T08:00:00"},
                      headers=owner).status_code == 422
    assert client.get(URL, params={"when": "not-a-time"},
                      headers=owner).status_code == 422


def test_local_synthetic_html_off_by_default_no_embedded_private_data(auth_fixture):
    assert client.get("/destination-demo").status_code == 404
    auth_fixture.setenv("GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER", "1")
    response = client.get("/destination-demo")
    assert response.status_code == 200
    assert response.headers["Cache-Control"] == "no-store"
    csp = response.headers["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in csp
    assert "connect-src 'self'" in csp
    assert "tile.openstreetmap.org" not in csp
    assert "/v2/me/destination-suggestions" in response.text
    assert "Top-3" in response.text
    assert "textContent = item.place_ref" in response.text
    assert "geolife-data" not in response.text
    assert "a-strong-demo-password" not in response.text
    assert "39.904" not in response.text
    assert "longitude" not in response.text


def test_recommendation_route_is_in_openapi_but_static_html_is_not(auth_fixture):
    schema = client.get("/openapi.json").json()["paths"]
    assert "/v2/me/destination-suggestions" in schema
    assert "/destination-demo" not in schema
