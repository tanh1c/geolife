from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pandas as pd


spec = spec_from_file_location(
    "mobile_work_hypothesis_audit", Path("analysis/03b_mobile_work_hypothesis_audit.py")
)
assert spec and spec.loader
audit = module_from_spec(spec)
spec.loader.exec_module(audit)


def test_match_controls_is_deterministic_and_stratified() -> None:
    features = pd.DataFrame(
        {
            "user_id": ["A", "B", "C", "D"],
            "mobile_work_like_candidate": [True, False, False, False],
            "recurring_location_count": [3, 3, 3, 1],
            "cp1_stay_count": [8, 8, 12, 8],
            "active_days": [10, 10, 20, 10],
            "usable_temporal_days": [5, 5, 10, 5],
            "observed_span_h": [30.0, 30.0, 60.0, 30.0],
        }
    )
    baseline = pd.DataFrame(
        {
            "user_id": ["A", "B", "C", "D"],
            "label": ["OFFICE"] * 4,
            "reject_reason": ["no_behavioral_window_overlap"] * 4,
        }
    )

    matched = audit.match_office_abstained_controls(features, baseline)

    assert matched.loc[0, ["candidate_user_id", "control_user_id"]].to_dict() == {
        "candidate_user_id": "A",
        "control_user_id": "B",
    }


def test_half_open_mode_windows_and_segment_matching_reject_boundaries() -> None:
    labels = pd.DataFrame(
        {
            "user_id": ["A", "A"],
            "start_time": pd.to_datetime(["2026-01-01 00:00Z", "2026-01-01 01:00Z"]),
            "end_time": pd.to_datetime(["2026-01-01 01:00Z", "2026-01-01 02:00Z"]),
            "mode": ["walk", "bus"],
        }
    )
    windows = audit.canonicalize_mode_windows(labels)
    segments = pd.DataFrame(
        {
            "user_id": ["A", "A"],
            "start_time": pd.to_datetime(["2026-01-01 00:10Z", "2026-01-01 00:50Z"]),
            "end_time": pd.to_datetime(["2026-01-01 00:20Z", "2026-01-01 01:10Z"]),
            "sequence_id": [0, 0],
            "distance_m": [100.0, 100.0],
        }
    )

    matched = audit.match_mode_segments(segments, windows)

    assert windows.to_dict("records") == [
        {"user_id": "A", "start_time": pd.Timestamp("2026-01-01 00:00:00+0000", tz="UTC"), "end_time": pd.Timestamp("2026-01-01 01:00:00+0000", tz="UTC"), "mode": "walk"},
        {"user_id": "A", "start_time": pd.Timestamp("2026-01-01 01:00:00+0000", tz="UTC"), "end_time": pd.Timestamp("2026-01-01 02:00:00+0000", tz="UTC"), "mode": "bus"},
    ]
    assert matched[["start_time", "end_time", "mode"]].to_dict("records") == [
        {"start_time": pd.Timestamp("2026-01-01 00:10:00+0000", tz="UTC"), "end_time": pd.Timestamp("2026-01-01 00:20:00+0000", tz="UTC"), "mode": "walk"}
    ]


def test_transition_metrics_use_location_ids_and_usable_days_only() -> None:
    stays = pd.DataFrame(
        {
            "user_id": ["A", "A", "A", "A"],
            "local_date": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02"]).date,
            "arrival_time_local": pd.to_datetime(["2026-01-01 08:00", "2026-01-01 10:00", "2026-01-02 08:00", "2026-01-02 10:00"]),
            "location_id": [0, 1, 0, 1],
            "latitude": [1.0] * 4,
            "longitude": [1.0] * 4,
        }
    )
    usable = pd.DataFrame(
        {
            "user_id": ["A", "A"],
            "local_date": pd.to_datetime(["2026-01-01", "2026-01-02"]).date,
            "usable_for_motif": [True, False],
        }
    )

    metrics = audit.build_transition_structure(stays, usable)

    assert metrics.loc[0, "recurrent_edge_count"] == 0
    assert metrics.loc[0, "transition_count"] == 1
    assert not {"latitude", "longitude"}.intersection(metrics.columns)


def test_sensitivity_keeps_frozen_candidates_primary() -> None:
    frozen = {"A", "B"}
    variants = {"baseline": {"A", "B"}, "higher": {"A"}, "lower": {"A", "B", "C"}}

    summary = audit.summarize_sensitivity(frozen, variants)

    result = summary.set_index("variant")
    assert result["jaccard"].to_dict() == {
        "baseline": 1.0,
        "higher": 0.5,
        "lower": 2 / 3,
    }
    assert result.loc["higher", ["retained", "added", "dropped"]].to_dict() == {
        "retained": 1,
        "added": 0,
        "dropped": 1,
    }
    assert result.loc["lower", ["retained", "added", "dropped"]].to_dict() == {
        "retained": 2,
        "added": 1,
        "dropped": 0,
    }


def test_mode_summary_reports_user_coverage_not_only_group_totals() -> None:
    windows = pd.DataFrame(
        {
            "user_id": ["A", "B"],
            "start_time": pd.to_datetime(["2026-01-01 00:00Z", "2026-01-02 00:00Z"]),
            "end_time": pd.to_datetime(["2026-01-01 02:00Z", "2026-01-02 04:00Z"]),
            "mode": ["walk", "bus"],
        }
    )
    segments = pd.DataFrame(
        {
            "user_id": ["A", "B"],
            "start_time": pd.to_datetime(["2026-01-01 00:00Z", "2026-01-02 00:00Z"]),
            "end_time": pd.to_datetime(["2026-01-01 01:00Z", "2026-01-02 02:00Z"]),
            "distance_m": [1000.0, 4000.0],
            "mode": ["walk", "bus"],
        }
    )

    summary = audit._mode_summary(segments, {"A": {"A", "B"}}, windows).iloc[0]

    assert summary["label_users"] == 2
    assert summary["matched_users"] == 2
    assert summary["median_labeled_duration_h_per_user"] == 3.0
    assert summary["median_matched_duration_h_per_user"] == 1.5
    assert summary["median_matched_distance_km_per_user"] == 2.5


def test_matching_reports_observation_support_balance() -> None:
    features = pd.DataFrame(
        {
            "user_id": ["A", "B"],
            "mobile_work_like_candidate": [True, False],
            "recurring_location_count": [3, 3],
            "cp1_stay_count": [8, 8],
            "active_days": [10, 10],
            "usable_temporal_days": [5, 5],
            "observed_span_h": [30.0, 30.0],
        }
    )
    baseline = pd.DataFrame(
        {"user_id": ["A", "B"], "label": ["OFFICE", "OFFICE"], "reject_reason": ["x", "x"]}
    )

    matched = audit.match_office_abstained_controls(features, baseline)

    assert {"candidate_active_days", "control_active_days", "candidate_usable_temporal_days", "control_usable_temporal_days"} <= set(matched.columns)
    assert matched.loc[0, "candidate_active_days"] == matched.loc[0, "control_active_days"]
    assert matched.loc[0, "candidate_usable_temporal_days"] == matched.loc[0, "control_usable_temporal_days"]


def test_report_avoids_semantic_work_claims_and_answers_questions() -> None:
    report = audit.render_report(
        {
            "parity": {"candidates": 23, "multiple_anchor": 23, "office_abstained": 23, "office_emitted": 0},
            "groups": {"A": 23, "B": 23, "C": 16},
            "decision": "mixed evidence",
            "feature_roles": {"independent_validation": ["mode composition"]},
        }
    )

    assert "semantic WORK" not in report
    assert "occupation" not in report.lower()
    assert "user_id" not in report
    for number in range(1, 11):
        assert f"## Q{number}" in report


def test_transition_structure_reports_edge_entropy() -> None:
    stays = pd.DataFrame(
        {
            "user_id": ["A"] * 6,
            "local_date": pd.to_datetime(
                [
                    "2026-01-01",
                    "2026-01-01",
                    "2026-01-01",
                    "2026-01-02",
                    "2026-01-02",
                    "2026-01-02",
                ]
            ).date,
            "arrival_time_local": pd.to_datetime(
                [
                    "2026-01-01 08:00",
                    "2026-01-01 09:00",
                    "2026-01-01 10:00",
                    "2026-01-02 08:00",
                    "2026-01-02 09:00",
                    "2026-01-02 10:00",
                ]
            ),
            "location_id": [0, 1, 2, 0, 1, 2],
        }
    )
    usable = pd.DataFrame(
        {
            "user_id": ["A", "A"],
            "local_date": pd.to_datetime(["2026-01-01", "2026-01-02"]).date,
            "usable_for_motif": [True, True],
        }
    )

    metrics = audit.build_transition_structure(stays, usable)

    assert metrics.loc[0, "recurrent_edge_count"] == 2
    assert metrics.loc[0, "edge_entropy"] == 1.0


def test_support_balance_reports_unmatched_group_a() -> None:
    features = pd.DataFrame(
        {
            "user_id": ["A1", "A2", "B1", "C1"],
            "active_days": [10, 12, 11, 20],
            "usable_temporal_days": [5, 6, 5, 10],
            "observed_span_h": [30.0, 40.0, 35.0, 80.0],
            "cp1_stay_count": [8, 9, 8, 30],
        }
    )
    membership = {"A": {"A1", "A2"}, "B": {"B1"}, "C": {"C1"}}
    matched = pd.DataFrame(
        {"candidate_user_id": ["A1"], "control_user_id": ["B1"]}
    )

    balance = audit._support_balance(features, membership, matched)

    status = balance.loc[balance["group"] == "A_matching_status"].iloc[0]
    assert status["matched_pairs"] == 1
    assert status["unmatched_A"] == 1


def test_candidate_features_for_anchor_recomputes_clustering_inputs() -> None:
    class FakeBase:
        def __init__(self) -> None:
            self.thresholds = []

        def cluster_behavior_locations(self, resolved, threshold_m):
            self.thresholds.append(threshold_m)
            clustered = resolved.copy()
            clustered["location_id"] = 0
            return clustered, pd.DataFrame()

        @staticmethod
        def _point_days_for_behavior(point_days):
            return point_days

        @staticmethod
        def build_user_day_features(clustered, point_days):
            return pd.DataFrame(
                {
                    "user_id": ["A"],
                    "local_date": pd.to_datetime(["2026-01-01"]).date,
                    "usable_for_temporal_profile": [True],
                    "usable_for_motif": [True],
                }
            )

        @staticmethod
        def build_user_behavior_features(clustered, point_days):
            return pd.DataFrame(
                {
                    "user_id": ["A"],
                    "weekday_usable_days": [5],
                    "weekday_mobility_repeatability": [1.0],
                    "weekday_distance_km": [10.0],
                    "recurring_daytime_locations": [2],
                    "office_dominant": [False],
                }
            )

        @staticmethod
        def compute_schedule_stability(daily):
            return pd.DataFrame()

        @staticmethod
        def _enrich_features(features, daily, stability, baseline):
            return features

        @staticmethod
        def assign_behavioral_candidates(features):
            result = features.copy()
            result["mobile_work_like_candidate"] = True
            return result

    base = FakeBase()
    resolved = pd.DataFrame(
        {
            "user_id": ["A"],
            "latitude": [1.0],
            "longitude": [1.0],
            "duration_s": [1200.0],
        }
    )

    result = audit._candidate_features_for_anchor(
        base,
        resolved,
        pd.DataFrame(),
        pd.DataFrame(),
        300.0,
    )

    assert base.thresholds == [300.0]
    assert result.loc[0, "mobile_work_like_candidate"]
