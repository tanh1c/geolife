"""Stage 07c: external POI / land-use enrichment for factorized work profiles.

This stage adds OpenStreetMap context as an independent semantic evidence axis.
It does NOT infer occupation, employment status, true WORK, or OFFICE.

Privacy boundary:
- exact anchor coordinates and raw OSM responses stay in private runtime caches;
- aggregate committed outputs must not contain coordinates, OSM names, or user IDs.

The core is network-optional: candidate construction, OSM-tag classification,
distance attachment, and aggregation are testable without external requests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Iterable
from urllib import parse, request

import numpy as np
import pandas as pd


PRIMARY_RADIUS_M = 100
SENSITIVITY_RADIUS_M = 250
DEFAULT_QUERY_RADIUS_M = SENSITIVITY_RADIUS_M
DEFAULT_BATCH_SIZE = 8
DEFAULT_ENDPOINT = "https://overpass-api.de/api/interpreter"
DEFAULT_USER_AGENT = "geolife-stage07c-research/1.0"

CONTEXT_CATEGORIES = (
    "residential",
    "office_commercial",
    "education",
    "healthcare",
    "industrial",
    "retail_service",
    "transport",
    "civic_institutional",
    "recreation_tourism",
)

WORK_COMPATIBLE_CATEGORIES = (
    "office_commercial",
    "education",
    "healthcare",
    "industrial",
    "retail_service",
    "transport",
    "civic_institutional",
)

LANDUSE_VALUES = {
    "residential",
    "commercial",
    "retail",
    "industrial",
    "education",
    "institutional",
    "civic_admin",
    "railway",
}

BUILDING_VALUES = {
    "apartments",
    "residential",
    "house",
    "detached",
    "terrace",
    "semidetached_house",
    "dormitory",
    "office",
    "commercial",
    "retail",
    "school",
    "university",
    "college",
    "kindergarten",
    "hospital",
    "industrial",
    "warehouse",
    "civic",
    "train_station",
    "transportation",
}

EDUCATION_AMENITIES = {
    "school",
    "university",
    "college",
    "kindergarten",
    "language_school",
    "music_school",
    "training",
    "driving_school",
}

HEALTHCARE_AMENITIES = {
    "hospital",
    "clinic",
    "doctors",
    "dentist",
    "pharmacy",
    "nursing_home",
    "social_facility",
}

RETAIL_SERVICE_AMENITIES = {
    "restaurant",
    "cafe",
    "fast_food",
    "food_court",
    "bar",
    "pub",
    "bank",
    "atm",
    "marketplace",
    "cinema",
    "theatre",
    "nightclub",
    "car_rental",
    "car_wash",
}

TRANSPORT_AMENITIES = {
    "bus_station",
    "taxi",
    "ferry_terminal",
    "parking",
    "parking_entrance",
    "bicycle_rental",
}

CIVIC_AMENITIES = {
    "police",
    "fire_station",
    "courthouse",
    "townhall",
    "post_office",
    "library",
    "community_centre",
    "social_centre",
    "place_of_worship",
    "public_building",
}

TRANSPORT_RAILWAY_VALUES = {
    "station",
    "halt",
    "tram_stop",
    "subway_entrance",
    "platform",
}

RESIDENTIAL_BUILDINGS = {
    "apartments",
    "residential",
    "house",
    "detached",
    "terrace",
    "semidetached_house",
    "dormitory",
}

OFFICE_BUILDINGS = {"office", "commercial"}
EDUCATION_BUILDINGS = {"school", "university", "college", "kindergarten"}
HEALTHCARE_BUILDINGS = {"hospital"}
INDUSTRIAL_BUILDINGS = {"industrial", "warehouse"}
RETAIL_BUILDINGS = {"retail"}
CIVIC_BUILDINGS = {"civic"}
TRANSPORT_BUILDINGS = {"train_station", "transportation"}


@dataclass(frozen=True)
class ExternalContextAudit:
    candidate_anchors: pd.DataFrame
    osm_elements: pd.DataFrame
    anchor_element_links: pd.DataFrame
    anchor_context: pd.DataFrame
    coverage_summary: pd.DataFrame
    category_summary: pd.DataFrame
    stable_secondary_peer: pd.DataFrame
    stable_secondary_summary: pd.DataFrame
    signature_summary: pd.DataFrame
    radius_sensitivity: pd.DataFrame
    request_log: pd.DataFrame


def _as_user_id(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "user_id" not in out.columns:
        raise ValueError("input frame missing user_id")
    out["user_id"] = out["user_id"].astype(str)
    return out


def _bool(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index, dtype=bool)
    return frame[column].fillna(False).astype(bool)


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _supported_home_rows(home_evidence: pd.DataFrame) -> pd.DataFrame:
    home = _as_user_id(home_evidence)
    if "unique_vote_winner" in home.columns:
        home = home.loc[_bool(home, "unique_vote_winner")]
    if "home_tier" in home.columns:
        home = home.loc[
            home["home_tier"].fillna("").astype(str).str.lower().isin({"high", "medium"})
        ]
    required = {"user_id", "location_id"}
    missing = required.difference(home.columns)
    if missing:
        raise ValueError(f"home_evidence missing required columns: {sorted(missing)}")
    home = home.copy()
    home["location_id"] = pd.to_numeric(home["location_id"], errors="raise").astype(int)
    if home["user_id"].duplicated().any():
        raise ValueError("supported home_evidence must have at most one row per user")
    keep = ["user_id", "location_id"]
    if "home_tier" in home.columns:
        keep.append("home_tier")
    return home[keep].rename(columns={"location_id": "home_location_id"})


def build_candidate_anchors(
    locations: pd.DataFrame,
    home_evidence: pd.DataFrame,
    factorized_profiles: pd.DataFrame,
    *,
    work_patterns: pd.DataFrame | None = None,
    edge_summary: pd.DataFrame | None = None,
    min_stay_count: int = 2,
) -> pd.DataFrame:
    """Build recurring non-HOME anchors for the reliable-HOME subset.

    Coordinates remain in this private table only.
    """
    if min_stay_count < 2:
        raise ValueError("min_stay_count must be >=2 to match recurring-location semantics")

    loc = _as_user_id(locations)
    required = {"user_id", "location_id", "latitude", "longitude", "stay_count"}
    missing = required.difference(loc.columns)
    if missing:
        raise ValueError(f"locations missing required columns: {sorted(missing)}")

    loc = loc.copy()
    loc["location_id"] = pd.to_numeric(loc["location_id"], errors="raise").astype(int)
    loc["latitude"] = pd.to_numeric(loc["latitude"], errors="raise")
    loc["longitude"] = pd.to_numeric(loc["longitude"], errors="raise")
    loc["stay_count"] = pd.to_numeric(loc["stay_count"], errors="coerce").fillna(0).astype(int)

    if loc.duplicated(["user_id", "location_id"]).any():
        raise ValueError("locations must be unique by user_id + location_id")

    home = _supported_home_rows(home_evidence)
    profiles = _as_user_id(factorized_profiles)
    if profiles["user_id"].duplicated().any():
        raise ValueError("factorized_profiles must contain one row per user")

    if "home_context_supported" in profiles.columns:
        profiles = profiles.loc[_bool(profiles, "home_context_supported")].copy()

    out = (
        loc.merge(home, on="user_id", how="inner", validate="many_to_one")
        .merge(profiles, on="user_id", how="inner", validate="many_to_one")
    )
    out = out.loc[
        out["stay_count"].ge(int(min_stay_count))
        & out["location_id"].ne(out["home_location_id"])
    ].copy()

    active_col = None
    for candidate in ("active_local_dates", "active_days"):
        if candidate in out.columns:
            active_col = candidate
            break
    if active_col:
        out["active_days"] = pd.to_numeric(out[active_col], errors="coerce")
    else:
        out["active_days"] = np.nan

    if "total_dwell_h" not in out.columns:
        out["total_dwell_h"] = np.nan
    else:
        out["total_dwell_h"] = pd.to_numeric(out["total_dwell_h"], errors="coerce")

    out["is_stable_secondary"] = False
    out["is_adaptive_dominant"] = False
    if work_patterns is not None and not work_patterns.empty:
        work = _as_user_id(work_patterns)
        if work["user_id"].duplicated().any():
            raise ValueError("work_patterns must contain one row per user")
        keep = ["user_id"]
        for column in ("window_pattern", "dominant_location_id"):
            if column in work.columns:
                keep.append(column)
        out = out.merge(
            work[keep],
            on="user_id",
            how="left",
            validate="many_to_one",
        )
        dominant = pd.to_numeric(out.get("dominant_location_id"), errors="coerce")
        out["is_adaptive_dominant"] = dominant.eq(out["location_id"])
        if "window_pattern" in out.columns:
            out["is_stable_secondary"] = (
                out["window_pattern"].eq("stable_secondary_anchor")
                & out["is_adaptive_dominant"]
            )

    out["appears_in_repeated_edge"] = False
    if edge_summary is not None and not edge_summary.empty:
        edges = _as_user_id(edge_summary)
        needed = {"user_id", "origin_location_id", "destination_location_id"}
        missing = needed.difference(edges.columns)
        if missing:
            raise ValueError(f"edge_summary missing required columns: {sorted(missing)}")
        if "repeated_edge" in edges.columns:
            edges = edges.loc[_bool(edges, "repeated_edge")]
        elif "active_days" in edges.columns:
            edges = edges.loc[pd.to_numeric(edges["active_days"], errors="coerce").ge(2)]
        else:
            edges = edges.iloc[0:0]

        endpoint_rows = []
        for row in edges.itertuples(index=False):
            endpoint_rows.append((str(row.user_id), int(row.origin_location_id)))
            endpoint_rows.append((str(row.user_id), int(row.destination_location_id)))
        repeated_endpoints = set(endpoint_rows)
        out["appears_in_repeated_edge"] = [
            (str(user), int(location)) in repeated_endpoints
            for user, location in zip(out["user_id"], out["location_id"], strict=True)
        ]

    keep_profile_flags = (
        "candidate_single_anchor_geometry",
        "candidate_anchor_set_geometry",
        "candidate_route_region_geometry",
        "schedule_agnostic_needed",
        "mobile_complexity_evidence",
        "route_repeated",
    )
    for flag in keep_profile_flags:
        if flag not in out.columns:
            out[flag] = False
        out[flag] = out[flag].fillna(False).astype(bool)

    out["anchor_key"] = (
        out["user_id"].astype(str)
        + "::L"
        + out["location_id"].astype(int).astype(str)
    )

    private_columns = [
        "anchor_key",
        "user_id",
        "location_id",
        "latitude",
        "longitude",
        "stay_count",
        "active_days",
        "total_dwell_h",
        "home_location_id",
        "is_stable_secondary",
        "is_adaptive_dominant",
        "appears_in_repeated_edge",
        *keep_profile_flags,
    ]
    if "home_tier" in out.columns:
        private_columns.append("home_tier")
    return (
        out[private_columns]
        .sort_values(["user_id", "location_id"], kind="stable")
        .reset_index(drop=True)
    )


def build_overpass_query(
    anchors: pd.DataFrame,
    *,
    radius_m: int = DEFAULT_QUERY_RADIUS_M,
) -> str:
    """Build one Overpass QL batch query for nearby semantic objects."""
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    if anchors.empty:
        raise ValueError("anchors must not be empty")
    required = {"latitude", "longitude"}
    missing = required.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors missing required columns: {sorted(missing)}")

    selectors = []
    landuse_regex = "|".join(sorted(LANDUSE_VALUES))
    building_regex = "|".join(sorted(BUILDING_VALUES))
    railway_regex = "|".join(sorted(TRANSPORT_RAILWAY_VALUES))

    for row in anchors.itertuples(index=False):
        lat = float(row.latitude)
        lon = float(row.longitude)
        around = f"(around:{int(radius_m)},{lat:.7f},{lon:.7f})"
        selectors.extend(
            [
                f'nwr{around}["amenity"];',
                f'nwr{around}["office"];',
                f'nwr{around}["shop"];',
                f'nwr{around}["craft"];',
                f'nwr{around}["healthcare"];',
                f'nwr{around}["landuse"~"^({landuse_regex})$"];',
                f'nwr{around}["building"~"^({building_regex})$"];',
                f'nwr{around}["railway"~"^({railway_regex})$"];',
                f'nwr{around}["public_transport"];',
                f'nwr{around}["highway"="bus_stop"];',
                f'nwr{around}["tourism"];',
                f'nwr{around}["leisure"];',
                f'nwr{around}["industrial"];',
                f'nwr{around}["man_made"="works"];',
            ]
        )

    return (
        "[out:json][timeout:90];\n(\n"
        + "\n".join(selectors)
        + "\n);\nout center tags;"
    )


def _query_hash(query: str) -> str:
    return hashlib.sha256(query.encode("utf-8")).hexdigest()[:20]


def _post_overpass(
    query: str,
    *,
    endpoint: str,
    user_agent: str,
    timeout_s: int,
) -> dict:
    body = parse.urlencode({"data": query}).encode("utf-8")
    req = request.Request(
        endpoint,
        data=body,
        headers={
            "User-Agent": user_agent,
            "Content-Type": "application/x-www-form-urlencoded",
        },
        method="POST",
    )
    with request.urlopen(req, timeout=timeout_s) as response:
        return json.loads(response.read().decode("utf-8"))


def parse_overpass_payload(
    payload: dict,
    *,
    query_hash: str | None = None,
) -> pd.DataFrame:
    """Parse OSM node/way/relation centers and semantic tags."""
    rows = []
    for element in payload.get("elements", []):
        element_type = str(element.get("type", ""))
        osm_id = element.get("id")
        if osm_id is None:
            continue
        if element_type == "node":
            lat = element.get("lat")
            lon = element.get("lon")
        else:
            center = element.get("center") or {}
            lat = center.get("lat")
            lon = center.get("lon")
        if lat is None or lon is None:
            continue
        tags = element.get("tags") or {}
        rows.append(
            {
                "osm_type": element_type,
                "osm_id": int(osm_id),
                "latitude": float(lat),
                "longitude": float(lon),
                "tags": dict(tags),
                "query_hash": query_hash,
            }
        )
    if not rows:
        return pd.DataFrame(
            columns=[
                "osm_type",
                "osm_id",
                "latitude",
                "longitude",
                "tags",
                "query_hash",
            ]
        )
    out = pd.DataFrame(rows)
    return (
        out.sort_values(["osm_type", "osm_id"], kind="stable")
        .drop_duplicates(["osm_type", "osm_id"], keep="first")
        .reset_index(drop=True)
    )


def fetch_overpass_elements(
    anchors: pd.DataFrame,
    *,
    cache_dir: Path,
    endpoint: str = DEFAULT_ENDPOINT,
    user_agent: str = DEFAULT_USER_AGENT,
    radius_m: int = DEFAULT_QUERY_RADIUS_M,
    batch_size: int = DEFAULT_BATCH_SIZE,
    pause_s: float = 1.0,
    timeout_s: int = 120,
    retries: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch semantic OSM objects in small cached batches.

    Raw response JSON is private and keyed by query hash.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be positive")
    cache_dir.mkdir(parents=True, exist_ok=True)
    anchors = anchors.reset_index(drop=True)
    element_parts = []
    logs = []

    for start in range(0, len(anchors), batch_size):
        batch = anchors.iloc[start : start + batch_size]
        query = build_overpass_query(batch, radius_m=radius_m)
        digest = _query_hash(query)
        cache_path = cache_dir / f"overpass_{digest}.json"
        cached = cache_path.exists()

        if cached:
            payload = json.loads(cache_path.read_text(encoding="utf-8"))
        else:
            last_error = None
            for attempt in range(retries):
                try:
                    payload = _post_overpass(
                        query,
                        endpoint=endpoint,
                        user_agent=user_agent,
                        timeout_s=timeout_s,
                    )
                    cache_path.write_text(
                        json.dumps(payload, ensure_ascii=False),
                        encoding="utf-8",
                    )
                    last_error = None
                    break
                except Exception as exc:  # network/runtime boundary
                    last_error = exc
                    if attempt + 1 < retries:
                        time.sleep(min(8.0, 2.0 ** attempt))
            if last_error is not None:
                raise RuntimeError(
                    f"Overpass request failed after {retries} attempts"
                ) from last_error
            if pause_s > 0:
                time.sleep(float(pause_s))

        parsed = parse_overpass_payload(payload, query_hash=digest)
        element_parts.append(parsed)
        logs.append(
            {
                "batch_index": int(start // batch_size),
                "anchor_count": int(len(batch)),
                "query_hash": digest,
                "cached": bool(cached),
                "element_count": int(len(parsed)),
                "endpoint": endpoint,
                "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            }
        )

    elements = (
        pd.concat(element_parts, ignore_index=True)
        if element_parts
        else parse_overpass_payload({})
    )
    if not elements.empty:
        elements = (
            elements.sort_values(["osm_type", "osm_id"], kind="stable")
            .drop_duplicates(["osm_type", "osm_id"], keep="first")
            .reset_index(drop=True)
        )
    return elements, pd.DataFrame(logs)


def _haversine_m(
    lat1: float,
    lon1: float,
    lat2: np.ndarray,
    lon2: np.ndarray,
) -> np.ndarray:
    radius = 6_371_008.8
    phi1 = math.radians(float(lat1))
    phi2 = np.radians(lon2 * 0 + lat2)
    dphi = np.radians(lat2 - float(lat1))
    dlambda = np.radians(lon2 - float(lon1))
    a = (
        np.sin(dphi / 2.0) ** 2
        + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * radius * np.arcsin(np.minimum(1.0, np.sqrt(a)))


def attach_elements_to_anchors(
    anchors: pd.DataFrame,
    elements: pd.DataFrame,
    *,
    radius_m: int = DEFAULT_QUERY_RADIUS_M,
) -> pd.DataFrame:
    """Attach OSM elements to every anchor whose center lies within radius."""
    columns = [
        "anchor_key",
        "user_id",
        "location_id",
        "osm_type",
        "osm_id",
        "distance_m",
        "tags",
    ]
    if anchors.empty or elements.empty:
        return pd.DataFrame(columns=columns)

    elem_lat = pd.to_numeric(elements["latitude"], errors="coerce").to_numpy(float)
    elem_lon = pd.to_numeric(elements["longitude"], errors="coerce").to_numpy(float)
    rows = []

    for anchor in anchors.itertuples(index=False):
        distances = _haversine_m(
            float(anchor.latitude),
            float(anchor.longitude),
            elem_lat,
            elem_lon,
        )
        indexes = np.flatnonzero(np.isfinite(distances) & (distances <= radius_m))
        for index in indexes:
            element = elements.iloc[int(index)]
            rows.append(
                {
                    "anchor_key": str(anchor.anchor_key),
                    "user_id": str(anchor.user_id),
                    "location_id": int(anchor.location_id),
                    "osm_type": str(element.osm_type),
                    "osm_id": int(element.osm_id),
                    "distance_m": float(distances[index]),
                    "tags": element.tags,
                }
            )

    return pd.DataFrame(rows, columns=columns)


def classify_osm_tags(tags: dict | None) -> tuple[str, ...]:
    """Map OSM tags to coarse, non-exclusive context categories."""
    tags = tags or {}
    amenity = str(tags.get("amenity", "")).lower()
    building = str(tags.get("building", "")).lower()
    landuse = str(tags.get("landuse", "")).lower()
    railway = str(tags.get("railway", "")).lower()
    public_transport = str(tags.get("public_transport", "")).lower()
    highway = str(tags.get("highway", "")).lower()
    office = str(tags.get("office", "")).lower()
    shop = str(tags.get("shop", "")).lower()
    craft = str(tags.get("craft", "")).lower()
    healthcare = str(tags.get("healthcare", "")).lower()
    tourism = str(tags.get("tourism", "")).lower()
    leisure = str(tags.get("leisure", "")).lower()
    industrial = str(tags.get("industrial", "")).lower()
    man_made = str(tags.get("man_made", "")).lower()

    categories: set[str] = set()

    if landuse == "residential" or building in RESIDENTIAL_BUILDINGS:
        categories.add("residential")

    if (
        office not in {"", "no"}
        or landuse in {"commercial", "retail"}
        or building in OFFICE_BUILDINGS
        or amenity == "coworking_space"
    ):
        categories.add("office_commercial")

    if (
        amenity in EDUCATION_AMENITIES
        or building in EDUCATION_BUILDINGS
        or landuse == "education"
    ):
        categories.add("education")

    if (
        amenity in HEALTHCARE_AMENITIES
        or healthcare not in {"", "no"}
        or building in HEALTHCARE_BUILDINGS
    ):
        categories.add("healthcare")

    if (
        landuse == "industrial"
        or building in INDUSTRIAL_BUILDINGS
        or industrial not in {"", "no"}
        or man_made == "works"
    ):
        categories.add("industrial")

    if (
        shop not in {"", "no"}
        or craft not in {"", "no"}
        or amenity in RETAIL_SERVICE_AMENITIES
        or building in RETAIL_BUILDINGS
        or tourism in {"hotel", "hostel", "motel", "guest_house"}
    ):
        categories.add("retail_service")

    if (
        amenity in TRANSPORT_AMENITIES
        or railway in TRANSPORT_RAILWAY_VALUES
        or public_transport not in {"", "no"}
        or highway == "bus_stop"
        or building in TRANSPORT_BUILDINGS
    ):
        categories.add("transport")

    if (
        amenity in CIVIC_AMENITIES
        or building in CIVIC_BUILDINGS
        or landuse in {"institutional", "civic_admin"}
        or office == "government"
    ):
        categories.add("civic_institutional")

    if leisure not in {"", "no"} or (
        tourism not in {"", "no"}
        and tourism not in {"hotel", "hostel", "motel", "guest_house"}
    ):
        categories.add("recreation_tourism")

    return tuple(sorted(categories))


def enrich_element_categories(links: pd.DataFrame) -> pd.DataFrame:
    if links.empty:
        out = links.copy()
        out["categories"] = pd.Series(dtype=object)
        return out
    out = links.copy()
    out["categories"] = out["tags"].map(classify_osm_tags)
    return out


def aggregate_anchor_context(
    anchors: pd.DataFrame,
    links: pd.DataFrame,
    *,
    radii_m: Iterable[int] = (PRIMARY_RADIUS_M, SENSITIVITY_RADIUS_M),
) -> pd.DataFrame:
    """Aggregate non-exclusive category evidence at one or more radii."""
    result = anchors.copy()
    categorized = enrich_element_categories(links)
    radii = tuple(sorted({int(radius) for radius in radii_m}))
    if any(radius <= 0 for radius in radii):
        raise ValueError("radii_m must contain positive values")

    for radius in radii:
        suffix = f"{radius}m"
        result[f"osm_object_count_{suffix}"] = 0
        for category in CONTEXT_CATEGORIES:
            result[f"{category}_present_{suffix}"] = False
            result[f"{category}_object_count_{suffix}"] = 0
            result[f"{category}_nearest_m_{suffix}"] = np.nan

        for index, anchor in result.iterrows():
            subset = categorized.loc[
                categorized["anchor_key"].eq(anchor["anchor_key"])
                & pd.to_numeric(categorized["distance_m"], errors="coerce").le(radius)
            ]
            result.at[index, f"osm_object_count_{suffix}"] = int(len(subset))
            for category in CONTEXT_CATEGORIES:
                mask = subset["categories"].map(lambda values: category in values)
                category_rows = subset.loc[mask]
                result.at[index, f"{category}_present_{suffix}"] = bool(len(category_rows))
                result.at[index, f"{category}_object_count_{suffix}"] = int(
                    len(category_rows)
                )
                if len(category_rows):
                    result.at[index, f"{category}_nearest_m_{suffix}"] = float(
                        pd.to_numeric(category_rows["distance_m"], errors="coerce").min()
                    )

        category_presence = [
            f"{category}_present_{suffix}" for category in CONTEXT_CATEGORIES
        ]
        result[f"semantic_category_count_{suffix}"] = (
            result[category_presence].fillna(False).astype(bool).sum(axis=1).astype(int)
        )
        work_presence = [
            f"{category}_present_{suffix}" for category in WORK_COMPATIBLE_CATEGORIES
        ]
        result[f"work_compatible_context_{suffix}"] = (
            result[work_presence].fillna(False).astype(bool).any(axis=1)
        )
        result[f"residential_context_{suffix}"] = result[
            f"residential_present_{suffix}"
        ].fillna(False).astype(bool)
        result[f"mixed_residential_work_context_{suffix}"] = (
            result[f"residential_context_{suffix}"]
            & result[f"work_compatible_context_{suffix}"]
        )
        result[f"residential_only_context_{suffix}"] = (
            result[f"residential_context_{suffix}"]
            & ~result[f"work_compatible_context_{suffix}"]
        )

        def signature(row: pd.Series) -> str:
            present = [
                category
                for category in CONTEXT_CATEGORIES
                if bool(row[f"{category}_present_{suffix}"])
            ]
            return "+".join(present) if present else "unknown"

        result[f"context_signature_{suffix}"] = result.apply(signature, axis=1)

    return result


def summarize_context_coverage(
    context: pd.DataFrame,
    *,
    radii_m: Iterable[int] = (PRIMARY_RADIUS_M, SENSITIVITY_RADIUS_M),
) -> pd.DataFrame:
    rows = []
    for radius in sorted({int(value) for value in radii_m}):
        suffix = f"{radius}m"
        semantic = _numeric(context, f"semantic_category_count_{suffix}").fillna(0).gt(0)
        objects = _numeric(context, f"osm_object_count_{suffix}").fillna(0).gt(0)
        rows.append(
            {
                "radius_m": radius,
                "candidate_anchors": int(len(context)),
                "candidate_users": int(context["user_id"].nunique()),
                "anchors_with_any_osm_object": int(objects.sum()),
                "anchors_with_semantic_category": int(semantic.sum()),
                "semantic_category_coverage_share": (
                    float(semantic.mean()) if len(context) else np.nan
                ),
                "users_with_semantic_category": int(
                    context.loc[semantic, "user_id"].nunique()
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_categories_by_cohort(
    context: pd.DataFrame,
    *,
    radius_m: int = PRIMARY_RADIUS_M,
) -> pd.DataFrame:
    suffix = f"{int(radius_m)}m"
    cohort_masks = {
        "all_candidate_anchors": pd.Series(True, index=context.index),
        "stable_secondary": _bool(context, "is_stable_secondary"),
        "repeated_route_anchor": _bool(context, "appears_in_repeated_edge"),
        "single_anchor_geometry_user": _bool(
            context, "candidate_single_anchor_geometry"
        ),
        "anchor_set_geometry_user": _bool(
            context, "candidate_anchor_set_geometry"
        ),
        "route_region_geometry_user": _bool(
            context, "candidate_route_region_geometry"
        ),
        "mobile_complexity_user": _bool(context, "mobile_complexity_evidence"),
    }
    rows = []
    for cohort, mask in cohort_masks.items():
        group = context.loc[mask]
        if group.empty:
            continue
        for category in CONTEXT_CATEGORIES:
            present = _bool(group, f"{category}_present_{suffix}")
            rows.append(
                {
                    "radius_m": int(radius_m),
                    "cohort": cohort,
                    "category": category,
                    "anchors": int(len(group)),
                    "users": int(group["user_id"].nunique()),
                    "present_anchors": int(present.sum()),
                    "present_share": float(present.mean()),
                }
            )
        for metric in (
            "work_compatible_context",
            "residential_context",
            "mixed_residential_work_context",
            "residential_only_context",
        ):
            present = _bool(group, f"{metric}_{suffix}")
            rows.append(
                {
                    "radius_m": int(radius_m),
                    "cohort": cohort,
                    "category": metric,
                    "anchors": int(len(group)),
                    "users": int(group["user_id"].nunique()),
                    "present_anchors": int(present.sum()),
                    "present_share": float(present.mean()),
                }
            )
    return pd.DataFrame(rows)


def compare_stable_secondary_to_peers(
    context: pd.DataFrame,
    *,
    radius_m: int = PRIMARY_RADIUS_M,
) -> pd.DataFrame:
    """Within-user external-context comparison for stable-secondary anchors."""
    suffix = f"{int(radius_m)}m"
    metrics = [
        *(f"{category}_present_{suffix}" for category in CONTEXT_CATEGORIES),
        f"work_compatible_context_{suffix}",
        f"residential_context_{suffix}",
        f"mixed_residential_work_context_{suffix}",
        f"residential_only_context_{suffix}",
        f"semantic_category_count_{suffix}",
    ]
    rows = []

    for user_id, group in context.groupby("user_id", sort=True):
        candidate = group.loc[_bool(group, "is_stable_secondary")]
        peers = group.loc[~_bool(group, "is_stable_secondary")]
        if len(candidate) != 1 or peers.empty:
            continue
        candidate = candidate.iloc[0]
        row = {
            "user_id": str(user_id),
            "candidate_location_id": int(candidate["location_id"]),
            "peer_anchor_count": int(len(peers)),
        }
        for metric in metrics:
            if metric not in group.columns:
                continue
            candidate_value = candidate[metric]
            if isinstance(candidate_value, (bool, np.bool_)):
                candidate_numeric = float(bool(candidate_value))
                peer_values = peers[metric].fillna(False).astype(bool).astype(float)
            else:
                candidate_numeric = float(pd.to_numeric(
                    pd.Series([candidate_value]), errors="coerce"
                ).iloc[0])
                peer_values = pd.to_numeric(peers[metric], errors="coerce").dropna()
            peer_mean = float(peer_values.mean()) if len(peer_values) else np.nan
            row[f"{metric}__candidate"] = candidate_numeric
            row[f"{metric}__peer_mean"] = peer_mean
            row[f"{metric}__difference"] = (
                candidate_numeric - peer_mean
                if np.isfinite(candidate_numeric) and np.isfinite(peer_mean)
                else np.nan
            )
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_stable_secondary_peer(
    comparison: pd.DataFrame,
    *,
    radius_m: int = PRIMARY_RADIUS_M,
) -> pd.DataFrame:
    if comparison.empty:
        return pd.DataFrame()
    suffix = f"{int(radius_m)}m"
    metrics = [
        *(f"{category}_present_{suffix}" for category in CONTEXT_CATEGORIES),
        f"work_compatible_context_{suffix}",
        f"residential_context_{suffix}",
        f"mixed_residential_work_context_{suffix}",
        f"residential_only_context_{suffix}",
        f"semantic_category_count_{suffix}",
    ]
    rows = []
    for metric in metrics:
        candidate_col = f"{metric}__candidate"
        peer_col = f"{metric}__peer_mean"
        diff_col = f"{metric}__difference"
        if candidate_col not in comparison:
            continue
        candidate = pd.to_numeric(comparison[candidate_col], errors="coerce")
        peer = pd.to_numeric(comparison[peer_col], errors="coerce")
        diff = pd.to_numeric(comparison[diff_col], errors="coerce")
        valid = candidate.notna() & peer.notna() & diff.notna()
        rows.append(
            {
                "radius_m": int(radius_m),
                "metric": metric.removesuffix(f"_{suffix}"),
                "users": int(valid.sum()),
                "candidate_mean": float(candidate.loc[valid].mean()) if valid.any() else np.nan,
                "median_peer_mean": float(peer.loc[valid].median()) if valid.any() else np.nan,
                "median_candidate_minus_peer": float(diff.loc[valid].median()) if valid.any() else np.nan,
                "candidate_gt_peer_users": int((diff.loc[valid] > 0).sum()),
                "candidate_lt_peer_users": int((diff.loc[valid] < 0).sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_signatures(
    context: pd.DataFrame,
    *,
    radius_m: int = PRIMARY_RADIUS_M,
) -> pd.DataFrame:
    column = f"context_signature_{int(radius_m)}m"
    if context.empty:
        return pd.DataFrame(
            columns=["radius_m", "context_signature", "anchors", "users"]
        )
    return (
        context.groupby(column, as_index=False)
        .agg(
            anchors=("anchor_key", "size"),
            users=("user_id", "nunique"),
        )
        .rename(columns={column: "context_signature"})
        .assign(radius_m=int(radius_m))
        .sort_values(["anchors", "context_signature"], ascending=[False, True])
        .reset_index(drop=True)
    )


def summarize_radius_sensitivity(
    context: pd.DataFrame,
    *,
    primary_radius_m: int = PRIMARY_RADIUS_M,
    sensitivity_radius_m: int = SENSITIVITY_RADIUS_M,
) -> pd.DataFrame:
    p = f"{int(primary_radius_m)}m"
    s = f"{int(sensitivity_radius_m)}m"
    rows = []
    for metric in (
        "work_compatible_context",
        "residential_context",
        "mixed_residential_work_context",
        "residential_only_context",
    ):
        primary = _bool(context, f"{metric}_{p}")
        sensitivity = _bool(context, f"{metric}_{s}")
        rows.append(
            {
                "metric": metric,
                "anchors": int(len(context)),
                "primary_radius_m": int(primary_radius_m),
                "sensitivity_radius_m": int(sensitivity_radius_m),
                "primary_present": int(primary.sum()),
                "sensitivity_present": int(sensitivity.sum()),
                "gained_at_sensitivity_radius": int((~primary & sensitivity).sum()),
                "lost_at_sensitivity_radius": int((primary & ~sensitivity).sum()),
            }
        )
    return pd.DataFrame(rows)


def run_audit_from_elements(
    candidate_anchors: pd.DataFrame,
    osm_elements: pd.DataFrame,
    *,
    query_radius_m: int = DEFAULT_QUERY_RADIUS_M,
    radii_m: Iterable[int] = (PRIMARY_RADIUS_M, SENSITIVITY_RADIUS_M),
    request_log: pd.DataFrame | None = None,
) -> ExternalContextAudit:
    links = attach_elements_to_anchors(
        candidate_anchors,
        osm_elements,
        radius_m=query_radius_m,
    )
    context = aggregate_anchor_context(
        candidate_anchors,
        links,
        radii_m=radii_m,
    )
    primary = min(int(value) for value in radii_m)
    sensitivity = max(int(value) for value in radii_m)
    peer = compare_stable_secondary_to_peers(
        context,
        radius_m=primary,
    )
    return ExternalContextAudit(
        candidate_anchors=candidate_anchors,
        osm_elements=osm_elements,
        anchor_element_links=links,
        anchor_context=context,
        coverage_summary=summarize_context_coverage(
            context,
            radii_m=radii_m,
        ),
        category_summary=summarize_categories_by_cohort(
            context,
            radius_m=primary,
        ),
        stable_secondary_peer=peer,
        stable_secondary_summary=summarize_stable_secondary_peer(
            peer,
            radius_m=primary,
        ),
        signature_summary=summarize_signatures(
            context,
            radius_m=primary,
        ),
        radius_sensitivity=summarize_radius_sensitivity(
            context,
            primary_radius_m=primary,
            sensitivity_radius_m=sensitivity,
        ),
        request_log=(
            request_log.copy()
            if request_log is not None
            else pd.DataFrame()
        ),
    )
