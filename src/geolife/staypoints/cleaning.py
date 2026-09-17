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


def _is_valid_coordinate(lat: float, lon: float) -> bool:
    return bool(np.isfinite(lat) and np.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180)


def clean_trajectory(
    df: pd.DataFrame,
    *,
    same_second_radius_m: float = 10.0,
    max_gap_s: float = 300.0,
    hard_speed_guard_kmh: float = 1200.0,
) -> pd.DataFrame:
    """Clean one ordered trajectory into independent timestamp-level sequences.

    The transform follows the approved CP1 contract: invalid coordinates and
    incompatible same-second groups are removed while creating a continuity
    boundary; temporal gaps and extreme speed segments split continuity without
    deleting their valid endpoints.
    """
    if same_second_radius_m < 0:
        raise ValueError("same_second_radius_m must be non-negative")
    if max_gap_s <= 0:
        raise ValueError("max_gap_s must be positive")
    if hard_speed_guard_kmh <= 0:
        raise ValueError("hard_speed_guard_kmh must be positive")

    raw = _validate_input(df)
    if raw.empty:
        return pd.DataFrame(
            columns=[
                "timestamp",
                "latitude",
                "longitude",
                "raw_point_count",
                "max_radius_m",
                "sequence_id",
                "boundary_before_reason",
            ]
        )

    events: list[dict[str, object]] = []

    for timestamp, group in raw.groupby("timestamp", sort=True):
        valid_mask = [
            _is_valid_coordinate(float(lat), float(lon))
            for lat, lon in zip(group["latitude"], group["longitude"], strict=True)
        ]
        valid = group.loc[valid_mask]
        invalid_count = len(group) - len(valid)

        if valid.empty:
            events.append({"kind": "boundary", "reason": "invalid_coordinate"})
            continue

        lat = float(valid["latitude"].median())
        lon = float(valid["longitude"].median())
        radii = haversine_m(
            valid["latitude"].to_numpy(dtype=float),
            valid["longitude"].to_numpy(dtype=float),
            lat,
            lon,
        )
        max_radius_m = float(np.max(radii)) if len(valid) else 0.0

        if max_radius_m > same_second_radius_m:
            events.append({"kind": "boundary", "reason": "same_second_spatial_conflict"})
            continue

        if invalid_count:
            events.append({"kind": "boundary", "reason": "invalid_coordinate"})

        events.append(
            {
                "kind": "point",
                "timestamp": timestamp,
                "latitude": lat,
                "longitude": lon,
                "raw_point_count": int(len(valid)),
                "max_radius_m": max_radius_m,
            }
        )

    rows: list[dict[str, object]] = []
    sequence_id = 0
    pending_reason: BoundaryReason | None = None
    previous: dict[str, object] | None = None

    for event in events:
        if event["kind"] == "boundary":
            reason = event["reason"]
            if rows and pending_reason is None:
                sequence_id += 1
            pending_reason = reason  # type: ignore[assignment]
            previous = None
            continue

        point = event.copy()
        reason: BoundaryReason | None = pending_reason
        pending_reason = None

        if previous is not None:
            dt_s = (point["timestamp"] - previous["timestamp"]).total_seconds()  # type: ignore[operator]
            if dt_s > max_gap_s:
                sequence_id += 1
                reason = "temporal_gap"
                previous = None
            elif dt_s > 0:
                distance_m = haversine_m(
                    float(previous["latitude"]),
                    float(previous["longitude"]),
                    float(point["latitude"]),
                    float(point["longitude"]),
                )
                speed_kmh = distance_m / dt_s * 3.6
                if speed_kmh > hard_speed_guard_kmh:
                    sequence_id += 1
                    reason = "hard_speed_guard"
                    previous = None

        point["sequence_id"] = sequence_id
        point["boundary_before_reason"] = reason
        point.pop("kind", None)
        rows.append(point)
        previous = point

    columns = [
        "timestamp",
        "latitude",
        "longitude",
        "raw_point_count",
        "max_radius_m",
        "sequence_id",
        "boundary_before_reason",
    ]
    result = pd.DataFrame(rows, columns=columns)

    # Pandas 3 may coerce missing values in a mixed string/None column to NaN.
    # The contract intentionally uses Python None for "no boundary before this row",
    # so restore the diagnostic field as an explicit object array.
    result["boundary_before_reason"] = np.array(
        [row["boundary_before_reason"] for row in rows],
        dtype=object,
    )
    return result
