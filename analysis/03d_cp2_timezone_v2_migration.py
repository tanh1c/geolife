"""CP2 timezone-v2 production migration audit helpers.

This module intentionally contains an independent reference implementation
transcribed from the finalized notebook-03 timezone-v2 path. It exists only to
audit the production migration; production inference remains in the model.
"""

from __future__ import annotations

from dataclasses import dataclass
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from timezonefinder import TimezoneFinder

from geolife.geo.distance import haversine_m


REFERENCE_LOCATION_THRESHOLD_M = 200.0
REFERENCE_HOME_MIN_DATES = 3
REFERENCE_HOME_MIN_SHARE = 0.50
REFERENCE_HOME_MIN_MARGIN = 0.20
REFERENCE_OFFICE_MIN_DATES = 3
REFERENCE_OFFICE_MIN_SHARE = 0.30
REFERENCE_OFFICE_MIN_MARGIN = 0.10
REFERENCE_SUPPORT_SATURATION_DATES = 5
REFERENCE_MIN_DATE_OVERLAP_S = 600.0

PARITY_EVIDENCE_COLUMNS = [
    "user_id",
    "label",
    "location_id",
    "relevant_dwell_share",
    "share_margin",
    "relevant_dates",
    "evidence_strength",
]


@dataclass(frozen=True)
class MigrationDecision:
    cp1_stay_count_status: str
    timezone_resolution_status: str
    semantic_location_status: str
    emission_key_status: str
    evidence_status: str
    runner_status: str


def _validate_reference_stays(stays: pd.DataFrame) -> pd.DataFrame:
    required = {
        "user_id",
        "arrival_time_utc",
        "departure_time_utc",
        "duration_s",
        "latitude",
        "longitude",
    }
    missing = required.difference(stays.columns)
    if missing:
        raise ValueError(f"missing required columns: {sorted(missing)}")

    out = stays.copy()
    out["user_id"] = out["user_id"].astype(str)
    out["arrival_time_utc"] = pd.to_datetime(
        out["arrival_time_utc"],
        utc=True,
    )
    out["departure_time_utc"] = pd.to_datetime(
        out["departure_time_utc"],
        utc=True,
    )
    out["duration_s"] = pd.to_numeric(out["duration_s"], errors="raise")
    out["latitude"] = pd.to_numeric(out["latitude"], errors="raise")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="raise")
    return out.sort_values(
        ["user_id", "arrival_time_utc", "departure_time_utc"],
        kind="stable",
    ).reset_index(drop=True)


def reference_resolve_timezones(stays: pd.DataFrame) -> pd.DataFrame:
    """Notebook-03 coordinate -> IANA -> naive local wall-clock reference."""
    result = _validate_reference_stays(stays)
    finder = TimezoneFinder()
    result["timezone_id"] = [
        finder.timezone_at(
            lng=float(lon),
            lat=float(lat),
        )
        for lat, lon in zip(
            result["latitude"].to_numpy(dtype=float),
            result["longitude"].to_numpy(dtype=float),
            strict=True,
        )
    ]
    result = result.loc[result["timezone_id"].notna()].copy()

    def to_local_wall(timestamp_utc, timezone_id):
        ts = pd.Timestamp(timestamp_utc)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        return ts.tz_convert(
            ZoneInfo(str(timezone_id))
        ).tz_localize(None)

    result["arrival_time_local"] = pd.to_datetime(
        [
            to_local_wall(ts, tzid)
            for ts, tzid in zip(
                result["arrival_time_utc"],
                result["timezone_id"],
                strict=True,
            )
        ]
    )
    result["departure_time_local"] = pd.to_datetime(
        [
            to_local_wall(ts, tzid)
            for ts, tzid in zip(
                result["departure_time_utc"],
                result["timezone_id"],
                strict=True,
            )
        ]
    )
    result["arrival_local_date"] = result["arrival_time_local"].dt.date
    result["arrival_local_weekday"] = (
        result["arrival_time_local"].dt.weekday.astype("Int64")
    )
    return result


def _pairwise(group: pd.DataFrame) -> np.ndarray:
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


def reference_complete_link(
    semantic_stays: pd.DataFrame,
    *,
    threshold_m: float = REFERENCE_LOCATION_THRESHOLD_M,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Notebook-03 complete-link representation with raw sklearn labels."""
    clustered_parts = []
    location_rows = []

    for user_id, group in semantic_stays.groupby("user_id", sort=True):
        g = group.sort_values("arrival_time_utc", kind="stable").copy()
        distances = _pairwise(g)
        if len(g) == 1:
            labels = np.zeros(1, dtype=int)
        else:
            labels = AgglomerativeClustering(
                n_clusters=None,
                metric="precomputed",
                linkage="complete",
                distance_threshold=threshold_m,
            ).fit_predict(distances)
        g["location_id"] = labels.astype(int)
        clustered_parts.append(g)

        location_ids = g["location_id"].to_numpy(dtype=int)
        for location_id in np.unique(location_ids):
            member_idx = np.flatnonzero(location_ids == location_id)
            members = g.iloc[member_idx]
            diameter_m = (
                float(
                    distances[
                        np.ix_(member_idx, member_idx)
                    ].max()
                )
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
                        members["arrival_local_date"].nunique()
                    ),
                    "total_dwell_h": float(
                        members["duration_s"].sum() / 3600.0
                    ),
                    "diameter_m": diameter_m,
                }
            )

    clustered = (
        pd.concat(clustered_parts, ignore_index=True)
        if clustered_parts
        else semantic_stays.copy()
    )
    locations = pd.DataFrame(location_rows)
    if locations.empty:
        locations = pd.DataFrame(
            columns=[
                "user_id",
                "location_id",
                "latitude",
                "longitude",
                "stay_count",
                "active_local_dates",
                "total_dwell_h",
                "diameter_m",
            ]
        )
    return clustered, locations


def _interval_overlap_s(start, end, window_start, window_end) -> float:
    overlap_start = max(start, window_start)
    overlap_end = min(end, window_end)
    if overlap_end <= overlap_start:
        return 0.0
    return float((overlap_end - overlap_start).total_seconds())


def _reference_contributions(
    semantic_stays: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    night_rows = []
    office_rows = []
    for row in semantic_stays.itertuples(index=False):
        start = row.arrival_time_local
        end = row.departure_time_local
        day = start.normalize() - pd.Timedelta(days=1)
        last_day = end.normalize()

        while day <= last_day:
            night_start = day + pd.Timedelta(hours=21)
            night_end = day + pd.Timedelta(days=1, hours=6)
            night_s = _interval_overlap_s(
                start,
                end,
                night_start,
                night_end,
            )
            if night_s > 0:
                night_rows.append(
                    {
                        "user_id": row.user_id,
                        "location_id": int(row.location_id),
                        "behavior_date": night_start.date(),
                        "overlap_s": night_s,
                    }
                )

            if day.weekday() in {0, 1, 2, 3, 4}:
                office_start = day + pd.Timedelta(hours=9)
                office_end = day + pd.Timedelta(hours=17)
                office_s = _interval_overlap_s(
                    start,
                    end,
                    office_start,
                    office_end,
                )
                if office_s > 0:
                    office_rows.append(
                        {
                            "user_id": row.user_id,
                            "location_id": int(row.location_id),
                            "behavior_date": office_start.date(),
                            "overlap_s": office_s,
                        }
                    )
            day += pd.Timedelta(days=1)

    columns = [
        "user_id",
        "location_id",
        "behavior_date",
        "overlap_s",
    ]
    return (
        pd.DataFrame(night_rows, columns=columns),
        pd.DataFrame(office_rows, columns=columns),
    )


def _aggregate(contrib: pd.DataFrame, prefix: str) -> pd.DataFrame:
    dwell_col = f"{prefix}_dwell_s"
    dates_col = f"{prefix}_dates"
    if contrib.empty:
        return pd.DataFrame(
            columns=[
                "user_id",
                "location_id",
                dwell_col,
                dates_col,
            ]
        )

    per_date = (
        contrib.groupby(
            ["user_id", "location_id", "behavior_date"],
            as_index=False,
        )["overlap_s"]
        .sum()
    )
    dwell = (
        per_date.groupby(
            ["user_id", "location_id"],
            as_index=False,
        )["overlap_s"]
        .sum()
        .rename(columns={"overlap_s": dwell_col})
    )
    dates = (
        per_date.loc[
            per_date["overlap_s"] >= REFERENCE_MIN_DATE_OVERLAP_S
        ]
        .groupby(
            ["user_id", "location_id"],
            as_index=False,
        )["behavior_date"]
        .nunique()
        .rename(columns={"behavior_date": dates_col})
    )
    return dwell.merge(
        dates,
        on=["user_id", "location_id"],
        how="left",
    ).fillna({dates_col: 0})


def reference_features(
    semantic_stays: pd.DataFrame,
    locations: pd.DataFrame,
) -> pd.DataFrame:
    night, office = _reference_contributions(semantic_stays)
    features = (
        locations.merge(
            _aggregate(night, "night"),
            on=["user_id", "location_id"],
            how="left",
        )
        .merge(
            _aggregate(office, "office"),
            on=["user_id", "location_id"],
            how="left",
        )
    )
    for col in [
        "night_dwell_s",
        "night_dates",
        "office_dwell_s",
        "office_dates",
    ]:
        features[col] = features[col].fillna(0)
    features["night_dates"] = features["night_dates"].astype(int)
    features["office_dates"] = features["office_dates"].astype(int)

    night_total = features.groupby("user_id")[
        "night_dwell_s"
    ].transform("sum")
    office_total = features.groupby("user_id")[
        "office_dwell_s"
    ].transform("sum")
    features["night_dwell_share"] = np.where(
        night_total > 0,
        features["night_dwell_s"] / night_total,
        0.0,
    )
    features["office_dwell_share"] = np.where(
        office_total > 0,
        features["office_dwell_s"] / office_total,
        0.0,
    )
    return features


def _top_with_margin(
    features: pd.DataFrame,
    *,
    label: str,
    min_dates: int,
) -> pd.DataFrame:
    if label == "HOME":
        share_col = "night_dwell_share"
        dates_col = "night_dates"
        dwell_col = "night_dwell_s"
    else:
        share_col = "office_dwell_share"
        dates_col = "office_dates"
        dwell_col = "office_dwell_s"

    ranked = features[
        (features["stay_count"] >= 2)
        & (features[dates_col] >= min_dates)
        & (features[dwell_col] > 0)
    ].copy()
    if ranked.empty:
        return ranked

    ranked = ranked.sort_values(
        [
            "user_id",
            share_col,
            dates_col,
            dwell_col,
            "stay_count",
        ],
        ascending=[True, False, False, False, False],
        kind="stable",
    )
    ranked["_rank"] = ranked.groupby(
        "user_id",
        sort=False,
    ).cumcount() + 1

    top = ranked.loc[ranked["_rank"] == 1].copy()
    second = ranked.loc[
        ranked["_rank"] == 2,
        ["user_id", share_col],
    ].rename(columns={share_col: "_second_share"})
    top = top.merge(second, on="user_id", how="left")
    top["_second_share"] = top["_second_share"].fillna(0.0)
    top["share_margin"] = top[share_col] - top["_second_share"]
    top["relevant_dwell_share"] = top[share_col]
    top["relevant_dates"] = top[dates_col].astype(int)
    return top


def reference_infer_home_office(
    stays: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    semantic = reference_resolve_timezones(stays)
    clustered, locations = reference_complete_link(semantic)
    features = reference_features(clustered, locations)

    emitted = []
    for label, min_dates, min_share, min_margin in [
        (
            "HOME",
            REFERENCE_HOME_MIN_DATES,
            REFERENCE_HOME_MIN_SHARE,
            REFERENCE_HOME_MIN_MARGIN,
        ),
        (
            "OFFICE",
            REFERENCE_OFFICE_MIN_DATES,
            REFERENCE_OFFICE_MIN_SHARE,
            REFERENCE_OFFICE_MIN_MARGIN,
        ),
    ]:
        top = _top_with_margin(
            features,
            label=label,
            min_dates=min_dates,
        )
        if top.empty:
            continue
        chosen = top[
            (top["relevant_dwell_share"] >= min_share)
            & (top["share_margin"] >= min_margin)
        ].copy()
        if chosen.empty:
            continue
        chosen["label"] = label
        support = np.minimum(
            chosen["relevant_dates"].to_numpy(dtype=float)
            / REFERENCE_SUPPORT_SATURATION_DATES,
            1.0,
        )
        chosen["evidence_strength"] = (
            chosen["relevant_dwell_share"].to_numpy(dtype=float)
            + chosen["share_margin"].to_numpy(dtype=float)
            + support
        ) / 3.0
        emitted.append(chosen)

    if emitted:
        labels = pd.concat(emitted, ignore_index=True)
        labels = labels.loc[:, PARITY_EVIDENCE_COLUMNS].sort_values(
            ["user_id", "label"],
            kind="stable",
        ).reset_index(drop=True)
    else:
        labels = pd.DataFrame(columns=PARITY_EVIDENCE_COLUMNS)
    return labels, clustered, locations


def compare_migration(
    *,
    stays: pd.DataFrame,
    production_labels: pd.DataFrame,
    production_semantic: pd.DataFrame,
    production_locations: pd.DataFrame,
    reference_labels: pd.DataFrame,
    reference_semantic: pd.DataFrame,
    reference_locations: pd.DataFrame,
) -> tuple[pd.DataFrame, MigrationDecision]:
    production_keys = production_labels[
        ["user_id", "label", "location_id"]
    ].sort_values(
        ["user_id", "label", "location_id"],
        kind="stable",
    ).reset_index(drop=True)
    reference_keys = reference_labels[
        ["user_id", "label", "location_id"]
    ].sort_values(
        ["user_id", "label", "location_id"],
        kind="stable",
    ).reset_index(drop=True)

    key_equal = production_keys.equals(reference_keys)

    prod_ev = production_labels[
        PARITY_EVIDENCE_COLUMNS
    ].sort_values(
        ["user_id", "label"],
        kind="stable",
    ).reset_index(drop=True)
    ref_ev = reference_labels[
        PARITY_EVIDENCE_COLUMNS
    ].sort_values(
        ["user_id", "label"],
        kind="stable",
    ).reset_index(drop=True)

    evidence_equal = False
    if len(prod_ev) == len(ref_ev) and key_equal:
        evidence_equal = (
            np.allclose(
                prod_ev["relevant_dwell_share"].to_numpy(float),
                ref_ev["relevant_dwell_share"].to_numpy(float),
                rtol=0.0,
                atol=1e-12,
            )
            and np.allclose(
                prod_ev["share_margin"].to_numpy(float),
                ref_ev["share_margin"].to_numpy(float),
                rtol=0.0,
                atol=1e-12,
            )
            and np.array_equal(
                prod_ev["relevant_dates"].to_numpy(int),
                ref_ev["relevant_dates"].to_numpy(int),
            )
            and np.allclose(
                prod_ev["evidence_strength"].to_numpy(float),
                ref_ev["evidence_strength"].to_numpy(float),
                rtol=0.0,
                atol=1e-12,
            )
        )

    stay_key = [
        "user_id",
        "arrival_time_utc",
        "departure_time_utc",
        "latitude",
        "longitude",
    ]
    prod_stays = production_semantic.sort_values(
        stay_key,
        kind="stable",
    ).reset_index(drop=True)
    ref_stays = reference_semantic.sort_values(
        stay_key,
        kind="stable",
    ).reset_index(drop=True)

    timezone_equal = False
    location_equal = False
    if len(prod_stays) == len(ref_stays):
        key_equal_stays = prod_stays[stay_key].equals(
            ref_stays[stay_key]
        )
        timezone_equal = bool(
            key_equal_stays
            and prod_stays["timezone_id"].equals(
                ref_stays["timezone_id"]
            )
            and prod_stays["arrival_time_local"].equals(
                ref_stays["arrival_time_local"]
            )
            and prod_stays["departure_time_local"].equals(
                ref_stays["departure_time_local"]
            )
        )
        location_equal = bool(
            key_equal_stays
            and np.array_equal(
                prod_stays["location_id"].to_numpy(int),
                ref_stays["location_id"].to_numpy(int),
            )
        )

    prod_location_keys = production_locations[
        ["user_id", "location_id", "stay_count"]
    ].sort_values(
        ["user_id", "location_id"],
        kind="stable",
    ).reset_index(drop=True)
    ref_location_keys = reference_locations[
        ["user_id", "location_id", "stay_count"]
    ].sort_values(
        ["user_id", "location_id"],
        kind="stable",
    ).reset_index(drop=True)
    location_equal = bool(
        location_equal
        and prod_location_keys.equals(ref_location_keys)
    )

    summary = pd.DataFrame(
        [
            {
                "cp1_stays": int(len(stays)),
                "cp1_users": int(stays["user_id"].nunique()),
                "production_semantic_stays": int(len(production_semantic)),
                "reference_semantic_stays": int(len(reference_semantic)),
                "production_semantic_users": int(
                    production_semantic["user_id"].nunique()
                ),
                "reference_semantic_users": int(
                    reference_semantic["user_id"].nunique()
                ),
                "production_locations": int(len(production_locations)),
                "reference_locations": int(len(reference_locations)),
                "production_recurring_locations": int(
                    (production_locations["stay_count"] >= 2).sum()
                ),
                "reference_recurring_locations": int(
                    (reference_locations["stay_count"] >= 2).sum()
                ),
                "production_recurring_users": int(
                    production_locations.loc[
                        production_locations["stay_count"] >= 2,
                        "user_id",
                    ].nunique()
                ),
                "reference_recurring_users": int(
                    reference_locations.loc[
                        reference_locations["stay_count"] >= 2,
                        "user_id",
                    ].nunique()
                ),
                "production_home_emitted": int(
                    (production_labels["label"] == "HOME").sum()
                ),
                "reference_home_emitted": int(
                    (reference_labels["label"] == "HOME").sum()
                ),
                "production_office_emitted": int(
                    (production_labels["label"] == "OFFICE").sum()
                ),
                "reference_office_emitted": int(
                    (reference_labels["label"] == "OFFICE").sum()
                ),
                "timezone_distribution_exact": bool(timezone_equal),
                "location_membership_exact": bool(location_equal),
                "emission_keys_exact": bool(key_equal),
                "evidence_exact": bool(evidence_equal),
            }
        ]
    )

    base = MigrationDecision(
        cp1_stay_count_status=(
            "pass_5821_frozen_cp1"
            if len(stays) == 5821
            else "blocked_unexpected_cp1_count"
        ),
        timezone_resolution_status=(
            "pass_reference_timezone_parity"
            if timezone_equal
            else "blocked_timezone_parity"
        ),
        semantic_location_status=(
            "pass_reference_location_parity"
            if location_equal
            else "blocked_location_parity"
        ),
        emission_key_status=(
            "pass_reference_emission_key_parity"
            if key_equal
            else "blocked_emission_key_parity"
        ),
        evidence_status=(
            "pass_reference_evidence_parity"
            if evidence_equal
            else "blocked_evidence_parity"
        ),
        runner_status="pending",
    )
    hard = [
        base.cp1_stay_count_status,
        base.timezone_resolution_status,
        base.semantic_location_status,
        base.emission_key_status,
        base.evidence_status,
    ]
    decision = MigrationDecision(
        cp1_stay_count_status=base.cp1_stay_count_status,
        timezone_resolution_status=base.timezone_resolution_status,
        semantic_location_status=base.semantic_location_status,
        emission_key_status=base.emission_key_status,
        evidence_status=base.evidence_status,
        runner_status=(
            "ready_to_refreeze_cp2_v2"
            if all(value.startswith("pass_") for value in hard)
            else "blocked"
        ),
    )
    return summary, decision


def decision_frame(decision: MigrationDecision) -> pd.DataFrame:
    return pd.DataFrame([decision.__dict__])
