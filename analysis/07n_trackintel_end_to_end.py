"""Stage 07n: end-to-end Trackintel pipeline comparator.

The helper keeps Trackintel itself out of the repository test dependency graph.
The notebook installs Trackintel 1.4.2 and performs raw GeoLife -> staypoints ->
DBSCAN locations -> OSNA. This module only provides normalization, matching,
and aggregate comparison utilities.

No result from this stage is a production retuning signal.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from geolife.geo.distance import haversine_m


def canonical_user_id(value: object) -> str:
    text = str(value)
    try:
        return f"{int(text):03d}"
    except ValueError:
        return text


def canonicalize_user_column(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["user_id"] = out["user_id"].map(canonical_user_id)
    return out


def _local_wall_dummy_utc(timestamp: object, timezone_id: str) -> pd.Timestamp:
    ts = pd.Timestamp(timestamp)
    if ts.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware")
    local = ts.tz_convert(str(timezone_id))
    return local.tz_localize(None).tz_localize("UTC")


def adapt_trackintel_stays_to_local_wall(
    staypoints: pd.DataFrame,
    timezone_ids: pd.Series,
) -> pd.DataFrame:
    """Return a local-wall-clock semantic copy of Trackintel staypoints.

    timezone_ids must align to staypoints.index. started_at is converted from
    physical UTC to the stay's local wall clock and re-encoded as dummy UTC.
    finished_at preserves true elapsed duration.
    """

    required = {"user_id", "started_at", "finished_at", "location_id"}
    missing = required.difference(staypoints.columns)
    if missing:
        raise ValueError(f"missing Trackintel stay columns: {sorted(missing)}")
    if not timezone_ids.index.equals(staypoints.index):
        timezone_ids = timezone_ids.reindex(staypoints.index)
    if timezone_ids.isna().any():
        raise ValueError("timezone_ids contains missing values")

    out = staypoints.copy()
    starts = pd.to_datetime(out["started_at"], utc=True)
    finishes = pd.to_datetime(out["finished_at"], utc=True)
    duration = finishes - starts

    encoded_start = pd.DatetimeIndex(
        [
            _local_wall_dummy_utc(ts, tzid)
            for ts, tzid in zip(starts, timezone_ids.astype(str), strict=True)
        ]
    )
    out["started_at"] = encoded_start
    out["finished_at"] = encoded_start + duration
    out["timezone_id"] = timezone_ids.astype(str).to_numpy()
    out["elapsed_s"] = duration.dt.total_seconds().to_numpy(dtype=float)
    return out


def staypoint_table_for_matching(trackintel_stays: pd.DataFrame) -> pd.DataFrame:
    """Normalize Trackintel staypoints to the comparison schema."""

    out = canonicalize_user_column(trackintel_stays)
    if "latitude" not in out.columns or "longitude" not in out.columns:
        if not hasattr(out, "geometry"):
            raise ValueError("Trackintel stays require latitude/longitude or geometry")
        out["longitude"] = out.geometry.x.astype(float)
        out["latitude"] = out.geometry.y.astype(float)

    result = pd.DataFrame(
        {
            "user_id": out["user_id"].astype(str),
            "start": pd.to_datetime(out["started_at"], utc=True),
            "end": pd.to_datetime(out["finished_at"], utc=True),
            "latitude": pd.to_numeric(out["latitude"], errors="raise"),
            "longitude": pd.to_numeric(out["longitude"], errors="raise"),
        },
        index=out.index,
    )
    return result.reset_index(drop=True)


def production_stay_table(stays: pd.DataFrame) -> pd.DataFrame:
    required = {
        "user_id",
        "arrival_time_utc",
        "departure_time_utc",
        "latitude",
        "longitude",
    }
    missing = required.difference(stays.columns)
    if missing:
        raise ValueError(f"missing CP1 stay columns: {sorted(missing)}")
    out = canonicalize_user_column(stays)
    return pd.DataFrame(
        {
            "user_id": out["user_id"].astype(str),
            "start": pd.to_datetime(out["arrival_time_utc"], utc=True),
            "end": pd.to_datetime(out["departure_time_utc"], utc=True),
            "latitude": pd.to_numeric(out["latitude"], errors="raise"),
            "longitude": pd.to_numeric(out["longitude"], errors="raise"),
        }
    ).reset_index(drop=True)


def _best_overlap_for_source(
    source: pd.DataFrame,
    target: pd.DataFrame,
    source_name: str,
) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    target_by_user = {u: g.reset_index(drop=True) for u, g in target.groupby("user_id")}

    for idx, row in source.reset_index(drop=True).iterrows():
        candidates = target_by_user.get(row["user_id"])
        base = {
            "source": source_name,
            "source_index": int(idx),
            "user_id": row["user_id"],
        }
        if candidates is None or candidates.empty:
            rows.append(
                {
                    **base,
                    "matched_target_index": np.nan,
                    "overlap_s": 0.0,
                    "overlap_over_shorter": 0.0,
                    "center_distance_m": np.nan,
                }
            )
            continue

        overlap_start = candidates["start"].map(lambda value: max(value, row["start"]))
        overlap_end = candidates["end"].map(lambda value: min(value, row["end"]))
        overlap_s = (overlap_end - overlap_start).dt.total_seconds().clip(lower=0.0)
        best_pos = int(overlap_s.to_numpy().argmax())
        best_overlap = float(overlap_s.iloc[best_pos])

        if best_overlap <= 0:
            rows.append(
                {
                    **base,
                    "matched_target_index": np.nan,
                    "overlap_s": 0.0,
                    "overlap_over_shorter": 0.0,
                    "center_distance_m": np.nan,
                }
            )
            continue

        target_row = candidates.iloc[best_pos]
        source_dur = max((row["end"] - row["start"]).total_seconds(), 0.0)
        target_dur = max((target_row["end"] - target_row["start"]).total_seconds(), 0.0)
        shorter = min(source_dur, target_dur)
        ratio = best_overlap / shorter if shorter > 0 else 0.0
        distance = float(
            haversine_m(
                float(row["latitude"]),
                float(row["longitude"]),
                float(target_row["latitude"]),
                float(target_row["longitude"]),
            )
        )
        rows.append(
            {
                **base,
                "matched_target_index": best_pos,
                "overlap_s": best_overlap,
                "overlap_over_shorter": ratio,
                "center_distance_m": distance,
            }
        )
    return pd.DataFrame(rows)


def compare_stay_inventories(
    production_stays: pd.DataFrame,
    trackintel_stays: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    prod = production_stay_table(production_stays)
    ti = staypoint_table_for_matching(trackintel_stays)

    forward = _best_overlap_for_source(prod, ti, "CP1")
    reverse = _best_overlap_for_source(ti, prod, "TRACKINTEL")
    details = pd.concat([forward, reverse], ignore_index=True)

    rows: list[dict[str, object]] = []
    for source_name, group in details.groupby("source", sort=True):
        overlap = pd.to_numeric(group["overlap_s"], errors="coerce").fillna(0)
        ratio = pd.to_numeric(group["overlap_over_shorter"], errors="coerce").fillna(0)
        dist = pd.to_numeric(group["center_distance_m"], errors="coerce")
        rows.append(
            {
                "source_inventory": source_name,
                "stays": int(len(group)),
                "temporal_overlap_any": int(overlap.gt(0).sum()),
                "temporal_overlap_rate": float(overlap.gt(0).mean()) if len(group) else np.nan,
                "overlap_and_within_200m": int((overlap.gt(0) & dist.le(200)).sum()),
                "overlap_and_within_200m_rate": float(
                    (overlap.gt(0) & dist.le(200)).mean()
                )
                if len(group)
                else np.nan,
                "strong_match_50pct_and_200m": int((ratio.ge(0.5) & dist.le(200)).sum()),
                "strong_match_rate": float((ratio.ge(0.5) & dist.le(200)).mean())
                if len(group)
                else np.nan,
            }
        )
    return details, pd.DataFrame(rows)


def trackintel_location_table(
    staypoints: pd.DataFrame,
    locations: pd.DataFrame,
    variant: str,
) -> pd.DataFrame:
    sp = canonicalize_user_column(staypoints)
    loc = canonicalize_user_column(locations).copy()
    loc["_location_index"] = loc.index

    counts = (
        sp.groupby(["user_id", "location_id"], as_index=False)
        .size()
        .rename(columns={"size": "stay_count"})
    )

    center = loc.geometry if hasattr(loc, "geometry") else loc["center"]
    location_ids = loc["location_id"] if "location_id" in loc.columns else loc["_location_index"]
    out = pd.DataFrame(
        {
            "user_id": loc["user_id"].astype(str).to_numpy(),
            "location_id": pd.to_numeric(location_ids, errors="raise").to_numpy(),
            "longitude": center.x.astype(float).to_numpy(),
            "latitude": center.y.astype(float).to_numpy(),
        }
    )
    out["location_id"] = out["location_id"].astype(int)
    out = out.merge(counts, on=["user_id", "location_id"], how="left")
    out["stay_count"] = out["stay_count"].fillna(0).astype(int)
    out["variant"] = str(variant)
    return out


def production_location_table(locations: pd.DataFrame) -> pd.DataFrame:
    required = {"user_id", "location_id", "latitude", "longitude", "stay_count"}
    missing = required.difference(locations.columns)
    if missing:
        raise ValueError(f"missing production location columns: {sorted(missing)}")
    out = canonicalize_user_column(locations)
    out = out[list(required)].copy()
    out["location_id"] = pd.to_numeric(out["location_id"], errors="raise").astype(int)
    out["stay_count"] = pd.to_numeric(out["stay_count"], errors="raise").astype(int)
    return out


def nearest_location_matches(
    production_locations: pd.DataFrame,
    trackintel_locations: pd.DataFrame,
) -> pd.DataFrame:
    prod = production_location_table(production_locations)
    ti = canonicalize_user_column(trackintel_locations)

    rows: list[dict[str, object]] = []
    ti_groups = {u: g.reset_index(drop=True) for u, g in ti.groupby("user_id")}
    for row in prod.itertuples(index=False):
        group = ti_groups.get(str(row.user_id))
        if group is None or group.empty:
            rows.append(
                {
                    "user_id": str(row.user_id),
                    "production_location_id": int(row.location_id),
                    "production_stay_count": int(row.stay_count),
                    "nearest_trackintel_location_id": np.nan,
                    "trackintel_stay_count": np.nan,
                    "distance_m": np.nan,
                }
            )
            continue
        distances = np.asarray(
            haversine_m(
                float(row.latitude),
                float(row.longitude),
                group["latitude"].to_numpy(dtype=float),
                group["longitude"].to_numpy(dtype=float),
            ),
            dtype=float,
        )
        pos = int(np.argmin(distances))
        chosen = group.iloc[pos]
        rows.append(
            {
                "user_id": str(row.user_id),
                "production_location_id": int(row.location_id),
                "production_stay_count": int(row.stay_count),
                "nearest_trackintel_location_id": int(chosen["location_id"]),
                "trackintel_stay_count": int(chosen["stay_count"]),
                "distance_m": float(distances[pos]),
            }
        )
    return pd.DataFrame(rows)


def summarize_location_geometry(matches: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for name, group in [
        ("all_production_locations", matches),
        ("recurring_production_locations", matches.loc[matches["production_stay_count"].ge(2)]),
    ]:
        dist = pd.to_numeric(group["distance_m"], errors="coerce")
        rows.append(
            {
                "scope": name,
                "production_locations": int(len(group)),
                "matched_any": int(dist.notna().sum()),
                "within_50m": int(dist.le(50).sum()),
                "within_100m": int(dist.le(100).sum()),
                "within_200m": int(dist.le(200).sum()),
                "median_distance_m": float(dist.median()) if dist.notna().any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def extract_osna_candidates(
    labeled_staypoints: pd.DataFrame,
    location_table: pd.DataFrame,
    variant: str,
) -> pd.DataFrame:
    required = {"user_id", "location_id", "purpose"}
    missing = required.difference(labeled_staypoints.columns)
    if missing:
        raise ValueError(f"missing OSNA output columns: {sorted(missing)}")

    frame = canonicalize_user_column(labeled_staypoints)
    frame["purpose"] = frame["purpose"].astype("string").str.lower()
    frame = frame.loc[frame["purpose"].isin(["home", "work"])].copy()
    frame["label"] = frame["purpose"].map({"home": "HOME", "work": "OFFICE"})

    candidates = frame[["user_id", "label", "location_id"]].drop_duplicates()
    counts = candidates.groupby(["user_id", "label"])["location_id"].nunique()
    if counts.gt(1).any():
        raise RuntimeError("OSNA produced multiple location identities for one user/label")

    loc = canonicalize_user_column(location_table)
    out = candidates.merge(
        loc[["user_id", "location_id", "latitude", "longitude"]],
        on=["user_id", "location_id"],
        how="left",
        validate="many_to_one",
    )
    if out[["latitude", "longitude"]].isna().any().any():
        raise RuntimeError("OSNA candidate did not join to Trackintel location center")
    out["variant"] = str(variant)
    return out[["variant", "user_id", "label", "location_id", "latitude", "longitude"]]


def production_candidate_table(production_output: pd.DataFrame) -> pd.DataFrame:
    required = {"user_id", "label", "location_id", "latitude", "longitude"}
    missing = required.difference(production_output.columns)
    if missing:
        raise ValueError(f"missing production candidate columns: {sorted(missing)}")
    out = canonicalize_user_column(production_output)
    out["label"] = out["label"].astype(str).str.upper()
    return out[list(required)].copy()


def compare_semantic_candidates(
    universe_users: list[str] | pd.Series,
    production_output: pd.DataFrame,
    comparator_candidates: pd.DataFrame,
    variant: str,
) -> pd.DataFrame:
    users = sorted({canonical_user_id(v) for v in universe_users})
    prod = production_candidate_table(production_output).rename(
        columns={
            "location_id": "production_location_id",
            "latitude": "production_latitude",
            "longitude": "production_longitude",
        }
    )
    comp = canonicalize_user_column(
        comparator_candidates.loc[comparator_candidates["variant"].eq(variant)].copy()
    ).rename(
        columns={
            "location_id": "trackintel_location_id",
            "latitude": "trackintel_latitude",
            "longitude": "trackintel_longitude",
        }
    )

    base = pd.MultiIndex.from_product(
        [users, ["HOME", "OFFICE"]], names=["user_id", "label"]
    ).to_frame(index=False)
    out = base.merge(prod, on=["user_id", "label"], how="left").merge(
        comp[
            [
                "user_id",
                "label",
                "trackintel_location_id",
                "trackintel_latitude",
                "trackintel_longitude",
            ]
        ],
        on=["user_id", "label"],
        how="left",
    )
    out["production_emitted"] = out["production_location_id"].notna()
    out["trackintel_selected"] = out["trackintel_location_id"].notna()

    distance = np.full(len(out), np.nan, dtype=float)
    mask = out["production_emitted"] & out["trackintel_selected"]
    if mask.any():
        distance[mask.to_numpy()] = haversine_m(
            out.loc[mask, "production_latitude"].to_numpy(dtype=float),
            out.loc[mask, "production_longitude"].to_numpy(dtype=float),
            out.loc[mask, "trackintel_latitude"].to_numpy(dtype=float),
            out.loc[mask, "trackintel_longitude"].to_numpy(dtype=float),
        )
    out["candidate_distance_m"] = distance

    out["status"] = "neither"
    out.loc[out["production_emitted"] & ~out["trackintel_selected"], "status"] = "production_only"
    out.loc[~out["production_emitted"] & out["trackintel_selected"], "status"] = "trackintel_only"
    both = out["production_emitted"] & out["trackintel_selected"]
    out.loc[both, "status"] = ">200m"
    out.loc[both & out["candidate_distance_m"].le(200), "status"] = "within_200m"
    out.loc[both & out["candidate_distance_m"].le(100), "status"] = "within_100m"
    out.loc[both & out["candidate_distance_m"].le(50), "status"] = "within_50m"
    out["variant"] = str(variant)
    return out


def summarize_semantic_candidates(comparison: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (variant, label), group in comparison.groupby(["variant", "label"], sort=True):
        both = group["production_emitted"] & group["trackintel_selected"]
        dist = pd.to_numeric(group["candidate_distance_m"], errors="coerce")
        rows.append(
            {
                "variant": variant,
                "label": label,
                "universe_users": int(group["user_id"].nunique()),
                "production_emitted": int(group["production_emitted"].sum()),
                "trackintel_selected": int(group["trackintel_selected"].sum()),
                "both_selected": int(both.sum()),
                "within_50m": int(dist.le(50).sum()),
                "within_100m": int(dist.le(100).sum()),
                "within_200m": int(dist.le(200).sum()),
                "median_distance_m_joint": float(dist.median()) if dist.notna().any() else np.nan,
            }
        )
    return pd.DataFrame(rows)


def synthetic_self_check() -> dict[str, object]:
    assert canonical_user_id("7") == "007"
    assert canonical_user_id(42) == "042"

    cp1 = pd.DataFrame(
        {
            "user_id": ["001"],
            "arrival_time_utc": [pd.Timestamp("2026-01-01T00:00:00Z")],
            "departure_time_utc": [pd.Timestamp("2026-01-01T01:00:00Z")],
            "latitude": [39.9],
            "longitude": [116.4],
        }
    )
    ti = pd.DataFrame(
        {
            "user_id": [1],
            "started_at": [pd.Timestamp("2026-01-01T00:10:00Z")],
            "finished_at": [pd.Timestamp("2026-01-01T00:50:00Z")],
            "latitude": [39.9001],
            "longitude": [116.4001],
        }
    )
    details, summary = compare_stay_inventories(cp1, ti)
    assert len(details) == 2
    assert summary["strong_match_50pct_and_200m"].sum() == 2

    return {"status": "ok", "detail_rows": int(len(details))}
