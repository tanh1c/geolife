from __future__ import annotations

import numpy as np
import pandas as pd

from geolife.geo.distance import haversine_m


OUTPUT_COLUMNS = [
    "sequence_id",
    "arrival_time",
    "departure_time",
    "duration_s",
    "latitude",
    "longitude",
    "n_points",
]


def _empty_stays() -> pd.DataFrame:
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def detect_staypoints(
    observations: pd.DataFrame,
    *,
    distance_threshold_m: float = 200.0,
    min_dwell_s: float = 1200.0,
) -> pd.DataFrame:
    """Detect anchor-based stay points independently within each sequence."""
    required = {"timestamp", "latitude", "longitude", "sequence_id"}
    missing = required.difference(observations.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")
    if distance_threshold_m < 0:
        raise ValueError("distance_threshold_m must be non-negative")
    if min_dwell_s < 0:
        raise ValueError("min_dwell_s must be non-negative")
    if observations.empty:
        return _empty_stays()

    points = observations.loc[:, ["timestamp", "latitude", "longitude", "sequence_id"]].copy()
    points["timestamp"] = pd.to_datetime(points["timestamp"], utc=True)
    points = points.sort_values(["sequence_id", "timestamp"], kind="stable").reset_index(drop=True)

    stays: list[dict[str, object]] = []

    for sequence_id, sequence in points.groupby("sequence_id", sort=False):
        sequence = sequence.reset_index(drop=True)
        n = len(sequence)
        i = 0

        while i < n:
            anchor = sequence.iloc[i]
            j = i + 1

            while j < n:
                point = sequence.iloc[j]
                distance_m = haversine_m(
                    float(anchor["latitude"]),
                    float(anchor["longitude"]),
                    float(point["latitude"]),
                    float(point["longitude"]),
                )
                if distance_m > distance_threshold_m:
                    break
                j += 1

            candidate_end = j - 1
            if candidate_end > i:
                arrival = sequence.iloc[i]["timestamp"]
                departure = sequence.iloc[candidate_end]["timestamp"]
                duration_s = float((departure - arrival).total_seconds())

                if duration_s >= min_dwell_s:
                    candidate = sequence.iloc[i : candidate_end + 1]
                    stays.append(
                        {
                            "sequence_id": sequence_id,
                            "arrival_time": arrival,
                            "departure_time": departure,
                            "duration_s": duration_s,
                            "latitude": float(np.median(candidate["latitude"].to_numpy(dtype=float))),
                            "longitude": float(np.median(candidate["longitude"].to_numpy(dtype=float))),
                            "n_points": int(len(candidate)),
                        }
                    )
                    # The first outside-radius point starts the next candidate.
                    i = j
                    continue

            # No emitted stay: move the anchor one observation and try again.
            i += 1

    if not stays:
        return _empty_stays()
    return pd.DataFrame(stays, columns=OUTPUT_COLUMNS)
