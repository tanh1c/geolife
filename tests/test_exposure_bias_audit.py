from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "08b_exposure_bias_audit.py"
)


def _module():
    spec = spec_from_file_location("stage08b", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_exposure_regime_keeps_zero_separate():
    stage = _module()
    values = pd.Series([0, 1, 2, 3, 10, 20, 30])
    regimes = stage.assign_exposure_regime(values)

    assert regimes.iloc[0] == "ZERO"
    assert set(regimes.iloc[1:]).issubset({"SPARSE", "MEDIUM", "DENSE"})
    assert "SPARSE" in set(regimes)
    assert "DENSE" in set(regimes)


def test_gate_status_separates_min_dates_share_and_margin():
    stage = _module()

    assert stage._classify_gate_status(
        opportunity_dates=2,
        has_raw_candidate=True,
        has_eligible_candidate=False,
        share=None,
        margin=None,
        min_share=0.5,
        min_margin=0.2,
    ) == "min_dates_blocked"

    assert stage._classify_gate_status(
        opportunity_dates=10,
        has_raw_candidate=True,
        has_eligible_candidate=True,
        share=0.4,
        margin=0.3,
        min_share=0.5,
        min_margin=0.2,
    ) == "share_blocked"

    assert stage._classify_gate_status(
        opportunity_dates=10,
        has_raw_candidate=True,
        has_eligible_candidate=True,
        share=0.6,
        margin=0.1,
        min_share=0.5,
        min_margin=0.2,
    ) == "margin_blocked"


def test_exposure_limited_summary_counts_full_observed_coverage():
    stage = _module()
    diagnostics = pd.DataFrame(
        [
            {
                "label": "HOME",
                "gate_status": "min_dates_blocked",
                "home_opportunity_dates": 2,
                "raw_top_date_coverage": 1.0,
                "raw_top_relevant_share": 0.9,
            },
            {
                "label": "HOME",
                "gate_status": "min_dates_blocked",
                "home_opportunity_dates": 2,
                "raw_top_date_coverage": 0.5,
                "raw_top_relevant_share": 0.7,
            },
            {
                "label": "OFFICE",
                "gate_status": "min_dates_blocked",
                "office_opportunity_dates": 1,
                "raw_top_date_coverage": 1.0,
                "raw_top_relevant_share": 0.8,
            },
        ]
    )

    out = stage.summarize_exposure_limited_cases(diagnostics)
    home = out.loc[out["label"].eq("HOME")].iloc[0]
    office = out.loc[out["label"].eq("OFFICE")].iloc[0]

    assert int(home["min_dates_blocked_users"]) == 2
    assert int(
        home["blocked_with_all_observed_opportunities_supporting_raw_top"]
    ) == 1
    assert int(office["min_dates_blocked_users"]) == 1


def test_bias_snapshot_does_not_invent_causal_verdict():
    stage = _module()
    regime = pd.DataFrame(
        [
            {"label": "HOME", "exposure_regime": "SPARSE", "emission_rate": 0.1},
            {"label": "HOME", "exposure_regime": "DENSE", "emission_rate": 0.5},
            {"label": "OFFICE", "exposure_regime": "SPARSE", "emission_rate": 0.05},
            {"label": "OFFICE", "exposure_regime": "DENSE", "emission_rate": 0.2},
        ]
    )
    limited = pd.DataFrame(
        [
            {
                "label": "HOME",
                "min_dates_blocked_users": 5,
                "blocked_with_all_observed_opportunities_supporting_raw_top": 2,
            },
            {
                "label": "OFFICE",
                "min_dates_blocked_users": 7,
                "blocked_with_all_observed_opportunities_supporting_raw_top": 3,
            },
        ]
    )
    assoc = pd.DataFrame(
        [
            {
                "label": "HOME",
                "metric": "opportunity_dates_vs_emission",
                "spearman_rho": 0.4,
            },
            {
                "label": "OFFICE",
                "metric": "opportunity_dates_vs_emission",
                "spearman_rho": 0.3,
            },
        ]
    )

    out = stage.build_bias_hypothesis_snapshot(regime, limited, assoc)
    assert set(out.columns) == {
        "label",
        "sparse_emission_rate",
        "dense_emission_rate",
        "opportunity_dates_vs_emission_spearman",
        "min_dates_blocked_users",
        "min_dates_blocked_with_full_observed_coverage",
    }


def test_synthetic_self_check():
    stage = _module()
    assert stage.synthetic_self_check()["status"] == "ok"


def test_notebook_contract():
    import json

    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "08b_exposure_bias_audit.ipynb"
    )
    notebook = json.loads(notebook_path.read_text())
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
    )

    required = [
        "/mnt/geolife-data",
        "home_opportunity_dates",
        "office_opportunity_dates",
        "home_exposure_regime",
        "office_exposure_regime",
        "min_dates_blocked",
        "share_blocked",
        "margin_blocked",
        "HOME_PROBABLE",
        "07j_near_miss_office_audit",
        "08a_home_coverage_expansion",
        "HOME = 27",
        "OFFICE = 16",
        "08b_exposure_bias_audit",
    ]
    for token in required:
        assert token in source
