from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07m_trackintel_semantic_parity.py"
)


def _module():
    spec = spec_from_file_location("stage07m", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_local_wall_adapter_preserves_clock_and_elapsed_duration():
    stage = _module()
    semantic = pd.DataFrame(
        {
            "user_id": ["u1", "u2"],
            "location_id": [0, 0],
            "latitude": [39.9, 40.7],
            "longitude": [116.4, -74.0],
            "duration_s": [3600.0, 5400.0],
            "arrival_time_local": [
                pd.Timestamp("2026-01-05 09:30", tz="Asia/Shanghai"),
                pd.Timestamp("2026-01-05 21:15", tz="America/New_York"),
            ],
            "departure_time_local": [
                pd.Timestamp("2026-01-05 10:30", tz="Asia/Shanghai"),
                pd.Timestamp("2026-01-05 22:45", tz="America/New_York"),
            ],
        }
    )

    adapted = stage.build_trackintel_adapter(semantic)

    assert list(adapted["started_at"].dt.hour) == [9, 21]
    assert list(adapted["started_at"].dt.minute) == [30, 15]
    assert list(
        (adapted["finished_at"] - adapted["started_at"]).dt.total_seconds()
    ) == [3600.0, 5400.0]
    assert adapted["finish_wall_delta_s"].eq(0).all()


def test_extract_trackintel_candidates_deduplicates_stay_rows():
    stage = _module()
    labeled = pd.DataFrame(
        {
            "user_id": ["u", "u", "u"],
            "location_id": [4, 4, 7],
            "purpose": ["home", "home", "work"],
        }
    )

    out = stage.extract_trackintel_candidates(labeled, "OSNA")

    assert len(out) == 2
    assert set(out["label"]) == {"HOME", "OFFICE"}
    assert dict(zip(out["label"], out["location_id"])) == {"HOME": 4, "OFFICE": 7}


def test_candidate_comparison_states_and_summary():
    stage = _module()
    production = pd.DataFrame(
        {
            "user_id": ["u1", "u1", "u2"],
            "label": ["HOME", "OFFICE", "HOME"],
            "location_id": [1, 2, 3],
        }
    )
    comparator = pd.DataFrame(
        {
            "method": ["FREQ", "FREQ", "FREQ", "FREQ"],
            "user_id": ["u1", "u1", "u2", "u2"],
            "label": ["HOME", "OFFICE", "HOME", "OFFICE"],
            "location_id": [1, 9, 8, 5],
        }
    )

    comparison = stage.build_candidate_comparison(
        ["u1", "u2"], production, comparator
    )
    statuses = {
        (row.user_id, row.label): row.status
        for row in comparison.itertuples(index=False)
    }

    assert statuses[("u1", "HOME")] == "both_same"
    assert statuses[("u1", "OFFICE")] == "both_different"
    assert statuses[("u2", "HOME")] == "both_different"
    assert statuses[("u2", "OFFICE")] == "comparator_only"

    summary = stage.summarize_agreement(comparison)
    home = summary.loc[summary["label"].eq("HOME")].iloc[0]
    assert int(home["production_emitted_users"]) == 2
    assert int(home["exact_location_match_users"]) == 1


def test_near_miss_work_summary_matches_candidate_identity():
    stage = _module()
    panel = pd.DataFrame(
        {
            "user_id": ["b", "m", "s"],
            "audit_group": ["baseline", "margin_near", "share_near"],
            "candidate_location_id": [1, 2, 3],
        }
    )
    comparator = pd.DataFrame(
        {
            "method": ["FREQ", "FREQ", "OSNA", "OSNA"],
            "user_id": ["m", "s", "m", "s"],
            "label": ["OFFICE", "OFFICE", "OFFICE", "OFFICE"],
            "location_id": [2, 8, 7, 3],
        }
    )

    private_rows, summary = stage.summarize_near_miss_work(panel, comparator)

    assert len(private_rows) == 4
    assert int(private_rows["exact_near_miss_candidate_match"].sum()) == 2
    assert set(summary["audit_group"]) == {"margin_near", "share_near"}


def test_synthetic_self_check():
    stage = _module()
    result = stage.synthetic_self_check()
    assert result["status"] == "ok"
