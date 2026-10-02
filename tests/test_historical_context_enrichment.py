from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07d_historical_context_enrichment.py"
)


def _module():
    spec = spec_from_file_location("stage07d", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_clcd_labels_keep_physical_land_cover_semantics():
    module = _module()
    assert module.clcd_label(1) == "cropland"
    assert module.clcd_label(5) == "water"
    assert module.clcd_label(8) == "impervious"
    assert module.clcd_label(9) == "wetland"
    assert module.clcd_label(999) == "unknown"


def test_clcd_sampling_plan_uses_only_observed_anchor_years():
    module = _module()
    anchors = pd.DataFrame({"median_observation_year": [2008, 2008, 2009, 2012]})
    plan = module.build_clcd_sampling_plan(anchors)
    assert plan["year"].tolist() == [2008, 2009, 2012]
    assert plan["anchors"].tolist() == [2, 1, 1]
    assert all("CLCD_v01_" in url for url in plan["url"])


def test_mode_code_ignores_zero_and_breaks_ties_deterministically():
    module = _module()
    values = np.array([[0, 8, 8], [1, 1, 0], [5, 0, 5]])
    assert module._mode_code(values, nodata=0) == 1.0


def test_ohsome_request_uses_anchor_observation_date_not_current_date():
    module = _module()
    anchor = {
        "latitude": 39.9,
        "longitude": 116.4,
        "median_observation_date": "2009-06-15",
    }
    body = module.build_ohsome_request(anchor, radius_m=100)
    assert body["time"] == "2009-06-15T00:00:00Z"
    assert len(body["aoi"]) == 4
    assert body["clip"] is True


def test_osm_tag_classification_is_nonexclusive():
    module = _module()
    categories = module.classify_osm_tags({
        "building": "office",
        "shop": "convenience",
        "public_transport": "platform",
    })
    assert "office_commercial" in categories
    assert "retail_service" in categories
    assert "transport" in categories


def test_join_keeps_semantic_claims_disabled():
    module = _module()
    anchors = pd.DataFrame([{
        "user_id": "u1",
        "location_id": 1,
        "median_observation_year": 2008,
    }])
    clcd = pd.DataFrame([{
        "user_id": "u1",
        "location_id": 1,
        "clcd_year": 2008,
        "clcd_point_class": "impervious",
    }])
    result = module.join_historical_context(anchors, clcd)
    assert result.iloc[0]["clcd_point_class"] == "impervious"
    assert not bool(result.iloc[0]["historical_semantic_claim_allowed"])
    assert not bool(result.iloc[0]["occupation_inference_allowed"])
    assert bool(result.iloc[0]["clcd_is_physical_context_only"])


def test_clcd_url_is_pinned_to_cog_record():
    module = _module()
    url = module.clcd_cog_url(2009)
    assert str(module.CLCD_RECORD_ID) in url
    assert "CLCD_v01_2009_albert.tif" in url

def test_secret_isolated_fetcher_path_accepts_bytes_and_caches(tmp_path):
    module = _module()
    import pyarrow as pa
    import pyarrow.parquet as pq
    from io import BytesIO

    table = pa.table({
        "tags": pa.array([{"building": "office"}], type=pa.map_(pa.string(), pa.string())),
    })
    buffer = BytesIO()
    pq.write_table(table, buffer)
    payload = buffer.getvalue()

    anchors = pd.DataFrame([{
        "user_id": "u1",
        "location_id": 1,
        "latitude": 39.9,
        "longitude": 116.4,
        "median_observation_date": "2009-06-15",
    }])

    calls = {"n": 0}

    def fetcher(body):
        calls["n"] += 1
        assert body["time"] == "2009-06-15T00:00:00Z"
        return payload

    context, log = module.fetch_ohsome_context_with_fetcher(
        anchors,
        fetcher=fetcher,
        cache_dir=tmp_path,
        radius_m=100,
    )
    assert calls["n"] == 1
    assert bool(context.iloc[0]["osm_office_commercial_present"])
    assert not bool(log.iloc[0]["cached"])

    context2, log2 = module.fetch_ohsome_context_with_fetcher(
        anchors,
        fetcher=fetcher,
        cache_dir=tmp_path,
        radius_m=100,
    )
    assert calls["n"] == 1
    assert bool(log2.iloc[0]["cached"])

def test_attach_anchor_coordinates_reconstructs_median_centroid():
    module = _module()
    anchors = pd.DataFrame([
        {"user_id": "u1", "location_id": 1, "median_observation_year": 2008},
    ])
    clustered = pd.DataFrame([
        {"user_id": "u1", "location_id": 1, "latitude": 39.9, "longitude": 116.4},
        {"user_id": "u1", "location_id": 1, "latitude": 39.92, "longitude": 116.42},
        {"user_id": "u1", "location_id": 1, "latitude": 39.91, "longitude": 116.41},
    ])

    result = module.attach_anchor_coordinates_from_clustered_stays(anchors, clustered)

    assert float(result.iloc[0]["latitude"]) == 39.91
    assert float(result.iloc[0]["longitude"]) == 116.41
    assert int(result.iloc[0]["coordinate_stay_count"]) == 3

def test_free_tier_rate_limit_stops_new_requests_and_returns_partial(tmp_path):
    module = _module()
    import pyarrow as pa
    import pyarrow.parquet as pq
    from io import BytesIO

    table = pa.table({
        "tags": pa.array([{"building": "office"}], type=pa.map_(pa.string(), pa.string())),
    })
    buffer = BytesIO()
    pq.write_table(table, buffer)
    payload = buffer.getvalue()

    anchors = pd.DataFrame([
        {
            "user_id": "u1",
            "location_id": 1,
            "latitude": 39.9,
            "longitude": 116.4,
            "median_observation_date": "2009-06-15",
        },
        {
            "user_id": "u1",
            "location_id": 2,
            "latitude": 39.91,
            "longitude": 116.41,
            "median_observation_date": "2009-06-16",
        },
        {
            "user_id": "u1",
            "location_id": 3,
            "latitude": 39.92,
            "longitude": 116.42,
            "median_observation_date": "2009-06-17",
        },
    ])

    calls = {"n": 0}

    def fetcher(body):
        calls["n"] += 1
        if calls["n"] == 1:
            return {
                "ok": True,
                "status_code": 200,
                "content": payload,
                "retry_after": None,
                "rate_limit_reset": None,
                "error": None,
            }
        return {
            "ok": False,
            "status_code": 429,
            "content": None,
            "retry_after": "60",
            "rate_limit_reset": None,
            "error": "quota exceeded",
        }

    context, log = module.fetch_ohsome_context_with_fetcher(
        anchors,
        fetcher=fetcher,
        cache_dir=tmp_path,
        max_new_requests_per_run=20,
    )

    assert calls["n"] == 2
    assert len(context) == 1
    assert log["status"].tolist() == [
        "fetched",
        "rate_limited",
        "deferred_rate_limited",
    ]

    summary = module.summarize_ohsome_run(anchors, context, log).iloc[0]
    assert int(summary["anchor_completed"]) == 1
    assert int(summary["rate_limited"]) == 1
    assert int(summary["deferred_rate_limited"]) == 1


def test_free_tier_request_budget_defers_remaining_anchors(tmp_path):
    module = _module()
    import pyarrow as pa
    import pyarrow.parquet as pq
    from io import BytesIO

    table = pa.table({
        "tags": pa.array([{"building": "office"}], type=pa.map_(pa.string(), pa.string())),
    })
    buffer = BytesIO()
    pq.write_table(table, buffer)
    payload = buffer.getvalue()

    anchors = pd.DataFrame([
        {
            "user_id": "u1",
            "location_id": i,
            "latitude": 39.9 + i * 0.001,
            "longitude": 116.4 + i * 0.001,
            "median_observation_date": f"2009-06-{10+i:02d}",
        }
        for i in range(1, 5)
    ])

    calls = {"n": 0}

    def fetcher(body):
        calls["n"] += 1
        return {
            "ok": True,
            "status_code": 200,
            "content": payload,
            "retry_after": None,
            "rate_limit_reset": None,
            "error": None,
        }

    context, log = module.fetch_ohsome_context_with_fetcher(
        anchors,
        fetcher=fetcher,
        cache_dir=tmp_path,
        max_new_requests_per_run=2,
    )

    assert calls["n"] == 2
    assert len(context) == 2
    assert log["status"].tolist().count("deferred_request_budget") == 2

def test_attach_anchor_coordinates_from_production_locations():
    module = _module()
    anchors = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 2,
                "median_observation_year": 2008,
            }
        ]
    )
    locations = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 2,
                "latitude": 39.91,
                "longitude": 116.41,
                "stay_count": 4,
            }
        ]
    )

    result = module.attach_anchor_coordinates_from_locations(
        anchors,
        locations,
    ).iloc[0]

    assert float(result["latitude"]) == 39.91
    assert float(result["longitude"]) == 116.41
    assert int(result["coordinate_stay_count"]) == 4

