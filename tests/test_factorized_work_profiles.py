from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07b_factorized_work_profiles.py"
)


def _module():
    spec = spec_from_file_location("stage07b", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_overlap_is_preserved_instead_of_forced_into_one_class():
    module = _module()
    behavior = pd.DataFrame(
        [{
            "user_id": "u1",
            "anchor_count_class": "multiple_anchor",
            "stable_shifted_candidate": True,
            "mobile_work_like_candidate": True,
        }]
    )
    work = pd.DataFrame(
        [{
            "user_id": "u1",
            "window_pattern": "stable_secondary_anchor",
            "eligible_windows": 4,
            "candidate_windows": 4,
        }]
    )
    routine = pd.DataFrame(
        [{
            "user_id": "u1",
            "usable_motif_days": 10,
            "has_repeated_edge": True,
            "distinct_edges": 12,
            "edge_entropy": 3.0,
        }]
    )

    row = module.run_audit(behavior, work, routine).profiles.iloc[0]

    assert bool(row["site_stable_secondary"])
    assert bool(row["site_multiple_recurring"])
    assert bool(row["route_repeated"])
    assert bool(row["schedule_shifted_evidence"])
    assert bool(row["mobile_complexity_evidence"])
    assert int(row["representation_option_count"]) == 3
    assert row["representation_signature"] == (
        "single_anchor+anchor_set+route_region+schedule_agnostic"
    )


def test_route_region_requires_repeated_route_plus_mobile_or_multi_site_context():
    module = _module()
    behavior = pd.DataFrame(
        [
            {
                "user_id": "plain_route",
                "anchor_count_class": "dominant_anchor",
                "stable_shifted_candidate": False,
                "mobile_work_like_candidate": False,
            },
            {
                "user_id": "multi_route",
                "anchor_count_class": "multiple_anchor",
                "stable_shifted_candidate": False,
                "mobile_work_like_candidate": False,
            },
        ]
    )
    work = pd.DataFrame(
        [
            {
                "user_id": "plain_route",
                "window_pattern": "insufficient",
                "eligible_windows": 0,
                "candidate_windows": 0,
            },
            {
                "user_id": "multi_route",
                "window_pattern": "multi_anchor",
                "eligible_windows": 4,
                "candidate_windows": 4,
            },
        ]
    )
    routine = pd.DataFrame(
        [
            {
                "user_id": "plain_route",
                "usable_motif_days": 10,
                "has_repeated_edge": True,
                "distinct_edges": 2,
                "edge_entropy": 0.5,
            },
            {
                "user_id": "multi_route",
                "usable_motif_days": 10,
                "has_repeated_edge": True,
                "distinct_edges": 8,
                "edge_entropy": 2.0,
            },
        ]
    )

    result = module.run_audit(behavior, work, routine).profiles.set_index("user_id")

    assert not bool(result.loc["plain_route", "candidate_route_region_geometry"])
    assert bool(result.loc["multi_route", "candidate_route_region_geometry"])


def test_pairwise_overlap_reports_conditional_overlap():
    module = _module()
    profiles = pd.DataFrame(
        {
            "user_id": ["a", "b", "c"],
            **{
                axis: [False, False, False]
                for axis in module.CORE_BOOLEAN_AXES
            },
        }
    )
    profiles.loc[0, "site_stable_secondary"] = True
    profiles.loc[1, "site_stable_secondary"] = True
    profiles.loc[0, "site_multiple_recurring"] = True

    overlap = module.pairwise_axis_overlap(profiles)
    row = overlap.loc[
        overlap["left_axis"].eq("site_stable_secondary")
        & overlap["right_axis"].eq("site_multiple_recurring")
    ].iloc[0]

    assert int(row["intersection_users"]) == 1
    assert float(row["right_given_left"]) == 0.5
    assert float(row["left_given_right"]) == 1.0


def test_support_summary_keeps_upstream_coverage_visible():
    module = _module()
    behavior = pd.DataFrame(
        [{
            "user_id": "u1",
            "anchor_count_class": "two_anchor",
            "stable_shifted_candidate": False,
            "mobile_work_like_candidate": False,
        }]
    )
    work = pd.DataFrame(
        [{
            "user_id": "u1",
            "window_pattern": "stable_secondary_anchor",
            "eligible_windows": 3,
            "candidate_windows": 2,
        }]
    )
    routine = pd.DataFrame(
        [{
            "user_id": "u1",
            "usable_motif_days": 8,
            "has_repeated_edge": False,
            "distinct_edges": 1,
            "edge_entropy": 0.0,
        }]
    )

    audit = module.run_audit(behavior, work, routine)
    summary = audit.support_summary.set_index("support_axis")

    assert int(summary.loc["behavior_evidence_available", "users"]) == 1
    assert int(summary.loc["work_pattern_observed", "users"]) == 1
    assert int(summary.loc["routine_evidence_available", "users"]) == 1


def test_semantic_and_occupation_claims_remain_disabled():
    module = _module()
    behavior = pd.DataFrame(
        [{
            "user_id": "u1",
            "anchor_count_class": "multiple_anchor",
            "stable_shifted_candidate": True,
            "mobile_work_like_candidate": True,
        }]
    )
    work = pd.DataFrame(
        [{
            "user_id": "u1",
            "window_pattern": "stable_secondary_anchor",
            "eligible_windows": 5,
            "candidate_windows": 5,
        }]
    )
    routine = pd.DataFrame(
        [{
            "user_id": "u1",
            "usable_motif_days": 10,
            "has_repeated_edge": True,
            "distinct_edges": 10,
            "edge_entropy": 3.0,
        }]
    )

    row = module.run_audit(behavior, work, routine).profiles.iloc[0]

    assert not bool(row["semantic_work_claim_allowed"])
    assert not bool(row["occupation_inference_allowed"])


def test_synthetic_self_check():
    module = _module()
    result = module.synthetic_self_check()
    assert result["status"] == "ok"
    assert result["users"] == 2
