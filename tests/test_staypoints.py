from __future__ import annotations

import pandas as pd

from geolife.staypoints.detector import detect_staypoints


def _cleaned(rows: list[tuple[str, float, float, int]]) -> pd.DataFrame:
    return pd.DataFrame(
        rows,
        columns=["timestamp", "latitude", "longitude", "sequence_id"],
    ).assign(timestamp=lambda x: pd.to_datetime(x["timestamp"], utc=True))


def test_short_cluster_inside_threshold_is_not_a_stay() -> None:
    points = _cleaned(
        [
            ("2026-01-01T10:00:00Z", 39.0, 116.0, 0),
            ("2026-01-01T10:05:00Z", 39.0002, 116.0, 0),
            ("2026-01-01T10:10:00Z", 39.0003, 116.0, 0),
        ]
    )

    stays = detect_staypoints(points, distance_threshold_m=200, min_dwell_s=1200)

    assert stays.empty


def test_cluster_inside_threshold_for_long_enough_is_emitted() -> None:
    points = _cleaned(
        [
            ("2026-01-01T10:00:00Z", 39.0, 116.0, 0),
            ("2026-01-01T10:07:00Z", 39.0002, 116.0, 0),
            ("2026-01-01T10:14:00Z", 39.0004, 116.0, 0),
            ("2026-01-01T10:21:00Z", 39.0006, 116.0, 0),
        ]
    )

    stays = detect_staypoints(points, distance_threshold_m=200, min_dwell_s=1200)

    assert len(stays) == 1
    stay = stays.iloc[0]
    assert stay["sequence_id"] == 0
    assert stay["arrival_time"] == pd.Timestamp("2026-01-01T10:00:00Z")
    assert stay["departure_time"] == pd.Timestamp("2026-01-01T10:21:00Z")
    assert stay["duration_s"] == 1260
    assert stay["n_points"] == 4


def test_terminal_stay_is_not_lost() -> None:
    points = _cleaned(
        [
            ("2026-01-01T10:00:00Z", 39.0, 116.0, 0),
            ("2026-01-01T10:05:00Z", 39.0002, 116.0, 0),
            ("2026-01-01T10:10:00Z", 39.0003, 116.0, 0),
            ("2026-01-01T10:21:00Z", 39.0004, 116.0, 0),
        ]
    )

    stays = detect_staypoints(points, distance_threshold_m=200, min_dwell_s=1200)

    assert len(stays) == 1
    assert stays.iloc[0]["departure_time"] == pd.Timestamp("2026-01-01T10:21:00Z")


def test_no_stay_crosses_sequence_boundary() -> None:
    points = _cleaned(
        [
            ("2026-01-01T10:00:00Z", 39.0, 116.0, 0),
            ("2026-01-01T10:10:00Z", 39.0, 116.0, 0),
            ("2026-01-01T10:11:00Z", 39.0, 116.0, 1),
            ("2026-01-01T10:25:00Z", 39.0, 116.0, 1),
        ]
    )

    stays = detect_staypoints(points, distance_threshold_m=200, min_dwell_s=1200)

    assert stays.empty


def test_first_outside_radius_point_closes_candidate_and_later_return_does_not_merge() -> None:
    points = _cleaned(
        [
            ("2026-01-01T10:00:00Z", 39.0000, 116.0000, 0),
            ("2026-01-01T10:05:00Z", 39.0009, 116.0000, 0),
            ("2026-01-01T10:10:00Z", 39.0016, 116.0000, 0),
            ("2026-01-01T10:15:00Z", 39.0020, 116.0000, 0),
            ("2026-01-01T10:21:00Z", 39.0004, 116.0000, 0),
        ]
    )

    stays = detect_staypoints(points, distance_threshold_m=200, min_dwell_s=1200)

    assert stays.empty
