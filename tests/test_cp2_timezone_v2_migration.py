from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "03d_cp2_timezone_v2_migration.py"
)


def _module():
    spec = spec_from_file_location("stage03d", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _stays():
    rows = []
    for day in ["2026-01-05", "2026-01-06", "2026-01-07"]:
        rows.append(
            {
                "user_id": "u",
                "arrival_time_utc": pd.Timestamp(f"{day}T13:00:00Z"),
                "departure_time_utc": pd.Timestamp(f"{day}T14:00:00Z"),
                "duration_s": 3600.0,
                "latitude": 39.9042,
                "longitude": 116.4074,
            }
        )
    return pd.DataFrame(rows)


def test_reference_timezone_resolution_matches_notebook_contract():
    module = _module()
    out = module.reference_resolve_timezones(_stays())

    assert len(out) == 3
    assert set(out["timezone_id"]) == {"Asia/Shanghai"}
    assert out.iloc[0]["arrival_time_local"] == pd.Timestamp(
        "2026-01-05 21:00:00"
    )
    assert out.iloc[0]["arrival_time_local"].tzinfo is None


def test_reference_complete_link_and_emission():
    module = _module()
    labels, semantic, locations = module.reference_infer_home_office(
        _stays()
    )

    assert len(semantic) == 3
    assert len(locations) == 1
    assert set(labels["label"]) == {"HOME"}
    assert labels.iloc[0]["relevant_dates"] == 3


def test_compare_migration_accepts_exact_reference_parity():
    module = _module()
    labels, semantic, locations = module.reference_infer_home_office(
        _stays()
    )

    # The migration decision normally requires the frozen 5,821 stay count.
    # Pad only the count check here while reusing exact reference outputs.
    padded = pd.concat(
        [_stays()] * 1941,
        ignore_index=True,
    ).iloc[:5821].copy()

    summary, decision = module.compare_migration(
        stays=padded,
        production_labels=labels.copy(),
        production_semantic=semantic.copy(),
        production_locations=locations.copy(),
        reference_labels=labels.copy(),
        reference_semantic=semantic.copy(),
        reference_locations=locations.copy(),
    )

    assert summary.iloc[0]["emission_keys_exact"]
    assert summary.iloc[0]["evidence_exact"]
    assert decision.cp1_stay_count_status == "pass_5821_frozen_cp1"
    assert decision.runner_status == "ready_to_refreeze_cp2_v2"
