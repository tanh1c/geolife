from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07n_trackintel_end_to_end.py"
)


def _module():
    spec = spec_from_file_location("stage07n", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_canonical_user_id():
    stage = _module()
    assert stage.canonical_user_id(0) == "000"
    assert stage.canonical_user_id("7") == "007"
    assert stage.canonical_user_id("181") == "181"
    assert stage.canonical_user_id("abc") == "abc"


def test_compare_stay_inventories_strong_overlap():
    stage = _module()
    cp1 = pd.DataFrame(
        {
            "user_id": ["001", "001"],
            "arrival_time_utc": [
                pd.Timestamp("2026-01-01T00:00:00Z"),
                pd.Timestamp("2026-01-01T02:00:00Z"),
            ],
            "departure_time_utc": [
                pd.Timestamp("2026-01-01T01:00:00Z"),
                pd.Timestamp("2026-01-01T03:00:00Z"),
            ],
            "latitude": [39.9, 39.91],
            "longitude": [116.4, 116.41],
        }
    )
    ti = pd.DataFrame(
        {
            "user_id": [1, 1],
            "started_at": [
                pd.Timestamp("2026-01-01T00:10:00Z"),
                pd.Timestamp("2026-01-01T02:10:00Z"),
            ],
            "finished_at": [
                pd.Timestamp("2026-01-01T00:50:00Z"),
                pd.Timestamp("2026-01-01T02:50:00Z"),
            ],
            "latitude": [39.9001, 39.9101],
            "longitude": [116.4001, 116.4101],
        }
    )

    details, summary = stage.compare_stay_inventories(cp1, ti)

    assert len(details) == 4
    assert int(summary["strong_match_50pct_and_200m"].sum()) == 4
    assert np.isclose(summary["strong_match_rate"].min(), 1.0)


def test_nearest_location_matches_and_summary():
    stage = _module()
    production = pd.DataFrame(
        {
            "user_id": ["001", "001"],
            "location_id": [0, 1],
            "latitude": [39.9, 39.95],
            "longitude": [116.4, 116.45],
            "stay_count": [3, 1],
        }
    )
    trackintel = pd.DataFrame(
        {
            "user_id": ["001", "001"],
            "location_id": [10, 11],
            "latitude": [39.9001, 40.5],
            "longitude": [116.4001, 117.0],
            "stay_count": [5, 2],
            "variant": ["e100", "e100"],
        }
    )

    matches = stage.nearest_location_matches(production, trackintel)
    summary = stage.summarize_location_geometry(matches)

    first = matches.loc[matches["production_location_id"].eq(0)].iloc[0]
    assert first["distance_m"] < 50
    recurring = summary.loc[
        summary["scope"].eq("recurring_production_locations")
    ].iloc[0]
    assert int(recurring["within_50m"]) == 1


def test_compare_semantic_candidates_distance_buckets():
    stage = _module()
    production = pd.DataFrame(
        {
            "user_id": ["001", "001"],
            "label": ["HOME", "OFFICE"],
            "location_id": [0, 1],
            "latitude": [39.9, 39.95],
            "longitude": [116.4, 116.45],
        }
    )
    comparator = pd.DataFrame(
        {
            "variant": ["e100", "e100"],
            "user_id": ["001", "002"],
            "label": ["HOME", "OFFICE"],
            "location_id": [10, 20],
            "latitude": [39.9001, 40.0],
            "longitude": [116.4001, 116.5],
        }
    )

    comparison = stage.compare_semantic_candidates(
        ["001", "002"], production, comparator, "e100"
    )

    home = comparison.loc[
        comparison["user_id"].eq("001") & comparison["label"].eq("HOME")
    ].iloc[0]
    office = comparison.loc[
        comparison["user_id"].eq("001") & comparison["label"].eq("OFFICE")
    ].iloc[0]
    assert home["status"] == "within_50m"
    assert office["status"] == "production_only"


def test_synthetic_self_check():
    stage = _module()
    result = stage.synthetic_self_check()
    assert result["status"] == "ok"


def test_notebook_contract():
    import json

    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07n_trackintel_end_to_end.ipynb"
    )
    notebook = json.loads(notebook_path.read_text())
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
    )

    required = [
        "TRACKINTEL_VERSION='1.4.2'",
        "/mnt/geolife-data",
        "read_geolife",
        "dist_threshold=200",
        "time_threshold=20",
        "gap_threshold=5",
        "epsilon=100",
        "epsilon=200",
        "method='OSNA'",
        "pre_filter=False",
        "24876978",
        "18670",
        "5821",
        "HOME",
        "OFFICE",
        "07n_trackintel_end_to_end",
    ]
    for token in required:
        assert token in source


def test_notebook_bootstrap_installs_before_third_party_imports():
    import json

    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07n_trackintel_end_to_end.ipynb"
    )
    notebook = json.loads(notebook_path.read_text())
    bootstrap = "".join(notebook["cells"][1]["source"])

    repo_install = bootstrap.index("pip','install','-q','-e','.[dev]'")
    trackintel_install = bootstrap.index("trackintel=={TRACKINTEL_VERSION}")
    geopandas_import = bootstrap.index("import geopandas as gpd")
    pandas_import = bootstrap.index("import pandas as pd")
    numpy_import = bootstrap.index("import numpy as np")

    assert repo_install < geopandas_import
    assert trackintel_install < geopandas_import
    assert repo_install < pandas_import
    assert repo_install < numpy_import
    assert "geopandas_missing=importlib.util.find_spec('geopandas') is None" in bootstrap
