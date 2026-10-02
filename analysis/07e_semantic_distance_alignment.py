"""Stage 07e: offline semantic-distance + mobility-alignment audit.

Consumes Stage-07d cached historical OSM Parquet responses. No API calls.

Goals:
- measure anchor-to-historical-feature distance by semantic category;
- keep OSM absence as mapping absence, not real-world absence;
- compare the exact Stage-05b stable-secondary anchor to other recurring
  non-HOME anchors from the same user;
- integrate user-level Stage-07b mobility axes without collapsing them into
  occupation or WORK/OFFICE labels.

This stage is research-only.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
import math
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
import pandas as pd


DISTANCE_THRESHOLDS_M = (25.0, 50.0, 100.0)
DISTANCE_BUCKETS = ("0_25", "25_50", "50_100", "none_within_100")

PROFILE_AXES = (
    "site_stable_secondary",
    "site_multiple_recurring",
    "site_adaptive_multi_anchor",
    "route_repeated",
    "schedule_shifted_evidence",
    "mobile_complexity_evidence",
    "independent_secondary_evidence_available",
)


@dataclass(frozen=True)
class SemanticDistanceAudit:
    feature_distances: pd.DataFrame
    anchor_metrics: pd.DataFrame
    aligned_anchors: pd.DataFrame
    distance_bucket_summary: pd.DataFrame
    category_threshold_summary: pd.DataFrame
    stable_secondary_user_comparisons: pd.DataFrame
    stable_secondary_summary: pd.DataFrame
    profile_axis_context_summary: pd.DataFrame


def _load_stage07d():
    path = Path(__file__).with_name("07d_historical_context_enrichment.py")
    spec = spec_from_file_location("stage07d_for_07e", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load Stage 07d from {path}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STAGE07D = _load_stage07d()
CONTEXT_CATEGORIES = tuple(STAGE07D.CONTEXT_CATEGORIES)
WORK_COMPATIBLE_CATEGORIES = frozenset(STAGE07D.WORK_COMPATIBLE_CATEGORIES)


def _normalise_anchor_keys(frame: pd.DataFrame) -> pd.DataFrame:
    required = {"user_id", "location_id"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"missing anchor keys: {sorted(missing)}")
    out = frame.copy()
    out["user_id"] = out["user_id"].astype(str)
    out["location_id"] = pd.to_numeric(
        out["location_id"], errors="raise"
    ).astype(int)
    return out


def validate_full_ohsome_cache(
    anchors: pd.DataFrame,
    request_log: pd.DataFrame,
    raw_cache_dir: Path,
) -> pd.DataFrame:
    """Validate one successful cached response per target anchor.

    The final Stage-07d run logs every anchor as cached/fetched. This check
    prevents a partial historical-OSM run from silently entering Stage 07e.
    """
    anchors = _normalise_anchor_keys(anchors)
    log = _normalise_anchor_keys(request_log)

    required = {"cache_key", "status"}
    missing = required.difference(log.columns)
    if missing:
        raise ValueError(f"request log missing columns: {sorted(missing)}")

    ok = log.loc[log["status"].isin(["cached", "fetched"])].copy()
    if ok.duplicated(["user_id", "location_id"]).any():
        raise ValueError("request log contains duplicate successful anchor rows")

    mapping = anchors[["user_id", "location_id"]].merge(
        ok[["user_id", "location_id", "cache_key", "status"]],
        on=["user_id", "location_id"],
        how="left",
        validate="one_to_one",
    )
    if mapping["cache_key"].isna().any():
        missing_count = int(mapping["cache_key"].isna().sum())
        raise ValueError(
            f"ohsome cache is incomplete: {missing_count} target anchors missing"
        )

    mapping["cache_path"] = mapping["cache_key"].map(
        lambda key: raw_cache_dir / f"{key}.parquet"
    )
    exists = mapping["cache_path"].map(Path.exists)
    if not exists.all():
        raise FileNotFoundError(
            f"ohsome raw cache missing {int((~exists).sum())} parquet files"
        )
    return mapping


def _bbox_to_dict(value) -> dict[str, float] | None:
    if value is None:
        return None
    if isinstance(value, dict):
        try:
            return {
                name: float(value[name])
                for name in ("xmin", "xmax", "ymin", "ymax")
            }
        except Exception:
            return None
    if hasattr(value, "as_py"):
        return _bbox_to_dict(value.as_py())
    try:
        raw = dict(value)
    except Exception:
        return None
    return _bbox_to_dict(raw)


def _local_xy_transform(anchor_lat: float, anchor_lon: float):
    """Return a short-range WGS84 -> local metre transform.

    All Stage-07d extracts use a ~100 m anchor-centred AOI. A local
    equirectangular transform is therefore sufficient for the distance audit
    and avoids imposing a single projected CRS across all users.
    """
    cos_lat = max(math.cos(math.radians(anchor_lat)), 1e-8)
    scale_x = 111_320.0 * cos_lat
    scale_y = 110_574.0

    def transform(x, y, z=None):
        return (np.asarray(x) - anchor_lon) * scale_x, (
            np.asarray(y) - anchor_lat
        ) * scale_y

    return transform


def _bbox_distance_m(
    bbox,
    *,
    anchor_lat: float,
    anchor_lon: float,
) -> float:
    parsed = _bbox_to_dict(bbox)
    if parsed is None:
        return np.nan

    closest_lon = min(max(anchor_lon, parsed["xmin"]), parsed["xmax"])
    closest_lat = min(max(anchor_lat, parsed["ymin"]), parsed["ymax"])
    dx = (
        (closest_lon - anchor_lon)
        * 111_320.0
        * max(math.cos(math.radians(anchor_lat)), 1e-8)
    )
    dy = (closest_lat - anchor_lat) * 110_574.0
    return float(math.hypot(dx, dy))


def geometry_distance_m(
    geom_wkb,
    *,
    anchor_lat: float,
    anchor_lon: float,
    bbox=None,
) -> tuple[float, str]:
    """Distance from anchor to WKB geometry, with bbox fallback."""
    if geom_wkb is not None:
        try:
            from shapely import from_wkb
            from shapely.geometry import Point
            from shapely.ops import transform as shapely_transform

            geometry = from_wkb(bytes(geom_wkb))
            if geometry is not None and not geometry.is_empty:
                projected = shapely_transform(
                    _local_xy_transform(anchor_lat, anchor_lon),
                    geometry,
                )
                distance = float(projected.distance(Point(0.0, 0.0)))
                if np.isfinite(distance):
                    return distance, "geometry"
        except Exception:
            pass

    fallback = _bbox_distance_m(
        bbox,
        anchor_lat=anchor_lat,
        anchor_lon=anchor_lon,
    )
    return fallback, "bbox_fallback" if np.isfinite(fallback) else "unavailable"


def extract_anchor_feature_distances(
    anchor: pd.Series | dict,
    parquet_content: bytes,
) -> pd.DataFrame:
    """Normalise one cached ohsome extract to feature-category distance rows."""
    row = dict(anchor)
    anchor_lat = float(row["latitude"])
    anchor_lon = float(row["longitude"])
    features = STAGE07D.parse_ohsome_parquet(parquet_content)

    rows = []
    for feature in features.itertuples(index=False):
        categories = tuple(getattr(feature, "categories", tuple()) or tuple())
        if not categories:
            continue
        distance_m, method = geometry_distance_m(
            getattr(feature, "geom", None),
            anchor_lat=anchor_lat,
            anchor_lon=anchor_lon,
            bbox=getattr(feature, "bbox", None),
        )
        if not np.isfinite(distance_m):
            continue

        osm_type = str(getattr(feature, "osm_type", ""))
        osm_id_raw = getattr(feature, "osm_id", pd.NA)
        try:
            osm_id = int(osm_id_raw)
        except Exception:
            osm_id = pd.NA

        for category in categories:
            rows.append(
                {
                    "user_id": str(row["user_id"]),
                    "location_id": int(row["location_id"]),
                    "category": str(category),
                    "work_compatible_category": bool(
                        category in WORK_COMPATIBLE_CATEGORIES
                    ),
                    "distance_m": float(distance_m),
                    "distance_method": method,
                    "osm_type": osm_type,
                    "osm_id": osm_id,
                    "geom_type": str(getattr(feature, "geom_type", "")),
                    "clipped": bool(getattr(feature, "clipped", False)),
                }
            )
    return pd.DataFrame(rows)


def build_feature_distance_table(
    anchors: pd.DataFrame,
    request_log: pd.DataFrame,
    raw_cache_dir: Path,
) -> pd.DataFrame:
    anchors = _normalise_anchor_keys(anchors)
    required = {"latitude", "longitude"}
    missing = required.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors missing coordinates: {sorted(missing)}")

    mapping = validate_full_ohsome_cache(anchors, request_log, raw_cache_dir)
    lookup = anchors.merge(
        mapping[["user_id", "location_id", "cache_path"]],
        on=["user_id", "location_id"],
        how="inner",
        validate="one_to_one",
    )

    parts = []
    for anchor in lookup.to_dict(orient="records"):
        content = Path(anchor["cache_path"]).read_bytes()
        part = extract_anchor_feature_distances(anchor, content)
        if not part.empty:
            parts.append(part)

    if not parts:
        return pd.DataFrame(
            columns=[
                "user_id",
                "location_id",
                "category",
                "work_compatible_category",
                "distance_m",
                "distance_method",
                "osm_type",
                "osm_id",
                "geom_type",
                "clipped",
            ]
        )

    result = pd.concat(parts, ignore_index=True)
    return result.sort_values(
        ["user_id", "location_id", "distance_m", "category"],
        kind="stable",
    ).reset_index(drop=True)


def _nearest_by_category(features: pd.DataFrame) -> pd.DataFrame:
    if features.empty:
        return pd.DataFrame(columns=["user_id", "location_id"])

    nearest = (
        features.groupby(
            ["user_id", "location_id", "category"],
            as_index=False,
        )["distance_m"]
        .min()
        .pivot(
            index=["user_id", "location_id"],
            columns="category",
            values="distance_m",
        )
        .reset_index()
    )
    nearest.columns.name = None
    return nearest


def _threshold_name(prefix: str, threshold_m: float) -> str:
    value = int(threshold_m) if float(threshold_m).is_integer() else threshold_m
    return f"{prefix}_within_{value}m"


def build_anchor_semantic_metrics(
    anchors: pd.DataFrame,
    features: pd.DataFrame,
    *,
    thresholds_m: Iterable[float] = DISTANCE_THRESHOLDS_M,
) -> pd.DataFrame:
    """Create one semantic-distance row per anchor.

    Distances are only interpreted inside the 100 m circular threshold even
    though Stage-07d used an axis-aligned ~100 m half-width bbox. Features
    detected in bbox corners may therefore have distance >100 m and are not
    counted as within-100 m evidence.
    """
    anchors = _normalise_anchor_keys(anchors)
    out = anchors.copy()
    nearest = _nearest_by_category(features)

    rename = {
        category: f"nearest_{category}_m"
        for category in CONTEXT_CATEGORIES
        if category in nearest.columns
    }
    nearest = nearest.rename(columns=rename)
    out = out.merge(
        nearest,
        on=["user_id", "location_id"],
        how="left",
        validate="one_to_one",
    )

    for category in CONTEXT_CATEGORIES:
        column = f"nearest_{category}_m"
        if column not in out.columns:
            out[column] = np.nan

    semantic_cols = [f"nearest_{category}_m" for category in CONTEXT_CATEGORIES]
    work_cols = [
        f"nearest_{category}_m"
        for category in CONTEXT_CATEGORIES
        if category in WORK_COMPATIBLE_CATEGORIES
    ]
    out["nearest_semantic_m"] = out[semantic_cols].min(axis=1, skipna=True)
    out["nearest_work_compatible_m"] = out[work_cols].min(
        axis=1, skipna=True
    )

    thresholds = tuple(float(value) for value in thresholds_m)
    for threshold in thresholds:
        out[_threshold_name("semantic", threshold)] = (
            out["nearest_semantic_m"].le(threshold).fillna(False)
        )
        out[_threshold_name("work_compatible", threshold)] = (
            out["nearest_work_compatible_m"].le(threshold).fillna(False)
        )
        for category in CONTEXT_CATEGORIES:
            out[_threshold_name(category, threshold)] = (
                out[f"nearest_{category}_m"].le(threshold).fillna(False)
            )

    censor_threshold = 100.0
    out["work_compatible_censored_distance_100m"] = (
        pd.to_numeric(out["nearest_work_compatible_m"], errors="coerce")
        .clip(upper=censor_threshold)
        .fillna(censor_threshold)
    )
    out["semantic_censored_distance_100m"] = (
        pd.to_numeric(out["nearest_semantic_m"], errors="coerce")
        .clip(upper=censor_threshold)
        .fillna(censor_threshold)
    )

    nearest_work = pd.to_numeric(
        out["nearest_work_compatible_m"], errors="coerce"
    )
    out["work_distance_bucket"] = np.select(
        [
            nearest_work.le(25),
            nearest_work.gt(25) & nearest_work.le(50),
            nearest_work.gt(50) & nearest_work.le(100),
        ],
        ["0_25", "25_50", "50_100"],
        default="none_within_100",
    )
    return out


def align_mobility_roles(
    anchor_metrics: pd.DataFrame,
    work_patterns: pd.DataFrame,
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    """Attach exact stable-secondary anchor role and user-level mobility axes."""
    anchors = _normalise_anchor_keys(anchor_metrics)
    patterns = work_patterns.copy()
    patterns["user_id"] = patterns["user_id"].astype(str)

    role_columns = [
        "user_id",
        "window_pattern",
        "dominant_location_id",
        "dominant_window_share",
    ]
    role_columns = [column for column in role_columns if column in patterns]
    roles = patterns[role_columns].copy()

    if "dominant_location_id" not in roles.columns:
        roles["dominant_location_id"] = pd.NA
    roles["dominant_location_id"] = pd.to_numeric(
        roles["dominant_location_id"], errors="coerce"
    ).astype("Int64")

    out = anchors.merge(
        roles,
        on="user_id",
        how="left",
        validate="many_to_one",
    )
    stable_user = out["window_pattern"].fillna("").eq(
        "stable_secondary_anchor"
    )
    out["stable_secondary_user"] = stable_user
    out["stable_secondary_anchor"] = (
        stable_user
        & out["dominant_location_id"].notna()
        & out["location_id"].astype("Int64").eq(
            out["dominant_location_id"].astype("Int64")
        )
    )
    out["stable_secondary_peer_anchor"] = (
        stable_user & ~out["stable_secondary_anchor"]
    )

    profile = profiles.copy()
    profile["user_id"] = profile["user_id"].astype(str)
    keep = ["user_id"] + [
        axis for axis in PROFILE_AXES if axis in profile.columns
    ]
    out = out.merge(
        profile[keep],
        on="user_id",
        how="left",
        validate="many_to_one",
    )
    for axis in PROFILE_AXES:
        if axis not in out.columns:
            out[axis] = False
        out[axis] = out[axis].fillna(False).astype(bool)

    out["semantic_work_claim_allowed"] = False
    out["occupation_inference_allowed"] = False
    return out


def summarize_distance_buckets(aligned: pd.DataFrame) -> pd.DataFrame:
    counts = (
        aligned.groupby("work_distance_bucket", as_index=False)
        .agg(
            anchors=("location_id", "size"),
            users=("user_id", "nunique"),
        )
    )
    order = {name: idx for idx, name in enumerate(DISTANCE_BUCKETS)}
    counts["_order"] = counts["work_distance_bucket"].map(order)
    counts["anchor_share"] = counts["anchors"] / max(len(aligned), 1)
    return counts.sort_values("_order").drop(columns="_order").reset_index(
        drop=True
    )


def summarize_category_thresholds(
    aligned: pd.DataFrame,
    *,
    thresholds_m: Iterable[float] = DISTANCE_THRESHOLDS_M,
) -> pd.DataFrame:
    rows = []
    for category in CONTEXT_CATEGORIES:
        for threshold in thresholds_m:
            column = _threshold_name(category, float(threshold))
            values = aligned[column].fillna(False).astype(bool)
            rows.append(
                {
                    "category": category,
                    "threshold_m": float(threshold),
                    "anchors": int(values.sum()),
                    "users": int(aligned.loc[values, "user_id"].nunique()),
                    "anchor_share": float(values.mean()),
                }
            )
    return pd.DataFrame(rows)


def build_stable_secondary_user_comparisons(
    aligned: pd.DataFrame,
    *,
    thresholds_m: Iterable[float] = DISTANCE_THRESHOLDS_M,
) -> pd.DataFrame:
    """Compare stable-secondary candidate to same-user recurring peers."""
    rows = []
    stable = aligned.loc[aligned["stable_secondary_user"]].copy()

    for user_id, group in stable.groupby("user_id", sort=True):
        candidates = group.loc[group["stable_secondary_anchor"]]
        peers = group.loc[group["stable_secondary_peer_anchor"]]
        if len(candidates) != 1 or peers.empty:
            continue

        candidate = candidates.iloc[0]
        row: dict[str, object] = {
            "user_id": str(user_id),
            "candidate_location_id": int(candidate["location_id"]),
            "peer_anchor_count": int(len(peers)),
            "candidate_work_censored_distance_100m": float(
                candidate["work_compatible_censored_distance_100m"]
            ),
            "peer_median_work_censored_distance_100m": float(
                peers["work_compatible_censored_distance_100m"].median()
            ),
            "candidate_minus_peer_median_distance_m": float(
                candidate["work_compatible_censored_distance_100m"]
                - peers["work_compatible_censored_distance_100m"].median()
            ),
        }

        candidate_distance = float(
            candidate["work_compatible_censored_distance_100m"]
        )
        peer_distances = pd.to_numeric(
            peers["work_compatible_censored_distance_100m"],
            errors="coerce",
        )
        peer_min = float(peer_distances.min())
        row["candidate_unique_closest_work_context"] = bool(
            candidate_distance < 100.0 and candidate_distance < peer_min
        )
        row["candidate_tied_closest_work_context"] = bool(
            candidate_distance < 100.0
            and np.isclose(
                candidate_distance,
                min(candidate_distance, peer_min),
                atol=1e-9,
            )
        )

        for threshold in thresholds_m:
            column = _threshold_name("work_compatible", float(threshold))
            candidate_value = float(bool(candidate[column]))
            peer_share = float(peers[column].fillna(False).astype(bool).mean())
            value = int(threshold)
            row[f"candidate_work_within_{value}m"] = bool(candidate_value)
            row[f"peer_share_work_within_{value}m"] = peer_share
            row[f"candidate_minus_peer_share_{value}m"] = (
                candidate_value - peer_share
            )

        rows.append(row)

    return pd.DataFrame(rows)


def _bootstrap_mean_ci(
    values: pd.Series,
    *,
    seed: int = 20261002,
    samples: int = 5000,
) -> tuple[float, float, float]:
    numeric = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    if len(numeric) == 0:
        return np.nan, np.nan, np.nan
    mean = float(numeric.mean())
    if len(numeric) == 1:
        return mean, np.nan, np.nan

    rng = np.random.default_rng(seed)
    draws = rng.choice(
        numeric,
        size=(int(samples), len(numeric)),
        replace=True,
    ).mean(axis=1)
    return mean, float(np.quantile(draws, 0.025)), float(
        np.quantile(draws, 0.975)
    )


def summarize_stable_secondary_comparisons(
    comparisons: pd.DataFrame,
    *,
    thresholds_m: Iterable[float] = DISTANCE_THRESHOLDS_M,
) -> pd.DataFrame:
    if comparisons.empty:
        return pd.DataFrame()

    rows = []
    for threshold in thresholds_m:
        value = int(threshold)
        difference = comparisons[
            f"candidate_minus_peer_share_{value}m"
        ]
        mean, low, high = _bootstrap_mean_ci(difference)
        rows.append(
            {
                "threshold_m": float(threshold),
                "users": int(len(comparisons)),
                "candidate_context_users": int(
                    comparisons[
                        f"candidate_work_within_{value}m"
                    ].fillna(False).sum()
                ),
                "mean_peer_context_share": float(
                    comparisons[
                        f"peer_share_work_within_{value}m"
                    ].mean()
                ),
                "mean_candidate_minus_peer_share": mean,
                "bootstrap_95_low": low,
                "bootstrap_95_high": high,
                "candidate_beats_peer_share_users": int(
                    difference.gt(0).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_profile_axis_context(
    aligned: pd.DataFrame,
    *,
    threshold_m: float = 100.0,
) -> pd.DataFrame:
    """User-level descriptive context by factorized mobility axis."""
    context_column = _threshold_name("work_compatible", threshold_m)
    per_user = (
        aligned.groupby("user_id", as_index=False)
        .agg(
            any_work_context=(context_column, "max"),
            anchor_share_work_context=(context_column, "mean"),
        )
    )

    profile_columns = ["user_id"] + [
        axis for axis in PROFILE_AXES if axis in aligned.columns
    ]
    profile = aligned[profile_columns].drop_duplicates("user_id")
    per_user = per_user.merge(
        profile,
        on="user_id",
        how="left",
        validate="one_to_one",
    )

    rows = []
    for axis in PROFILE_AXES:
        values = per_user[axis].fillna(False).astype(bool)
        subset = per_user.loc[values]
        rows.append(
            {
                "axis": axis,
                "users": int(len(subset)),
                "users_any_work_context": int(
                    subset["any_work_context"].fillna(False).sum()
                ),
                "share_users_any_work_context": (
                    float(subset["any_work_context"].mean())
                    if len(subset)
                    else np.nan
                ),
                "median_anchor_share_work_context": (
                    float(subset["anchor_share_work_context"].median())
                    if len(subset)
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def run_audit(
    anchors: pd.DataFrame,
    request_log: pd.DataFrame,
    raw_cache_dir: Path,
    work_patterns: pd.DataFrame,
    profiles: pd.DataFrame,
) -> SemanticDistanceAudit:
    feature_distances = build_feature_distance_table(
        anchors,
        request_log,
        raw_cache_dir,
    )
    anchor_metrics = build_anchor_semantic_metrics(
        anchors,
        feature_distances,
    )
    aligned = align_mobility_roles(
        anchor_metrics,
        work_patterns,
        profiles,
    )
    comparisons = build_stable_secondary_user_comparisons(aligned)
    return SemanticDistanceAudit(
        feature_distances=feature_distances,
        anchor_metrics=anchor_metrics,
        aligned_anchors=aligned,
        distance_bucket_summary=summarize_distance_buckets(aligned),
        category_threshold_summary=summarize_category_thresholds(aligned),
        stable_secondary_user_comparisons=comparisons,
        stable_secondary_summary=summarize_stable_secondary_comparisons(
            comparisons
        ),
        profile_axis_context_summary=summarize_profile_axis_context(aligned),
    )


def synthetic_self_check() -> dict[str, object]:
    anchors = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "latitude": 39.9,
                "longitude": 116.4,
                "nearest_work_compatible_m": 10.0,
                "work_compatible_censored_distance_100m": 10.0,
                "work_distance_bucket": "0_25",
                "work_compatible_within_25m": True,
                "work_compatible_within_50m": True,
                "work_compatible_within_100m": True,
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "latitude": 39.91,
                "longitude": 116.41,
                "nearest_work_compatible_m": np.nan,
                "work_compatible_censored_distance_100m": 100.0,
                "work_distance_bucket": "none_within_100",
                "work_compatible_within_25m": False,
                "work_compatible_within_50m": False,
                "work_compatible_within_100m": False,
            },
        ]
    )
    work = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "window_pattern": "stable_secondary_anchor",
                "dominant_location_id": 1,
                "dominant_window_share": 0.8,
            }
        ]
    )
    profiles = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "site_stable_secondary": True,
                "route_repeated": True,
            }
        ]
    )
    aligned = align_mobility_roles(anchors, work, profiles)
    comparisons = build_stable_secondary_user_comparisons(aligned)
    assert int(aligned["stable_secondary_anchor"].sum()) == 1
    assert len(comparisons) == 1
    assert bool(comparisons.iloc[0]["candidate_unique_closest_work_context"])
    assert (
        comparisons.iloc[0]["candidate_minus_peer_share_100m"]
        == 1.0
    )
    return {"users": 1, "status": "ok"}
