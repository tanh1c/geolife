from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "08c_exposure_aware_policy.py"
)


def _module():
    spec = spec_from_file_location("stage08c", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_relative_dominance_floors_derive_from_baseline_boundaries():
    stage = _module()
    values = stage.relative_top2_dominance(
        pd.Series([0.50, 0.30]),
        pd.Series([0.20, 0.10]),
    )
    assert np.isclose(values[0], 0.625)
    assert np.isclose(values[1], 0.60)


def test_sparse_home_only_relaxes_absolute_support_dates():
    stage = _module()
    diagnostics = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "label": "HOME",
                "home_exposure_regime": "SPARSE",
                "gate_status": "min_dates_blocked",
                "home_opportunity_dates": 2,
                "raw_top_location_id": 4,
                "raw_top_relevant_dates": 2,
                "raw_top_date_coverage": 1.0,
                "raw_top_relevant_share": 0.60,
                "raw_top_share_margin": 0.25,
                "production_HOME": False,
            },
            {
                "user_id": "u2",
                "label": "HOME",
                "home_exposure_regime": "SPARSE",
                "gate_status": "min_dates_blocked",
                "home_opportunity_dates": 1,
                "raw_top_location_id": 5,
                "raw_top_relevant_dates": 1,
                "raw_top_date_coverage": 1.0,
                "raw_top_relevant_share": 0.80,
                "raw_top_share_margin": 0.50,
                "production_HOME": False,
            },
        ]
    )
    assignments = pd.DataFrame(
        [
            {"user_id": "u1", "label": "HOME", "method": "recurrence", "location_id": 4},
            {"user_id": "u2", "label": "HOME", "method": "recurrence", "location_id": 5},
        ]
    )
    production = pd.DataFrame(
        [{"user_id": "u9", "label": "OFFICE", "location_id": 99}]
    )

    out = stage.sparse_home_support_candidates(
        diagnostics, assignments, production
    )

    assert list(out["user_id"]) == ["u1"]
    assert int(out.iloc[0]["candidate_location_id"]) == 4


def test_dense_home_requires_probable_and_relative_dominance():
    stage = _module()
    diagnostics = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "label": "HOME",
                "home_exposure_regime": "DENSE",
                "gate_status": "share_blocked",
                "eligible_location_id": 3,
                "relevant_dwell_share": 0.40,
                "share_margin": 0.20,
                "production_HOME": False,
            }
        ]
    )
    expansion = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 3,
                "home_expansion_tier": "HOME_PROBABLE",
                "external_exact_family_count": 3,
                "collides_with_production_office": False,
            }
        ]
    )
    out = stage.dense_home_concentration_candidates(diagnostics, expansion)
    assert len(out) == 1
    assert float(out.iloc[0]["relative_top2_dominance"]) > 0.625


def test_dense_office_robust_filter_needs_dropout_and_corroboration():
    stage = _module()
    diagnostics = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "label": "OFFICE",
                "office_exposure_regime": "DENSE",
                "eligible_location_id": 8,
                "relevant_dwell_share": 0.25,
                "share_margin": 0.10,
                "production_OFFICE": False,
            }
        ]
    )
    near = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "audit_group": "share_near",
                "candidate_location_id": 8,
                "candidate_equals_production_home": False,
                "static_comparator_match_count": 1,
                "split_full_candidate_match_count": 0,
                "full_candidate_heldout_top1": False,
                "dropout_candidate_retention": 0.90,
            }
        ]
    )

    out = stage.dense_office_near_miss_candidates(diagnostics, near)
    assert len(out) == 1
    assert bool(out.iloc[0]["robust_policy_candidate"])


def test_policy_summary_keeps_production_unchanged():
    stage = _module()
    sparse = pd.DataFrame({"user_id": ["s1"]})
    dense = pd.DataFrame({"user_id": ["d1", "d2"]})
    office = pd.DataFrame(
        {
            "user_id": ["o1", "o2"],
            "robust_policy_candidate": [True, False],
        }
    )

    out = stage.policy_coverage_summary(sparse, dense, office)
    final = out.loc[out["policy"].eq("exposure_aware_experimental_all")].iloc[0]
    assert int(final["HOME_coverage"]) == 30
    assert int(final["OFFICE_coverage"]) == 17
    assert not bool(final["production_changed"])


def test_synthetic_self_check():
    stage = _module()
    assert stage.synthetic_self_check()["status"] == "ok"


def test_notebook_contract():
    import json

    path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "08c_exposure_aware_policy.ipynb"
    )
    notebook = json.loads(path.read_text())
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
    )

    required = [
        "/mnt/geolife-data",
        "08b_exposure_bias_audit",
        "08a_home_coverage_expansion",
        "07j_near_miss_office_audit",
        "HOME_SPARSE_2OF2_RECURRENCE",
        "HOME_DENSE_RELATIVE_DOMINANCE",
        "OFFICE_DENSE_ROBUST_RELATIVE",
        "HOME_RELATIVE_DOMINANCE_FLOOR",
        "OFFICE_RELATIVE_DOMINANCE_FLOOR",
        "production HOME = 27",
        "production OFFICE = 16",
        "production_changed",
    ]
    for token in required:
        assert token in source
