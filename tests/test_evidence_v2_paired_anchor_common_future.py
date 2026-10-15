"""Synthetic-only tests for Stage10k; no private GeoLife stays or user IDs."""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd
import pytest


SOURCE = Path(__file__).resolve().parents[1] / "analysis" / "10k_paired_anchor_common_future_audit.py"


def _module():
    spec = spec_from_file_location("stage10k_paired", SOURCE)
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _frame(coords):
    return pd.DataFrame(coords, columns=["latitude", "longitude"])


def _stays():
    rows = []
    for day in range(1, 11):
        utc = pd.Timestamp(f"2026-01-{day:02d}T14:30:00Z")
        rows.append({
            "user_id": "synthetic-only",
            "arrival_time_utc": utc,
            "departure_time_utc": utc + pd.Timedelta(hours=2),
            "duration_s": 7200.0, "latitude": 39.9, "longitude": 116.4,
        })
    return pd.DataFrame(rows)


def test_cross_cutoff_ids_not_used_to_decide_identity():
    m = _module()
    old = _frame([(39.9, 116.4), (39.9001, 116.4)])
    same = _frame([(39.9001, 116.4)])
    far = _frame([(39.92, 116.4)])
    partial = _frame([(39.90185, 116.4)])  # ~206m from first, ~195m from second
    assert m.anchor_geometry(old, same, threshold_m=200) == "strict_compatible"
    assert m.anchor_geometry(old, far, threshold_m=200) == "fully_separated"
    assert m.anchor_geometry(old, partial, threshold_m=200) == "partial_overlap_uncertain"


def test_future_multiset_nested_and_rejects_missing():
    m = _module()
    f = _stays()
    m.assert_nested_future(f, f.iloc[7:])
    with pytest.raises(ValueError, match="not nested"):
        m.assert_nested_future(f.iloc[:7], f)


def test_transition_counts_and_paired_discordance():
    m = _module()
    def row(label, geometry, e, l, **extra):
        return {
            "user_id": f"user-{label}-{e}", "label": label,
            "emission_transition": "both_emitted",
            "geometry": geometry, "early_state": e, "late_state": l,
            "early_unique": e == "same_anchor",
            "late_unique": l == "same_anchor",
            "early_unresolved_detail": None,
            "late_unresolved_detail": None, **extra,
        }
    rows = [
        row("HOME", "strict_compatible", "same_anchor", "same_anchor"),
        row("OFFICE", "strict_compatible", "same_anchor", "spatial_unresolved"),
        row("HOME", "partial_overlap_uncertain", "same_anchor", "other_train_anchor"),
    ]
    report = m._aggregate_pair(rows, first=.6, second=.7, shared_stays=3)
    assert report["both_emitted_geometry"]["strict_compatible"] == 2
    assert report["strict_compatible_recurrence_on_common_time"]["paired_n"] == 2
    assert report["strict_compatible_recurrence_on_common_time"]["early_only"] == 1
    assert report["strict_compatible_recurrence_on_both_spatial"]["paired_n"] == 1


def test_stage10j_guard_fails_on_mutated_reference():
    m = _module()
    with pytest.raises(ValueError, match="Stage10j"):
        m._reference_rows({"experiment": "other"})
    expected = {
        "train_fraction": .7, "train_users_with_stays": 114,
        "future_stays": 10, "users_with_cutoff_crossing_stays": 0,
        "overall": {"train_emitted": 1}, "labels": [],
    }
    m._assert_reference(dict(expected), expected, .7)
    altered = dict(expected, future_stays=11)
    with pytest.raises(ValueError, match="parity"):
        m._assert_reference(altered, expected, .7)


def test_synthetic_end_to_end_using_stage10j():
    m = _module()
    stage_j = m._load("stage10j_for_test", "10j_cutoff_sensitivity.py")
    stays = _stays()
    j = stage_j.run_cutoffs(stays)
    report, private = m.run_paired_audit(stays, j)
    assert report["stage10j_aggregate_parity"] is True
    assert report["semantic_home_office_accuracy"] is None
    assert len(report["pairs"]) == 3
    for pair in report["pairs"]:
        assert pair["emission_transition"]["both_emitted"] == 1
        assert pair["both_emitted_geometry"]["strict_compatible"] == 1
        assert pair["strict_compatible_recurrence_on_common_time"]["both_reappear"] == 1
    assert len(private) == 3
    assert "synthetic-only" not in str(report)
