"""Pure synthetic checks for the real-Modal E2E auditor.

CI must never require access to or fetch the actual GeoLife private cache.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd
import pytest


PATH = Path(__file__).resolve().parents[1] / "scripts" / "modal_real_data_e2e.py"
SPEC = importlib.util.spec_from_file_location("modal_real_data_e2e", PATH)
assert SPEC and SPEC.loader
audit = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_cohort_selection_without_hardcoding_private_user_ids():
    stays = pd.DataFrame({"user_id": ["000", "001", "002"]})
    recurring = pd.DataFrame({"user_id": ["000", "001", "002"]})
    selected = pd.DataFrame({"user_id": ["000", "001"],
                             "label": ["HOME", "OFFICE"]})
    groups = audit.select_cases(stays, recurring, selected)
    assert groups["HOME"] == "000"
    assert groups["OFFICE"] == "001"
    assert groups["RECURRING_ABSTAIN"] == "002"
    assert groups["NO_STAY"] == "003"
    assert len(groups) == 4


def test_cohort_selection_fails_explicitly_if_no_home():
    stays = pd.DataFrame({"user_id": ["000"]})
    recurring = pd.DataFrame({"user_id": ["000"]})
    selected = pd.DataFrame(columns=["user_id", "label"])
    with pytest.raises(audit.AuditGateFailure, match="HOME_CASE"):
        audit.select_cases(stays, recurring, selected)


def test_user_id_normalization_and_schema_guard():
    rows = pd.DataFrame([{
        "user_id": 0,
        "arrival_time_utc": "2009-01-05T13:00:00Z",
        "departure_time_utc": "2009-01-05T14:00:00Z",
        "duration_s": 3600,
        "latitude": 39.0,
        "longitude": 116.0,
    }])
    clean = audit.normalize_users(rows)
    assert clean.user_id.tolist() == ["000"]
    with pytest.raises(audit.AuditGateFailure, match="CP1_CACHE_SCHEMA"):
        audit.normalize_users(rows.drop(columns=["duration_s"]))


def _map_fixture():
    stays = pd.DataFrame([{"user_id": "000"}])
    locations = pd.DataFrame([{
        "user_id": "000", "location_id": 0,
        "latitude": 39.90423, "longitude": 116.40744,
        "stay_count": 3, "total_dwell_h": 4.0,
    }])
    selected = pd.DataFrame([{
        "user_id": "000", "label": "HOME", "location_id": 0,
        "evidence_strength": 0.8,
    }])
    payload = {
        "dataset_user_id": "000",
        "source": "dataset_cp1_cache",
        "detected_stays": 1,
        "recurring_locations": 1,
        "raw_points": None,
        "model_version": "cp2-v2-complete-link-200m",
        "coordinate_precision": "rounded_3_decimals",
        "predictions": {
            "HOME": {"status": "emitted", "location_ref": "L0", "evidence_score": 0.8},
            "OFFICE": {"status": "abstained", "reason": "insufficient_semantic_evidence"},
        },
        "map_locations": [{
            "location_ref": "L0", "label": "HOME", "latitude": 39.904,
            "longitude": 116.407, "visit_count": 3,
        }],
    }
    return stays, locations, selected, payload


def test_auth_map_parity_accepts_rounding_only():
    stays, locations, selected, payload = _map_fixture()
    audit.validate_inference(payload, "000", stays, locations, selected)


def test_map_parity_detects_cross_account_or_inexact_coordinates():
    stays, locations, selected, payload = _map_fixture()
    payload["dataset_user_id"] = "001"
    with pytest.raises(audit.AuditGateFailure, match="ACCOUNT_SCOPE_USER_ID"):
        audit.validate_inference(payload, "000", stays, locations, selected)
    payload["dataset_user_id"] = "000"
    payload["map_locations"][0]["latitude"] = 39.905
    with pytest.raises(audit.AuditGateFailure, match="MAP_LATITUDE_PARITY"):
        audit.validate_inference(payload, "000", stays, locations, selected)


def test_missing_trusted_cache_fails_cleanly(tmp_path):
    with pytest.raises(audit.AuditGateFailure, match="PRIVATE_CP1_CACHE_MISSING"):
        audit.execute(tmp_path / "does-not-exist.pkl")


def test_synthetic_upload_fixture_does_not_use_real_user_data():
    sample = audit._synthetic_new_points()
    assert len(sample) == 15
    assert all(pt["timestamp_utc"].endswith("Z") for pt in sample)
    assert all(pt["latitude"] == 39.9 and pt["longitude"] == 116.4 for pt in sample)
    assert all("user_id" not in pt for pt in sample)
