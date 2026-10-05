from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07i_threshold_sensitivity.py"
)


def _module():
    spec = spec_from_file_location("stage07i", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_predeclared_office_grid_is_3x3x3_with_frozen_baseline():
    module = _module()
    configs = module.office_gate_grid()
    assert len(configs) == 27
    triples = {
        (
            cfg.office_min_dates,
            cfg.office_min_share,
            cfg.office_min_margin,
        )
        for cfg in configs
    }
    assert (3, 0.30, 0.10) in triples
    assert (2, 0.20, 0.05) in triples
    assert (5, 0.40, 0.20) in triples


def test_mobility_oat_changes_one_axis_at_a_time():
    module = _module()
    configs = module.mobility_oat_configs()
    assert len(configs) == 11

    baseline = configs[0]
    assert baseline.name == "baseline"
    baseline_values = {
        key: getattr(baseline, key)
        for key in module.BASELINE_MOBILITY
    }

    for cfg in configs[1:]:
        changed = [
            key
            for key, value in baseline_values.items()
            if getattr(cfg, key) != value
        ]
        assert changed == [cfg.changed_axis]


def test_joint_profiles_are_predeclared_not_semantic_selected():
    module = _module()
    configs = module.mobility_profile_configs()
    assert [cfg.name for cfg in configs] == [
        "relaxed",
        "mildly_relaxed",
        "baseline_profile",
        "strict",
    ]
    relaxed = configs[0]
    strict = configs[-1]
    assert relaxed.min_observed_days < strict.min_observed_days
    assert relaxed.min_candidate_days < strict.min_candidate_days
    assert relaxed.min_candidate_stays < strict.min_candidate_stays
    assert relaxed.stability_threshold < strict.stability_threshold


def test_bcl_radius_sensitivity_stops_at_existing_extraction_padding():
    module = _module()
    assert module.BCL_RADII_M == (25.0, 50.0, 75.0, 100.0, 125.0, 150.0)
    assert max(module.BCL_RADII_M) == module.MAX_REUSED_BCL_RADIUS_M
    assert module.MAX_REUSED_BCL_RADIUS_M == 150.0


def test_bcl_primary_osm_support_does_not_count_osm_negative_as_contradiction():
    module = _module()
    panel = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "bcl_candidate_minus_peer_100m": 0.5,
                "bcl_candidate_context_100m": True,
                "osm_candidate_context_100m": False,
                "osm_candidate_minus_peer_100m": -0.5,
                "behavior_primary_support": False,
                "behavior_directional_majority": True,
            },
            {
                "user_id": "u2",
                "bcl_candidate_minus_peer_100m": 0.4,
                "bcl_candidate_context_100m": True,
                "osm_candidate_context_100m": True,
                "osm_candidate_minus_peer_100m": 0.2,
                "behavior_primary_support": True,
                "behavior_directional_majority": True,
            },
            {
                "user_id": "u3",
                "bcl_candidate_minus_peer_100m": -0.2,
                "bcl_candidate_context_100m": False,
                "osm_candidate_context_100m": True,
                "osm_candidate_minus_peer_100m": 0.2,
                "behavior_primary_support": False,
                "behavior_directional_majority": False,
            },
        ]
    )
    row = module.bcl_primary_osm_support_summary(panel).iloc[0]

    assert row["bcl_candidate_favoring_users"] == 2
    assert row["bcl_favoring_with_osm_candidate_context_support"] == 1
    assert row["bcl_favoring_with_osm_candidate_favoring_support"] == 1
    assert row["bcl_favoring_without_osm_mapped_candidate_context"] == 1
    assert row["behavior_strict_and_bcl_favoring_users"] == 1
    assert row["behavior_directional_and_bcl_favoring_users"] == 2


def test_office_grid_bcl_annotation_is_explicitly_evaluable_subset():
    module = _module()
    grid = pd.DataFrame(
        [
            {
                "office_min_dates": 3,
                "office_min_share": 0.30,
                "office_min_margin": 0.10,
                "emitted_users": 2,
            }
        ]
    )
    emitted = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 7,
                "office_min_dates": 3,
                "office_min_share": 0.30,
                "office_min_margin": 0.10,
            },
            {
                "user_id": "u2",
                "location_id": 8,
                "office_min_dates": 3,
                "office_min_share": 0.30,
                "office_min_margin": 0.10,
            },
        ]
    )
    metrics = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 7,
                "work_compatible_lexical_within_100m": True,
                "business_name_within_100m": False,
            }
        ]
    )
    result = module.annotate_office_grid_with_bcl(grid, emitted, metrics)
    row = result.iloc[0]
    assert row["bcl_evaluable_emitted_users"] == 1
    assert row["bcl_context_emitted_users"] == 1
    assert row["bcl_business_name_emitted_users"] == 0


def test_synthetic_self_check():
    module = _module()
    result = module.synthetic_self_check()
    assert result["status"] == "ok"
    assert result["office_grid"] == 27


def test_stage07i_notebook_contract():
    path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07i_threshold_sensitivity.ipynb"
    )
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    required = [
        "office_gate_sensitivity.csv",
        "mobility_gate_sensitivity.csv",
        "bcl_radius_and_mobility_sensitivity.csv",
        "bcl_primary_osm_support_snapshot.csv",
        "baseline 05b reproduction: PASS",
        "frozen production OFFICE reproduction: PASS",
        "BCL PRIMARY / OSM SUPPORT-ONLY SNAPSHOT",
    ]
    for snippet in required:
        assert snippet in code

    assert "200.0])" not in code
