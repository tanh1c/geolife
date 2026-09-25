"""Private materialization for the behavior-first GeoLife EDA."""

from __future__ import annotations

import argparse
import io
import os
import re
import tempfile
import zipfile
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering

from geolife.geo.distance import haversine_m
from geolife.model import HomeOfficeConfig, build_semantic_locations, infer_home_office
from geolife.staypoints import clean_trajectory_with_audit, detect_staypoints

ARTIFACT_DIR = Path("artifacts/03a")
STAY_CACHE = ARTIFACT_DIR / "stays_baseline_v1.pkl"
POINT_DAY_CACHE = ARTIFACT_DIR / "cleaned_point_daily_metrics.pkl"
EXPECTED_STAYS = 5_821
EXPECTED_STAY_USERS = 136
EXPECTED_RELEASE_USERS = 182
CHECKPOINT_EVERY = 500
FROZEN_CP1 = {
    "same_second_radius_m": 10.0,
    "max_gap_s": 300.0,
    "hard_speed_guard_kmh": 1200.0,
    "distance_threshold_m": 200.0,
    "min_dwell_s": 1200.0,
}
FROZEN_CLEANING_KWARGS = {
    key: FROZEN_CP1[key]
    for key in ("same_second_radius_m", "max_gap_s", "hard_speed_guard_kmh")
}
FROZEN_STAY_KWARGS = {
    key: FROZEN_CP1[key] for key in ("distance_threshold_m", "min_dwell_s")
}
STAY_COLUMNS = [
    "user_id",
    "source_file",
    "sequence_id",
    "arrival_time_utc",
    "departure_time_utc",
    "duration_s",
    "latitude",
    "longitude",
    "n_points",
]
POINT_DAY_COLUMNS = [
    "user_id",
    "local_date",
    "point_count",
    "observed_span_s",
    "largest_gap_s",
    "has_large_gap",
    "cleaned_travel_distance_m",
    "movement_duration_s",
    "transition_count",
    "first_observed_hour",
    "last_observed_hour",
    "hour_coverage_count",
]
_MEMBER_RE = re.compile(r"(?:^|/)Data/(\d{3})/Trajectory/([^/]+\.plt)$")


def ensure_private_artifact_path(path: Path) -> None:
    """Reject EDA artifact writes outside the private artifact directory."""
    try:
        path.resolve().relative_to(ARTIFACT_DIR.resolve())
    except ValueError as error:
        raise ValueError("private artifacts must be written beneath artifacts/03a") from error


_POINT_DAY_HELPER_COLUMNS = ["_first_timestamp", "_last_timestamp", "_observed_hours"]


def _point_day_columns(*, include_helpers: bool = False) -> list[str]:
    return POINT_DAY_COLUMNS + (_POINT_DAY_HELPER_COLUMNS if include_helpers else [])


# CP1 audit rows are allocated to the UTC-local day of their event timestamp.
# This preserves terminal/discarded events that no retained row can carry.
def _audit_counts_by_day(audit: pd.DataFrame) -> pd.Series:
    if audit.empty:
        return pd.Series(dtype="int64")
    return audit.groupby(audit["timestamp"].dt.date, sort=True).size()


def _aggregate_point_days(point_days: pd.DataFrame) -> pd.DataFrame:
    """Merge per-PLT daily aggregates into exactly one row per user and day."""
    if point_days.empty:
        return _empty_point_days()

    rows = []
    for (user_id, local_date), day in point_days.groupby(["user_id", "local_date"], sort=True):
        first = day["_first_timestamp"].min()
        last = day["_last_timestamp"].max()
        rows.append(
            {
                "user_id": user_id,
                "local_date": local_date,
                "point_count": int(day["point_count"].sum()),
                "observed_span_s": float((last - first).total_seconds()) if pd.notna(first) else 0.0,
                "largest_gap_s": float(day["largest_gap_s"].max()),
                "has_large_gap": bool(day["has_large_gap"].any()),
                "cleaned_travel_distance_m": float(day["cleaned_travel_distance_m"].sum()),
                "movement_duration_s": float(day["movement_duration_s"].sum()),
                "transition_count": int(day["transition_count"].sum()),
                "first_observed_hour": int(day["first_observed_hour"].min()) if pd.notna(first) else pd.NA,
                "last_observed_hour": int(day["last_observed_hour"].max()) if pd.notna(last) else pd.NA,
                "hour_coverage_count": len({hour for hours in day["_observed_hours"] for hour in hours}),
            }
        )
    return pd.DataFrame(rows, columns=POINT_DAY_COLUMNS)


def _empty_stays() -> pd.DataFrame:
    return pd.DataFrame(columns=STAY_COLUMNS)


def _empty_point_days() -> pd.DataFrame:
    return pd.DataFrame(columns=POINT_DAY_COLUMNS)


def classify_day_quality(point_day: pd.DataFrame) -> pd.DataFrame:
    """Apply exploratory observation-support gates without interpreting gaps as behavior."""
    result = point_day.copy()
    result["usable_for_temporal_profile"] = (
        (result.get("point_count", 0) >= 3)
        & (result.get("observed_span_h", 0.0) >= 2.0)
        & (result.get("largest_gap_h", 0.0) <= 6.0)
    )
    result["usable_for_motif"] = (
        (result.get("stay_count", 0) >= 1) & (result.get("stay_observed_span_h", 0.0) >= 2.0)
    )
    return result


def summarize_cleaned_point_days(cleaned: pd.DataFrame, timezone_id: str) -> pd.DataFrame:
    """Summarize cleaned trajectories by local day without crossing CP1 sequences."""
    required = {"timestamp", "latitude", "longitude", "sequence_id"}
    missing = required.difference(cleaned.columns)
    if missing:
        raise ValueError(f"cleaned points are missing columns: {sorted(missing)}")
    if cleaned.empty:
        return classify_day_quality(pd.DataFrame())

    points = cleaned.copy()
    points["timestamp"] = pd.to_datetime(points["timestamp"], utc=True)
    local = points["timestamp"].dt.tz_convert(timezone_id)
    points["local_date"] = local.dt.date
    points["local_hour"] = local.dt.hour
    rows = []
    group_columns = ["local_date"] if "user_id" not in points else ["user_id", "local_date"]
    for key, day in points.groupby(group_columns, sort=True):
        if "user_id" in points:
            user_id, local_date = key
        else:
            user_id, local_date = None, key
        timestamps = day["timestamp"]
        gaps_s = timestamps.diff().dt.total_seconds().iloc[1:]
        lat = day["latitude"].to_numpy(dtype=float)
        lon = day["longitude"].to_numpy(dtype=float)
        sequences = day["sequence_id"].to_numpy()
        if len(day) > 1:
            distances_m = np.asarray(haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:]), dtype=float)
            valid_segments = (gaps_s.to_numpy(dtype=float) > 0) & (sequences[:-1] == sequences[1:])
            distance_m = float(distances_m[valid_segments].sum())
            movement_duration_h = float(gaps_s.to_numpy(dtype=float)[valid_segments].sum() / 3600)
        else:
            distance_m = movement_duration_h = 0.0
        observed_span_h = float((timestamps.max() - timestamps.min()).total_seconds() / 3600)
        boundary_count = (
            int(day["boundary_before_reason"].notna().sum())
            if "boundary_before_reason" in day
            else 0
        )
        rows.append(
            {
                "user_id": user_id,
                "local_date": local_date,
                "point_count": len(day),
                "observed_span_h": observed_span_h,
                "largest_gap_h": float(gaps_s[gaps_s > 0].max() / 3600) if (gaps_s > 0).any() else 0.0,
                "has_large_gap": bool((gaps_s > 6 * 3600).any()),
                "cleaned_distance_km": distance_m / 1000,
                "movement_duration_proxy_h": min(movement_duration_h, observed_span_h),
                "boundary_count": boundary_count,
                "first_local_hour": int(day["local_hour"].min()),
                "last_local_hour": int(day["local_hour"].max()),
                "hour_coverage_count": int(day["local_hour"].nunique()),
            }
        )
    return classify_day_quality(pd.DataFrame(rows))


def resolve_stay_timezones(stays: pd.DataFrame) -> pd.DataFrame:
    """Add per-stay IANA wall-clock fields for the exploratory all-resolved view."""
    try:
        from timezonefinder import TimezoneFinder
    except ImportError as error:
        raise RuntimeError(
            "timezonefinder==9.0.0 is required for all-resolved behavior EDA; "
            "install it before running --stage behavior"
        ) from error

    result = stays.copy()
    finder = TimezoneFinder(in_memory=True)
    timezone_ids = [
        finder.timezone_at(lng=float(longitude), lat=float(latitude))
        for latitude, longitude in zip(result["latitude"], result["longitude"], strict=True)
    ]
    result["timezone_id"] = timezone_ids
    resolved = result["timezone_id"].notna()
    result["arrival_time_local"] = pd.Series([pd.NaT] * len(result), dtype="object")
    result["departure_time_local"] = pd.Series([pd.NaT] * len(result), dtype="object")
    for timezone_id, indices in result.loc[resolved].groupby("timezone_id").groups.items():
        result.loc[indices, "arrival_time_local"] = pd.to_datetime(
            result.loc[indices, "arrival_time_utc"], utc=True
        ).dt.tz_convert(ZoneInfo(timezone_id)).astype(object)
        result.loc[indices, "departure_time_local"] = pd.to_datetime(
            result.loc[indices, "departure_time_utc"], utc=True
        ).dt.tz_convert(ZoneInfo(timezone_id)).astype(object)
    result["local_date"] = result["arrival_time_local"].map(
        lambda value: value.date() if pd.notna(value) else pd.NaT
    )
    result["local_weekday"] = result["arrival_time_local"].map(
        lambda value: value.weekday() if pd.notna(value) else pd.NA
    )
    return result


def relabel_locations_deterministically(clustered: pd.DataFrame) -> pd.DataFrame:
    """Rank within-user clusters by dwell, support, first arrival, then internal key."""
    result = clustered.copy()
    ranking = (
        result.groupby(["user_id", "internal_cluster_key"], as_index=False)
        .agg(
            total_dwell_s=("duration_s", "sum"),
            stay_count=("duration_s", "size"),
            first_arrival=("arrival_time_utc", "min"),
        )
        .sort_values(
            ["user_id", "total_dwell_s", "stay_count", "first_arrival", "internal_cluster_key"],
            ascending=[True, False, False, True, True],
            kind="stable",
        )
    )
    ranking["location_id"] = ranking.groupby("user_id", sort=False).cumcount()
    return result.merge(
        ranking.loc[:, ["user_id", "internal_cluster_key", "location_id"]],
        on=["user_id", "internal_cluster_key"],
        how="left",
        validate="many_to_one",
    )


def cluster_behavior_locations(
    stays: pd.DataFrame, threshold_m: float
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Complete-link cluster stays per user and return deterministic coordinate-free labels."""
    clustered_parts = []
    summary_parts = []
    for user_id, user_stays in stays.groupby("user_id", sort=True):
        user_stays = user_stays.copy()
        latitude = user_stays["latitude"].to_numpy(dtype=float)
        longitude = user_stays["longitude"].to_numpy(dtype=float)
        distances = np.asarray(
            haversine_m(latitude[:, None], longitude[:, None], latitude[None, :], longitude[None, :]),
            dtype=float,
        )
        if len(user_stays) == 1:
            labels = np.zeros(1, dtype=int)
        else:
            labels = AgglomerativeClustering(
                metric="precomputed",
                linkage="complete",
                distance_threshold=threshold_m,
                n_clusters=None,
            ).fit_predict(distances)
        user_stays["internal_cluster_key"] = labels
        clustered_parts.append(relabel_locations_deterministically(user_stays))
    clustered = pd.concat(clustered_parts, ignore_index=True) if clustered_parts else stays.copy()
    if not clustered.empty:
        summary_parts.append(
            clustered.groupby(["user_id", "location_id"], as_index=False).agg(
                total_dwell_s=("duration_s", "sum"), stay_count=("duration_s", "size")
            )
        )
    summary = pd.concat(summary_parts, ignore_index=True) if summary_parts else pd.DataFrame(
        columns=["user_id", "location_id", "total_dwell_s", "stay_count"]
    )
    return clustered, summary


def _stay_day_contributions(stays: pd.DataFrame) -> pd.DataFrame:
    """Split each stay's dwell at local hour and local-date boundaries."""
    rows = []
    for _, stay in stays.iterrows():
        arrival = stay["arrival_time_local"]
        departure = stay.get("departure_time_local", arrival + pd.Timedelta(seconds=stay["duration_s"]))
        start, end = arrival, departure
        while start < end:
            boundary = min(end, start.normalize() + pd.Timedelta(hours=start.hour + 1))
            rows.append(
                {
                    "user_id": stay["user_id"],
                    "local_date": start.date(),
                    "location_id": stay["location_id"],
                    "arrival_time_local": arrival,
                    "departure_time_local": departure,
                    "local_hour": start.hour,
                    "dwell_s": float((boundary - start).total_seconds()),
                }
            )
            start = boundary
    return pd.DataFrame(
        rows,
        columns=[
            "user_id", "local_date", "location_id", "arrival_time_local", "departure_time_local",
            "local_hour", "dwell_s",
        ],
    )


def build_user_day_features(stays: pd.DataFrame, point_days: pd.DataFrame) -> pd.DataFrame:
    """Join stay-based recurrence and dwell to cleaned-point movement by user/local day."""
    day_columns = ["user_id", "local_date"]
    contributions = _stay_day_contributions(stays)
    stay_days = (
        contributions.groupby(day_columns, as_index=False)
        .agg(
            recurring_location_count=("location_id", "nunique"),
            dwell_h=("dwell_s", lambda values: values.sum() / 3600),
            first_arrival=("arrival_time_local", "min"),
            last_departure=("departure_time_local", "max"),
        )
        if not contributions.empty
        else pd.DataFrame(columns=day_columns + ["recurring_location_count", "dwell_h", "first_arrival", "last_departure"])
    )
    stay_counts = (
        stays.groupby(["user_id", stays["arrival_time_local"].map(lambda value: value.date())])
        .size()
        .rename("stay_count")
        .reset_index(name="stay_count")
        .rename(columns={"arrival_time_local": "local_date"})
        if not stays.empty
        else pd.DataFrame(columns=day_columns + ["stay_count"])
    )
    stay_days = stay_days.merge(stay_counts, on=day_columns, how="outer", validate="one_to_one")
    stay_days["stay_observed_span_h"] = (
        (stay_days["last_departure"] - stay_days["first_arrival"]).dt.total_seconds() / 3600
    )
    result = point_days.merge(stay_days, on=day_columns, how="outer", validate="one_to_one")
    result["hourly_dwell"] = [np.zeros(24).tolist() for _ in range(len(result))]
    for contribution in contributions.itertuples(index=False):
        mask = (result["user_id"] == contribution.user_id) & (result["local_date"] == contribution.local_date)
        index = result.index[mask][0]
        hourly_dwell = np.asarray(result.at[index, "hourly_dwell"], dtype=float)
        hourly_dwell[contribution.local_hour] += contribution.dwell_s
        result.at[index, "hourly_dwell"] = hourly_dwell.tolist()
    result["local_weekday"] = pd.to_datetime(result["local_date"]).dt.weekday
    for column in ("stay_count", "recurring_location_count", "dwell_h", "stay_observed_span_h"):
        result[column] = result[column].fillna(0)
    return classify_day_quality(result)


def _jsd(left: np.ndarray, right: np.ndarray) -> float:
    left = np.asarray(left, dtype=float)
    right = np.asarray(right, dtype=float)
    if left.sum() == 0 or right.sum() == 0:
        return float("nan")
    left /= left.sum()
    right /= right.sum()
    midpoint = (left + right) / 2

    def divergence(values: np.ndarray) -> float:
        positive = values > 0
        return float((values[positive] * np.log2(values[positive] / midpoint[positive])).sum())

    return (divergence(left) + divergence(right)) / 2


def compute_schedule_stability(daily: pd.DataFrame) -> pd.DataFrame:
    """Compute continuous schedule evidence only for users meeting all support gates."""
    rows = []
    for user_id, user_days in daily.loc[daily["usable_for_temporal_profile"]].groupby("user_id", sort=True):
        user_days = user_days.sort_values("local_date", kind="stable").copy()
        user_days["week"] = pd.to_datetime(user_days["local_date"]).dt.to_period("W").astype(str)
        midpoint = len(user_days) // 2
        early, late = user_days.iloc[:midpoint], user_days.iloc[midpoint:]
        eligible = (
            user_days["week"].nunique() >= 2
            and len(early) >= 3
            and len(late) >= 3
            and early["dwell_h"].sum() >= 6.0
            and late["dwell_h"].sum() >= 6.0
        )
        jsd = (
            _jsd(np.sum(early["hourly_dwell"].tolist(), axis=0), np.sum(late["hourly_dwell"].tolist(), axis=0))
            if eligible
            else float("nan")
        )
        weekly_profiles = [
            np.sum(week["hourly_dwell"].tolist(), axis=0)
            for _, week in user_days.groupby("week", sort=True)
        ]
        weekly_jsds = [
            _jsd(weekly_profiles[index], weekly_profiles[other])
            for index in range(len(weekly_profiles))
            for other in range(index + 1, len(weekly_profiles))
        ]
        rows.append(
            {
                "user_id": user_id,
                "schedule_status": "eligible" if eligible else "insufficient",
                "early_late_jsd": jsd,
                "weekly_jsd_median": float(np.median(weekly_jsds)) if eligible and weekly_jsds else float("nan"),
                "active_calendar_weeks": user_days["week"].nunique(),
                "early_usable_days": len(early),
                "late_usable_days": len(late),
            }
        )
    return pd.DataFrame(rows)


def build_daily_motifs(stays: pd.DataFrame) -> pd.DataFrame:
    """Encode ordered daily stays with deterministic labels, never coordinate values."""
    rows = []
    for (user_id, local_date), day in stays.groupby(["user_id", "local_date"], sort=True):
        sequence = day.sort_values("arrival_time_local", kind="stable")["location_id"].tolist()
        rows.append(
            {"user_id": user_id, "local_date": local_date, "motif": "→".join(f"L{location}" for location in sequence)}
        )
    return pd.DataFrame(rows, columns=["user_id", "local_date", "motif"])


def build_user_behavior_features(
    stays: pd.DataFrame, point_days: pd.DataFrame
) -> pd.DataFrame:
    """Produce compact coverage, recurrence, and movement summaries for the exploratory EDA."""
    daily = build_user_day_features(stays, point_days)
    motifs = build_daily_motifs(stays)
    rows = []
    for user_id, user_days in daily.groupby("user_id", sort=True):
        user_stays = stays.loc[stays["user_id"] == user_id]
        location_dwell = user_stays.groupby("location_id")["duration_s"].sum().sort_values(ascending=False)
        shares = location_dwell / location_dwell.sum() if not location_dwell.empty else pd.Series(dtype=float)
        user_motifs = motifs.loc[motifs["user_id"] == user_id, "motif"]
        motif_counts = user_motifs.value_counts()
        motif_shares = motif_counts / motif_counts.sum() if not motif_counts.empty else pd.Series(dtype=float)
        hourly_dwell = np.sum(user_days["hourly_dwell"].tolist(), axis=0)
        hour_shares = hourly_dwell / hourly_dwell.sum() if hourly_dwell.sum() else hourly_dwell
        hour_entropy = float(-(hour_shares[hour_shares > 0] * np.log2(hour_shares[hour_shares > 0])).sum())
        weekday_dwell_h = float(user_days.loc[user_days["local_weekday"] < 5, "dwell_h"].sum())
        weekend_dwell_h = float(user_days.loc[user_days["local_weekday"] >= 5, "dwell_h"].sum())
        total_dwell_h = weekday_dwell_h + weekend_dwell_h
        weekday_motifs = motifs.loc[
            (motifs["user_id"] == user_id)
            & (pd.to_datetime(motifs["local_date"]).dt.weekday < 5),
            "motif",
        ]
        weekend_motifs = motifs.loc[
            (motifs["user_id"] == user_id)
            & (pd.to_datetime(motifs["local_date"]).dt.weekday >= 5),
            "motif",
        ]
        rows.append(
            {
                "user_id": user_id,
                "active_days": len(user_days),
                "usable_temporal_days": int(user_days["usable_for_temporal_profile"].sum()),
                "usable_motif_days": int(user_days["usable_for_motif"].sum()),
                "cp1_stay_count": len(user_stays),
                "recurring_location_count": len(location_dwell),
                "top_1_dwell_share": float(shares.iloc[:1].sum()) if not shares.empty else 0.0,
                "top_2_dwell_share": float(shares.iloc[:2].sum()) if not shares.empty else 0.0,
                "top_3_dwell_share": float(shares.iloc[:3].sum()) if not shares.empty else 0.0,
                "hour_entropy": hour_entropy,
                "temporal_concentration": float(hour_shares.max()) if hourly_dwell.sum() else 0.0,
                "weekday_dwell_proportion": weekday_dwell_h / total_dwell_h if total_dwell_h else 0.0,
                "weekend_dwell_proportion": weekend_dwell_h / total_dwell_h if total_dwell_h else 0.0,
                "most_frequent_motif": motif_counts.index[0] if not motif_counts.empty else pd.NA,
                "motif_frequency": float(motif_shares.iloc[0]) if not motif_shares.empty else 0.0,
                "motif_entropy": float(-(motif_shares * np.log2(motif_shares)).sum()) if not motif_shares.empty else 0.0,
                "weekday_motif_stability": float(weekday_motifs.value_counts(normalize=True).iloc[0]) if not weekday_motifs.empty else 0.0,
                "weekend_motif_stability": float(weekend_motifs.value_counts(normalize=True).iloc[0]) if not weekend_motifs.empty else 0.0,
                "cleaned_distance_km": float(user_days.get("cleaned_distance_km", pd.Series(dtype=float)).sum()),
                "movement_duration_proxy_h": float(user_days.get("movement_duration_proxy_h", pd.Series(dtype=float)).sum()),
            }
        )
    return pd.DataFrame(rows)


REASON_ORDER = (
    "no_cp1_stay",
    "outside_frozen_v1_geographic_scope",
    "no_recurring_location",
    "no_behavioral_window_overlap",
    "insufficient_relevant_dates",
    "share_below_frozen_gate",
    "margin_below_frozen_gate",
    "emitted",
)
_AUDIT_COLUMNS = [
    "user_id", "label", "reject_reason", "location_id", "relevant_dwell_share",
    "share_margin", "relevant_dates", "relevant_dwell_h", "stay_count",
]


def _audit_row(user_id: str, label: str, reason: str, candidate: pd.Series | None = None) -> dict[str, object]:
    row: dict[str, object] = {"user_id": user_id, "label": label, "reject_reason": reason}
    for column in _AUDIT_COLUMNS[3:]:
        row[column] = candidate.get(column, pd.NA) if candidate is not None else pd.NA
    return row


def _window_features(
    semantic_stays: pd.DataFrame,
    locations: pd.DataFrame,
    config: HomeOfficeConfig,
    label: str,
) -> pd.DataFrame:
    prefix = "home" if label == "HOME" else "office"
    rows = []
    for location in locations.itertuples(index=False):
        location_stays = semantic_stays.loc[
            (semantic_stays["user_id"] == location.user_id)
            & (semantic_stays["location_id"] == location.location_id)
        ]
        overlaps: list[tuple[object, float]] = []
        for stay in location_stays.itertuples(index=False):
            start, end = stay.arrival_time_local, stay.departure_time_local
            day, last_day = start.normalize() - pd.Timedelta(days=1), end.normalize()
            while day <= last_day:
                if label == "HOME":
                    window_start = day + pd.Timedelta(hours=config.home_start_hour)
                    window_end = day + pd.Timedelta(days=1, hours=config.home_end_hour)
                    behavior_date, include = window_start.date(), True
                else:
                    window_start = day + pd.Timedelta(hours=config.office_start_hour)
                    window_end = day + pd.Timedelta(hours=config.office_end_hour)
                    behavior_date, include = window_start.date(), day.weekday() in config.office_weekdays
                overlap_s = max(0.0, float((min(end, window_end) - max(start, window_start)).total_seconds()))
                if include and overlap_s:
                    overlaps.append((behavior_date, overlap_s))
                day += pd.Timedelta(days=1)
        per_date = pd.DataFrame(overlaps, columns=["behavior_date", "overlap_s"])
        rows.append(
            {
                "user_id": location.user_id,
                "location_id": location.location_id,
                "stay_count": location.stay_count,
                f"{prefix}_dwell_s": float(per_date["overlap_s"].sum()) if not per_date.empty else 0.0,
                f"{prefix}_dates": int((per_date.groupby("behavior_date")["overlap_s"].sum() >= config.min_relevant_date_overlap_s).sum()) if not per_date.empty else 0,
            }
        )
    features = pd.DataFrame(rows)
    dwell_col, share_col = f"{prefix}_dwell_s", f"{prefix}_dwell_share"
    denominator = features.groupby("user_id")[dwell_col].transform("sum")
    features[share_col] = np.where(denominator > 0, features[dwell_col] / denominator, 0.0)
    return features


def _top_audit_candidate(features: pd.DataFrame, label: str, config: HomeOfficeConfig) -> pd.Series | None:
    """Mirror frozen candidate eligibility while retaining raw-overlap diagnostics."""
    prefix = "home" if label == "HOME" else "office"
    dwell_col, dates_col, share_col = (f"{prefix}_{suffix}" for suffix in ("dwell_s", "dates", "dwell_share"))
    minimum_dates = config.home_min_dates if label == "HOME" else config.office_min_dates
    raw = features.loc[(features["stay_count"] >= 2) & (features[dwell_col] > 0)]
    eligible = raw.loc[raw[dates_col] >= minimum_dates].sort_values(
        [share_col, dates_col, dwell_col, "stay_count", "location_id"],
        ascending=[False, False, False, False, True], kind="stable",
    )
    if eligible.empty:
        if raw.empty:
            return None
        candidate = raw.sort_values(
            [share_col, dates_col, dwell_col, "stay_count", "location_id"],
            ascending=[False, False, False, False, True], kind="stable",
        ).iloc[0].copy()
        candidate["_insufficient_relevant_dates"] = True
        return candidate
    top = eligible.iloc[0].copy()
    top["relevant_dwell_share"] = top[share_col]
    top["share_margin"] = top[share_col] - (eligible.iloc[1][share_col] if len(eligible) > 1 else 0.0)
    top["relevant_dates"] = top[dates_col]
    top["relevant_dwell_h"] = top[dwell_col] / 3600.0
    return top


def _candidate_reason(candidate: pd.Series | None, label: str, config: HomeOfficeConfig) -> str:
    if candidate is None:
        return "no_behavioral_window_overlap"
    if candidate.get("_insufficient_relevant_dates", False):
        return "insufficient_relevant_dates"
    minimum_share = config.home_min_share if label == "HOME" else config.office_min_share
    minimum_margin = config.home_min_margin if label == "HOME" else config.office_min_margin
    if float(candidate["relevant_dwell_share"]) < minimum_share:
        return "share_below_frozen_gate"
    if float(candidate["share_margin"]) < minimum_margin:
        return "margin_below_frozen_gate"
    return "emitted"


def build_baseline_user_audit(release_users: set[str], stays: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct one ordered frozen-v1 outcome for each release user and label."""
    config = HomeOfficeConfig()
    raw_users = set(stays["user_id"].astype(str)) if not stays.empty else set()
    semantic, locations = build_semantic_locations(stays, config=config)
    semantic_users = set(semantic["user_id"].astype(str)) if not semantic.empty else set()
    recurring_users = (
        set(locations.loc[locations["stay_count"] >= 2, "user_id"].astype(str))
        if not locations.empty
        else set()
    )
    features_by_label = {
        label: _window_features(semantic, locations, config, label)
        for label in ("HOME", "OFFICE")
    } if not semantic.empty else {"HOME": pd.DataFrame(), "OFFICE": pd.DataFrame()}
    rows = []
    for user_id in sorted(release_users):
        for label in ("HOME", "OFFICE"):
            if user_id not in raw_users:
                rows.append(_audit_row(user_id, label, "no_cp1_stay"))
                continue
            if user_id not in semantic_users:
                rows.append(_audit_row(user_id, label, "outside_frozen_v1_geographic_scope"))
                continue
            if user_id not in recurring_users:
                rows.append(_audit_row(user_id, label, "no_recurring_location"))
                continue
            candidate = _top_audit_candidate(
                features_by_label[label].loc[features_by_label[label]["user_id"] == user_id], label, config
            )
            rows.append(_audit_row(user_id, label, _candidate_reason(candidate, label, config), candidate))
    audit = pd.DataFrame(rows, columns=_AUDIT_COLUMNS)
    assert len(audit) == len(release_users) * 2
    assert not audit.duplicated(["user_id", "label"]).any()
    assert audit["reject_reason"].isin(REASON_ORDER).all()
    emitted = infer_home_office(stays, config=config).loc[:, ["user_id", "label"]]
    audited = audit.loc[audit["reject_reason"] == "emitted", ["user_id", "label"]]
    assert audited.equals(emitted.reset_index(drop=True))
    return audit


def _anchor_count_class(summary: pd.DataFrame) -> str:
    recurring = int((summary["stay_count"] >= 2).sum())
    if recurring == 0:
        return "no_stable_anchor"
    if recurring == 1:
        return "dominant_anchor"
    if recurring == 2:
        return "two_anchor"
    return "multiple_anchor"


def run_location_sensitivity(stays: pd.DataFrame) -> pd.DataFrame:
    """Summarize the specified 100/200/300 m recurrence sensitivity outcomes."""
    if "local_date" not in stays:
        raise ValueError("stays must include local_date")
    variants: dict[float, tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]] = {}
    for threshold_m in (100.0, 200.0, 300.0):
        clustered, summary = cluster_behavior_locations(stays, threshold_m)
        motifs = build_daily_motifs(clustered)
        variants[threshold_m] = (clustered, summary, motifs)
    baseline_clustered, _baseline_summary, baseline_motifs = variants[200.0]

    def top_memberships(clustered: pd.DataFrame) -> dict[str, frozenset[tuple[pd.Timestamp, pd.Timestamp]]]:
        return {
            user_id: frozenset(
                zip(group["arrival_time_utc"], group["departure_time_utc"], strict=True)
            )
            for user_id, group in clustered.loc[clustered["location_id"] == 0].groupby("user_id", sort=True)
        }

    baseline_top = top_memberships(baseline_clustered)
    baseline_motif_content = baseline_motifs.set_index(["user_id", "local_date"])["motif"]
    rows = []
    for threshold_m, (clustered, summary, motifs) in variants.items():
        user_classes = [
            _anchor_count_class(group)
            for _, group in summary.groupby("user_id", sort=True)
        ]
        top = top_memberships(clustered)
        shared_top = set(top).intersection(baseline_top)
        motif_content = motifs.set_index(["user_id", "local_date"])["motif"]
        shared_motif_days = baseline_motif_content.index.intersection(motif_content.index)
        rows.append(
            {
                "threshold_m": threshold_m,
                "anchor_count_class": pd.Series(user_classes).value_counts().to_dict(),
                "top_anchor_stability_vs_200": (
                    sum(top[user_id] == baseline_top[user_id] for user_id in shared_top) / len(baseline_top)
                    if baseline_top else 1.0
                ),
                "recurring_location_count": int((summary["stay_count"] >= 2).sum()),
                "motif_membership_stability_vs_200": (
                    sum(
                        motif_content.loc[index] == baseline_motif_content.loc[index]
                        for index in shared_motif_days
                    ) / len(baseline_motif_content)
                    if len(baseline_motif_content) else 1.0
                ),
            }
        )
    return pd.DataFrame(rows)


def process_trajectory(
    user_id: str, source_file: str, raw: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply frozen CP1 once and retain only stay and daily aggregate outputs."""
    cleaned, audit = clean_trajectory_with_audit(raw, **FROZEN_CLEANING_KWARGS)
    detected = detect_staypoints(cleaned, **FROZEN_STAY_KWARGS)

    if detected.empty:
        stays = _empty_stays()
    else:
        stays = detected.rename(
            columns={"arrival_time": "arrival_time_utc", "departure_time": "departure_time_utc"}
        ).assign(user_id=user_id, source_file=source_file)
        stays = stays.loc[:, STAY_COLUMNS]

    points = cleaned.copy()
    points["local_date"] = points["timestamp"].dt.date
    points["local_hour"] = points["timestamp"].dt.hour
    audit_counts = _audit_counts_by_day(audit)
    point_days = {local_date: day for local_date, day in points.groupby("local_date", sort=True)}
    rows = []
    for local_date in sorted(set(point_days).union(audit_counts.index)):
        day = point_days.get(local_date)
        if day is None:
            rows.append(
                {
                    "user_id": user_id,
                    "local_date": local_date,
                    "point_count": 0,
                    "observed_span_s": 0.0,
                    "largest_gap_s": 0.0,
                    "has_large_gap": False,
                    "cleaned_travel_distance_m": 0.0,
                    "movement_duration_s": 0.0,
                    "transition_count": int(audit_counts[local_date]),
                    "first_observed_hour": pd.NA,
                    "last_observed_hour": pd.NA,
                    "hour_coverage_count": 0,
                    "_first_timestamp": pd.NaT,
                    "_last_timestamp": pd.NaT,
                    "_observed_hours": frozenset(),
                }
            )
            continue
        timestamps = day["timestamp"]
        gaps = timestamps.diff().dt.total_seconds().iloc[1:]
        lat = day["latitude"].to_numpy(dtype=float)
        lon = day["longitude"].to_numpy(dtype=float)
        sequence_id = day["sequence_id"].to_numpy()
        if len(day) > 1:
            segments = np.asarray(haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:]), dtype=float)
            positive_same_sequence = (gaps.to_numpy(dtype=float) > 0) & (sequence_id[1:] == sequence_id[:-1])
            travel_m = float(segments[positive_same_sequence].sum())
            movement_duration_s = float(gaps.to_numpy(dtype=float)[positive_same_sequence].sum())
        else:
            travel_m = 0.0
            movement_duration_s = 0.0
        rows.append(
            {
                "user_id": user_id,
                "local_date": local_date,
                "point_count": len(day),
                "observed_span_s": float((timestamps.max() - timestamps.min()).total_seconds()),
                "largest_gap_s": float(gaps.max()) if not gaps.empty else 0.0,
                "has_large_gap": bool((gaps > 6 * 3600).any()),
                "cleaned_travel_distance_m": travel_m,
                "movement_duration_s": movement_duration_s,
                "transition_count": int(audit_counts.get(local_date, 0)),
                "first_observed_hour": int(day["local_hour"].min()),
                "last_observed_hour": int(day["local_hour"].max()),
                "hour_coverage_count": int(day["local_hour"].nunique()),
                "_first_timestamp": timestamps.min(),
                "_last_timestamp": timestamps.max(),
                "_observed_hours": frozenset(day["local_hour"]),
            }
        )
    return stays, pd.DataFrame(rows, columns=_point_day_columns(include_helpers=True))


def validate_materialization(
    stays: pd.DataFrame, point_days: pd.DataFrame, release_users: set[str]
) -> None:
    """Validate the frozen CP1 reconciliation before any cache is accepted."""
    assert len(release_users) == EXPECTED_RELEASE_USERS, (
        f"expected {EXPECTED_RELEASE_USERS} release users, got {len(release_users)}"
    )
    assert len(stays) == EXPECTED_STAYS, (
        f"expected {EXPECTED_STAYS:,} stays, got {len(stays):,}"
    )
    assert stays["user_id"].nunique() == EXPECTED_STAY_USERS, (
        f"expected {EXPECTED_STAY_USERS} users with a stay, got {stays['user_id'].nunique()}"
    )
    assert set(stays["user_id"]).issubset(release_users)
    assert set(point_days["user_id"]).issubset(release_users)
    assert not point_days.duplicated(["user_id", "local_date"]).any(), (
        "expected exactly one row per user and local date"
    )


def _write_pickle_atomically(frame: pd.DataFrame, path: Path) -> None:
    ensure_private_artifact_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as tmp:
        temporary_path = Path(tmp.name)
    try:
        frame.to_pickle(temporary_path)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _zip_members(archive: zipfile.ZipFile) -> list[tuple[str, str, str]]:
    members = []
    for name in archive.namelist():
        match = _MEMBER_RE.search(name)
        if match:
            members.append((match.group(1), match.group(2), name))
    return sorted(members)


def _release_users(archive: zipfile.ZipFile) -> set[str]:
    return {
        match.group(1)
        for name in archive.namelist()
        if (match := re.search(r"(?:^|/)Data/(\d{3})(?:/|$)", name))
    }


def _read_zip_plt(archive: zipfile.ZipFile, member: str) -> pd.DataFrame:
    with archive.open(member) as raw_file:
        text = io.TextIOWrapper(raw_file, encoding="utf-8")
        frame = pd.read_csv(
            text,
            skiprows=6,
            header=None,
            names=["latitude", "longitude", "unused", "altitude_ft", "serial_date", "date", "time"],
        )
    frame["timestamp"] = pd.to_datetime(
        frame["date"].astype(str) + " " + frame["time"].astype(str),
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
        utc=True,
    )
    return frame.loc[:, ["timestamp", "latitude", "longitude"]]


def materialize_frozen_cp1(
    zip_path: Path, stay_cache: Path = STAY_CACHE, point_day_cache: Path = POINT_DAY_CACHE
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Materialize private frozen-CP1 caches from the release ZIP."""
    ensure_private_artifact_path(stay_cache)
    ensure_private_artifact_path(point_day_cache)
    with zipfile.ZipFile(zip_path) as archive:
        release_users = _release_users(archive)
        if stay_cache.exists() and point_day_cache.exists():
            # These private caches are created locally by this runner; do not load untrusted pickles.
            stays = pd.read_pickle(stay_cache)
            point_days = pd.read_pickle(point_day_cache)
            try:
                validate_materialization(stays, point_days, release_users)
            except AssertionError:
                pass
            else:
                return stays, point_days

        stay_parts: list[pd.DataFrame] = []
        point_day_parts: list[pd.DataFrame] = []
        members = _zip_members(archive)
        for index, (user_id, _filename, member) in enumerate(members, start=1):
            stays, point_days = process_trajectory(user_id, member, _read_zip_plt(archive, member))
            if not stays.empty:
                stay_parts.append(stays)
            if not point_days.empty:
                point_day_parts.append(point_days)
            if index % CHECKPOINT_EVERY == 0:
                _write_pickle_atomically(
                    pd.concat(stay_parts, ignore_index=True) if stay_parts else _empty_stays(), stay_cache
                )
                _write_pickle_atomically(
                    pd.concat(point_day_parts, ignore_index=True)
                    if point_day_parts
                    else _empty_point_days(),
                    point_day_cache,
                )

    all_stays = pd.concat(stay_parts, ignore_index=True) if stay_parts else _empty_stays()
    all_point_day_parts = (
        pd.concat(point_day_parts, ignore_index=True)
        if point_day_parts
        else pd.DataFrame(columns=_point_day_columns(include_helpers=True))
    )
    all_point_days = _aggregate_point_days(all_point_day_parts)
    validate_materialization(all_stays, all_point_days, release_users)
    _write_pickle_atomically(all_stays, stay_cache)
    _write_pickle_atomically(all_point_days, point_day_cache)
    return all_stays, all_point_days


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["materialize", "comparator"], required=True)
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    stays, _point_days = materialize_frozen_cp1(args.zip)
    with zipfile.ZipFile(args.zip) as archive:
        release_users = _release_users(archive)
    if args.stage == "comparator":
        audit = build_baseline_user_audit(release_users, stays)
        assert len(audit) == EXPECTED_RELEASE_USERS * 2
        counts = audit.loc[audit["reject_reason"] == "emitted", "label"].value_counts()
        assert counts.get("HOME", 0) == 27
        assert counts.get("OFFICE", 0) == 16
        print("validated frozen-v1 comparator parity: 27 HOME, 16 OFFICE")
        return
    print(
        f"validated {len(stays)} stays across {stays['user_id'].nunique()} users; "
        f"release universe {EXPECTED_RELEASE_USERS} users"
    )


if __name__ == "__main__":
    main()
