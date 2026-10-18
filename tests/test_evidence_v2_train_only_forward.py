"""Synthetic-only Stage10f tests: true TRAIN-only inference and future matching."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

from geolife.model import HomeOfficeConfig, infer_home_office


PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis" / "10f_train_only_forward_validation.py"
)


def _module():
    spec = spec_from_file_location("stage10f_train_only", PATH)
    assert spec and spec.loader
    obj = module_from_spec(spec)
    sys.modules[spec.name] = obj
    spec.loader.exec_module(obj)
    return obj


def _stays(*, change_future_location=False):
    rows = []
    # Synthetic Beijing HOME night: 14:30 UTC = 22:30 local (UTC+8).
    for day in range(1, 11):
        utc = pd.Timestamp(f"2026-01-{day:02d}T14:30:00Z")
        coord = 39.90
        if change_future_location and day >= 8:
            coord = 39.92  # Future location 2.2 km away.
        rows.append({
            "user_id": "synthetic-01",
            "arrival_time_utc": utc,
            "departure_time_utc": utc + pd.Timedelta(hours=2),
            "duration_s": 7200.0,
            "latitude": coord,
            "longitude": 116.40,
        })
    return pd.DataFrame(rows)


def test_partition_train_future_chronological_and_fixed():
    stage = _module()
    train, future, split = stage.partition_stays(_stays())
    assert len(train) == 7
    assert len(future) == 3
    assert int(split["cutoff_crossing_excluded"].iloc[0]) == 0
    assert train["departure_time_utc"].max() < future["arrival_time_utc"].min()


def test_cross_cutoff_stay_excluded_from_both_folds():
    stage = _module()
    frame = _stays()
    crossing = pd.DataFrame([{
        "user_id": "synthetic-01",
        "arrival_time_utc": pd.Timestamp("2026-01-07T23:00:00Z"),
        "departure_time_utc": pd.Timestamp("2026-01-08T01:00:00Z"),
        "duration_s": 7200.0,
        "latitude": 39.90, "longitude": 116.40,
    }])
    train, future, split = stage.partition_stays(
        pd.concat([frame, crossing], ignore_index=True)
    )
    assert len(train) == 7 and len(future) == 3
    assert int(split["cutoff_crossing_excluded"].iloc[0]) == 1


def test_train_only_emissions_match_frozen_public_model():
    stage = _module()
    train, future, _ = stage.partition_stays(_stays())
    cfg = HomeOfficeConfig()
    emitted, semantic = stage.train_only_emissions(train, config=cfg)
    public = infer_home_office(train, config=cfg)
    assert len(semantic) == len(train)
    assert sorted(emitted["label"].tolist()) == ["HOME"]
    assert set(emitted["label"].tolist()) == set(public["label"].tolist())
    assert set(emitted["location_id"].tolist()) == set(public["location_id"].tolist())
    assert emitted["train_eligible_location_count"].tolist() == [1]


def test_future_reappears_in_home_window_without_refit():
    stage = _module()
    report, results, _ = stage.forward_validate(_stays())
    assert report["overall"]["train_emitted_candidates"] == 1
    assert report["overall"]["future_window_assessable"] == 1
    assert report["overall"]["future_same_anchor_reappears"] == 1
    assert report["spatial_future_stays"]["matched"] == 3
    assert bool(results.iloc[0]["future_same_anchor_reappears"])
    assert results.iloc[0]["future_same_anchor_window_dwell_share"] == pytest.approx(1)
    assert report["calibrated_probability"] is None
    assert "synthetic-01" not in str(report)


def test_future_new_location_not_assigned_to_train_home():
    stage = _module()
    report, results, _ = stage.forward_validate(
        _stays(change_future_location=True)
    )
    assert report["spatial_future_stays"]["not_matched"] == 3
    assert report["overall"]["future_window_assessable"] == 1
    assert report["overall"]["future_same_anchor_reappears"] == 0
    assert not bool(results.iloc[0]["future_same_anchor_reappears"])


def test_ambiguous_future_mapping_abstains():
    stage = _module()
    train = pd.DataFrame([
        {"user_id": "synthetic-01", "location_id": 0,
         "latitude": 39.90, "longitude": 116.40},
        {"user_id": "synthetic-01", "location_id": 1,
         "latitude": 39.903, "longitude": 116.40},
    ])
    future = pd.DataFrame([
        {"user_id": "synthetic-01", "latitude": 39.9015, "longitude": 116.40},
    ])
    out = stage.align_to_train_locations(future, train)
    assert out.loc[0, "location_id"] == stage.AMBIGUOUS_ID
    assert out.loc[0, "spatial_match_status"] == "ambiguous"


def test_fraction_guards_and_empty_predictions():
    stage = _module()
    with pytest.raises(ValueError, match="train_fraction"):
        stage.partition_stays(_stays(), train_fraction=.99)
    with pytest.raises(ValueError, match="max_diameter_m"):
        stage.align_to_train_locations(pd.DataFrame(), pd.DataFrame(), max_diameter_m=0)
    report, rows, _ = stage.forward_validate(_stays().iloc[:3])
    # This train segment has fewer than three relevant dates, thus no emission.
    assert report["overall"]["train_emitted_candidates"] == 0
    assert rows.empty
