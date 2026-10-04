from __future__ import annotations

import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
RERUN_NOTEBOOKS = [
    "05_home_office_reliability_validation.ipynb",
    "05b_home_consensus_adaptive_work.ipynb",
    "05c_stable_secondary_independent_evidence.ipynb",
    "07b_factorized_work_profiles.ipynb",
    "07c_historical_source_alignment.ipynb",
    "07d_historical_context_enrichment.ipynb",
    "07e_semantic_distance_alignment.ipynb",
]


def _code(path: Path) -> tuple[str, str]:
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code_cells = [
        "".join(cell.get("source", []))
        if isinstance(cell.get("source", []), list)
        else str(cell.get("source", ""))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    ]
    assert code_cells
    return code_cells[0], "\n".join(code_cells)


@pytest.mark.parametrize("filename", RERUN_NOTEBOOKS)
def test_cp2_v2_rerun_notebooks_refresh_runtime_before_analysis(filename: str) -> None:
    first_code, all_code = _code(ROOT / "notebooks" / filename)

    assert "pip" in first_code
    assert "-e" in first_code
    assert "except ModuleNotFoundError" not in all_code
    assert "eda/07" not in first_code

    geolife_import = all_code.find("from geolife.model")
    if geolife_import >= 0:
        install = all_code.find("pip")
        assert install >= 0
        assert install < geolife_import


@pytest.mark.parametrize(
    "filename",
    [
        "05_home_office_reliability_validation.ipynb",
        "05b_home_consensus_adaptive_work.ipynb",
        "05c_stable_secondary_independent_evidence.ipynb",
    ],
)
def test_cp2_v2_semantic_notebooks_preflight_timezonefinder(filename: str) -> None:
    _, all_code = _code(ROOT / "notebooks" / filename)

    assert "from timezonefinder import TimezoneFinder" in all_code
    assert "tz_localize(None)" not in all_code


def test_stage07e_bootstraps_pandas_and_analysis_helper() -> None:
    first_code, all_code = _code(
        ROOT / "notebooks" / "07e_semantic_distance_alignment.ipynb"
    )

    assert "import pandas as pd" in first_code
    assert "spec_from_file_location('s07e'" in first_code
    assert "spec.loader.exec_module(s07e)" in first_code

    first_pd_use = all_code.find("pd.read_pickle")
    first_s07e_use = all_code.find("s07e.STAGE07D")
    pd_import = all_code.find("import pandas as pd")
    helper_load = all_code.find("spec.loader.exec_module(s07e)")

    assert pd_import >= 0
    assert helper_load >= 0
    assert first_pd_use > pd_import
    assert first_s07e_use > helper_load
