"""Stage 07g: normalize BCL POI 2008 for the production Beijing study region.

Stage 07f verified:
- official Figshare source identity and CC BY 4.0 licence;
- extracted FileGDB container POI2008All.gdb;
- point layer POI2008CN;
- 6,039,158 source features;
- EPSG:4326;
- source fields PNAME, X, Y.

Stage 07g does NOT create semantic WORK/OFFICE labels. It creates a compact,
reproducible Parquet subset for the same geographic policy used by production
Home/Office inference: a 100 km radius around central Beijing.

Design:
1. coarse GDAL bbox pushdown into FileGDB;
2. exact Haversine <=100 km filter;
3. preserve raw PNAME / X / Y;
4. preserve geometry-derived lon/lat separately;
5. quantify geometry-vs-raw-X/Y consistency;
6. persist QC + hash manifest.

The output is an external historical context artifact, not ground truth.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import math
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from geolife.model import HomeOfficeConfig


EARTH_RADIUS_M = 6_371_008.8
SOURCE_ID = "bcl_poi_2008"
SOURCE_YEAR = 2008
SOURCE_LAYER = "POI2008CN"
SOURCE_CRS = "EPSG:4326"
SOURCE_FEATURE_COUNT_07F = 6_039_158
SOURCE_CONTAINER_KIND = "gdb"
OUTPUT_SCHEMA_VERSION = "bcl_poi_2008_beijing_100km_v1"
EXPECTED_07F_RUNNER_STATUS = "ready_for_normalization"

NORMALIZED_COLUMNS = [
    "poi_id",
    "pname_raw",
    "geom_lon",
    "geom_lat",
    "raw_x",
    "raw_y",
    "distance_to_beijing_km",
    "raw_geom_delta_m",
    "source_year",
    "source_layer",
    "source_crs",
]

POINT_WKT_RE = re.compile(
    r"^\s*POINT(?:\s+(?:Z|M|ZM))?\s*\(\s*"
    r"([-+0-9.eE]+)\s+([-+0-9.eE]+)"
)


@dataclass(frozen=True)
class StudyRegion:
    latitude: float
    longitude: float
    radius_km: float
    name: str = "production_beijing_100km"

    @property
    def radius_m(self) -> float:
        return float(self.radius_km) * 1000.0


@dataclass(frozen=True)
class NormalizationDecision:
    source_handoff_status: str
    schema_status: str
    spatial_filter_status: str
    output_integrity_status: str
    raw_xy_qc_status: str
    runner_status: str
    notes: str


def production_study_region() -> StudyRegion:
    cfg = HomeOfficeConfig()
    return StudyRegion(
        latitude=float(cfg.beijing_latitude),
        longitude=float(cfg.beijing_longitude),
        radius_km=float(cfg.beijing_radius_km),
    )


def study_region_bbox(region: StudyRegion) -> tuple[float, float, float, float]:
    """Return a conservative spherical lon/lat bbox enclosing the radius."""
    lat_rad = math.radians(region.latitude)
    angular = region.radius_m / EARTH_RADIUS_M

    min_lat = max(-math.pi / 2, lat_rad - angular)
    max_lat = min(math.pi / 2, lat_rad + angular)

    if min_lat <= -math.pi / 2 or max_lat >= math.pi / 2:
        min_lon, max_lon = -math.pi, math.pi
    else:
        ratio = math.sin(angular) / max(math.cos(lat_rad), 1e-12)
        ratio = min(1.0, max(-1.0, ratio))
        delta_lon = math.asin(ratio)
        lon_rad = math.radians(region.longitude)
        min_lon = lon_rad - delta_lon
        max_lon = lon_rad + delta_lon

    return (
        math.degrees(min_lon),
        math.degrees(min_lat),
        math.degrees(max_lon),
        math.degrees(max_lat),
    )


def haversine_m(
    latitude_a,
    longitude_a,
    latitude_b,
    longitude_b,
):
    lat1 = np.radians(np.asarray(latitude_a, dtype=float))
    lon1 = np.radians(np.asarray(longitude_a, dtype=float))
    lat2 = np.radians(np.asarray(latitude_b, dtype=float))
    lon2 = np.radians(np.asarray(longitude_b, dtype=float))

    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    )
    a = np.clip(a, 0.0, 1.0)
    return 2.0 * EARTH_RADIUS_M * np.arcsin(np.sqrt(a))


def parse_point_wkt(series: pd.Series) -> pd.DataFrame:
    extracted = series.astype("string").str.extract(POINT_WKT_RE)
    return pd.DataFrame(
        {
            "geom_lon": pd.to_numeric(extracted[0], errors="coerce"),
            "geom_lat": pd.to_numeric(extracted[1], errors="coerce"),
        },
        index=series.index,
    )


def normalize_bbox_chunk(
    frame: pd.DataFrame,
    *,
    region: StudyRegion | None = None,
    poi_id_start: int = 0,
) -> pd.DataFrame:
    """Normalize one GDAL bbox-filtered CSV chunk and exact-radius filter it."""
    reg = region or production_study_region()
    required = {"WKT", "PNAME", "X", "Y"}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"bbox chunk missing columns: {sorted(missing)}")

    geom = parse_point_wkt(frame["WKT"])
    raw_x = pd.to_numeric(frame["X"], errors="coerce")
    raw_y = pd.to_numeric(frame["Y"], errors="coerce")

    geometry_valid = (
        geom["geom_lon"].between(-180.0, 180.0)
        & geom["geom_lat"].between(-90.0, 90.0)
    )
    distance_m = np.full(len(frame), np.nan, dtype=float)
    valid_idx = geometry_valid.to_numpy()
    if valid_idx.any():
        distance_m[valid_idx] = haversine_m(
            geom.loc[geometry_valid, "geom_lat"].to_numpy(float),
            geom.loc[geometry_valid, "geom_lon"].to_numpy(float),
            reg.latitude,
            reg.longitude,
        )

    exact = geometry_valid & pd.Series(
        distance_m <= reg.radius_m + 1e-6,
        index=frame.index,
    )
    if not exact.any():
        return pd.DataFrame(columns=NORMALIZED_COLUMNS)

    selected = frame.loc[exact].copy()
    selected_geom = geom.loc[exact]
    selected_raw_x = raw_x.loc[exact]
    selected_raw_y = raw_y.loc[exact]
    selected_distance = distance_m[exact.to_numpy()]

    raw_valid = (
        selected_raw_x.between(-180.0, 180.0)
        & selected_raw_y.between(-90.0, 90.0)
    )
    raw_delta = np.full(len(selected), np.nan, dtype=float)
    raw_idx = raw_valid.to_numpy()
    if raw_idx.any():
        raw_delta[raw_idx] = haversine_m(
            selected_geom.loc[raw_valid, "geom_lat"].to_numpy(float),
            selected_geom.loc[raw_valid, "geom_lon"].to_numpy(float),
            selected_raw_y.loc[raw_valid].to_numpy(float),
            selected_raw_x.loc[raw_valid].to_numpy(float),
        )

    out = pd.DataFrame(
        {
            "poi_id": np.arange(
                int(poi_id_start),
                int(poi_id_start) + len(selected),
                dtype=np.int64,
            ),
            "pname_raw": selected["PNAME"].astype("string").array,
            "geom_lon": selected_geom["geom_lon"].to_numpy(float),
            "geom_lat": selected_geom["geom_lat"].to_numpy(float),
            "raw_x": selected_raw_x.to_numpy(float),
            "raw_y": selected_raw_y.to_numpy(float),
            "distance_to_beijing_km": selected_distance / 1000.0,
            "raw_geom_delta_m": raw_delta,
            "source_year": np.full(len(selected), SOURCE_YEAR, dtype=np.int16),
            "source_layer": pd.array(
                [SOURCE_LAYER] * len(selected),
                dtype="string",
            ),
            "source_crs": pd.array(
                [SOURCE_CRS] * len(selected),
                dtype="string",
            ),
        }
    )
    return out.loc[:, NORMALIZED_COLUMNS]


def build_ogr2ogr_bbox_command(
    *,
    gdb_path: str | Path,
    csv_path: str | Path,
    region: StudyRegion | None = None,
    layer: str = SOURCE_LAYER,
) -> list[str]:
    reg = region or production_study_region()
    min_lon, min_lat, max_lon, max_lat = study_region_bbox(reg)
    return [
        "ogr2ogr",
        "-f",
        "CSV",
        "-overwrite",
        "-spat",
        f"{min_lon:.12f}",
        f"{min_lat:.12f}",
        f"{max_lon:.12f}",
        f"{max_lat:.12f}",
        "-select",
        "PNAME,X,Y",
        "-lco",
        "GEOMETRY=AS_WKT",
        str(csv_path),
        str(gdb_path),
        str(layer),
    ]


def validate_07f_handoff(
    acquisition_manifest: dict[str, Any],
    worker_report: dict[str, Any],
) -> pd.DataFrame:
    gates = acquisition_manifest.get("gates") or {}
    status = str(gates.get("runner_status") or "")
    container_kind = str(worker_report.get("container_kind") or "")
    container_path = str(worker_report.get("container_path") or "")
    verification = acquisition_manifest.get("file_verification") or {}
    source_md5 = str(verification.get("md5") or "")

    if status != EXPECTED_07F_RUNNER_STATUS:
        raise ValueError(
            f"Stage 07f is not ready for normalization: {status!r}"
        )
    if container_kind != SOURCE_CONTAINER_KIND:
        raise ValueError(
            f"expected validated FileGDB container, got {container_kind!r}"
        )
    if not container_path.lower().endswith(".gdb"):
        raise ValueError(
            f"validated container path is not a .gdb directory: {container_path}"
        )
    if not source_md5:
        raise ValueError("Stage 07f manifest is missing verified source MD5")

    return pd.DataFrame(
        [
            {
                "stage07f_runner_status": status,
                "container_kind": container_kind,
                "container_path": container_path,
                "source_md5": source_md5,
                "source_size_bytes": verification.get("size_bytes"),
            }
        ]
    )


def normalization_fingerprint(
    *,
    source_md5: str,
    container_path: str,
    region: StudyRegion | None = None,
    layer: str = SOURCE_LAYER,
    schema_version: str = OUTPUT_SCHEMA_VERSION,
) -> str:
    reg = region or production_study_region()
    payload = {
        "source_md5": str(source_md5).lower(),
        "container_name": Path(container_path).name,
        "layer": str(layer),
        "source_crs": SOURCE_CRS,
        "region": asdict(reg),
        "schema_version": schema_version,
    }
    serialised = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return sha256(serialised).hexdigest()


def evaluate_normalization_qc(
    summary: dict[str, Any],
    *,
    region: StudyRegion | None = None,
) -> NormalizationDecision:
    reg = region or production_study_region()

    row_count = int(summary.get("row_count") or 0)
    invalid_geometry = int(summary.get("invalid_geometry_count") or 0)
    max_distance = pd.to_numeric(
        pd.Series([summary.get("max_distance_to_beijing_km")]),
        errors="coerce",
    ).iloc[0]
    schema_columns = list(summary.get("schema_columns") or [])
    parquet_exists = bool(summary.get("parquet_exists"))
    parquet_sha256 = str(summary.get("parquet_sha256") or "")
    raw_xy_valid = int(summary.get("raw_xy_valid_count") or 0)

    source_handoff_status = (
        "pass_stage07f_handoff"
        if summary.get("stage07f_handoff_ok") is True
        else "blocked_stage07f_handoff"
    )
    schema_status = (
        "pass_normalized_schema"
        if schema_columns == NORMALIZED_COLUMNS
        else "blocked_schema_mismatch"
    )
    spatial_filter_status = (
        "pass_exact_100km_filter"
        if (
            row_count > 0
            and invalid_geometry == 0
            and pd.notna(max_distance)
            and float(max_distance) <= reg.radius_km + 1e-6
        )
        else "blocked_spatial_filter_qc"
    )
    output_integrity_status = (
        "pass_parquet_hash"
        if parquet_exists and len(parquet_sha256) == 64
        else "blocked_output_integrity"
    )
    raw_xy_qc_status = (
        "measured_raw_xy_consistency"
        if raw_xy_valid > 0
        else "warning_no_valid_raw_xy"
    )

    hard_pass = all(
        value.startswith("pass_")
        for value in (
            source_handoff_status,
            schema_status,
            spatial_filter_status,
            output_integrity_status,
        )
    )
    runner_status = (
        "ready_for_anchor_context_audit"
        if hard_pass
        else "blocked"
    )
    notes = (
        "raw X/Y consistency is descriptive QC and does not override "
        "the FileGDB geometry or CRS"
    )
    return NormalizationDecision(
        source_handoff_status=source_handoff_status,
        schema_status=schema_status,
        spatial_filter_status=spatial_filter_status,
        output_integrity_status=output_integrity_status,
        raw_xy_qc_status=raw_xy_qc_status,
        runner_status=runner_status,
        notes=notes,
    )


def decision_frame(decision: NormalizationDecision) -> pd.DataFrame:
    return pd.DataFrame([decision.__dict__])


def build_normalization_manifest(
    *,
    fingerprint: str,
    source_md5: str,
    source_container_path: str,
    output_parquet_path: str,
    output_parquet_sha256: str,
    summary: dict[str, Any],
    decision: NormalizationDecision,
    region: StudyRegion | None = None,
) -> dict[str, Any]:
    reg = region or production_study_region()
    return {
        "source_id": SOURCE_ID,
        "source_year": SOURCE_YEAR,
        "source_layer": SOURCE_LAYER,
        "source_crs": SOURCE_CRS,
        "source_container_kind": SOURCE_CONTAINER_KIND,
        "source_container_path": source_container_path,
        "source_md5": source_md5,
        "normalization_fingerprint": fingerprint,
        "normalization_schema_version": OUTPUT_SCHEMA_VERSION,
        "study_region": asdict(reg),
        "output_parquet_path": output_parquet_path,
        "output_parquet_sha256": output_parquet_sha256,
        "summary": summary,
        "decision": decision.__dict__,
        "semantic_claim_allowed": False,
        "occupation_inference_allowed": False,
    }


def synthetic_self_check() -> dict[str, Any]:
    region = production_study_region()
    bbox = study_region_bbox(region)
    assert bbox[0] < region.longitude < bbox[2]
    assert bbox[1] < region.latitude < bbox[3]

    frame = pd.DataFrame(
        {
            "WKT": [
                f"POINT ({region.longitude} {region.latitude})",
                "POINT (130 50)",
            ],
            "PNAME": ["中心点", "far"],
            "X": [region.longitude, 130.0],
            "Y": [region.latitude, 50.0],
        }
    )
    out = normalize_bbox_chunk(frame, region=region)
    assert len(out) == 1
    assert out.iloc[0]["pname_raw"] == "中心点"
    assert float(out.iloc[0]["raw_geom_delta_m"]) < 1e-6

    fp1 = normalization_fingerprint(
        source_md5="abc",
        container_path="/x/POI2008All.gdb",
        region=region,
    )
    fp2 = normalization_fingerprint(
        source_md5="abc",
        container_path="/y/POI2008All.gdb",
        region=region,
    )
    assert fp1 == fp2
    return {"status": "ok", "schema_version": OUTPUT_SCHEMA_VERSION}
