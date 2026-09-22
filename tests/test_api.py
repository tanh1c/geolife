from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
import yaml
from fastapi.testclient import TestClient

from geolife.api.app import app
from geolife.model import infer_home_office


client = TestClient(app)

BEIJING_LAT = 39.9042
BEIJING_LON = 116.4074
TOKYO_LAT = 35.6762
TOKYO_LON = 139.6503


def _utc(local_timestamp: str) -> pd.Timestamp:
    return pd.Timestamp(local_timestamp, tz="Asia/Shanghai").tz_convert("UTC")


def _stay(
    arrival_local: str,
    departure_local: str,
    *,
    latitude: float = BEIJING_LAT,
    longitude: float = BEIJING_LON,
) -> dict[str, object]:
    return {
        "arrival_time_utc": _utc(arrival_local).isoformat().replace("+00:00", "Z"),
        "departure_time_utc": _utc(departure_local).isoformat().replace("+00:00", "Z"),
        "latitude": latitude,
        "longitude": longitude,
    }


def _payload(user_id: str, stays: list[dict[str, object]]) -> dict[str, object]:
    return {"user_id": user_id, "stays": stays}


def _direct_frame(user_id: str, stays: list[dict[str, object]]) -> pd.DataFrame:
    frame = pd.DataFrame(stays)
    frame["arrival_time_utc"] = pd.to_datetime(frame["arrival_time_utc"], utc=True)
    frame["departure_time_utc"] = pd.to_datetime(frame["departure_time_utc"], utc=True)
    frame["duration_s"] = (
        frame["departure_time_utc"] - frame["arrival_time_utc"]
    ).dt.total_seconds()
    frame["user_id"] = user_id
    return frame[
        [
            "user_id",
            "arrival_time_utc",
            "departure_time_utc",
            "duration_s",
            "latitude",
            "longitude",
        ]
    ]


def _result_by_label(body: dict[str, object]) -> dict[str, dict[str, object]]:
    return {item["label"]: item for item in body["results"]}


def test_health_contract() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "geolife-home-office-api",
        "api_version": "v1",
        "model_contract": "cp2-v1",
    }


def test_home_emits_while_office_abstains() -> None:
    stays = [
        _stay("2026-01-05 21:00", "2026-01-05 22:00"),
        _stay("2026-01-06 21:00", "2026-01-06 22:00"),
        _stay("2026-01-07 21:00", "2026-01-07 22:00"),
    ]

    response = client.post("/v1/home-office/infer", json=_payload("u-home", stays))

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "u-home"
    assert body["model_contract"] == "cp2-v1"

    results = _result_by_label(body)
    assert results["HOME"]["status"] == "emitted"
    assert results["HOME"]["relevant_dates"] == 3
    assert results["OFFICE"] == {
        "label": "OFFICE",
        "status": "abstained",
        "reason": "insufficient_semantic_evidence",
    }


def test_out_of_scope_geography_is_200_with_explicit_abstention() -> None:
    stays = [
        _stay(
            "2026-01-05 21:00",
            "2026-01-05 22:00",
            latitude=TOKYO_LAT,
            longitude=TOKYO_LON,
        ),
        _stay(
            "2026-01-06 21:00",
            "2026-01-06 22:00",
            latitude=TOKYO_LAT,
            longitude=TOKYO_LON,
        ),
    ]

    response = client.post("/v1/home-office/infer", json=_payload("u-travel", stays))

    assert response.status_code == 200
    results = _result_by_label(response.json())
    for label in ["HOME", "OFFICE"]:
        assert results[label] == {
            "label": label,
            "status": "abstained",
            "reason": "out_of_scope_geography",
        }


def test_no_recurring_location_has_specific_abstention_reason() -> None:
    stays = [
        _stay("2026-01-05 21:00", "2026-01-05 22:00", latitude=39.90, longitude=116.40),
        _stay("2026-01-06 21:00", "2026-01-06 22:00", latitude=39.91, longitude=116.40),
        _stay("2026-01-07 21:00", "2026-01-07 22:00", latitude=39.92, longitude=116.40),
    ]

    response = client.post("/v1/home-office/infer", json=_payload("u-once", stays))

    assert response.status_code == 200
    results = _result_by_label(response.json())
    for label in ["HOME", "OFFICE"]:
        assert results[label]["status"] == "abstained"
        assert results[label]["reason"] == "insufficient_recurring_history"


def test_home_and_office_may_share_location_id() -> None:
    stays = []
    for day in ["2026-01-05", "2026-01-06", "2026-01-07"]:
        stays.append(_stay(f"{day} 21:00", f"{day} 22:00"))
        stays.append(_stay(f"{day} 10:00", f"{day} 11:00"))

    response = client.post("/v1/home-office/infer", json=_payload("u-both", stays))

    assert response.status_code == 200
    results = _result_by_label(response.json())
    assert results["HOME"]["status"] == "emitted"
    assert results["OFFICE"]["status"] == "emitted"
    assert results["HOME"]["location_id"] == results["OFFICE"]["location_id"]


def test_response_does_not_expose_precise_inferred_coordinates() -> None:
    stays = [
        _stay("2026-01-05 21:00", "2026-01-05 22:00"),
        _stay("2026-01-06 21:00", "2026-01-06 22:00"),
        _stay("2026-01-07 21:00", "2026-01-07 22:00"),
    ]

    response = client.post("/v1/home-office/infer", json=_payload("u-private", stays))

    assert response.status_code == 200
    encoded = response.text
    assert '"latitude"' not in encoded
    assert '"longitude"' not in encoded


def test_naive_timestamp_is_rejected() -> None:
    payload = _payload(
        "u-naive",
        [
            {
                "arrival_time_utc": "2026-01-05T21:00:00",
                "departure_time_utc": "2026-01-05T22:00:00",
                "latitude": BEIJING_LAT,
                "longitude": BEIJING_LON,
            }
        ],
    )

    response = client.post("/v1/home-office/infer", json=payload)

    assert response.status_code == 422


@pytest.mark.parametrize(
    "stay",
    [
        {
            "arrival_time_utc": "2026-01-05T13:00:00Z",
            "departure_time_utc": "2026-01-05T12:00:00Z",
            "latitude": BEIJING_LAT,
            "longitude": BEIJING_LON,
        },
        {
            "arrival_time_utc": "2026-01-05T13:00:00Z",
            "departure_time_utc": "2026-01-05T14:00:00Z",
            "latitude": 91.0,
            "longitude": BEIJING_LON,
        },
        {
            "arrival_time_utc": "2026-01-05T13:00:00Z",
            "departure_time_utc": "2026-01-05T14:00:00Z",
            "latitude": BEIJING_LAT,
            "longitude": 181.0,
        },
    ],
)
def test_invalid_interval_or_coordinates_are_rejected(stay: dict[str, object]) -> None:
    response = client.post("/v1/home-office/infer", json=_payload("u-invalid", [stay]))

    assert response.status_code == 422


def test_empty_stays_are_rejected() -> None:
    response = client.post("/v1/home-office/infer", json=_payload("u-empty", []))

    assert response.status_code == 422


def test_openapi_exposes_v1_inference_and_discriminated_result_shapes() -> None:
    schema = client.get("/openapi.json").json()

    assert "/health" in schema["paths"]
    assert "/v1/classify/{user_id}" in schema["paths"]
    assert "/v1/home-office/infer" in schema["paths"]

    post = schema["paths"]["/v1/home-office/infer"]["post"]
    assert "200" in post["responses"]
    assert "422" in post["responses"]

    response_schema = post["responses"]["200"]["content"]["application/json"]["schema"]
    assert response_schema


def test_http_result_matches_direct_production_model() -> None:
    stays = []
    for day in ["2026-01-05", "2026-01-06", "2026-01-07"]:
        stays.append(_stay(f"{day} 21:00", f"{day} 22:00"))
        stays.append(_stay(f"{day} 10:00", f"{day} 11:00"))

    direct = infer_home_office(_direct_frame("u-parity", stays))
    response = client.post("/v1/home-office/infer", json=_payload("u-parity", stays))

    assert response.status_code == 200
    http_results = _result_by_label(response.json())

    for row in direct.itertuples(index=False):
        item = http_results[row.label]
        assert item["status"] == "emitted"
        assert item["location_id"] == row.location_id
        assert item["evidence_strength"] == pytest.approx(row.evidence_strength)
        assert item["relevant_dwell_share"] == pytest.approx(row.relevant_dwell_share)
        assert item["share_margin"] == pytest.approx(row.share_margin)
        assert item["relevant_dates"] == row.relevant_dates
        assert item["relevant_dwell_h"] == pytest.approx(row.relevant_dwell_h)



def test_validation_error_does_not_echo_sensitive_input_values() -> None:
    payload = _payload(
        "u-sensitive-error",
        [
            {
                "arrival_time_utc": "2026-01-05T13:00:00Z",
                "departure_time_utc": "2026-01-05T14:00:00Z",
                "latitude": 91.123456,
                "longitude": 116.456789,
            }
        ],
    )

    response = client.post("/v1/home-office/infer", json=payload)

    assert response.status_code == 422
    assert "91.123456" not in response.text
    assert "116.456789" not in response.text


def test_request_cannot_override_frozen_model_thresholds() -> None:
    stays = [
        _stay("2026-01-05 21:00", "2026-01-05 22:00"),
        _stay("2026-01-06 21:00", "2026-01-06 22:00"),
        _stay("2026-01-07 21:00", "2026-01-07 22:00"),
    ]
    payload = _payload("u-no-override", stays)
    payload["home_min_share"] = 0.0

    response = client.post("/v1/home-office/infer", json=payload)

    assert response.status_code == 422


def test_openapi_emitted_response_schema_omits_precise_coordinates() -> None:
    schema = client.get("/openapi.json").json()
    emitted = schema["components"]["schemas"]["EmittedResult"]["properties"]

    assert "latitude" not in emitted
    assert "longitude" not in emitted


def test_committed_openapi_yaml_matches_runtime_contract_shape() -> None:
    spec_path = Path(__file__).resolve().parents[1] / "openapi.yaml"
    spec = yaml.safe_load(spec_path.read_text(encoding="utf-8"))
    runtime = client.get("/openapi.json").json()

    assert spec["openapi"] == runtime["openapi"]
    assert spec["info"] == runtime["info"]
    assert set(spec["paths"]) == set(runtime["paths"])
    assert "/health" in spec["paths"]
    assert "/v1/classify/{user_id}" in spec["paths"]
    assert "/v1/home-office/infer" in spec["paths"]

    emitted = spec["components"]["schemas"]["EmittedResult"]["properties"]
    assert "latitude" not in emitted
    assert "longitude" not in emitted



def _raw_point(
    local_timestamp: str,
    *,
    latitude: float = BEIJING_LAT,
    longitude: float = BEIJING_LON,
) -> dict[str, object]:
    return {
        "timestamp_utc": _utc(local_timestamp).isoformat().replace("+00:00", "Z"),
        "latitude": latitude,
        "longitude": longitude,
    }


def _raw_stay(
    day: str,
    start_hour: str,
    *,
    latitude: float = BEIJING_LAT,
    longitude: float = BEIJING_LON,
) -> list[dict[str, object]]:
    return [
        _raw_point(
            f"{day} {start_hour}:{minute:02d}",
            latitude=latitude,
            longitude=longitude,
        )
        for minute in [0, 5, 10, 15, 20]
    ]


def test_mentor_classify_endpoint_accepts_raw_gps_and_emits_home_confidence() -> None:
    points = []
    for day in ["2026-01-05", "2026-01-06", "2026-01-07"]:
        points.extend(_raw_stay(day, "21"))

    response = client.post(
        "/v1/classify/u-raw-home",
        json={"points": points},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == "u-raw-home"
    assert body["api_version"] == "v1"

    home = next(item for item in body["locations"] if item["label"] == "HOME")
    assert 0.0 <= home["confidence"] <= 1.0
    assert home["confidence_method"] == "home_office_evidence"

    encoded = response.text
    assert '"latitude"' not in encoded
    assert '"longitude"' not in encoded


def test_mentor_classify_endpoint_can_emit_generic_poi_from_other_recurring_location() -> None:
    points = []

    for day in ["2026-01-05", "2026-01-06", "2026-01-07"]:
        points.extend(_raw_stay(day, "21"))

    poi_lat = BEIJING_LAT + 0.004
    for day in ["2026-01-10", "2026-01-11"]:
        points.extend(
            _raw_stay(
                day,
                "18",
                latitude=poi_lat,
                longitude=BEIJING_LON,
            )
        )

    response = client.post(
        "/v1/classify/u-raw-poi",
        json={"points": points},
    )

    assert response.status_code == 200
    body = response.json()

    labels = [item["label"] for item in body["locations"]]
    assert "HOME" in labels
    assert "POI" in labels

    poi = next(item for item in body["locations"] if item["label"] == "POI")
    assert poi["confidence_method"] == "poi_visit_share"
    assert 0.0 < poi["confidence"] <= 1.0


def test_mentor_classify_endpoint_abstains_when_raw_sequence_has_no_stay() -> None:
    response = client.post(
        "/v1/classify/u-moving",
        json={
            "points": [
                _raw_point("2026-01-05 10:00"),
                _raw_point("2026-01-05 10:05", latitude=39.92),
            ]
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["locations"] == []
    assert {
        item["reason"]
        for item in body["abstentions"]
    } == {"insufficient_stay_history"}


def test_mentor_classify_openapi_documents_raw_points_poi_and_confidence() -> None:
    schema = client.get("/openapi.json").json()

    classify = schema["paths"]["/v1/classify/{user_id}"]["post"]
    assert "200" in classify["responses"]
    assert "422" in classify["responses"]

    gps = schema["components"]["schemas"]["GpsPoint"]["properties"]
    assert {"timestamp_utc", "latitude", "longitude"} <= set(gps)

    location = schema["components"]["schemas"]["ClassifiedLocation"]["properties"]
    assert "confidence" in location
    assert "confidence_method" in location
    assert "POI" in location["label"]["enum"]
