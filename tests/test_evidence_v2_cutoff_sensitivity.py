"""Synthetic only. Cross-cutoff sensitivity is NOT independent holdout validation."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "analysis" / "10j_cutoff_sensitivity.py"


def _module():
    spec = spec_from_file_location("stage10j_sensitivity", SCRIPT)
    m = module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _stays():
    rows = []
    for day in range(1, 11):
        start = pd.Timestamp(f"2026-01-{day:02d}T14:30:00Z")
        rows.append({
            "user_id": "synthetic",
            "arrival_time_utc": start,
            "departure_time_utc": start + pd.Timedelta(hours=2),
            "duration_s": 7200.0,
            "latitude": 39.90,
            "longitude": 116.40,
        })
    return pd.DataFrame(rows)


def test_cutoffs_refit_only_train_stays_and_count_future_reappearance():
    stage = _module()
    report = stage.run_cutoffs(_stays())
    assert report["fractions"] == [.6, .7, .8]
    assert report["independent_participant_replications"] is False
    assert report["semantic_home_office_accuracy"] is None
    assert len(report["results"]) == 3
    for result in report["results"]:
        assert result["overall"]["train_emitted"] == 1
        assert result["overall"]["future_time_observable"] == 1
        assert result["overall"]["future_unique_spatial_observable"] == 1
        assert result["overall"]["future_same_anchor_reappears"] == 1
        assert result["overall"]["future_spatially_unresolved"] == 0
        assert result["labels"][0]["label"] == "HOME"
    assert "synthetic" not in str(report)


def test_fraction_validation():
    stage = _module()
    for fractions in ((), (.7, .7), (.4,), (.95,)):
        with pytest.raises(ValueError, match="fraction|Fraction"):
            stage.run_cutoffs(_stays(), fractions=fractions)
