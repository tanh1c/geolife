from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pandas as pd


SPEC = spec_from_file_location(
    "support_controlled_03b1",
    Path("analysis/03b1_observation_support_controlled_audit.py"),
)
assert SPEC and SPEC.loader
audit = module_from_spec(SPEC)
SPEC.loader.exec_module(audit)


def test_equalized_day_sampling_preserves_pair_and_weekday_weekend_counts() -> None:
    daily = pd.DataFrame(
        {
            "user_id": ["A"] * 6 + ["B"] * 4,
            "local_date": pd.to_datetime(
                [
                    "2026-01-05",
                    "2026-01-06",
                    "2026-01-07",
                    "2026-01-10",
                    "2026-01-11",
                    "2026-01-12",
                    "2026-01-05",
                    "2026-01-06",
                    "2026-01-10",
                    "2026-01-11",
                ]
            ).date,
            "local_weekday": [0, 1, 2, 5, 6, 0, 0, 1, 5, 6],
            "usable_for_temporal_profile": [True] * 10,
            "cleaned_distance_km": np.arange(10, dtype=float),
            "movement_duration_proxy_h": [1.0] * 10,
            "boundary_count": [0] * 10,
            "stay_count": [1] * 10,
            "recurring_location_count": [1] * 10,
        }
    )

    left, right = audit._sample_equalized_days(
        daily,
        "A",
        "B",
        quality_column="usable_for_temporal_profile",
        rng=np.random.default_rng(42),
    )

    assert len(left) == len(right) == 4
    assert int((left["local_weekday"] < 5).sum()) == 2
    assert int((right["local_weekday"] < 5).sum()) == 2
    assert int((left["local_weekday"] >= 5).sum()) == 2
    assert int((right["local_weekday"] >= 5).sum()) == 2


def test_route_metrics_count_repeated_edges_across_days() -> None:
    days = pd.DataFrame(
        {
            "edge_counts": [
                {"L0->L1": 1, "L1->L0": 1},
                {"L0->L1": 1},
                {"L0->L2": 1},
            ]
        }
    )

    result = audit._route_metrics(days)

    assert result["transition_count_per_day"] == 4 / 3
    assert result["distinct_edge_count_per_day"] == 1.0
    assert result["recurrent_edge_count_per_day"] == 1 / 3
    assert result["edge_entropy"] > 0
    assert result["top_edge_frequency"] == 0.5


def test_sample_to_duration_hits_exact_target_and_scales_partial_segment() -> None:
    segments = pd.DataFrame(
        {
            "start_time": pd.to_datetime(
                ["2026-01-01 00:00Z", "2026-01-01 01:00Z"]
            ),
            "end_time": pd.to_datetime(
                ["2026-01-01 01:00Z", "2026-01-01 02:00Z"]
            ),
            "distance_m": [1000.0, 2000.0],
            "mode": ["walk", "bus"],
        }
    )

    sample = audit._sample_to_duration(
        segments,
        5400.0,
        rng=np.random.default_rng(0),
    )

    assert np.isclose(sample["duration_s"].sum(), 5400.0)
    assert sample["distance_m"].sum() <= 3000.0


def test_bootstrap_summary_uses_paired_median_per_replicate() -> None:
    rows = pd.DataFrame(
        {
            "metric": ["m", "m", "m", "m"],
            "bootstrap": [0, 0, 1, 1],
            "pair_index": [1, 2, 1, 2],
            "controlled_days": [5, 5, 5, 5],
            "difference": [1.0, 3.0, 2.0, 4.0],
        }
    )

    summary = audit._bootstrap_summary(rows).iloc[0]

    assert summary["eligible_pairs"] == 2
    assert summary["controlled_days_median"] == 5
    assert summary["paired_difference_median"] == 2.5
    assert summary["probability_difference_gt_0"] == 1.0


def test_signal_status_does_not_promote_interval_overlapping_zero() -> None:
    summary = pd.DataFrame(
        {
            "metric": ["positive", "mixed", "negative"],
            "ci95_low": [0.1, -0.1, -2.0],
            "ci95_high": [1.0, 0.3, -0.1],
        }
    )

    result = audit._signal_status(
        summary,
        ["positive", "mixed", "negative", "missing"],
    )

    assert result["positive"] == "A_higher"
    assert result["mixed"] == "overlaps_zero"
    assert result["negative"] == "B_higher"
    assert result["missing"] == "unavailable"


def test_report_is_aggregate_and_semantically_cautious() -> None:
    report = audit._render_report(
        {
            "support": {"matched_pairs": 23},
            "n_bootstraps": 100,
            "mobility_summary": [],
            "route_summary": [],
            "transport_summary": [],
            "route_signal_status": {},
            "transport_signal_status": {},
            "interpretation": "mixed",
            "decision": "semantic decision deferred",
            "next_step": "review",
        }
    )

    assert "candidate_user_id" not in report
    assert "control_user_id" not in report
    assert "proven to be a mobile worker" in report
    assert "semantic decision deferred" in report


def test_day_edge_table_avoids_local_weekday_merge_collision() -> None:
    clustered = pd.DataFrame(
        {
            "user_id": ["A", "A"],
            "local_date": pd.to_datetime(["2026-01-05", "2026-01-05"]).date,
            "local_weekday": [0, 0],
            "arrival_time_local": pd.to_datetime(
                ["2026-01-05 08:00", "2026-01-05 09:00"]
            ),
            "location_id": [0, 1],
        }
    )
    daily = pd.DataFrame(
        {
            "user_id": ["A"],
            "local_date": pd.to_datetime(["2026-01-05"]).date,
            "local_weekday": [0],
            "usable_for_motif": [True],
        }
    )

    result = audit._day_edge_table(clustered, daily)

    assert len(result) == 1
    assert result.loc[0, "local_weekday"] == 0
    assert result.loc[0, "edge_counts"] == {"L0->L1": 1}
