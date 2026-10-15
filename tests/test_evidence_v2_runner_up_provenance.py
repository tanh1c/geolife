"""Synthetic Stage10c tests; private GeoLife candidate/coordinate data never load in CI."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


SRC = (
    Path(__file__).resolve().parents[1]
    / "analysis" / "10c_evidence_v2_runner_up_provenance.py"
)


def _stage():
    spec = spec_from_file_location("stage10c_runner_up", SRC)
    assert spec and spec.loader
    m = module_from_spec(spec)
    sys.modules[spec.name] = m
    spec.loader.exec_module(m)
    return m


def _feature(user, loc, *, home_share=0, home_dates=0, office_share=0,
             office_dates=0, stays=2):
    return {
        "user_id": user,
        "location_id": loc,
        "stay_count": stays,
        "home_dwell_share": home_share,
        "home_dates": home_dates,
        "home_dwell_s": 3600 * home_share,
        "office_dwell_share": office_share,
        "office_dates": office_dates,
        "office_dwell_s": 3600 * office_share,
    }


def _candidate(user, loc, label, tier, top, runner):
    return {
        "user_id": user,
        "location_id": loc,
        "label": label,
        "tier": tier,
        "exposure_regime": "DENSE",
        "top_share": top,
        "runner_up_share": runner,
    }


def _fixtures():
    features = pd.DataFrame([
        _feature("u-home-single", 1, home_share=.8, home_dates=4),
        _feature("u-home-single", 2, home_share=.2, home_dates=2),  # not eligible
        _feature("u-home-two", 1, home_share=.6, home_dates=4),
        _feature("u-home-two", 2, home_share=.3, home_dates=3),
        _feature("u-home-sparse", 3, home_share=.75, home_dates=2),
        _feature("u-home-sparse", 4, home_share=.2, home_dates=0),  # raw does allow 0 dates
        _feature("u-office-single", 1, office_share=.8, office_dates=4),
    ])
    scored = pd.DataFrame([
        _candidate("u-home-single", 1, "HOME", "HOME_CORE", .8, np.nan),
        _candidate("u-home-two", 1, "HOME", "HOME_CORE", .6, .3),
        _candidate("u-home-sparse", 3, "HOME", "HOME_SPARSE_CANDIDATE", .75, .2),
        _candidate("u-office-single", 1, "OFFICE", "OFFICE_CORE", .8, np.nan),
    ])
    return scored, features


def test_exact_runner_up_provenance_and_label_specific_raw_ranking():
    scorer = _stage()
    scored, features = _fixtures()
    detail = scorer.audit_runner_up(scored, features)
    assert len(detail) == 4
    assert detail["eligible_competitor_status"].tolist() == [
        "sole_eligible_location", "has_eligible_runner_up",
        "has_eligible_runner_up", "sole_eligible_location",
    ]
    assert detail["eligible_location_count"].tolist() == [1, 2, 2, 1]
    summary = scorer.aggregate_report(detail)
    assert summary["candidate_rows"] == 4
    assert summary["sole_eligible_location"] == 2
    assert summary["has_eligible_runner_up"] == 2
    assert "u-home-single" not in str(summary)


def test_audit_rejects_changed_cp2_top_location_id():
    scored, features = _fixtures()
    scored.loc[scored["user_id"].eq("u-home-two"), "location_id"] = 999
    with pytest.raises(ValueError, match="identity diverges"):
        _stage().audit_runner_up(scored, features)


def test_audit_rejects_changed_top_share():
    scored, features = _fixtures()
    scored.loc[scored["user_id"].eq("u-home-two"), "top_share"] = .61
    with pytest.raises(ValueError, match="top share diverges"):
        _stage().audit_runner_up(scored, features)


def test_audit_detects_stage10a_peer_mismatch():
    scored, features = _fixtures()
    scored.loc[scored["user_id"].eq("u-home-two"), "runner_up_share"] = np.nan
    with pytest.raises(ValueError, match="lost an existing eligible runner-up"):
        _stage().audit_runner_up(scored, features)


def test_stage08b_filled_zero_is_not_assumed_an_observed_runner_up():
    scored, features = _fixtures()
    scored.loc[scored["user_id"].eq("u-home-single"), "runner_up_share"] = 0.0
    with pytest.raises(ValueError, match="falsely has a known runner-up"):
        _stage().audit_runner_up(scored, features)
