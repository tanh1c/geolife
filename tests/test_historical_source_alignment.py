from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07c_historical_source_alignment.py"
)


def _module():
    spec = spec_from_file_location("stage07c_hist", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_registry_keeps_unverified_semantic_sources_blocked():
    module = _module()
    registry = module.source_gate_summary().set_index("source_id")

    assert registry.loc["gaode_poi_2010_paper", "runner_ready_now"] == False
    assert registry.loc["junxi_gaode_2011", "runner_ready_now"] == False
    assert registry.loc["baidu_poi_2012_candidate", "runner_ready_now"] == False
    assert registry.loc["ohsome_historical_osm", "runner_ready_now"] == True


def test_anchor_median_date_is_observation_based():
    module = _module()
    stays = pd.DataFrame(
        [
            {"user_id": "u1", "location_id": 1, "arrival_time_utc": "2008-01-01T00:00:00Z"},
            {"user_id": "u1", "location_id": 1, "arrival_time_utc": "2008-05-01T00:00:00Z"},
            {"user_id": "u1", "location_id": 1, "arrival_time_utc": "2009-01-01T00:00:00Z"},
        ]
    )
    anchors = pd.DataFrame([{"user_id": "u1", "location_id": 1}])

    result = module.summarize_anchor_observation_dates(stays, anchors).iloc[0]

    assert result["median_observation_date"] == "2008-05-01"
    assert int(result["median_observation_year"]) == 2008


def test_bcl_2008_is_exact_only_for_2008_and_proxy_only_plus_minus_one_year():
    module = _module()
    anchors = pd.DataFrame(
        [
            {"user_id": "a", "location_id": 1, "median_observation_date": "2007-06-01"},
            {"user_id": "b", "location_id": 1, "median_observation_date": "2008-06-01"},
            {"user_id": "c", "location_id": 1, "median_observation_date": "2009-06-01"},
            {"user_id": "d", "location_id": 1, "median_observation_date": "2010-06-01"},
        ]
    )

    plan = module.build_temporal_source_plan(anchors)
    bcl = plan.loc[plan["source_id"].eq("bcl_poi_2008")]

    assert set(bcl["user_id"]) == {"a", "b", "c"}
    assert (
        bcl.set_index("user_id").loc["b", "alignment_type"]
        == "exact_year"
    )
    assert (
        bcl.set_index("user_id").loc["a", "temporal_offset_years"]
        == 1
    )
    assert (
        bcl.set_index("user_id").loc["c", "temporal_offset_years"]
        == -1
    )


def test_clcd_is_exact_year_for_each_geolife_year():
    module = _module()
    anchors = pd.DataFrame(
        [
            {
                "user_id": str(year),
                "location_id": 1,
                "median_observation_date": f"{year}-07-01",
            }
            for year in range(2007, 2013)
        ]
    )

    plan = module.build_temporal_source_plan(anchors)
    clcd = plan.loc[plan["source_id"].eq("clcd_annual")]

    assert len(clcd) == 6
    assert set(clcd["source_year"].astype(int)) == set(range(2007, 2013))
    assert set(clcd["temporal_offset_years"].astype(int)) == {0}
    assert set(clcd["alignment_type"]) == {"exact_year"}


def test_ohsome_is_not_assigned_before_earliest_supported_snapshot():
    module = _module()
    anchors = pd.DataFrame(
        [
            {"user_id": "early", "location_id": 1, "median_observation_date": "2007-09-01"},
            {"user_id": "late", "location_id": 1, "median_observation_date": "2007-11-01"},
        ]
    )

    plan = module.build_temporal_source_plan(anchors)
    osm = plan.loc[plan["source_id"].eq("ohsome_historical_osm")]

    assert set(osm["user_id"]) == {"late"}


def test_2011_sources_remain_separate_and_blocked():
    module = _module()
    anchors = pd.DataFrame(
        [{"user_id": "u", "location_id": 1, "median_observation_date": "2011-05-01"}]
    )

    plan = module.build_temporal_source_plan(anchors).set_index("source_id")

    assert "junxi_gaode_2011" in plan.index
    assert "bcl_poi_2011_research_corpus" in plan.index
    assert "bcl_blocks_2011" in plan.index
    assert str(plan.loc["junxi_gaode_2011", "use_status"]).startswith("blocked_")
    assert str(plan.loc["bcl_poi_2011_research_corpus", "use_status"]).startswith("blocked_")

def test_support_qualified_anchor_builder_excludes_home_and_low_support_users():
    module = _module()
    locations = pd.DataFrame(
        [
            {"user_id": "u1", "location_id": 0, "stay_count": 5},
            {"user_id": "u1", "location_id": 1, "stay_count": 3},
            {"user_id": "u1", "location_id": 2, "stay_count": 1},
            {"user_id": "u2", "location_id": 0, "stay_count": 5},
            {"user_id": "u2", "location_id": 1, "stay_count": 3},
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
            {"user_id": "u1", "home_context_supported": True},
            {"user_id": "u2", "home_context_supported": False},
        ]
    )

    anchors = module.build_support_qualified_anchors(
        locations,
        home,
        profiles,
        min_stay_count=2,
    )

    assert len(anchors) == 1
    assert anchors.iloc[0]["user_id"] == "u1"
    assert int(anchors.iloc[0]["location_id"]) == 1

