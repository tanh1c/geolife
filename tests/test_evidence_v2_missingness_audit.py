"""Synthetic-only tests for the Stage10b multi-cause feature audit."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "analysis" / "10b_evidence_v2_missingness_audit.py"


def _stage():
    spec = spec_from_file_location("stage10b_missingness", SRC)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _row(**values):
    data = {
        "user_id": "user-secret",
        "label": "HOME",
        "tier": "HOME_CORE",
        "exposure_regime": "DENSE",
        "top_share": 0.6,
        "runner_up_share": 0.2,
        "candidate_support_days": 4,
        "opportunity_days": 6,
        "identity_stability": 1.0,
        "evidence_v2": 0.75,
    }
    data.update(values)
    return data


def test_report_can_count_multiple_blockers_for_same_candidate():
    stage = _stage()
    rows = [
        _row(user_id="safe-1"),
        _row(
            user_id="safe-2", runner_up_share=np.nan,
            identity_stability=np.nan, evidence_v2=np.nan,
        ),
        _row(
            user_id="safe-3", opportunity_days=0,
            evidence_v2=np.nan,
        ),
        _row(
            user_id="safe-4", runner_up_share=np.nan,
            evidence_v2=np.nan,
        ),
    ]
    result = stage.multi_cause_report(pd.DataFrame(rows))
    overall = result["overall"]
    assert overall["candidate_rows"] == 4
    assert overall["scorable_rows"] == 1
    assert overall["missing_runner_up"] == 2
    assert overall["missing_or_invalid_identity_stability"] == 1
    assert overall["invalid_observed_opportunity"] == 1
    assert overall["multiple_blockers"] == 1
    assert result["counts_may_overlap"] is True
    assert result["groups"][0]["score_median_suppressed"] is True
    assert "user-secret" not in str(result)


def test_audit_fails_if_stage10a_score_disagrees_with_complete_features():
    with pytest.raises(ValueError, match="Mismatch"):
        _stage().multi_cause_report(
            pd.DataFrame([_row(evidence_v2=np.nan)])
        )


def test_invalid_second_is_not_mislabeled_missing():
    stage = _stage()
    bad = pd.DataFrame([
        _row(runner_up_share=0.7, evidence_v2=np.nan),
    ])
    overall = stage.multi_cause_report(bad)["overall"]
    assert overall["missing_runner_up"] == 0
    assert overall["invalid_top_or_runner_up"] == 1


def test_partial_scores_and_null_stability_not_imputed():
    stage = _stage()
    bad = pd.DataFrame([
        _row(
            runner_up_share=np.nan,
            identity_stability=np.nan,
            evidence_v2=np.nan,
        )
    ])
    report = stage.multi_cause_report(bad)["overall"]
    assert report["scorable_rows"] == 0
    assert report["missing_runner_up"] == 1
    assert report["missing_or_invalid_identity_stability"] == 1


def test_required_columns_and_min_group_validation():
    stage = _stage()
    with pytest.raises(ValueError, match="Missing expected"):
        stage.multi_cause_report(pd.DataFrame([{"foo": 1}]))
    with pytest.raises(ValueError, match="min_group"):
        stage.multi_cause_report(pd.DataFrame([_row()]), min_group=1)
