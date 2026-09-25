from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

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
