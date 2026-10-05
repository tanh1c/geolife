from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07p_methodological_synthesis.py"
)


def _module():
    spec = spec_from_file_location("stage07p", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_final_policy_snapshot_uses_frozen_gate_and_near_miss_counts():
    stage = _module()
    frames = {
        "07i_office_gate": pd.DataFrame(
            [
                {
                    "office_min_dates": 3,
                    "office_min_share": 0.30,
                    "office_min_margin": 0.10,
                    "emitted_users": 16,
                    "new_vs_baseline_emitted": 0,
                },
                {
                    "office_min_dates": 3,
                    "office_min_share": 0.30,
                    "office_min_margin": 0.05,
                    "emitted_users": 18,
                    "new_vs_baseline_emitted": 2,
                },
                {
                    "office_min_dates": 3,
                    "office_min_share": 0.20,
                    "office_min_margin": 0.10,
                    "emitted_users": 23,
                    "new_vs_baseline_emitted": 7,
                },
            ]
        ),
        "07l_policy": pd.DataFrame(
            [
                {
                    "near_miss_users": 9,
                    "both_split_tests_users": 1,
                    "heldout_top1_users": 2,
                    "bcl_work_context_150m_users": 0,
                }
            ]
        ),
    }

    out = stage.build_final_policy_snapshot(frames).iloc[0]

    assert int(out["production_HOME"]) == 27
    assert int(out["production_OFFICE"]) == 16
    assert int(out["office_margin_relax_extra_users"]) == 2
    assert int(out["office_share_relax_extra_users"]) == 7
    assert not bool(out["change_office_gate"])
    assert out["final_policy"] == "freeze_HOME_27_OFFICE_16"


def test_pipeline_sensitivity_summary_orders_upstream_and_semantic_layers():
    stage = _module()
    frames = {
        "07n_stay": pd.DataFrame(
            [
                {"source_inventory": "CP1", "strong_match_rate": 0.365},
                {"source_inventory": "TRACKINTEL", "strong_match_rate": 0.968},
            ]
        ),
        "07n_location": pd.DataFrame(
            [
                {
                    "variant": "dbscan100",
                    "scope": "recurring_production_locations",
                    "within_200m": 559,
                    "production_locations": 716,
                },
                {
                    "variant": "dbscan200",
                    "scope": "recurring_production_locations",
                    "within_200m": 530,
                    "production_locations": 716,
                },
            ]
        ),
        "07n_semantic": pd.DataFrame(
            [
                {"variant": "dbscan200", "label": "HOME", "within_200m": 21},
                {"variant": "dbscan200", "label": "OFFICE", "within_200m": 9},
            ]
        ),
    }

    out = stage.build_pipeline_sensitivity_summary(frames)

    assert set(out["layer"]) == {
        "stay extraction",
        "location geometry",
        "semantic candidate",
    }
    home = out.loc[out["metric"].str.contains("HOME")].iloc[0]
    office = out.loc[out["metric"].str.contains("OFFICE")].iloc[0]
    assert np.isclose(home["value"], 21 / 27)
    assert np.isclose(office["value"], 9 / 16)


def test_claim_boundary_keeps_accuracy_and_poi_proof_out_of_scope():
    stage = _module()
    boundary = stage.build_claim_boundary()

    unsupported = " ".join(
        boundary.loc[boundary["claim_type"].eq("not_supported"), "claim"].tolist()
    ).lower()
    assert "accuracy" in unsupported
    assert "ground truth" in unsupported
    assert "poi" in unsupported


def test_synthetic_self_check():
    stage = _module()
    assert stage.synthetic_self_check()["status"] == "ok"


def test_notebook_contract():
    import json

    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07p_methodological_synthesis.ipynb"
    )
    notebook = json.loads(notebook_path.read_text())
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
    )

    required = [
        "/mnt/geolife-data/cache/cp2_v2",
        "05_home_office_reliability_validation",
        "07i_threshold_sensitivity",
        "07j_near_miss_office_audit",
        "07l_imagery_unblinding_synthesis",
        "07m_trackintel_semantic_parity",
        "07n_trackintel_end_to_end",
        "07o_literature_comparator_suite",
        "validate_measured_inputs",
        "HOME = 27",
        "OFFICE = 16",
        "freeze_HOME_27_OFFICE_16",
        "07p_methodological_synthesis",
    ]
    for token in required:
        assert token in source
