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

SEMANTIC_STAY_COLUMNS = [
    "user_id",
    "arrival_time_utc",
    "departure_time_utc",
    "duration_s",
    "latitude",
    "longitude",
    "distance_to_beijing_km",
    "arrival_time_local",
    "departure_time_local",
    "arrival_local_date",
    "arrival_local_weekday",
    "location_id",
]

LOCATION_COLUMNS = [
    "user_id",
    "location_id",
    "latitude",
    "longitude",
    "stay_count",
    "active_local_dates",
    "total_dwell_h",
    "diameter_m",
]

OUTPUT_COLUMNS = [
    "user_id",
    "label",
    "location_id",
    "latitude",
    "longitude",
    "evidence_strength",
    "relevant_dwell_share",
    "share_margin",
    "relevant_dates",
    "relevant_dwell_h",
    "stay_count",
    "active_local_dates",
    "diameter_m",
]


@dataclass(frozen=True)
class HomeOfficeConfig:
    """Frozen CP2 v1 engineering baseline for Home/Office inference."""

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

    def __post_init__(self) -> None:
        if self.beijing_radius_km <= 0:
            raise ValueError("beijing_radius_km must be positive")
        if self.location_max_diameter_m <= 0:
            raise ValueError("location_max_diameter_m must be positive")
        if self.min_relevant_date_overlap_s < 0:
            raise ValueError("min_relevant_date_overlap_s must be non-negative")
        for name, value in [
            ("beijing_min_stay_share", self.beijing_min_stay_share),
            ("beijing_min_dwell_share", self.beijing_min_dwell_share),
            ("home_min_share", self.home_min_share),
            ("home_min_margin", self.home_min_margin),
            ("office_min_share", self.office_min_share),
            ("office_min_margin", self.office_min_margin),
        ]:
            if not 0.0 <= value <= 1.0:
                raise ValueError(f"{name} must be within [0, 1]")
        for name, value in [
            ("home_min_dates", self.home_min_dates),
            ("office_min_dates", self.office_min_dates),
            ("support_saturation_dates", self.support_saturation_dates),
        ]:
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        for name, value in [
            ("home_start_hour", self.home_start_hour),
            ("home_end_hour", self.home_end_hour),
            ("office_start_hour", self.office_start_hour),
            ("office_end_hour", self.office_end_hour),
        ]:
            if not 0 <= value <= 23:
                raise ValueError(f"{name} must be between 0 and 23")
        if not self.office_weekdays:
            raise ValueError("office_weekdays must not be empty")
        if any(day < 0 or day > 6 for day in self.office_weekdays):
            raise ValueError("office_weekdays values must be between 0 and 6")
        ZoneInfo(self.timezone)


def _empty_semantic_stays() -> pd.DataFrame:
    return pd.DataFrame(columns=SEMANTIC_STAY_COLUMNS)


def _empty_locations() -> pd.DataFrame:
    return pd.DataFrame(columns=LOCATION_COLUMNS)


def _empty_output() -> pd.DataFrame:
    return pd.DataFrame(columns=OUTPUT_COLUMNS)


def _validate_stays(stays: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED_STAY_COLUMNS.difference(stays.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    out = stays.loc[:, sorted(REQUIRED_STAY_COLUMNS)].copy()
    out["user_id"] = out["user_id"].astype(str)
    out["arrival_time_utc"] = pd.to_datetime(out["arrival_time_utc"], utc=True)
    out["departure_time_utc"] = pd.to_datetime(out["departure_time_utc"], utc=True)
    out["duration_s"] = pd.to_numeric(out["duration_s"], errors="coerce")
    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")

    if out[
        ["arrival_time_utc", "departure_time_utc", "duration_s", "latitude", "longitude"]
    ].isna().any().any():
        raise ValueError("stay table contains missing or unparsable required values")
    if (out["duration_s"] < 0).any():
        raise ValueError("duration_s must be non-negative")
    if (out["departure_time_utc"] < out["arrival_time_utc"]).any():
        raise ValueError("departure_time_utc must not precede arrival_time_utc")
    if (~out["latitude"].between(-90.0, 90.0)).any():
        raise ValueError("latitude outside [-90, 90]")
    if (~out["longitude"].between(-180.0, 180.0)).any():
        raise ValueError("longitude outside [-180, 180]")

    return out.sort_values(
        ["user_id", "arrival_time_utc", "departure_time_utc"],
        kind="stable",
    ).reset_index(drop=True)


def _pairwise_haversine_matrix_m(group: pd.DataFrame) -> np.ndarray:
    lat = group["latitude"].to_numpy(dtype=float)
    lon = group["longitude"].to_numpy(dtype=float)
    return np.asarray(
        haversine_m(
            lat[:, None],
            lon[:, None],
            lat[None, :],
            lon[None, :],
        ),
        dtype=float,
    )


def _complete_link_user(
    group: pd.DataFrame,
    *,
    threshold_m: float,
) -> tuple[pd.DataFrame, np.ndarray]:
    ordered = group.sort_values("arrival_time_local", kind="stable").copy()
    n = len(ordered)

    if n == 1:
        ordered["location_id"] = 0
        return ordered, np.zeros((1, 1), dtype=float)

    distances = _pairwise_haversine_matrix_m(ordered)
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
    ordered["location_id"] = ordered["_raw_location_id"].map(label_map).astype(int)
    ordered = ordered.drop(columns="_raw_location_id")
    return ordered, distances


def build_semantic_locations(
    stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply frozen CP2 geography/timezone policy and compact location clustering.

    Returns in-region semantic stays with a per-user location_id and the
    corresponding location summary table. Out-of-region travel stays and users
    outside the Beijing-focused cohort are intentionally absent.
    """
    cfg = config or HomeOfficeConfig()
    raw = _validate_stays(stays)
    if raw.empty:
        return _empty_semantic_stays(), _empty_locations()

    distance_km = np.asarray(
        haversine_m(
            raw["latitude"].to_numpy(dtype=float),
            raw["longitude"].to_numpy(dtype=float),
            cfg.beijing_latitude,
            cfg.beijing_longitude,
        ),
        dtype=float,
    ) / 1000.0

    raw["distance_to_beijing_km"] = distance_km
    raw["_inside_region"] = raw["distance_to_beijing_km"] <= cfg.beijing_radius_km
    raw["_inside_dwell_s"] = np.where(raw["_inside_region"], raw["duration_s"], 0.0)

    by_user = (
        raw.groupby("user_id")
        .agg(
            total_stays=("user_id", "size"),
            inside_stays=("_inside_region", "sum"),
            total_dwell_s=("duration_s", "sum"),
            inside_dwell_s=("_inside_dwell_s", "sum"),
        )
    )
    by_user["stay_share_inside"] = by_user["inside_stays"] / by_user["total_stays"]
    by_user["dwell_share_inside"] = np.where(
        by_user["total_dwell_s"] > 0,
        by_user["inside_dwell_s"] / by_user["total_dwell_s"],
        0.0,
    )

    eligible = by_user.index[
        (by_user["stay_share_inside"] >= cfg.beijing_min_stay_share)
        & (by_user["dwell_share_inside"] >= cfg.beijing_min_dwell_share)
    ]

    semantic = raw[raw["user_id"].isin(eligible) & raw["_inside_region"]].copy()
    if semantic.empty:
        return _empty_semantic_stays(), _empty_locations()

    timezone = ZoneInfo(cfg.timezone)
    semantic["arrival_time_local"] = semantic["arrival_time_utc"].dt.tz_convert(timezone)
    semantic["departure_time_local"] = semantic["departure_time_utc"].dt.tz_convert(timezone)
    semantic["arrival_local_date"] = semantic["arrival_time_local"].dt.date
    semantic["arrival_local_weekday"] = semantic["arrival_time_local"].dt.weekday

    clustered_parts: list[pd.DataFrame] = []
    location_rows: list[dict[str, object]] = []

    for user_id, group in semantic.groupby("user_id", sort=True):
        clustered_user, distances = _complete_link_user(
            group,
            threshold_m=cfg.location_max_diameter_m,
        )
        clustered_parts.append(clustered_user)

        labels = clustered_user["location_id"].to_numpy(dtype=int)
        for location_id in np.unique(labels):
            member_idx = np.flatnonzero(labels == location_id)
            members = clustered_user.iloc[member_idx]
            diameter_m = (
                float(distances[np.ix_(member_idx, member_idx)].max())
                if len(member_idx) > 1
                else 0.0
            )
            if diameter_m > cfg.location_max_diameter_m + 1e-6:
                raise RuntimeError("complete-link location exceeded configured maximum diameter")

            location_rows.append(
                {
                    "user_id": user_id,
                    "location_id": int(location_id),
                    "latitude": float(members["latitude"].median()),
                    "longitude": float(members["longitude"].median()),
                    "stay_count": int(len(members)),
                    "active_local_dates": int(members["arrival_time_local"].dt.date.nunique()),
                    "total_dwell_h": float(members["duration_s"].sum() / 3600.0),
                    "diameter_m": diameter_m,
                }
            )

    clustered = pd.concat(clustered_parts, ignore_index=True)
    clustered = clustered.sort_values(
        ["user_id", "arrival_time_local", "location_id"],
        kind="stable",
    ).reset_index(drop=True)

    locations = pd.DataFrame(location_rows, columns=LOCATION_COLUMNS)
    locations = locations.sort_values(["user_id", "location_id"], kind="stable").reset_index(drop=True)

    return clustered.loc[:, SEMANTIC_STAY_COLUMNS], locations


def _interval_overlap_s(
    start: pd.Timestamp,
    end: pd.Timestamp,
    window_start: pd.Timestamp,
    window_end: pd.Timestamp,
) -> float:
    overlap_start = max(start, window_start)
    overlap_end = min(end, window_end)
    if overlap_end <= overlap_start:
        return 0.0
    return float((overlap_end - overlap_start).total_seconds())


def _window_contributions(
    semantic_stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig,
    kind: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []

    for row in semantic_stays.itertuples(index=False):
        start = row.arrival_time_local
        end = row.departure_time_local
        day = start.normalize() - pd.Timedelta(days=1)
        last_day = end.normalize()

        while day <= last_day:
            if kind == "home":
                window_start = day + pd.Timedelta(hours=config.home_start_hour)
                window_end = day + pd.Timedelta(days=1) + pd.Timedelta(hours=config.home_end_hour)
                behavior_date = window_start.date()
                include = True
            elif kind == "office":
                window_start = day + pd.Timedelta(hours=config.office_start_hour)
                window_end = day + pd.Timedelta(hours=config.office_end_hour)
                behavior_date = window_start.date()
                include = day.weekday() in config.office_weekdays
            else:
                raise ValueError(f"unknown contribution kind: {kind}")

            if include:
                overlap_s = _interval_overlap_s(start, end, window_start, window_end)
                if overlap_s > 0:
                    rows.append(
                        {
                            "user_id": row.user_id,
                            "location_id": int(row.location_id),
                            "behavior_date": behavior_date,
                            "overlap_s": overlap_s,
                        }
                    )
            day += pd.Timedelta(days=1)

    return pd.DataFrame(
        rows,
        columns=["user_id", "location_id", "behavior_date", "overlap_s"],
    )


def _aggregate_window(
    contrib: pd.DataFrame,
    *,
    prefix: str,
    min_date_overlap_s: float,
) -> pd.DataFrame:
    dwell_col = f"{prefix}_dwell_s"
    dates_col = f"{prefix}_dates"

    if contrib.empty:
        return pd.DataFrame(columns=["user_id", "location_id", dwell_col, dates_col])

    per_date = (
        contrib.groupby(["user_id", "location_id", "behavior_date"], as_index=False)["overlap_s"]
        .sum()
    )
    dwell = (
        per_date.groupby(["user_id", "location_id"], as_index=False)["overlap_s"]
        .sum()
        .rename(columns={"overlap_s": dwell_col})
    )
    dates = (
        per_date.loc[per_date["overlap_s"] >= min_date_overlap_s]
        .groupby(["user_id", "location_id"], as_index=False)["behavior_date"]
        .nunique()
        .rename(columns={"behavior_date": dates_col})
    )
    return dwell.merge(dates, on=["user_id", "location_id"], how="left").fillna({dates_col: 0})


def _location_features(
    semantic_stays: pd.DataFrame,
    locations: pd.DataFrame,
    *,
    config: HomeOfficeConfig,
) -> pd.DataFrame:
    home = _aggregate_window(
        _window_contributions(semantic_stays, config=config, kind="home"),
        prefix="home",
        min_date_overlap_s=config.min_relevant_date_overlap_s,
    )
    office = _aggregate_window(
        _window_contributions(semantic_stays, config=config, kind="office"),
        prefix="office",
        min_date_overlap_s=config.min_relevant_date_overlap_s,
    )

    features = (
        locations.merge(home, on=["user_id", "location_id"], how="left")
        .merge(office, on=["user_id", "location_id"], how="left")
    )
    for col in ["home_dwell_s", "home_dates", "office_dwell_s", "office_dates"]:
        features[col] = features[col].fillna(0)

    features["home_dates"] = features["home_dates"].astype(int)
    features["office_dates"] = features["office_dates"].astype(int)

    for prefix in ["home", "office"]:
        dwell_col = f"{prefix}_dwell_s"
        share_col = f"{prefix}_dwell_share"
        user_total = features.groupby("user_id")[dwell_col].transform("sum")
        features[share_col] = np.where(user_total > 0, features[dwell_col] / user_total, 0.0)

    return features


def _top_candidate(
    features: pd.DataFrame,
    *,
    label: str,
    min_dates: int,
) -> pd.DataFrame:
    if label == "HOME":
        prefix = "home"
    elif label == "OFFICE":
        prefix = "office"
    else:
        raise ValueError(label)

    dwell_col = f"{prefix}_dwell_s"
    dates_col = f"{prefix}_dates"
    share_col = f"{prefix}_dwell_share"

    eligible = features[
        (features["stay_count"] >= 2)
        & (features[dates_col] >= min_dates)
        & (features[dwell_col] > 0)
    ].copy()
    if eligible.empty:
        return eligible

    eligible = eligible.sort_values(
        ["user_id", share_col, dates_col, dwell_col, "stay_count", "location_id"],
        ascending=[True, False, False, False, False, True],
        kind="stable",
    )
    eligible["_rank"] = eligible.groupby("user_id").cumcount() + 1

    top = eligible.loc[eligible["_rank"] == 1].copy()
    second = eligible.loc[
        eligible["_rank"] == 2,
        ["user_id", share_col],
    ].rename(columns={share_col: "_second_share"})

    top = top.merge(second, on="user_id", how="left")
    top["_second_share"] = top["_second_share"].fillna(0.0)
    top["share_margin"] = top[share_col] - top["_second_share"]
    top["relevant_dwell_share"] = top[share_col]
    top["relevant_dates"] = top[dates_col].astype(int)
    top["relevant_dwell_h"] = top[dwell_col] / 3600.0
    return top


def _emit_label(
    top: pd.DataFrame,
    *,
    label: str,
    min_share: float,
    min_margin: float,
    support_saturation_dates: int,
) -> pd.DataFrame:
    if top.empty:
        return _empty_output()

    emitted = top[
        (top["relevant_dwell_share"] >= min_share)
        & (top["share_margin"] >= min_margin)
    ].copy()
    if emitted.empty:
        return _empty_output()

    support_factor = np.minimum(
        emitted["relevant_dates"].to_numpy(dtype=float) / float(support_saturation_dates),
        1.0,
    )
    emitted["evidence_strength"] = (
        emitted["relevant_dwell_share"].to_numpy(dtype=float)
        + emitted["share_margin"].to_numpy(dtype=float)
        + support_factor
    ) / 3.0
    emitted["label"] = label

    return emitted.loc[:, OUTPUT_COLUMNS]


def infer_home_office(
    stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
) -> pd.DataFrame:
    """Infer conservative Home/Office labels from CP1 stay events.

    evidence_strength is a heuristic evidence index in [0, 1], not a
    calibrated probability of semantic correctness.
    """
    cfg = config or HomeOfficeConfig()
    semantic_stays, locations = build_semantic_locations(stays, config=cfg)
    if semantic_stays.empty or locations.empty:
        return _empty_output()

    features = _location_features(semantic_stays, locations, config=cfg)

    home_top = _top_candidate(features, label="HOME", min_dates=cfg.home_min_dates)
    office_top = _top_candidate(features, label="OFFICE", min_dates=cfg.office_min_dates)

    home = _emit_label(
        home_top,
        label="HOME",
        min_share=cfg.home_min_share,
        min_margin=cfg.home_min_margin,
        support_saturation_dates=cfg.support_saturation_dates,
    )
    office = _emit_label(
        office_top,
        label="OFFICE",
        min_share=cfg.office_min_share,
        min_margin=cfg.office_min_margin,
        support_saturation_dates=cfg.support_saturation_dates,
    )

    if home.empty and office.empty:
        return _empty_output()

    out = pd.concat([home, office], ignore_index=True)
    label_order = pd.Categorical(out["label"], categories=["HOME", "OFFICE"], ordered=True)
    out = (
        out.assign(_label_order=label_order)
        .sort_values(["user_id", "_label_order"], kind="stable")
        .drop(columns="_label_order")
        .reset_index(drop=True)
    )
    return out.loc[:, OUTPUT_COLUMNS]
