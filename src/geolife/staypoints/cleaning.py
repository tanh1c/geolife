from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import pandas as pd

from geolife.geo.distance import haversine_m

BoundaryReason = Literal[
    "invalid_coordinate",
    "same_second_spatial_conflict",
    "temporal_gap",
    "hard_speed_guard",
]

OUTPUT_COLUMNS = [
    "timestamp",
    "latitude",
    "longitude",
    "raw_point_count",
    "max_radius_m",
    "sequence_id",
    "boundary_before_reason",
]


@dataclass(frozen=True)
class CleaningConfig:
    same_second_radius_m: float = 10.0
    max_gap_s: float = 300.0
    hard_speed_guard_kmh: float = 1200.0


def _validate_input(df: pd.DataFrame) -> pd.DataFrame:
    required = {"timestamp", "latitude", "longitude"}
    missing = required.difference(df.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    out = df.loc[:, ["timestamp", "latitude", "longitude"]].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True)
    if out["timestamp"].isna().any():
        raise ValueError("timestamp contains unparsable values")
    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")
    return out.sort_values("timestamp", kind="stable").reset_index(drop=True)


def _empty_cleaned() -> pd.DataFrame:
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def clean_trajectory(
    df: pd.DataFrame,
    *,
    same_second_radius_m: float = 10.0,
    max_gap_s: float = 300.0,
    hard_speed_guard_kmh: float = 1200.0,
) -> pd.DataFrame:
    """Clean one ordered trajectory into independent timestamp-level sequences.

    Semantics follow the approved CP1 contract. Same-second consolidation and
    pairwise boundary checks are vectorized so full-release validation does not
    execute a Python loop for every raw timestamp.
    """
    if same_second_radius_m < 0:
        raise ValueError("same_second_radius_m must be non-negative")
    if max_gap_s <= 0:
        raise ValueError("max_gap_s must be positive")
    if hard_speed_guard_kmh <= 0:
        raise ValueError("hard_speed_guard_kmh must be positive")

    raw = _validate_input(df)
    if raw.empty:
        return _empty_cleaned()

    lat = raw["latitude"].to_numpy(dtype=float)
    lon = raw["longitude"].to_numpy(dtype=float)
    valid_coordinate = (
        np.isfinite(lat)
        & np.isfinite(lon)
        & (lat >= -90.0)
        & (lat <= 90.0)
        & (lon >= -180.0)
        & (lon <= 180.0)
    )

    all_counts = raw.groupby("timestamp", sort=True).size()
    valid = raw.loc[valid_coordinate, ["timestamp", "latitude", "longitude"]]

    summary = pd.DataFrame(index=all_counts.index)
    summary["all_count"] = all_counts.astype(np.int64)

    if valid.empty:
        return _empty_cleaned()

    grouped = valid.groupby("timestamp", sort=True)
    valid_counts = grouped.size()
    centers = grouped[["latitude", "longitude"]].median()

    center_lat = valid["timestamp"].map(centers["latitude"]).to_numpy(dtype=float)
    center_lon = valid["timestamp"].map(centers["longitude"]).to_numpy(dtype=float)
    radii_m = np.asarray(
        haversine_m(
            valid["latitude"].to_numpy(dtype=float),
            valid["longitude"].to_numpy(dtype=float),
            center_lat,
            center_lon,
        ),
        dtype=float,
    )
    max_radii = pd.Series(radii_m, index=valid.index).groupby(valid["timestamp"], sort=True).max()

    summary["valid_count"] = valid_counts.reindex(summary.index, fill_value=0).astype(np.int64)
    summary["latitude"] = centers["latitude"].reindex(summary.index)
    summary["longitude"] = centers["longitude"].reindex(summary.index)
    summary["max_radius_m"] = max_radii.reindex(summary.index)

    all_count_arr = summary["all_count"].to_numpy(dtype=np.int64)
    valid_count_arr = summary["valid_count"].to_numpy(dtype=np.int64)
    max_radius_arr = summary["max_radius_m"].to_numpy(dtype=float)

    invalid_present = all_count_arr > valid_count_arr
    spatial_conflict = (valid_count_arr > 0) & (max_radius_arr > same_second_radius_m)
    retained = (valid_count_arr > 0) & ~spatial_conflict

    # One diagnostic reason per timestamp. Spatial conflict wins over an invalid
    # row at the same timestamp, matching the original event-order semantics.
    reason_at_timestamp = np.full(len(summary), None, dtype=object)
    reason_at_timestamp[invalid_present] = "invalid_coordinate"
    reason_at_timestamp[spatial_conflict] = "same_second_spatial_conflict"

    retained_positions = np.flatnonzero(retained)
    if retained_positions.size == 0:
        return _empty_cleaned()

    # Carry the most recent explicit invalid/conflict boundary since the
    # previous retained observation onto the next retained row.
    explicit_reason = np.full(retained_positions.size, None, dtype=object)
    boundary_positions = np.flatnonzero(
        np.fromiter((reason is not None for reason in reason_at_timestamp), dtype=bool)
    )
    if boundary_positions.size:
        lookup = np.searchsorted(boundary_positions, retained_positions, side="right") - 1
        has_boundary = lookup >= 0
        latest_boundary_position = np.full(retained_positions.size, -1, dtype=np.int64)
        latest_boundary_position[has_boundary] = boundary_positions[lookup[has_boundary]]
        previous_retained_position = np.concatenate(
            (np.array([-1], dtype=np.int64), retained_positions[:-1])
        )
        carries_boundary = has_boundary & (latest_boundary_position > previous_retained_position)
        explicit_reason[carries_boundary] = reason_at_timestamp[
            latest_boundary_position[carries_boundary]
        ]

    timestamp_index = pd.DatetimeIndex(summary.index[retained_positions]).astype(
        "datetime64[ns, UTC]"
    )
    timestamp_ns = timestamp_index.asi8.astype(np.int64, copy=False)
    retained_lat = summary["latitude"].to_numpy(dtype=float)[retained_positions]
    retained_lon = summary["longitude"].to_numpy(dtype=float)[retained_positions]
    retained_count = valid_count_arr[retained_positions]
    retained_radius = max_radius_arr[retained_positions]

    final_reason = explicit_reason.copy()
    n_retained = retained_positions.size

    if n_retained > 1:
        dt_s = np.diff(timestamp_ns).astype(float) / 1_000_000_000.0
        no_explicit_boundary = np.fromiter(
            (reason is None for reason in final_reason[1:]), dtype=bool
        )

        temporal_gap = no_explicit_boundary & (dt_s > max_gap_s)
        if np.any(temporal_gap):
            final_reason[np.flatnonzero(temporal_gap) + 1] = "temporal_gap"

        distances_m = np.asarray(
            haversine_m(
                retained_lat[:-1],
                retained_lon[:-1],
                retained_lat[1:],
                retained_lon[1:],
            ),
            dtype=float,
        )
        positive_dt = dt_s > 0
        speed_kmh = np.full(dt_s.shape, np.nan, dtype=float)
        speed_kmh[positive_dt] = distances_m[positive_dt] / dt_s[positive_dt] * 3.6

        hard_speed = (
            no_explicit_boundary
            & ~temporal_gap
            & positive_dt
            & (speed_kmh > hard_speed_guard_kmh)
        )
        if np.any(hard_speed):
            final_reason[np.flatnonzero(hard_speed) + 1] = "hard_speed_guard"

    boundary_mask = np.fromiter((reason is not None for reason in final_reason), dtype=bool)
    increments = np.zeros(n_retained, dtype=np.int64)
    if n_retained > 1:
        increments[1:] = boundary_mask[1:].astype(np.int64)
    sequence_id = np.cumsum(increments)

    result = pd.DataFrame(
        {
            "timestamp": timestamp_index,
            "latitude": retained_lat,
            "longitude": retained_lon,
            "raw_point_count": retained_count,
            "max_radius_m": retained_radius,
            "sequence_id": sequence_id,
        }
    )
    result["boundary_before_reason"] = final_reason
    return result.loc[:, OUTPUT_COLUMNS]
