"""Stage 07b: factorized work-regime profiles.

Stage 07 v1 showed that site topology, route topology, schedule timing, and
mobility complexity overlap within the same users. Stage 07b therefore keeps
those dimensions separate instead of assigning one mutually-exclusive class.

This stage remains research-only. It does not infer occupation, employment
status, true workplace, or semantic POI ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

import numpy as np
import pandas as pd


CORE_BOOLEAN_AXES = (
    "site_stable_secondary",
    "site_multiple_recurring",
    "site_adaptive_multi_anchor",
    "site_unstable",
    "route_repeated",
    "schedule_shifted_evidence",
    "mobile_complexity_evidence",
    "home_context_supported",
    "independent_secondary_evidence_available",
)

REPRESENTATION_FLAGS = (
    "candidate_single_anchor_geometry",
    "candidate_anchor_set_geometry",
    "candidate_route_region_geometry",
    "schedule_agnostic_needed",
)


@dataclass(frozen=True)
class FactorizedWorkProfileAudit:
    profiles: pd.DataFrame
    support_summary: pd.DataFrame
    axis_summary: pd.DataFrame
    pairwise_overlap: pd.DataFrame
    signature_summary: pd.DataFrame
    representation_summary: pd.DataFrame


def _load_stage07():
    path = Path(__file__).with_name("07_work_regime_archetypes.py")
    spec = spec_from_file_location("stage07_base_for_07b", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load Stage 07 base from {path}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = _load_stage07()


def _numeric(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(np.nan, index=frame.index, dtype=float)
    return pd.to_numeric(frame[column], errors="coerce")


def _bool(frame: pd.DataFrame, column: str) -> pd.Series:
    if column not in frame.columns:
        return pd.Series(False, index=frame.index, dtype=bool)
    return frame[column].fillna(False).astype(bool)


def _first_existing(frame: pd.DataFrame, *columns: str) -> pd.Series:
    for column in columns:
        if column in frame.columns:
            return frame[column]
    return pd.Series(np.nan, index=frame.index)


def _route_complexity_percentile(profiles: pd.DataFrame) -> pd.Series:
    distinct = _numeric(profiles, "route_distinct_edges")
    entropy = _numeric(profiles, "route_edge_entropy")
    supported = profiles["routine_evidence_available"].fillna(False).astype(bool)

    result = pd.Series(np.nan, index=profiles.index, dtype=float)
    if not supported.any():
        return result

    d_rank = distinct.loc[supported].rank(method="average", pct=True)
    e_rank = entropy.loc[supported].rank(method="average", pct=True)
    combined = pd.concat(
        [d_rank.rename("distinct"), e_rank.rename("entropy")],
        axis=1,
    ).mean(axis=1, skipna=True)
    result.loc[combined.index] = combined
    return result


def build_factorized_profiles(
    behavior_features: pd.DataFrame,
    work_patterns: pd.DataFrame,
    routine_users: pd.DataFrame,
    home_evidence: pd.DataFrame | None = None,
    independent_secondary_evidence: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Build orthogonal evidence axes from the Stage-07 integration matrix."""
    evidence = BASE.build_evidence_matrix(
        behavior_features,
        work_patterns,
        routine_users,
        home_evidence=home_evidence,
        independent_secondary_evidence=independent_secondary_evidence,
    ).copy()

    out = pd.DataFrame({"user_id": evidence["user_id"].astype(str)})

    # Upstream-support axes.
    out["behavior_evidence_available"] = (
        evidence["anchor_count_class"].fillna("unknown").astype(str).ne("unknown")
    )
    work_support_candidates = [
        column
        for column in (
            "eligible_windows",
            "candidate_windows",
            "dominant_window_share",
            "distinct_top_locations",
        )
        if column in evidence.columns
    ]
    if work_support_candidates:
        out["work_pattern_observed"] = evidence[
            work_support_candidates
        ].notna().any(axis=1)
    else:
        out["work_pattern_observed"] = evidence["window_pattern"].ne("insufficient")

    routine_support = _first_existing(
        evidence,
        "usable_motif_days_routine",
        "distinct_edges",
        "total_transitions",
    )
    out["routine_evidence_available"] = pd.to_numeric(
        routine_support, errors="coerce"
    ).notna()
    out["home_context_supported"] = _bool(evidence, "home_context_supported")
    out["independent_secondary_evidence_available"] = _bool(
        evidence, "independent_secondary_evidence_available"
    )

    # Site / anchor structure. These are intentionally overlapping axes.
    out["anchor_count_class"] = evidence["anchor_count_class"].fillna("unknown").astype(str)
    out["adaptive_window_pattern"] = evidence["window_pattern"].fillna("insufficient").astype(str)
    out["site_stable_secondary"] = _bool(evidence, "stable_single_secondary")
    out["site_multiple_recurring"] = out["anchor_count_class"].eq("multiple_anchor")
    out["site_adaptive_multi_anchor"] = out["adaptive_window_pattern"].eq("multi_anchor")
    out["site_unstable"] = _bool(evidence, "unstable_state")
    out["site_dominant_anchor_only"] = out["anchor_count_class"].eq("dominant_anchor")
    out["site_two_anchor"] = out["anchor_count_class"].eq("two_anchor")
    out["site_no_stable_anchor"] = out["anchor_count_class"].eq("no_stable_anchor")
    out["site_distinct_top_locations"] = _numeric(evidence, "distinct_top_locations")
    out["site_dominant_window_share"] = _numeric(evidence, "dominant_window_share")
    out["site_candidate_window_share"] = _numeric(evidence, "candidate_window_share")

    # Route / OD structure.
    out["route_repeated"] = _bool(evidence, "route_recurrence_evidence")
    out["route_distinct_edges"] = _numeric(evidence, "distinct_edges")
    out["route_repeated_edges"] = _numeric(evidence, "repeated_edges")
    out["route_edge_entropy"] = _numeric(evidence, "edge_entropy")
    out["route_top_edge_day_share"] = _numeric(evidence, "top_edge_day_share")
    out["route_top_edge_transition_share"] = _numeric(
        evidence, "top_edge_transition_share"
    )
    out["route_departure_concentration"] = _numeric(
        evidence, "median_repeated_departure_concentration"
    )

    # Schedule timing.
    out["schedule_shifted_evidence"] = _bool(
        evidence, "stable_shifted_candidate"
    )
    out["schedule_arrival_concentration"] = _numeric(
        evidence, "median_arrival_hour_concentration"
    )
    out["schedule_dominant_hour_shift_h"] = _numeric(
        evidence, "median_dominant_hour_shift_h"
    )

    # Mobility complexity.
    out["mobile_complexity_evidence"] = _bool(
        evidence, "mobile_complexity_evidence"
    )
    out["movement_distance_per_usable_day_km"] = _numeric(
        evidence, "distance_per_usable_day_km"
    )
    out["movement_duration_per_usable_day_h"] = _numeric(
        evidence, "movement_proxy_per_usable_day_h"
    )

    # Independent secondary-anchor evidence remains a separate axis.
    out["independent_valid_axes"] = _numeric(evidence, "valid_evidence_axes")
    out["independent_top1_axes"] = _numeric(evidence, "top1_evidence_axes")
    out["independent_beats_peer_axes"] = _numeric(
        evidence, "beats_peer_median_axes"
    )
    out["independent_comparator_anchors"] = _numeric(
        evidence, "comparator_anchor_count"
    )

    # Descriptive relative route complexity; no semantic threshold is created.
    out["route_complexity_percentile"] = _route_complexity_percentile(out)

    # Multiple representation geometries may be simultaneously plausible.
    out["candidate_single_anchor_geometry"] = out["site_stable_secondary"]
    out["candidate_anchor_set_geometry"] = (
        out["site_multiple_recurring"] | out["site_adaptive_multi_anchor"]
    )
    out["candidate_route_region_geometry"] = (
        out["route_repeated"]
        & (
            out["mobile_complexity_evidence"]
            | out["site_multiple_recurring"]
            | out["site_adaptive_multi_anchor"]
        )
    )
    out["schedule_agnostic_needed"] = out["schedule_shifted_evidence"]

    out["representation_option_count"] = (
        out[
            [
                "candidate_single_anchor_geometry",
                "candidate_anchor_set_geometry",
                "candidate_route_region_geometry",
            ]
        ]
        .fillna(False)
        .astype(bool)
        .sum(axis=1)
        .astype(int)
    )
    out["representation_abstain"] = out["representation_option_count"].eq(0)

    def _signature(row: pd.Series) -> str:
        options = []
        if bool(row["candidate_single_anchor_geometry"]):
            options.append("single_anchor")
        if bool(row["candidate_anchor_set_geometry"]):
            options.append("anchor_set")
        if bool(row["candidate_route_region_geometry"]):
            options.append("route_region")
        if bool(row["schedule_agnostic_needed"]):
            options.append("schedule_agnostic")
        return "+".join(options) if options else "abstain"

    out["representation_signature"] = out.apply(_signature, axis=1)

    # Explicit semantic boundary.
    out["semantic_work_claim_allowed"] = False
    out["occupation_inference_allowed"] = False

    return out.sort_values("user_id").reset_index(drop=True)


def summarize_support(profiles: pd.DataFrame) -> pd.DataFrame:
    if profiles.empty:
        return pd.DataFrame(
            columns=["support_axis", "users", "share"]
        )
    rows = []
    for axis in (
        "behavior_evidence_available",
        "work_pattern_observed",
        "routine_evidence_available",
        "home_context_supported",
        "independent_secondary_evidence_available",
    ):
        values = _bool(profiles, axis)
        rows.append(
            {
                "support_axis": axis,
                "users": int(values.sum()),
                "share": float(values.mean()),
            }
        )
    return pd.DataFrame(rows)


def summarize_axes(profiles: pd.DataFrame) -> pd.DataFrame:
    if profiles.empty:
        return pd.DataFrame(
            columns=["axis", "users_true", "population_share"]
        )
    rows = []
    for axis in CORE_BOOLEAN_AXES:
        values = _bool(profiles, axis)
        rows.append(
            {
                "axis": axis,
                "users_true": int(values.sum()),
                "population_share": float(values.mean()),
            }
        )
    return pd.DataFrame(rows)


def pairwise_axis_overlap(profiles: pd.DataFrame) -> pd.DataFrame:
    """Quantify overlap instead of forcing mutually-exclusive categories."""
    rows = []
    axes = list(CORE_BOOLEAN_AXES)
    for i, left_name in enumerate(axes):
        left = _bool(profiles, left_name)
        for right_name in axes[i + 1 :]:
            right = _bool(profiles, right_name)
            intersection = int((left & right).sum())
            union = int((left | right).sum())
            left_count = int(left.sum())
            right_count = int(right.sum())
            rows.append(
                {
                    "left_axis": left_name,
                    "right_axis": right_name,
                    "left_users": left_count,
                    "right_users": right_count,
                    "intersection_users": intersection,
                    "jaccard": (
                        float(intersection / union) if union else np.nan
                    ),
                    "right_given_left": (
                        float(intersection / left_count)
                        if left_count
                        else np.nan
                    ),
                    "left_given_right": (
                        float(intersection / right_count)
                        if right_count
                        else np.nan
                    ),
                }
            )
    return pd.DataFrame(rows)


def summarize_signatures(profiles: pd.DataFrame) -> pd.DataFrame:
    if profiles.empty:
        return pd.DataFrame(
            columns=["evidence_signature", "users", "share"]
        )

    signature_axes = (
        "site_stable_secondary",
        "site_multiple_recurring",
        "route_repeated",
        "schedule_shifted_evidence",
        "mobile_complexity_evidence",
        "home_context_supported",
        "independent_secondary_evidence_available",
    )

    def _signature(row: pd.Series) -> str:
        active = [
            axis
            for axis in signature_axes
            if bool(row.get(axis, False))
        ]
        return "+".join(active) if active else "none"

    values = profiles.apply(_signature, axis=1)
    counts = values.value_counts(dropna=False)
    total = len(profiles)
    return pd.DataFrame(
        {
            "evidence_signature": counts.index.astype(str),
            "users": counts.to_numpy(dtype=int),
            "share": counts.to_numpy(dtype=float) / total,
        }
    ).reset_index(drop=True)


def summarize_representations(profiles: pd.DataFrame) -> pd.DataFrame:
    if profiles.empty:
        return pd.DataFrame(
            columns=["representation_signature", "users", "share"]
        )
    counts = profiles["representation_signature"].value_counts()
    total = len(profiles)
    return pd.DataFrame(
        {
            "representation_signature": counts.index.astype(str),
            "users": counts.to_numpy(dtype=int),
            "share": counts.to_numpy(dtype=float) / total,
        }
    ).reset_index(drop=True)


def run_audit(
    behavior_features: pd.DataFrame,
    work_patterns: pd.DataFrame,
    routine_users: pd.DataFrame,
    home_evidence: pd.DataFrame | None = None,
    independent_secondary_evidence: pd.DataFrame | None = None,
) -> FactorizedWorkProfileAudit:
    profiles = build_factorized_profiles(
        behavior_features,
        work_patterns,
        routine_users,
        home_evidence=home_evidence,
        independent_secondary_evidence=independent_secondary_evidence,
    )
    return FactorizedWorkProfileAudit(
        profiles=profiles,
        support_summary=summarize_support(profiles),
        axis_summary=summarize_axes(profiles),
        pairwise_overlap=pairwise_axis_overlap(profiles),
        signature_summary=summarize_signatures(profiles),
        representation_summary=summarize_representations(profiles),
    )


def synthetic_self_check() -> dict[str, object]:
    behavior = pd.DataFrame(
        [
            {
                "user_id": "overlap",
                "anchor_count_class": "multiple_anchor",
                "stable_shifted_candidate": True,
                "mobile_work_like_candidate": True,
            },
            {
                "user_id": "single",
                "anchor_count_class": "two_anchor",
                "stable_shifted_candidate": False,
                "mobile_work_like_candidate": False,
            },
        ]
    )
    work = pd.DataFrame(
        [
            {
                "user_id": "overlap",
                "window_pattern": "stable_secondary_anchor",
                "eligible_windows": 5,
                "candidate_windows": 5,
            },
            {
                "user_id": "single",
                "window_pattern": "stable_secondary_anchor",
                "eligible_windows": 5,
                "candidate_windows": 4,
            },
        ]
    )
    routine = pd.DataFrame(
        [
            {
                "user_id": "overlap",
                "usable_motif_days": 10,
                "has_repeated_edge": True,
                "distinct_edges": 8,
                "edge_entropy": 2.5,
            },
            {
                "user_id": "single",
                "usable_motif_days": 8,
                "has_repeated_edge": False,
                "distinct_edges": 1,
                "edge_entropy": 0.0,
            },
        ]
    )

    audit = run_audit(behavior, work, routine)
    result = audit.profiles.set_index("user_id")

    assert bool(result.loc["overlap", "site_stable_secondary"])
    assert bool(result.loc["overlap", "site_multiple_recurring"])
    assert bool(result.loc["overlap", "route_repeated"])
    assert bool(result.loc["overlap", "schedule_shifted_evidence"])
    assert bool(result.loc["overlap", "mobile_complexity_evidence"])
    assert result.loc["overlap", "representation_option_count"] == 3
    assert (
        result.loc["overlap", "representation_signature"]
        == "single_anchor+anchor_set+route_region+schedule_agnostic"
    )

    assert bool(result.loc["single", "candidate_single_anchor_geometry"])
    assert not bool(result.loc["single", "candidate_anchor_set_geometry"])
    assert not bool(result.loc["single", "candidate_route_region_geometry"])
    assert not result["occupation_inference_allowed"].any()

    return {
        "users": int(len(result)),
        "overlap_representation": str(
            result.loc["overlap", "representation_signature"]
        ),
        "status": "ok",
    }
