"""Stage 08a: targeted HOME coverage expansion / confidence tiers.

The frozen production HOME-27 remains the high-confidence core.

Stage 05b already reduced the entire non-production HOME space to two
HIGH/MEDIUM unique-vote winners outside the emitted core. Stage 08a therefore
audits only those candidates and adds independent evidence measured later in
Stages 07m, 07n, and 07o.

This stage can assign research/output tiers:
- HOME_PROBABLE
- HOME_PLAUSIBLE
- ABSTAIN

It does not alter the production HOME gate or relabel HOME-27.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from geolife.geo.distance import haversine_m


INTERNAL_ACCEPTED_TIERS = {"high", "medium"}
EXACT_EXTERNAL_METHODS = (
    "trackintel_osna_exact",
    "scikit_home_exact",
    "scitepress_home_exact",
)


def select_expansion_candidates(home_evidence: pd.DataFrame) -> pd.DataFrame:
    """Return non-production HIGH/MEDIUM unique HOME consensus winners."""

    required = {
        "user_id",
        "location_id",
        "home_tier",
        "production_status",
        "unique_vote_winner",
        "method_votes",
        "reliability_axes",
    }
    missing = required.difference(home_evidence.columns)
    if missing:
        raise ValueError(f"home_evidence missing columns: {sorted(missing)}")

    frame = home_evidence.copy()
    frame["user_id"] = frame["user_id"].astype(str)
    frame["location_id"] = pd.to_numeric(
        frame["location_id"], errors="raise"
    ).astype(int)

    mask = (
        frame["unique_vote_winner"].fillna(False).astype(bool)
        & frame["home_tier"].astype(str).isin(INTERNAL_ACCEPTED_TIERS)
        & ~frame["production_status"].astype(str).eq("baseline_emitted")
    )
    out = frame.loc[mask].copy()

    if out["user_id"].duplicated().any():
        raise RuntimeError("Stage 08a expects at most one expansion candidate per user")
    return out.sort_values(["home_tier", "user_id"], kind="stable").reset_index(drop=True)


def attach_location_context(
    candidates: pd.DataFrame,
    locations: pd.DataFrame,
    production_output: pd.DataFrame,
) -> pd.DataFrame:
    """Attach production-location geometry/features and OFFICE collision status."""

    required_loc = {"user_id", "location_id", "latitude", "longitude"}
    missing = required_loc.difference(locations.columns)
    if missing:
        raise ValueError(f"locations missing columns: {sorted(missing)}")

    loc = locations.copy()
    loc["user_id"] = loc["user_id"].astype(str)
    loc["location_id"] = pd.to_numeric(loc["location_id"], errors="raise").astype(int)

    descriptive = [
        col
        for col in [
            "user_id",
            "location_id",
            "latitude",
            "longitude",
            "stay_count",
            "total_dwell_h",
            "active_local_dates",
            "diameter_m",
            "home_dwell_h",
            "home_share",
        ]
        if col in loc.columns
    ]

    # Location-table values are authoritative for geometry/descriptive fields.
    # Drop overlapping non-key columns from cached Stage-05b evidence first so
    # pandas does not create latitude_x/latitude_y (or similar) suffixes.
    overlap = [
        col
        for col in descriptive
        if col not in {"user_id", "location_id"} and col in candidates.columns
    ]
    base = candidates.drop(columns=overlap, errors="ignore").copy()

    out = base.merge(
        loc[descriptive],
        on=["user_id", "location_id"],
        how="left",
        validate="one_to_one",
    )
    if out[["latitude", "longitude"]].isna().any().any():
        raise RuntimeError("expansion candidate missing location geometry")

    office = production_output.loc[
        production_output["label"].astype(str).str.upper().eq("OFFICE"),
        ["user_id", "location_id"],
    ].copy()
    office["user_id"] = office["user_id"].astype(str)
    office["location_id"] = pd.to_numeric(
        office["location_id"], errors="raise"
    ).astype(int)
    office = office.rename(columns={"location_id": "production_office_location_id"})

    out = out.merge(office, on="user_id", how="left")
    out["collides_with_production_office"] = (
        out["production_office_location_id"].notna()
        & out["location_id"].eq(out["production_office_location_id"])
    )
    return out


def _same_namespace_exact(
    candidates: pd.DataFrame,
    comparator: pd.DataFrame,
    *,
    method: str | None = None,
    label: str = "HOME",
) -> pd.Series:
    comp = comparator.copy()
    comp["user_id"] = comp["user_id"].astype(str)
    if "label" in comp.columns:
        comp = comp.loc[comp["label"].astype(str).str.upper().eq(label)]
    if method is not None and "method" in comp.columns:
        comp = comp.loc[comp["method"].astype(str).eq(method)]

    location_col = "location_id"
    if location_col not in comp.columns:
        raise ValueError("comparator requires location_id")

    comp = comp[["user_id", location_col]].drop_duplicates("user_id")
    mapping = dict(
        zip(
            comp["user_id"],
            pd.to_numeric(comp[location_col], errors="coerce"),
        )
    )
    return pd.Series(
        [
            bool(
                user in mapping
                and pd.notna(mapping[user])
                and int(mapping[user]) == int(location_id)
            )
            for user, location_id in zip(
                candidates["user_id"], candidates["location_id"], strict=True
            )
        ],
        index=candidates.index,
        dtype=bool,
    )


def _spatial_distance_to_candidate(
    candidates: pd.DataFrame,
    comparator: pd.DataFrame,
    *,
    label: str = "HOME",
    variant: str | None = None,
) -> pd.Series:
    comp = comparator.copy()
    comp["user_id"] = comp["user_id"].astype(str)
    if "label" in comp.columns:
        comp = comp.loc[comp["label"].astype(str).str.upper().eq(label)]
    if variant is not None and "variant" in comp.columns:
        comp = comp.loc[comp["variant"].astype(str).eq(variant)]

    required = {"user_id", "latitude", "longitude"}
    missing = required.difference(comp.columns)
    if missing:
        raise ValueError(f"spatial comparator missing columns: {sorted(missing)}")

    comp = comp[["user_id", "latitude", "longitude"]].drop_duplicates("user_id")
    mapping = {
        str(row.user_id): (float(row.latitude), float(row.longitude))
        for row in comp.itertuples(index=False)
    }

    values: list[float] = []
    for row in candidates.itertuples(index=False):
        point = mapping.get(str(row.user_id))
        if point is None:
            values.append(np.nan)
            continue
        values.append(
            float(
                haversine_m(
                    float(row.latitude),
                    float(row.longitude),
                    point[0],
                    point[1],
                )
            )
        )
    return pd.Series(values, index=candidates.index, dtype=float)


def build_expansion_evidence_matrix(
    candidates: pd.DataFrame,
    *,
    trackintel_semantic_candidates: pd.DataFrame,
    scikit_home_candidates: pd.DataFrame,
    scitepress_candidates: pd.DataFrame,
    geohash_home_candidates: pd.DataFrame,
    trackintel_e2e_candidates: pd.DataFrame,
) -> pd.DataFrame:
    """Join later independent semantic evidence onto Stage-05b candidates."""

    out = candidates.copy()

    out["trackintel_osna_exact"] = _same_namespace_exact(
        out, trackintel_semantic_candidates, method="OSNA"
    )
    out["trackintel_freq_exact"] = _same_namespace_exact(
        out, trackintel_semantic_candidates, method="FREQ"
    )
    out["scikit_home_exact"] = _same_namespace_exact(out, scikit_home_candidates)
    out["scitepress_home_exact"] = _same_namespace_exact(out, scitepress_candidates)

    out["geohash_distance_m"] = _spatial_distance_to_candidate(
        out, geohash_home_candidates
    )
    out["geohash_within_200m"] = out["geohash_distance_m"].le(200)

    for variant in ("dbscan100", "dbscan200"):
        distance_col = f"trackintel_e2e_{variant}_distance_m"
        out[distance_col] = _spatial_distance_to_candidate(
            out,
            trackintel_e2e_candidates,
            variant=variant,
        )
        out[f"trackintel_e2e_{variant}_within_200m"] = out[distance_col].le(200)

    out["external_exact_family_count"] = out[
        list(EXACT_EXTERNAL_METHODS)
    ].sum(axis=1).astype(int)
    out["auxiliary_support_count"] = (
        out["trackintel_freq_exact"].astype(int)
        + out["geohash_within_200m"].astype(int)
        + out["trackintel_e2e_dbscan100_within_200m"].astype(int)
        + out["trackintel_e2e_dbscan200_within_200m"].astype(int)
    )

    return out


def assign_expansion_tiers(evidence: pd.DataFrame) -> pd.DataFrame:
    """Assign transparent HOME expansion tiers.

    HOME_PROBABLE:
      - Stage-05b HIGH/MEDIUM unique winner (already guaranteed by candidate set)
      - >=2 internal methods voted for the candidate
      - >=2/3 Stage-05b reliability axes
      - >=2 exact confirmations across three deliberately different external
        semantic families: Trackintel OSNA, scikit nighttime-frequency, and
        SCITEPRESS work/rest-style HOME
      - no collision with production OFFICE

    HOME_PLAUSIBLE:
      - same internal evidence floor
      - not PROBABLE
      - at least one exact external confirmation OR spatial support within 200 m
        from geohash / end-to-end Trackintel

    Otherwise ABSTAIN.

    These are evidence tiers, not calibrated probabilities.
    """

    out = evidence.copy()

    internal_floor = (
        out["home_tier"].astype(str).isin(INTERNAL_ACCEPTED_TIERS)
        & out["unique_vote_winner"].fillna(False).astype(bool)
        & pd.to_numeric(out["method_votes"], errors="coerce").ge(2)
        & pd.to_numeric(out["reliability_axes"], errors="coerce").ge(2)
    )
    no_office_collision = ~out["collides_with_production_office"].fillna(False)

    probable = (
        internal_floor
        & no_office_collision
        & out["external_exact_family_count"].ge(2)
    )
    any_spatial = (
        out["geohash_within_200m"].fillna(False)
        | out["trackintel_e2e_dbscan100_within_200m"].fillna(False)
        | out["trackintel_e2e_dbscan200_within_200m"].fillna(False)
    )
    plausible = (
        internal_floor
        & no_office_collision
        & ~probable
        & (
            out["external_exact_family_count"].ge(1)
            | out["trackintel_freq_exact"].fillna(False)
            | any_spatial
        )
    )

    out["home_expansion_tier"] = "ABSTAIN"
    out.loc[plausible, "home_expansion_tier"] = "HOME_PLAUSIBLE"
    out.loc[probable, "home_expansion_tier"] = "HOME_PROBABLE"

    reasons: list[str] = []
    for row in out.itertuples(index=False):
        if bool(row.collides_with_production_office):
            reasons.append("production_office_collision")
        elif row.home_expansion_tier == "HOME_PROBABLE":
            reasons.append("internal_consensus_plus_2_external_exact_families")
        elif row.home_expansion_tier == "HOME_PLAUSIBLE":
            reasons.append("internal_consensus_plus_partial_external_support")
        else:
            reasons.append("insufficient_external_confirmation")
    out["tier_reason"] = reasons
    return out


def summarize_expansion(evidence: pd.DataFrame, *, core_home_users: int = 27) -> pd.DataFrame:
    counts = evidence["home_expansion_tier"].value_counts()
    probable = int(counts.get("HOME_PROBABLE", 0))
    plausible = int(counts.get("HOME_PLAUSIBLE", 0))
    abstain = int(counts.get("ABSTAIN", 0))

    return pd.DataFrame(
        [
            {
                "HOME_HIGH_CONFIDENCE_CORE": int(core_home_users),
                "HOME_PROBABLE_NEW": probable,
                "HOME_PLAUSIBLE_NEW": plausible,
                "HOME_EXPANSION_ABSTAIN": abstain,
                "high_plus_probable_coverage": int(core_home_users + probable),
                "high_plus_probable_plausible_coverage": int(
                    core_home_users + probable + plausible
                ),
                "production_HOME_unchanged": int(core_home_users),
            }
        ]
    )


def candidate_support_summary(evidence: pd.DataFrame) -> pd.DataFrame:
    """Aggregate support without exposing user ids."""

    if evidence.empty:
        return pd.DataFrame()

    return (
        evidence.groupby("home_expansion_tier", as_index=False)
        .agg(
            candidates=("user_id", "size"),
            high_internal_tier=("home_tier", lambda s: int(pd.Series(s).eq("high").sum())),
            median_method_votes=("method_votes", "median"),
            median_reliability_axes=("reliability_axes", "median"),
            median_external_exact_families=("external_exact_family_count", "median"),
            osna_exact=("trackintel_osna_exact", "sum"),
            scikit_exact=("scikit_home_exact", "sum"),
            scitepress_exact=("scitepress_home_exact", "sum"),
            geohash_within_200m=("geohash_within_200m", "sum"),
            e2e_dbscan100_within_200m=("trackintel_e2e_dbscan100_within_200m", "sum"),
            e2e_dbscan200_within_200m=("trackintel_e2e_dbscan200_within_200m", "sum"),
            office_collisions=("collides_with_production_office", "sum"),
        )
        .sort_values("home_expansion_tier", kind="stable")
        .reset_index(drop=True)
    )


def synthetic_self_check() -> dict[str, object]:
    base = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "location_id": 1,
                "home_tier": "high",
                "production_status": "fixed_candidate_not_emitted",
                "unique_vote_winner": True,
                "method_votes": 3,
                "reliability_axes": 3,
            },
            {
                "user_id": "u2",
                "location_id": 2,
                "home_tier": "medium",
                "production_status": "fixed_candidate_not_emitted",
                "unique_vote_winner": True,
                "method_votes": 2,
                "reliability_axes": 2,
            },
        ]
    )
    loc = pd.DataFrame(
        {
            "user_id": ["u1", "u2"],
            "location_id": [1, 2],
            "latitude": [39.9, 39.91],
            "longitude": [116.4, 116.41],
        }
    )
    prod = pd.DataFrame(columns=["user_id", "label", "location_id"])
    candidates = attach_location_context(base, loc, prod)

    ti = pd.DataFrame(
        {
            "method": ["OSNA", "FREQ", "OSNA"],
            "user_id": ["u1", "u1", "u2"],
            "label": ["HOME", "HOME", "HOME"],
            "location_id": [1, 1, 2],
        }
    )
    sk = pd.DataFrame(
        {
            "user_id": ["u1"],
            "label": ["HOME"],
            "location_id": [1],
        }
    )
    sc = pd.DataFrame(
        {
            "user_id": ["u1"],
            "label": ["HOME"],
            "location_id": [1],
        }
    )
    gh = pd.DataFrame(
        {
            "user_id": ["u2"],
            "label": ["HOME"],
            "latitude": [39.9101],
            "longitude": [116.4101],
        }
    )
    e2e = pd.DataFrame(
        {
            "variant": ["dbscan100", "dbscan200"],
            "user_id": ["u2", "u2"],
            "label": ["HOME", "HOME"],
            "latitude": [39.9101, 39.9101],
            "longitude": [116.4101, 116.4101],
        }
    )

    matrix = build_expansion_evidence_matrix(
        candidates,
        trackintel_semantic_candidates=ti,
        scikit_home_candidates=sk,
        scitepress_candidates=sc,
        geohash_home_candidates=gh,
        trackintel_e2e_candidates=e2e,
    )
    tiered = assign_expansion_tiers(matrix)
    tiers = dict(zip(tiered["user_id"], tiered["home_expansion_tier"]))
    assert tiers["u1"] == "HOME_PROBABLE"
    assert tiers["u2"] == "HOME_PLAUSIBLE"

    return {"status": "ok", "candidates": 2, "probable": 1, "plausible": 1}
