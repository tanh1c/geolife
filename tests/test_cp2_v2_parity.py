from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


MODULE_PATH = Path(__file__).resolve().parents[1] / "analysis" / "03_cp2_v2_parity.py"
SPEC = importlib.util.spec_from_file_location("cp2_v2_parity", MODULE_PATH)
assert SPEC is not None and SPEC.loader is not None
parity = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(parity)


def _semantic_stays(location_ids: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": ["u", "u", "u"],
            "arrival_time_utc": pd.to_datetime(
                [
                    "2026-01-01T12:00:00Z",
                    "2026-01-02T12:00:00Z",
                    "2026-01-03T12:00:00Z",
                ],
                utc=True,
            ),
            "departure_time_utc": pd.to_datetime(
                [
                    "2026-01-01T13:00:00Z",
                    "2026-01-02T13:00:00Z",
                    "2026-01-03T13:00:00Z",
                ],
                utc=True,
            ),
            "duration_s": [3600.0, 3600.0, 3600.0],
            "latitude": [39.9, 39.9, 40.0],
            "longitude": [116.4, 116.4, 116.5],
            "timezone_id": ["Asia/Shanghai"] * 3,
            "arrival_time_local": pd.to_datetime(
                [
                    "2026-01-01 20:00:00",
                    "2026-01-02 20:00:00",
                    "2026-01-03 20:00:00",
                ]
            ),
            "departure_time_local": pd.to_datetime(
                [
                    "2026-01-01 21:00:00",
                    "2026-01-02 21:00:00",
                    "2026-01-03 21:00:00",
                ]
            ),
            "location_id": location_ids,
        }
    )


def _locations(location_ids: list[int]) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "user_id": ["u", "u"],
            "location_id": location_ids,
            "latitude": [39.9, 40.0],
            "longitude": [116.4, 116.5],
            "stay_count": [2, 1],
            "active_local_dates": [2, 1],
            "total_dwell_h": [2.0, 1.0],
            "diameter_m": [0.0, 0.0],
        }
    )


def test_parity_uses_cluster_membership_not_raw_location_ids() -> None:
    production_stays = _semantic_stays([0, 0, 1])
    reference_stays = _semantic_stays([7, 7, 3])
    production_locations = _locations([0, 1])
    reference_locations = _locations([7, 3])
    production_labels = pd.DataFrame(
        [{"user_id": "u", "label": "HOME", "location_id": 0}]
    )
    reference_labels = pd.DataFrame(
        [{"user_id": "u", "label": "HOME", "location_id": 7}]
    )

    result = parity.compare_reference(
        production_stays,
        production_locations,
        production_labels,
        reference_stays,
        reference_locations,
        reference_labels,
    )

    assert result["location_membership_exact_match"] is True
    assert result["label_semantic_exact_match"] is True
    assert result["all_parity_checks_pass"] is True
