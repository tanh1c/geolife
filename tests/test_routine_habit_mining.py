from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analysis" / "06_routine_habit_mining.py"


def _module():
    spec = spec_from_file_location("stage06", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_circular_hours_wrap_midnight() -> None:
    module = _module()
    mean_hour, concentration = module.circular_hour_stats([23.5, 0.5])
    assert mean_hour < 1.0 or mean_hour > 23.0
    assert concentration > 0.95


def test_supported_sequence_collapses_consecutive_duplicate_locations() -> None:
    module = _module()
    tz = "Asia/Shanghai"
    base = pd.Timestamp("2026-01-05 08:00", tz=tz)

    stays = pd.DataFrame(
        {
            "user_id": ["u1"] * 5,
            "location_id": [0, 0, 1, 1, 0],
            "arrival_time_local": [
                base,
                base + pd.Timedelta(hours=1),
                base + pd.Timedelta(hours=3),
                base + pd.Timedelta(hours=4),
                base + pd.Timedelta(hours=6),
            ],
            "departure_time_local": [
                base + pd.Timedelta(minutes=30),
                base + pd.Timedelta(hours=2),
                base + pd.Timedelta(hours=3, minutes=30),
                base + pd.Timedelta(hours=5),
                base + pd.Timedelta(hours=7),
            ],
        }
    )
    stays["arrival_time_utc"] = stays["arrival_time_local"].map(lambda x: x.tz_convert("UTC"))
    stays["departure_time_utc"] = stays["departure_time_local"].map(lambda x: x.tz_convert("UTC"))

    support = pd.DataFrame(
        {
            "user_id": ["u1"],
            "local_date": [base.date()],
            "usable_for_motif": [True],
        }
    )

    days, transitions = module.build_supported_day_sequences(stays, support)

    assert days.iloc[0]["sequence"] == (0, 1, 0)
    assert transitions["edge"].tolist() == ["L0→L1", "L1→L0"]


def test_synthetic_self_check() -> None:
    result = _module().synthetic_self_check()
    assert result["status"] == "ok"
    assert result["top_edge_active_days"] >= 10
    assert result["top_edge_departure_concentration"] > 0.95
    assert result["split_same_top_edge"]
