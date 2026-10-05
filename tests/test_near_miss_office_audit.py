from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys

import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07j_near_miss_office_audit.py"
)


def _module():
    spec = spec_from_file_location("stage07j", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _office_details(module):
    rows = []

    def add(user, loc, gate, support=4, score=.4):
        rows.append(
            {
                "user_id": user,
                "location_id": loc,
                "support_days": support,
                "score": score,
                "office_min_dates": gate[0],
                "office_min_share": gate[1],
                "office_min_margin": gate[2],
            }
        )

    # baseline user appears in all relaxed configs
    add("b", 1, module.BASELINE_GATE)
    add("b", 1, module.MARGIN_RELAX_GATE)
    add("b", 1, module.SHARE_RELAX_GATE)

    # one-step near misses
    add("m", 2, module.MARGIN_RELAX_GATE, score=.31)
    add("s", 3, module.SHARE_RELAX_GATE, score=.25)
    return pd.DataFrame(rows)


def test_build_audit_cohort_is_disjoint_and_keeps_only_new_users():
    module = _module()
    cohort = module.build_audit_cohort(_office_details(module))

    counts = dict(
        zip(
            cohort["audit_group"],
            cohort["user_id"],
        )
    )
    assert set(cohort["audit_group"]) == {
        "baseline",
        "margin_near",
        "share_near",
    }
    assert len(cohort) == 3
    assert cohort["user_id"].nunique() == 3
    assert cohort.loc[
        cohort["audit_group"].eq("margin_near"), "user_id"
    ].tolist() == ["m"]
    assert cohort.loc[
        cohort["audit_group"].eq("share_near"), "user_id"
    ].tolist() == ["s"]


def test_overlapping_margin_and_share_near_miss_is_rejected():
    module = _module()
    details = _office_details(module)
    extra = pd.DataFrame(
        [
            {
                "user_id": "x",
                "location_id": 9,
                "support_days": 4,
                "score": .35,
                "office_min_dates": module.MARGIN_RELAX_GATE[0],
                "office_min_share": module.MARGIN_RELAX_GATE[1],
                "office_min_margin": module.MARGIN_RELAX_GATE[2],
            },
            {
                "user_id": "x",
                "location_id": 9,
                "support_days": 4,
                "score": .25,
                "office_min_dates": module.SHARE_RELAX_GATE[0],
                "office_min_share": module.SHARE_RELAX_GATE[1],
                "office_min_margin": module.SHARE_RELAX_GATE[2],
            },
        ]
    )
    details = pd.concat([details, extra], ignore_index=True)
    with pytest.raises(ValueError, match="unexpectedly overlap"):
        module.build_audit_cohort(details)


def test_static_method_evidence_checks_candidate_identity_and_home_collision():
    module = _module()
    cohort = module.build_audit_cohort(_office_details(module))
    assignments = pd.DataFrame(
        [
            {"user_id":"b","method":"fixed_window","label":"OFFICE","location_id":1,"score":.4,"support_days":4,"emitted":True},
            {"user_id":"m","method":"fixed_window","label":"OFFICE","location_id":2,"score":.31,"support_days":4,"emitted":False},
            {"user_id":"s","method":"fixed_window","label":"OFFICE","location_id":3,"score":.25,"support_days":4,"emitted":False},
            {"user_id":"m","method":"howde_style","label":"OFFICE","location_id":2,"score":.5,"support_days":4,"emitted":False},
            {"user_id":"m","method":"recurrence","label":"OFFICE","location_id":4,"score":.5,"support_days":4,"emitted":False},
            {"user_id":"m","method":"fixed_window","label":"HOME","location_id":2,"score":.6,"support_days":5,"emitted":True},
        ]
    )
    panel = module.attach_static_method_evidence(cohort, assignments).set_index("user_id")

    assert bool(panel.loc["m","howde_matches_candidate"])
    assert not bool(panel.loc["m","recurrence_matches_candidate"])
    assert panel.loc["m","static_comparator_match_count"] == 1
    assert bool(panel.loc["m","candidate_equals_production_home"])


def test_split_half_evidence_requires_each_half_to_match_full_candidate():
    module = _module()
    cohort = module.build_audit_cohort(_office_details(module))
    details = pd.DataFrame(
        [
            {"user_id":"m","method":"fixed_window","label":"OFFICE","split":"first_second","location_id_left":2,"location_id_right":2},
            {"user_id":"m","method":"fixed_window","label":"OFFICE","split":"odd_even","location_id_left":2,"location_id_right":7},
        ]
    )
    out = module.attach_split_half_evidence(cohort, details).set_index("user_id")
    assert bool(out.loc["m","first_second_both_match_candidate"])
    assert not bool(out.loc["m","odd_even_both_match_candidate"])
    assert out.loc["m","split_full_candidate_match_count"] == 1


def test_bcl_context_is_evaluable_only_on_exact_user_location_match():
    module = _module()
    cohort = module.build_audit_cohort(_office_details(module))
    metrics = pd.DataFrame(
        [
            {
                "user_id":"m",
                "location_id":2,
                "work_compatible_lexical_within_100m":True,
                "business_name_within_100m":False,
                "education_within_100m":True,
                "retail_service_within_100m":False,
                "work_compatible_lexical_within_150m":True,
                "business_name_within_150m":True,
                "education_within_150m":True,
                "retail_service_within_150m":False,
            }
        ]
    )
    out = module.attach_bcl_context(cohort, metrics).set_index("user_id")
    assert bool(out.loc["m","bcl_evaluable"])
    assert bool(out.loc["m","business_name_within_150m"])
    assert not bool(out.loc["s","bcl_evaluable"])


def test_synthetic_self_check():
    module = _module()
    result = module.synthetic_self_check()
    assert result["status"] == "ok"
    assert result["rows"] == 3


def test_stage07j_notebook_contract():
    path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07j_near_miss_office_audit.ipynb"
    )
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    required = [
        "near-miss cohort reproduction: PASS",
        "full-period candidate identity validation: PASS",
        "near_miss_office_audit_private.pkl",
        "behavioral_robustness.csv",
        "bcl_context_summary.csv",
        "STATIC COMPARATOR MATCH COUNT",
        "SPLIT FULL-CANDIDATE MATCH COUNT",
    ]
    for snippet in required:
        assert snippet in code

    assert "dropout_retention_ge_75pct_users" not in code
    assert "promotion_score" not in code
