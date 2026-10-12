"""Track B1 v2 serving contract and real variant routing tests.

No raw GeoLife dataset is required. These are synthetic GPS fixtures.
"""
from __future__ import annotations

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from geolife.api.app import app
from geolife.api.v2 import (
    BASELINE, CANDIDATE, InferenceRequestV2, model_config, selected_model
)
from geolife.model import build_semantic_locations

client = TestClient(app)


def single_point():
    return {
        "timestamp_utc": "2009-01-05T13:00:00Z",
        "latitude": 39.9042,
        "longitude": 116.4074,
    }


def nightly_points():
    points = []
    for day in (5, 6, 7):
        for minute in (0, 5, 10, 15, 20):
            points.append({
                "timestamp_utc": f"2009-01-{day:02d}T13:{minute:02d}:00Z",
                "latitude": 39.9042,
                "longitude": 116.4074,
            })
    return points


def test_v2_stateless_abstention_privacy_and_metadata(monkeypatch):
    monkeypatch.setenv("GEOLIFE_ROLLOUT_MODE", "baseline")
    monkeypatch.setenv("GEOLIFE_RELEASE_ID", "sha-for-test")
    response = client.post("/v2/inferences", json={"points": [single_point()]})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["api_version"] == "v2"
    assert body["model"]["model_version"] == BASELINE
    assert body["model"]["release_id"] == "sha-for-test"
    assert body["observation"] == {
        "raw_points": 1, "detected_stays": 0, "recurring_locations": 0
    }
    assert body["predictions"]["HOME"] == {
        "status": "abstained", "reason": "insufficient_stay_history"
    }
    assert body["predictions"]["OFFICE"]["status"] == "abstained"
    assert body["other_recurring_places"] == []
    assert "user_id" not in body
    encoded = json.dumps(body)
    assert '"latitude"' not in encoded and '"longitude"' not in encoded
    assert len(body["request_id"]) >= 30


def test_v2_home_emission_uses_frozen_cp1_cp2(monkeypatch):
    monkeypatch.setenv("GEOLIFE_ROLLOUT_MODE", "baseline")
    response = client.post("/v2/inferences", json={"points": nightly_points()})
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["observation"]["detected_stays"] == 3
    home = data["predictions"]["HOME"]
    assert home["status"] == "emitted"
    assert home["evidence_method"] == "dwell_share_margin_date_support"
    assert 0 <= home["evidence_score"] <= 1
    assert home["location_ref"].startswith("L")
    assert data["predictions"]["OFFICE"]["status"] == "abstained"
    assert data["other_recurring_places"] == []


def test_v2_canary_100_percent_candidate_and_rollback(monkeypatch):
    monkeypatch.setenv("GEOLIFE_ROLLOUT_MODE", "canary")
    monkeypatch.setenv("GEOLIFE_CANARY_PERCENT", "100")
    response = client.post("/v2/inferences", json={"points": nightly_points()})
    assert response.status_code == 200, response.text
    assert response.json()["model"]["model_version"] == CANDIDATE
    assert response.json()["model"]["routing_mode"] == "canary"
    monkeypatch.setenv("GEOLIFE_ROLLOUT_MODE", "baseline")
    rollback = client.post("/v2/inferences", json={"points": nightly_points()})
    assert rollback.status_code == 200
    assert rollback.json()["model"]["model_version"] == BASELINE


def test_deterministic_canary_assignment(monkeypatch):
    monkeypatch.setenv("GEOLIFE_ROLLOUT_MODE", "canary")
    monkeypatch.setenv("GEOLIFE_CANARY_PERCENT", "10")
    monkeypatch.setenv("GEOLIFE_CANARY_SALT", "fixed-synthetic-test")
    req = InferenceRequestV2(
        client_request_id="opaque-token-77", points=[single_point()]
    )
    assert selected_model(req, "random1") == selected_model(req, "random2")
    counts = {BASELINE: 0, CANDIDATE: 0}
    for i in range(1000):
        variant = selected_model(
            InferenceRequestV2(client_request_id=f"t{i}", points=[single_point()]),
            "unused",
        )
        counts[variant] += 1
    # A statistical tolerance is appropriate; never assert exact 10% membership.
    assert 60 < counts[CANDIDATE] < 140


def test_two_real_clustering_implementations_are_distinct():
    # Four locations in a chain, each hop ~89 m. DBSCAN(100m) chains all.
    # Complete-link(200m) rejects a cluster with ~267 m diameter.
    coords = [39.0000, 39.0008, 39.0016, 39.0024]
    rows = []
    for i, lat in enumerate(coords):
        date = f"2009-01-{i+5:02d}"
        rows.append({
            "user_id": "_test_", "arrival_time_utc": f"{date}T13:00:00Z",
            "departure_time_utc": f"{date}T14:00:00Z",
            "duration_s": 3600.0, "latitude": lat, "longitude": 116.0,
        })
    stays = pd.DataFrame(rows)
    _, complete_link = build_semantic_locations(stays, config=model_config(BASELINE))
    _, dbscan = build_semantic_locations(stays, config=model_config(CANDIDATE))
    assert len(complete_link) > len(dbscan)
    assert len(dbscan) == 1
    assert complete_link["diameter_m"].max() <= 200.0 + 1e-6


@pytest.mark.parametrize("bad", [
    {"points": [{"timestamp_utc": "2009-01-05T13:00:00", "latitude": 39.9042, "longitude": 116.4074}]},
    {"points": [{"timestamp_utc": "2009-01-05T13:00:00Z", "latitude": 91.123456, "longitude": 116.4074}]},
    {"points": [single_point()], "unknown_field": "not-allowed"},
    {"points": [single_point()], "client_request_id": "person@example.com"},
])
def test_v2_invalid_input_is_sanitized(bad):
    response = client.post("/v2/inferences", json=bad)
    assert response.status_code == 422
    assert "91.123456" not in response.text
    assert "person@example.com" not in response.text


def test_v2_openapi_v1_compat_and_readiness(monkeypatch):
    monkeypatch.setenv("GEOLIFE_ROLLOUT_MODE", "baseline")
    assert client.get("/health/ready").json()["status"] == "ready"
    info = client.get("/v2/model-info").json()
    assert set(info["available_models"]) == {BASELINE, CANDIDATE}
    assert info["routing_mode"] == "baseline"
    schema = client.get("/openapi.json").json()
    assert "/v1/classify/{user_id}" in schema["paths"]
    assert "/v1/home-office/infer" in schema["paths"]
    assert "/v2/inferences" in schema["paths"]
    assert "/v2/model-info" in schema["paths"]
    assert "/health/ready" in schema["paths"]
    response_properties = schema["components"]["schemas"]["InferenceResponseV2"]["properties"]
    assert "predictions" in response_properties and "other_recurring_places" in response_properties
    assert "latitude" not in response_properties and "longitude" not in response_properties
