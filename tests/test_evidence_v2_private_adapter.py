"""Synthetic-only integration tests for trusted Stage-05/08c private-cache adapter."""

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis" / "10a_evidence_v2_private_adapter.py"
)


def _module():
    spec = spec_from_file_location("stage10a_adapter", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _synthetic_inputs():
    diag = []
    expansion = []
    home_dense = []
    home_sparse = []
    office_robust = []
    dropout = []
    user_number = 0

    specs = [
        ("HOME", "HOME_CORE", 27),
        ("OFFICE", "OFFICE_CORE", 16),
        ("HOME", "HOME_PROBABLE", 5),
        ("HOME", "HOME_SPARSE_CANDIDATE", 4),
        ("OFFICE", "OFFICE_ROBUST_CANDIDATE", 3),
    ]
    for label, tier, count in specs:
        for _ in range(count):
            user_number += 1
            user = f"synthetic-{user_number:03d}"
            loc = user_number + 100
            sparse = tier == "HOME_SPARSE_CANDIDATE"
            core = tier.endswith("CORE")
            # Distinct location IDs ensure identity joins are checked.
            top = 0.60 if label == "HOME" else 0.40
            margin = 0.20
            diag.append({
                "user_id": user,
                "label": label,
                "production_HOME": core and label == "HOME",
                "production_OFFICE": core and label == "OFFICE",
                "eligible_location_id": np.nan if sparse else loc,
                "raw_top_location_id": loc,
                "relevant_dwell_share": np.nan if sparse else top,
                "share_margin": np.nan if sparse else margin,
                "relevant_dates": np.nan if sparse else 4,
                "raw_top_relevant_share": .90 if sparse else top,
                "raw_top_share_margin": .90 if sparse else margin,
                "raw_top_relevant_dates": 2 if sparse else 4,
                "home_opportunity_dates": 2 if sparse else 5,
                "office_opportunity_dates": 2 if sparse else 5,
                "home_exposure_regime": "SPARSE" if sparse else "DENSE",
                "office_exposure_regime": "DENSE",
            })
            if tier == "HOME_PROBABLE":
                expansion.append({
                    "user_id": user, "location_id": loc,
                    "home_expansion_tier": "HOME_PROBABLE",
                })
                home_dense.append({"user_id": user, "candidate_location_id": loc})
            if tier == "HOME_SPARSE_CANDIDATE":
                home_sparse.append({"user_id": user, "candidate_location_id": loc})
            if tier == "OFFICE_ROBUST_CANDIDATE":
                office_robust.append({
                    "user_id": user, "candidate_location_id": loc,
                    "robust_policy_candidate": True,
                })
            if not sparse:
                for rate in (0.1, 0.2, 0.3):
                    for seed in (11, 23, 42):
                        dropout.append({
                            "user_id": user, "label": label,
                            "method": "fixed_window",
                            "location_id_reference": loc,
                            "dropout_rate": rate, "seed": seed,
                            "candidate_retained": rate < 0.3,
                        })

    return {
        "diagnostics": pd.DataFrame(diag),
        "home_expansion": pd.DataFrame(expansion),
        "sparse_home": pd.DataFrame(home_sparse),
        "dense_home": pd.DataFrame(home_dense),
        "dense_office": pd.DataFrame(office_robust),
        "dropout": pd.DataFrame(dropout),
    }


def test_private_adapter_exact_tier_lineage_and_missing_robustness():
    stage = _module()
    features = stage.build_candidate_features(**_synthetic_inputs())
    counts = features["tier"].value_counts().to_dict()
    assert counts == stage.EXPECTED_TIERS
    assert len(features) == 55
    assert not features.duplicated(["user_id", "label"]).any()
    sparse = features.loc[features.tier.eq("HOME_SPARSE_CANDIDATE")]
    assert sparse["identity_stability"].isna().all()
    assert sparse["runner_up_share"].isna().all()
    core = features.loc[features.tier.eq("HOME_CORE")]
    assert core["runner_up_share"].iloc[0] == pytest.approx(0.4)
    assert core["identity_stability"].iloc[0] == pytest.approx(6 / 9)
    scored = stage.load_scorer().score_evidence_v2(features)
    assert scored.loc[scored.tier.eq("HOME_SPARSE_CANDIDATE"), "evidence_v2"].isna().all()
    assert scored.loc[scored.tier.eq("HOME_CORE"), "evidence_v2"].notna().all()
    report = stage.load_scorer().aggregate_report(scored)
    assert report["candidate_rows"] == 55
    assert "synthetic-001" not in str(report)
    assert report["calibrated_probability"] is None


def test_private_adapter_rejects_lineage_mismatch():
    stage = _module()
    frames = _synthetic_inputs()
    frames["dense_home"].loc[0, "candidate_location_id"] = 999
    with pytest.raises(ValueError, match="HOME_PROBABLE identity"):
        stage.build_candidate_features(**frames)


def test_private_adapter_rejects_candidate_location_drift():
    stage = _module()
    frames = _synthetic_inputs()
    frames["diagnostics"].loc[0, "eligible_location_id"] = 999
    with pytest.raises(ValueError, match="same-namespace"):
        stage.build_candidate_features(**frames)


def test_private_adapter_refuses_untrusted_or_missing_cache_files(tmp_path):
    stage = _module()
    with pytest.raises(FileNotFoundError, match="Missing PRIVATE Stage artifacts"):
        stage.load_private_features(tmp_path)


def test_private_adapter_uses_exact_declared_cache_layout(tmp_path):
    stage = _module()
    data = _synthetic_inputs()
    for name, path in stage.required_cache_files(tmp_path).items():
        path.parent.mkdir(parents=True, exist_ok=True)
        data[name].to_pickle(path)
    features = stage.load_private_features(tmp_path)
    assert len(features) == 55
    assert features["source_policy"].isin(
        ("frozen_cp2_v2", "08a_08c", "08c_sparse_2of2", "08c_dense_robust")
    ).all()


def test_private_adapter_fails_on_incomplete_dropout_trials():
    stage = _module()
    data = _synthetic_inputs()
    first = data["dropout"].iloc[0]["user_id"]
    mask = ~(
        data["dropout"]["user_id"].eq(first)
        & data["dropout"]["dropout_rate"].eq(0.3)
    )
    data["dropout"] = data["dropout"].loc[mask].copy()
    features = stage.build_candidate_features(**data)
    first_score = features.loc[features.user_id.eq(first), "identity_stability"]
    assert len(first_score) == 1 and pd.isna(first_score.iloc[0])
