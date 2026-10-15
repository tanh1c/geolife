"""Stage10e synthetic-only UTC time split feasibility tests."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest


SRC = Path(__file__).resolve().parents[1] / "analysis" / "10e_forward_holdout_preflight.py"


def _module():
    spec = spec_from_file_location("stage10e_preflight", SRC)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stays():
    rows = []
    # 10 observed UTC days, 7 train / 3 future.
    for day in range(1, 11):
        rows.append({
            "user_id": "synthetic1",
            "arrival_time_utc": pd.Timestamp(f"2026-01-{day:02d}T10:00:00Z"),
            "departure_time_utc": pd.Timestamp(f"2026-01-{day:02d}T11:00:00Z"),
        })
    # Only one observed UTC day -> can't form a holdout.
    rows.append({
        "user_id": "synthetic2",
        "arrival_time_utc": pd.Timestamp("2026-01-01T10:00:00Z"),
        "departure_time_utc": pd.Timestamp("2026-01-01T11:00:00Z"),
    })
    return pd.DataFrame(rows)


def _candidates():
    return pd.DataFrame([
        {"user_id": "synthetic1", "label": "HOME", "tier": "HOME_CORE", "location_id": 4},
        {"user_id": "synthetic2", "label": "OFFICE", "tier": "OFFICE_CORE", "location_id": 9},
    ])


def _split(stays=None, candidates=None):
    m = _module()
    return m.split_feasibility(
        _stays() if stays is None else stays,
        _candidates() if candidates is None else candidates,
        expected_stays=None, expected_users=None,
        enforce_tier_parity=False,
    )


def test_temporal_split_is_chronological_and_feasibility_aggregated():
    result = _split()
    good = result.loc[result.user_id.eq("synthetic1")].iloc[0]
    assert good.train_stays == 7
    assert good.test_stays == 3
    assert good.train_dates == 7
    assert good.test_dates == 3
    assert good.proxy_both_train_future
    sparse = result.loc[result.user_id.eq("synthetic2")].iloc[0]
    assert sparse.observed_dates == 1
    assert not sparse.proxy_both_train_future
    summary = _module().aggregate_feasibility(result)
    assert summary["overall"]["candidate_rows"] == 2
    assert summary["overall"]["both_train_and_future_proxy"] == 1
    assert summary["validated_predictive_performance"] is False
    assert "synthetic1" not in str(summary)


def test_straddling_cutoff_stays_are_excluded():
    stays = _stays()
    stays = pd.concat([
        stays,
        pd.DataFrame([{
            "user_id": "synthetic1",
            "arrival_time_utc": pd.Timestamp("2026-01-07T23:30:00Z"),
            "departure_time_utc": pd.Timestamp("2026-01-08T00:30:00Z"),
        }]),
    ], ignore_index=True)
    result = _split(stays=stays)
    row = result.loc[result.user_id.eq("synthetic1")].iloc[0]
    assert row.cross_cutoff_stays_excluded == 1
    assert row.train_stays == 7
    assert row.test_stays == 3


def test_refuses_invalid_time_intervals_and_missing_users():
    data = _stays()
    data.loc[0, "departure_time_utc"] = data.loc[0, "arrival_time_utc"]
    with pytest.raises(ValueError, match="Invalid CP1"):
        _split(stays=data)
    c = _candidates()
    c.loc[0, "user_id"] = "nonexistent"
    with pytest.raises(ValueError, match="no frozen CP1"):
        _split(candidates=c)


def test_bad_fraction_and_frozen_parity_fail_closed():
    with pytest.raises(ValueError, match="train_fraction"):
        _module().split_feasibility(
            _stays(), _candidates(), train_fraction=.95,
            expected_stays=None, expected_users=None, enforce_tier_parity=False,
        )
    with pytest.raises(ValueError, match="Frozen CP1 count mismatch"):
        _module().split_feasibility(
            _stays(), _candidates(), expected_stays=5821,
            expected_users=None, enforce_tier_parity=False,
        )
