from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys

import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07h_evidence_triangulation.py"
)


def _module():
    spec = spec_from_file_location("stage07h", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _work():
    return pd.DataFrame(
        [
            {
                "user_id": "u1",
                "window_pattern": "stable_secondary_anchor",
                "dominant_location_id": 7,
            },
            {
                "user_id": "u2",
                "window_pattern": "stable_secondary_anchor",
                "dominant_location_id": 8,
            },
        ]
    )


def _behavior():
    return pd.DataFrame(
        [
            {
                "user_id": "u1",
                "secondary_location_id": 7,
                "valid_evidence_axes": 4,
                "top1_evidence_axes": 3,
                "beats_peer_median_axes": 4,
            }
        ]
    )


def _osm():
    return pd.DataFrame(
        [
            {
                "user_id": "u1",
                "candidate_location_id": 7,
                "candidate_work_within_25m": True,
                "peer_share_work_within_25m": 0.0,
                "candidate_minus_peer_share_25m": 1.0,
                "candidate_work_within_50m": True,
                "peer_share_work_within_50m": 0.5,
                "candidate_minus_peer_share_50m": 0.5,
                "candidate_work_within_100m": True,
                "peer_share_work_within_100m": 0.5,
                "candidate_minus_peer_share_100m": 0.5,
            },
            {
                "user_id": "u2",
                "candidate_location_id": 8,
                "candidate_work_within_25m": False,
                "peer_share_work_within_25m": 0.5,
                "candidate_minus_peer_share_25m": -0.5,
                "candidate_work_within_50m": False,
                "peer_share_work_within_50m": 0.5,
                "candidate_minus_peer_share_50m": -0.5,
                "candidate_work_within_100m": False,
                "peer_share_work_within_100m": 0.5,
                "candidate_minus_peer_share_100m": -0.5,
            },
        ]
    )


def _bcl():
    return pd.DataFrame(
        [
            {
                "user_id": "u1",
                "candidate_location_id": 7,
                "candidate_work_lexical_within_25m": True,
                "peer_share_work_lexical_within_25m": 0.0,
                "candidate_minus_peer_share_25m": 1.0,
                "candidate_work_lexical_within_50m": True,
                "peer_share_work_lexical_within_50m": 0.0,
                "candidate_minus_peer_share_50m": 1.0,
                "candidate_work_lexical_within_100m": True,
                "peer_share_work_lexical_within_100m": 0.5,
                "candidate_minus_peer_share_100m": 0.5,
            },
            {
                "user_id": "u2",
                "candidate_location_id": 8,
                "candidate_work_lexical_within_25m": False,
                "peer_share_work_lexical_within_25m": 0.0,
                "candidate_minus_peer_share_25m": 0.0,
                "candidate_work_lexical_within_50m": False,
                "peer_share_work_lexical_within_50m": 0.0,
                "candidate_minus_peer_share_50m": 0.0,
                "candidate_work_lexical_within_100m": True,
                "peer_share_work_lexical_within_100m": 0.0,
                "candidate_minus_peer_share_100m": 1.0,
            },
        ]
    )


def test_user_panel_preserves_frozen_cohort_and_missing_behavior():
    module = _module()
    panel = module.build_user_evidence_panel(
        _work(), _behavior(), _osm(), _bcl()
    ).set_index("user_id")

    assert len(panel) == 2
    assert bool(panel.loc["u1", "behavior_available"])
    assert not bool(panel.loc["u2", "behavior_available"])

    assert bool(panel.loc["u1", "behavior_primary_support"])
    assert bool(panel.loc["u1", "behavior_directional_majority"])
    assert panel.loc["u1", "behavior_band"] == "strict"
    assert panel.loc["u2", "behavior_band"] == "unavailable"

    assert bool(panel.loc["u1", "external_both_positive_100m"])
    assert bool(panel.loc["u1", "strict_three_way_convergence_100m"])
    assert panel.loc["u2", "candidate_context_pattern_100m"] == "bcl_only"


def test_candidate_identity_mismatch_is_rejected():
    module = _module()
    osm = _osm()
    osm.loc[osm["user_id"].eq("u1"), "candidate_location_id"] = 999

    with pytest.raises(ValueError, match="candidate location identity mismatch"):
        module.build_user_evidence_panel(
            _work(), _behavior(), osm, _bcl()
        )


def test_external_direction_summary_keeps_signs_separate():
    module = _module()
    panel = module.build_user_evidence_panel(
        _work(), _behavior(), _osm(), _bcl()
    )
    summary = module.summarize_external_direction(panel).set_index(
        "threshold_m"
    )

    assert summary.loc[100.0, "users_with_both_sources"] == 2
    assert summary.loc[100.0, "both_positive"] == 1
    assert summary.loc[100.0, "opposite_positive_negative"] == 1
    assert summary.loc[25.0, "both_positive"] == 1


def test_context_overlap_is_candidate_specific():
    module = _module()
    panel = module.build_user_evidence_panel(
        _work(), _behavior(), _osm(), _bcl()
    )
    overlap = module.summarize_candidate_context_overlap(
        panel, threshold_m=100.0
    ).set_index("pattern")

    assert overlap.loc["both", "users"] == 1
    assert overlap.loc["bcl_only", "users"] == 1
    assert overlap.loc["osm_only", "users"] == 0
    assert overlap.loc["neither", "users"] == 0


def test_decision_snapshot_distinguishes_strict_and_directional():
    module = _module()
    panel = module.build_user_evidence_panel(
        _work(), _behavior(), _osm(), _bcl()
    )
    snapshot = module.decision_snapshot(panel).iloc[0]

    assert snapshot["stable_secondary_users"] == 2
    assert snapshot["behavior_available_users"] == 1
    assert snapshot["behavior_strict_support_users"] == 1
    assert snapshot["behavior_directional_majority_users"] == 1
    assert snapshot["external_both_positive_100m_users"] == 1
    assert snapshot["strict_three_way_convergence_100m_users"] == 1


def test_synthetic_self_check():
    module = _module()
    result = module.synthetic_self_check()
    assert result["status"] == "ok"
    assert result["users"] == 1


def test_stage07h_notebook_contract():
    path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07h_evidence_triangulation.ipynb"
    )
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    required = [
        "GEOLIFE_REPO_BRANCH",
        "05c_stable_secondary_evidence",
        "07e_semantic_distance_alignment",
        "07g_bcl_poi_2008_alignment",
        "build_user_evidence_panel",
        "summarize_external_direction",
        "summarize_candidate_context_overlap",
        "stable_secondary_triangulation_private.pkl",
        "decision_snapshot.csv",
    ]
    for snippet in required:
        assert snippet in code

    assert "WORK/OFFICE score" not in code
