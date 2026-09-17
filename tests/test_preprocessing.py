from __future__ import annotations

import warnings

import pandas as pd

from geolife.staypoints.cleaning import (
    clean_trajectory,
    clean_trajectory_with_audit,
)


def _df(rows: list[tuple[str, float, float]]) -> pd.DataFrame:
    return pd.DataFrame(rows, columns=["timestamp", "latitude", "longitude"]).assign(
        timestamp=lambda x: pd.to_datetime(x["timestamp"], utc=True)
    )


def _assert_boundary_reasons(actual: pd.Series, expected: list[str | None]) -> None:
    values = actual.tolist()
    assert len(values) == len(expected)
    for value, expected_value in zip(values, expected, strict=True):
        if expected_value is None:
            assert pd.isna(value)
        else:
            assert value == expected_value


def test_invalid_coordinate_creates_boundary_and_is_not_bridged() -> None:
    raw = _df(
        [
            ("2026-01-01T10:00:00Z", 39.0, 116.0),
            ("2026-01-01T10:01:00Z", 39.0, 116.0),
            ("2026-01-01T10:02:00Z", 200.0, 116.0),
            ("2026-01-01T10:03:00Z", 39.0, 116.0),
            ("2026-01-01T10:04:00Z", 39.0, 116.0),
        ]
    )

    out = clean_trajectory(raw)

    assert len(out) == 4
    assert out["sequence_id"].tolist() == [0, 0, 1, 1]
    _assert_boundary_reasons(
        out["boundary_before_reason"],
        [None, None, "invalid_coordinate", None],
    )


def test_compact_same_second_observations_collapse_to_median_representative() -> None:
    raw = _df(
        [
            ("2026-01-01T10:00:00Z", 39.000000, 116.000000),
            ("2026-01-01T10:00:00Z", 39.000020, 116.000010),
            ("2026-01-01T10:00:00Z", 39.000010, 116.000020),
        ]
    )

    out = clean_trajectory(raw)

    assert len(out) == 1
    row = out.iloc[0]
    assert row["latitude"] == 39.000010
    assert row["longitude"] == 116.000010
    assert row["raw_point_count"] == 3
    assert row["max_radius_m"] <= 10.0
    assert row["sequence_id"] == 0


def test_same_second_spatial_conflict_creates_boundary() -> None:
    raw = _df(
        [
            ("2026-01-01T09:59:00Z", 39.0, 116.0),
            ("2026-01-01T10:00:00Z", 39.0, 116.0),
            ("2026-01-01T10:00:00Z", 39.02, 116.0),
            ("2026-01-01T10:01:00Z", 39.0, 116.0),
        ]
    )

    out = clean_trajectory(raw)

    assert len(out) == 2
    assert out["sequence_id"].tolist() == [0, 1]
    _assert_boundary_reasons(
        out["boundary_before_reason"],
        [None, "same_second_spatial_conflict"],
    )


def test_terminal_spatial_conflict_remains_observable_in_audit_events() -> None:
    raw = _df(
        [
            ("2026-01-01T09:59:00Z", 39.0, 116.0),
            ("2026-01-01T10:00:00Z", 39.0, 116.0),
            ("2026-01-01T10:00:00Z", 39.02, 116.0),
        ]
    )

    cleaned, audit = clean_trajectory_with_audit(raw)

    assert len(cleaned) == 1
    conflicts = audit.loc[audit["reason"] == "same_second_spatial_conflict"]
    assert len(conflicts) == 1
    assert conflicts.iloc[0]["timestamp"] == pd.Timestamp("2026-01-01T10:00:00Z")


def test_temporal_gap_above_max_gap_creates_boundary() -> None:
    raw = _df(
        [
            ("2026-01-01T10:00:00Z", 39.0, 116.0),
            ("2026-01-01T10:01:00Z", 39.0, 116.0),
            ("2026-01-01T10:20:00Z", 39.0, 116.0),
            ("2026-01-01T10:21:00Z", 39.0, 116.0),
        ]
    )

    out = clean_trajectory(raw, max_gap_s=300)

    assert out["sequence_id"].tolist() == [0, 0, 1, 1]
    _assert_boundary_reasons(
        out["boundary_before_reason"],
        [None, None, "temporal_gap", None],
    )


def test_hard_speed_guard_splits_without_deleting_either_endpoint() -> None:
    raw = _df(
        [
            ("2026-01-01T10:00:00Z", 39.0000, 116.0000),
            ("2026-01-01T10:01:00Z", 39.0008, 116.0000),
            ("2026-01-01T10:02:00Z", 40.0000, 116.0000),
            ("2026-01-01T10:03:00Z", 40.0008, 116.0000),
        ]
    )

    out = clean_trajectory(raw, max_gap_s=300, hard_speed_guard_kmh=1200)

    assert len(out) == 4
    assert out["sequence_id"].tolist() == [0, 0, 1, 1]
    _assert_boundary_reasons(
        out["boundary_before_reason"],
        [None, None, "hard_speed_guard", None],
    )


def test_audit_append_does_not_emit_pandas_futurewarning() -> None:
    raw = _df(
        [
            ("2026-01-01T10:00:00Z", 39.0, 116.0),
            ("2026-01-01T10:20:00Z", 39.0, 116.0),
            ("2026-01-01T10:21:00Z", 40.0, 116.0),
        ]
    )

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _, audit = clean_trajectory_with_audit(
            raw,
            max_gap_s=300,
            hard_speed_guard_kmh=1200,
        )

    assert set(audit["reason"]) == {"temporal_gap", "hard_speed_guard"}
    future_warnings = [w for w in caught if issubclass(w.category, FutureWarning)]
    assert future_warnings == []
