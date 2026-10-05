from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys

import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07l_imagery_unblinding_synthesis.py"
)


def _module():
    spec = spec_from_file_location("stage07l", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _review_rows():
    classes = [
        "large_office_commercial_like_complex",
        "education_campus",
        "industrial_warehouse",
        "residential_compound",
        "transport_infrastructure",
        "mixed_urban_block",
        "other_visible_structure",
        "ambiguous",
        "healthcare_institutional",
    ]
    rows = []
    for i, klass in enumerate(classes, start=1):
        rows.append(
            {
                "audit_id": f"I{i:02d}",
                "imagery_available": "yes",
                "imagery_date_used": "approx 2008",
                "imagery_date_offset_days": "",
                "imagery_quality": "high",
                "structure_present": "yes",
                "visual_context_class": klass,
                "visual_context_confidence": "medium",
                "candidate_inside_same_complex": "yes",
                "historical_name_evidence": "",
                "present_day_name_aid": "",
                "review_notes": "",
            }
        )
    return pd.DataFrame(rows)


def _key():
    rows = []
    for i in range(1, 10):
        rows.append(
            {
                "audit_id": f"I{i:02d}",
                "user_id": f"u{i}",
                "audit_group": "margin_near" if i <= 2 else "share_near",
                "candidate_location_id": 100 + i,
                "production_home_location_id": i,
                "candidate_home_distance_m": 1000.0 + i,
                "full_support_days": 3 + i,
                "full_office_share": 0.2 + i / 100.0,
                "howde_matches_candidate": i % 2 == 0,
                "recurrence_matches_candidate": i == 3,
                "split_full_candidate_match_count": 2 if i == 4 else 0,
                "full_candidate_heldout_top1": i in {4, 5},
                "dropout_candidate_retention": 1.0 if i <= 5 else 0.8,
                "bcl_evaluable": i in {1, 2},
                "work_compatible_lexical_within_100m": False,
                "business_name_within_100m": False,
                "work_compatible_lexical_within_150m": False,
                "business_name_within_150m": False,
            }
        )
    return pd.DataFrame(rows)


def _audit():
    rows = []
    for i in range(1, 10):
        rows.append(
            {
                "user_id": f"u{i}",
                "audit_group": "margin_near" if i <= 2 else "share_near",
                "candidate_location_id": 100 + i,
                "candidate_equals_production_home": False,
                "howde_matches_candidate": i % 2 == 0,
                "recurrence_matches_candidate": i == 3,
                "split_full_candidate_match_count": 2 if i == 4 else 0,
                "full_candidate_heldout_top1": i in {4, 5},
                "dropout_candidate_retention": 1.0 if i <= 5 else 0.8,
                "bcl_evaluable": i in {1, 2},
                "work_compatible_lexical_within_100m": False,
                "business_name_within_100m": False,
                "work_compatible_lexical_within_150m": False,
                "business_name_within_150m": False,
            }
        )
    return pd.DataFrame(rows)


def test_visual_bucket_rules_are_conservative():
    module = _module()
    assert module.classify_visual_bucket(
        "large_office_commercial_like_complex"
    ) == "office_like"
    assert module.classify_visual_bucket(
        "education_campus"
    ) == "institutional_or_daytime_compatible"
    assert module.classify_visual_bucket(
        "industrial_warehouse"
    ) == "institutional_or_daytime_compatible"
    assert module.classify_visual_bucket(
        "residential_compound"
    ) == "office_contradictory_context"
    assert module.classify_visual_bucket(
        "transport_infrastructure"
    ) == "office_contradictory_context"
    assert module.classify_visual_bucket(
        "mixed_urban_block"
    ) == "indeterminate"


def test_build_unblinded_panel_matches_all_nine():
    module = _module()
    panel = module.build_unblinded_panel(
        _review_rows(), _key(), _audit()
    )
    assert len(panel) == 9
    assert panel["audit_id"].nunique() == 9
    assert set(panel["audit_group"]) == {"margin_near", "share_near"}
    assert "user_id" in panel.columns
    assert panel["visual_bucket"].notna().all()


def test_unblinding_rejects_missing_review_id():
    module = _module()
    review = _review_rows().iloc[:-1].copy()
    with pytest.raises(ValueError, match="expected 9 reviewed"):
        module.build_unblinded_panel(review, _key(), _audit())


def test_policy_snapshot_does_not_create_promotion_score():
    module = _module()
    panel = module.build_unblinded_panel(
        _review_rows(), _key(), _audit()
    )
    snapshot = module.policy_snapshot(panel)
    assert len(snapshot) == 1
    assert "promotion_score" not in snapshot.columns
    assert snapshot.iloc[0]["near_miss_users"] == 9
    assert snapshot.iloc[0]["office_like_imagery_users"] == 1


def test_cross_source_signatures_remain_transparent():
    module = _module()
    panel = module.build_unblinded_panel(
        _review_rows(), _key(), _audit()
    )
    signatures = module.summarize_cross_source_signatures(panel)
    required = {
        "audit_group",
        "visual_bucket",
        "howde_match",
        "recurrence_match",
        "both_splits",
        "heldout_top1",
        "dropout_perfect",
        "bcl_work_150m",
        "bcl_business_150m",
        "users",
    }
    assert required.issubset(signatures.columns)


def test_stage07l_notebook_contract():
    path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07l_imagery_unblinding_synthesis.ipynb"
    )
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )
    required = [
        "GEOLIFE_07K_REVIEW_CSV",
        "historical_imagery_unblinding_key_private.pkl",
        "near_miss_office_audit_private.pkl",
        "unblinding validation: PASS",
        "visual_context_by_near_miss_family.csv",
        "behavior_by_visual_bucket.csv",
        "cross_source_signature_summary.csv",
        "policy_snapshot.csv",
        "imagery_behavior_bcl_case_matrix_private.pkl",
    ]
    for snippet in required:
        assert snippet in code

    assert "promotion_score" not in code
