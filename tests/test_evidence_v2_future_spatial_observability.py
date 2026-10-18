"""Synthetic-only Stage10i local-window observability audits."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest
from geolife.model import HomeOfficeConfig


SRC = Path(__file__).resolve().parents[1] / "analysis" / "10i_future_spatial_observability.py"


def _module():
    spec = spec_from_file_location("stage10i_spatial", SRC)
    mod = module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def _future(user, loc, *, label="HOME", n_dates=2):
    rows = []
    for i in range(n_dates):
        date = pd.Timestamp("2026-01-05") + pd.Timedelta(days=i)
        local_hour = 22 if label == "HOME" else 10
        arrival = date.tz_localize("Asia/Shanghai") + pd.Timedelta(hours=local_hour)
        rows.append({
            "user_id": user, "location_id": loc,
            "timezone_id": "Asia/Shanghai",
            "arrival_time_local": arrival,
            "departure_time_local": arrival + pd.Timedelta(hours=2),
        })
    return pd.DataFrame(rows)


def _candidate(user, label, future_dates, anchor_dates):
    return {
        "user_id": user,
        "label": label,
        "train_location_id": 8,
        "future_observed_window_dates": future_dates,
        "future_same_anchor_window_dates": anchor_dates,
    }


def test_time_observable_but_spatially_unresolved_does_not_count_as_recurrence():
    stage = _module()
    private = stage.audit_future_windows(
        pd.DataFrame([_candidate("synthetic", "HOME", 2, 0)]),
        _future("synthetic", -1),
        HomeOfficeConfig(),
    )
    r = stage.summarize_spatial(private)["overall"]
    assert r["future_time_observable"] == 1
    assert r["future_unique_spatial_observable"] == 0
    assert r["future_spatially_unresolved"] == 1
    assert r["future_anchor_not_observed"] == 1
    assert r["nonreappeared_without_unique_spatial_support"] == 1
    assert "synthetic" not in str(r)


def test_matching_other_train_anchor_is_observed_but_not_exact_candidate():
    stage = _module()
    private = stage.audit_future_windows(
        pd.DataFrame([_candidate("synthetic", "OFFICE", 2, 0)]),
        _future("synthetic", 9, label="OFFICE"),
        HomeOfficeConfig(),
    )
    r = stage.summarize_spatial(private)["overall"]
    assert r["future_unique_spatial_observable"] == 1
    assert r["future_same_anchor_reappears"] == 0
    assert r["nonreappeared_with_other_unique_anchor"] == 1


def test_matched_exact_candidate_is_counted_and_parity_guard_detects_drift():
    stage = _module()
    future = _future("synthetic", 8)
    result = pd.DataFrame([_candidate("synthetic", "HOME", 2, 2)])
    private = stage.audit_future_windows(result, future, HomeOfficeConfig())
    r = stage.summarize_spatial(private)["overall"]
    assert r["future_same_anchor_reappears"] == 1
    assert r["future_unique_spatial_observable"] == 1

    changed = result.copy()
    changed.loc[0, "future_same_anchor_window_dates"] = 1
    with pytest.raises(ValueError, match="parity mismatch"):
        stage.audit_future_windows(changed, future, HomeOfficeConfig())
