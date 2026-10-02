"""Stage 07c: historical external-context source audit and temporal alignment.

This stage does not enrich anchors yet. It verifies what kind of historical
external evidence could be used for each GeoLife anchor date, and it records
blocking issues before any source is allowed into Stage 07d.

The policy is deliberately gate-first:
- verified temporal provenance is required for historical semantics;
- access/license/CRS uncertainty blocks automatic use;
- nearest-year proxies are explicit and never silently promoted to ground truth;
- land-cover is a physical constraint, not a functional semantic classifier;
- historical OSM is a cross-check because early coverage can be incomplete.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import date
from typing import Iterable

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class HistoricalSource:
    source_id: str
    source_name: str
    evidence_role: str
    temporal_start: str
    temporal_end: str
    spatial_resolution: str
    semantic_resolution: str
    provenance_status: str
    access_status: str
    license_status: str
    crs_status: str
    automatic_runner_status: str
    official_url: str
    notes: str


SOURCES: tuple[HistoricalSource, ...] = (
    HistoricalSource(
        source_id="bcl_poi_2008",
        source_name="Beijing City Lab — Points of interest of China in 2008",
        evidence_role="historical_semantic_candidate",
        temporal_start="2008-01-01",
        temporal_end="2008-12-31",
        spatial_resolution="individual POI",
        semantic_resolution="coordinates + place names; no category field",
        provenance_status="verified_scraped_in_2008_snapshot_2008",
        access_status="dataset page + DOI metadata; direct file availability must be checked at runtime",
        license_status="unverified_for_dataset_file",
        crs_status="unverified_for_dataset_file",
        automatic_runner_status="blocked_pending_access_license_crs",
        official_url="https://www.beijingcitylab.org/data/data-011/index.html",
        notes=(
            "Primary early semantic candidate. Exact for 2008; may be used only "
            "as an explicitly flagged ±1-year proxy for 2007/2009. Name-only "
            "semantics require high-precision lexical mapping, not free-form inference."
        ),
    ),
    HistoricalSource(
        source_id="gaode_poi_2010_paper",
        source_name="Peer-reviewed Gaode POI corpus used for 2010 BTH analysis",
        evidence_role="historical_semantic_candidate",
        temporal_start="2010-01-01",
        temporal_end="2010-12-31",
        spatial_resolution="individual POI",
        semantic_resolution="name + category + latitude/longitude",
        provenance_status="verified_author_declared_2010_crawl",
        access_status="paper verifies corpus; reusable corpus access not verified",
        license_status="unverified",
        crs_status="paper_reports_mars_coordinates_then_WGS84_conversion",
        automatic_runner_status="blocked_pending_corpus_access_license",
        official_url="https://www.geog.com.cn/EN/abstract/article/0375-5444/51955",
        notes=(
            "Strongest evidence for Gaode 2010 provenance. Do not assume a third-party "
            "archive is the same corpus. Exact file provenance and reuse rights remain gated."
        ),
    ),
    HistoricalSource(
        source_id="junxi_gaode_2011",
        source_name="Junxi Qu catalog — Gaode 2011-labelled archive",
        evidence_role="historical_semantic_candidate",
        temporal_start="2011-01-01",
        temporal_end="2011-12-31",
        spatial_resolution="individual POI",
        semantic_resolution="catalog-labelled POI archive",
        provenance_status="file_label_verified_collection_provenance_unverified",
        access_status="catalog listing",
        license_status="unverified",
        crs_status="unverified",
        automatic_runner_status="blocked_pending_provenance_license_crs",
        official_url="https://junexqu.github.io/datasets/",
        notes=(
            "Catalog proves a Gaode 2010–11-labelled archive is listed, not that the "
            "2011 file is a contemporaneous crawl or that redistribution/reuse is allowed."
        ),
    ),
    HistoricalSource(
        source_id="bcl_poi_2011_research_corpus",
        source_name="Beijing City Lab research corpus — nationwide POIs for 2011",
        evidence_role="historical_semantic_candidate",
        temporal_start="2011-01-01",
        temporal_end="2011-12-31",
        spatial_resolution="individual POI / research corpus",
        semantic_resolution="POI location/name evidence described in research output",
        provenance_status="research_use_verified_public_dataset_access_unverified",
        access_status="research output only",
        license_status="unverified",
        crs_status="unverified",
        automatic_runner_status="blocked_pending_dataset_access_metadata",
        official_url="https://www.beijingcitylab.org/projects/project-032/index.html",
        notes=(
            "BCL research output reports 5,281,382 POIs for 2011. It does not by itself "
            "establish a reusable public dataset, license, or coordinate metadata."
        ),
    ),
    HistoricalSource(
        source_id="baidu_poi_2012_candidate",
        source_name="Baidu 2012 historical POI candidate",
        evidence_role="historical_semantic_candidate",
        temporal_start="2012-01-01",
        temporal_end="2012-12-31",
        spatial_resolution="individual POI",
        semantic_resolution="candidate POI corpus",
        provenance_status="historical_corpus_provenance_unverified",
        access_status="catalog/research leads only",
        license_status="unverified",
        crs_status="unverified",
        automatic_runner_status="blocked_pending_provenance_access_license_crs",
        official_url="https://junexqu.github.io/datasets/",
        notes=(
            "Baidu Place Search existed in 2012, but that fact alone does not create "
            "a reproducible historical 2012 snapshot. Keep blocked until an actual corpus "
            "with collection provenance is verified."
        ),
    ),
    HistoricalSource(
        source_id="clcd_annual",
        source_name="China Land Cover Dataset (CLCD) annual 30 m",
        evidence_role="exact_year_physical_context",
        temporal_start="2007-01-01",
        temporal_end="2012-12-31",
        spatial_resolution="30 m raster",
        semantic_resolution="land cover only",
        provenance_status="verified_annual_historical_landsat_product",
        access_status="open_download_files_for_each_year",
        license_status="record_specific_license_must_be_checked_before_redistribution",
        crs_status="published_georeferenced_raster; exact file CRS must be read from raster metadata",
        automatic_runner_status="ready_for_local_analysis_after_license_ack",
        official_url="https://zenodo.org/records/4417810",
        notes=(
            "Use exact observation year 2007–2012. Physical constraint only: built-up/"
            "cropland/forest/water/etc. Never map impervious/built-up directly to office, "
            "residential, school, hospital, or occupation."
        ),
    ),
    HistoricalSource(
        source_id="bcl_planning_permits",
        source_name="Beijing City Lab — Land Use Planning Permits 1997–2013",
        evidence_role="historical_administrative_crosscheck",
        temporal_start="1997-01-01",
        temporal_end="2013-12-31",
        spatial_resolution="permit/project",
        semantic_resolution="administrative land-use/planning evidence",
        provenance_status="verified_crawled_from_beijing_planning_commission",
        access_status="download_listed",
        license_status="unverified_on_dataset_page",
        crs_status="geocoded_dataset_metadata_requires_file_inspection",
        automatic_runner_status="blocked_pending_license_crs",
        official_url="https://www.beijingcitylab.org/data/data-009/index.html",
        notes=(
            "Permit/use is an administrative event, not proof that a facility was operating "
            "on the GeoLife visit date. Use only as corroboration."
        ),
    ),
    HistoricalSource(
        source_id="bcl_land_transactions",
        source_name="Beijing City Lab — Land Transactions 2005–2013",
        evidence_role="historical_administrative_crosscheck",
        temporal_start="2005-01-01",
        temporal_end="2013-12-31",
        spatial_resolution="parcel/transaction",
        semantic_resolution="land transaction/planned-use evidence",
        provenance_status="verified_crawled_2013_official_beijing_source_with_2005_2013_coverage",
        access_status="download_listed",
        license_status="unverified_on_dataset_page",
        crs_status="dataset_metadata_requires_file_inspection",
        automatic_runner_status="blocked_pending_license_crs",
        official_url="https://www.beijingcitylab.org/data/data-002/index.html",
        notes=(
            "Transaction/planned use is not proof of actual occupancy or function on the "
            "visit date. Use as supporting administrative context only."
        ),
    ),
    HistoricalSource(
        source_id="bcl_blocks_2011",
        source_name="Beijing City Lab — Redefined Cities / Urban Blocks 2011",
        evidence_role="historical_morphology_prior",
        temporal_start="2011-01-01",
        temporal_end="2011-12-31",
        spatial_resolution="urban block",
        semantic_resolution="morphology/density; no verified fine functional label",
        provenance_status="verified_2011_block_product_based_on_POI_and_roads",
        access_status="download_listed",
        license_status="unverified_on_dataset_page",
        crs_status="shapefile_metadata_requires_file_inspection",
        automatic_runner_status="blocked_pending_license_crs",
        official_url="https://www.beijingcitylab.org/data/data-035/index.html",
        notes=(
            "Useful neighborhood/morphology prior for 2011. Do not convert block density "
            "attributes into residential/office/healthcare ground truth."
        ),
    ),
    HistoricalSource(
        source_id="ohsome_historical_osm",
        source_name="ohsome API — historical OpenStreetMap snapshots",
        evidence_role="historical_osm_crosscheck",
        temporal_start="2007-10-08",
        temporal_end="2012-12-31",
        spatial_resolution="OSM feature",
        semantic_resolution="historical OSM tags",
        provenance_status="verified_database_snapshot_time",
        access_status="open_api",
        license_status="OSM_ODbL_attribution_sharealike",
        crs_status="WGS84_lonlat_API_geometry",
        automatic_runner_status="ready_for_crosscheck",
        official_url="https://docs.ohsome.org/ohsome-api/v2/reference/time.html",
        notes=(
            "Exact database snapshot timestamp, but mapping lag/incomplete early China "
            "coverage remains a major bias. Missing feature is missing mapping evidence, "
            "not proof of real-world absence."
        ),
    ),
)


def source_registry() -> pd.DataFrame:
    return pd.DataFrame([asdict(source) for source in SOURCES])


def _as_user_id(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "user_id" not in out.columns:
        raise ValueError("input frame missing user_id")
    out["user_id"] = out["user_id"].astype(str)
    return out


def summarize_anchor_observation_dates(
    clustered_stays: pd.DataFrame,
    candidate_anchors: pd.DataFrame,
) -> pd.DataFrame:
    """Attach first/median/last observation date to candidate anchors."""
    stays = _as_user_id(clustered_stays)
    anchors = _as_user_id(candidate_anchors)

    required_stays = {"user_id", "location_id", "arrival_time_utc"}
    missing = required_stays.difference(stays.columns)
    if missing:
        raise ValueError(f"clustered_stays missing required columns: {sorted(missing)}")
    required_anchors = {"user_id", "location_id"}
    missing = required_anchors.difference(anchors.columns)
    if missing:
        raise ValueError(f"candidate_anchors missing required columns: {sorted(missing)}")

    stays = stays.copy()
    stays["location_id"] = pd.to_numeric(stays["location_id"], errors="raise").astype(int)
    anchors = anchors.copy()
    anchors["location_id"] = pd.to_numeric(anchors["location_id"], errors="raise").astype(int)
    stays["arrival_time_utc"] = pd.to_datetime(stays["arrival_time_utc"], utc=True)

    selected = stays.merge(
        anchors[["user_id", "location_id"]].drop_duplicates(),
        on=["user_id", "location_id"],
        how="inner",
        validate="many_to_one",
    )
    rows = []
    for (user_id, location_id), group in selected.groupby(
        ["user_id", "location_id"], sort=True
    ):
        times = group["arrival_time_utc"].sort_values(kind="stable").reset_index(drop=True)
        median_time = times.iloc[(len(times) - 1) // 2]
        rows.append(
            {
                "user_id": str(user_id),
                "location_id": int(location_id),
                "observation_count": int(len(times)),
                "first_observation_date": times.iloc[0].date().isoformat(),
                "median_observation_date": median_time.date().isoformat(),
                "last_observation_date": times.iloc[-1].date().isoformat(),
                "median_observation_year": int(median_time.year),
            }
        )

    summary = pd.DataFrame(rows)
    result = anchors.merge(
        summary,
        on=["user_id", "location_id"],
        how="left",
        validate="one_to_one",
    )
    return result


def _date(value: str) -> date:
    return pd.Timestamp(value).date()


def _eligible_ohsome(observation_date: date) -> bool:
    return observation_date >= date(2007, 10, 8)


def build_temporal_source_plan(
    anchors_with_dates: pd.DataFrame,
) -> pd.DataFrame:
    """Create a per-anchor evidence plan without pretending blocked sources are usable."""
    anchors = _as_user_id(anchors_with_dates)
    required = {"user_id", "location_id", "median_observation_date"}
    missing = required.difference(anchors.columns)
    if missing:
        raise ValueError(f"anchors_with_dates missing required columns: {sorted(missing)}")

    rows: list[dict[str, object]] = []
    for anchor in anchors.itertuples(index=False):
        observation_date = _date(str(anchor.median_observation_date))
        year = observation_date.year
        common = {
            "user_id": str(anchor.user_id),
            "location_id": int(anchor.location_id),
            "median_observation_date": observation_date.isoformat(),
            "observation_year": int(year),
        }

        # Exact-year physical context: always available conceptually for GeoLife years.
        if 2007 <= year <= 2012:
            rows.append(
                {
                    **common,
                    "source_id": "clcd_annual",
                    "alignment_type": "exact_year",
                    "source_year": int(year),
                    "temporal_offset_years": 0,
                    "evidence_role": "exact_year_physical_context",
                    "use_status": "eligible_after_local_file_and_license_ack",
                }
            )

        # BCL 2008 semantic source: exact in 2008; explicit +/-1 year proxy only.
        if year in {2007, 2008, 2009}:
            rows.append(
                {
                    **common,
                    "source_id": "bcl_poi_2008",
                    "alignment_type": "exact_year" if year == 2008 else "nearest_year_proxy",
                    "source_year": 2008,
                    "temporal_offset_years": 2008 - int(year),
                    "evidence_role": "historical_semantic_candidate",
                    "use_status": "blocked_pending_access_license_crs",
                }
            )

        if year == 2010:
            rows.append(
                {
                    **common,
                    "source_id": "gaode_poi_2010_paper",
                    "alignment_type": "exact_year",
                    "source_year": 2010,
                    "temporal_offset_years": 0,
                    "evidence_role": "historical_semantic_candidate",
                    "use_status": "blocked_pending_corpus_access_license",
                }
            )

        if year == 2011:
            rows.extend(
                [
                    {
                        **common,
                        "source_id": "junxi_gaode_2011",
                        "alignment_type": "exact_year_label_only",
                        "source_year": 2011,
                        "temporal_offset_years": 0,
                        "evidence_role": "historical_semantic_candidate",
                        "use_status": "blocked_pending_provenance_license_crs",
                    },
                    {
                        **common,
                        "source_id": "bcl_poi_2011_research_corpus",
                        "alignment_type": "exact_year_research_evidence",
                        "source_year": 2011,
                        "temporal_offset_years": 0,
                        "evidence_role": "historical_semantic_candidate",
                        "use_status": "blocked_pending_dataset_access_metadata",
                    },
                    {
                        **common,
                        "source_id": "bcl_blocks_2011",
                        "alignment_type": "exact_year",
                        "source_year": 2011,
                        "temporal_offset_years": 0,
                        "evidence_role": "historical_morphology_prior",
                        "use_status": "blocked_pending_license_crs",
                    },
                ]
            )

        if year == 2012:
            rows.append(
                {
                    **common,
                    "source_id": "baidu_poi_2012_candidate",
                    "alignment_type": "exact_year_candidate",
                    "source_year": 2012,
                    "temporal_offset_years": 0,
                    "evidence_role": "historical_semantic_candidate",
                    "use_status": "blocked_pending_provenance_access_license_crs",
                }
            )

        # Administrative cross-checks cover the full GeoLife period.
        rows.append(
            {
                **common,
                "source_id": "bcl_planning_permits",
                "alignment_type": "date_range_crosscheck",
                "source_year": pd.NA,
                "temporal_offset_years": pd.NA,
                "evidence_role": "historical_administrative_crosscheck",
                "use_status": "blocked_pending_license_crs",
            }
        )
        rows.append(
            {
                **common,
                "source_id": "bcl_land_transactions",
                "alignment_type": "date_range_crosscheck",
                "source_year": pd.NA,
                "temporal_offset_years": pd.NA,
                "evidence_role": "historical_administrative_crosscheck",
                "use_status": "blocked_pending_license_crs",
            }
        )

        if _eligible_ohsome(observation_date):
            rows.append(
                {
                    **common,
                    "source_id": "ohsome_historical_osm",
                    "alignment_type": "exact_snapshot_date",
                    "source_year": int(year),
                    "temporal_offset_years": 0,
                    "evidence_role": "historical_osm_crosscheck",
                    "use_status": "ready_for_crosscheck",
                }
            )

    return pd.DataFrame(rows)


def summarize_plan(plan: pd.DataFrame) -> pd.DataFrame:
    if plan.empty:
        return pd.DataFrame(
            columns=[
                "source_id",
                "evidence_role",
                "use_status",
                "anchors",
                "users",
            ]
        )
    return (
        plan.groupby(["source_id", "evidence_role", "use_status"], as_index=False)
        .agg(
            anchors=("location_id", "size"),
            users=("user_id", "nunique"),
        )
        .sort_values(["anchors", "source_id"], ascending=[False, True])
        .reset_index(drop=True)
    )


def summarize_year_coverage(plan: pd.DataFrame) -> pd.DataFrame:
    if plan.empty:
        return pd.DataFrame()
    grouped = (
        plan.groupby(["observation_year", "source_id", "use_status"], as_index=False)
        .agg(
            anchors=("location_id", "size"),
            users=("user_id", "nunique"),
        )
    )
    return grouped.sort_values(
        ["observation_year", "anchors", "source_id"],
        ascending=[True, False, True],
    ).reset_index(drop=True)


def source_gate_summary() -> pd.DataFrame:
    registry = source_registry()
    registry["runner_ready_now"] = registry["automatic_runner_status"].isin(
        {"ready_for_crosscheck", "ready_for_local_analysis_after_license_ack"}
    )
    return registry[
        [
            "source_id",
            "source_name",
            "evidence_role",
            "provenance_status",
            "access_status",
            "license_status",
            "crs_status",
            "automatic_runner_status",
            "runner_ready_now",
            "official_url",
        ]
    ]


def synthetic_self_check() -> dict[str, object]:
    stays = pd.DataFrame(
        [
            {"user_id": "u", "location_id": 1, "arrival_time_utc": "2008-01-01T00:00:00Z"},
            {"user_id": "u", "location_id": 1, "arrival_time_utc": "2008-07-01T00:00:00Z"},
            {"user_id": "u", "location_id": 1, "arrival_time_utc": "2008-12-01T00:00:00Z"},
        ]
    )
    anchors = pd.DataFrame([{"user_id": "u", "location_id": 1}])
    dated = summarize_anchor_observation_dates(stays, anchors)
    assert dated.loc[0, "median_observation_date"] == "2008-07-01"
    plan = build_temporal_source_plan(dated)
    assert "bcl_poi_2008" in set(plan["source_id"])
    assert "clcd_annual" in set(plan["source_id"])
    assert "ohsome_historical_osm" in set(plan["source_id"])
    bcl = plan.loc[plan["source_id"].eq("bcl_poi_2008")].iloc[0]
    assert bcl["alignment_type"] == "exact_year"
    assert bcl["use_status"].startswith("blocked_")
    return {
        "status": "ok",
        "sources": int(len(SOURCES)),
        "plan_rows": int(len(plan)),
    }
