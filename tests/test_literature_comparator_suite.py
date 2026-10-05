from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07o_literature_comparator_suite.py"
)


def _module():
    spec = spec_from_file_location("stage07o", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_scikit_home_replica_uses_night_visits_and_fallback():
    stage = _module()
    obs = pd.DataFrame(
        {
            "user_id": ["a", "a", "a", "b", "b"],
            "location_id": [1, 1, 2, 3, 4],
            "datetime": [
                pd.Timestamp("2026-01-01 23:00"),
                pd.Timestamp("2026-01-02 23:00"),
                pd.Timestamp("2026-01-03 12:00"),
                pd.Timestamp("2026-01-01 12:00"),
                pd.Timestamp("2026-01-02 13:00"),
            ],
            "latitude": [1.0, 1.0, 2.0, 3.0, 4.0],
            "longitude": [1.0, 1.0, 2.0, 3.0, 4.0],
        }
    )

    out = stage.scikit_mobility_home_replica(obs)

    a = out.loc[out["user_id"].eq("a")].iloc[0]
    b = out.loc[out["user_id"].eq("b")].iloc[0]
    assert int(a["location_id"]) == 1
    assert not bool(a["used_fallback_all_visits"])
    assert bool(b["used_fallback_all_visits"])


def test_geohash_round_trip_center_is_close():
    stage = _module()
    code = stage.geohash_encode(39.9042, 116.4074, 7)
    lat, lon = stage.geohash_center(code)
    assert abs(lat - 39.9042) < 0.01
    assert abs(lon - 116.4074) < 0.01


def test_geohash_monthly_home_selects_supported_night_cell():
    stage = _module()
    rows = []
    for day in range(1, 5):
        for hour in [21, 22, 23]:
            rows.append(
                {
                    "user_id": "u",
                    "location_id": 1,
                    "datetime": pd.Timestamp(2026, 1, day, hour),
                    "local_date": pd.Timestamp(2026, 1, day).date(),
                    "year_month": "2026-01",
                    "hour": hour,
                    "latitude": 39.9042,
                    "longitude": 116.4074,
                }
            )
    for day in [1, 2]:
        for hour in [10, 11]:
            rows.append(
                {
                    "user_id": "u",
                    "location_id": 2,
                    "datetime": pd.Timestamp(2026, 1, day, hour),
                    "local_date": pd.Timestamp(2026, 1, day).date(),
                    "year_month": "2026-01",
                    "hour": hour,
                    "latitude": 39.95,
                    "longitude": 116.45,
                }
            )

    monthly, audit = stage.geohash2302_monthly_home(pd.DataFrame(rows))
    user_home = stage.aggregate_geohash2302_home(monthly)

    assert len(audit) == 1
    assert len(monthly) == 1
    assert len(user_home) == 1
    assert user_home.iloc[0]["label"] == "HOME"


def test_pavan_feature_space_preserves_three_dimensions_without_score():
    stage = _module()
    locations = pd.DataFrame(
        {
            "user_id": ["u", "u", "u"],
            "location_id": [0, 1, 2],
            "diameter_m": [100.0, 80.0, 50.0],
            "total_dwell_h": [20.0, 10.0, 2.0],
            "stay_count": [5, 4, 1],
            "active_local_dates": [4, 3, 1],
        }
    )
    prod = pd.DataFrame(
        {
            "user_id": ["u"],
            "label": ["HOME"],
            "location_id": [0],
        }
    )

    frame, summary, rank_summary = stage.pavan_feature_space(locations, prod)

    assert set(["area_proxy_m2", "intensity_dwell_h", "frequency_visits"]).issubset(frame)
    assert "importance_score" not in frame.columns
    assert len(frame) == 2
    assert int(rank_summary.iloc[0]["top1_intensity"]) == 1
    assert int(rank_summary.iloc[0]["top1_frequency"]) == 1
    assert "HOME" in set(summary["production_role"])


def test_scitepress_style_uses_top_two_and_time_windows():
    stage = _module()
    tz = "Asia/Shanghai"
    semantic = pd.DataFrame(
        {
            "user_id": ["u", "u", "u", "u"],
            "location_id": [0, 0, 1, 1],
            "arrival_time_local": [
                pd.Timestamp("2026-01-01 00:00", tz=tz),
                pd.Timestamp("2026-01-02 00:00", tz=tz),
                pd.Timestamp("2026-01-01 09:00", tz=tz),
                pd.Timestamp("2026-01-02 09:00", tz=tz),
            ],
            "departure_time_local": [
                pd.Timestamp("2026-01-01 05:00", tz=tz),
                pd.Timestamp("2026-01-02 05:00", tz=tz),
                pd.Timestamp("2026-01-01 17:00", tz=tz),
                pd.Timestamp("2026-01-02 17:00", tz=tz),
            ],
            "duration_s": [18000.0, 18000.0, 28800.0, 28800.0],
        }
    )
    locations = pd.DataFrame(
        {
            "user_id": ["u", "u"],
            "location_id": [0, 1],
            "latitude": [39.9, 39.91],
            "longitude": [116.4, 116.41],
            "stay_count": [2, 2],
        }
    )

    out = stage.scitepress_style_candidates(semantic, locations)
    home = out.loc[out["label"].eq("HOME")].iloc[0]
    work = out.loc[out["label"].eq("OFFICE")].iloc[0]

    assert int(home["location_id"]) == 0
    assert int(work["location_id"]) == 1
    assert not bool(home["same_home_work_candidate"])


def test_synthetic_self_check():
    stage = _module()
    assert stage.synthetic_self_check()["status"] == "ok"


def test_notebook_contract():
    import json

    notebook_path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07o_literature_comparator_suite.ipynb"
    )
    notebook = json.loads(notebook_path.read_text())
    source = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
    )

    required = [
        "/mnt/geolife-data",
        "stays_baseline_v1.pkl",
        "assert len(stays)==5821",
        "HOME",
        "OFFICE",
        "SCIKIT_MOBILITY_1_3_1_HOME",
        "ARXIV2302_GEOHASH_STAY_HOUR",
        "SCITEPRESS_WORK_REST_STYLE",
        "PAVAN",
        "22:00",
        "07:00",
        "21:00",
        "06:00",
        "00:00",
        "08:00",
        "18:00",
        "07o_literature_comparator_suite",
    ]
    for token in required:
        assert token in source
