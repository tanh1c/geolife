"""Exploratory helpers for the GeoLife EDA notebook.

This module deliberately lives under notebooks/ rather than src/geolife/ because the
production data loader has not been designed/tested yet. Promote only reviewed logic.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

PLT_COLUMNS = [
    "latitude",
    "longitude",
    "unused",
    "altitude_ft",
    "serial_date",
    "date",
    "time",
]
EARTH_RADIUS_M = 6_371_000.0


def read_plt(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, skiprows=6, header=None, names=PLT_COLUMNS)
    df["timestamp"] = pd.to_datetime(
        df["date"].astype(str) + " " + df["time"].astype(str),
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
        utc=True,
    )
    df["altitude_ft"] = pd.to_numeric(df["altitude_ft"], errors="coerce")
    df.loc[df["altitude_ft"] == -777, "altitude_ft"] = np.nan
    return df


def haversine_vectorized(lat1, lon1, lat2, lon2):
    lat1 = np.radians(np.asarray(lat1, dtype=float))
    lon1 = np.radians(np.asarray(lon1, dtype=float))
    lat2 = np.radians(np.asarray(lat2, dtype=float))
    lon2 = np.radians(np.asarray(lon2, dtype=float))
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return EARTH_RADIUS_M * c


def inventory_dataset(data_root: Path) -> tuple[pd.DataFrame, list[tuple[str, Path]]]:
    users = sorted(p for p in data_root.iterdir() if p.is_dir() and p.name.isdigit())
    inventory_rows = []
    files: list[tuple[str, Path]] = []
    for user_dir in users:
        plt_files = sorted((user_dir / "Trajectory").glob("*.plt"))
        inventory_rows.append(
            {
                "user_id": user_dir.name,
                "trajectory_count": len(plt_files),
                "has_labels": (user_dir / "labels.txt").exists(),
            }
        )
        files.extend((user_dir.name, path) for path in plt_files)
    return pd.DataFrame(inventory_rows), files


def summarize_trajectory(user_id: str, path: Path) -> dict:
    df = read_plt(path)
    n = len(df)
    result = {
        "user_id": user_id,
        "trajectory_id": path.stem,
        "n_points": n,
        "start_time": df["timestamp"].min(),
        "end_time": df["timestamp"].max(),
        "duration_min": np.nan,
        "distance_km": np.nan,
        "median_sampling_s": np.nan,
        "p95_sampling_s": np.nan,
        "max_speed_kmh": np.nan,
        "p99_speed_kmh": np.nan,
        "missing_altitude_rate": float(df["altitude_ft"].isna().mean()) if n else np.nan,
        "min_lat": df["latitude"].min() if n else np.nan,
        "max_lat": df["latitude"].max() if n else np.nan,
        "min_lon": df["longitude"].min() if n else np.nan,
        "max_lon": df["longitude"].max() if n else np.nan,
        "invalid_lat": int((~df["latitude"].between(-90, 90)).sum()) if n else 0,
        "invalid_lon": int((~df["longitude"].between(-180, 180)).sum()) if n else 0,
        "null_timestamp": int(df["timestamp"].isna().sum()) if n else 0,
        "duplicate_timestamp": int(df["timestamp"].duplicated().sum()) if n else 0,
        "non_monotonic_timestamp": int(not df["timestamp"].dropna().is_monotonic_increasing) if n else 0,
    }
    if n < 2:
        return result

    dt = df["timestamp"].diff().dt.total_seconds().to_numpy()[1:]
    distances_m = haversine_vectorized(
        df["latitude"].to_numpy()[:-1],
        df["longitude"].to_numpy()[:-1],
        df["latitude"].to_numpy()[1:],
        df["longitude"].to_numpy()[1:],
    )
    valid_dt = np.isfinite(dt) & (dt > 0)
    speed_kmh = np.full_like(distances_m, np.nan, dtype=float)
    speed_kmh[valid_dt] = distances_m[valid_dt] / dt[valid_dt] * 3.6

    result["duration_min"] = (
        df["timestamp"].max() - df["timestamp"].min()
    ).total_seconds() / 60.0
    result["distance_km"] = np.nansum(distances_m) / 1000.0

    positive_dt = dt[valid_dt]
    if positive_dt.size:
        result["median_sampling_s"] = float(np.nanmedian(positive_dt))
        result["p95_sampling_s"] = float(np.nanpercentile(positive_dt, 95))
    finite_speed = speed_kmh[np.isfinite(speed_kmh)]
    if finite_speed.size:
        result["max_speed_kmh"] = float(np.nanmax(finite_speed))
        result["p99_speed_kmh"] = float(np.nanpercentile(finite_speed, 99))
    return result


def summarize_all(files: list[tuple[str, Path]], progress_every: int = 1000) -> pd.DataFrame:
    rows = []
    for idx, (user_id, path) in enumerate(files, start=1):
        rows.append(summarize_trajectory(user_id, path))
        if progress_every and idx % progress_every == 0:
            print(f"processed {idx:,}/{len(files):,} trajectories")
    result = pd.DataFrame(rows)
    if not result.empty:
        result["start_time"] = pd.to_datetime(result["start_time"], utc=True)
        result["end_time"] = pd.to_datetime(result["end_time"], utc=True)
    return result


def read_labels(path: Path, user_id: str) -> pd.DataFrame:
    df = pd.read_csv(path, sep=r"\s+", skiprows=1, header=None)
    if df.empty:
        return pd.DataFrame(columns=["start_time", "end_time", "mode", "user_id"])
    df.columns = ["start_date", "start_clock", "end_date", "end_clock", "mode"]
    df["start_time"] = pd.to_datetime(
        df["start_date"] + " " + df["start_clock"],
        format="%Y/%m/%d %H:%M:%S",
        errors="coerce",
        utc=True,
    )
    df["end_time"] = pd.to_datetime(
        df["end_date"] + " " + df["end_clock"],
        format="%Y/%m/%d %H:%M:%S",
        errors="coerce",
        utc=True,
    )
    df["user_id"] = user_id
    return df[["start_time", "end_time", "mode", "user_id"]]
