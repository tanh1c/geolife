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
    assert "CLCD_v01_2009.tif" in url
