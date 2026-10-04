from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07g_bcl_poi_2008_alignment.py"
)


def _module():
    spec = spec_from_file_location("stage07g", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _manifest(module):
    return {
        "source_id": module.EXPECTED_SOURCE_ID,
        "figshare_article_id": module.EXPECTED_FIGSHARE_ARTICLE_ID,
        "figshare_doi": module.EXPECTED_FIGSHARE_DOI_PREFIX + ".v1",
        "gates": {"runner_status": "ready_for_normalization"},
        "inspection_summary": {
            "container_kind": "gdb",
            "container_path": "/mnt/geolife-data/external/bcl_poi_2008/extracted/POI2008All.gdb",
            "epsg_codes": "4326",
        },
        "semantic_claim_allowed": False,
        "occupation_inference_allowed": False,
    }


def test_manifest_gate_requires_completed_07f_contract():
    module = _module()
    gate = module.validate_07f_manifest(_manifest(module))
    assert gate.ready
    assert gate.runner_status == "ready_for_normalization"

    blocked = _manifest(module)
    blocked["gates"]["runner_status"] = "blocked"
    blocked_gate = module.validate_07f_manifest(blocked)
    assert not blocked_gate.ready
    assert "runner_status" in blocked_gate.notes


def test_bcl_eligibility_uses_cp2_v2_namespace_and_2007_2009_window():
    module = _module()
    anchors = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "latitude": 39.9,
                "longitude": 116.4,
                "median_observation_date": "2007-06-01",
                "median_observation_year": 2007,
                "location_namespace": module.EXPECTED_LOCATION_NAMESPACE,
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "latitude": 39.9,
                "longitude": 116.4,
                "median_observation_date": "2008-06-01",
                "median_observation_year": 2008,
                "location_namespace": module.EXPECTED_LOCATION_NAMESPACE,
            },
            {
                "user_id": "u1",
                "location_id": 3,
                "latitude": 39.9,
                "longitude": 116.4,
                "median_observation_date": "2009-06-01",
                "median_observation_year": 2009,
                "location_namespace": module.EXPECTED_LOCATION_NAMESPACE,
            },
            {
                "user_id": "u1",
                "location_id": 4,
                "latitude": 39.9,
                "longitude": 116.4,
                "median_observation_date": "2010-06-01",
                "median_observation_year": 2010,
                "location_namespace": module.EXPECTED_LOCATION_NAMESPACE,
            },
        ]
    )
    eligible = module.bcl_eligible_anchors(anchors)
    assert eligible["location_id"].tolist() == [1, 2, 3]
    assert eligible["bcl_alignment_type"].tolist() == [
        "nearest_year_proxy",
        "exact_year",
        "nearest_year_proxy",
    ]
    assert eligible["bcl_temporal_offset_years"].tolist() == [1, 0, -1]


def test_spatial_tiles_pad_beyond_final_evidence_radius():
    module = _module()
    anchors = pd.DataFrame(
        [
            {"latitude": 39.9000, "longitude": 116.4000},
            {"latitude": 39.9005, "longitude": 116.4005},
        ]
    )
    tiles = module.build_spatial_tiles(
        anchors,
        tile_size_deg=1.0,
        padding_m=150.0,
    )
    assert len(tiles) == 1
    row = tiles.iloc[0]
    assert row["anchor_count"] == 2
    assert row["xmin"] < anchors["longitude"].min()
    assert row["xmax"] > anchors["longitude"].max()
    assert row["ymin"] < anchors["latitude"].min()
    assert row["ymax"] > anchors["latitude"].max()


def test_lexical_rules_keep_unknown_and_ambiguous_explicit():
    module = _module()
    pois = pd.DataFrame(
        [
            {"poi_name": "北京大学", "latitude": 39.9, "longitude": 116.4},
            {"poi_name": "示例有限公司", "latitude": 39.9, "longitude": 116.4},
            {"poi_name": "大学医院", "latitude": 39.9, "longitude": 116.4},
            {"poi_name": "无类别名称", "latitude": 39.9, "longitude": 116.4},
        ]
    )
    result = module.classify_poi_names(pois)
    assert result.loc[0, "lexical_categories"] == ("education",)
    assert "business_name" in result.loc[1, "lexical_categories"]
    assert result.loc[2, "lexical_status"] == "ambiguous_multi_signal"
    assert result.loc[3, "lexical_status"] == "unknown"


def test_exact_radial_matching_and_anchor_metrics():
    module = _module()
    anchors = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "latitude": 39.9,
                "longitude": 116.4,
            }
        ]
    )
    # Roughly 30 m east at Beijing latitude.
    lon_delta = 30.0 / (111_320.0 * 0.768)
    pois = pd.DataFrame(
        [
            {
                "poi_name": "示例有限公司",
                "latitude": 39.9,
                "longitude": 116.4 + lon_delta,
            },
            {
                "poi_name": "远处商场",
                "latitude": 39.9,
                "longitude": 116.4 + 0.01,
            },
        ]
    )
    classified = module.classify_poi_names(pois)
    matches = module.assign_pois_to_anchors(
        anchors,
        classified,
        max_distance_m=100.0,
    )
    assert len(matches) == 1
    assert 25.0 < matches.iloc[0]["distance_m"] < 40.0

    metrics = module.build_anchor_lexical_metrics(anchors, matches)
    assert not bool(metrics.iloc[0]["work_compatible_lexical_within_25m"])
    assert bool(metrics.iloc[0]["work_compatible_lexical_within_50m"])
    assert bool(metrics.iloc[0]["business_name_within_50m"])


def test_stable_secondary_lexical_comparison_is_same_user():
    module = _module()
    aligned = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "stable_secondary_user": True,
                "stable_secondary_anchor": True,
                "stable_secondary_peer_anchor": False,
                "work_compatible_lexical_within_25m": True,
                "work_compatible_lexical_within_50m": True,
                "work_compatible_lexical_within_100m": True,
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "stable_secondary_user": True,
                "stable_secondary_anchor": False,
                "stable_secondary_peer_anchor": True,
                "work_compatible_lexical_within_25m": False,
                "work_compatible_lexical_within_50m": False,
                "work_compatible_lexical_within_100m": False,
            },
            {
                "user_id": "u1",
                "location_id": 3,
                "stable_secondary_user": True,
                "stable_secondary_anchor": False,
                "stable_secondary_peer_anchor": True,
                "work_compatible_lexical_within_25m": False,
                "work_compatible_lexical_within_50m": True,
                "work_compatible_lexical_within_100m": True,
            },
        ]
    )
    result = module.build_stable_secondary_lexical_comparisons(aligned)
    assert len(result) == 1
    row = result.iloc[0]
    assert row["peer_anchor_count"] == 2
    assert row["candidate_minus_peer_share_25m"] == 1.0
    assert row["candidate_minus_peer_share_100m"] == 0.5


def test_stage07g_notebook_contract():
    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07g_bcl_poi_2008_alignment.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    required = [
        "GEOLIFE_REPO_BRANCH",
        "validate_07f_manifest",
        "bcl_eligible_anchors",
        "extract_bcl_neighborhoods",
        "ogr2ogr",
        "POI2008CN",
        "classify_poi_names",
        "assign_pois_to_anchors",
        "build_stable_secondary_lexical_comparisons",
        "bcl_neighborhood_pois_classified_private.pkl",
        "stable_secondary_bcl_summary.csv",
    ]
    for snippet in required:
        assert snippet in code

    assert "production_complete_link_200m_beijing_policy_v1" not in code
