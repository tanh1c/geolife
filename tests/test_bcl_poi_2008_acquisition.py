from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import json
import sys

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07f_bcl_poi_2008_acquisition.py"
)


def _module():
    spec = spec_from_file_location("stage07f", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_figshare_file_parser_and_candidate_selection():
    module = _module()
    metadata = {
        "files": [
            {
                "id": 2,
                "name": "notes.txt",
                "size": 4,
                "download_url": "https://example/notes.txt",
            },
            {
                "id": 1,
                "name": "poi2008.zip",
                "size": 100,
                "download_url": "https://example/poi2008.zip",
                "computed_md5": "abc",
            },
        ]
    }

    files = module.figshare_files(metadata)
    candidate = module.select_public_download_candidate(metadata)

    assert len(files) == 2
    assert candidate is not None
    assert candidate["name"] == "poi2008.zip"


def test_missing_file_keeps_runner_blocked_even_with_metadata():
    module = _module()
    metadata = {
        "id": module.FIGSHARE_ARTICLE_ID,
        "title": "Points of interest of China in 2008",
        "doi": module.FIGSHARE_DOI,
        "license": {"name": "CC BY 4.0"},
        "files": [],
    }

    decision = module.evaluate_acquisition_gates(
        metadata,
        http_status=200,
    )

    assert decision.metadata_access == "pass_public_metadata_identity"
    assert decision.file_access == "blocked_no_file_available"
    assert decision.runner_status == "blocked"


def test_manual_mdb_can_pass_file_and_format_gate_but_not_crs():
    module = _module()
    metadata = {
        "id": module.FIGSHARE_ARTICLE_ID,
        "doi": module.FIGSHARE_DOI,
        "license": {"name": "CC BY 4.0"},
        "files": [],
    }

    decision = module.evaluate_acquisition_gates(
        metadata,
        http_status=200,
        local_candidate_files=["/mnt/geolife-data/external/bcl/poi.mdb"],
    )

    assert decision.file_access == "pass_manual_or_cached_file"
    assert decision.format_status == "pass_mdb"
    assert decision.crs_status == "blocked_pending_mdb_crs_inspection"
    assert decision.runner_status == "ready_for_mdb_inspection"


def test_ambiguous_license_stays_blocked():
    module = _module()
    metadata = {
        "id": module.FIGSHARE_ARTICLE_ID,
        "doi": module.FIGSHARE_DOI,
        "license": {"name": "Custom terms"},
        "files": [
            {
                "id": 1,
                "name": "poi.mdb",
                "download_url": "https://example/poi.mdb",
            }
        ],
    }

    decision = module.evaluate_acquisition_gates(
        metadata,
        http_status=200,
        inspected_crs="EPSG:4326",
    )

    assert decision.license_status.startswith(
        "blocked_unreviewed_explicit_license"
    )
    assert decision.runner_status == "blocked"


def test_verify_download_checks_size_and_hash(tmp_path):
    module = _module()
    path = tmp_path / "x.bin"
    path.write_bytes(b"abc")

    result = module.verify_download(
        path,
        expected_size=3,
        expected_md5="900150983cd24fb0d6963f7d28e17f72",
    )

    assert result["exists"]
    assert result["size_ok"]
    assert result["md5_ok"]
    assert len(result["sha256"]) == 64


def test_safe_member_path_rejects_archive_traversal(tmp_path):
    module = _module()

    try:
        module.safe_member_path(tmp_path, "../escape.mdb")
    except ValueError as exc:
        assert "unsafe archive path" in str(exc)
    else:
        raise AssertionError("path traversal must be rejected")


def test_parse_ogrinfo_report_extracts_geometry_fields_and_srs():
    module = _module()
    report = module.parse_ogrinfo_report(
        """Layer name: POI
Geometry: Point
Feature Count: 6,123,456
Extent: (73.0, 18.0) - (135.0, 54.0)
Layer SRS WKT:
GEOGCRS["WGS 84",
    ID["EPSG",4326]]
FID Column = OBJECTID
Geometry Column = Shape
name: String (255.0)
x: Real (0.0)
y: Real (0.0)
"""
    )

    assert report["layers"] == ["POI"]
    assert report["geometry_types"] == ["Point"]
    assert report["feature_counts"] == [6123456]
    assert report["layer_count"] == 1
    assert set(report["field_names"]) == {"name", "x", "y"}
    assert report["srs_blocks"]
    assert report["epsg_codes"] == ["4326"]


def test_bcl_eligible_anchor_summary_uses_corrected_namespace():
    module = _module()
    anchors = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "median_observation_year": 2008,
                "location_namespace": module.EXPECTED_LOCATION_NAMESPACE,
            },
            {
                "user_id": "u2",
                "location_id": 1,
                "median_observation_year": 2009,
                "location_namespace": module.EXPECTED_LOCATION_NAMESPACE,
            },
            {
                "user_id": "u3",
                "location_id": 1,
                "median_observation_year": 2011,
                "location_namespace": module.EXPECTED_LOCATION_NAMESPACE,
            },
        ]
    )

    result = module.build_bcl_eligible_anchor_summary(anchors).iloc[0]

    assert result["candidate_anchors"] == 3
    assert result["bcl_eligible_anchors"] == 2
    assert result["bcl_exact_2008_anchors"] == 1
    assert result["bcl_proxy_anchors"] == 1


def test_acquisition_manifest_keeps_semantic_claims_disabled(tmp_path):
    module = _module()
    metadata_summary = pd.DataFrame(
        [
            {
                "article_id": module.FIGSHARE_ARTICLE_ID,
                "license_name": "CC BY 4.0",
            }
        ]
    )
    decision = module.GateDecision(
        metadata_access="pass_public_metadata",
        file_access="pass_public_file",
        license_status="pass_explicit:CC BY 4.0",
        format_status="pass_mdb",
        structure_status="pass_spatial_point_structure",
        crs_status="pass_inspected_crs",
        runner_status="ready_for_normalization",
        notes="",
    )

    manifest = module.acquisition_manifest(
        source_mode="public_figshare",
        source_url="https://example/poi.mdb",
        local_path=str(tmp_path / "poi.mdb"),
        file_verification={"exists": True},
        metadata_summary=metadata_summary,
        gate_decision=decision,
        inspection_summary=pd.DataFrame([{"layer_count": 1}]),
    )

    assert manifest["semantic_claim_allowed"] is False
    assert manifest["occupation_inference_allowed"] is False


def test_synthetic_self_check():
    module = _module()
    assert module.synthetic_self_check()["status"] == "ok"


def test_stage07f_notebook_contract():
    path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07f_bcl_poi_2008_acquisition.ipynb"
    )
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    required = [
        "FIGSHARE_API_URL",
        "GEOLIFE_MODAL_VOLUME_NAME",
        "modal.Volume.from_name",
        "apt_install",
        "mdbtools",
        "odbc-mdbtools",
        "gdal-bin",
        "acquisition_manifest",
        "license_allows_public_download",
    ]
    for snippet in required:
        assert snippet in code

    assert "fetch_ohsome" not in code


def test_noncommercial_and_no_derivatives_licenses_do_not_auto_pass():
    module = _module()

    assert not module.license_is_explicit_reuse_candidate("CC BY-NC 4.0")
    assert not module.license_is_explicit_reuse_candidate("CC BY-ND 4.0")
    assert module.license_is_explicit_reuse_candidate("CC BY 4.0")
    assert module.license_is_explicit_reuse_candidate("CC BY-SA 4.0")


def test_figshare_identity_mismatch_blocks_metadata_gate():
    module = _module()
    metadata = {
        "id": module.FIGSHARE_ARTICLE_ID + 1,
        "doi": module.FIGSHARE_DOI,
        "license": {"name": "CC BY 4.0"},
        "files": [],
    }

    decision = module.evaluate_acquisition_gates(
        metadata,
        http_status=200,
    )

    assert decision.metadata_access == "blocked_metadata_access_or_identity"
    assert decision.runner_status == "blocked"


def test_link_only_file_is_not_selected_as_corpus_download():
    module = _module()
    metadata = {
        "id": module.FIGSHARE_ARTICLE_ID,
        "doi": module.FIGSHARE_DOI,
        "license": {"name": "CC BY 4.0"},
        "files": [
            {
                "id": 9,
                "name": "poi2008.zip",
                "download_url": "https://example/poi2008.zip",
                "is_link_only": True,
            }
        ],
    }

    assert module.select_public_download_candidate(metadata) is None
    decision = module.evaluate_acquisition_gates(
        metadata,
        http_status=200,
    )
    assert decision.file_access == "blocked_link_only_not_corpus_file"


def test_mdb_structure_gate_requires_spatial_point_layer():
    module = _module()

    good = {
        "gdal_pgeo_available": True,
        "ogr": {
            "layer_count": 1,
            "geometry_types": ["Point"],
            "feature_counts": [6000000],
            "field_names": ["name"],
        },
    }
    bad = {
        "gdal_pgeo_available": True,
        "ogr": {
            "layer_count": 1,
            "geometry_types": ["None"],
            "feature_counts": [6000000],
            "field_names": ["name"],
        },
    }

    assert module.mdb_structure_is_plausible(good)
    assert not module.mdb_structure_is_plausible(bad)


def test_rar_public_candidate_and_format_gate():
    module = _module()
    metadata = {
        "id": module.FIGSHARE_ARTICLE_ID,
        "doi": module.FIGSHARE_DOI + ".v1",
        "license": {"name": "CC BY 4.0"},
        "files": [
            {
                "id": 53238599,
                "name": "Points of interest of China in 2008.rar",
                "size": 120023687,
                "download_url": "https://ndownloader.figshare.com/files/53238599",
                "computed_md5": "e77c3473874a6fb64fd0c52d3c66fc84",
                "is_link_only": False,
            }
        ],
    }

    candidate = module.select_public_download_candidate(metadata)
    decision = module.evaluate_acquisition_gates(
        metadata,
        http_status=200,
    )

    assert candidate is not None
    assert candidate["suffix"] == ".rar"
    assert decision.file_access == "pass_public_file"
    assert decision.license_status == "pass_explicit:CC BY 4.0"
    assert decision.format_status == "inspect_archive_for_mdb"
    assert decision.runner_status == "ready_for_mdb_inspection"


def test_stage07f_notebook_contract_includes_rar_worker_support():
    import json

    path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07f_bcl_poi_2008_acquisition.ipynb"
    )
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    assert "'.rar'" in code
    assert "'unar'" in code
    assert "RAR extraction failed" in code


def test_gdb_structure_can_pass_without_pgeo_driver():
    module = _module()
    report = {
        "container_kind": "gdb",
        "gdal_pgeo_available": False,
        "ogr": {
            "layer_count": 1,
            "geometry_types": ["Point"],
            "feature_counts": [6000000],
            "field_names": ["name"],
        },
    }

    assert module.mdb_structure_is_plausible(report)


def test_inspected_gdb_can_reach_ready_for_normalization():
    module = _module()
    metadata = {
        "id": module.FIGSHARE_ARTICLE_ID,
        "doi": module.FIGSHARE_DOI + ".v1",
        "license": {"name": "CC BY 4.0"},
        "files": [
            {
                "id": 53238599,
                "name": "Points of interest of China in 2008.rar",
                "download_url": "https://ndownloader.figshare.com/files/53238599",
                "is_link_only": False,
            }
        ],
    }

    decision = module.evaluate_acquisition_gates(
        metadata,
        http_status=200,
        inspected_crs="EPSG:4326",
        inspected_structure_ok=True,
        inspected_container_kind="gdb",
    )

    assert decision.format_status == "pass_inspected_gdb"
    assert decision.structure_status == "pass_spatial_point_structure"
    assert decision.crs_status == "pass_inspected_crs"
    assert decision.runner_status == "ready_for_normalization"


def test_extracted_inventory_marks_gdb_components():
    module = _module()
    inventory = module.summarize_extracted_inventory(
        [
            "/tmp/a/data.gdb/a00000001.gdbtable",
            "/tmp/a/poi.shp",
            "/tmp/a/readme.txt",
        ]
    )

    assert inventory["is_gdb_component"].tolist() == [True, False, False]
    assert inventory["is_supported_candidate"].tolist() == [True, True, False]


def test_stage07f_notebook_contract_inventories_alternate_containers():
    import json

    path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07f_bcl_poi_2008_acquisition.ipynb"
    )
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    assert "extension_counts" in code
    assert "container_kind" in code
    assert "endswith('.gdb')" in code
    assert "no supported spatial container found after acquisition" in code
