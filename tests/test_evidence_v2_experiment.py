"""Synthetic-only tests: never load GeoLife private caches in CI."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "analysis" / "10_evidence_v2_experiment.py"
)


def _module():
    spec = spec_from_file_location("stage10_evidence_v2", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _row(**changes):
    row = {
        "user_id": "synthetic-01",
        "label": "HOME",
        "location_id": 0,
        "tier": "HOME_CORE",
        "exposure_regime": "MEDIUM",
        "top_share": 0.6,
        "runner_up_share": 0.2,
        "candidate_support_days": 4,
        "opportunity_days": 5,
        "identity_stability": 0.9,
    }
    row.update(changes)
    return row


def test_formula_components_and_bounded_score():
    scored = _module().score_evidence_v2(pd.DataFrame([_row()]))
    result = scored.iloc[0]
    assert result["v2_status"] == "ok"
    assert result["relative_dominance"] == pytest.approx(0.75)
    assert result["opportunity_coverage"] == pytest.approx(0.8)
    assert result["support_factor"] == pytest.approx(0.8)
    assert result["evidence_v2"] == pytest.approx(
        np.cbrt(0.75 * 0.8 * 0.9) * np.sqrt(0.8)
    )
    assert 0 < result["evidence_v2"] <= 1


def test_sparse_two_of_two_gets_support_penalty_not_perfect_score():
    scored = _module().score_evidence_v2(
        pd.DataFrame([
            _row(candidate_support_days=2, opportunity_days=2, identity_stability=1)
        ])
    )
    result = scored.iloc[0]
    assert result["opportunity_coverage"] == pytest.approx(1.0)
    assert result["support_factor"] == pytest.approx(0.4)
    assert result["evidence_v2"] < 0.7


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"runner_up_share": np.nan}, "missing_or_invalid_runner_up"),
        ({"runner_up_share": 0.7}, "missing_or_invalid_runner_up"),
        ({"top_share": 0}, "missing_or_invalid_runner_up"),
        ({"opportunity_days": 0}, "missing_or_invalid_opportunity"),
        ({"candidate_support_days": 6, "opportunity_days": 5}, "missing_or_invalid_opportunity"),
        ({"identity_stability": np.nan}, "missing_or_invalid_stability"),
        ({"identity_stability": 1.1}, "missing_or_invalid_stability"),
    ],
)
def test_incomplete_or_invalid_inputs_do_not_fabricate_scores(changes, reason):
    scored = _module().score_evidence_v2(pd.DataFrame([_row(**changes)]))
    assert scored.iloc[0]["v2_status"] == reason
    assert pd.isna(scored.iloc[0]["evidence_v2"])


def test_robustness_zero_yields_zero_not_missing():
    scored = _module().score_evidence_v2(
        pd.DataFrame([_row(identity_stability=0)])
    )
    assert scored.iloc[0]["v2_status"] == "ok"
    assert scored.iloc[0]["evidence_v2"] == 0


def test_validation_does_not_accept_duplicate_or_work_as_label():
    stage = _module()
    with pytest.raises(ValueError, match="Duplicate"):
        stage.score_evidence_v2(pd.DataFrame([_row(), _row()]))
    with pytest.raises(ValueError, match="HOME/OFFICE"):
        stage.score_evidence_v2(pd.DataFrame([_row(label="WORK")]))


def test_small_groups_suppress_score_statistics_and_never_export_user_ids():
    stage = _module()
    rows = [
        _row(user_id=f"private-id-{i}", location_id=i, tier="HOME_PROBABLE")
        for i in range(3)
    ]
    scored = stage.score_evidence_v2(pd.DataFrame(rows))
    report = stage.aggregate_report(scored, min_group=5)
    assert report["candidate_rows"] == 3
    assert report["groups"][0]["median_evidence_v2"] is None
    assert report["calibrated_probability"] is None
    assert "private-id-" not in str(report)
    with pytest.raises(ValueError, match="at least 2"):
        stage.aggregate_report(scored, min_group=1)


def test_empty_frame_has_no_scoring_failure():
    stage = _module()
    empty = pd.DataFrame(columns=sorted(stage.REQUIRED))
    scored = stage.score_evidence_v2(empty)
    report = stage.aggregate_report(scored)
    assert report["candidate_rows"] == 0
    assert report["groups"] == []
