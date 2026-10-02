from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07c_external_poi_landuse_enrichment.py"
)


def _module():
    spec = spec_from_file_location("stage07c", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_candidate_anchors_exclude_supported_home_and_keep_recurring_nonhome():
    module = _module()
    locations = pd.DataFrame(
        [
            {"user_id": "u1", "location_id": 0, "latitude": 39.9, "longitude": 116.4, "stay_count": 6, "active_local_dates": 5, "total_dwell_h": 50},
            {"user_id": "u1", "location_id": 1, "latitude": 39.91, "longitude": 116.41, "stay_count": 4, "active_local_dates": 4, "total_dwell_h": 30},
            {"user_id": "u1", "location_id": 2, "latitude": 39.92, "longitude": 116.42, "stay_count": 1, "active_local_dates": 1, "total_dwell_h": 2},
            {"user_id": "u2", "location_id": 0, "latitude": 39.8, "longitude": 116.3, "stay_count": 5, "active_local_dates": 4, "total_dwell_h": 40},
            {"user_id": "u2", "location_id": 1, "latitude": 39.81, "longitude": 116.31, "stay_count": 3, "active_local_dates": 3, "total_dwell_h": 20},
        ]
    )
    home = pd.DataFrame(
        [
            {"user_id": "u1", "location_id": 0, "home_tier": "high", "unique_vote_winner": True},
            {"user_id": "u2", "location_id": 0, "home_tier": "low", "unique_vote_winner": True},
        ]
    )
    profiles = pd.DataFrame(
        [
            {"user_id": "u1", "home_context_supported": True, "candidate_single_anchor_geometry": True},
            {"user_id": "u2", "home_context_supported": False, "candidate_single_anchor_geometry": True},
        ]
    )
    work = pd.DataFrame(
        [{"user_id": "u1", "window_pattern": "stable_secondary_anchor", "dominant_location_id": 1}]
    )
    edges = pd.DataFrame(
        [{
            "user_id": "u1",
            "origin_location_id": 0,
            "destination_location_id": 1,
            "repeated_edge": True,
        }]
    )

    anchors = module.build_candidate_anchors(
        locations,
        home,
        profiles,
        work_patterns=work,
        edge_summary=edges,
    )

    assert len(anchors) == 1
    row = anchors.iloc[0]
    assert row["user_id"] == "u1"
    assert int(row["location_id"]) == 1
    assert bool(row["is_stable_secondary"])
    assert bool(row["appears_in_repeated_edge"])


def test_osm_tag_classification_is_multi_label():
    module = _module()
    categories = module.classify_osm_tags(
        {
            "building": "office",
            "shop": "convenience",
            "public_transport": "platform",
        }
    )
    assert "office_commercial" in categories
    assert "retail_service" in categories
    assert "transport" in categories


def test_overpass_payload_parses_way_center_and_node_coordinates():
    module = _module()
    payload = {
        "elements": [
            {
                "type": "node",
                "id": 1,
                "lat": 39.9,
                "lon": 116.4,
                "tags": {"amenity": "school"},
            },
            {
                "type": "way",
                "id": 2,
                "center": {"lat": 39.91, "lon": 116.41},
                "tags": {"building": "office"},
            },
        ]
    }

    parsed = module.parse_overpass_payload(payload, query_hash="abc")

    assert len(parsed) == 2
    assert set(parsed["osm_type"]) == {"node", "way"}
    assert set(parsed["osm_id"]) == {1, 2}


def test_radius_aggregation_keeps_primary_and_sensitivity_separate():
    module = _module()
    anchors = pd.DataFrame(
        [{
            "anchor_key": "u1::L1",
            "user_id": "u1",
            "location_id": 1,
            "latitude": 39.9,
            "longitude": 116.4,
            "stay_count": 3,
            "active_days": 3,
            "total_dwell_h": 20.0,
            "home_location_id": 0,
            "is_stable_secondary": True,
            "is_adaptive_dominant": True,
            "appears_in_repeated_edge": True,
            "candidate_single_anchor_geometry": True,
            "candidate_anchor_set_geometry": True,
            "candidate_route_region_geometry": True,
            "schedule_agnostic_needed": False,
            "mobile_complexity_evidence": False,
            "route_repeated": True,
        }]
    )
    links = pd.DataFrame(
        [
            {
                "anchor_key": "u1::L1",
                "user_id": "u1",
                "location_id": 1,
                "osm_type": "node",
                "osm_id": 1,
                "distance_m": 50.0,
                "tags": {"building": "office"},
            },
            {
                "anchor_key": "u1::L1",
                "user_id": "u1",
                "location_id": 1,
                "osm_type": "node",
                "osm_id": 2,
                "distance_m": 180.0,
                "tags": {"landuse": "residential"},
            },
        ]
    )

    context = module.aggregate_anchor_context(anchors, links, radii_m=(100, 250)).iloc[0]

    assert bool(context["office_commercial_present_100m"])
    assert not bool(context["residential_present_100m"])
    assert bool(context["residential_present_250m"])
    assert bool(context["mixed_residential_work_context_250m"])


def test_missing_semantic_tags_is_unknown_not_negative_ground_truth():
    module = _module()
    anchors = pd.DataFrame(
        [{
            "anchor_key": "u1::L1",
            "user_id": "u1",
            "location_id": 1,
            "latitude": 39.9,
            "longitude": 116.4,
            "stay_count": 3,
            "active_days": 3,
            "total_dwell_h": 20.0,
            "home_location_id": 0,
            "is_stable_secondary": False,
            "is_adaptive_dominant": False,
            "appears_in_repeated_edge": False,
            "candidate_single_anchor_geometry": False,
            "candidate_anchor_set_geometry": True,
            "candidate_route_region_geometry": False,
            "schedule_agnostic_needed": False,
            "mobile_complexity_evidence": False,
            "route_repeated": False,
        }]
    )

    context = module.aggregate_anchor_context(
        anchors,
        pd.DataFrame(columns=["anchor_key", "user_id", "location_id", "osm_type", "osm_id", "distance_m", "tags"]),
        radii_m=(100, 250),
    ).iloc[0]

    assert context["context_signature_100m"] == "unknown"
    assert int(context["semantic_category_count_100m"]) == 0
    assert not bool(context["work_compatible_context_100m"])


def test_stable_secondary_peer_comparison_is_within_user():
    module = _module()
    context = pd.DataFrame(
        [
            {
                "anchor_key": "u1::L1",
                "user_id": "u1",
                "location_id": 1,
                "is_stable_secondary": True,
                "office_commercial_present_100m": True,
                "residential_present_100m": False,
                "education_present_100m": False,
                "healthcare_present_100m": False,
                "industrial_present_100m": False,
                "retail_service_present_100m": False,
                "transport_present_100m": False,
                "civic_institutional_present_100m": False,
                "recreation_tourism_present_100m": False,
                "work_compatible_context_100m": True,
                "residential_context_100m": False,
                "mixed_residential_work_context_100m": False,
                "residential_only_context_100m": False,
                "semantic_category_count_100m": 1,
            },
            {
                "anchor_key": "u1::L2",
                "user_id": "u1",
                "location_id": 2,
                "is_stable_secondary": False,
                "office_commercial_present_100m": False,
                "residential_present_100m": True,
                "education_present_100m": False,
                "healthcare_present_100m": False,
                "industrial_present_100m": False,
                "retail_service_present_100m": False,
                "transport_present_100m": False,
                "civic_institutional_present_100m": False,
                "recreation_tourism_present_100m": False,
                "work_compatible_context_100m": False,
                "residential_context_100m": True,
                "mixed_residential_work_context_100m": False,
                "residential_only_context_100m": True,
                "semantic_category_count_100m": 1,
            },
        ]
    )

    comparison = module.compare_stable_secondary_to_peers(context, radius_m=100)
    row = comparison.iloc[0]

    assert row["office_commercial_present_100m__difference"] == 1.0
    assert row["residential_context_100m__difference"] == -1.0
