from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "06c_change_detection_representation_feasibility.py"
)


def _module():
    spec = spec_from_file_location("stage06c", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _frames(days: int = 56, *, identity_shift: bool = True):
    dates = pd.date_range("2026-01-01", periods=days, freq="D")
    day_rows, transition_rows, point_rows = [], [], []
    for index, date in enumerate(dates):
        destination = 1 if (not identity_shift or index < days // 2) else 2
        day_rows.append({"user_id": "u1", "local_date": date.date(), "sequence": (0, destination)})
        transition_rows.append(
            {
                "user_id": "u1",
                "local_date": date.date(),
                "origin_location_id": 0,
                "destination_location_id": destination,
                "departure_hour": 8.0,
            }
        )
        point_rows.append(
            {
                "user_id": "u1",
                "local_date": date.date(),
                "cleaned_travel_distance_m": 10_000.0,
                "movement_duration_s": 3_600.0,
            }
        )
    return pd.DataFrame(day_rows), pd.DataFrame(transition_rows), pd.DataFrame(point_rows)


def test_day_records_reuse_stage06_days_and_stage03a_movement_units():
    module = _module()
    day, transitions, points = _frames(days=2, identity_shift=False)
    records = module.build_day_records(day, transitions, points)
    assert len(records) == 2
    assert records.loc[0, "location_ids"] == (0, 1)
    assert records.loc[0, "edges"] == ((0, 1),)
    assert records.loc[0, "cleaned_distance_km"] == 10.0
    assert records.loc[0, "movement_duration_proxy_h"] == 1.0


def test_fixed_calendar_windows_report_adjacent_support():
    module = _module()
    day, transitions, points = _frames(identity_shift=False)
    records = module.build_day_records(day, transitions, points)
    windows = module.build_calendar_windows(records, window_days_values=(28,))
    coverage = module.summarize_coverage(windows, min_usable_days=6)
    assert windows["usable_day_count"].tolist() == [28, 28]
    assert np.allclose(windows["calendar_coverage_share"], 1.0)
    assert int(coverage.loc[0, "adjacent_eligible_pairs"]) == 1


def test_coarse_representation_can_stay_stable_when_exact_od_changes():
    module = _module()
    day, transitions, points = _frames(identity_shift=True)
    records = module.build_day_records(day, transitions, points)
    windows = module.build_calendar_windows(records, window_days_values=(28,))
    pair = module.build_adjacent_pairs(records, windows, min_usable_days=6).iloc[0]
    assert pair["exact_edge_jsd"] == 1.0
    assert pair["left__transition_count_per_usable_day"] == 1.0
    assert pair["right__transition_count_per_usable_day"] == 1.0
    assert pair["left__edge_entropy"] == pair["right__edge_entropy"] == 0.0


def test_random_null_flags_identity_shift_not_unchanged_coarse_rate():
    module = _module()
    day, transitions, points = _frames(identity_shift=True)
    records = module.build_day_records(day, transitions, points)
    windows = module.build_calendar_windows(records, window_days_values=(28,))
    pairs = module.build_adjacent_pairs(records, windows, min_usable_days=6)
    calibration = module.random_partition_calibration(records, pairs, repetitions=80, seed=7)
    exact = calibration.loc[calibration["metric"].eq("exact_edge_jsd")].iloc[0]
    coarse = calibration.loc[
        calibration["metric"].eq("transition_count_per_usable_day")
    ].iloc[0]
    assert bool(exact["observed_above_random_p95"])
    assert float(exact["observed_difference"]) == 1.0
    assert not bool(coarse["observed_above_random_p95"])
    assert float(coarse["observed_difference"]) == 0.0


def test_insufficient_adjacent_support_returns_empty_stability_tables():
    module = _module()
    day, _transitions, points = _frames(days=6, identity_shift=False)
    transitions = pd.DataFrame(
        columns=[
            "user_id",
            "local_date",
            "origin_location_id",
            "destination_location_id",
            "departure_hour",
        ]
    )
    audit = module.run_audit(
        day,
        transitions,
        points,
        window_days_values=(28,),
        random_partitions=5,
        bootstrap_repetitions=5,
    )
    assert audit.adjacent_pairs.empty
    assert audit.random_partition.empty
    assert audit.test_retest.empty
    assert audit.readiness.empty
    assert audit.exact_od_baseline.empty
