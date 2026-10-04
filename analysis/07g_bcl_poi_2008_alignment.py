"""Stage 07g: BCL POI 2008 normalization and lexical-context alignment.

This stage consumes the provenance/CRS-gated BCL POI 2008 FileGDB from
Stage 07f and the CP2-v2 recurring non-HOME anchor universe from Stage 07c.

BCL POI 2008 exposes coordinates and PNAME, but no trusted category field.
Therefore this stage:
- spatially extracts POI names near temporally relevant anchors;
- preserves raw names;
- derives only predeclared high-precision lexical *signals*;
- keeps unknown and multi-signal names explicit;
- compares exact Stage-05b stable-secondary anchors with same-user peers;
- never emits HOME, WORK, OFFICE, occupation, or employment labels.

All precise anchor/POI records are private artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
import math
from pathlib import Path
import re
import sys
import unicodedata
from typing import Iterable

import numpy as np
import pandas as pd


EXPECTED_LOCATION_NAMESPACE = "production_complete_link_200m_all_resolved_timezone_v2"
EXPECTED_SOURCE_ID = "bcl_poi_2008"
EXPECTED_FIGSHARE_ARTICLE_ID = 28667492
EXPECTED_FIGSHARE_DOI_PREFIX = "10.6084/m9.figshare.28667492"
EXPECTED_CONTAINER_KIND = "gdb"
EXPECTED_EPSG = "4326"
EXPECTED_LAYER = "POI2008CN"
BCL_SOURCE_YEAR = 2008
BCL_ELIGIBLE_YEARS = frozenset({2007, 2008, 2009})
DISTANCE_THRESHOLDS_M = (25.0, 50.0, 100.0)
EXTRACTION_PADDING_M = 150.0
DEFAULT_TILE_SIZE_DEG = 0.02

LEXICAL_CATEGORIES = (
    "business_name",
    "education",
    "healthcare",
    "industrial",
    "retail_service",
    "transport",
    "civic_institutional",
    "residential",
    "recreation_tourism",
)

WORK_COMPATIBLE_LEXICAL_CATEGORIES = frozenset(
    {
        "business_name",
        "education",
        "healthcare",
        "industrial",
        "retail_service",
        "transport",
        "civic_institutional",
    }
)

# Conservative name cues only. These are lexical signals, not trusted POI labels.
LEXICAL_RULES: dict[str, tuple[str, ...]] = {
    "business_name": (
        "有限公司",
        "有限责任公司",
        "集团",
        "公司",
        "写字楼",
        "商务中心",
        "company",
        "corporation",
        "corp",
        "ltd",
        "office",
    ),
    "education": (
        "大学",
        "学院",
        "学校",
        "中学",
        "小学",
        "幼儿园",
        "university",
        "college",
        "school",
        "kindergarten",
    ),
    "healthcare": (
        "医院",
        "卫生院",
        "诊所",
        "hospital",
        "clinic",
        "health center",
    ),
    "industrial": (
        "工业园",
        "产业园",
        "工厂",
        "厂",
        "factory",
        "industrial park",
    ),
    "retail_service": (
        "购物中心",
        "商场",
        "超市",
        "市场",
        "商城",
        "mall",
        "supermarket",
        "market",
    ),
    "transport": (
        "火车站",
        "地铁站",
        "汽车站",
        "客运站",
        "机场",
        "railway station",
        "metro station",
        "bus station",
        "airport",
    ),
    "civic_institutional": (
        "人民政府",
        "政府",
        "公安局",
        "派出所",
        "法院",
        "检察院",
        "government",
        "police",
        "court",
    ),
    "residential": (
        "小区",
        "公寓",
        "宿舍",
        "住宅",
        "家属院",
        "apartment",
        "residential",
        "dormitory",
    ),
    "recreation_tourism": (
        "公园",
        "景区",
        "博物馆",
        "体育馆",
        "酒店",
        "宾馆",
        "park",
        "museum",
        "stadium",
        "hotel",
    ),
}


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
class BclManifestGate:
    ready: bool
    source_id: str
    runner_status: str
    container_kind: str
    container_path: str
    epsg_codes: str
    notes: str


def _load_stage07e():
    path = Path(__file__).with_name("07e_semantic_distance_alignment.py")
    spec = spec_from_file_location("stage07e_for_07g", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load Stage 07e from {path}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STAGE07E = _load_stage07e()


def _as_user_id(frame: pd.DataFrame) -> pd.DataFrame:
    if "user_id" not in frame.columns:
        raise ValueError("frame missing user_id")
    out = frame.copy()
    out["user_id"] = out["user_id"].astype(str)
    return out


def validate_07f_manifest(manifest: dict) -> BclManifestGate:
    """Validate that Stage 07f permits deterministic normalization."""
    gates = manifest.get("gates") or {}
    inspection = manifest.get("inspection_summary") or {}
    source_id = str(manifest.get("source_id") or "")
    runner_status = str(gates.get("runner_status") or "")
    container_kind = str(inspection.get("container_kind") or "").lower()
    container_path = str(inspection.get("container_path") or "")
    epsg_codes = str(inspection.get("epsg_codes") or "")
    article_id = pd.to_numeric(
        pd.Series([manifest.get("figshare_article_id")]), errors="coerce"
    ).iloc[0]
    doi = str(manifest.get("figshare_doi") or "").lower()

    failures: list[str] = []
    if source_id != EXPECTED_SOURCE_ID:
        failures.append("source_id")
    if pd.isna(article_id) or int(article_id) != EXPECTED_FIGSHARE_ARTICLE_ID:
        failures.append("figshare_article_id")
    if not doi.startswith(EXPECTED_FIGSHARE_DOI_PREFIX.lower()):
        failures.append("figshare_doi")
    if runner_status != "ready_for_normalization":
        failures.append("runner_status")
    if container_kind != EXPECTED_CONTAINER_KIND:
        failures.append("container_kind")
    if not container_path.lower().endswith(".gdb"):
        failures.append("container_path")
    if EXPECTED_EPSG not in epsg_codes:
        failures.append("epsg_4326")
    if bool(manifest.get("semantic_claim_allowed", True)):
        failures.append("semantic_claim_allowed_must_be_false")
    if bool(manifest.get("occupation_inference_allowed", True)):
        failures.append("occupation_inference_allowed_must_be_false")

    return BclManifestGate(
        ready=not failures,
        source_id=source_id,
        runner_status=runner_status,
        container_kind=container_kind,
        container_path=container_path,
        epsg_codes=epsg_codes,
        notes="ok" if not failures else "failed:" + ",".join(failures),
    )


def manifest_gate_frame(gate: BclManifestGate) -> pd.DataFrame:
    return pd.DataFrame([gate.__dict__])


def bcl_eligible_anchors(anchor_dates: pd.DataFrame) -> pd.DataFrame:
    """Return CP2-v2 anchors whose median year is exact/proxy relevant to BCL 2008."""
    anchors = _as_user_id(anchor_dates)
    required = {
        "location_id",
        "latitude",
        "longitude",
        "median_observation_date",
        "median_observation_year",
        "location_namespace",
    }
    missing = required.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchor dates missing columns: {sorted(missing)}")
    namespaces = set(
        anchors["location_namespace"].dropna().astype(str).unique()
    )
    if namespaces != {EXPECTED_LOCATION_NAMESPACE}:
        raise ValueError(
            "incompatible location namespace for Stage 07g: "
            f"{sorted(namespaces)}"
        )

    years = pd.to_numeric(
        anchors["median_observation_year"], errors="raise"
    ).astype(int)
    out = anchors.loc[years.isin(BCL_ELIGIBLE_YEARS)].copy()
    out["location_id"] = pd.to_numeric(
        out["location_id"], errors="raise"
    ).astype(int)
    out["latitude"] = pd.to_numeric(out["latitude"], errors="raise")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="raise")
    out["bcl_alignment_type"] = years.loc[out.index].map(
        lambda year: "exact_year" if int(year) == BCL_SOURCE_YEAR
        else "nearest_year_proxy"
    )
    out["bcl_temporal_offset_years"] = (
        BCL_SOURCE_YEAR - years.loc[out.index]
    ).astype(int)
    return out.reset_index(drop=True)


def summarize_bcl_eligibility(
    all_anchors: pd.DataFrame,
    eligible: pd.DataFrame,
) -> pd.DataFrame:
    years = pd.to_numeric(
        eligible["median_observation_year"], errors="coerce"
    ) if not eligible.empty else pd.Series(dtype=float)
    return pd.DataFrame(
        [
            {
                "candidate_anchors": int(len(all_anchors)),
                "candidate_users": int(all_anchors["user_id"].astype(str).nunique()),
                "bcl_eligible_anchors": int(len(eligible)),
                "bcl_eligible_users": int(
                    eligible["user_id"].astype(str).nunique()
                ) if not eligible.empty else 0,
                "exact_2008_anchors": int(years.eq(2008).sum()),
                "proxy_2007_anchors": int(years.eq(2007).sum()),
                "proxy_2009_anchors": int(years.eq(2009).sum()),
            }
        ]
    )


def build_spatial_tiles(
    anchors: pd.DataFrame,
    *,
    tile_size_deg: float = DEFAULT_TILE_SIZE_DEG,
    padding_m: float = EXTRACTION_PADDING_M,
) -> pd.DataFrame:
    """Group anchors into deterministic geographic query tiles.

    Each output bbox encloses all anchors assigned to the tile plus at least
    padding_m in latitude/longitude. The padding exceeds the final 100 m
    evidence threshold, so tile boundaries cannot remove a <=100 m POI.
    """
    if tile_size_deg <= 0:
        raise ValueError("tile_size_deg must be positive")
    if padding_m < max(DISTANCE_THRESHOLDS_M):
        raise ValueError("padding_m must be >= final evidence threshold")

    required = {"latitude", "longitude"}
    missing = required.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors missing columns: {sorted(missing)}")
    if anchors.empty:
        return pd.DataFrame(
            columns=[
                "tile_id", "anchor_count", "xmin", "ymin", "xmax", "ymax"
            ]
        )

    work = anchors.copy()
    work["latitude"] = pd.to_numeric(work["latitude"], errors="raise")
    work["longitude"] = pd.to_numeric(work["longitude"], errors="raise")
    work["_tile_x"] = np.floor(work["longitude"] / tile_size_deg).astype(int)
    work["_tile_y"] = np.floor(work["latitude"] / tile_size_deg).astype(int)

    rows: list[dict[str, object]] = []
    for (tile_x, tile_y), group in work.groupby(
        ["_tile_x", "_tile_y"], sort=True
    ):
        lat0 = float(group["latitude"].mean())
        lat_pad = float(padding_m) / 111_320.0
        lon_scale = max(math.cos(math.radians(lat0)), 1e-6)
        lon_pad = float(padding_m) / (111_320.0 * lon_scale)
        rows.append(
            {
                "tile_id": f"{int(tile_x)}_{int(tile_y)}",
                "anchor_count": int(len(group)),
                "xmin": float(group["longitude"].min() - lon_pad),
                "ymin": float(group["latitude"].min() - lat_pad),
                "xmax": float(group["longitude"].max() + lon_pad),
                "ymax": float(group["latitude"].max() + lat_pad),
            }
        )
    return pd.DataFrame(rows)


def normalize_poi_name(value: object) -> str:
    text = "" if value is None else str(value)
    text = unicodedata.normalize("NFKC", text).strip().lower()
    text = re.sub(r"\s+", " ", text)
    return text


def lexical_categories_for_name(value: object) -> tuple[str, ...]:
    text = normalize_poi_name(value)
    if not text:
        return tuple()
    categories = [
        category
        for category in LEXICAL_CATEGORIES
        if any(token.lower() in text for token in LEXICAL_RULES[category])
    ]
    return tuple(categories)


def classify_poi_names(pois: pd.DataFrame) -> pd.DataFrame:
    """Attach deterministic multi-label lexical signals while preserving raw names."""
    required = {"poi_name", "latitude", "longitude"}
    missing = required.difference(pois.columns)
    if missing:
        raise ValueError(f"POIs missing columns: {sorted(missing)}")
    out = pois.copy()
    out["poi_name"] = out["poi_name"].fillna("").astype(str)
    out["name_normalized"] = out["poi_name"].map(normalize_poi_name)
    out["lexical_categories"] = out["poi_name"].map(
        lexical_categories_for_name
    )
    out["lexical_signal_count"] = out["lexical_categories"].map(len).astype(int)
    out["lexical_status"] = np.select(
        [
            out["lexical_signal_count"].eq(0),
            out["lexical_signal_count"].eq(1),
        ],
        ["unknown", "single_signal"],
        default="ambiguous_multi_signal",
    )
    out["work_compatible_lexical_signal"] = out["lexical_categories"].map(
        lambda values: bool(
            set(values).intersection(WORK_COMPATIBLE_LEXICAL_CATEGORIES)
        )
    )
    return out


def haversine_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    radius = 6_371_008.8
    phi1 = math.radians(float(lat1))
    phi2 = math.radians(float(lat2))
    dphi = math.radians(float(lat2) - float(lat1))
    dlambda = math.radians(float(lon2) - float(lon1))
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    )
    return float(radius * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a)))


def assign_pois_to_anchors(
    anchors: pd.DataFrame,
    pois: pd.DataFrame,
    *,
    max_distance_m: float = 100.0,
) -> pd.DataFrame:
    """Return private anchor-POI pairs within max_distance_m.

    The caller should spatially pre-extract POIs near the anchor set. This
    helper performs the exact radial distance gate.
    """
    if max_distance_m <= 0:
        raise ValueError("max_distance_m must be positive")
    anchors = _as_user_id(anchors)
    required_a = {"location_id", "latitude", "longitude"}
    required_p = {"poi_name", "latitude", "longitude"}
    missing = required_a.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors missing columns: {sorted(missing)}")
    missing = required_p.difference(pois.columns)
    if missing:
        raise ValueError(f"POIs missing columns: {sorted(missing)}")

    classified = (
        pois.copy()
        if "lexical_categories" in pois.columns
        else classify_poi_names(pois)
    )
    if anchors.empty or classified.empty:
        return pd.DataFrame(
            columns=[
                "user_id",
                "location_id",
                "poi_name",
                "poi_latitude",
                "poi_longitude",
                "distance_m",
                "lexical_categories",
                "lexical_status",
                "work_compatible_lexical_signal",
            ]
        )

    rows: list[dict[str, object]] = []
    # This exact matcher is intentionally simple; Stage 07g first reduces the
    # 6M-source universe to small GDAL spatial tiles.
    for anchor in anchors.itertuples(index=False):
        alat = float(anchor.latitude)
        alon = float(anchor.longitude)
        lat_pad = float(max_distance_m) / 111_320.0
        lon_pad = float(max_distance_m) / (
            111_320.0 * max(math.cos(math.radians(alat)), 1e-6)
        )
        nearby = classified.loc[
            classified["latitude"].between(alat - lat_pad, alat + lat_pad)
            & classified["longitude"].between(alon - lon_pad, alon + lon_pad)
        ]
        for poi in nearby.itertuples(index=False):
            distance = haversine_m(
                alat,
                alon,
                float(poi.latitude),
                float(poi.longitude),
            )
            if distance > float(max_distance_m):
                continue
            rows.append(
                {
                    "user_id": str(anchor.user_id),
                    "location_id": int(anchor.location_id),
                    "poi_name": str(poi.poi_name),
                    "poi_latitude": float(poi.latitude),
                    "poi_longitude": float(poi.longitude),
                    "distance_m": distance,
                    "lexical_categories": tuple(poi.lexical_categories),
                    "lexical_status": str(poi.lexical_status),
                    "work_compatible_lexical_signal": bool(
                        poi.work_compatible_lexical_signal
                    ),
                }
            )
    return pd.DataFrame(rows)


def _threshold_name(prefix: str, threshold_m: float) -> str:
    return f"{prefix}_within_{int(threshold_m)}m"


def build_anchor_lexical_metrics(
    anchors: pd.DataFrame,
    matches: pd.DataFrame,
    *,
    thresholds_m: Iterable[float] = DISTANCE_THRESHOLDS_M,
) -> pd.DataFrame:
    anchors = _as_user_id(anchors)
    out = anchors.copy()
    out["location_id"] = pd.to_numeric(
        out["location_id"], errors="raise"
    ).astype(int)

    if matches.empty:
        grouped_any: dict[tuple[str, int], pd.DataFrame] = {}
    else:
        work = matches.copy()
        work["user_id"] = work["user_id"].astype(str)
        work["location_id"] = pd.to_numeric(
            work["location_id"], errors="raise"
        ).astype(int)
        grouped_any = {
            key: group
            for key, group in work.groupby(
                ["user_id", "location_id"], sort=False
            )
        }

    rows = []
    thresholds = tuple(float(value) for value in thresholds_m)
    for anchor in out.itertuples(index=False):
        key = (str(anchor.user_id), int(anchor.location_id))
        group = grouped_any.get(key, pd.DataFrame())
        row: dict[str, object] = {
            "user_id": key[0],
            "location_id": key[1],
            "nearest_poi_m": (
                float(pd.to_numeric(group["distance_m"], errors="coerce").min())
                if not group.empty else np.nan
            ),
            "poi_count_within_100m": int(len(group)),
            "nearest_work_compatible_lexical_m": np.nan,
        }
        if not group.empty:
            work_signal = group.loc[
                group["work_compatible_lexical_signal"].fillna(False).astype(bool)
            ]
            if not work_signal.empty:
                row["nearest_work_compatible_lexical_m"] = float(
                    pd.to_numeric(
                        work_signal["distance_m"], errors="coerce"
                    ).min()
                )

        for threshold in thresholds:
            if group.empty:
                in_range = group
            else:
                in_range = group.loc[
                    pd.to_numeric(group["distance_m"], errors="coerce")
                    .le(threshold)
                ]
            row[_threshold_name("any_poi", threshold)] = bool(len(in_range))
            row[_threshold_name("any_lexical_signal", threshold)] = bool(
                not in_range.empty
                and in_range["lexical_status"].ne("unknown").any()
            )
            row[_threshold_name("work_compatible_lexical", threshold)] = bool(
                not in_range.empty
                and in_range["work_compatible_lexical_signal"]
                .fillna(False).astype(bool).any()
            )
            for category in LEXICAL_CATEGORIES:
                row[_threshold_name(category, threshold)] = bool(
                    not in_range.empty
                    and in_range["lexical_categories"].map(
                        lambda values: category in set(values)
                    ).any()
                )
        rows.append(row)

    metrics = pd.DataFrame(rows)
    passthrough = [
        column
        for column in out.columns
        if column not in {"user_id", "location_id"}
    ]
    if passthrough:
        metrics = metrics.merge(
            out[["user_id", "location_id", *passthrough]],
            on=["user_id", "location_id"],
            how="left",
            validate="one_to_one",
        )
    return metrics


def align_mobility_roles(
    anchor_metrics: pd.DataFrame,
    work_patterns: pd.DataFrame,
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    """Reuse the audited Stage-07e exact-role/profile alignment contract."""
    return STAGE07E.align_mobility_roles(
        anchor_metrics,
        work_patterns,
        profiles,
    )


def build_stable_secondary_lexical_comparisons(
    aligned: pd.DataFrame,
    *,
    thresholds_m: Iterable[float] = DISTANCE_THRESHOLDS_M,
) -> pd.DataFrame:
    """Compare BCL lexical-name evidence at exact stable-secondary vs peers."""
    rows: list[dict[str, object]] = []
    stable = aligned.loc[
        aligned["stable_secondary_user"].fillna(False).astype(bool)
    ].copy()

    for user_id, group in stable.groupby("user_id", sort=True):
        candidates = group.loc[
            group["stable_secondary_anchor"].fillna(False).astype(bool)
        ]
        peers = group.loc[
            group["stable_secondary_peer_anchor"].fillna(False).astype(bool)
        ]
        # If the exact candidate is outside the BCL temporal subset it is not
        # present in aligned and this user correctly contributes no comparison.
        if len(candidates) != 1 or peers.empty:
            continue
        candidate = candidates.iloc[0]
        row: dict[str, object] = {
            "user_id": str(user_id),
            "candidate_location_id": int(candidate["location_id"]),
            "peer_anchor_count": int(len(peers)),
        }
        for threshold in thresholds_m:
            value = int(threshold)
            column = _threshold_name(
                "work_compatible_lexical", float(threshold)
            )
            candidate_value = float(bool(candidate[column]))
            peer_share = float(
                peers[column].fillna(False).astype(bool).mean()
            )
            row[f"candidate_work_lexical_within_{value}m"] = bool(
                candidate_value
            )
            row[f"peer_share_work_lexical_within_{value}m"] = peer_share
            row[f"candidate_minus_peer_share_{value}m"] = (
                candidate_value - peer_share
            )
        rows.append(row)
    return pd.DataFrame(rows)


def _bootstrap_mean_ci(
    values: pd.Series,
    *,
    seed: int = 20261004,
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
    return (
        mean,
        float(np.quantile(draws, 0.025)),
        float(np.quantile(draws, 0.975)),
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
        diff = comparisons[f"candidate_minus_peer_share_{value}m"]
        mean, low, high = _bootstrap_mean_ci(diff)
        rows.append(
            {
                "threshold_m": float(threshold),
                "users": int(len(comparisons)),
                "candidate_context_users": int(
                    comparisons[
                        f"candidate_work_lexical_within_{value}m"
                    ].fillna(False).sum()
                ),
                "mean_peer_context_share": float(
                    comparisons[
                        f"peer_share_work_lexical_within_{value}m"
                    ].mean()
                ),
                "mean_candidate_minus_peer_share": mean,
                "bootstrap_95_low": low,
                "bootstrap_95_high": high,
                "candidate_beats_peer_share_users": int(diff.gt(0).sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_category_thresholds(
    metrics: pd.DataFrame,
    *,
    thresholds_m: Iterable[float] = DISTANCE_THRESHOLDS_M,
) -> pd.DataFrame:
    rows = []
    for category in LEXICAL_CATEGORIES:
        for threshold in thresholds_m:
            column = _threshold_name(category, float(threshold))
            values = metrics[column].fillna(False).astype(bool)
            rows.append(
                {
                    "category": category,
                    "threshold_m": float(threshold),
                    "anchors": int(values.sum()),
                    "users": int(
                        metrics.loc[values, "user_id"].astype(str).nunique()
                    ),
                    "anchor_share": float(values.mean())
                    if len(values) else np.nan,
                }
            )
    return pd.DataFrame(rows)


def summarize_profile_axis_context(
    aligned: pd.DataFrame,
    *,
    threshold_m: float = 100.0,
) -> pd.DataFrame:
    context_column = _threshold_name(
        "work_compatible_lexical", threshold_m
    )
    per_user = (
        aligned.groupby("user_id", as_index=False)
        .agg(
            any_bcl_work_lexical=(context_column, "max"),
            anchor_share_bcl_work_lexical=(context_column, "mean"),
        )
    )
    profile_columns = ["user_id"] + [
        axis for axis in PROFILE_AXES if axis in aligned.columns
    ]
    profile = aligned[profile_columns].drop_duplicates("user_id")
    for axis in PROFILE_AXES:
        if axis not in profile.columns:
            profile[axis] = False
    per_user = per_user.merge(
        profile[["user_id", *PROFILE_AXES]],
        on="user_id",
        how="left",
        validate="one_to_one",
    )
    rows = []
    for axis in PROFILE_AXES:
        subset = per_user.loc[
            per_user[axis].fillna(False).astype(bool)
        ]
        rows.append(
            {
                "axis": axis,
                "users": int(len(subset)),
                "users_any_bcl_work_lexical": int(
                    subset["any_bcl_work_lexical"].fillna(False).sum()
                ),
                "share_users_any_bcl_work_lexical": (
                    float(subset["any_bcl_work_lexical"].mean())
                    if len(subset) else np.nan
                ),
                "median_anchor_share_bcl_work_lexical": (
                    float(
                        subset["anchor_share_bcl_work_lexical"].median()
                    )
                    if len(subset) else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def lexical_status_summary(classified_pois: pd.DataFrame) -> pd.DataFrame:
    if classified_pois.empty:
        return pd.DataFrame(
            columns=["lexical_status", "pois", "share"]
        )
    counts = (
        classified_pois.groupby("lexical_status", as_index=False)
        .agg(pois=("poi_name", "size"))
    )
    counts["share"] = counts["pois"] / len(classified_pois)
    return counts.sort_values("pois", ascending=False).reset_index(drop=True)


def synthetic_self_check() -> dict[str, object]:
    anchors = pd.DataFrame(
        [
            {
                "user_id": "u",
                "location_id": 1,
                "latitude": 39.9,
                "longitude": 116.4,
                "median_observation_date": "2008-06-01",
                "median_observation_year": 2008,
                "location_namespace": EXPECTED_LOCATION_NAMESPACE,
            },
            {
                "user_id": "u",
                "location_id": 2,
                "latitude": 39.901,
                "longitude": 116.401,
                "median_observation_date": "2011-06-01",
                "median_observation_year": 2011,
                "location_namespace": EXPECTED_LOCATION_NAMESPACE,
            },
        ]
    )
    eligible = bcl_eligible_anchors(anchors)
    assert len(eligible) == 1
    assert lexical_categories_for_name("北京大学") == ("education",)
    assert "business_name" in lexical_categories_for_name("示例有限公司")
    tiles = build_spatial_tiles(eligible)
    assert int(tiles["anchor_count"].sum()) == 1
    return {
        "status": "ok",
        "eligible": int(len(eligible)),
        "tiles": int(len(tiles)),
    }
