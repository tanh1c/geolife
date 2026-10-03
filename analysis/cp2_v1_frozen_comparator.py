"""Frozen CP2 v1 semantic-cohort helper for historical comparator audits.

This module exists only so exploratory reports that explicitly compare against
the September-2026 CP2-v1 Beijing-focused baseline do not silently change when
production moves to CP2 v2.

It is not production inference.
"""

from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering

from geolife.geo.distance import haversine_m


REQUIRED_STAY_COLUMNS = {
    "user_id",
    "arrival_time_utc",
    "departure_time_utc",
    "duration_s",
    "latitude",
    "longitude",
}


@dataclass(frozen=True)
class FrozenV1HomeOfficeConfig:
    beijing_latitude: float = 39.9042
    beijing_longitude: float = 116.4074
    beijing_radius_km: float = 100.0
    beijing_min_stay_share: float = 0.80
    beijing_min_dwell_share: float = 0.80
    timezone: str = "Asia/Shanghai"

    location_max_diameter_m: float = 200.0
    min_relevant_date_overlap_s: float = 600.0

    home_start_hour: int = 21
    home_end_hour: int = 6
    office_start_hour: int = 9
    office_end_hour: int = 17
    office_weekdays: tuple[int, ...] = (0, 1, 2, 3, 4)

    home_min_dates: int = 3
    home_min_share: float = 0.50
    home_min_margin: float = 0.20

    office_min_dates: int = 3
    office_min_share: float = 0.30
    office_min_margin: float = 0.10

    support_saturation_dates: int = 5


def _validate_stays(stays: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_STAY_COLUMNS.difference(stays.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    out = stays.loc[:, sorted(REQUIRED_STAY_COLUMNS)].copy()
    out["user_id"] = out["user_id"].astype(str)
    out["arrival_time_utc"] = pd.to_datetime(out["arrival_time_utc"], utc=True)
    out["departure_time_utc"] = pd.to_datetime(
        out["departure_time_utc"], utc=True
    )
    out["duration_s"] = pd.to_numeric(out["duration_s"], errors="coerce")
    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")
    if out.isna().any().any():
        raise ValueError("stay table contains missing/unparsable required values")
    return out.sort_values(
        ["user_id", "arrival_time_utc", "departure_time_utc"],
        kind="stable",
    ).reset_index(drop=True)


def _pairwise(group: pd.DataFrame) -> np.ndarray:
    lat = group["latitude"].to_numpy(float)
    lon = group["longitude"].to_numpy(float)
    return np.asarray(
        haversine_m(
            lat[:, None],
            lon[:, None],
            lat[None, :],
            lon[None, :],
        ),
        dtype=float,
    )


def _cluster_user(
    group: pd.DataFrame,
    threshold_m: float,
) -> tuple[pd.DataFrame, np.ndarray]:
    ordered = group.sort_values("arrival_time_local", kind="stable").copy()
    if len(ordered) == 1:
        ordered["location_id"] = 0
        return ordered, np.zeros((1, 1), dtype=float)

    distances = _pairwise(ordered)
    raw_labels = AgglomerativeClustering(
        n_clusters=None,
        metric="precomputed",
        linkage="complete",
        distance_threshold=threshold_m,
    ).fit_predict(distances)
    ordered["_raw_location_id"] = raw_labels.astype(int)
    first_seen = (
        ordered.groupby("_raw_location_id", sort=False)["arrival_time_local"]
        .min()
        .sort_values(kind="stable")
    )
    label_map = {raw: idx for idx, raw in enumerate(first_seen.index)}
    ordered["location_id"] = (
        ordered["_raw_location_id"].map(label_map).astype(int)
    )
    return ordered.drop(columns="_raw_location_id"), distances


def build_frozen_v1_semantic_locations(
    stays: pd.DataFrame,
    *,
    config: FrozenV1HomeOfficeConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = config or FrozenV1HomeOfficeConfig()
    raw = _validate_stays(stays)
    if raw.empty:
        return raw.assign(location_id=pd.Series(dtype=int)), pd.DataFrame()

    raw["distance_to_beijing_km"] = (
        np.asarray(
            haversine_m(
                raw["latitude"].to_numpy(float),
                raw["longitude"].to_numpy(float),
                cfg.beijing_latitude,
                cfg.beijing_longitude,
            ),
            dtype=float,
        )
        / 1000.0
    )
    raw["_inside_region"] = (
        raw["distance_to_beijing_km"] <= cfg.beijing_radius_km
    )
    raw["_inside_dwell_s"] = np.where(
        raw["_inside_region"],
        raw["duration_s"],
        0.0,
    )

    by_user = raw.groupby("user_id").agg(
        total_stays=("user_id", "size"),
        inside_stays=("_inside_region", "sum"),
        total_dwell_s=("duration_s", "sum"),
        inside_dwell_s=("_inside_dwell_s", "sum"),
    )
    by_user["stay_share_inside"] = (
        by_user["inside_stays"] / by_user["total_stays"]
    )
    by_user["dwell_share_inside"] = np.where(
        by_user["total_dwell_s"] > 0,
        by_user["inside_dwell_s"] / by_user["total_dwell_s"],
        0.0,
    )
    eligible = by_user.index[
        (by_user["stay_share_inside"] >= cfg.beijing_min_stay_share)
        & (
            by_user["dwell_share_inside"]
            >= cfg.beijing_min_dwell_share
        )
    ]

    semantic = raw.loc[
        raw["user_id"].isin(eligible) & raw["_inside_region"]
    ].copy()
    if semantic.empty:
        return semantic.assign(location_id=pd.Series(dtype=int)), pd.DataFrame()

    timezone = ZoneInfo(cfg.timezone)
    semantic["arrival_time_local"] = semantic[
        "arrival_time_utc"
    ].dt.tz_convert(timezone)
    semantic["departure_time_local"] = semantic[
        "departure_time_utc"
    ].dt.tz_convert(timezone)
    semantic["arrival_local_date"] = semantic[
        "arrival_time_local"
    ].dt.date

    clustered_parts: list[pd.DataFrame] = []
    location_rows: list[dict[str, object]] = []
    for user_id, group in semantic.groupby("user_id", sort=True):
        clustered, distances = _cluster_user(
            group,
            cfg.location_max_diameter_m,
        )
        clustered_parts.append(clustered)
        labels = clustered["location_id"].to_numpy(int)
        for location_id in np.unique(labels):
            member_idx = np.flatnonzero(labels == location_id)
            members = clustered.iloc[member_idx]
            diameter_m = (
                float(distances[np.ix_(member_idx, member_idx)].max())
                if len(member_idx) > 1
                else 0.0
            )
            location_rows.append(
                {
                    "user_id": user_id,
                    "location_id": int(location_id),
                    "latitude": float(members["latitude"].median()),
                    "longitude": float(members["longitude"].median()),
                    "stay_count": int(len(members)),
                    "active_local_dates": int(
                        members["arrival_time_local"].dt.date.nunique()
                    ),
                    "total_dwell_h": float(
                        members["duration_s"].sum() / 3600.0
                    ),
                    "diameter_m": diameter_m,
                }
            )

    return (
        pd.concat(clustered_parts, ignore_index=True),
        pd.DataFrame(location_rows),
    )
