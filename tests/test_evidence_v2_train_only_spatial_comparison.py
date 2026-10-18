"""Synthetic-only Stage10l TRAIN score and spatially controlled comparison tests."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd
import pytest

SOURCE = Path(__file__).resolve().parents[1] / "analysis" / "10l_train_only_v1_v2_spatial_comparison.py"


def _load():
    spec = spec_from_file_location("stage10l_synthetic", SOURCE)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stays(peer=False):
    rows = []
    for day in range(1, 15):
        utc = pd.Timestamp(f"2026-01-{day:02d}T14:00:00Z")
        rows.append({
            "user_id": "synthetic-10l",
            "arrival_time_utc": utc,
            "departure_time_utc": utc + pd.Timedelta(hours=2),
            "duration_s": 7200.0, "latitude": 39.90, "longitude": 116.40,
        })
        if peer and day <= 5:
            rows.append({
                "user_id": "synthetic-10l",
                "arrival_time_utc": utc + pd.Timedelta(hours=1),
                "departure_time_utc": utc + pd.Timedelta(hours=2),
                "duration_s": 3600.0, "latitude": 39.92, "longitude": 116.40,
            })
    return pd.DataFrame(rows)


def _inputs(m, stays):
    ten_j = m._load("stage10j_synth_10l", "10j_cutoff_sensitivity.py")
    ten_f = m._load("stage10f_synth_10l", "10f_train_only_forward_validation.py")
    ten_i = m._load("stage10i_synth_10l", "10i_future_spatial_observability.py")
    from geolife.model import HomeOfficeConfig
    from geolife.model import home_office as cp2

    j = ten_j.run_cutoffs(stays)
    _, outcomes, _ = ten_f.forward_validate(stays)
    train, future, _ = ten_f.partition_stays(stays, train_fraction=.7)
    emitted, members = ten_f.train_only_emissions(train, config=HomeOfficeConfig())
    aligned = ten_f.align_to_train_locations(
        cp2._resolve_stay_timezones(cp2._validate_stays(future)), members
    )
    assert len(emitted) == len(outcomes)
    spatial = ten_i.audit_future_windows(outcomes, aligned, HomeOfficeConfig())
    return outcomes, spatial, j


@pytest.mark.parametrize("peer", [False, True])
def test_end_to_end_recomputes_train_only_and_never_fills_missing_peer(peer):
    m = _load()
    stays = _stays(peer=peer)
    outcomes, spatial, j = _inputs(m, stays)
    scored = m.build_paired_private(stays, outcomes, spatial, j)
    assert len(scored) == 1
    row = scored.iloc[0]
    assert row["label"] == "HOME"
    assert row["future_unique_spatial_observable"]
    assert row["future_same_anchor_reappears_spatial"]
    assert 0 <= row["train_mask_stability_R"] <= 1
    assert row["train_mask_trial_count"] == 9
    if peer:
        assert row["train_eligible_location_count"] == 2
        assert row["evidence_v2_status"] == "ok"
        c = row["train_relative_peer_dominance"]
        o = row["train_observed_date_coverage"]
        h = row["train_support_factor"]
        r = row["train_mask_stability_R"]
        assert row["evidence_v2_train_only"] == pytest.approx(
            np.cbrt(c * o * r) * np.sqrt(h)
        )
    else:
        assert row["train_eligible_location_count"] == 1
        assert row["evidence_v2_status"] == "missing_or_invalid_runner_up"
        assert pd.isna(row["evidence_v2_train_only"])
        assert not row["fair_head_to_head_cohort"]


def test_mask_only_removes_train_dates_and_deterministic_for_same_seed():
    m = _load()
    train = _stays()
    rng_seed = m._seed("synthetic-10l", .3, 2)
    masked = m.mask_train_dates(train, rate=.3, seed=rng_seed)
    again = m.mask_train_dates(train, rate=.3, seed=rng_seed)
    pd.testing.assert_frame_equal(masked, again)
    assert len(masked) < len(train)
    assert set(masked["arrival_time_utc"]).issubset(
        set(train["arrival_time_utc"])
    )
    assert m._seed("synthetic-10l", .3, 2) != m._seed("synthetic-10l", .3, 1)


def test_score_ranking_on_exact_same_spatial_cohort_and_suppression():
    m = _load()
    rows = []
    for i in range(44):
        good = i < 22
        rows.append({
            "user_id": f"synthetic-{i}",
            "label": "HOME" if i % 2 else "OFFICE",
            "train_location_id": i,
            "train_peer_group": "multiple_eligible",
            "train_evidence_strength": .8 if good else .2,
            "evidence_v2_train_only": .7 if good else .3,
            "evidence_v2_status": "ok",
            "future_time_observable": True,
            "future_unique_spatial_observable": True,
            "future_same_anchor_reappears_spatial": good,
            "train_mask_stability_R": 1.,
        })
    output = m.summarize_head_to_head(pd.DataFrame(rows))
    overall = output["overall"]
    assert overall["fair_comparison"]["n"] == 44
    assert overall["fair_comparison"]["reappeared"] == 22
    assert overall["fair_comparison"]["pairwise_recurrence_concordance_v1"] == 1
    assert overall["fair_comparison"]["pairwise_recurrence_concordance_v2"] == 1
    assert output["ground_truth_semantic_accuracy"] is None
    assert "synthetic-" not in str(output)

    frame = pd.DataFrame(rows)
    frame.loc[:19, "future_unique_spatial_observable"] = False
    reduced = m.summarize_head_to_head(frame)
    assert reduced["overall"]["fair_comparison"]["n"] == 24
    assert reduced["overall"]["fair_comparison"]["pairwise_recurrence_concordance_v2"] is None


def test_stage10j_parity_missing_peer_and_future_states_fail_closed():
    m = _load()
    with pytest.raises(ValueError, match="Stage10j"):
        m._reference70({"experiment": "invalid"})
    with pytest.raises(ValueError, match="min_group"):
        m.summarize_head_to_head(pd.DataFrame(), min_group=1)
    frames = pd.DataFrame([{
        "user_id": "synthetic",
        "label": "HOME",
        "train_location_id": 0,
    }])
    with pytest.raises(ValueError, match="null/duplicate"):
        m._unique(pd.concat([frames, frames]), name="duplicate")
