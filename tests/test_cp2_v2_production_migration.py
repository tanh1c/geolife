from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "03d_cp2_v2_production_migration.py"
)


def _module():
    spec = spec_from_file_location("stage03d", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _mixed_timezone_stays() -> pd.DataFrame:
    shanghai = pd.Timestamp(
        "2026-01-05 21:00",
        tz="Asia/Shanghai",
    ).tz_convert("UTC")
    tokyo = pd.Timestamp(
        "2026-01-06 21:00",
        tz="Asia/Tokyo",
    ).tz_convert("UTC")
    return pd.DataFrame(
        [
            {
                "user_id": "u",
                "arrival_time_utc": shanghai,
                "departure_time_utc": shanghai + pd.Timedelta(hours=1),
                "duration_s": 3600.0,
                "latitude": 39.9042,
                "longitude": 116.4074,
            },
            {
                "user_id": "u",
                "arrival_time_utc": tokyo,
                "departure_time_utc": tokyo + pd.Timedelta(hours=1),
                "duration_s": 3600.0,
                "latitude": 35.6762,
                "longitude": 139.6503,
            },
        ]
    )


def test_reference_timezone_contract_matches_audited_notebook():
    module = _module()
    resolved = module.reference_resolve_timezones(_mixed_timezone_stays())

    assert set(resolved["timezone_id"]) == {
        "Asia/Shanghai",
        "Asia/Tokyo",
    }
    assert resolved["arrival_time_local"].dt.hour.tolist() == [21, 21]


def test_small_sample_production_reference_parity_passes_semantic_axes():
    module = _module()
    result = module.run_migration_comparison(_mixed_timezone_stays())

    decision = result["decision"]
    assert decision["cp1_input_status"] == "blocked_cp1_input"
    assert decision["timezone_resolution_status"] == "pass_all_stays_resolved"
    assert decision["local_time_parity_status"] == "pass_exact_local_time_parity"
    assert decision["cluster_parity_status"] == "pass_cluster_signature_parity"
    assert decision["emission_parity_status"] == "pass_emission_evidence_parity"
    assert decision["runner_status"] == "blocked"


def test_location_namespace_is_explicitly_v2():
    module = _module()
    assert (
        module.LOCATION_NAMESPACE
        == "production_complete_link_200m_local_timezone_v2"
    )


def test_historical_v1_is_comparator_not_parity_target():
    module = _module()
    result = module.run_migration_comparison(_mixed_timezone_stays())

    assert result["historical_v1"] == {
        "semantic_users": 97,
        "semantic_locations": 1111,
        "recurring_locations": 486,
        "recurring_users": 73,
        "HOME": 27,
        "OFFICE": 16,
    }
    assert result["emission_parity"]["production_counts"] == {
        "HOME": 0,
        "OFFICE": 0,
    }


def test_synthetic_self_check():
    module = _module()
    check = module.synthetic_self_check()
    assert check["status"] == "ok"
    assert check["location_namespace"].endswith("_v2")
