from __future__ import annotations

import importlib.util
from pathlib import Path
import sys

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
MODULES = [
    ROOT / "analysis" / "05_home_office_reliability.py",
    ROOT / "analysis" / "05b_home_consensus_adaptive_work.py",
    ROOT / "analysis" / "05c_stable_secondary_independent_evidence.py",
]


@pytest.mark.parametrize("module_path", MODULES)
def test_downstream_helpers_accept_mixed_per_stay_timezones(module_path: Path) -> None:
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    values = pd.Series(
        [
            pd.Timestamp("2026-01-01T20:00:00+08:00"),
            pd.Timestamp("2026-01-01T21:00:00+09:00"),
        ],
        dtype="object",
    )
    result = module._local_wall_series(values)

    assert str(result.dtype) == "datetime64[ns]"
    assert result.iloc[0] == pd.Timestamp("2026-01-01 20:00:00")
    assert result.iloc[1] == pd.Timestamp("2026-01-01 21:00:00")


def test_stage05_time_shift_preserves_per_row_timezone() -> None:
    module_path = ROOT / "analysis" / "05_home_office_reliability.py"
    spec = importlib.util.spec_from_file_location("stage05_shift", module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)

    values = pd.Series(
        [
            pd.Timestamp("2026-01-01T20:00:00+08:00"),
            pd.Timestamp("2026-01-01T21:00:00+09:00"),
        ],
        dtype="object",
    )
    shifted = module._shift_local_series(values, pd.Timedelta(hours=12))

    assert shifted.iloc[0].utcoffset() == values.iloc[0].utcoffset()
    assert shifted.iloc[1].utcoffset() == values.iloc[1].utcoffset()
    assert shifted.iloc[0].hour == 8
    assert shifted.iloc[1].hour == 9
