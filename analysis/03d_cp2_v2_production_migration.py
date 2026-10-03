"""Independent audit for the CP2 v2 production migration.

This module intentionally reconstructs the final Notebook-03 candidate without
calling production semantic helpers for the reference path. It is used to check
that the production migration implements the already-reviewed contract:

    WGS84 stay coordinate
        -> timezonefinder
        -> IANA timezone_id
        -> ZoneInfo(timezone_id)
        -> local wall-clock arrival/departure
        -> complete-link 200 m recurring locations
        -> frozen HOME/OFFICE evidence windows and emission gates

The reference comparison is by stay semantics, cluster signatures and emitted
evidence. Raw AgglomerativeClustering label integers are not treated as stable
across implementations.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
from sklearn.cluster import AgglomerativeClustering
from timezonefinder import TimezoneFinder

from geolife.geo.distance import haversine_m
from geolife.model import (
    HomeOfficeConfig,
    build_semantic_locations,
    infer_home_office,
)


EXPECTED_CP1_STAYS = 5_821
EXPECTED_CP1_STAY_USERS = 136
LOCATION_NAMESPACE = "production_complete_link_200m_local_timezone_v2"

SOURCE_KEY_COLUMNS = [
    "user_id",
    "arrival_time_utc",
    "departure_time_utc",
    "duration_s",
    "latitude",
    "longitude",
]


@dataclass(frozen=True)
class MigrationDecision:
    cp1_input_status: str
    timezone_resolution_status: str
    local_time_parity_status: str
    cluster_parity_status: str
    emission_parity_status: str
    runner_status: str


def _validate_reference_stays(stays: pd.DataFrame) -> pd.DataFrame:
    missing = set(SOURCE_KEY_COLUMNS).difference(stays.columns)
    if missing:
        raise ValueError(f"missing required stay columns: {sorted(missing)}")

    out = stays.loc[:, SOURCE_KEY_COLUMNS].copy()
    out["user_id"] = out["user_id"].astype(str)
    out["arrival_time_utc"] = pd.to_datetime(out["arrival_time_utc"], utc=True)
    out["departure_time_utc"] = pd.to_datetime(out["departure_time_utc"], utc=True)
    out["duration_s"] = pd.to_numeric(out["duration_s"], errors="coerce")
    out["latitude"] = pd.to_numeric(out["latitude"], errors="coerce")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="coerce")
    if out.isna().any().any():
        raise ValueError("reference stay input contains missing/unparsable values")
    return out.sort_values(
        ["user_id", "arrival_time_utc", "departure_time_utc"],
        kind="stable",
    ).reset_index(drop=True)


def reference_resolve_timezones(stays: pd.DataFrame) -> pd.DataFrame:
    """Reconstruct Notebook-03 coordinate -> IANA -> naive local wall time."""
    out = _validate_reference_stays(stays)
    finder = TimezoneFinder(in_memory=True)
    out["timezone_id"] = pd.array(
        [
            finder.timezone_at(lng=float(lon), lat=float(lat))
            for lat, lon in zip(
                out["latitude"].to_numpy(float),
                out["longitude"].to_numpy(float),
                strict=True,
            )
        ],
        dtype="string",
    )

    out["arrival_time_local"] = pd.NaT
    out["departure_time_local"] = pd.NaT
    for timezone_id, indices in out.loc[
        out["timezone_id"].notna()
    ].groupby("timezone_id", sort=True).groups.items():
        timezone = ZoneInfo(str(timezone_id))
        out.loc[indices, "arrival_time_local"] = (
            out.loc[indices, "arrival_time_utc"]
            .dt.tz_convert(timezone)
            .dt.tz_localize(None)
            .to_numpy()
        )
        out.loc[indices, "departure_time_local"] = (
            out.loc[indices, "departure_time_utc"]
            .dt.tz_convert(timezone)
            .dt.tz_localize(None)
            .to_numpy()
        )

    out["arrival_time_local"] = pd.to_datetime(
        out["arrival_time_local"], errors="coerce"
    )
    out["departure_time_local"] = pd.to_datetime(
        out["departure_time_local"], errors="coerce"
    )
    out["arrival_local_date"] = out["arrival_time_local"].dt.date
    return out.loc[out["timezone_id"].notna()].copy()


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


def reference_complete_link(
    resolved: pd.DataFrame,
    threshold_m: float = 200.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Independent reconstruction of Notebook-03 complete-link candidate."""
    clustered_parts: list[pd.DataFrame] = []
    rows: list[dict[str, object]] = []

    for user_id, group in resolved.groupby("user_id", sort=True):
        ordered = group.sort_values("arrival_time_utc", kind="stable").copy()
        if len(ordered) == 1:
            labels = np.zeros(1, dtype=int)
            distances = np.zeros((1, 1), dtype=float)
        else:
            distances = _pairwise(ordered)
            labels = AgglomerativeClustering(
                n_clusters=None,
                metric="precomputed",
                linkage="complete",
                distance_threshold=threshold_m,
            ).fit_predict(distances)

        ordered["_reference_location_id"] = labels.astype(int)
        clustered_parts.append(ordered)

        label_array = ordered["_reference_location_id"].to_numpy(int)
        for location_id in np.unique(label_array):
            member_idx = np.flatnonzero(label_array == location_id)
            members = ordered.iloc[member_idx]
            diameter_m = (
                float(distances[np.ix_(member_idx, member_idx)].max())
                if len(member_idx) > 1
                else 0.0
            )
            rows.append(
                {
                    "user_id": user_id,
                    "_reference_location_id": int(location_id),
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

    clustered = pd.concat(clustered_parts, ignore_index=True)
    locations = pd.DataFrame(rows)
    return clustered, locations


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


def _window_rows(
    clustered: pd.DataFrame,
    *,
    config: HomeOfficeConfig,
    kind: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for row in clustered.itertuples(index=False):
        start = row.arrival_time_local
        end = row.departure_time_local
        day = start.normalize() - pd.Timedelta(days=1)
        last_day = end.normalize()

        while day <= last_day:
            if kind == "HOME":
                window_start = day + pd.Timedelta(
                    hours=config.home_start_hour
                )
                window_end = (
                    day
                    + pd.Timedelta(days=1)
                    + pd.Timedelta(hours=config.home_end_hour)
                )
                include = True
            elif kind == "OFFICE":
                window_start = day + pd.Timedelta(
                    hours=config.office_start_hour
                )
                window_end = day + pd.Timedelta(
                    hours=config.office_end_hour
                )
                include = day.weekday() in config.office_weekdays
            else:
                raise ValueError(kind)

            if include:
                overlap_s = _interval_overlap_s(
                    start,
                    end,
                    window_start,
                    window_end,
                )
                if overlap_s > 0:
                    rows.append(
                        {
                            "user_id": row.user_id,
                            "_reference_location_id": int(
                                row._reference_location_id
                            ),
                            "behavior_date": window_start.date(),
                            "overlap_s": overlap_s,
                        }
                    )
            day += pd.Timedelta(days=1)

    return pd.DataFrame(
        rows,
        columns=[
            "user_id",
            "_reference_location_id",
            "behavior_date",
            "overlap_s",
        ],
    )


def _aggregate_reference(
    contrib: pd.DataFrame,
    *,
    prefix: str,
    config: HomeOfficeConfig,
) -> pd.DataFrame:
    dwell_col = f"{prefix}_dwell_s"
    dates_col = f"{prefix}_dates"
    keys = ["user_id", "_reference_location_id"]
    if contrib.empty:
        return pd.DataFrame(columns=[*keys, dwell_col, dates_col])

    per_date = (
        contrib.groupby([*keys, "behavior_date"], as_index=False)["overlap_s"]
        .sum()
    )
    dwell = (
        per_date.groupby(keys, as_index=False)["overlap_s"]
        .sum()
        .rename(columns={"overlap_s": dwell_col})
    )
    dates = (
        per_date.loc[
            per_date["overlap_s"] >= config.min_relevant_date_overlap_s
        ]
        .groupby(keys, as_index=False)["behavior_date"]
        .nunique()
        .rename(columns={"behavior_date": dates_col})
    )
    return dwell.merge(dates, on=keys, how="left").fillna(
        {dates_col: 0}
    )


def reference_infer(
    clustered: pd.DataFrame,
    locations: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
) -> pd.DataFrame:
    """Independently apply the frozen behavioral windows and emission gates."""
    cfg = config or HomeOfficeConfig()
    keys = ["user_id", "_reference_location_id"]
    home = _aggregate_reference(
        _window_rows(clustered, config=cfg, kind="HOME"),
        prefix="home",
        config=cfg,
    )
    office = _aggregate_reference(
        _window_rows(clustered, config=cfg, kind="OFFICE"),
        prefix="office",
        config=cfg,
    )
    features = (
        locations.merge(home, on=keys, how="left")
        .merge(office, on=keys, how="left")
    )
    for col in ["home_dwell_s", "office_dwell_s"]:
        features[col] = pd.to_numeric(
            features[col], errors="coerce"
        ).fillna(0.0)
    for col in ["home_dates", "office_dates"]:
        features[col] = pd.to_numeric(
            features[col], errors="coerce"
        ).fillna(0).astype(int)

    for prefix in ["home", "office"]:
        dwell_col = f"{prefix}_dwell_s"
        total = features.groupby("user_id")[dwell_col].transform("sum")
        share = np.zeros(len(features), dtype=float)
        np.divide(
            features[dwell_col].to_numpy(float),
            total.to_numpy(float),
            out=share,
            where=total.to_numpy(float) > 0,
        )
        features[f"{prefix}_dwell_share"] = share

    emitted_parts: list[pd.DataFrame] = []
    specs = [
        (
            "HOME",
            "home",
            cfg.home_min_dates,
            cfg.home_min_share,
            cfg.home_min_margin,
        ),
        (
            "OFFICE",
            "office",
            cfg.office_min_dates,
            cfg.office_min_share,
            cfg.office_min_margin,
        ),
    ]
    for label, prefix, min_dates, min_share, min_margin in specs:
        dwell_col = f"{prefix}_dwell_s"
        dates_col = f"{prefix}_dates"
        share_col = f"{prefix}_dwell_share"
        eligible = features.loc[
            (features["stay_count"] >= 2)
            & (features[dates_col] >= min_dates)
            & (features[dwell_col] > 0)
        ].copy()
        if eligible.empty:
            continue
        eligible = eligible.sort_values(
            [
                "user_id",
                share_col,
                dates_col,
                dwell_col,
                "stay_count",
                "_reference_location_id",
            ],
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
        top = top.loc[
            (top["relevant_dwell_share"] >= min_share)
            & (top["share_margin"] >= min_margin)
        ].copy()
        if top.empty:
            continue
        support = np.minimum(
            top["relevant_dates"].to_numpy(float)
            / float(cfg.support_saturation_dates),
            1.0,
        )
        top["evidence_strength"] = (
            top["relevant_dwell_share"].to_numpy(float)
            + top["share_margin"].to_numpy(float)
            + support
        ) / 3.0
        top["label"] = label
        emitted_parts.append(top)

    if not emitted_parts:
        return pd.DataFrame(
            columns=[
                "user_id",
                "label",
                "_reference_location_id",
                "latitude",
                "longitude",
                "evidence_strength",
                "relevant_dwell_share",
                "share_margin",
                "relevant_dates",
                "relevant_dwell_h",
            ]
        )
    return pd.concat(emitted_parts, ignore_index=True)


def _with_duplicate_rank(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["_duplicate_rank"] = out.groupby(
        SOURCE_KEY_COLUMNS,
        sort=False,
        dropna=False,
    ).cumcount()
    return out


def compare_local_time_semantics(
    production_semantic: pd.DataFrame,
    reference_resolved: pd.DataFrame,
) -> dict[str, object]:
    prod = _with_duplicate_rank(production_semantic)
    ref = _with_duplicate_rank(reference_resolved)
    keys = [*SOURCE_KEY_COLUMNS, "_duplicate_rank"]
    merged = prod.merge(
        ref[
            [
                *keys,
                "timezone_id",
                "arrival_time_local",
                "departure_time_local",
            ]
        ],
        on=keys,
        how="outer",
        suffixes=("_production", "_reference"),
        indicator=True,
    )
    both = merged["_merge"].eq("both")
    timezone_equal = (
        merged.loc[both, "timezone_id_production"].astype("string").to_numpy()
        == merged.loc[both, "timezone_id_reference"].astype("string").to_numpy()
    )
    arrival_equal = (
        merged.loc[both, "arrival_time_local_production"].to_numpy()
        == merged.loc[both, "arrival_time_local_reference"].to_numpy()
    )
    departure_equal = (
        merged.loc[both, "departure_time_local_production"].to_numpy()
        == merged.loc[both, "departure_time_local_reference"].to_numpy()
    )
    return {
        "production_rows": int(len(prod)),
        "reference_rows": int(len(ref)),
        "matched_rows": int(both.sum()),
        "timezone_exact_rows": int(np.asarray(timezone_equal).sum()),
        "arrival_local_exact_rows": int(np.asarray(arrival_equal).sum()),
        "departure_local_exact_rows": int(
            np.asarray(departure_equal).sum()
        ),
        "unmatched_rows": int((~both).sum()),
    }


def _location_signature(row) -> tuple[object, ...]:
    return (
        str(row.user_id),
        round(float(row.latitude), 7),
        round(float(row.longitude), 7),
        int(row.stay_count),
        int(row.active_local_dates),
        round(float(row.total_dwell_h), 6),
        round(float(row.diameter_m), 6),
    )


def compare_location_partitions(
    production_locations: pd.DataFrame,
    reference_locations: pd.DataFrame,
) -> dict[str, object]:
    prod = Counter(
        _location_signature(row)
        for row in production_locations.itertuples(index=False)
    )
    ref = Counter(
        _location_signature(row)
        for row in reference_locations.itertuples(index=False)
    )
    missing = ref - prod
    extra = prod - ref
    return {
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
        "missing_reference_signatures": int(sum(missing.values())),
        "extra_production_signatures": int(sum(extra.values())),
    }


def _emission_signature(row) -> tuple[object, ...]:
    return (
        str(row.user_id),
        str(row.label),
        round(float(row.latitude), 7),
        round(float(row.longitude), 7),
        round(float(row.evidence_strength), 9),
        round(float(row.relevant_dwell_share), 9),
        round(float(row.share_margin), 9),
        int(row.relevant_dates),
        round(float(row.relevant_dwell_h), 6),
    )


def compare_emissions(
    production: pd.DataFrame,
    reference: pd.DataFrame,
) -> dict[str, object]:
    prod = Counter(
        _emission_signature(row)
        for row in production.itertuples(index=False)
    )
    ref = Counter(
        _emission_signature(row)
        for row in reference.itertuples(index=False)
    )
    missing = ref - prod
    extra = prod - ref

    def counts(frame: pd.DataFrame) -> dict[str, int]:
        value = frame["label"].value_counts() if not frame.empty else pd.Series()
        return {
            "HOME": int(value.get("HOME", 0)),
            "OFFICE": int(value.get("OFFICE", 0)),
        }

    return {
        "production_counts": counts(production),
        "reference_counts": counts(reference),
        "production_unique_users": int(
            production["user_id"].nunique() if not production.empty else 0
        ),
        "reference_unique_users": int(
            reference["user_id"].nunique() if not reference.empty else 0
        ),
        "missing_reference_emissions": int(sum(missing.values())),
        "extra_production_emissions": int(sum(extra.values())),
    }


def run_migration_comparison(stays: pd.DataFrame) -> dict[str, object]:
    """Compare production CP2 v2 against the independent Notebook-03 reference."""
    validated = _validate_reference_stays(stays)
    production_semantic, production_locations = build_semantic_locations(
        validated
    )
    production_emitted = infer_home_office(validated)

    reference_resolved = reference_resolve_timezones(validated)
    reference_clustered, reference_locations = reference_complete_link(
        reference_resolved,
        threshold_m=HomeOfficeConfig().location_max_diameter_m,
    )
    reference_emitted = reference_infer(
        reference_clustered,
        reference_locations,
    )

    local = compare_local_time_semantics(
        production_semantic,
        reference_resolved,
    )
    locations = compare_location_partitions(
        production_locations,
        reference_locations,
    )
    emissions = compare_emissions(
        production_emitted,
        reference_emitted,
    )

    resolved_all = (
        len(reference_resolved) == len(validated)
        and reference_resolved["timezone_id"].notna().all()
    )
    local_pass = (
        local["unmatched_rows"] == 0
        and local["timezone_exact_rows"] == len(validated)
        and local["arrival_local_exact_rows"] == len(validated)
        and local["departure_local_exact_rows"] == len(validated)
    )
    cluster_pass = (
        locations["missing_reference_signatures"] == 0
        and locations["extra_production_signatures"] == 0
    )
    emission_pass = (
        emissions["missing_reference_emissions"] == 0
        and emissions["extra_production_emissions"] == 0
    )

    cp1_status = (
        "pass_frozen_cp1"
        if (
            len(validated) == EXPECTED_CP1_STAYS
            and validated["user_id"].nunique() == EXPECTED_CP1_STAY_USERS
        )
        else "blocked_cp1_input"
    )
    decision = MigrationDecision(
        cp1_input_status=cp1_status,
        timezone_resolution_status=(
            "pass_all_stays_resolved"
            if resolved_all
            else "blocked_unresolved_timezone"
        ),
        local_time_parity_status=(
            "pass_exact_local_time_parity"
            if local_pass
            else "blocked_local_time_parity"
        ),
        cluster_parity_status=(
            "pass_cluster_signature_parity"
            if cluster_pass
            else "blocked_cluster_parity"
        ),
        emission_parity_status=(
            "pass_emission_evidence_parity"
            if emission_pass
            else "blocked_emission_parity"
        ),
        runner_status="",
    )
    hard = [
        decision.cp1_input_status,
        decision.timezone_resolution_status,
        decision.local_time_parity_status,
        decision.cluster_parity_status,
        decision.emission_parity_status,
    ]
    decision = MigrationDecision(
        **{
            **decision.__dict__,
            "runner_status": (
                "ready_for_cp2_v2_review"
                if all(value.startswith("pass_") for value in hard)
                else "blocked"
            ),
        }
    )

    timezone_counts = (
        reference_resolved["timezone_id"].value_counts().to_dict()
    )
    return {
        "decision": decision.__dict__,
        "location_namespace": LOCATION_NAMESPACE,
        "cp1_stays": int(len(validated)),
        "cp1_stay_users": int(validated["user_id"].nunique()),
        "timezone_resolved_stays": int(len(reference_resolved)),
        "timezone_resolved_users": int(
            reference_resolved["user_id"].nunique()
        ),
        "distinct_timezones": int(
            reference_resolved["timezone_id"].nunique()
        ),
        "timezone_counts": {
            str(key): int(value)
            for key, value in timezone_counts.items()
        },
        "local_time_parity": local,
        "location_parity": locations,
        "emission_parity": emissions,
        "historical_v1": {
            "semantic_users": 97,
            "semantic_locations": 1_111,
            "recurring_locations": 486,
            "recurring_users": 73,
            "HOME": 27,
            "OFFICE": 16,
        },
    }


def synthetic_self_check() -> dict[str, object]:
    arrival_shanghai = pd.Timestamp(
        "2026-01-05 21:00",
        tz="Asia/Shanghai",
    ).tz_convert("UTC")
    arrival_tokyo = pd.Timestamp(
        "2026-01-06 21:00",
        tz="Asia/Tokyo",
    ).tz_convert("UTC")
    frame = pd.DataFrame(
        [
            {
                "user_id": "u",
                "arrival_time_utc": arrival_shanghai,
                "departure_time_utc": arrival_shanghai
                + pd.Timedelta(hours=1),
                "duration_s": 3600.0,
                "latitude": 39.9042,
                "longitude": 116.4074,
            },
            {
                "user_id": "u",
                "arrival_time_utc": arrival_tokyo,
                "departure_time_utc": arrival_tokyo
                + pd.Timedelta(hours=1),
                "duration_s": 3600.0,
                "latitude": 35.6762,
                "longitude": 139.6503,
            },
        ]
    )
    resolved = reference_resolve_timezones(frame)
    assert len(resolved) == 2
    assert set(resolved["timezone_id"]) == {
        "Asia/Shanghai",
        "Asia/Tokyo",
    }
    assert resolved["arrival_time_local"].dt.hour.tolist() == [21, 21]
    return {"status": "ok", "location_namespace": LOCATION_NAMESPACE}
