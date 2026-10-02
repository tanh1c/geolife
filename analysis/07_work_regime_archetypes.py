"""Stage 07: descriptive work-regime / occupational-mobility archetypes.

This stage does NOT infer occupation or job title. It composes previously
audited behavioral states into a user-level work-regime hypothesis and a
recommended WORK representation:

- fixed_site_like -> one recurring work-anchor candidate;
- shifted_fixed_site_like -> one schedule-agnostic work-anchor candidate;
- multi_site_recurring -> a set of recurring work-like anchors;
- route_centric_mobile_like -> route/activity-region representation;
- irregular -> abstain from a fixed workplace representation;
- insufficient -> abstain.

The taxonomy is research-only and must not be described as semantic ground
truth, employment status, or occupation inference.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd


ARCHETYPES = (
    "shifted_fixed_site_like",
    "fixed_site_like",
    "route_centric_mobile_like",
    "multi_site_recurring",
    "irregular",
    "insufficient",
)

WORK_REPRESENTATION = {
    "shifted_fixed_site_like": "single_work_anchor_schedule_agnostic",
    "fixed_site_like": "single_work_anchor_candidate",
    "route_centric_mobile_like": "route_or_activity_region",
    "multi_site_recurring": "work_anchor_set",
    "irregular": "abstain_fixed_workplace",
    "insufficient": "abstain_insufficient_evidence",
}


@dataclass(frozen=True)
class WorkRegimeAudit:
    evidence_matrix: pd.DataFrame
    archetypes: pd.DataFrame
    archetype_summary: pd.DataFrame
    representation_summary: pd.DataFrame
    upstream_overlap: pd.DataFrame
    evidence_summary: pd.DataFrame


def _as_user_id(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "user_id" not in out.columns:
        raise ValueError("input frame missing user_id")
    out["user_id"] = out["user_id"].astype(str)
    return out


def _one_row_per_user(frame: pd.DataFrame, name: str) -> pd.DataFrame:
    out = _as_user_id(frame)
    if out["user_id"].duplicated().any():
        raise ValueError(f"{name} must contain at most one row per user")
    return out


def _bool_series(frame: pd.DataFrame, column: str, default: bool = False) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=bool)
    return frame[column].fillna(default).astype(bool)


def _numeric_series(
    frame: pd.DataFrame,
    column: str,
    default: float = np.nan,
) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(default, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _anchor_class(features: pd.DataFrame) -> pd.Series:
    if "anchor_count_class" in features.columns:
        return features["anchor_count_class"].fillna("unknown").astype(str)

    recurring = _numeric_series(features, "recurring_location_count", default=0).fillna(0)
    return pd.Series(
        np.select(
            [
                recurring.le(0),
                recurring.eq(1),
                recurring.eq(2),
                recurring.ge(3),
            ],
            [
                "no_stable_anchor",
                "dominant_anchor",
                "two_anchor",
                "multiple_anchor",
            ],
            default="unknown",
        ),
        index=features.index,
        dtype=object,
    )


def build_evidence_matrix(
    behavior_features: pd.DataFrame,
    work_patterns: pd.DataFrame,
    routine_users: pd.DataFrame,
    home_evidence: pd.DataFrame | None = None,
    independent_secondary_evidence: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Join already-audited states without creating new semantic labels."""
    behavior = _one_row_per_user(behavior_features, "behavior_features").copy()
    work = _one_row_per_user(work_patterns, "work_patterns").copy()
    routine = _one_row_per_user(routine_users, "routine_users").copy()

    behavior["anchor_count_class"] = _anchor_class(behavior)
    keep_behavior = [
        "user_id",
        "anchor_count_class",
    ]
    for column in (
        "recurring_location_count",
        "stable_shifted_candidate",
        "mobile_work_like_candidate",
        "usable_temporal_days",
        "usable_motif_days",
        "distance_per_usable_day_km",
        "movement_proxy_per_usable_day_h",
        "weekday_active_days",
    ):
        if column in behavior.columns:
            keep_behavior.append(column)

    keep_work = ["user_id"]
    for column in (
        "window_pattern",
        "eligible_windows",
        "candidate_windows",
        "candidate_window_share",
        "distinct_top_locations",
        "dominant_window_share",
        "median_arrival_hour_concentration",
        "median_dominant_hour_shift_h",
        "dominant_matches_baseline_emitted_office",
    ):
        if column in work.columns:
            keep_work.append(column)

    keep_routine = ["user_id"]
    for column in (
        "usable_motif_days",
        "transition_days",
        "total_transitions",
        "distinct_edges",
        "repeated_edges",
        "top_edge_day_share",
        "top_edge_transition_share",
        "edge_entropy",
        "median_repeated_departure_concentration",
        "has_repeated_edge",
    ):
        if column in routine.columns:
            keep_routine.append(column)

    users = sorted(
        set(behavior["user_id"])
        | set(work["user_id"])
        | set(routine["user_id"])
    )
    out = pd.DataFrame({"user_id": users})
    out = out.merge(
        behavior[keep_behavior],
        on="user_id",
        how="left",
        validate="one_to_one",
    )
    out = out.merge(
        work[keep_work],
        on="user_id",
        how="left",
        validate="one_to_one",
        suffixes=("", "_work"),
    )
    out = out.merge(
        routine[keep_routine],
        on="user_id",
        how="left",
        validate="one_to_one",
        suffixes=("", "_routine"),
    )

    if home_evidence is not None and not home_evidence.empty:
        home = _as_user_id(home_evidence)
        if "unique_vote_winner" in home.columns:
            home = home.loc[_bool_series(home, "unique_vote_winner")]
        keep_home = ["user_id"]
        for column in ("home_tier", "method_votes", "location_id"):
            if column in home.columns:
                keep_home.append(column)
        home = home[keep_home].drop_duplicates("user_id", keep="first")
        out = out.merge(
            home,
            on="user_id",
            how="left",
            validate="one_to_one",
        )

    if independent_secondary_evidence is not None and not independent_secondary_evidence.empty:
        independent = _one_row_per_user(
            independent_secondary_evidence,
            "independent_secondary_evidence",
        )
        keep_independent = ["user_id"]
        for column in (
            "valid_evidence_axes",
            "top1_evidence_axes",
            "beats_peer_median_axes",
            "comparator_anchor_count",
        ):
            if column in independent.columns:
                keep_independent.append(column)
        out = out.merge(
            independent[keep_independent],
            on="user_id",
            how="left",
            validate="one_to_one",
        )

    out["home_context_supported"] = (
        out.get("home_tier", pd.Series(index=out.index, dtype=object))
        .fillna("")
        .astype(str)
        .str.lower()
        .isin({"high", "medium"})
    )
    out["stable_shifted_candidate"] = _bool_series(
        out, "stable_shifted_candidate"
    )
    out["mobile_work_like_candidate"] = _bool_series(
        out, "mobile_work_like_candidate"
    )
    out["has_repeated_edge"] = _bool_series(out, "has_repeated_edge")
    out["window_pattern"] = (
        out.get("window_pattern", pd.Series(index=out.index, dtype=object))
        .fillna("insufficient")
        .astype(str)
    )
    out["anchor_count_class"] = (
        out["anchor_count_class"].fillna("unknown").astype(str)
    )

    # Explicit evidence flags used by the deterministic taxonomy.
    out["stable_single_secondary"] = out["window_pattern"].eq(
        "stable_secondary_anchor"
    )
    out["multi_anchor_state"] = (
        out["window_pattern"].eq("multi_anchor")
        | out["anchor_count_class"].eq("multiple_anchor")
    )
    out["unstable_state"] = out["window_pattern"].eq("unstable")
    out["route_recurrence_evidence"] = out["has_repeated_edge"]
    out["mobile_complexity_evidence"] = out["mobile_work_like_candidate"]
    out["independent_secondary_evidence_available"] = _numeric_series(
        out, "valid_evidence_axes"
    ).fillna(0).gt(0)

    return out.sort_values("user_id").reset_index(drop=True)


def assign_work_regimes(evidence: pd.DataFrame) -> pd.DataFrame:
    """Assign descriptive regimes using only previously defined evidence states."""
    out = _one_row_per_user(evidence, "evidence").copy()

    required = {
        "stable_single_secondary",
        "multi_anchor_state",
        "unstable_state",
        "stable_shifted_candidate",
        "mobile_complexity_evidence",
        "route_recurrence_evidence",
    }
    missing = required.difference(out.columns)
    if missing:
        raise ValueError(f"evidence missing required columns: {sorted(missing)}")

    shifted_fixed = (
        out["stable_single_secondary"].fillna(False).astype(bool)
        & out["stable_shifted_candidate"].fillna(False).astype(bool)
    )
    regular_fixed = (
        out["stable_single_secondary"].fillna(False).astype(bool)
        & ~out["stable_shifted_candidate"].fillna(False).astype(bool)
    )
    route_mobile = (
        out["mobile_complexity_evidence"].fillna(False).astype(bool)
        & out["route_recurrence_evidence"].fillna(False).astype(bool)
        & out["multi_anchor_state"].fillna(False).astype(bool)
    )
    multi_site = (
        out["multi_anchor_state"].fillna(False).astype(bool)
        & out["route_recurrence_evidence"].fillna(False).astype(bool)
    )
    irregular = (
        out["unstable_state"].fillna(False).astype(bool)
        | (
            out["multi_anchor_state"].fillna(False).astype(bool)
            & ~out["route_recurrence_evidence"].fillna(False).astype(bool)
        )
        | (
            out["mobile_complexity_evidence"].fillna(False).astype(bool)
            & ~out["route_recurrence_evidence"].fillna(False).astype(bool)
        )
    )

    # Precedence matters: route-centric is a more specific multi-anchor state;
    # shifted fixed-site is a more specific stable-single-secondary state.
    out["work_regime"] = np.select(
        [
            route_mobile,
            shifted_fixed,
            regular_fixed,
            multi_site,
            irregular,
        ],
        [
            "route_centric_mobile_like",
            "shifted_fixed_site_like",
            "fixed_site_like",
            "multi_site_recurring",
            "irregular",
        ],
        default="insufficient",
    )
    out["work_representation"] = out["work_regime"].map(WORK_REPRESENTATION)

    out["regime_evidence_axes"] = (
        out[
            [
                "stable_single_secondary",
                "multi_anchor_state",
                "stable_shifted_candidate",
                "mobile_complexity_evidence",
                "route_recurrence_evidence",
                "unstable_state",
            ]
        ]
        .fillna(False)
        .astype(bool)
        .sum(axis=1)
        .astype(int)
    )

    out["semantic_claim_allowed"] = False
    out["occupation_inference_allowed"] = False
    return out


def summarize_archetypes(archetypes: pd.DataFrame) -> pd.DataFrame:
    if archetypes.empty:
        return pd.DataFrame(
            columns=[
                "work_regime",
                "users",
                "home_context_supported_share",
                "repeated_route_share",
                "independent_secondary_evidence_share",
                "median_regime_evidence_axes",
            ]
        )

    rows = []
    for regime, group in archetypes.groupby("work_regime", sort=True):
        rows.append(
            {
                "work_regime": str(regime),
                "users": int(group["user_id"].nunique()),
                "home_context_supported_share": float(
                    group["home_context_supported"].fillna(False).astype(bool).mean()
                ),
                "repeated_route_share": float(
                    group["route_recurrence_evidence"].fillna(False).astype(bool).mean()
                ),
                "independent_secondary_evidence_share": float(
                    group["independent_secondary_evidence_available"]
                    .fillna(False)
                    .astype(bool)
                    .mean()
                ),
                "median_regime_evidence_axes": float(
                    pd.to_numeric(
                        group["regime_evidence_axes"], errors="coerce"
                    ).median()
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_representations(archetypes: pd.DataFrame) -> pd.DataFrame:
    if archetypes.empty:
        return pd.DataFrame(columns=["work_representation", "users"])
    return (
        archetypes.groupby("work_representation", as_index=False)
        .agg(users=("user_id", "nunique"))
        .sort_values(["users", "work_representation"], ascending=[False, True])
        .reset_index(drop=True)
    )


def summarize_upstream_overlap(archetypes: pd.DataFrame) -> pd.DataFrame:
    """Show how the new taxonomy composes, rather than replaces, upstream states."""
    rows = []
    flags = (
        "stable_single_secondary",
        "multi_anchor_state",
        "stable_shifted_candidate",
        "mobile_complexity_evidence",
        "route_recurrence_evidence",
        "home_context_supported",
        "independent_secondary_evidence_available",
    )
    for regime, group in archetypes.groupby("work_regime", sort=True):
        base = {
            "work_regime": str(regime),
            "users": int(group["user_id"].nunique()),
        }
        for flag in flags:
            base[f"{flag}_users"] = int(
                group[flag].fillna(False).astype(bool).sum()
            )
        rows.append(base)
    return pd.DataFrame(rows)


def summarize_evidence(archetypes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for regime, group in archetypes.groupby("work_regime", sort=True):
        rows.append(
            {
                "work_regime": str(regime),
                "users": int(group["user_id"].nunique()),
                "median_distinct_edges": (
                    float(_numeric_series(group, "distinct_edges").median())
                    if "distinct_edges" in group
                    else np.nan
                ),
                "median_edge_entropy": (
                    float(_numeric_series(group, "edge_entropy").median())
                    if "edge_entropy" in group
                    else np.nan
                ),
                "median_repeated_edges": (
                    float(_numeric_series(group, "repeated_edges").median())
                    if "repeated_edges" in group
                    else np.nan
                ),
                "median_dominant_window_share": (
                    float(_numeric_series(group, "dominant_window_share").median())
                    if "dominant_window_share" in group
                    else np.nan
                ),
                "median_top1_independent_axes": (
                    float(_numeric_series(group, "top1_evidence_axes").median())
                    if "top1_evidence_axes" in group
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def run_audit(
    behavior_features: pd.DataFrame,
    work_patterns: pd.DataFrame,
    routine_users: pd.DataFrame,
    home_evidence: pd.DataFrame | None = None,
    independent_secondary_evidence: pd.DataFrame | None = None,
) -> WorkRegimeAudit:
    evidence = build_evidence_matrix(
        behavior_features,
        work_patterns,
        routine_users,
        home_evidence=home_evidence,
        independent_secondary_evidence=independent_secondary_evidence,
    )
    archetypes = assign_work_regimes(evidence)
    return WorkRegimeAudit(
        evidence_matrix=evidence,
        archetypes=archetypes,
        archetype_summary=summarize_archetypes(archetypes),
        representation_summary=summarize_representations(archetypes),
        upstream_overlap=summarize_upstream_overlap(archetypes),
        evidence_summary=summarize_evidence(archetypes),
    )


def synthetic_self_check() -> dict[str, object]:
    behavior = pd.DataFrame(
        [
            {
                "user_id": "fixed",
                "anchor_count_class": "two_anchor",
                "stable_shifted_candidate": False,
                "mobile_work_like_candidate": False,
            },
            {
                "user_id": "shift",
                "anchor_count_class": "two_anchor",
                "stable_shifted_candidate": True,
                "mobile_work_like_candidate": False,
            },
            {
                "user_id": "route",
                "anchor_count_class": "multiple_anchor",
                "stable_shifted_candidate": False,
                "mobile_work_like_candidate": True,
            },
            {
                "user_id": "multi",
                "anchor_count_class": "multiple_anchor",
                "stable_shifted_candidate": False,
                "mobile_work_like_candidate": False,
            },
            {
                "user_id": "irregular",
                "anchor_count_class": "multiple_anchor",
                "stable_shifted_candidate": False,
                "mobile_work_like_candidate": True,
            },
        ]
    )
    work = pd.DataFrame(
        [
            {"user_id": "fixed", "window_pattern": "stable_secondary_anchor"},
            {"user_id": "shift", "window_pattern": "stable_secondary_anchor"},
            {"user_id": "route", "window_pattern": "multi_anchor"},
            {"user_id": "multi", "window_pattern": "multi_anchor"},
            {"user_id": "irregular", "window_pattern": "unstable"},
        ]
    )
    routine = pd.DataFrame(
        [
            {"user_id": "fixed", "has_repeated_edge": True},
            {"user_id": "shift", "has_repeated_edge": True},
            {"user_id": "route", "has_repeated_edge": True},
            {"user_id": "multi", "has_repeated_edge": True},
            {"user_id": "irregular", "has_repeated_edge": False},
        ]
    )
    result = run_audit(behavior, work, routine).archetypes.set_index("user_id")
    assert result.loc["fixed", "work_regime"] == "fixed_site_like"
    assert result.loc["shift", "work_regime"] == "shifted_fixed_site_like"
    assert result.loc["route", "work_regime"] == "route_centric_mobile_like"
    assert result.loc["multi", "work_regime"] == "multi_site_recurring"
    assert result.loc["irregular", "work_regime"] == "irregular"
    assert not result["occupation_inference_allowed"].any()
    return {
        "users": int(len(result)),
        "regimes": sorted(result["work_regime"].unique().tolist()),
        "status": "ok",
    }
