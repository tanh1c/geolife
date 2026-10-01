from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "06b_routine_representation_robustness.py"
)


def _module():
    spec = spec_from_file_location("stage06b", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_synthetic_self_check() -> None:
    result = _module().synthetic_self_check()
    assert result["status"] == "ok"
    assert result["stable_jsd"] < 0.2
    assert result["shifted_jsd"] > 0.9
    assert result["shift_detected_beyond_random_p95"]


def test_one_day_motif_is_not_repeatable_under_primary_support() -> None:
    module = _module()

    days = pd.DataFrame(
        [
            {
                "user_id": "one_day",
                "local_date": pd.Timestamp("2026-01-01").date(),
                "motif": "L0→L1",
            },
            *[
                {
                    "user_id": "supported",
                    "local_date": (
                        pd.Timestamp("2026-01-01") + pd.Timedelta(days=index)
                    ).date(),
                    "motif": "L0→L1",
                }
                for index in range(6)
            ],
        ]
    )
    edges = pd.DataFrame(
        [
            {"user_id": "one_day", "active_days": 1},
            {"user_id": "supported", "active_days": 4},
        ]
    )

    result = module.supported_motif_comparator(days, edges).iloc[0]

    assert result["eligible_users"] == 1
    assert result["users_with_supported_collapsed_motif"] == 1
    assert result["users_with_repeated_od"] == 1


def test_distribution_metrics_detect_rank_swap_without_large_shift() -> None:
    module = _module()

    metrics = module.distribution_metrics(
        {(0, 1): 40, (0, 2): 38},
        {(0, 1): 38, (0, 2): 40},
    )

    assert metrics["comparable"]
    assert not metrics["top1_same"]
    assert metrics["jsd"] < 0.01
    assert metrics["weighted_jaccard"] > 0.9
