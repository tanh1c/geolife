"""Synthetic-only Stage 10h parity + missingness tests."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT_H = ROOT / "analysis" / "10h_train_only_component_audit.py"
SCRIPT_F = ROOT / "analysis" / "10f_train_only_forward_validation.py"


def _import(path, name):
    spec = spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    mod = module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _stays():
    # Fake Beijing HOME + weekday OFFICE, no real GPS/user data.
    records = []
    for day in range(1, 11):
        base = pd.Timestamp(f"2026-01-{day:02d}T00:00:00Z")
        records.append({
            "user_id": "synthetic-01",
            "arrival_time_utc": base + pd.Timedelta(hours=14, minutes=30),
            "departure_time_utc": base + pd.Timedelta(hours=16, minutes=30),
            "duration_s": 7200.0,
            "latitude": 39.90, "longitude": 116.40,
        })
        if base.weekday() < 5:
            records.append({
                "user_id": "synthetic-01",
                "arrival_time_utc": base + pd.Timedelta(hours=2, minutes=30),
                "departure_time_utc": base + pd.Timedelta(hours=4, minutes=30),
                "duration_s": 7200.0,
                "latitude": 39.915, "longitude": 116.415,
            })
    return pd.DataFrame(records)


def _prepared():
    stage_f = _import(SCRIPT_F, "synthetic_stage10f_for_10h")
    stage_h = _import(SCRIPT_H, "synthetic_stage10h")
    stays = _stays()
    _, outcomes, _ = stage_f.forward_validate(stays)
    profile = stage_h.build_train_only_features(stays, outcomes)
    return stage_h, stays, outcomes, profile


def test_reconstruct_train_only_v1_components_from_frozen_cp2():
    stage, _, outcomes, enriched = _prepared()
    assert len(enriched) == len(outcomes) == 2
    assert set(enriched["label"]) == {"HOME", "OFFICE"}
    assert enriched["train_relative_peer_dominance"].isna().all()
    assert enriched["train_observed_date_coverage"].between(0, 1).all()
    assert enriched["train_support_factor"].between(0, 1).all()
    assert (
        enriched["train_eligible_location_count_reconstructed"] == 1
    ).all()
    assert (
        enriched["train_observed_opportunity_dates"]
        >= enriched["train_support_days_reconstructed"]
    ).all()
    report = stage.aggregate_components(enriched)
    assert report["overall"]["train_candidates"] == 2
    assert report["overall"]["train_peer_dominance_available"] == 0
    assert report["ground_truth_semantic_accuracy"] is None
    assert report["v2_model_replacement"] is False
    assert "synthetic-01" not in str(report)
    assert report["labels"][0]["median_components_assessable"][
        "train_evidence_strength"
    ] is None


def test_stage10h_rejects_tampered_v1_score_and_train_anchor():
    stage, stays, outcomes, _ = _prepared()
    changed = outcomes.copy()
    changed["train_evidence_strength"] += .01
    with pytest.raises(ValueError, match="score parity"):
        stage.build_train_only_features(stays, changed)
    changed = outcomes.copy()
    changed["train_location_id"] = 999
    with pytest.raises(ValueError, match="identity mismatch"):
        stage.build_train_only_features(stays, changed)


def test_stage10h_min_group_and_frozen_future_outcome_gates():
    stage, stays, outcomes, enriched = _prepared()
    with pytest.raises(ValueError, match="min_group"):
        stage.aggregate_components(enriched, min_group=4)
    changed = outcomes.copy()
    changed["future_same_anchor_window_dates"] = (
        changed["future_observed_window_dates"] + 1
    )
    with pytest.raises(ValueError, match="exceed observed"):
        stage.build_train_only_features(stays, changed)
