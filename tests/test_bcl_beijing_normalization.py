from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json
import sys

import numpy as np
import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07g_bcl_beijing_normalization.py"
)


def _module():
    spec = spec_from_file_location("stage07g", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_production_region_matches_home_office_policy():
    module = _module()
    region = module.production_study_region()

    assert region.latitude == 39.9042
    assert region.longitude == 116.4074
    assert region.radius_km == 100.0


def test_region_bbox_contains_cardinal_radius_points():
    module = _module()
    region = module.production_study_region()
    min_lon, min_lat, max_lon, max_lat = module.study_region_bbox(region)

    assert min_lon < region.longitude < max_lon
    assert min_lat < region.latitude < max_lat

    north_lat = region.latitude + np.degrees(
        region.radius_m / module.EARTH_RADIUS_M
    )
    south_lat = region.latitude - np.degrees(
        region.radius_m / module.EARTH_RADIUS_M
    )
    assert max_lat >= north_lat - 1e-9
    assert min_lat <= south_lat + 1e-9


def test_parse_point_wkt_supports_point_and_point_z():
    module = _module()
    parsed = module.parse_point_wkt(
        pd.Series(
            [
                "POINT (116.4 39.9)",
                "POINT Z (116.5 40.0 12)",
                None,
            ]
        )
    )

    assert parsed.loc[0, "geom_lon"] == 116.4
    assert parsed.loc[0, "geom_lat"] == 39.9
    assert parsed.loc[1, "geom_lon"] == 116.5
    assert parsed.loc[1, "geom_lat"] == 40.0
    assert pd.isna(parsed.loc[2, "geom_lon"])


def test_normalize_chunk_applies_exact_radius_and_preserves_raw_fields():
    module = _module()
    region = module.production_study_region()

    near_lon = region.longitude
    near_lat = region.latitude
    far_lon = 130.0
    far_lat = 50.0

    frame = pd.DataFrame(
        {
            "WKT": [
                f"POINT ({near_lon} {near_lat})",
                f"POINT ({far_lon} {far_lat})",
            ],
            "PNAME": ["  原始名称  ", "far"],
            "X": [near_lon + 0.000001, far_lon],
            "Y": [near_lat, far_lat],
        }
    )

    out = module.normalize_bbox_chunk(
        frame,
        region=region,
        poi_id_start=10,
    )

    assert len(out) == 1
    assert out.iloc[0]["poi_id"] == 10
    assert out.iloc[0]["pname_raw"] == "  原始名称  "
    assert out.iloc[0]["source_year"] == 2008
    assert out.iloc[0]["source_layer"] == "POI2008CN"
    assert out.iloc[0]["source_crs"] == "EPSG:4326"
    assert out.iloc[0]["distance_to_beijing_km"] < 1e-6
    assert 0.0 < out.iloc[0]["raw_geom_delta_m"] < 1.0


def test_normalize_chunk_rejects_missing_required_columns():
    module = _module()

    try:
        module.normalize_bbox_chunk(
            pd.DataFrame({"PNAME": ["x"]})
        )
    except ValueError as exc:
        assert "missing columns" in str(exc)
    else:
        raise AssertionError("missing geometry/source coordinate columns must fail")


def test_ogr2ogr_command_uses_bbox_pushdown_and_preserves_wkt():
    module = _module()
    command = module.build_ogr2ogr_bbox_command(
        gdb_path="/data/POI2008All.gdb",
        csv_path="/tmp/bbox.csv",
    )
    joined = " ".join(command)

    assert command[0] == "ogr2ogr"
    assert "-spat" in command
    assert "PNAME,X,Y" in command
    assert "GEOMETRY=AS_WKT" in command
    assert "/data/POI2008All.gdb" in command
    assert "POI2008CN" in command


def test_validate_07f_handoff_requires_ready_gdb_and_md5():
    module = _module()
    manifest = {
        "gates": {"runner_status": "ready_for_normalization"},
        "file_verification": {
            "md5": "abc123",
            "size_bytes": 120023687,
        },
    }
    report = {
        "container_kind": "gdb",
        "container_path": "/mnt/data/POI2008All.gdb",
    }

    result = module.validate_07f_handoff(manifest, report).iloc[0]

    assert result["container_kind"] == "gdb"
    assert result["source_md5"] == "abc123"


def test_validate_07f_handoff_rejects_non_ready_source():
    module = _module()
    manifest = {
        "gates": {"runner_status": "blocked"},
        "file_verification": {"md5": "abc"},
    }
    report = {
        "container_kind": "gdb",
        "container_path": "/mnt/data/POI2008All.gdb",
    }

    try:
        module.validate_07f_handoff(manifest, report)
    except ValueError as exc:
        assert "not ready" in str(exc)
    else:
        raise AssertionError("blocked Stage 07f handoff must fail")


def test_fingerprint_is_path_independent_but_source_sensitive():
    module = _module()

    a = module.normalization_fingerprint(
        source_md5="aaa",
        container_path="/a/POI2008All.gdb",
    )
    b = module.normalization_fingerprint(
        source_md5="aaa",
        container_path="/b/POI2008All.gdb",
    )
    c = module.normalization_fingerprint(
        source_md5="bbb",
        container_path="/b/POI2008All.gdb",
    )

    assert a == b
    assert a != c


def test_normalization_qc_passes_complete_valid_summary():
    module = _module()
    summary = {
        "stage07f_handoff_ok": True,
        "row_count": 100,
        "invalid_geometry_count": 0,
        "max_distance_to_beijing_km": 99.999,
        "schema_columns": module.NORMALIZED_COLUMNS,
        "parquet_exists": True,
        "parquet_sha256": "a" * 64,
        "raw_xy_valid_count": 99,
    }

    decision = module.evaluate_normalization_qc(summary)

    assert decision.source_handoff_status == "pass_stage07f_handoff"
    assert decision.schema_status == "pass_normalized_schema"
    assert decision.spatial_filter_status == "pass_exact_100km_filter"
    assert decision.output_integrity_status == "pass_parquet_hash"
    assert decision.runner_status == "ready_for_anchor_context_audit"


def test_normalization_qc_blocks_out_of_radius_output():
    module = _module()
    summary = {
        "stage07f_handoff_ok": True,
        "row_count": 100,
        "invalid_geometry_count": 0,
        "max_distance_to_beijing_km": 100.01,
        "schema_columns": module.NORMALIZED_COLUMNS,
        "parquet_exists": True,
        "parquet_sha256": "a" * 64,
        "raw_xy_valid_count": 99,
    }

    decision = module.evaluate_normalization_qc(summary)

    assert decision.spatial_filter_status == "blocked_spatial_filter_qc"
    assert decision.runner_status == "blocked"


def test_manifest_keeps_semantic_claims_disabled():
    module = _module()
    decision = module.NormalizationDecision(
        source_handoff_status="pass_stage07f_handoff",
        schema_status="pass_normalized_schema",
        spatial_filter_status="pass_exact_100km_filter",
        output_integrity_status="pass_parquet_hash",
        raw_xy_qc_status="measured_raw_xy_consistency",
        runner_status="ready_for_anchor_context_audit",
        notes="",
    )

    manifest = module.build_normalization_manifest(
        fingerprint="f" * 64,
        source_md5="abc",
        source_container_path="/x/POI2008All.gdb",
        output_parquet_path="/x/out.parquet",
        output_parquet_sha256="a" * 64,
        summary={"row_count": 1},
        decision=decision,
    )

    assert manifest["semantic_claim_allowed"] is False
    assert manifest["occupation_inference_allowed"] is False


def test_synthetic_self_check():
    module = _module()
    assert module.synthetic_self_check()["status"] == "ok"


def test_stage07g_notebook_contract():
    path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07g_bcl_beijing_normalization.ipynb"
    )
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    required = [
        "validate_07f_handoff",
        "GEOLIFE_MODAL_VOLUME_NAME",
        "modal.Volume.from_name",
        "ogr2ogr",
        "GEOMETRY=AS_WKT",
        "chunksize",
        "ParquetWriter",
        "distance_to_beijing_km",
        "raw_geom_delta_m",
        "normalization_fingerprint",
        "ready_for_anchor_context_audit",
    ]
    for snippet in required:
        assert snippet in code

    assert "WORK" not in code
    assert "OFFICE" not in code


def test_normalize_chunk_preserves_null_name_as_nullable_string():
    module = _module()
    region = module.production_study_region()
    frame = pd.DataFrame(
        {
            "WKT": [f"POINT ({region.longitude} {region.latitude})"],
            "PNAME": [None],
            "X": [region.longitude],
            "Y": [region.latitude],
        }
    )

    out = module.normalize_bbox_chunk(frame, region=region)

    assert len(out) == 1
    assert pd.isna(out.iloc[0]["pname_raw"])
