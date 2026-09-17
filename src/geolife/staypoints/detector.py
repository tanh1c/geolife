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
    """Detect anchor-based stay points independently within each sequence.

    Semantics match the approved CP1 contract. The implementation vectorizes
    each anchor-to-suffix distance scan so NumPy performs the Haversine work in
    bulk instead of a Python inner loop. It also stops once the remaining time
    in a sequence is shorter than ``min_dwell_s`` because no later anchor can
    possibly emit a stay.
    """
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
        if n < 2:
            continue

        timestamps = sequence["timestamp"].tolist()
        timestamp_ns = sequence["timestamp"].astype("int64").to_numpy(dtype=np.int64)
        latitudes = sequence["latitude"].to_numpy(dtype=float)
        longitudes = sequence["longitude"].to_numpy(dtype=float)

        i = 0
        while i < n - 1:
            # If even the final observation is too close in time, neither this
            # anchor nor any later one can satisfy the dwell threshold.
            remaining_s = float(timestamp_ns[-1] - timestamp_ns[i]) / 1_000_000_000.0
            if remaining_s < min_dwell_s:
                break

            distances_m = np.asarray(
                haversine_m(
                    latitudes[i],
                    longitudes[i],
                    latitudes[i + 1 :],
                    longitudes[i + 1 :],
                ),
                dtype=float,
            )
            outside = np.flatnonzero(distances_m > distance_threshold_m)

            if outside.size:
                # +1 because distances_m[0] corresponds to sequence[i + 1].
                j = i + 1 + int(outside[0])
            else:
                j = n

            candidate_end = j - 1
            if candidate_end > i:
                duration_s = float(timestamp_ns[candidate_end] - timestamp_ns[i]) / 1_000_000_000.0

                if duration_s >= min_dwell_s:
                    candidate_slice = slice(i, candidate_end + 1)
                    stays.append(
                        {
                            "sequence_id": sequence_id,
                            "arrival_time": timestamps[i],
                            "departure_time": timestamps[candidate_end],
                            "duration_s": duration_s,
                            "latitude": float(np.median(latitudes[candidate_slice])),
                            "longitude": float(np.median(longitudes[candidate_slice])),
                            "n_points": int(candidate_end - i + 1),
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
