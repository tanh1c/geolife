from __future__ import annotations

import math
import warnings

import pandas as pd
import pytest

from geolife.model.home_office import (
    HomeOfficeConfig,
    build_semantic_locations,
    infer_home_office,
)


BEIJING_LAT = 39.9042
BEIJING_LON = 116.4074


def _utc(local_timestamp: str) -> pd.Timestamp:
    return _utc_in_zone(local_timestamp, "Asia/Shanghai")


def _utc_in_zone(local_timestamp: str, timezone_id: str) -> pd.Timestamp:
    return pd.Timestamp(local_timestamp, tz=timezone_id).tz_convert("UTC")


def _stays(
    rows: list[tuple[str, str, str, float, float]],
) -> pd.DataFrame:
    frame = pd.DataFrame(
        rows,
        columns=[
            "user_id",
            "arrival_local",
            "departure_local",
            "latitude",
            "longitude",
        ],
    )
    frame["arrival_time_utc"] = frame["arrival_local"].map(_utc)
    frame["departure_time_utc"] = frame["departure_local"].map(_utc)
    frame["duration_s"] = (
        frame["departure_time_utc"] - frame["arrival_time_utc"]
    ).dt.total_seconds()
    return frame[
        [
            "user_id",
            "arrival_time_utc",
            "departure_time_utc",
            "duration_s",
            "latitude",
            "longitude",
        ]
    ]


def test_all_resolved_stays_are_retained_without_beijing_geography_gate() -> None:
    frame = pd.DataFrame(
        [
            {
                "user_id": "traveler",
                "arrival_time_utc": _utc_in_zone(
                    "2026-01-05 21:00",
                    "Asia/Shanghai",
                ),
                "departure_time_utc": _utc_in_zone(
                    "2026-01-05 22:00",
                    "Asia/Shanghai",
                ),
                "latitude": BEIJING_LAT,
                "longitude": BEIJING_LON,
            },
            {
                "user_id": "traveler",
                "arrival_time_utc": _utc_in_zone(
                    "2026-01-06 21:00",
                    "Asia/Tokyo",
                ),
                "departure_time_utc": _utc_in_zone(
                    "2026-01-06 22:00",
                    "Asia/Tokyo",
                ),
                "latitude": 35.6762,
                "longitude": 139.6503,
            },
        ]
    )
    frame["duration_s"] = (
        frame["departure_time_utc"] - frame["arrival_time_utc"]
    ).dt.total_seconds()

    semantic_stays, _ = build_semantic_locations(frame)

    assert len(semantic_stays) == 2
    assert set(semantic_stays["timezone_id"]) == {
        "Asia/Shanghai",
        "Asia/Tokyo",
    }


def test_each_stay_uses_its_coordinate_derived_local_clock() -> None:
    frame = pd.DataFrame(
        [
            {
                "user_id": "traveler",
                "arrival_time_utc": pd.Timestamp(
                    "2026-01-05T13:00:00Z"
                ),
                "departure_time_utc": pd.Timestamp(
                    "2026-01-05T14:00:00Z"
                ),
                "duration_s": 3600.0,
                "latitude": BEIJING_LAT,
                "longitude": BEIJING_LON,
            },
            {
                "user_id": "traveler",
                "arrival_time_utc": pd.Timestamp(
                    "2026-01-05T13:00:00Z"
                ),
                "departure_time_utc": pd.Timestamp(
                    "2026-01-05T14:00:00Z"
                ),
                "duration_s": 3600.0,
                "latitude": 35.6762,
                "longitude": 139.6503,
            },
        ]
    )

    semantic_stays, _ = build_semantic_locations(frame)
    by_tz = semantic_stays.set_index("timezone_id")

    assert by_tz.loc["Asia/Shanghai", "arrival_time_local"].hour == 21
    assert by_tz.loc["Asia/Tokyo", "arrival_time_local"].hour == 22


def test_travel_stays_can_contribute_to_home_in_their_own_timezone() -> None:
    rows = []
    for day in ["2026-01-05", "2026-01-06", "2026-01-07"]:
        rows.append(
            {
                "user_id": "traveler",
                "arrival_time_utc": _utc_in_zone(
                    f"{day} 21:00",
                    "Asia/Tokyo",
                ),
                "departure_time_utc": _utc_in_zone(
                    f"{day} 22:00",
                    "Asia/Tokyo",
                ),
                "duration_s": 3600.0,
                "latitude": 35.6762,
                "longitude": 139.6503,
            }
        )

    out = infer_home_office(pd.DataFrame(rows))

    home = out.query("label == 'HOME'").iloc[0]
    assert home["relevant_dates"] == 3
    assert home["relevant_dwell_share"] == pytest.approx(1.0)


def test_complete_link_does_not_chain_a_three_point_300m_span_into_one_location() -> None:
    stays = _stays(
        [
            ("u", "2026-01-01 21:00", "2026-01-01 22:00", BEIJING_LAT, BEIJING_LON),
            ("u", "2026-01-02 21:00", "2026-01-02 22:00", BEIJING_LAT + 0.00135, BEIJING_LON),
            ("u", "2026-01-03 21:00", "2026-01-03 22:00", BEIJING_LAT + 0.00270, BEIJING_LON),
        ]
    )

    _, locations = build_semantic_locations(stays)

    assert len(locations) == 2
    assert locations["diameter_m"].max() <= 200.0 + 1e-6


def test_night_evidence_uses_only_interval_overlap() -> None:
    stays = _stays(
        [
            ("u", "2026-01-05 20:50", "2026-01-05 21:30", BEIJING_LAT, BEIJING_LON),
            ("u", "2026-01-06 20:50", "2026-01-06 21:30", BEIJING_LAT, BEIJING_LON),
        ]
    )
    config = HomeOfficeConfig(
        home_min_dates=2,
        home_min_share=0.0,
        home_min_margin=0.0,
        office_min_dates=99,
    )

    out = infer_home_office(stays, config=config)
    home = out.loc[out["label"] == "HOME"].iloc[0]

    assert home["relevant_dates"] == 2
    assert home["relevant_dwell_h"] == pytest.approx(1.0)


def test_home_and_office_may_emit_the_same_location() -> None:
    rows = []
    for day in ["2026-01-05", "2026-01-06", "2026-01-07"]:
        rows.append(("u", f"{day} 21:00", f"{day} 22:00", BEIJING_LAT, BEIJING_LON))
        rows.append(("u", f"{day} 10:00", f"{day} 11:00", BEIJING_LAT, BEIJING_LON))

    out = infer_home_office(_stays(rows))

    assert set(out["label"]) == {"HOME", "OFFICE"}
    assert out["location_id"].nunique() == 1


def test_default_home_gate_abstains_when_top_two_margin_is_too_small() -> None:
    rows = []
    for day in ["2026-01-05", "2026-01-06", "2026-01-07"]:
        rows.append(("u", f"{day} 21:00", f"{day} 21:55", BEIJING_LAT, BEIJING_LON))
        rows.append(
            (
                "u",
                f"{day} 21:00",
                f"{day} 21:45",
                BEIJING_LAT + 0.004,
                BEIJING_LON,
            )
        )

    out = infer_home_office(_stays(rows))

    assert "HOME" not in set(out["label"])


def test_default_home_gate_emits_and_evidence_strength_matches_contract() -> None:
    rows = []
    for day in ["2026-01-05", "2026-01-06", "2026-01-07"]:
        rows.append(("u", f"{day} 21:00", f"{day} 22:00", BEIJING_LAT, BEIJING_LON))
        rows.append(
            (
                "u",
                f"{day} 21:00",
                f"{day} 21:20",
                BEIJING_LAT + 0.004,
                BEIJING_LON,
            )
        )

    out = infer_home_office(_stays(rows))
    home = out.loc[out["label"] == "HOME"].iloc[0]

    expected_share = 0.75
    expected_margin = 0.50
    expected_support = 3 / 5
    expected_strength = (expected_share + expected_margin + expected_support) / 3

    assert home["relevant_dwell_share"] == pytest.approx(expected_share)
    assert home["share_margin"] == pytest.approx(expected_margin)
    assert home["relevant_dates"] == 3
    assert home["evidence_strength"] == pytest.approx(expected_strength)
    assert 0.0 <= home["evidence_strength"] <= 1.0


def test_office_uses_its_separate_default_gate() -> None:
    rows = []
    for day in ["2026-01-05", "2026-01-06", "2026-01-07"]:
        rows.append(("u", f"{day} 10:00", f"{day} 10:40", BEIJING_LAT, BEIJING_LON))
        rows.append(
            (
                "u",
                f"{day} 10:00",
                f"{day} 10:20",
                BEIJING_LAT + 0.004,
                BEIJING_LON,
            )
        )

    out = infer_home_office(_stays(rows))
    office = out.loc[out["label"] == "OFFICE"].iloc[0]

    assert office["relevant_dates"] == 3
    assert office["relevant_dwell_share"] == pytest.approx(2 / 3)
    assert office["share_margin"] == pytest.approx(1 / 3)
    assert office["evidence_strength"] == pytest.approx(((2 / 3) + (1 / 3) + 0.6) / 3)


def test_evidence_strength_is_not_reported_as_probability() -> None:
    config = HomeOfficeConfig()
    assert config.timezone_resolution == "coordinate_iana"
    assert config.unresolved_timezone_policy == "drop"
    assert not hasattr(config, "beijing_radius_km")
    assert not hasattr(config, "timezone")
    assert config.home_min_dates == 3
    assert config.home_min_share == 0.50
    assert config.home_min_margin == 0.20
    assert config.office_min_dates == 3
    assert config.office_min_share == 0.30
    assert config.office_min_margin == 0.10
    assert config.support_saturation_dates == 5



def test_partial_emission_does_not_warn_on_empty_frame_concat() -> None:
    rows = [
        ("u", "2026-01-05 21:00", "2026-01-05 22:00", BEIJING_LAT, BEIJING_LON),
        ("u", "2026-01-06 21:00", "2026-01-06 22:00", BEIJING_LAT, BEIJING_LON),
        ("u", "2026-01-07 21:00", "2026-01-07 22:00", BEIJING_LAT, BEIJING_LON),
    ]

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        out = infer_home_office(_stays(rows))

    assert set(out["label"]) == {"HOME"}
    assert not [w for w in caught if issubclass(w.category, FutureWarning)]


def test_dbscan_variant_is_available_for_track_benchmark() -> None:
    stays = _stays(
        [
            ("u", "2026-01-01 21:00", "2026-01-01 22:00", BEIJING_LAT, BEIJING_LON),
            ("u", "2026-01-02 21:00", "2026-01-02 22:00", BEIJING_LAT + 0.00135, BEIJING_LON),
            ("u", "2026-01-03 21:00", "2026-01-03 22:00", BEIJING_LAT + 0.00270, BEIJING_LON),
        ]
    )
    config = HomeOfficeConfig(
        clustering_method="dbscan",
        dbscan_eps_m=200.0,
    )

    _, locations = build_semantic_locations(stays, config=config)

    assert len(locations) == 1
    assert locations.iloc[0]["stay_count"] == 3
    assert locations.iloc[0]["diameter_m"] > 200.0


def test_clustering_method_config_validation() -> None:
    with pytest.raises(ValueError, match="clustering_method"):
        HomeOfficeConfig(clustering_method="not-a-method")

    with pytest.raises(ValueError, match="dbscan_eps_m"):
        HomeOfficeConfig(clustering_method="dbscan", dbscan_eps_m=0.0)



def test_timezone_resolution_config_is_frozen_to_coordinate_iana() -> None:
    with pytest.raises(ValueError, match="timezone_resolution"):
        HomeOfficeConfig(timezone_resolution="fixed")

    with pytest.raises(ValueError, match="unresolved_timezone_policy"):
        HomeOfficeConfig(unresolved_timezone_policy="raise")
