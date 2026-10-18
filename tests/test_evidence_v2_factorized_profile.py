"""Synthetic-only validation of factorized evidence; no real GPS or private artifacts."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


SRC = (
    Path(__file__).resolve().parents[1]
    / "analysis" / "10d_evidence_v2_factorized_profile.py"
)


def _stage():
    spec = spec_from_file_location("stage10d_factorized", SRC)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _input():
    rows = [
        # Singleton with known dropout stability: cannot claim C=1.
        ("synthetic-one", "HOME", "HOME_CORE", "MEDIUM", 1, .7, np.nan, 4, 5, .8, np.nan, "sole_eligible_location"),
        ("synthetic-two", "HOME", "HOME_CORE", "DENSE", 2, .65, .25, 4, 5, .9, .7, "has_eligible_runner_up"),
        # Sparse 2/2: high observed opportunity, short support, unknown stability.
        ("synthetic-three", "HOME", "HOME_SPARSE_CANDIDATE", "SPARSE", 3, .8, np.nan, 2, 2, np.nan, np.nan, "sole_eligible_location"),
        ("synthetic-four", "OFFICE", "OFFICE_CORE", "DENSE", 4, .5, .3, 3, 5, .75, .6, "has_eligible_runner_up"),
        ("synthetic-five", "OFFICE", "OFFICE_CORE", "MEDIUM", 5, .9, np.nan, 4, 4, 1.0, np.nan, "sole_eligible_location"),
    ]
    names = (
        "user_id", "label", "tier", "exposure_regime", "location_id", "top_share",
        "runner_up_share", "candidate_support_days", "opportunity_days",
        "identity_stability", "evidence_v2", "eligible_competitor_status",
    )
    data = pd.DataFrame(rows, columns=names)
    provenance = data[list(names[:5]) + ["eligible_competitor_status"]].copy()
    scored = data.drop(columns="eligible_competitor_status")
    return scored, provenance


def test_factorization_preserves_singleton_peer_unknown_and_sparse_stability():
    stage = _stage()
    scored, provenance = _input()
    out = stage.build_factorized_profile(scored, provenance)
    assert len(out) == 5
    assert out["temporal_evidence_available"].all()
    assert int(out["identity_stability_available"].sum()) == 4
    assert int(out["peer_dominance_available"].sum()) == 2
    singleton = out.loc[out["user_id"].eq("synthetic-one")].iloc[0]
    assert pd.isna(singleton["relative_peer_dominance"])
    assert singleton["observed_date_coverage"] == pytest.approx(.8)
    sparse = out.loc[out["user_id"].eq("synthetic-three")].iloc[0]
    assert sparse["observed_date_coverage"] == pytest.approx(1)
    assert sparse["support_factor"] == pytest.approx(.4)
    assert pd.isna(sparse["identity_stability"])
    peer = out.loc[out["user_id"].eq("synthetic-two")].iloc[0]
    assert peer["relative_peer_dominance"] == pytest.approx(.65 / (.65 + .25))
    report = stage.aggregate_factorized(out)
    assert report["overall"]["candidate_rows"] == 5
    assert report["overall"]["temporal_available"] == 5
    assert report["overall"]["original_full_score_available"] == 2
    assert report["single_evidence_v2_score_replacement"] is False
    assert report["calibrated_probability"] is None
    assert "synthetic-one" not in str(report)


def test_no_false_imputation_or_cross_stage_lineage_mismatch():
    stage = _stage()
    scored, provenance = _input()
    provenance.loc[0, "location_id"] = 100
    with pytest.raises(ValueError, match="lineage mismatch"):
        stage.build_factorized_profile(scored, provenance)
    scored, provenance = _input()
    scored.loc[0, "runner_up_share"] = 0
    with pytest.raises(ValueError, match="contradicts"):
        stage.build_factorized_profile(scored, provenance)


def test_score_availability_disagreement_fails_closed():
    stage = _stage()
    scored, provenance = _input()
    scored.loc[0, "evidence_v2"] = .99
    with pytest.raises(ValueError, match="Original v2-score availability"):
        stage.build_factorized_profile(scored, provenance)


def test_group_stat_suppression_and_min_group():
    stage = _stage()
    scored, provenance = _input()
    profiles = stage.build_factorized_profile(scored, provenance)
    report = stage.aggregate_factorized(profiles, min_group=5)
    assert all(
        x["median_identity_stability"] is None for x in report["groups"]
    )
    with pytest.raises(ValueError, match="min_group"):
        stage.aggregate_factorized(profiles, min_group=1)
    # Only known peer evidence qualifies for a conditional peer statistic.
    for x in report["groups"]:
        if x["peer_dominance_available"] == 0:
            assert x["median_relative_peer_dominance"] is None


def test_duplicate_identity_or_bad_observation_fails():
    stage = _stage()
    scored, provenance = _input()
    scored = pd.concat([scored, scored.iloc[[0]]], ignore_index=True)
    with pytest.raises(ValueError, match="Duplicate"):
        stage.build_factorized_profile(scored, provenance)
    scored, provenance = _input()
    scored.loc[0, "opportunity_days"] = 0
    with pytest.raises(ValueError, match="opportunity exposure"):
        stage.build_factorized_profile(scored, provenance)
