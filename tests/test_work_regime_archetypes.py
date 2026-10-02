from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd

MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07_work_regime_archetypes.py"
)


def _module():
    spec = spec_from_file_location("stage07", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_specific_regimes_take_precedence_over_broader_states():
    module = _module()
    behavior = pd.DataFrame(
        [
            {
                "user_id": "route",
                "anchor_count_class": "multiple_anchor",
                "mobile_work_like_candidate": True,
                "stable_shifted_candidate": False,
            },
            {
                "user_id": "shift",
                "anchor_count_class": "two_anchor",
                "mobile_work_like_candidate": False,
                "stable_shifted_candidate": True,
            },
        ]
    )
    work = pd.DataFrame(
        [
            {"user_id": "route", "window_pattern": "multi_anchor"},
            {"user_id": "shift", "window_pattern": "stable_secondary_anchor"},
        ]
    )
    routine = pd.DataFrame(
        [
            {"user_id": "route", "has_repeated_edge": True},
            {"user_id": "shift", "has_repeated_edge": True},
        ]
    )

    result = module.run_audit(behavior, work, routine).archetypes.set_index("user_id")

    assert result.loc["route", "work_regime"] == "route_centric_mobile_like"
    assert result.loc["route", "work_representation"] == "route_or_activity_region"
    assert result.loc["shift", "work_regime"] == "shifted_fixed_site_like"
    assert (
        result.loc["shift", "work_representation"]
        == "single_work_anchor_schedule_agnostic"
    )


def test_multi_anchor_without_route_recurrence_is_irregular_not_mobile():
    module = _module()
    behavior = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "anchor_count_class": "multiple_anchor",
                "mobile_work_like_candidate": True,
                "stable_shifted_candidate": False,
            }
        ]
    )
    work = pd.DataFrame([{"user_id": "u1", "window_pattern": "multi_anchor"}])
    routine = pd.DataFrame([{"user_id": "u1", "has_repeated_edge": False}])

    row = module.run_audit(behavior, work, routine).archetypes.iloc[0]

    assert row["work_regime"] == "irregular"
    assert row["work_representation"] == "abstain_fixed_workplace"


def test_fixed_site_like_does_not_become_semantic_office_or_occupation():
    module = _module()
    behavior = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "anchor_count_class": "two_anchor",
                "stable_shifted_candidate": False,
                "mobile_work_like_candidate": False,
            }
        ]
    )
    work = pd.DataFrame(
        [{"user_id": "u1", "window_pattern": "stable_secondary_anchor"}]
    )
    routine = pd.DataFrame([{"user_id": "u1", "has_repeated_edge": True}])

    row = module.run_audit(behavior, work, routine).archetypes.iloc[0]

    assert row["work_regime"] == "fixed_site_like"
    assert not bool(row["semantic_claim_allowed"])
    assert not bool(row["occupation_inference_allowed"])


def test_home_context_and_independent_secondary_evidence_are_diagnostic_only():
    module = _module()
    behavior = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "anchor_count_class": "two_anchor",
                "stable_shifted_candidate": False,
                "mobile_work_like_candidate": False,
            }
        ]
    )
    work = pd.DataFrame(
        [{"user_id": "u1", "window_pattern": "stable_secondary_anchor"}]
    )
    routine = pd.DataFrame(
        [{"user_id": "u1", "has_repeated_edge": True, "distinct_edges": 2}]
    )
    home = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 0,
                "home_tier": "high",
                "unique_vote_winner": True,
            }
        ]
    )
    independent = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "valid_evidence_axes": 4,
                "top1_evidence_axes": 2,
                "beats_peer_median_axes": 3,
                "comparator_anchor_count": 4,
            }
        ]
    )

    audit = module.run_audit(
        behavior,
        work,
        routine,
        home_evidence=home,
        independent_secondary_evidence=independent,
    )
    row = audit.archetypes.iloc[0]

    assert bool(row["home_context_supported"])
    assert bool(row["independent_secondary_evidence_available"])
    assert row["work_regime"] == "fixed_site_like"
    assert int(row["top1_evidence_axes"]) == 2


def test_missing_work_or_routine_evidence_abstains():
    module = _module()
    behavior = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "anchor_count_class": "dominant_anchor",
                "stable_shifted_candidate": False,
                "mobile_work_like_candidate": False,
            }
        ]
    )
    work = pd.DataFrame(
        [{"user_id": "u2", "window_pattern": "insufficient"}]
    )
    routine = pd.DataFrame(
        [{"user_id": "u3", "has_repeated_edge": False}]
    )

    archetypes = module.run_audit(behavior, work, routine).archetypes.set_index("user_id")

    assert archetypes.loc["u1", "work_regime"] == "insufficient"
    assert archetypes.loc["u2", "work_regime"] == "insufficient"
    assert archetypes.loc["u3", "work_regime"] == "insufficient"


def test_synthetic_self_check():
    module = _module()
    result = module.synthetic_self_check()
    assert result["status"] == "ok"
    assert result["users"] == 5
