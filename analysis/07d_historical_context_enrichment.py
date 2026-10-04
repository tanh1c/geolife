"""Stage 07d: historical context enrichment.

Primary:
- exact-year CLCD physical context for every support-qualified anchor.

Optional cross-check:
- historical OpenStreetMap via ohsome snapshots at the anchor observation date.

Blocked semantic sources from Stage 07c are intentionally not loaded here.

This stage does not infer occupation, employment status, true WORK, or OFFICE.
"""

from __future__ import annotations

from io import BytesIO
import hashlib
import json
import math
from pathlib import Path
import time
from typing import Iterable

import numpy as np
import pandas as pd


CLCD_RECORD_ID = 8176941
CLCD_COG_BASE = f"https://zenodo.org/records/{CLCD_RECORD_ID}/files"
CLCD_LABELS = {
    1: "cropland",
    2: "forest",
    3: "shrub",
    4: "grassland",
    5: "water",
    6: "snow_ice",
    7: "barren",
    8: "impervious",
    9: "wetland",
}

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

OHSOME_API_DEFAULT = "https://api.heigit.org/ohsome-api/v2-rc"
OHSOME_START_DATE = pd.Timestamp("2007-10-08").date()

EDUCATION_AMENITIES = {
    "school", "university", "college", "kindergarten",
    "language_school", "music_school", "training", "driving_school",
}
HEALTHCARE_AMENITIES = {
    "hospital", "clinic", "doctors", "dentist", "pharmacy",
    "nursing_home", "social_facility",
}
RETAIL_SERVICE_AMENITIES = {
    "restaurant", "cafe", "fast_food", "food_court", "bar", "pub",
    "bank", "atm", "marketplace", "cinema", "theatre", "nightclub",
    "car_rental", "car_wash",
}
TRANSPORT_AMENITIES = {
    "bus_station", "taxi", "ferry_terminal", "parking",
    "parking_entrance", "bicycle_rental",
}
CIVIC_AMENITIES = {
    "police", "fire_station", "courthouse", "townhall", "post_office",
    "library", "community_centre", "social_centre", "place_of_worship",
    "public_building",
}
TRANSPORT_RAILWAY_VALUES = {
    "station", "halt", "tram_stop", "subway_entrance", "platform",
}
RESIDENTIAL_BUILDINGS = {
    "apartments", "residential", "house", "detached", "terrace",
    "semidetached_house", "dormitory",
}
OFFICE_BUILDINGS = {"office", "commercial"}
EDUCATION_BUILDINGS = {"school", "university", "college", "kindergarten"}
HEALTHCARE_BUILDINGS = {"hospital"}
INDUSTRIAL_BUILDINGS = {"industrial", "warehouse"}
RETAIL_BUILDINGS = {"retail"}
CIVIC_BUILDINGS = {"civic"}
TRANSPORT_BUILDINGS = {"train_station", "transportation"}




def attach_anchor_coordinates_from_locations(
    anchors: pd.DataFrame,
    locations: pd.DataFrame,
) -> pd.DataFrame:
    """Attach private centroids from the production semantic-location table."""
    required_anchor = {"user_id", "location_id"}
    missing = required_anchor.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors missing columns: {sorted(missing)}")

    required_locations = {
        "user_id",
        "location_id",
        "latitude",
        "longitude",
        "stay_count",
    }
    missing = required_locations.difference(locations.columns)
    if missing:
        raise ValueError(f"locations missing columns: {sorted(missing)}")

    left = anchors.copy()
    left["user_id"] = left["user_id"].astype(str)
    left["location_id"] = pd.to_numeric(
        left["location_id"], errors="raise"
    ).astype(int)

    loc = locations.copy()
    loc["user_id"] = loc["user_id"].astype(str)
    loc["location_id"] = pd.to_numeric(
        loc["location_id"], errors="raise"
    ).astype(int)
    loc["latitude"] = pd.to_numeric(loc["latitude"], errors="raise")
    loc["longitude"] = pd.to_numeric(loc["longitude"], errors="raise")
    loc["stay_count"] = pd.to_numeric(
        loc["stay_count"], errors="raise"
    ).astype(int)

    result = left.merge(
        loc[
            [
                "user_id",
                "location_id",
                "latitude",
                "longitude",
                "stay_count",
            ]
        ].rename(columns={"stay_count": "coordinate_stay_count"}),
        on=["user_id", "location_id"],
        how="left",
        validate="one_to_one",
    )
    if result[["latitude", "longitude"]].isna().any(axis=None):
        missing_rows = result.loc[
            result[["latitude", "longitude"]].isna().any(axis=1),
            ["user_id", "location_id"],
        ]
        raise ValueError(
            "could not attach production coordinates for all anchors: "
            f"{len(missing_rows)} missing"
        )
    return result


def attach_anchor_coordinates_from_clustered_stays(
    anchors: pd.DataFrame,
    clustered_stays: pd.DataFrame,
) -> pd.DataFrame:
    """Attach private anchor centroids from the frozen 200 m clustered stays.

    Stage 07c's dated-anchor artifact is coordinate-free by design/legacy.
    Stage 07d reconstructs coordinates privately from the same deterministic
    clustering so external joins can run without changing aggregate outputs.
    """
    required_anchor = {"user_id", "location_id"}
    missing = required_anchor.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors missing columns: {sorted(missing)}")

    required_stays = {"user_id", "location_id", "latitude", "longitude"}
    missing = required_stays.difference(clustered_stays.columns)
    if missing:
        raise ValueError(f"clustered_stays missing columns: {sorted(missing)}")

    left = anchors.copy()
    left["user_id"] = left["user_id"].astype(str)
    left["location_id"] = pd.to_numeric(left["location_id"], errors="raise").astype(int)

    stays = clustered_stays.copy()
    stays["user_id"] = stays["user_id"].astype(str)
    stays["location_id"] = pd.to_numeric(stays["location_id"], errors="raise").astype(int)
    stays["latitude"] = pd.to_numeric(stays["latitude"], errors="raise")
    stays["longitude"] = pd.to_numeric(stays["longitude"], errors="raise")

    centroids = (
        stays.groupby(["user_id", "location_id"], as_index=False)
        .agg(
            latitude=("latitude", "median"),
            longitude=("longitude", "median"),
            coordinate_stay_count=("latitude", "size"),
        )
    )

    result = left.merge(
        centroids,
        on=["user_id", "location_id"],
        how="left",
        validate="one_to_one",
    )

    if result[["latitude", "longitude"]].isna().any(axis=None):
        missing_rows = result.loc[
            result[["latitude", "longitude"]].isna().any(axis=1),
            ["user_id", "location_id"],
        ]
        raise ValueError(
            "could not reconstruct coordinates for all anchors: "
            f"{len(missing_rows)} missing"
        )

    return result


def clcd_cog_url(year: int) -> str:
    year = int(year)
    if year < 1985 or year > 2022:
        raise ValueError("year outside the pinned CLCD v1.0.2 record range")
    return f"{CLCD_COG_BASE}/CLCD_v01_{year}_albert.tif?download=1"


def clcd_label(code: object) -> str:
    value = pd.to_numeric(pd.Series([code]), errors="coerce").iloc[0]
    if pd.isna(value):
        return "unknown"
    return CLCD_LABELS.get(int(value), "unknown")


def build_clcd_sampling_plan(anchors: pd.DataFrame) -> pd.DataFrame:
    required = {"median_observation_year"}
    missing = required.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors missing columns: {sorted(missing)}")
    years = (
        pd.to_numeric(anchors["median_observation_year"], errors="coerce")
        .dropna().astype(int)
    )
    rows = []
    for year in sorted(years.unique()):
        mask = years.eq(year)
        rows.append(
            {
                "year": int(year),
                "anchors": int(mask.sum()),
                "url": clcd_cog_url(int(year)),
            }
        )
    return pd.DataFrame(rows)


def _mode_code(values: np.ndarray, nodata: float | int | None = None) -> float:
    array = np.asarray(values).reshape(-1)
    array = array[np.isfinite(array)]
    if nodata is not None and np.isfinite(nodata):
        array = array[array != nodata]
    array = array[array > 0]
    if len(array) == 0:
        return np.nan
    unique, counts = np.unique(array.astype(int), return_counts=True)
    max_count = counts.max()
    return float(unique[counts == max_count].min())


def _sample_one_clcd_dataset(
    anchors: pd.DataFrame,
    dataset,
    *,
    local_windows: Iterable[int] = (3, 5),
) -> pd.DataFrame:
    """Sample point class and local modal classes from an open rasterio dataset."""
    from rasterio.windows import Window
    from rasterio.warp import transform as warp_transform

    required = {"user_id", "location_id", "latitude", "longitude"}
    missing = required.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors missing columns: {sorted(missing)}")

    lat = pd.to_numeric(anchors["latitude"], errors="raise").to_numpy(float)
    lon = pd.to_numeric(anchors["longitude"], errors="raise").to_numpy(float)

    target_crs = dataset.crs
    if target_crs is None:
        raise ValueError("CLCD raster has no CRS metadata")
    if str(target_crs).upper() in {"EPSG:4326", "OGC:CRS84"}:
        xs, ys = lon.tolist(), lat.tolist()
    else:
        xs, ys = warp_transform("EPSG:4326", target_crs, lon.tolist(), lat.tolist())

    rows = []
    for source_row, x, y in zip(anchors.itertuples(index=False), xs, ys, strict=True):
        row_index, col_index = dataset.index(float(x), float(y))
        point = dataset.read(
            1,
            window=Window(col_index, row_index, 1, 1),
            boundless=True,
            fill_value=dataset.nodata if dataset.nodata is not None else 0,
        )
        point_code = _mode_code(point, dataset.nodata)
        result = {
            "user_id": str(source_row.user_id),
            "location_id": int(source_row.location_id),
            "clcd_year": int(source_row.median_observation_year),
            "clcd_point_code": point_code,
            "clcd_point_class": clcd_label(point_code),
        }
        for window_size in local_windows:
            window_size = int(window_size)
            if window_size <= 0 or window_size % 2 == 0:
                raise ValueError("local_windows must contain positive odd integers")
            half = window_size // 2
            data = dataset.read(
                1,
                window=Window(
                    col_index - half,
                    row_index - half,
                    window_size,
                    window_size,
                ),
                boundless=True,
                fill_value=dataset.nodata if dataset.nodata is not None else 0,
            )
            code = _mode_code(data, dataset.nodata)
            result[f"clcd_mode_{window_size}x{window_size}_code"] = code
            result[f"clcd_mode_{window_size}x{window_size}_class"] = clcd_label(code)
        rows.append(result)

    out = pd.DataFrame(rows)
    if not out.empty:
        out["clcd_point_equals_3x3"] = (
            out["clcd_point_class"].eq(out["clcd_mode_3x3_class"])
            if "clcd_mode_3x3_class" in out
            else pd.NA
        )
        out["clcd_point_equals_5x5"] = (
            out["clcd_point_class"].eq(out["clcd_mode_5x5_class"])
            if "clcd_mode_5x5_class" in out
            else pd.NA
        )
        out["clcd_impervious_point"] = out["clcd_point_class"].eq("impervious")
    return out


def sample_clcd_remote(
    anchors: pd.DataFrame,
    *,
    url_by_year: dict[int, str] | None = None,
    local_windows: Iterable[int] = (3, 5),
) -> pd.DataFrame:
    """Remote-sample pinned CLCD Cloud Optimized GeoTIFFs via rasterio.

    The pinned 2023 CLCD record states that files are COGs. Runtime must have
    rasterio/GDAL with HTTPS support. Exact coordinates stay in the caller's
    private anchor table and are not copied into the returned result.
    """
    import rasterio

    required = {"median_observation_year"}
    missing = required.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors missing columns: {sorted(missing)}")

    parts = []
    years = pd.to_numeric(anchors["median_observation_year"], errors="raise").astype(int)
    for year in sorted(years.unique()):
        group = anchors.loc[years.eq(year)].copy()
        url = (
            url_by_year[int(year)]
            if url_by_year and int(year) in url_by_year
            else clcd_cog_url(int(year))
        )
        env_options = {
            "GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR",
            "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif",
            "GDAL_HTTP_MULTIRANGE": "YES",
        }
        with rasterio.Env(**env_options):
            with rasterio.open(url) as dataset:
                sampled = _sample_one_clcd_dataset(
                    group,
                    dataset,
                    local_windows=local_windows,
                )
                sampled["clcd_source_url"] = url
                sampled["clcd_raster_crs"] = str(dataset.crs)
                sampled["clcd_pixel_width"] = float(dataset.transform.a)
                sampled["clcd_pixel_height"] = float(dataset.transform.e)
                parts.append(sampled)

    return pd.concat(parts, ignore_index=True) if parts else pd.DataFrame()


def summarize_clcd(samples: pd.DataFrame) -> pd.DataFrame:
    if samples.empty:
        return pd.DataFrame()
    return (
        samples.groupby(["clcd_year", "clcd_point_class"], as_index=False)
        .agg(
            anchors=("location_id", "size"),
            users=("user_id", "nunique"),
            point_3x3_agreement=("clcd_point_equals_3x3", "mean"),
            point_5x5_agreement=("clcd_point_equals_5x5", "mean"),
        )
        .sort_values(["clcd_year", "anchors"], ascending=[True, False])
        .reset_index(drop=True)
    )


def summarize_clcd_population(samples: pd.DataFrame) -> pd.DataFrame:
    if samples.empty:
        return pd.DataFrame()
    rows = []
    for metric, values in (
        ("point_class_known", samples["clcd_point_class"].ne("unknown")),
        ("point_impervious", samples["clcd_point_class"].eq("impervious")),
        ("point_equals_3x3", samples["clcd_point_equals_3x3"].fillna(False)),
        ("point_equals_5x5", samples["clcd_point_equals_5x5"].fillna(False)),
    ):
        rows.append(
            {
                "metric": metric,
                "anchors": int(len(samples)),
                "true_anchors": int(values.sum()),
                "share": float(values.mean()),
            }
        )
    return pd.DataFrame(rows)


def _bbox_around(lat: float, lon: float, radius_m: float) -> list[float]:
    if radius_m <= 0:
        raise ValueError("radius_m must be positive")
    lat_delta = radius_m / 111_320.0
    lon_scale = max(math.cos(math.radians(lat)), 1e-6)
    lon_delta = radius_m / (111_320.0 * lon_scale)
    return [
        float(lon - lon_delta),
        float(lat - lat_delta),
        float(lon + lon_delta),
        float(lat + lat_delta),
    ]


def ohsome_semantic_filter() -> str:
    return (
        "amenity=* or office=* or shop=* or craft=* or healthcare=* or "
        "landuse in (residential,commercial,retail,industrial,education,institutional,civic_admin,railway) or "
        "building in (apartments,residential,house,detached,terrace,semidetached_house,dormitory,"
        "office,commercial,retail,school,university,college,kindergarten,hospital,industrial,warehouse,"
        "civic,train_station,transportation) or "
        "railway in (station,halt,tram_stop,subway_entrance,platform) or "
        "public_transport=* or highway=bus_stop or tourism=* or leisure=* or "
        "industrial=* or man_made=works"
    )


def ohsome_eligible_anchors(anchors: pd.DataFrame) -> pd.DataFrame:
    """Return anchors whose median observation date is queryable by ohsome."""
    required = {"median_observation_date"}
    missing = required.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors missing columns: {sorted(missing)}")
    dates = pd.to_datetime(
        anchors["median_observation_date"],
        errors="raise",
    ).dt.date
    return anchors.loc[dates.ge(OHSOME_START_DATE)].copy()


def build_ohsome_request(
    anchor: pd.Series | dict,
    *,
    radius_m: float = 100.0,
) -> dict:
    row = dict(anchor)
    lat = float(row["latitude"])
    lon = float(row["longitude"])
    timestamp = pd.Timestamp(row["median_observation_date"])
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return {
        "aoi": _bbox_around(lat, lon, radius_m),
        "filter": ohsome_semantic_filter(),
        "time": timestamp.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "clip": True,
    }


def classify_osm_tags(tags: dict | None) -> tuple[str, ...]:
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


def _tags_to_dict(value) -> dict:
    if isinstance(value, dict):
        return value
    if value is None:
        return {}
    if isinstance(value, list):
        try:
            return dict(value)
        except Exception:
            return {}
    try:
        return dict(value)
    except Exception:
        return {}


def parse_ohsome_parquet(content: bytes) -> pd.DataFrame:
    import pyarrow.parquet as pq

    table = pq.read_table(BytesIO(content))
    try:
        frame = table.to_pandas(maps_as_pydicts="strict")
    except TypeError:
        frame = table.to_pandas()
    if "tags" not in frame.columns:
        frame["tags"] = [{} for _ in range(len(frame))]
    frame["tags"] = frame["tags"].map(_tags_to_dict)
    frame["categories"] = frame["tags"].map(classify_osm_tags)
    return frame


def _ohsome_cache_key(request_body: dict) -> str:
    payload = json.dumps(request_body, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:24]


def _summarize_ohsome_anchor(
    anchor: dict,
    content: bytes,
) -> tuple[dict[str, object], int]:
    features = parse_ohsome_parquet(content)
    active_categories = sorted(
        {
            category
            for values in features["categories"]
            for category in values
        }
    )
    category_set = set(active_categories)
    row: dict[str, object] = {
        "user_id": str(anchor["user_id"]),
        "location_id": int(anchor["location_id"]),
        "osm_snapshot_date": str(anchor["median_observation_date"]),
        "osm_feature_count": int(len(features)),
        "osm_context_signature": (
            "+".join(active_categories) if active_categories else "unknown"
        ),
        "osm_semantic_category_count": int(len(active_categories)),
        "osm_work_compatible_context": bool(
            category_set.intersection(WORK_COMPATIBLE_CATEGORIES)
        ),
        "osm_residential_context": "residential" in category_set,
    }
    for category in CONTEXT_CATEGORIES:
        row[f"osm_{category}_present"] = category in category_set
    return row, int(len(features))


def fetch_ohsome_context_with_fetcher(
    anchors: pd.DataFrame,
    *,
    fetcher,
    cache_dir: Path,
    radius_m: float = 100.0,
    pause_s: float = 0.0,
    max_new_requests_per_run: int | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Fetch historical OSM context using an injected fetcher.

    The fetcher may return raw Parquet bytes or a structured response dict:
      {
        "ok": bool,
        "status_code": int,
        "content": bytes | None,
        "retry_after": str | None,
        "rate_limit_reset": str | None,
        "error": str | None,
      }

    Free-tier safety:
    - every successful response is cached per anchor request;
    - max_new_requests_per_run bounds fresh API calls;
    - the first HTTP 429 stops additional fresh calls for this run;
    - cached anchors are still parsed;
    - partial context + request log are returned instead of failing the stage.
    """
    cache_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    logs = []
    new_requests = 0
    rate_limited = False

    for anchor in anchors.to_dict(orient="records"):
        body = build_ohsome_request(anchor, radius_m=radius_m)
        digest = _ohsome_cache_key(body)
        path = cache_dir / f"{digest}.parquet"
        cached = path.exists()

        if cached:
            content = path.read_bytes()
            status = "cached"
            status_code = 200
            retry_after = None
            rate_limit_reset = None
            error = None
        elif rate_limited:
            logs.append(
                {
                    "user_id": str(anchor["user_id"]),
                    "location_id": int(anchor["location_id"]),
                    "cache_key": digest,
                    "cached": False,
                    "status": "deferred_rate_limited",
                    "status_code": 429,
                    "retry_after": None,
                    "rate_limit_reset": None,
                    "feature_count": pd.NA,
                    "error": None,
                }
            )
            continue
        elif (
            max_new_requests_per_run is not None
            and new_requests >= int(max_new_requests_per_run)
        ):
            logs.append(
                {
                    "user_id": str(anchor["user_id"]),
                    "location_id": int(anchor["location_id"]),
                    "cache_key": digest,
                    "cached": False,
                    "status": "deferred_request_budget",
                    "status_code": pd.NA,
                    "retry_after": None,
                    "rate_limit_reset": None,
                    "feature_count": pd.NA,
                    "error": None,
                }
            )
            continue
        else:
            result = fetcher(body)
            new_requests += 1

            if isinstance(result, (bytes, bytearray)):
                content = bytes(result)
                status = "fetched"
                status_code = 200
                retry_after = None
                rate_limit_reset = None
                error = None
            elif isinstance(result, dict):
                status_code = int(result.get("status_code", 0) or 0)
                retry_after = result.get("retry_after")
                rate_limit_reset = result.get("rate_limit_reset")
                error = result.get("error")
                if status_code == 429:
                    rate_limited = True
                    logs.append(
                        {
                            "user_id": str(anchor["user_id"]),
                            "location_id": int(anchor["location_id"]),
                            "cache_key": digest,
                            "cached": False,
                            "status": "rate_limited",
                            "status_code": 429,
                            "retry_after": retry_after,
                            "rate_limit_reset": rate_limit_reset,
                            "feature_count": pd.NA,
                            "error": error,
                        }
                    )
                    continue
                if not bool(result.get("ok", False)):
                    logs.append(
                        {
                            "user_id": str(anchor["user_id"]),
                            "location_id": int(anchor["location_id"]),
                            "cache_key": digest,
                            "cached": False,
                            "status": "request_error",
                            "status_code": status_code,
                            "retry_after": retry_after,
                            "rate_limit_reset": rate_limit_reset,
                            "feature_count": pd.NA,
                            "error": error,
                        }
                    )
                    continue
                content = result.get("content")
                if not isinstance(content, (bytes, bytearray)):
                    raise TypeError("successful ohsome response must contain bytes")
                content = bytes(content)
                status = "fetched"
            else:
                raise TypeError("ohsome fetcher must return bytes or a response dict")

            path.write_bytes(content)
            if pause_s > 0:
                time.sleep(float(pause_s))

        try:
            row, feature_count = _summarize_ohsome_anchor(anchor, content)
        except Exception as exc:
            logs.append(
                {
                    "user_id": str(anchor["user_id"]),
                    "location_id": int(anchor["location_id"]),
                    "cache_key": digest,
                    "cached": bool(cached),
                    "status": "parse_error",
                    "status_code": status_code,
                    "retry_after": retry_after,
                    "rate_limit_reset": rate_limit_reset,
                    "feature_count": pd.NA,
                    "error": str(exc),
                }
            )
            continue

        rows.append(row)
        logs.append(
            {
                "user_id": str(anchor["user_id"]),
                "location_id": int(anchor["location_id"]),
                "cache_key": digest,
                "cached": bool(cached),
                "status": status,
                "status_code": status_code,
                "retry_after": retry_after,
                "rate_limit_reset": rate_limit_reset,
                "feature_count": int(feature_count),
                "error": error,
            }
        )

    return pd.DataFrame(rows), pd.DataFrame(logs)


def summarize_ohsome_run(
    anchors: pd.DataFrame,
    context: pd.DataFrame,
    request_log: pd.DataFrame,
) -> pd.DataFrame:
    total = int(len(anchors))
    completed = int(len(context))
    status_counts = (
        request_log["status"].value_counts(dropna=False).to_dict()
        if not request_log.empty and "status" in request_log.columns
        else {}
    )
    return pd.DataFrame(
        [
            {
                "anchor_target": total,
                "anchor_completed": completed,
                "completion_share": float(completed / total) if total else np.nan,
                "cached": int(status_counts.get("cached", 0)),
                "fetched_this_run": int(status_counts.get("fetched", 0)),
                "rate_limited": int(status_counts.get("rate_limited", 0)),
                "deferred_rate_limited": int(
                    status_counts.get("deferred_rate_limited", 0)
                ),
                "deferred_request_budget": int(
                    status_counts.get("deferred_request_budget", 0)
                ),
                "request_error": int(status_counts.get("request_error", 0)),
                "parse_error": int(status_counts.get("parse_error", 0)),
            }
        ]
    )

def fetch_ohsome_context(
    anchors: pd.DataFrame,
    *,
    api_key: str,
    cache_dir: Path,
    api_url: str = OHSOME_API_DEFAULT,
    radius_m: float = 100.0,
    pause_s: float = 0.25,
    timeout_s: float = 240.0,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Direct-key convenience wrapper for non-Modal runtimes."""
    if not api_key:
        raise ValueError("ohsome API key is required")
    import httpx

    endpoint = api_url.rstrip("/") + "/extraction/features.parquet"

    def fetcher(body: dict) -> bytes:
        response = httpx.post(
            endpoint,
            json=body,
            headers={"authorization": api_key},
            timeout=timeout_s,
        )
        response.raise_for_status()
        return response.content

    return fetch_ohsome_context_with_fetcher(
        anchors,
        fetcher=fetcher,
        cache_dir=cache_dir,
        radius_m=radius_m,
        pause_s=pause_s,
    )


def summarize_ohsome(context: pd.DataFrame) -> pd.DataFrame:
    if context.empty:
        return pd.DataFrame()
    rows = [
        {
            "metric": "anchors",
            "anchors": int(len(context)),
            "users": int(context["user_id"].nunique()),
            "share": 1.0,
        },
        {
            "metric": "semantic_context_found",
            "anchors": int(context["osm_semantic_category_count"].gt(0).sum()),
            "users": int(
                context.loc[
                    context["osm_semantic_category_count"].gt(0), "user_id"
                ].nunique()
            ),
            "share": float(context["osm_semantic_category_count"].gt(0).mean()),
        },
        {
            "metric": "work_compatible_context",
            "anchors": int(context["osm_work_compatible_context"].sum()),
            "users": int(
                context.loc[context["osm_work_compatible_context"], "user_id"].nunique()
            ),
            "share": float(context["osm_work_compatible_context"].mean()),
        },
        {
            "metric": "residential_context",
            "anchors": int(context["osm_residential_context"].sum()),
            "users": int(
                context.loc[context["osm_residential_context"], "user_id"].nunique()
            ),
            "share": float(context["osm_residential_context"].mean()),
        },
    ]
    return pd.DataFrame(rows)


def join_historical_context(
    anchors: pd.DataFrame,
    clcd_samples: pd.DataFrame,
    ohsome_context: pd.DataFrame | None = None,
) -> pd.DataFrame:
    keys = ["user_id", "location_id"]
    result = anchors.merge(
        clcd_samples,
        on=keys,
        how="left",
        validate="one_to_one",
        suffixes=("", "_clcd"),
    )
    if ohsome_context is not None and not ohsome_context.empty:
        result = result.merge(
            ohsome_context,
            on=keys,
            how="left",
            validate="one_to_one",
        )

    result["historical_semantic_claim_allowed"] = False
    result["occupation_inference_allowed"] = False
    result["clcd_is_physical_context_only"] = True
    return result
