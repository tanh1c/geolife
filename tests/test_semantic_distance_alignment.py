from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07e_semantic_distance_alignment.py"
)


def _module():
    spec = spec_from_file_location("stage07e", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_geometry_distance_m_uses_wkb_geometry():
    module = _module()
    from shapely.geometry import Point

    lat = 39.9
    lon = 116.4
    lon_delta = 50.0 / (111_320.0 * np.cos(np.radians(lat)))
    geometry = Point(lon + lon_delta, lat)

    distance, method = module.geometry_distance_m(
        geometry.wkb,
        anchor_lat=lat,
        anchor_lon=lon,
    )

    assert method == "geometry"
    assert 49.0 <= distance <= 51.0


def test_geometry_distance_m_falls_back_to_bbox():
    module = _module()

    distance, method = module.geometry_distance_m(
        None,
        anchor_lat=39.9,
        anchor_lon=116.4,
        bbox={
            "xmin": 116.4,
            "xmax": 116.401,
            "ymin": 39.9,
            "ymax": 39.901,
        },
    )

    assert method == "bbox_fallback"
    assert distance == 0.0


def test_anchor_metrics_use_exact_threshold_and_censor_at_100m():
    module = _module()
    anchors = pd.DataFrame(
        [
            {"user_id": "u1", "location_id": 1},
            {"user_id": "u1", "location_id": 2},
            {"user_id": "u1", "location_id": 3},
        ]
    )
    features = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "category": "office_commercial",
                "distance_m": 20.0,
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "category": "industrial",
                "distance_m": 110.0,
            },
        ]
    )

    result = module.build_anchor_semantic_metrics(anchors, features)
    result = result.set_index("location_id")

    assert bool(result.loc[1, "work_compatible_within_25m"])
    assert result.loc[1, "work_distance_bucket"] == "0_25"

    assert not bool(result.loc[2, "work_compatible_within_100m"])
    assert result.loc[2, "work_distance_bucket"] == "none_within_100"
    assert result.loc[2, "work_compatible_censored_distance_100m"] == 100.0

    assert result.loc[3, "work_distance_bucket"] == "none_within_100"
    assert result.loc[3, "work_compatible_censored_distance_100m"] == 100.0


def test_align_mobility_roles_marks_exact_dominant_location():
    module = _module()
    anchors = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 3,
                "location_namespace": module.EXPECTED_LOCATION_NAMESPACE,
            },
            {
                "user_id": "u1",
                "location_id": 7,
                "location_namespace": module.EXPECTED_LOCATION_NAMESPACE,
            },
        ]
    )
    work = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "window_pattern": "stable_secondary_anchor",
                "dominant_location_id": 7,
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

    result = module.align_mobility_roles(anchors, work, profiles)

    assert result.loc[
        result["location_id"].eq(7), "stable_secondary_anchor"
    ].item()
    assert result.loc[
        result["location_id"].eq(3), "stable_secondary_peer_anchor"
    ].item()


def test_stable_secondary_comparison_is_within_user():
    module = _module()
    aligned = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "stable_secondary_user": True,
                "stable_secondary_anchor": True,
                "stable_secondary_peer_anchor": False,
                "work_compatible_censored_distance_100m": 10.0,
                "work_compatible_within_25m": True,
                "work_compatible_within_50m": True,
                "work_compatible_within_100m": True,
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "stable_secondary_user": True,
                "stable_secondary_anchor": False,
                "stable_secondary_peer_anchor": True,
                "work_compatible_censored_distance_100m": 100.0,
                "work_compatible_within_25m": False,
                "work_compatible_within_50m": False,
                "work_compatible_within_100m": False,
            },
            {
                "user_id": "u1",
                "location_id": 3,
                "stable_secondary_user": True,
                "stable_secondary_anchor": False,
                "stable_secondary_peer_anchor": True,
                "work_compatible_censored_distance_100m": 60.0,
                "work_compatible_within_25m": False,
                "work_compatible_within_50m": False,
                "work_compatible_within_100m": True,
            },
        ]
    )

    result = module.build_stable_secondary_user_comparisons(aligned)

    assert len(result) == 1
    row = result.iloc[0]
    assert row["peer_anchor_count"] == 2
    assert row["candidate_minus_peer_share_100m"] == 0.5
    assert bool(row["candidate_unique_closest_work_context"])


def test_profile_axis_summary_is_user_level_not_anchor_weighted():
    module = _module()
    aligned = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "work_compatible_within_100m": True,
                "route_repeated": True,
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "work_compatible_within_100m": False,
                "route_repeated": True,
            },
            {
                "user_id": "u2",
                "location_id": 1,
                "work_compatible_within_100m": False,
                "route_repeated": True,
            },
        ]
    )

    result = module.summarize_profile_axis_context(aligned)
    route = result.loc[result["axis"].eq("route_repeated")].iloc[0]

    assert route["users"] == 2
    assert route["users_any_work_context"] == 1
    assert route["share_users_any_work_context"] == 0.5


def _cache_anchor(user_id, location_id, lat, lon, date):
    return {
        "user_id": user_id,
        "location_id": location_id,
        "latitude": lat,
        "longitude": lon,
        "median_observation_date": date,
    }


def test_validate_full_cache_rejects_missing_raw_file(tmp_path):
    module = _module()
    anchors = pd.DataFrame(
        [
            _cache_anchor("u1", 1, 39.90, 116.40, "2009-06-15"),
            _cache_anchor("u1", 2, 39.91, 116.41, "2009-06-16"),
        ]
    )

    first_body = module.STAGE07D.build_ohsome_request(anchors.iloc[0])
    first_key = module.STAGE07D._ohsome_cache_key(first_body)
    (tmp_path / f"{first_key}.parquet").write_bytes(b"x")

    stale_log = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "cache_key": first_key,
                "status": "cached",
            }
        ]
    )

    try:
        module.validate_full_ohsome_cache(
            anchors,
            stale_log,
            tmp_path,
        )
    except ValueError as exc:
        assert "raw cache is incomplete" in str(exc)
    else:
        raise AssertionError("missing raw parquet should be rejected")


def test_validate_full_cache_accepts_complete_raw_cache_with_stale_log(tmp_path):
    module = _module()
    anchors = pd.DataFrame(
        [
            _cache_anchor("u1", 1, 39.90, 116.40, "2009-06-15"),
            _cache_anchor("u1", 2, 39.91, 116.41, "2009-06-16"),
        ]
    )

    keys = []
    for anchor in anchors.to_dict(orient="records"):
        body = module.STAGE07D.build_ohsome_request(anchor)
        key = module.STAGE07D._ohsome_cache_key(body)
        keys.append(key)
        (tmp_path / f"{key}.parquet").write_bytes(b"x")

    stale_log = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "cache_key": keys[0],
                "status": "cached",
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "cache_key": keys[1],
                "status": "deferred_request_budget",
            },
        ]
    )

    mapping = module.validate_full_ohsome_cache(
        anchors,
        stale_log,
        tmp_path,
    )

    assert len(mapping) == 2
    assert mapping["cache_path"].map(Path.exists).all()
    assert mapping["request_log_is_success"].tolist() == [True, False]



def test_extract_anchor_feature_distances_from_parquet():
    module = _module()
    from io import BytesIO

    import pyarrow as pa
    import pyarrow.parquet as pq
    from shapely.geometry import Point

    lat = 39.9
    lon = 116.4
    lon_delta = 30.0 / (111_320.0 * np.cos(np.radians(lat)))
    geometry = Point(lon + lon_delta, lat)

    table = pa.table(
        {
            "osm_type": ["node"],
            "osm_id": [123],
            "tags": pa.array(
                [[("building", "office")]],
                type=pa.map_(pa.string(), pa.string()),
            ),
            "bbox": pa.array(
                [
                    {
                        "xmin": lon + lon_delta,
                        "xmax": lon + lon_delta,
                        "ymin": lat,
                        "ymax": lat,
                    }
                ],
                type=pa.struct(
                    [
                        ("xmin", pa.float64()),
                        ("xmax", pa.float64()),
                        ("ymin", pa.float64()),
                        ("ymax", pa.float64()),
                    ]
                ),
            ),
            "geom_type": ["Point"],
            "geom": [geometry.wkb],
            "clipped": [False],
        }
    )
    buffer = BytesIO()
    pq.write_table(table, buffer)

    rows = module.extract_anchor_feature_distances(
        {
            "user_id": "u1",
            "location_id": 1,
            "latitude": lat,
            "longitude": lon,
        },
        buffer.getvalue(),
    )

    assert len(rows) == 1
    assert rows.iloc[0]["category"] == "office_commercial"
    assert bool(rows.iloc[0]["work_compatible_category"])
    assert 29.0 <= rows.iloc[0]["distance_m"] <= 31.0


def test_synthetic_self_check():
    module = _module()
    assert module.synthetic_self_check()["status"] == "ok"

def test_stable_secondary_category_summary_uses_same_user_peers():
    module = _module()
    aligned = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "stable_secondary_user": True,
                "stable_secondary_anchor": True,
                "stable_secondary_peer_anchor": False,
                "office_commercial_within_100m": True,
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "stable_secondary_user": True,
                "stable_secondary_anchor": False,
                "stable_secondary_peer_anchor": True,
                "office_commercial_within_100m": False,
            },
            {
                "user_id": "u1",
                "location_id": 3,
                "stable_secondary_user": True,
                "stable_secondary_anchor": False,
                "stable_secondary_peer_anchor": True,
                "office_commercial_within_100m": True,
            },
        ]
    )
    for category in module.CONTEXT_CATEGORIES:
        for threshold in module.DISTANCE_THRESHOLDS_M:
            column = module._threshold_name(category, threshold)
            if column not in aligned.columns:
                aligned[column] = False
    aligned["office_commercial_within_100m"] = [True, False, True]

    result = module.summarize_stable_secondary_categories(
        aligned,
        thresholds_m=(100.0,),
    )
    row = result.loc[
        result["category"].eq("office_commercial")
        & result["threshold_m"].eq(100.0)
    ].iloc[0]

    assert row["users"] == 1
    assert row["candidate_context_users"] == 1
    assert row["mean_peer_context_share"] == 0.5
    assert row["mean_candidate_minus_peer_share"] == 0.5


def test_profile_axis_category_summary_is_user_level():
    module = _module()
    aligned = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "office_commercial_within_100m": True,
                "route_repeated": True,
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "office_commercial_within_100m": False,
                "route_repeated": True,
            },
            {
                "user_id": "u2",
                "location_id": 1,
                "office_commercial_within_100m": False,
                "route_repeated": True,
            },
        ]
    )
    for category in module.CONTEXT_CATEGORIES:
        column = module._threshold_name(category, 100.0)
        if column not in aligned.columns:
            aligned[column] = False
    aligned["office_commercial_within_100m"] = [True, False, False]

    result = module.summarize_profile_axis_categories(
        aligned,
        threshold_m=100.0,
    )
    row = result.loc[
        result["axis"].eq("route_repeated")
        & result["category"].eq("office_commercial")
    ].iloc[0]

    assert row["users"] == 2
    assert row["users_any_category_context"] == 1
    assert row["share_users_any_category_context"] == 0.5

def test_stage07e_notebook_execution_contract():
    import json

    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07e_semantic_distance_alignment.ipynb"
    )
    notebook = json.loads(notebook_path.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]
    joined = "\n".join(code_cells)

    required_snippets = [
        "feature_dist=s07e.build_feature_distance_table",
        "aligned=s07e.align_mobility_roles",
        "comparisons=s07e.build_stable_secondary_user_comparisons",
        "stable_category_summary=s07e.summarize_stable_secondary_categories",
        "axis_category_summary=s07e.summarize_profile_axis_categories",
        "feature_dist.to_pickle",
        "axis_category_summary.to_csv",
    ]
    for snippet in required_snippets:
        assert snippet in joined

    for cell in notebook["cells"]:
        source = "".join(cell.get("source", []))
        if "to_pickle(" in source or "to_csv(" in source:
            assert cell.get("cell_type") == "code"

def test_align_mobility_roles_rejects_old_location_namespace():
    module = _module()
    anchors = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "location_namespace": "behavior_dwell_ranked_200m",
            }
        ]
    )
    work = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "window_pattern": "stable_secondary_anchor",
                "dominant_location_id": 1,
            }
        ]
    )
    profiles = pd.DataFrame([{"user_id": "u1"}])

    try:
        module.align_mobility_roles(anchors, work, profiles)
    except ValueError as exc:
        assert "incompatible location namespace" in str(exc)
    else:
        raise AssertionError("old behavior-location ids must be rejected")



def test_validate_full_cache_ignores_pre_ohsome_anchor(tmp_path):
    module = _module()
    anchors = pd.DataFrame(
        [
            _cache_anchor("u1", 1, 39.90, 116.40, "2007-09-01"),
            _cache_anchor("u1", 2, 39.91, 116.41, "2008-01-01"),
        ]
    )

    eligible = anchors.iloc[1]
    body = module.STAGE07D.build_ohsome_request(eligible)
    key = module.STAGE07D._ohsome_cache_key(body)
    (tmp_path / f"{key}.parquet").write_bytes(b"x")

    mapping = module.validate_full_ohsome_cache(
        anchors,
        pd.DataFrame(),
        tmp_path,
    )

    assert len(mapping) == 1
    assert mapping.iloc[0]["location_id"] == 2
    assert Path(mapping.iloc[0]["cache_path"]).exists()


def test_pre_ohsome_anchor_is_not_treated_as_no_context():
    module = _module()
    anchors = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "median_observation_date": "2007-09-01",
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "median_observation_date": "2008-01-01",
            },
        ]
    )
    features = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 2,
                "category": "office_commercial",
                "distance_m": 20.0,
            }
        ]
    )

    result = module.build_anchor_semantic_metrics(anchors, features).set_index("location_id")

    assert not bool(result.loc[1, "ohsome_eligible"])
    assert pd.isna(result.loc[1, "work_compatible_censored_distance_100m"])
    assert result.loc[1, "work_distance_bucket"] == "not_eligible"

    assert bool(result.loc[2, "ohsome_eligible"])
    assert result.loc[2, "work_distance_bucket"] == "0_25"

    summary = module.summarize_distance_buckets(result.reset_index())
    assert int(summary["anchors"].sum()) == 1


def test_stable_secondary_comparison_excludes_ineligible_peer():
    module = _module()
    aligned = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "median_observation_date": "2008-01-01",
                "stable_secondary_user": True,
                "stable_secondary_anchor": True,
                "stable_secondary_peer_anchor": False,
                "work_compatible_censored_distance_100m": 20.0,
                "work_compatible_within_25m": True,
                "work_compatible_within_50m": True,
                "work_compatible_within_100m": True,
            },
            {
                "user_id": "u1",
                "location_id": 2,
                "median_observation_date": "2007-09-01",
                "stable_secondary_user": True,
                "stable_secondary_anchor": False,
                "stable_secondary_peer_anchor": True,
                "work_compatible_censored_distance_100m": np.nan,
                "work_compatible_within_25m": False,
                "work_compatible_within_50m": False,
                "work_compatible_within_100m": False,
            },
            {
                "user_id": "u1",
                "location_id": 3,
                "median_observation_date": "2008-02-01",
                "stable_secondary_user": True,
                "stable_secondary_anchor": False,
                "stable_secondary_peer_anchor": True,
                "work_compatible_censored_distance_100m": 100.0,
                "work_compatible_within_25m": False,
                "work_compatible_within_50m": False,
                "work_compatible_within_100m": False,
            },
        ]
    )

    result = module.build_stable_secondary_user_comparisons(aligned)

    assert len(result) == 1
    assert int(result.iloc[0]["peer_anchor_count"]) == 1
    assert result.iloc[0]["candidate_minus_peer_share_100m"] == 1.0
