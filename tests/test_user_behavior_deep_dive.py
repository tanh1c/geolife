from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from types import SimpleNamespace

import pandas as pd
import pytest


spec = spec_from_file_location(
    "user_behavior_deep_dive", Path("analysis/03a_user_behavior_deep_dive.py")
)
assert spec and spec.loader
behavior = module_from_spec(spec)
spec.loader.exec_module(behavior)


def _stays(count: int, users: int) -> pd.DataFrame:
    return pd.DataFrame({
        "user_id": [f"{index % users:03d}" for index in range(count)],
        "source_file": ["Data/000/Trajectory/example.plt"] * count,
        "sequence_id": [0] * count,
        "arrival_time_utc": pd.Timestamp("2008-01-01", tz="UTC"),
        "departure_time_utc": pd.Timestamp("2008-01-01 00:20", tz="UTC"),
        "duration_s": [1200.0] * count,
        "latitude": [39.0] * count,
        "longitude": [116.0] * count,
        "n_points": [2] * count,
    })


def _point_days(users: int) -> pd.DataFrame:
    return pd.DataFrame({
        "user_id": [f"{index:03d}" for index in range(users)],
        "local_date": pd.Timestamp("2008-01-01").date(),
    })


def test_private_artifact_path_rejects_paths_outside_03a() -> None:
    with pytest.raises(ValueError, match="artifacts/03a"):
        behavior.ensure_private_artifact_path(Path("reports/leak.csv"))


def test_private_artifact_path_rejects_normalized_traversal_escape() -> None:
    with pytest.raises(ValueError, match="artifacts/03a"):
        behavior.ensure_private_artifact_path(Path("artifacts/03a/../leak.pkl"))


def test_validate_materialization_rejects_wrong_frozen_stay_reconciliation() -> None:
    with pytest.raises(AssertionError, match="5,821 stays"):
        behavior.validate_materialization(
            _stays(1, users=1),
            _point_days(users=1),
            {f"{index:03d}" for index in range(182)},
        )


def test_validate_materialization_requires_182_release_users() -> None:
    with pytest.raises(AssertionError, match="182 release users"):
        behavior.validate_materialization(
            _stays(5821, users=136), _point_days(users=136), {"001"}
        )


def test_validate_materialization_rejects_duplicate_user_day_rows() -> None:
    point_days = pd.concat([_point_days(users=136), _point_days(users=136)], ignore_index=True)
    with pytest.raises(AssertionError, match="one row per user and local date"):
        behavior.validate_materialization(
            _stays(5821, users=136), point_days, {f"{index:03d}" for index in range(182)}
        )


def test_validate_materialization_accepts_frozen_reconciliation() -> None:
    release_users = {f"{index:03d}" for index in range(182)}
    behavior.validate_materialization(
        _stays(5821, users=136), _point_days(users=136), release_users
    )


def test_process_trajectory_uses_frozen_cp1_and_emits_daily_point_metrics() -> None:
    raw = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                [
                    "2008-01-01T00:00:00Z",
                    "2008-01-01T00:05:00Z",
                    "2008-01-01T00:10:00Z",
                    "2008-01-01T00:15:00Z",
                    "2008-01-01T00:20:00Z",
                ]
            ),
            "latitude": [39.0] * 5,
            "longitude": [116.0] * 5,
        }
    )

    stays, point_days = behavior.process_trajectory(
        "001", "Data/001/Trajectory/example.plt", raw
    )

    assert stays.loc[0, "user_id"] == "001"
    assert stays.loc[0, "source_file"] == "Data/001/Trajectory/example.plt"
    assert stays.loc[0, "duration_s"] == 1200.0
    assert point_days.loc[0, "point_count"] == 5
    assert point_days.loc[0, "observed_span_s"] == 1200.0
    assert point_days.loc[0, "cleaned_travel_distance_m"] == 0.0


def test_materialization_aggregates_same_user_day_across_plt_files(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    zip_path = tmp_path / "geolife.zip"
    plt_a = "\n".join(
        ["header"] * 6
        + [f"39.0,116.0,0,0,0,2008-01-01,00:{minute:02d}:00" for minute in range(0, 25, 5)]
    )
    plt_b = "\n".join(
        ["header"] * 6
        + [f"39.0,116.0,0,0,0,2008-01-01,01:{minute:02d}:00" for minute in range(0, 25, 5)]
    )
    with behavior.zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("Geolife Trajectories 1.3/Data/001/Trajectory/a.plt", plt_a)
        archive.writestr("Geolife Trajectories 1.3/Data/001/Trajectory/b.plt", plt_b)

    cache_dir = Path("artifacts/03a/test_same_day_aggregation")
    stay_cache = cache_dir / "stays.pkl"
    point_day_cache = cache_dir / "point_days.pkl"
    monkeypatch.setattr(behavior, "EXPECTED_STAYS", 2)
    monkeypatch.setattr(behavior, "EXPECTED_STAY_USERS", 1)
    monkeypatch.setattr(behavior, "EXPECTED_RELEASE_USERS", 1)
    try:
        _stays, point_days = behavior.materialize_frozen_cp1(zip_path, stay_cache, point_day_cache)
    finally:
        for cache in (stay_cache, point_day_cache):
            cache.unlink(missing_ok=True)
        cache_dir.rmdir()

    assert len(point_days) == 1
    assert point_days.loc[0, "point_count"] == 10
    assert point_days.loc[0, "observed_span_s"] == 4800.0
    assert point_days.loc[0, "movement_duration_s"] == 2400.0


def test_process_trajectory_does_not_bridge_cp1_boundaries_for_movement() -> None:
    raw = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2008-01-01T00:00:00Z", "2008-01-01T00:05:01Z"]
            ),
            "latitude": [39.0, 40.0],
            "longitude": [116.0, 116.0],
        }
    )

    _stays, point_days = behavior.process_trajectory(
        "001", "Data/001/Trajectory/example.plt", raw
    )

    assert point_days.loc[0, "cleaned_travel_distance_m"] == 0.0
    assert point_days.loc[0, "movement_duration_s"] == 0.0


def test_process_trajectory_allocates_terminal_audit_event_to_its_day() -> None:
    raw = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2008-01-01T00:00:00Z", "2008-01-01T00:10:00Z"]
            ),
            "latitude": [39.0, 999.0],
            "longitude": [116.0, 116.0],
        }
    )

    _stays, point_days = behavior.process_trajectory(
        "001", "Data/001/Trajectory/example.plt", raw
    )

    assert point_days.loc[0, "transition_count"] == 1


def test_process_trajectory_emits_audit_only_utc_day() -> None:
    raw = pd.DataFrame(
        {
            "timestamp": pd.to_datetime(
                ["2008-01-01T00:00:00Z", "2008-01-02T00:00:00Z"]
            ),
            "latitude": [39.0, 999.0],
            "longitude": [116.0, 116.0],
        }
    )

    _stays, point_days = behavior.process_trajectory(
        "001", "Data/001/Trajectory/example.plt", raw
    )

    jan_2 = point_days.loc[point_days["local_date"] == pd.Timestamp("2008-01-02").date()].iloc[0]
    assert jan_2["point_count"] == 0
    assert jan_2["observed_span_s"] == 0.0
    assert jan_2["cleaned_travel_distance_m"] == 0.0
    assert jan_2["movement_duration_s"] == 0.0
    assert jan_2["transition_count"] == 1


def _cleaned_points(rows: list[tuple[str, float, float, int, str | None]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": "A",
            "timestamp": pd.to_datetime([row[0] for row in rows], utc=True),
            "latitude": [row[1] for row in rows],
            "longitude": [row[2] for row in rows],
            "sequence_id": [row[3] for row in rows],
            "boundary_before_reason": [row[4] for row in rows],
        }
    )


def test_cleaned_point_day_distance_uses_adjacent_cleaned_points_not_stays() -> None:
    """Catches a regression that substitutes stay displacement for point movement."""
    cleaned = _cleaned_points(
        [
            ("2026-01-01T00:00:00Z", 39.9000, 116.4000, 0, None),
            ("2026-01-01T01:00:00Z", 39.9100, 116.4000, 0, None),
            ("2026-01-01T02:00:00Z", 39.9200, 116.4000, 0, None),
        ]
    )

    row = behavior.summarize_cleaned_point_days(cleaned, "Asia/Shanghai").iloc[0]

    assert row["cleaned_distance_km"] > 2.0
    assert row["point_count"] == 3
    assert row["movement_duration_proxy_h"] == 2.0


def test_cleaned_point_days_do_not_bridge_sequences_or_non_positive_time() -> None:
    """Catches movement segments that cross CP1 boundaries or reversed timestamps."""
    cleaned = _cleaned_points(
        [
            ("2026-01-01T00:00:00Z", 39.9000, 116.4000, 0, None),
            ("2026-01-01T01:00:00Z", 39.9100, 116.4000, 0, None),
            ("2026-01-01T02:00:00Z", 40.9100, 116.4000, 1, "gap"),
            ("2026-01-01T01:30:00Z", 40.9200, 116.4000, 1, None),
        ]
    )

    row = behavior.summarize_cleaned_point_days(cleaned, "Asia/Shanghai").iloc[0]

    assert 1.0 < row["cleaned_distance_km"] < 2.0
    assert row["movement_duration_proxy_h"] == 1.0
    assert row["boundary_count"] == 1


def test_day_quality_marks_sparse_or_gappy_day_not_usable() -> None:
    """Catches temporal-profile eligibility that ignores sparse or gappy observation."""
    day = pd.DataFrame(
        [{"point_count": 2, "observed_span_h": 1.0, "largest_gap_h": 7.0}]
    )

    result = behavior.classify_day_quality(day).iloc[0]

    assert not result["usable_for_temporal_profile"]


def test_day_quality_requires_stay_span_for_motif_eligibility() -> None:
    """Catches motif eligibility inferred from cleaned points instead of stay evidence."""
    day = pd.DataFrame(
        [{"stay_count": 1, "stay_observed_span_h": 1.5, "point_count": 3,
          "observed_span_h": 3.0, "largest_gap_h": 1.0}]
    )

    result = behavior.classify_day_quality(day).iloc[0]

    assert not result["usable_for_motif"]


def _local_stays(rows: list[tuple[str, str, float, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": [row[0] for row in rows],
            "arrival_time_utc": pd.to_datetime([row[1] for row in rows], utc=True),
            "departure_time_utc": pd.to_datetime([row[1] for row in rows], utc=True)
            + pd.to_timedelta([row[4] for row in rows], unit="s"),
            "latitude": [row[2] for row in rows],
            "longitude": [row[3] for row in rows],
            "duration_s": [row[4] for row in rows],
        }
    )


def test_location_ids_rank_dwell_before_first_seen() -> None:
    """Catches deterministic labels ranked by arrival rather than accumulated dwell."""
    stays = _local_stays(
        [
            ("A", "2026-01-01T01:00:00Z", 39.90, 116.40, 3600),
            ("A", "2026-01-02T01:00:00Z", 39.90, 116.40, 3600),
            ("A", "2026-01-01T02:00:00Z", 39.91, 116.40, 1200),
        ]
    )

    clustered, _ = behavior.cluster_behavior_locations(stays, 200.0)

    assert clustered.groupby("location_id")["duration_s"].sum().idxmax() == 0


def test_resolved_local_time_retains_non_beijing_stay_when_timezone_resolves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Catches an all-resolved exploratory view that filters valid non-Beijing stays."""
    class Finder:
        def __init__(self, *, in_memory: bool) -> None:
            assert in_memory

        def timezone_at(self, *, lng: float, lat: float) -> str:
            assert (lat, lng) == (35.6762, 139.6503)
            return "Asia/Tokyo"

    monkeypatch.setitem(sys.modules, "timezonefinder", SimpleNamespace(TimezoneFinder=Finder))
    stays = _local_stays([("A", "2026-01-01T01:00:00Z", 35.6762, 139.6503, 1200)])

    result = behavior.resolve_stay_timezones(stays)

    assert result.loc[0, "timezone_id"] == "Asia/Tokyo"
    assert result.loc[0, "local_date"] == pd.Timestamp("2026-01-01").date()


def test_resolved_local_time_explains_missing_timezonefinder() -> None:
    """Catches a missing dependency failing without the prescribed behavior-stage guidance."""
    with pytest.raises(RuntimeError, match="timezonefinder==9.0.0"):
        behavior.resolve_stay_timezones(_local_stays([("A", "2026-01-01T01:00:00Z", 0.0, 0.0, 1200)]))


def _daily_for_stability(rows: list[tuple[str, str, float]]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": [row[0] for row in rows],
            "local_date": pd.to_datetime([row[1] for row in rows]).date,
            "usable_for_temporal_profile": True,
            "dwell_h": [row[2] for row in rows],
            "hourly_dwell": [[row[2]] + [0.0] * 23 for row in rows],
        }
    )


def test_schedule_stability_requires_weeks_days_and_dwell_in_each_half() -> None:
    """Catches a schedule result emitted without support in both observation halves."""
    daily = _daily_for_stability(
        [("A", "2026-01-01", 2.0), ("A", "2026-01-08", 2.0), ("A", "2026-01-15", 2.0)]
    )

    stability = behavior.compute_schedule_stability(daily)

    assert stability.loc[0, "schedule_status"] == "insufficient"


def test_daily_motif_uses_deterministic_location_ids_only() -> None:
    """Catches motif exports that expose coordinates instead of deterministic L labels."""
    stays = pd.DataFrame(
        {
            "user_id": ["A", "A", "A"],
            "local_date": [pd.Timestamp("2026-01-01").date()] * 3,
            "arrival_time_local": pd.to_datetime(
                ["2026-01-01 08:00", "2026-01-01 12:00", "2026-01-01 18:00"]
            ),
            "location_id": [0, 1, 0],
            "duration_s": [1200.0, 1200.0, 1200.0],
            "latitude": [39.9, 39.91, 39.9],
        }
    )

    motifs = behavior.build_daily_motifs(stays)

    assert motifs.loc[0, "motif"] == "L0→L1→L0"
    assert "latitude" not in motifs.columns


def test_user_day_features_join_stay_dwell_to_cleaned_point_movement() -> None:
    """Catches user-day features built from stay displacement rather than cleaned metrics."""
    stays = pd.DataFrame(
        {
            "user_id": ["A"], "local_date": [pd.Timestamp("2026-01-01").date()],
            "location_id": [0], "duration_s": [7200.0], "arrival_time_local": [pd.Timestamp("2026-01-01 09:00")],
        }
    )
    point_days = pd.DataFrame(
        {
            "user_id": ["A"], "local_date": [pd.Timestamp("2026-01-01").date()],
            "cleaned_distance_km": [12.5], "movement_duration_proxy_h": [3.0],
        }
    )

    daily = behavior.build_user_day_features(stays, point_days)

    assert daily.loc[0, "cleaned_distance_km"] == 12.5
    assert daily.loc[0, "dwell_h"] == 2.0


def test_schedule_stability_returns_continuous_jsd_after_support_gates() -> None:
    """Catches eligible schedule profiles that omit the continuous early-late comparison."""
    daily = _daily_for_stability(
        [
            ("A", "2026-01-01", 2.0), ("A", "2026-01-02", 2.0), ("A", "2026-01-03", 2.0),
            ("A", "2026-01-08", 2.0), ("A", "2026-01-09", 2.0), ("A", "2026-01-10", 2.0),
        ]
    )

    stability = behavior.compute_schedule_stability(daily)

    assert stability.loc[0, "schedule_status"] == "eligible"
    assert stability.loc[0, "early_late_jsd"] == 0.0
    assert stability.loc[0, "weekly_jsd_median"] == 0.0


def test_behavior_features_report_temporal_and_motif_summaries() -> None:
    """Catches user summaries that lose dwell schedules or deterministic motif support."""
    stays = pd.DataFrame(
        {
            "user_id": ["A", "A", "A", "A"],
            "local_date": [pd.Timestamp("2026-01-01").date()] * 2
            + [pd.Timestamp("2026-01-02").date()] * 2,
            "location_id": [0, 1, 0, 1],
            "duration_s": [3600.0] * 4,
            "arrival_time_local": pd.to_datetime(
                ["2026-01-01 08:00", "2026-01-01 12:00", "2026-01-02 08:00", "2026-01-02 12:00"]
            ),
        }
    )
    point_days = pd.DataFrame(
        {
            "user_id": ["A", "A"],
            "local_date": [pd.Timestamp("2026-01-01").date(), pd.Timestamp("2026-01-02").date()],
            "point_count": [3, 3], "observed_span_h": [3.0, 3.0], "largest_gap_h": [1.0, 1.0],
            "cleaned_distance_km": [2.0, 2.0], "movement_duration_proxy_h": [2.0, 2.0],
        }
    )

    features = behavior.build_user_behavior_features(stays, point_days)

    assert features.loc[0, "most_frequent_motif"] == "L0→L1"
    assert features.loc[0, "motif_frequency"] == 1.0
    assert features.loc[0, "hour_entropy"] > 0.0


def test_materialize_rebuilds_an_invalid_checkpoint(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    zip_path = tmp_path / "geolife.zip"
    member = "Geolife Trajectories 1.3/Data/001/Trajectory/example.plt"
    plt = "\n".join(
        ["header"] * 6
        + [f"39.0,116.0,0,0,0,2008-01-01,00:{minute:02d}:00" for minute in range(0, 25, 5)]
    )
    with behavior.zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr(member, plt)

    cache_dir = Path("artifacts/03a/test_invalid_checkpoint")
    stay_cache = cache_dir / "stays.pkl"
    point_day_cache = cache_dir / "point_days.pkl"
    behavior._write_pickle_atomically(behavior._empty_stays(), stay_cache)
    behavior._write_pickle_atomically(behavior._empty_point_days(), point_day_cache)
    monkeypatch.setattr(behavior, "EXPECTED_STAYS", 1)
    monkeypatch.setattr(behavior, "EXPECTED_STAY_USERS", 1)
    monkeypatch.setattr(behavior, "EXPECTED_RELEASE_USERS", 1)

    try:
        stays, point_days = behavior.materialize_frozen_cp1(
            zip_path, stay_cache, point_day_cache
        )
    finally:
        for cache in (stay_cache, point_day_cache):
            cache.unlink(missing_ok=True)
        cache_dir.rmdir()

    assert len(stays) == 1
    assert len(point_days) == 1


def _frozen_audit_stays(user_id: str, timestamps: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": user_id,
            "arrival_time_utc": pd.to_datetime(timestamps, utc=True),
            "departure_time_utc": pd.to_datetime(timestamps, utc=True) + pd.Timedelta(hours=1),
            "duration_s": 3600.0,
            "latitude": 39.9042,
            "longitude": 116.4074,
        }
    )


def test_baseline_audit_keeps_user_without_stay_in_full_release_universe() -> None:
    audit = behavior.build_baseline_user_audit(
        {"000", "001"}, _frozen_audit_stays("001", ["2026-01-05T14:00:00Z"])
    )

    assert len(audit) == 4
    missing = audit.query("user_id == '000' and label == 'HOME'").iloc[0]
    assert missing["reject_reason"] == "no_cp1_stay"
    assert audit["reject_reason"].isin(behavior.REASON_ORDER).all()


def test_baseline_audit_prefers_no_overlap_before_insufficient_dates() -> None:
    audit = behavior.build_baseline_user_audit(
        {"001"},
        _frozen_audit_stays("001", ["2026-01-05T02:00:00Z", "2026-01-06T02:00:00Z"]),
    )

    home = audit.query("label == 'HOME'").iloc[0]
    assert home["reject_reason"] == "no_behavioral_window_overlap"


def test_baseline_audit_marks_relevant_overlap_with_too_few_dates() -> None:
    audit = behavior.build_baseline_user_audit(
        {"001"}, _frozen_audit_stays("001", ["2026-01-05T14:00:00Z", "2026-01-06T14:00:00Z"])
    )

    home = audit.query("label == 'HOME'").iloc[0]
    assert home["reject_reason"] == "insufficient_relevant_dates"


def test_location_sensitivity_covers_all_requested_thresholds() -> None:
    stays = _frozen_audit_stays(
        "001", ["2026-01-05T14:00:00Z", "2026-01-06T14:00:00Z"]
    )
    stays["arrival_time_local"] = stays["arrival_time_utc"].dt.tz_convert("Asia/Shanghai")
    stays["local_date"] = stays["arrival_time_local"].dt.date

    sensitivity = behavior.run_location_sensitivity(stays)

    assert sensitivity["threshold_m"].tolist() == [100.0, 200.0, 300.0]
    assert {
        "anchor_count_class",
        "top_anchor_stability_vs_200",
        "recurring_location_count",
        "motif_membership_stability_vs_200",
    }.issubset(sensitivity.columns)
    assert "regime_membership_stability_vs_200" not in sensitivity.columns
    assert len(sensitivity) == 3


def test_location_sensitivity_detects_changed_top_anchor_membership() -> None:
    stays = _frozen_audit_stays(
        "001",
        ["2026-01-05T14:00:00Z", "2026-01-06T14:00:00Z"],
    )
    stays.loc[1, "latitude"] += 0.00135
    stays["arrival_time_local"] = stays["arrival_time_utc"].dt.tz_convert("Asia/Shanghai")
    stays["local_date"] = stays["arrival_time_local"].dt.date

    sensitivity = behavior.run_location_sensitivity(stays)

    assert sensitivity.loc[
        sensitivity["threshold_m"] == 100.0, "top_anchor_stability_vs_200"
    ].iloc[0] < 1.0


def test_baseline_audit_ranks_only_locations_with_relevant_date_support() -> None:
    features = pd.DataFrame(
        {
            "location_id": [0, 1],
            "stay_count": [3, 2],
            "home_dwell_s": [3600.0, 14400.0],
            "home_dates": [3, 2],
            "home_dwell_share": [0.2, 0.8],
        }
    )

    candidate = behavior._top_audit_candidate(features, "HOME", behavior.HomeOfficeConfig())

    assert candidate["location_id"] == 0
    assert candidate["relevant_dates"] == 3
    assert candidate["share_margin"] == 0.2
    assert candidate["relevant_dwell_share"] == 0.2


def test_baseline_audit_keeps_raw_overlap_to_explain_insufficient_dates() -> None:
    stays = _frozen_audit_stays("001", ["2026-01-05T14:00:00Z", "2026-01-06T14:00:00Z"])

    audit = behavior.build_baseline_user_audit({"001"}, stays)

    home = audit.query("label == 'HOME'").iloc[0]
    assert home["reject_reason"] == "insufficient_relevant_dates"


def test_location_sensitivity_compares_daily_motif_content_not_just_users() -> None:
    stays = _frozen_audit_stays("001", ["2026-01-05T14:00:00Z", "2026-01-05T15:00:00Z"])
    stays.loc[1, "latitude"] += 0.00135
    stays["arrival_time_local"] = stays["arrival_time_utc"].dt.tz_convert("Asia/Shanghai")
    stays["local_date"] = stays["arrival_time_local"].dt.date

    sensitivity = behavior.run_location_sensitivity(stays)

    assert sensitivity.loc[
        sensitivity["threshold_m"] == 100.0, "motif_membership_stability_vs_200"
    ].iloc[0] == 0.0


def test_temporal_features_split_stay_dwell_across_local_hours_and_dates() -> None:
    stays = pd.DataFrame(
        {
            "user_id": ["A"],
            "local_date": [pd.Timestamp("2026-01-02").date()],
            "location_id": [0],
            "duration_s": [7200.0],
            "arrival_time_local": [pd.Timestamp("2026-01-02 23:00", tz="Asia/Shanghai")],
            "departure_time_local": [pd.Timestamp("2026-01-03 01:00", tz="Asia/Shanghai")],
        }
    )
    point_days = pd.DataFrame(
        {
            "user_id": ["A", "A"],
            "local_date": [pd.Timestamp("2026-01-02").date(), pd.Timestamp("2026-01-03").date()],
            "point_count": [3, 3],
            "observed_span_h": [3.0, 3.0],
            "largest_gap_h": [1.0, 1.0],
        }
    )

    daily = behavior.build_user_day_features(stays, point_days)

    friday = daily.loc[daily["local_date"] == pd.Timestamp("2026-01-02").date()].iloc[0]
    saturday = daily.loc[daily["local_date"] == pd.Timestamp("2026-01-03").date()].iloc[0]
    assert friday["dwell_h"] == 1.0
    assert friday["hourly_dwell"][23] == 3600.0
    assert saturday["dwell_h"] == 1.0
    assert saturday["hourly_dwell"][0] == 3600.0


def test_daily_stay_span_ends_at_last_departure() -> None:
    stays = pd.DataFrame(
        {
            "user_id": ["A", "A"],
            "local_date": [pd.Timestamp("2026-01-02").date()] * 2,
            "location_id": [0, 0],
            "duration_s": [3600.0, 7200.0],
            "arrival_time_local": pd.to_datetime(
                ["2026-01-02 08:00", "2026-01-02 18:00"], utc=True
            ),
            "departure_time_local": pd.to_datetime(
                ["2026-01-02 09:00", "2026-01-02 20:00"], utc=True
            ),
        }
    )
    point_days = pd.DataFrame(
        {
            "user_id": ["A"],
            "local_date": [pd.Timestamp("2026-01-02").date()],
            "point_count": [3],
            "observed_span_h": [3.0],
            "largest_gap_h": [1.0],
        }
    )

    daily = behavior.build_user_day_features(stays, point_days)

    assert daily.loc[0, "stay_observed_span_h"] == 12.0
