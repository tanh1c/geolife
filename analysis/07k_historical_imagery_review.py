"""Stage 07k: blinded historical-imagery adjudication workflow.

Creates private KML and review manifests for manual Google Earth Pro historical
imagery review. This stage does not download imagery and does not infer OFFICE
automatically.

The review display is intentionally blinded to Stage-07j behavioral/BCL
diagnostics. A private key links audit IDs back to user/candidate metadata only
after visual classification is completed.
"""

from __future__ import annotations

from datetime import date
import hashlib
import html
import math
from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd


EARTH_RADIUS_M = 6_371_008.8
RING_RADII_M = (50.0, 100.0, 150.0)

VISUAL_CONTEXT_CLASSES = (
    "large_office_commercial_like_complex",
    "education_campus",
    "healthcare_institutional",
    "industrial_warehouse",
    "residential_compound",
    "transport_infrastructure",
    "mixed_urban_block",
    "construction_vacant",
    "recreation_green_space",
    "other_visible_structure",
    "ambiguous",
)

CONFIDENCE_LEVELS = ("high", "medium", "low")
YES_NO_UNCLEAR = ("yes", "no", "unclear")


def _users(frame: pd.DataFrame) -> pd.DataFrame:
    if "user_id" not in frame.columns:
        raise ValueError("frame missing user_id")
    out = frame.copy()
    out["user_id"] = out["user_id"].astype(str)
    return out


def assign_blinded_audit_ids(panel: pd.DataFrame) -> pd.DataFrame:
    """Assign deterministic IDs that do not expose user ID or audit group."""
    out = _users(panel)
    required = {"candidate_location_id", "audit_group"}
    missing = required.difference(out.columns)
    if missing:
        raise ValueError(f"panel missing columns: {sorted(missing)}")
    if out["user_id"].duplicated().any():
        raise ValueError("07k expects one candidate row per user")

    def key(row: pd.Series) -> str:
        raw = (
            f"{row['user_id']}|{int(row['candidate_location_id'])}|"
            "stage07k-historical-imagery"
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    out["_blind_order"] = out.apply(key, axis=1)
    out = out.sort_values("_blind_order", kind="stable").reset_index(drop=True)
    width = max(2, len(str(len(out))))
    out["audit_id"] = [
        f"I{index:0{width}d}" for index in range(1, len(out) + 1)
    ]
    return out.drop(columns="_blind_order")


def _median_distinct_date(values: Iterable[object]) -> date | pd.NaT:
    days = sorted(
        {
            pd.Timestamp(value).date()
            for value in values
            if pd.notna(value)
        }
    )
    if not days:
        return pd.NaT
    return days[(len(days) - 1) // 2]


def build_location_observation_summary(
    semantic_stays: pd.DataFrame,
) -> pd.DataFrame:
    stays = _users(semantic_stays)
    required = {"location_id", "arrival_local_date"}
    missing = required.difference(stays.columns)
    if missing:
        raise ValueError(
            f"semantic stays missing columns: {sorted(missing)}"
        )
    stays["location_id"] = pd.to_numeric(
        stays["location_id"], errors="raise"
    ).astype(int)

    rows = []
    for (user_id, location_id), group in stays.groupby(
        ["user_id", "location_id"], sort=False
    ):
        dates = [
            pd.Timestamp(value).date()
            for value in group["arrival_local_date"]
            if pd.notna(value)
        ]
        unique_dates = sorted(set(dates))
        rows.append(
            {
                "user_id": str(user_id),
                "location_id": int(location_id),
                "observation_start_date": (
                    unique_dates[0] if unique_dates else pd.NaT
                ),
                "observation_median_date": _median_distinct_date(unique_dates),
                "observation_end_date": (
                    unique_dates[-1] if unique_dates else pd.NaT
                ),
                "observation_active_dates": int(len(unique_dates)),
                "observation_stays": int(len(group)),
            }
        )
    return pd.DataFrame(rows)


def _haversine_scalar_m(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = (
        math.sin(dphi / 2.0) ** 2
        + math.cos(phi1)
        * math.cos(phi2)
        * math.sin(dlambda / 2.0) ** 2
    )
    return 2.0 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(a)))


def build_spatial_review_panel(
    audit_panel: pd.DataFrame,
    semantic_locations: pd.DataFrame,
    semantic_stays: pd.DataFrame,
) -> pd.DataFrame:
    """Attach candidate/HOME coordinates and local observation dates."""
    panel = assign_blinded_audit_ids(audit_panel)
    locations = _users(semantic_locations)
    required = {"location_id", "latitude", "longitude"}
    missing = required.difference(locations.columns)
    if missing:
        raise ValueError(
            f"semantic locations missing columns: {sorted(missing)}"
        )
    locations["location_id"] = pd.to_numeric(
        locations["location_id"], errors="raise"
    ).astype(int)
    if locations.duplicated(["user_id", "location_id"]).any():
        raise ValueError("semantic location keys must be unique")

    candidate_lookup = locations[
        ["user_id", "location_id", "latitude", "longitude"]
    ].rename(
        columns={
            "location_id": "candidate_location_id",
            "latitude": "candidate_latitude",
            "longitude": "candidate_longitude",
        }
    )
    panel = panel.merge(
        candidate_lookup,
        on=["user_id", "candidate_location_id"],
        how="left",
        validate="one_to_one",
    )
    if panel[["candidate_latitude", "candidate_longitude"]].isna().any().any():
        raise ValueError("candidate coordinate lookup failed")

    observation = build_location_observation_summary(semantic_stays).rename(
        columns={"location_id": "candidate_location_id"}
    )
    panel = panel.merge(
        observation,
        on=["user_id", "candidate_location_id"],
        how="left",
        validate="one_to_one",
    )

    home_lookup = locations[
        ["user_id", "location_id", "latitude", "longitude"]
    ].rename(
        columns={
            "location_id": "production_home_location_id",
            "latitude": "home_latitude",
            "longitude": "home_longitude",
        }
    )
    panel = panel.merge(
        home_lookup,
        on=["user_id", "production_home_location_id"],
        how="left",
        validate="one_to_one",
    )

    distances = []
    for row in panel.itertuples(index=False):
        if pd.isna(row.home_latitude) or pd.isna(row.home_longitude):
            distances.append(np.nan)
        else:
            distances.append(
                _haversine_scalar_m(
                    float(row.candidate_latitude),
                    float(row.candidate_longitude),
                    float(row.home_latitude),
                    float(row.home_longitude),
                )
            )
    panel["candidate_home_distance_m"] = distances
    return panel


def blinded_review_manifest(spatial_panel: pd.DataFrame) -> pd.DataFrame:
    """Create the visual-review sheet without behavioral/BCL/group labels."""
    source = spatial_panel.copy()
    columns = [
        "audit_id",
        "candidate_latitude",
        "candidate_longitude",
        "observation_start_date",
        "observation_median_date",
        "observation_end_date",
        "observation_active_dates",
        "observation_stays",
    ]
    out = source[columns].copy()
    out["imagery_available"] = ""
    out["imagery_date_used"] = ""
    out["imagery_date_offset_days"] = ""
    out["imagery_quality"] = ""
    out["structure_present"] = ""
    out["visual_context_class"] = ""
    out["visual_context_confidence"] = ""
    out["candidate_inside_same_complex"] = ""
    out["historical_name_evidence"] = ""
    out["present_day_name_aid"] = ""
    out["review_notes"] = ""
    return out


def unblinding_key(spatial_panel: pd.DataFrame) -> pd.DataFrame:
    """Private key; never place user IDs inside KML or blind review CSV."""
    wanted = [
        "audit_id",
        "user_id",
        "audit_group",
        "candidate_location_id",
        "production_home_location_id",
        "candidate_home_distance_m",
        "full_support_days",
        "full_office_share",
        "howde_matches_candidate",
        "recurrence_matches_candidate",
        "split_full_candidate_match_count",
        "full_candidate_heldout_top1",
        "dropout_candidate_retention",
        "bcl_evaluable",
        "work_compatible_lexical_within_100m",
        "business_name_within_100m",
        "work_compatible_lexical_within_150m",
        "business_name_within_150m",
    ]
    return spatial_panel[
        [column for column in wanted if column in spatial_panel.columns]
    ].copy()


def review_priority_ids(spatial_panel: pd.DataFrame) -> pd.DataFrame:
    """Nine near-miss IDs to review first; margin/share family stays blinded."""
    out = spatial_panel.loc[
        spatial_panel["audit_group"].isin(["margin_near", "share_near"]),
        ["audit_id"],
    ].copy()
    return out.sort_values("audit_id").reset_index(drop=True)


def _circle_coordinates(
    latitude: float,
    longitude: float,
    radius_m: float,
    *,
    vertices: int = 72,
) -> list[tuple[float, float]]:
    lat1 = math.radians(latitude)
    lon1 = math.radians(longitude)
    angular = radius_m / EARTH_RADIUS_M
    coords = []
    for step in range(vertices + 1):
        bearing = 2.0 * math.pi * step / vertices
        lat2 = math.asin(
            math.sin(lat1) * math.cos(angular)
            + math.cos(lat1) * math.sin(angular) * math.cos(bearing)
        )
        lon2 = lon1 + math.atan2(
            math.sin(bearing) * math.sin(angular) * math.cos(lat1),
            math.cos(angular) - math.sin(lat1) * math.sin(lat2),
        )
        coords.append((math.degrees(lon2), math.degrees(lat2)))
    return coords


def _kml_date(value: object) -> str:
    if pd.isna(value):
        return "unknown"
    return pd.Timestamp(value).date().isoformat()


def _kml_description(row: pd.Series) -> str:
    # Intentionally blinded: no audit group, user ID, behavior, or BCL.
    lines = [
        f"Audit ID: {row['audit_id']}",
        f"Observation start: {_kml_date(row['observation_start_date'])}",
        f"Observation median: {_kml_date(row['observation_median_date'])}",
        f"Observation end: {_kml_date(row['observation_end_date'])}",
        f"Active local dates: {int(row['observation_active_dates'])}",
        "Review the nearest available historical imagery to the median date.",
        "Classify visible structure/land-use only; do not infer employer.",
    ]
    return "<br/>".join(html.escape(line) for line in lines)


def _linestring_placemark(
    name: str,
    coords: list[tuple[float, float]],
    style_url: str,
) -> str:
    coord_text = " ".join(f"{lon:.8f},{lat:.8f},0" for lon, lat in coords)
    return (
        "<Placemark>"
        f"<name>{html.escape(name)}</name>"
        f"<styleUrl>#{style_url}</styleUrl>"
        "<LineString><tessellate>1</tessellate>"
        f"<coordinates>{coord_text}</coordinates>"
        "</LineString></Placemark>"
    )


def write_review_kml(
    spatial_panel: pd.DataFrame,
    output_path: str | Path,
    *,
    audit_ids: Iterable[str] | None = None,
    include_home_reference: bool = True,
) -> Path:
    """Write private blinded KML for Google Earth Pro."""
    frame = spatial_panel.copy()
    if audit_ids is not None:
        allowed = {str(value) for value in audit_ids}
        frame = frame.loc[frame["audit_id"].isin(allowed)].copy()
    if frame.empty:
        raise ValueError("no rows selected for KML")

    placemarks = []
    for _, row in frame.sort_values("audit_id").iterrows():
        audit_id = str(row["audit_id"])
        description = _kml_description(row)
        placemarks.append(
            "<Placemark>"
            f"<name>{html.escape(audit_id)} candidate</name>"
            "<styleUrl>#candidate</styleUrl>"
            f"<description><![CDATA[{description}]]></description>"
            "<Point>"
            f"<coordinates>{float(row['candidate_longitude']):.8f},"
            f"{float(row['candidate_latitude']):.8f},0</coordinates>"
            "</Point></Placemark>"
        )

        for radius in RING_RADII_M:
            coords = _circle_coordinates(
                float(row["candidate_latitude"]),
                float(row["candidate_longitude"]),
                float(radius),
            )
            placemarks.append(
                _linestring_placemark(
                    f"{audit_id} — {int(radius)}m",
                    coords,
                    f"ring{int(radius)}",
                )
            )

        if (
            include_home_reference
            and pd.notna(row.get("home_latitude"))
            and pd.notna(row.get("home_longitude"))
        ):
            placemarks.append(
                "<Placemark>"
                f"<name>{html.escape(audit_id)} HOME reference</name>"
                "<styleUrl>#home</styleUrl>"
                "<description><![CDATA[Reference HOME marker for spatial orientation only.]]></description>"
                "<Point>"
                f"<coordinates>{float(row['home_longitude']):.8f},"
                f"{float(row['home_latitude']):.8f},0</coordinates>"
                "</Point></Placemark>"
            )

    kml = """<?xml version="1.0" encoding="UTF-8"?>
<kml xmlns="http://www.opengis.net/kml/2.2"><Document>
<name>GeoLife Stage 07k historical imagery review</name>
<Style id="candidate"><IconStyle><scale>1.1</scale><color>ff00ffff</color></IconStyle></Style>
<Style id="home"><IconStyle><scale>0.9</scale><color>ff00ff00</color></IconStyle></Style>
<Style id="ring50"><LineStyle><color>ff00ffff</color><width>2</width></LineStyle></Style>
<Style id="ring100"><LineStyle><color>ffffaa00</color><width>2</width></LineStyle></Style>
<Style id="ring150"><LineStyle><color>ffff00ff</color><width>2</width></LineStyle></Style>
""" + "\n".join(placemarks) + "\n</Document></kml>"

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(kml, encoding="utf-8")
    return path


def validate_completed_review(review: pd.DataFrame) -> pd.DataFrame:
    """Validate manual rubric values; does not create a semantic OFFICE label."""
    out = review.copy()
    required = {
        "audit_id",
        "imagery_available",
        "visual_context_class",
        "visual_context_confidence",
        "structure_present",
    }
    missing = required.difference(out.columns)
    if missing:
        raise ValueError(f"review missing columns: {sorted(missing)}")

    for column, allowed in (
        ("imagery_available", YES_NO_UNCLEAR),
        ("structure_present", YES_NO_UNCLEAR),
        ("candidate_inside_same_complex", YES_NO_UNCLEAR),
        ("visual_context_confidence", CONFIDENCE_LEVELS),
    ):
        values = out[column].astype(str).str.strip().str.lower()
        nonempty = values.ne("")
        invalid = nonempty & ~values.isin(allowed)
        if invalid.any():
            raise ValueError(
                f"invalid {column}: {sorted(values.loc[invalid].unique())}"
            )

    classes = out["visual_context_class"].astype(str).str.strip()
    nonempty = classes.ne("")
    invalid = nonempty & ~classes.isin(VISUAL_CONTEXT_CLASSES)
    if invalid.any():
        raise ValueError(
            "invalid visual_context_class: "
            f"{sorted(classes.loc[invalid].unique())}"
        )
    return out


def review_rubric_table() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "visual_context_class": list(VISUAL_CONTEXT_CLASSES),
            "interpretation": [
                "large complex visually compatible with office/commercial use; imagery alone does not prove OFFICE",
                "campus-like education complex",
                "hospital / institutional complex",
                "industrial or warehouse morphology",
                "residential compound / housing morphology",
                "transport station / road / infrastructure context",
                "dense mixed-use urban block with no reliable single function",
                "construction site, vacant land, or undeveloped parcel",
                "park / sports / green-space morphology",
                "visible built structure not fitting another class",
                "imagery insufficient or morphology not classifiable",
            ],
        }
    )


def synthetic_self_check() -> dict[str, object]:
    panel = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "audit_group": "margin_near",
                "candidate_location_id": 1,
                "production_home_location_id": 0,
                "full_support_days": 4,
                "full_office_share": 0.31,
            },
            {
                "user_id": "u2",
                "audit_group": "baseline",
                "candidate_location_id": 2,
                "production_home_location_id": 0,
                "full_support_days": 5,
                "full_office_share": 0.5,
            },
        ]
    )
    locations = pd.DataFrame(
        [
            {"user_id": "u1", "location_id": 0, "latitude": 39.9, "longitude": 116.4},
            {"user_id": "u1", "location_id": 1, "latitude": 39.91, "longitude": 116.41},
            {"user_id": "u2", "location_id": 0, "latitude": 39.8, "longitude": 116.3},
            {"user_id": "u2", "location_id": 2, "latitude": 39.82, "longitude": 116.32},
        ]
    )
    stays = pd.DataFrame(
        [
            {"user_id": "u1", "location_id": 1, "arrival_local_date": "2008-01-01"},
            {"user_id": "u1", "location_id": 1, "arrival_local_date": "2008-01-03"},
            {"user_id": "u2", "location_id": 2, "arrival_local_date": "2009-02-01"},
        ]
    )
    spatial = build_spatial_review_panel(panel, locations, stays)
    assert len(spatial) == 2
    assert spatial["audit_id"].str.startswith("I").all()
    assert spatial["candidate_home_distance_m"].gt(0).all()
    manifest = blinded_review_manifest(spatial)
    assert "user_id" not in manifest.columns
    assert "audit_group" not in manifest.columns
    return {
        "status": "ok",
        "rows": len(spatial),
        "rubric_classes": len(VISUAL_CONTEXT_CLASSES),
    }
