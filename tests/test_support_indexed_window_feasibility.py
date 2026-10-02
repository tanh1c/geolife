from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "06d_support_indexed_window_feasibility.py"
)


def _module():
    spec = spec_from_file_location("stage06d", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _day_records(dates, destinations=None):
    if destinations is None:
        destinations = [1] * len(dates)
    rows = []
    for date, destination in zip(dates, destinations, strict=True):
        rows.append(
            {
                "user_id": "u1",
                "local_date": pd.Timestamp(date).date(),
                "location_ids": (0, int(destination)),
                "edges": ((0, int(destination)),),
                "departure_hours": (8.0,),
                "cleaned_distance_km": 10.0,
                "movement_duration_proxy_h": 1.0,
            }
        )
    return pd.DataFrame(rows)


def test_support_blocks_hold_observation_count_fixed_and_apply_span_caps():
    module = _module()
    first = [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
        "2026-02-27",
        "2026-02-28",
        "2026-03-01",
    ]
    second = pd.date_range("2026-03-02", periods=6, freq="D")
    records = _day_records([*first, *second])

    windows = module.build_support_windows(
        records,
        support_days_values=(6,),
        max_span_days_values=(56, 84),
    )

    assert set(windows["usable_day_count"]) == {6}
    cap56 = windows.loc[windows["max_span_days"].eq(56)]
    cap84 = windows.loc[windows["max_span_days"].eq(84)]
    assert cap56["span_eligible"].tolist() == [False, True]
    assert cap84["span_eligible"].tolist() == [True, True]

    coverage = module.summarize_coverage(windows)
    row56 = coverage.loc[coverage["max_span_days"].eq(56)].iloc[0]
    row84 = coverage.loc[coverage["max_span_days"].eq(84)].iloc[0]
    assert int(row56["adjacent_eligible_pairs"]) == 0
    assert int(row84["adjacent_eligible_pairs"]) == 1


def test_invalid_middle_block_is_not_bridged():
    module = _module()
    block0 = pd.date_range("2026-01-01", periods=6, freq="D")
    block1 = [
        "2026-01-07",
        "2026-01-08",
        "2026-01-09",
        "2026-03-10",
        "2026-03-11",
        "2026-03-12",
    ]
    block2 = pd.date_range("2026-03-13", periods=6, freq="D")
    records = _day_records([*block0, *block1, *block2])

    windows = module.build_support_windows(
        records,
        support_days_values=(6,),
        max_span_days_values=(56,),
    )
    assert windows["span_eligible"].tolist() == [True, False, True]

    pairs = module.build_adjacent_pairs(records, windows)
    assert pairs.empty


def test_random_null_separates_exact_identity_shift_from_stable_coarse_rate():
    module = _module()
    dates = pd.date_range("2026-01-01", periods=12, freq="D")
    destinations = [1] * 6 + [2] * 6
    records = _day_records(dates, destinations)

    windows = module.build_support_windows(
        records,
        support_days_values=(6,),
        max_span_days_values=(56,),
    )
    pairs = module.build_adjacent_pairs(records, windows)
    assert len(pairs) == 1
    assert float(pairs.iloc[0]["exact_edge_jsd"]) == 1.0

    calibration = module.random_partition_calibration(
        records,
        pairs,
        repetitions=100,
        seed=7,
    )
    exact = calibration.loc[
        calibration["metric"].eq("exact_edge_jsd")
    ].iloc[0]
    coarse = calibration.loc[
        calibration["metric"].eq("transition_count_per_usable_day")
    ].iloc[0]

    assert bool(exact["observed_above_random_p95"])
    assert float(exact["observed_difference"]) == 1.0
    assert not bool(coarse["observed_above_random_p95"])
    assert float(coarse["observed_difference"]) == 0.0


def test_readiness_requires_unique_user_coverage_not_only_pair_count():
    module = _module()
    test_retest = pd.DataFrame(
        [
            {
                "support_days": 8,
                "max_span_days": 84,
                "feature": "cleaned_distance_km_per_usable_day",
                "comparable_pairs": 25,
                "users": 5,
                "spearman_test_retest": 0.8,
                "median_abs_difference": 1.0,
                "median_random_abs_difference": 1.0,
                "chronological_above_random_p95_share": 0.04,
            }
        ]
    )
    bootstrap = pd.DataFrame(
        [
            {
                "support_days": 8,
                "max_span_days": 84,
                "feature": "cleaned_distance_km_per_usable_day",
                "median_ci95_width_over_observed_iqr": 0.5,
            }
        ]
    )

    readiness = module.build_readiness_table(
        test_retest,
        bootstrap,
    ).iloc[0]

    assert bool(readiness["pair_coverage_ok"])
    assert not bool(readiness["user_coverage_ok"])
    assert not bool(readiness["coverage_ok"])
    assert not bool(readiness["candidate_for_stage07"])


def test_stage07_decision_requires_a_primary_feature():
    module = _module()
    readiness = pd.DataFrame(
        [
            {
                "support_days": 8,
                "max_span_days": 84,
                "feature": "edge_entropy",
                "primary_feature": False,
                "candidate_for_stage07": True,
            },
            {
                "support_days": 8,
                "max_span_days": 84,
                "feature": "cleaned_distance_km_per_usable_day",
                "primary_feature": True,
                "candidate_for_stage07": False,
            },
            {
                "support_days": 10,
                "max_span_days": 84,
                "feature": "cleaned_distance_km_per_usable_day",
                "primary_feature": True,
                "candidate_for_stage07": True,
            },
        ]
    )
    decision = module.build_decision_table(readiness)

    first = decision.loc[
        decision["support_days"].eq(8)
        & decision["max_span_days"].eq(84)
    ].iloc[0]
    second = decision.loc[
        decision["support_days"].eq(10)
        & decision["max_span_days"].eq(84)
    ].iloc[0]

    assert not bool(first["stage07_ready"])
    assert bool(second["stage07_ready"])
