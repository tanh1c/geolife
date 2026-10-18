"""Stage 10g synthetic-only v1 TRAIN evidence vs future persistence tests."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest


SRC = (
    Path(__file__).resolve().parents[1]
    / "analysis" / "10g_train_score_recurrence_audit.py"
)


def _module():
    spec = spec_from_file_location("stage10g_train_audit", SRC)
    assert spec is not None and spec.loader is not None
    obj = module_from_spec(spec)
    sys.modules[spec.name] = obj
    spec.loader.exec_module(obj)
    return obj


def _row(i, *, label="HOME", future_dates=3, matched_dates=2,
         eligible=1, score=.75, support=4):
    return {
        "user_id": f"synthetic-{i:02d}",
        "label": label,
        "train_location_id": 0,
        "train_evidence_strength": score,
        "train_support_dates": support,
        "train_eligible_location_count": eligible,
        "future_observed_window_dates": future_dates,
        "future_same_anchor_window_dates": matched_dates,
        "future_window_assessable": future_dates >= 1,
        "future_same_anchor_reappears": future_dates >= 1 and matched_dates >= 1,
    }


def test_valid_score_association_is_train_only_and_recurrence_aware():
    stage = _module()
    rows = [
        _row(1, score=.80, matched_dates=2),
        _row(2, score=.86, matched_dates=1),
        _row(3, score=.90, matched_dates=0),
        _row(4, score=.60, matched_dates=0),
        _row(5, score=.78, matched_dates=2),
        _row(6, score=.71, matched_dates=0),
        _row(7, score=.75, matched_dates=1),
        _row(8, label="OFFICE", future_dates=0, matched_dates=0),
    ]
    checked = stage.validate_private_train_results(pd.DataFrame(rows))
    result = stage.aggregate_train_score(checked)
    assert result["overall"]["train_emitted_candidates"] == 8
    assert result["overall"]["future_assessable_1date"] == 7
    assert result["overall"]["future_reappears_1date"] == 4
    assert result["overall"]["future_assessable_2dates"] == 7
    assert result["overall"]["future_reappears_2dates"] == 2
    assert result["overall"]["median_train_v1_score_reappears"] is None
    assert result["overall"]["median_train_v1_score_not_reappears"] is None
    assert result["overall"]["retention_share_1date"] == pytest.approx(4/7, abs=1e-6)
    assert result["overall"]["retention_share_2dates"] == pytest.approx(2/7, abs=1e-6)
    assert result["experimental_evidence_v2_evaluated"] is False
    assert "synthetic-" not in str(result)
    assert result["calibrated_probability"] is None


def test_singleton_and_multiple_competitor_strata_are_separate():
    stage = _module()
    rows = [_row(i, eligible=1) for i in range(5)]
    rows += [_row(i + 5, eligible=2, matched_dates=0) for i in range(5)]
    checked = stage.validate_private_train_results(pd.DataFrame(rows))
    report = stage.aggregate_train_score(checked)
    group = {x["train_competitor_group"]: x for x in report["train_competitor_groups"]}
    assert group["singleton_eligible"]["future_reappears_1date"] == 5
    assert group["multiple_eligible"]["future_reappears_1date"] == 0
    assert group["singleton_eligible"]["retention_share_1date"] == 1.0
    assert group["multiple_eligible"]["retention_share_1date"] == 0.0


def test_two_date_gate_needs_two_actual_candidate_dates():
    stage = _module()
    row = _row(1, future_dates=2, matched_dates=1)
    output = stage.validate_private_train_results(pd.DataFrame([row]))
    assert output.iloc[0]["future_same_anchor_reappears"]
    assert output.iloc[0]["future_2date_assessable"]
    assert not output.iloc[0]["future_2date_reappears"]


def test_impossible_future_date_and_flag_mismatch_rejected():
    stage = _module()
    rows = pd.DataFrame([_row(1, future_dates=1, matched_dates=2)])
    with pytest.raises(ValueError, match="exceed observed"):
        stage.validate_private_train_results(rows)
    rows = pd.DataFrame([_row(1)])
    rows.loc[0, "future_same_anchor_reappears"] = False
    with pytest.raises(ValueError, match="flags disagree"):
        stage.validate_private_train_results(rows)


def test_duplicate_identity_and_prohibited_small_group_request_rejected():
    stage = _module()
    row = _row(1)
    with pytest.raises(ValueError, match="Duplicate TRAIN"):
        stage.validate_private_train_results(pd.DataFrame([row, row]))
    checked = stage.validate_private_train_results(pd.DataFrame([row]))
    with pytest.raises(ValueError, match="at least 5"):
        stage.aggregate_train_score(checked, min_group=1)
