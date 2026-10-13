"""Synthetic demo auth, per-user data isolation, and map disclosure regression tests.

No real GeoLife users, trajectory or private caches are included.
"""
from __future__ import annotations

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from geolife.api.app import app
from geolife.api.demo_auth import provision_account
from geolife.api.demo import _load_stays_cache


client = TestClient(app)


def synthetic_stays(user: str, lat: float) -> list[dict[str, object]]:
    # Beijing-local night observations, stored as UTC:
    # 21:00 Beijing = 13:00 UTC.
    return [
        {
            "user_id": user,
            "arrival_time_utc": f"2009-01-{day:02d}T13:00:00Z",
            "departure_time_utc": f"2009-01-{day:02d}T14:00:00Z",
            "duration_s": 3600.0,
            "latitude": lat,
            "longitude": 116.4074,
            "source_file": "synthetic.plt",
        }
        for day in (5, 6, 7)
    ]


@pytest.fixture()
def demo_setup(tmp_path, monkeypatch):
    db = tmp_path / "private-demo.sqlite"
    provision_account(db, "demo_000", "000", "a-strong-demo-password-000")
    provision_account(db, "demo_001", "001", "a-strong-demo-password-001")
    # These are deliberately different locations for the two demo IDs.
    cache = tmp_path / "trusted_cp1_stays.pkl"
    pd.DataFrame(
        synthetic_stays("000", 39.9042) + synthetic_stays("001", 39.7042)
    ).to_pickle(cache)
    _load_stays_cache.cache_clear()
    monkeypatch.setenv("GEOLIFE_DEMO_AUTH_DB", str(db))
    monkeypatch.setenv("GEOLIFE_STAYS_CACHE", str(cache))
    yield
    _load_stays_cache.cache_clear()


def login(account: str, password: str) -> str:
    response = client.post(
        "/v2/auth/login",
        json={"account_id": account, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str):
    return {"Authorization": "Bearer " + token}


def test_dataset_and_upload_require_auth(demo_setup):
    for path in ("/v2/me/dataset-inferences", "/v2/me/inferences"):
        r = client.post(path, json={"points": [{"timestamp_utc": "2009-01-05T13:00:00Z",
                                                 "latitude": 39.9, "longitude": 116.4}]})
        assert r.status_code == 401
    assert client.get("/v2/auth/me").status_code == 401


def test_login_logout_and_account_scoping(demo_setup):
    token0 = login("demo_000", "a-strong-demo-password-000")
    token1 = login("demo_001", "a-strong-demo-password-001")

    who = client.get("/v2/auth/me", headers=auth(token0))
    assert who.status_code == 200
    assert who.json() == {"account_id": "demo_000", "dataset_user_id": "000"}
    r0 = client.post("/v2/me/dataset-inferences", headers=auth(token0))
    r1 = client.post("/v2/me/dataset-inferences", headers=auth(token1))
    assert r0.status_code == 200, r0.text
    assert r1.status_code == 200, r1.text
    a, b = r0.json(), r1.json()

    assert a["dataset_user_id"] == "000" and b["dataset_user_id"] == "001"
    assert a["source"] == b["source"] == "dataset_cp1_cache"
    assert a["detected_stays"] == b["detected_stays"] == 3
    assert a["recurring_locations"] == b["recurring_locations"] == 1
    assert a["predictions"]["HOME"]["status"] == "emitted"
    assert b["predictions"]["HOME"]["status"] == "emitted"
    assert len(a["map_locations"]) >= 1 and len(b["map_locations"]) >= 1
    assert a["map_locations"][0]["latitude"] == 39.904
    assert b["map_locations"][0]["latitude"] == 39.704
    assert a["map_locations"][0]["latitude"] != b["map_locations"][0]["latitude"]
    assert "39.704" not in r0.text
    assert "39.904" not in r1.text
    assert "source_file" not in r0.text
    assert "116.4074" not in r0.text

    # Client cannot change the dataset mapping by passing an arbitrary user ID.
    override = client.post(
        "/v2/me/dataset-inferences",
        json={"dataset_user_id": "001"}, headers=auth(token0)
    )
    assert override.status_code == 200
    assert override.json()["dataset_user_id"] == "000"
    assert "39.704" not in override.text

    assert client.post("/v2/auth/logout", headers=auth(token0)).json() == {
        "logged_out": True
    }
    assert client.get("/v2/auth/me", headers=auth(token0)).status_code == 401
    assert client.get("/v2/auth/me", headers=auth(token1)).status_code == 200


def test_uploaded_gps_is_scoped_and_does_not_use_dataset_cache(demo_setup):
    token = login("demo_000", "a-strong-demo-password-000")
    one_point = [{
        "timestamp_utc": "2009-01-05T13:00:00Z",
        "latitude": 39.9042,
        "longitude": 116.4074,
    }]
    response = client.post(
        "/v2/me/inferences",
        json={"points": one_point}, headers=auth(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "new_gps"
    assert body["dataset_user_id"] == "000"
    assert body["raw_points"] == 1
    assert body["detected_stays"] == 0
    assert body["predictions"]["HOME"]["status"] == "abstained"
    assert body["map_locations"] == []


def test_invalid_credentials_do_not_expose_mapping_or_password(demo_setup):
    bad = client.post("/v2/auth/login", json={
        "account_id": "demo_000", "password": "invalid-attempt!"
    })
    unknown = client.post("/v2/auth/login", json={
        "account_id": "demo_999", "password": "invalid-attempt!"
    })
    assert bad.status_code == unknown.status_code == 401
    assert bad.json() == unknown.json()
    assert "000" not in bad.text
    assert "invalid-attempt!" not in bad.text


def test_absent_private_cache_is_503_not_any_other_user_data(demo_setup, monkeypatch):
    token = login("demo_000", "a-strong-demo-password-000")
    monkeypatch.delenv("GEOLIFE_STAYS_CACHE")
    response = client.post("/v2/me/dataset-inferences", headers=auth(token))
    assert response.status_code == 503
    assert "CP1 cache" in response.text


def test_ui_is_available_without_exposing_data_or_secrets(demo_setup):
    response = client.get("/demo")
    assert response.status_code == 200, response.text
    assert "text/html" in response.headers["content-type"]
    assert "/v2/me/dataset-inferences" in response.text
    assert "/v2/me/inferences" in response.text
    assert "OpenStreetMap" in response.text
    assert "a-strong-demo-password" not in response.text
    assert "trusted_cp1_stays" not in response.text


def test_map_endpoints_are_described_by_openapi_and_are_bearer_protected(demo_setup):
    schema = client.get("/openapi.json").json()
    for route in (
        "/v2/auth/login", "/v2/auth/logout", "/v2/auth/me",
        "/v2/me/inferences", "/v2/me/dataset-inferences",
    ):
        assert route in schema["paths"]
    assert schema["components"]["schemas"]["MapLocation"]["properties"]["latitude"]
    assert "/demo" not in schema["paths"]
    assert "GEOLIFE_DEMO_AUTH_DB" not in str(schema)
