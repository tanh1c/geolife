"""Stage 07h: multi-source evidence triangulation for stable-secondary anchors.

This stage combines already-computed, source-native evidence from:
- Stage 05c behavioral independent-evidence audit;
- Stage 07e historical OSM context audit;
- Stage 07g BCL POI 2008 lexical-context audit.

It does not create a new semantic classifier or a WORK/OFFICE score.

The stable-secondary cohort comes from Stage 05b. Candidate location identity must
agree across all available upstream sources before any triangulation summary is
produced.
"""

from __future__ import annotations

from typing import Iterable

import numpy as np
import pandas as pd


DISTANCE_THRESHOLDS_M = (25.0, 50.0, 100.0)
BEHAVIOR_STRICT_TOP1_AXES = 3
EPS = 1e-12


def _users(frame: pd.DataFrame) -> pd.DataFrame:
    if "user_id" not in frame.columns:
        raise ValueError("frame missing user_id")
    out = frame.copy()
    out["user_id"] = out["user_id"].astype(str)
    return out


def stable_secondary_base(work_patterns: pd.DataFrame) -> pd.DataFrame:
    work = _users(work_patterns)
    required = {"window_pattern", "dominant_location_id"}
    missing = required.difference(work.columns)
    if missing:
        raise ValueError(f"work_patterns missing columns: {sorted(missing)}")

    stable = work.loc[
        work["window_pattern"].eq("stable_secondary_anchor")
        & work["dominant_location_id"].notna(),
        ["user_id", "dominant_location_id"],
    ].copy()
    stable["candidate_location_id"] = pd.to_numeric(
        stable["dominant_location_id"], errors="raise"
    ).astype(int)
    stable = stable.drop(columns=["dominant_location_id"])
    if stable["user_id"].duplicated().any():
        raise ValueError("stable-secondary cohort must contain one row per user")
    return stable.sort_values("user_id").reset_index(drop=True)


def _sign(value: object) -> str:
    if pd.isna(value):
        return "unavailable"
    number = float(value)
    if number > EPS:
        return "positive"
    if number < -EPS:
        return "negative"
    return "neutral"


def _behavior_band(row: pd.Series) -> str:
    if not bool(row["behavior_available"]):
        return "unavailable"
    top = int(row["behavior_top1_evidence_axes"])
    if top >= BEHAVIOR_STRICT_TOP1_AXES:
        return "strict"
    if top == 2:
        return "partial"
    return "weak"


def _prepare_behavior(frame: pd.DataFrame) -> pd.DataFrame:
    if frame is None or frame.empty:
        return pd.DataFrame(
            columns=[
                "user_id",
                "behavior_candidate_location_id",
                "behavior_valid_evidence_axes",
                "behavior_top1_evidence_axes",
                "behavior_beats_peer_median_axes",
            ]
        )

    behavior = _users(frame)
    required = {
        "secondary_location_id",
        "valid_evidence_axes",
        "top1_evidence_axes",
        "beats_peer_median_axes",
    }
    missing = required.difference(behavior.columns)
    if missing:
        raise ValueError(
            f"Stage-05c comparison missing columns: {sorted(missing)}"
        )
    if behavior["user_id"].duplicated().any():
        raise ValueError("Stage-05c comparison must contain one row per user")

    out = behavior[
        [
            "user_id",
            "secondary_location_id",
            "valid_evidence_axes",
            "top1_evidence_axes",
            "beats_peer_median_axes",
        ]
    ].copy()
    return out.rename(
        columns={
            "secondary_location_id": "behavior_candidate_location_id",
            "valid_evidence_axes": "behavior_valid_evidence_axes",
            "top1_evidence_axes": "behavior_top1_evidence_axes",
            "beats_peer_median_axes": "behavior_beats_peer_median_axes",
        }
    )


def _prepare_external(
    frame: pd.DataFrame,
    *,
    prefix: str,
    lexical: bool,
    thresholds_m: Iterable[float] = DISTANCE_THRESHOLDS_M,
) -> pd.DataFrame:
    if frame is None or frame.empty:
        columns = ["user_id", f"{prefix}_candidate_location_id"]
        for threshold in thresholds_m:
            value = int(threshold)
            columns.extend(
                [
                    f"{prefix}_candidate_context_{value}m",
                    f"{prefix}_peer_share_{value}m",
                    f"{prefix}_candidate_minus_peer_{value}m",
                ]
            )
        return pd.DataFrame(columns=columns)

    source = _users(frame)
    if source["user_id"].duplicated().any():
        raise ValueError(f"{prefix} comparison must contain one row per user")

    required = {"candidate_location_id"}
    for threshold in thresholds_m:
        value = int(threshold)
        if lexical:
            required.update(
                {
                    f"candidate_work_lexical_within_{value}m",
                    f"peer_share_work_lexical_within_{value}m",
                    f"candidate_minus_peer_share_{value}m",
                }
            )
        else:
            required.update(
                {
                    f"candidate_work_within_{value}m",
                    f"peer_share_work_within_{value}m",
                    f"candidate_minus_peer_share_{value}m",
                }
            )
    missing = required.difference(source.columns)
    if missing:
        raise ValueError(
            f"{prefix} comparison missing columns: {sorted(missing)}"
        )

    out = pd.DataFrame(
        {
            "user_id": source["user_id"],
            f"{prefix}_candidate_location_id": pd.to_numeric(
                source["candidate_location_id"], errors="raise"
            ).astype(int),
        }
    )
    for threshold in thresholds_m:
        value = int(threshold)
        if lexical:
            candidate = f"candidate_work_lexical_within_{value}m"
            peer = f"peer_share_work_lexical_within_{value}m"
        else:
            candidate = f"candidate_work_within_{value}m"
            peer = f"peer_share_work_within_{value}m"
        diff = f"candidate_minus_peer_share_{value}m"

        out[f"{prefix}_candidate_context_{value}m"] = (
            source[candidate].fillna(False).astype(bool)
        )
        out[f"{prefix}_peer_share_{value}m"] = pd.to_numeric(
            source[peer], errors="coerce"
        )
        out[f"{prefix}_candidate_minus_peer_{value}m"] = pd.to_numeric(
            source[diff], errors="coerce"
        )
    return out


def _validate_candidate_ids(panel: pd.DataFrame) -> None:
    base = pd.to_numeric(panel["candidate_location_id"], errors="raise").astype(int)
    for column in (
        "behavior_candidate_location_id",
        "osm_candidate_location_id",
        "bcl_candidate_location_id",
    ):
        if column not in panel.columns:
            continue
        values = pd.to_numeric(panel[column], errors="coerce")
        mismatch = values.notna() & values.astype("Int64").ne(base.astype("Int64"))
        if mismatch.any():
            sample = panel.loc[
                mismatch,
                ["user_id", "candidate_location_id", column],
            ].head(5)
            raise ValueError(
                f"candidate location identity mismatch in {column}; "
                f"sample={sample.to_dict(orient='records')}"
            )


def build_user_evidence_panel(
    work_patterns: pd.DataFrame,
    behavior_comparison: pd.DataFrame,
    osm_comparison: pd.DataFrame,
    bcl_comparison: pd.DataFrame,
    *,
    thresholds_m: Iterable[float] = DISTANCE_THRESHOLDS_M,
) -> pd.DataFrame:
    """Build one row per frozen Stage-05b stable-secondary user."""
    thresholds = tuple(float(value) for value in thresholds_m)
    panel = stable_secondary_base(work_patterns)
    behavior = _prepare_behavior(behavior_comparison)
    osm = _prepare_external(
        osm_comparison,
        prefix="osm",
        lexical=False,
        thresholds_m=thresholds,
    )
    bcl = _prepare_external(
        bcl_comparison,
        prefix="bcl",
        lexical=True,
        thresholds_m=thresholds,
    )

    for source in (behavior, osm, bcl):
        panel = panel.merge(
            source,
            on="user_id",
            how="left",
            validate="one_to_one",
        )

    _validate_candidate_ids(panel)

    panel["behavior_available"] = panel[
        "behavior_candidate_location_id"
    ].notna()
    panel["osm_available"] = panel["osm_candidate_location_id"].notna()
    panel["bcl_available"] = panel["bcl_candidate_location_id"].notna()

    for column in (
        "behavior_valid_evidence_axes",
        "behavior_top1_evidence_axes",
        "behavior_beats_peer_median_axes",
    ):
        panel[column] = pd.to_numeric(panel[column], errors="coerce")

    panel["behavior_primary_support"] = (
        panel["behavior_available"]
        & panel["behavior_top1_evidence_axes"].ge(
            BEHAVIOR_STRICT_TOP1_AXES
        )
    )
    panel["behavior_band"] = panel.apply(_behavior_band, axis=1)

    for prefix in ("osm", "bcl"):
        positive_columns = []
        negative_columns = []
        for threshold in thresholds:
            value = int(threshold)
            diff_col = f"{prefix}_candidate_minus_peer_{value}m"
            sign_col = f"{prefix}_sign_{value}m"
            panel[sign_col] = panel[diff_col].map(_sign)
            positive_columns.append(panel[diff_col].gt(EPS))
            negative_columns.append(panel[diff_col].lt(-EPS))
        panel[f"{prefix}_positive_thresholds"] = pd.concat(
            positive_columns, axis=1
        ).sum(axis=1)
        panel[f"{prefix}_negative_thresholds"] = pd.concat(
            negative_columns, axis=1
        ).sum(axis=1)

    primary = int(max(thresholds))
    osm_context = panel[f"osm_candidate_context_{primary}m"].fillna(False)
    bcl_context = panel[f"bcl_candidate_context_{primary}m"].fillna(False)
    both_available = panel["osm_available"] & panel["bcl_available"]

    panel["candidate_context_pattern_100m"] = np.select(
        [
            ~both_available,
            osm_context & bcl_context,
            osm_context & ~bcl_context,
            ~osm_context & bcl_context,
        ],
        [
            "unavailable",
            "both",
            "osm_only",
            "bcl_only",
        ],
        default="neither",
    )

    panel["external_direction_pattern_100m"] = (
        "osm:"
        + panel[f"osm_sign_{primary}m"].astype(str)
        + "|bcl:"
        + panel[f"bcl_sign_{primary}m"].astype(str)
    )

    panel["external_positive_sources_100m"] = (
        panel[f"osm_candidate_minus_peer_{primary}m"].gt(EPS).astype(int)
        + panel[f"bcl_candidate_minus_peer_{primary}m"].gt(EPS).astype(int)
    )
    panel["external_negative_sources_100m"] = (
        panel[f"osm_candidate_minus_peer_{primary}m"].lt(-EPS).astype(int)
        + panel[f"bcl_candidate_minus_peer_{primary}m"].lt(-EPS).astype(int)
    )
    panel["external_both_positive_100m"] = (
        panel["osm_available"]
        & panel["bcl_available"]
        & panel["external_positive_sources_100m"].eq(2)
    )
    panel["strict_three_way_convergence_100m"] = (
        panel["behavior_primary_support"]
        & panel["external_both_positive_100m"]
    )
    panel["triangulation_signature_100m"] = (
        "behavior:"
        + panel["behavior_band"].astype(str)
        + "|"
        + panel["external_direction_pattern_100m"].astype(str)
        + "|context:"
        + panel["candidate_context_pattern_100m"].astype(str)
    )

    return panel.sort_values("user_id").reset_index(drop=True)


def summarize_source_coverage(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for source in ("behavior", "osm", "bcl"):
        available = panel[f"{source}_available"].fillna(False).astype(bool)
        rows.append(
            {
                "source": source,
                "stable_secondary_users": int(len(panel)),
                "users_available": int(available.sum()),
                "availability_share": float(available.mean())
                if len(panel)
                else np.nan,
            }
        )
    both_external = (
        panel["osm_available"].fillna(False)
        & panel["bcl_available"].fillna(False)
    )
    rows.append(
        {
            "source": "osm_and_bcl",
            "stable_secondary_users": int(len(panel)),
            "users_available": int(both_external.sum()),
            "availability_share": float(both_external.mean())
            if len(panel)
            else np.nan,
        }
    )
    all_three = both_external & panel["behavior_available"].fillna(False)
    rows.append(
        {
            "source": "behavior_osm_bcl",
            "stable_secondary_users": int(len(panel)),
            "users_available": int(all_three.sum()),
            "availability_share": float(all_three.mean())
            if len(panel)
            else np.nan,
        }
    )
    return pd.DataFrame(rows)


def summarize_external_direction(
    panel: pd.DataFrame,
    *,
    thresholds_m: Iterable[float] = DISTANCE_THRESHOLDS_M,
) -> pd.DataFrame:
    rows = []
    for threshold in thresholds_m:
        value = int(threshold)
        both = panel.loc[
            panel["osm_available"].fillna(False)
            & panel["bcl_available"].fillna(False)
        ].copy()
        osm = both[f"osm_sign_{value}m"]
        bcl = both[f"bcl_sign_{value}m"]
        rows.append(
            {
                "threshold_m": float(threshold),
                "users_with_both_sources": int(len(both)),
                "both_positive": int(
                    (osm.eq("positive") & bcl.eq("positive")).sum()
                ),
                "both_negative": int(
                    (osm.eq("negative") & bcl.eq("negative")).sum()
                ),
                "same_direction_including_neutral": int(osm.eq(bcl).sum()),
                "opposite_positive_negative": int(
                    (
                        (osm.eq("positive") & bcl.eq("negative"))
                        | (osm.eq("negative") & bcl.eq("positive"))
                    ).sum()
                ),
                "osm_positive_users": int(osm.eq("positive").sum()),
                "bcl_positive_users": int(bcl.eq("positive").sum()),
            }
        )
    return pd.DataFrame(rows)


def summarize_candidate_context_overlap(
    panel: pd.DataFrame,
    *,
    threshold_m: float = 100.0,
) -> pd.DataFrame:
    value = int(threshold_m)
    both = panel.loc[
        panel["osm_available"].fillna(False)
        & panel["bcl_available"].fillna(False)
    ].copy()
    osm = both[f"osm_candidate_context_{value}m"].fillna(False).astype(bool)
    bcl = both[f"bcl_candidate_context_{value}m"].fillna(False).astype(bool)
    rows = [
        {
            "pattern": "both",
            "users": int((osm & bcl).sum()),
        },
        {
            "pattern": "osm_only",
            "users": int((osm & ~bcl).sum()),
        },
        {
            "pattern": "bcl_only",
            "users": int((~osm & bcl).sum()),
        },
        {
            "pattern": "neither",
            "users": int((~osm & ~bcl).sum()),
        },
    ]
    out = pd.DataFrame(rows)
    out["share"] = out["users"] / max(len(both), 1)
    return out


def summarize_triangulation_signatures(panel: pd.DataFrame) -> pd.DataFrame:
    return (
        panel.groupby(
            [
                "behavior_band",
                "external_direction_pattern_100m",
                "candidate_context_pattern_100m",
            ],
            as_index=False,
            dropna=False,
        )
        .agg(users=("user_id", "nunique"))
        .sort_values(
            ["users", "behavior_band", "external_direction_pattern_100m"],
            ascending=[False, True, True],
        )
        .reset_index(drop=True)
    )


def summarize_behavior_external_relationship(panel: pd.DataFrame) -> pd.DataFrame:
    """Descriptive cross-tab; no causal or semantic interpretation."""
    return (
        panel.groupby(
            ["behavior_band", "external_positive_sources_100m"],
            as_index=False,
            dropna=False,
        )
        .agg(
            users=("user_id", "nunique"),
            median_behavior_beats_peer_axes=(
                "behavior_beats_peer_median_axes",
                "median",
            ),
        )
        .sort_values(
            ["behavior_band", "external_positive_sources_100m"]
        )
        .reset_index(drop=True)
    )


def decision_snapshot(panel: pd.DataFrame) -> pd.DataFrame:
    both_external = (
        panel["osm_available"].fillna(False)
        & panel["bcl_available"].fillna(False)
    )
    all_three = both_external & panel["behavior_available"].fillna(False)
    return pd.DataFrame(
        [
            {
                "stable_secondary_users": int(len(panel)),
                "behavior_available_users": int(
                    panel["behavior_available"].sum()
                ),
                "behavior_strict_support_users": int(
                    panel["behavior_primary_support"].sum()
                ),
                "both_external_sources_users": int(both_external.sum()),
                "all_three_sources_users": int(all_three.sum()),
                "external_both_positive_100m_users": int(
                    panel["external_both_positive_100m"].sum()
                ),
                "strict_three_way_convergence_100m_users": int(
                    panel["strict_three_way_convergence_100m"].sum()
                ),
                "candidate_context_both_sources_100m_users": int(
                    panel["candidate_context_pattern_100m"].eq("both").sum()
                ),
            }
        ]
    )


def synthetic_self_check() -> dict[str, object]:
    work = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "window_pattern": "stable_secondary_anchor",
                "dominant_location_id": 7,
            }
        ]
    )
    behavior = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "secondary_location_id": 7,
                "valid_evidence_axes": 4,
                "top1_evidence_axes": 2,
                "beats_peer_median_axes": 3,
            }
        ]
    )
    osm = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "candidate_location_id": 7,
                "candidate_work_within_25m": True,
                "peer_share_work_within_25m": 0.0,
                "candidate_minus_peer_share_25m": 1.0,
                "candidate_work_within_50m": True,
                "peer_share_work_within_50m": 0.5,
                "candidate_minus_peer_share_50m": 0.5,
                "candidate_work_within_100m": True,
                "peer_share_work_within_100m": 1.0,
                "candidate_minus_peer_share_100m": 0.0,
            }
        ]
    )
    bcl = pd.DataFrame(
        [
            {
                "user_id": "u1",
                "candidate_location_id": 7,
                "candidate_work_lexical_within_25m": False,
                "peer_share_work_lexical_within_25m": 0.0,
                "candidate_minus_peer_share_25m": 0.0,
                "candidate_work_lexical_within_50m": True,
                "peer_share_work_lexical_within_50m": 0.0,
                "candidate_minus_peer_share_50m": 1.0,
                "candidate_work_lexical_within_100m": True,
                "peer_share_work_lexical_within_100m": 0.5,
                "candidate_minus_peer_share_100m": 0.5,
            }
        ]
    )
    panel = build_user_evidence_panel(work, behavior, osm, bcl)
    assert len(panel) == 1
    assert panel.loc[0, "behavior_band"] == "partial"
    assert panel.loc[0, "osm_positive_thresholds"] == 2
    assert panel.loc[0, "bcl_positive_thresholds"] == 2
    assert not bool(panel.loc[0, "behavior_primary_support"])
    return {
        "status": "ok",
        "users": 1,
        "signature": str(panel.loc[0, "triangulation_signature_100m"]),
    }
