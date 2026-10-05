from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "08a_home_coverage_expansion.py"
)


def _module():
    spec = spec_from_file_location("stage08a", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_select_expansion_candidates_filters_to_high_medium_unique_nonproduction():
    stage = _module()
    frame = pd.DataFrame(
        [
            {
                "user_id": "a",
                "location_id": 1,
                "home_tier": "high",
                "production_status": "fixed_candidate_not_emitted",
                "unique_vote_winner": True,
                "method_votes": 3,
                "reliability_axes": 3,
            },
            {
                "user_id": "b",
                "location_id": 2,
                "home_tier": "medium",
                "production_status": "baseline_emitted",
                "unique_vote_winner": True,
                "method_votes": 2,
                "reliability_axes": 2,
            },
            {
                "user_id": "c",
                "location_id": 3,
                "home_tier": "uncertain",
                "production_status": "outside_fixed_candidate",
                "unique_vote_winner": True,
                "method_votes": 2,
                "reliability_axes": 2,
            },
        ]
    )

    out = stage.select_expansion_candidates(frame)

    assert len(out) == 1
    assert out.iloc[0]["user_id"] == "a"


def test_attach_location_context_replaces_cached_geometry_without_suffixes():
    stage = _module()
    candidates = pd.DataFrame(
        [
            {
                "user_id": "u",
                "location_id": 1,
                "home_tier": "high",
                "production_status": "fixed_candidate_not_emitted",
                "unique_vote_winner": True,
                "method_votes": 3,
                "reliability_axes": 3,
                "latitude": 0.0,
                "longitude": 0.0,
            }
        ]
    )
    locations = pd.DataFrame(
        {
            "user_id": ["u"],
            "location_id": [1],
            "latitude": [39.9],
            "longitude": [116.4],
            "stay_count": [5],
        }
    )
    production = pd.DataFrame(columns=["user_id", "label", "location_id"])

    out = stage.attach_location_context(candidates, locations, production)

    assert "latitude" in out.columns
    assert "longitude" in out.columns
    assert "latitude_x" not in out.columns
    assert "latitude_y" not in out.columns
    assert float(out.iloc[0]["latitude"]) == 39.9


def test_probable_requires_two_external_exact_families():
    stage = _module()
    frame = pd.DataFrame(
        [
            {
                "user_id": "u",
                "location_id": 1,
                "home_tier": "high",
                "unique_vote_winner": True,
                "method_votes": 3,
                "reliability_axes": 3,
                "collides_with_production_office": False,
                "trackintel_osna_exact": True,
                "trackintel_freq_exact": False,
                "scikit_home_exact": True,
                "scitepress_home_exact": False,
                "geohash_within_200m": False,
                "trackintel_e2e_dbscan100_within_200m": False,
                "trackintel_e2e_dbscan200_within_200m": False,
                "external_exact_family_count": 2,
                "auxiliary_support_count": 0,
            }
        ]
    )

    out = stage.assign_expansion_tiers(frame)
    assert out.iloc[0]["home_expansion_tier"] == "HOME_PROBABLE"


def test_office_collision_forces_abstain():
    stage = _module()
    frame = pd.DataFrame(
        [
            {
                "user_id": "u",
                "location_id": 1,
                "home_tier": "high",
                "unique_vote_winner": True,
                "method_votes": 3,
                "reliability_axes": 3,
                "collides_with_production_office": True,
                "trackintel_osna_exact": True,
                "trackintel_freq_exact": True,
                "scikit_home_exact": True,
                "scitepress_home_exact": True,
                "geohash_within_200m": True,
                "trackintel_e2e_dbscan100_within_200m": True,
                "trackintel_e2e_dbscan200_within_200m": True,
                "external_exact_family_count": 3,
                "auxiliary_support_count": 4,
            }
        ]
    )

    out = stage.assign_expansion_tiers(frame)
    assert out.iloc[0]["home_expansion_tier"] == "ABSTAIN"
    assert out.iloc[0]["tier_reason"] == "production_office_collision"


def test_synthetic_self_check():
    stage = _module()
    result = stage.synthetic_self_check()
    assert result["status"] == "ok"
    assert result["probable"] == 1
    assert result["plausible"] == 1


def test_notebook_contract():
    import json

    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "08a_home_coverage_expansion.ipynb"
    )
    notebook = json.loads(notebook_path.read_text())
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
    )

    required = [
        "/mnt/geolife-data",
        "05b_home_consensus_adaptive_work",
        "07m_trackintel_semantic_parity",
        "07n_trackintel_end_to_end",
        "07o_literature_comparator_suite",
        "HOME_HIGH_CONFIDENCE_CORE",
        "HOME_PROBABLE",
        "HOME_PLAUSIBLE",
        "ABSTAIN",
        "historical_stage05b_expected_candidates",
        "candidate_count_matches_historical",
        "production_HOME_unchanged",
        "08a_home_coverage_expansion",
    ]
    for token in required:
        assert token in source
