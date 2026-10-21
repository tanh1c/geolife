"""Synthetic fixtures only: no private GeoLife data in CI."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone

# pytest CLI on GitHub Actions does not guarantee the repo root on sys.path.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pytest

from scripts.replay_geolife_chronological_drift import (
    ReplayGateError, StayEvent, js_bits, plot_aggregate, prepare_events, replay,
    save_aggregate,
)


def sample(months: int = 8, count: int = 40) -> list[StayEvent]:
    events = []
    for m in range(1, months + 1):
        for j in range(count):
            events.append(StayEvent(
                datetime(2009, m, 1 + (j % 20), 9, tzinfo=timezone.utc),
                f"test_owner_{j % 8}",  # internal only, never in aggregate
                ("night_00_05" if m >= 6 else "morning_06_11"),
                ("120m_plus" if m >= 6 else "20_29m"),
                "unobserved",
            ))
    return events


def test_js_zero_for_identical_and_positive_for_shift():
    assert js_bits([10, 5, 3], [10, 5, 3]) == pytest.approx(0)
    assert js_bits([30, 0, 0], [0, 0, 30]) > 0.5


def test_chronology_reference_and_injected_alert_separate():
    result = replay(sample(), reference_months=2)
    assert result["reference_months_utc"] == ["2009-01", "2009-02"]
    assert result["windows"][0]["status"] == "reference"
    assert result["windows"][-1]["status"] == "observed_shift_candidate"
    assert result["injected_simulation"]["windows"][-1]["status"] == "simulated_alert"
    assert result["scope"].startswith("private_geolife_")


def test_missing_support_resets_consecutive_streak_and_suppresses_histogram():
    events = sample()
    events = [e for e in events if e.arrival_utc.month != 7 or e.owner == "test_owner_0"]
    result = replay(events, reference_months=2)
    july = next(w for w in result["windows"] if w["month_utc"] == "2009-07")
    assert july["status"] == "insufficient_support"
    assert july["histograms"] is None
    assert july["stays"] is None
    assert result["windows"][-1]["status"] == "observed"


def test_no_user_or_coordinates_in_artifacts(tmp_path):
    result = replay(sample(), reference_months=2)
    save_aggregate(result, tmp_path)
    plot_aggregate(result, tmp_path)
    data = (tmp_path / "chronological_drift_aggregate.json").read_text()
    assert "test_owner_" not in data
    assert "latitude" not in data and "longitude" not in data
    assert (tmp_path / "chronological_drift_js.png").stat().st_size > 0
    assert (tmp_path / "injected_alert_demo.png").stat().st_size > 0


def test_fail_closed_missing_schema_and_frozen_parity():
    with pytest.raises(ReplayGateError, match="CACHE_SCHEMA"):
        prepare_events(pd.DataFrame({"user_id": ["000"]}))
    frame = pd.DataFrame([{
        "user_id": "000",
        "arrival_time_utc": "2009-01-01T00:00:00Z",
        "departure_time_utc": "2009-01-01T00:20:00Z",
        "duration_s": 1200,
        "latitude": 39.9, "longitude": 116.4,
    }])
    with pytest.raises(ReplayGateError, match="FROZEN_CP1_PARITY"):
        prepare_events(frame)


def test_insufficient_windows_rejected():
    with pytest.raises(ReplayGateError, match="INSUFFICIENT_SUPPORTED_WINDOWS"):
        replay(sample(months=2), reference_months=3)


def test_fully_missing_month_resets_streak():
    events = [e for e in sample() if e.arrival_utc.month != 7]
    result = replay(events, reference_months=2)
    july = next(w for w in result["windows"] if w["month_utc"] == "2009-07")
    assert july["status"] == "insufficient_support"
    assert july["histograms"] is None
    assert result["windows"][-1]["status"] == "observed"
