"""Stage 05b: HOME consensus tiers and adaptive secondary-anchor audit.

This module consumes the private Stage-05 reliability outputs. It does not
treat any heuristic as HOME/WORK ground truth and does not modify production
inference.

HOME:
- combine candidate convergence with split, held-out and dropout evidence;
- expose transparent evidence tiers rather than calibrated confidence.

WORK-like secondary-anchor audit:
- exclude a HOME consensus anchor;
- rank recurring secondary anchors in sliding calendar windows;
- do not use a fixed clock window to select the anchor;
- report persistence, switching and learned arrival-time concentration.
"""

from __future__ import annotations

from collections import Counter
from typing import Iterable

import numpy as np
import pandas as pd


def _local_wall_series(values: pd.Series) -> pd.Series:
    """Normalize mixed tz-aware timestamps to naive per-stay local wall clock."""
    normalized = []
    for value in values:
        ts = pd.Timestamp(value)
        if pd.isna(ts):
            normalized.append(pd.NaT)
        elif ts.tzinfo is not None:
            normalized.append(ts.tz_localize(None))
        else:
            normalized.append(ts)
    return pd.Series(normalized, index=values.index, dtype="datetime64[ns]")

METHOD_FIXED = "fixed_window"
METHOD_HOWDE = "howde_style"
METHOD_RECURRENCE = "recurrence"
METHODS = (METHOD_FIXED, METHOD_HOWDE, METHOD_RECURRENCE)

HOME_LABEL = "HOME"
OFFICE_LABEL = "OFFICE"

HOME_TIER_HIGH = "high"
HOME_TIER_MEDIUM = "medium"
HOME_TIER_UNCERTAIN = "uncertain"

PRIMARY_DROPOUT_RATE = 0.30
PRIMARY_WORK_WINDOW_DAYS = 42
PRIMARY_WORK_STEP_DAYS = 14
MIN_WORK_OBSERVED_DAYS = 6
MIN_WORK_CANDIDATE_DAYS = 3
MIN_WORK_CANDIDATE_STAYS = 2

WORK_PATTERN_COLUMNS = [
    "user_id",
    "home_tier",
    "window_days",
    "eligible_windows",
    "candidate_windows",
    "candidate_window_share",
    "distinct_top_locations",
    "dominant_location_id",
    "dominant_window_share",
    "second_location_window_share",
    "switch_count",
    "longest_run_windows",
    "longest_run_share",
    "median_visit_day_share",
    "median_arrival_hour_concentration",
    "median_dominant_hour_shift_h",
    "window_pattern",
]


def _empty_work_patterns() -> pd.DataFrame:
    return pd.DataFrame(columns=WORK_PATTERN_COLUMNS)


def _method_list(values: pd.Series) -> tuple[str, ...]:
    order = {method: index for index, method in enumerate(METHODS)}
    unique = sorted(set(map(str, values)), key=lambda value: order.get(value, 99))
    return tuple(unique)


def _circular_hour_stats(values: pd.Series) -> tuple[float, float]:
    """Return circular mean hour and resultant concentration in [0, 1]."""
    numeric = pd.to_numeric(values, errors="coerce").dropna().to_numpy(dtype=float)
    if numeric.size == 0:
        return np.nan, np.nan
    theta = 2.0 * np.pi * (numeric % 24.0) / 24.0
    mean_sin = float(np.mean(np.sin(theta)))
    mean_cos = float(np.mean(np.cos(theta)))
    concentration = float(np.hypot(mean_sin, mean_cos))
    angle = float(np.arctan2(mean_sin, mean_cos))
    if angle < 0:
        angle += 2.0 * np.pi
    center_hour = 24.0 * angle / (2.0 * np.pi)
    return center_hour, concentration


def _circular_hour_distance(left: float, right: float) -> float:
    if not np.isfinite(left) or not np.isfinite(right):
        return np.nan
    delta = abs(float(left) - float(right)) % 24.0
    return min(delta, 24.0 - delta)


def _split_confirmation(
    split_details: pd.DataFrame,
    *,
    user_id: str,
    location_id: int,
    methods: set[str],
) -> tuple[int, int, tuple[str, ...]]:
    if split_details.empty:
        return 0, 0, tuple()

    subset = split_details.loc[
        split_details["user_id"].astype(str).eq(str(user_id))
        & split_details["label"].eq(HOME_LABEL)
        & split_details["method"].isin(methods)
    ].copy()
    if subset.empty:
        return 0, 0, tuple()

    confirmed = subset.loc[
        subset["location_id_left"].eq(location_id)
        & subset["location_id_right"].eq(location_id)
    ].copy()

    axes = int(confirmed["split"].nunique()) if not confirmed.empty else 0
    confirming_methods = (
        _method_list(confirmed["method"]) if not confirmed.empty else tuple()
    )
    return axes, len(confirming_methods), confirming_methods


def _holdout_confirmation(
    holdout_details: pd.DataFrame,
    *,
    user_id: str,
    location_id: int,
    methods: set[str],
) -> tuple[int, int, tuple[str, ...], tuple[str, ...]]:
    if holdout_details.empty:
        return 0, 0, tuple(), tuple()

    subset = holdout_details.loc[
        holdout_details["user_id"].astype(str).eq(str(user_id))
        & holdout_details["label"].eq(HOME_LABEL)
        & holdout_details["method"].isin(methods)
        & holdout_details["location_id"].eq(location_id)
    ].copy()
    if subset.empty:
        return 0, 0, tuple(), tuple()

    seen = subset.loc[subset["seen_in_holdout"].fillna(False).astype(bool)]
    top1 = subset.loc[subset["heldout_top1"].fillna(False).astype(bool)]

    seen_methods = _method_list(seen["method"]) if not seen.empty else tuple()
    top1_methods = _method_list(top1["method"]) if not top1.empty else tuple()
    return len(seen_methods), len(top1_methods), seen_methods, top1_methods


def _dropout_confirmation(
    dropout_details: pd.DataFrame,
    *,
    user_id: str,
    location_id: int,
    methods: set[str],
    dropout_rate: float,
) -> tuple[int, tuple[str, ...], float]:
    if dropout_details.empty:
        return 0, tuple(), np.nan

    rate = pd.to_numeric(dropout_details["dropout_rate"], errors="coerce")
    subset = dropout_details.loc[
        dropout_details["user_id"].astype(str).eq(str(user_id))
        & dropout_details["label"].eq(HOME_LABEL)
        & dropout_details["method"].isin(methods)
        & dropout_details["location_id_reference"].eq(location_id)
        & np.isclose(rate, dropout_rate)
    ].copy()
    if subset.empty:
        return 0, tuple(), np.nan

    per_method = (
        subset.groupby("method", as_index=False)
        .agg(
            retention=("candidate_retained", "mean"),
            seeds=("seed", "nunique"),
        )
    )
    supported = per_method.loc[per_method["retention"].ge(2.0 / 3.0)]
    supported_methods = (
        _method_list(supported["method"]) if not supported.empty else tuple()
    )
    mean_retention = float(per_method["retention"].mean())
    return len(supported_methods), supported_methods, mean_retention


def build_home_consensus(
    assignments: pd.DataFrame,
    split_details: pd.DataFrame,
    holdout_details: pd.DataFrame,
    dropout_details: pd.DataFrame,
    *,
    dropout_rate: float = PRIMARY_DROPOUT_RATE,
) -> pd.DataFrame:
    """Build candidate-level HOME evidence and transparent consensus tiers.

    high:
        unique vote winner, >=2 methods agree, and all three reliability axes
        have at least one confirming method.

    medium:
        unique vote winner, >=2 methods agree, and at least two of the three
        reliability axes have confirming evidence.

    uncertain:
        everything else.

    The tier is an audit summary, not semantic accuracy or calibrated confidence.
    """
    required = {
        "user_id",
        "method",
        "label",
        "location_id",
        "emitted",
    }
    missing = required.difference(assignments.columns)
    if missing:
        raise ValueError(f"assignments missing required columns: {sorted(missing)}")

    home = assignments.loc[assignments["label"].eq(HOME_LABEL)].copy()
    if home.empty:
        return pd.DataFrame()

    grouped_rows = []
    for (user_id, location_id), group in home.groupby(
        ["user_id", "location_id"], sort=True
    ):
        methods = _method_list(group["method"])
        method_set = set(methods)
        fixed = group.loc[group["method"].eq(METHOD_FIXED)]
        grouped_rows.append(
            {
                "user_id": str(user_id),
                "location_id": int(location_id),
                "method_votes": int(len(methods)),
                "methods": "|".join(methods),
                "fixed_selected": bool(not fixed.empty),
                "fixed_emitted": bool(
                    not fixed.empty and fixed["emitted"].fillna(False).astype(bool).any()
                ),
                "howde_selected": METHOD_HOWDE in method_set,
                "recurrence_selected": METHOD_RECURRENCE in method_set,
            }
        )

    evidence = pd.DataFrame(grouped_rows)
    evidence["max_method_votes"] = evidence.groupby("user_id")["method_votes"].transform(
        "max"
    )
    evidence["top_vote_candidate"] = evidence["method_votes"].eq(
        evidence["max_method_votes"]
    )
    top_counts = (
        evidence.loc[evidence["top_vote_candidate"]]
        .groupby("user_id")["location_id"]
        .transform("size")
    )
    evidence["unique_vote_winner"] = False
    evidence.loc[evidence["top_vote_candidate"], "unique_vote_winner"] = (
        top_counts.to_numpy() == 1
    )

    extra_rows = []
    for row in evidence.itertuples(index=False):
        methods = set(str(row.methods).split("|")) if row.methods else set()

        split_axes, split_method_count, split_methods = _split_confirmation(
            split_details,
            user_id=row.user_id,
            location_id=int(row.location_id),
            methods=methods,
        )
        (
            holdout_seen_count,
            holdout_top1_count,
            holdout_seen_methods,
            holdout_top1_methods,
        ) = _holdout_confirmation(
            holdout_details,
            user_id=row.user_id,
            location_id=int(row.location_id),
            methods=methods,
        )
        (
            dropout_method_count,
            dropout_methods,
            dropout_mean_retention,
        ) = _dropout_confirmation(
            dropout_details,
            user_id=row.user_id,
            location_id=int(row.location_id),
            methods=methods,
            dropout_rate=dropout_rate,
        )

        reliability_axes = int(split_axes > 0) + int(holdout_top1_count > 0) + int(
            dropout_method_count > 0
        )

        if (
            bool(row.unique_vote_winner)
            and int(row.method_votes) >= 2
            and reliability_axes == 3
        ):
            tier = HOME_TIER_HIGH
        elif (
            bool(row.unique_vote_winner)
            and int(row.method_votes) >= 2
            and reliability_axes >= 2
        ):
            tier = HOME_TIER_MEDIUM
        else:
            tier = HOME_TIER_UNCERTAIN

        if bool(row.fixed_emitted):
            production_status = "baseline_emitted"
        elif bool(row.fixed_selected):
            production_status = "fixed_candidate_not_emitted"
        else:
            production_status = "outside_fixed_candidate"

        extra_rows.append(
            {
                "split_axes_confirmed": int(split_axes),
                "split_confirming_method_count": int(split_method_count),
                "split_confirming_methods": "|".join(split_methods),
                "holdout_seen_method_count": int(holdout_seen_count),
                "holdout_top1_method_count": int(holdout_top1_count),
                "holdout_seen_methods": "|".join(holdout_seen_methods),
                "holdout_top1_methods": "|".join(holdout_top1_methods),
                "dropout30_confirming_method_count": int(dropout_method_count),
                "dropout30_confirming_methods": "|".join(dropout_methods),
                "dropout30_mean_retention": dropout_mean_retention,
                "reliability_axes": int(reliability_axes),
                "home_tier": tier,
                "production_status": production_status,
                "expansion_candidate": bool(
                    tier in {HOME_TIER_HIGH, HOME_TIER_MEDIUM}
                    and production_status != "baseline_emitted"
                ),
            }
        )

    out = pd.concat(
        [evidence.reset_index(drop=True), pd.DataFrame(extra_rows)],
        axis=1,
    )
    return out.sort_values(
        ["user_id", "method_votes", "location_id"],
        ascending=[True, False, True],
        kind="stable",
    ).reset_index(drop=True)


def home_consensus_winners(evidence: pd.DataFrame) -> pd.DataFrame:
    if evidence.empty:
        return evidence.copy()
    return evidence.loc[evidence["unique_vote_winner"]].copy().reset_index(drop=True)


def summarize_home_consensus(evidence: pd.DataFrame) -> dict[str, pd.DataFrame]:
    winners = home_consensus_winners(evidence)
    if winners.empty:
        empty = pd.DataFrame()
        return {
            "tier_summary": empty,
            "production_summary": empty,
            "vote_summary": empty,
            "expansion_summary": empty,
        }

    tier_summary = (
        winners.groupby("home_tier", as_index=False)
        .agg(
            users=("user_id", "nunique"),
            median_method_votes=("method_votes", "median"),
            median_reliability_axes=("reliability_axes", "median"),
        )
        .sort_values("home_tier", kind="stable")
    )

    production_summary = (
        winners.groupby(["home_tier", "production_status"], as_index=False)
        .agg(users=("user_id", "nunique"))
    )

    vote_summary = (
        winners.groupby(["method_votes", "home_tier"], as_index=False)
        .agg(users=("user_id", "nunique"))
    )

    expansion = winners.loc[winners["expansion_candidate"]]
    expansion_summary = (
        expansion.groupby(["home_tier", "production_status"], as_index=False)
        .agg(users=("user_id", "nunique"))
        if not expansion.empty
        else pd.DataFrame(
            columns=["home_tier", "production_status", "users"]
        )
    )
    return {
        "tier_summary": tier_summary,
        "production_summary": production_summary,
        "vote_summary": vote_summary,
        "expansion_summary": expansion_summary,
    }


def _location_window_stats(
    frame: pd.DataFrame,
    *,
    observed_days: int,
) -> pd.DataFrame:
    if frame.empty:
        return pd.DataFrame()

    work = frame.copy()
    work["arrival_time_local"] = _local_wall_series(work["arrival_time_local"])
    work["local_date"] = work["arrival_time_local"].dt.date
    work["arrival_hour"] = (
        work["arrival_time_local"].dt.hour
        + work["arrival_time_local"].dt.minute / 60.0
        + work["arrival_time_local"].dt.second / 3600.0
    )

    rows = []
    total_dwell_s = float(work["duration_s"].sum())
    for location_id, group in work.groupby("location_id", sort=True):
        center, concentration = _circular_hour_stats(group["arrival_hour"])
        active_days = int(group["local_date"].nunique())
        dwell_s = float(group["duration_s"].sum())
        rows.append(
            {
                "location_id": int(location_id),
                "stay_count": int(len(group)),
                "active_days": active_days,
                "visit_day_share": (
                    float(active_days / observed_days) if observed_days > 0 else 0.0
                ),
                "dwell_s": dwell_s,
                "dwell_share_nonhome": (
                    float(dwell_s / total_dwell_s) if total_dwell_s > 0 else 0.0
                ),
                "arrival_hour_center": center,
                "arrival_hour_concentration": concentration,
            }
        )
    return pd.DataFrame(rows)


def build_adaptive_work_windows(
    semantic_stays: pd.DataFrame,
    home_evidence: pd.DataFrame,
    *,
    window_days: int = PRIMARY_WORK_WINDOW_DAYS,
    step_days: int = PRIMARY_WORK_STEP_DAYS,
    min_observed_days: int = MIN_WORK_OBSERVED_DAYS,
    min_candidate_days: int = MIN_WORK_CANDIDATE_DAYS,
    min_candidate_stays: int = MIN_WORK_CANDIDATE_STAYS,
    accepted_home_tiers: Iterable[str] = (HOME_TIER_HIGH, HOME_TIER_MEDIUM),
) -> pd.DataFrame:
    """Track recurring non-HOME anchors in sliding windows.

    Selection is schedule-light: no 9–17 or other fixed clock range is used to
    choose the secondary anchor. Arrival-time center/concentration are measured
    after selection as descriptive schedule evidence.
    """
    if semantic_stays.empty or home_evidence.empty:
        return pd.DataFrame()

    accepted = set(accepted_home_tiers)
    homes = home_consensus_winners(home_evidence)
    homes = homes.loc[
        homes["home_tier"].isin(accepted) & homes["method_votes"].ge(2),
        ["user_id", "location_id", "home_tier"],
    ].rename(columns={"location_id": "home_location_id"})
    if homes.empty:
        return pd.DataFrame()

    stays = semantic_stays.copy()
    stays["user_id"] = stays["user_id"].astype(str)
    stays["arrival_time_local"] = _local_wall_series(stays["arrival_time_local"])
    stays["local_date"] = stays["arrival_time_local"].dt.date

    rows = []
    for home in homes.itertuples(index=False):
        user = stays.loc[stays["user_id"].eq(str(home.user_id))].copy()
        if user.empty:
            continue

        # Preserve the timezone carried by production semantic stays.
        min_date = pd.Timestamp(user["arrival_time_local"].min()).normalize()
        max_date = pd.Timestamp(user["arrival_time_local"].max()).normalize()
        starts = list(
            pd.date_range(
                min_date,
                max_date,
                freq=f"{int(step_days)}D",
            )
        )
        if not starts:
            starts = [min_date]

        for window_index, start in enumerate(starts):
            end = start + pd.Timedelta(days=int(window_days))
            window = user.loc[
                (user["arrival_time_local"] >= start)
                & (user["arrival_time_local"] < end)
            ].copy()

            observed_days = int(window["local_date"].nunique())
            if observed_days < min_observed_days:
                continue

            nonhome = window.loc[
                window["location_id"].ne(int(home.home_location_id))
            ].copy()
            stats = _location_window_stats(nonhome, observed_days=observed_days)

            base = {
                "user_id": str(home.user_id),
                "home_location_id": int(home.home_location_id),
                "home_tier": str(home.home_tier),
                "window_index": int(window_index),
                "window_start": start.date(),
                "window_end": (end - pd.Timedelta(days=1)).date(),
                "observed_stay_days": observed_days,
                "window_days": int(window_days),
                "step_days": int(step_days),
            }

            if stats.empty:
                rows.append(
                    {
                        **base,
                        "top_location_id": pd.NA,
                        "top_active_days": 0,
                        "top_visit_day_share": 0.0,
                        "top_dwell_share_nonhome": 0.0,
                        "top_stay_count": 0,
                        "top_arrival_hour_center": np.nan,
                        "top_arrival_hour_concentration": np.nan,
                        "second_visit_day_share": 0.0,
                        "visit_day_share_margin": 0.0,
                    }
                )
                continue

            eligible = stats.loc[
                stats["active_days"].ge(min_candidate_days)
                & stats["stay_count"].ge(min_candidate_stays)
            ].copy()

            if eligible.empty:
                rows.append(
                    {
                        **base,
                        "top_location_id": pd.NA,
                        "top_active_days": 0,
                        "top_visit_day_share": 0.0,
                        "top_dwell_share_nonhome": 0.0,
                        "top_stay_count": 0,
                        "top_arrival_hour_center": np.nan,
                        "top_arrival_hour_concentration": np.nan,
                        "second_visit_day_share": 0.0,
                        "visit_day_share_margin": 0.0,
                    }
                )
                continue

            eligible = eligible.sort_values(
                [
                    "active_days",
                    "visit_day_share",
                    "dwell_s",
                    "stay_count",
                    "location_id",
                ],
                ascending=[False, False, False, False, True],
                kind="stable",
            )
            top = eligible.iloc[0]
            second_share = (
                float(eligible.iloc[1]["visit_day_share"])
                if len(eligible) > 1
                else 0.0
            )

            rows.append(
                {
                    **base,
                    "top_location_id": int(top["location_id"]),
                    "top_active_days": int(top["active_days"]),
                    "top_visit_day_share": float(top["visit_day_share"]),
                    "top_dwell_share_nonhome": float(top["dwell_share_nonhome"]),
                    "top_stay_count": int(top["stay_count"]),
                    "top_arrival_hour_center": float(top["arrival_hour_center"]),
                    "top_arrival_hour_concentration": float(
                        top["arrival_hour_concentration"]
                    ),
                    "second_visit_day_share": second_share,
                    "visit_day_share_margin": float(
                        top["visit_day_share"] - second_share
                    ),
                }
            )

    return pd.DataFrame(rows)


def _longest_run(values: list[int]) -> int:
    if not values:
        return 0
    longest = current = 1
    for previous, value in zip(values, values[1:]):
        if value == previous:
            current += 1
            longest = max(longest, current)
        else:
            current = 1
    return int(longest)


def summarize_adaptive_work_patterns(
    windows: pd.DataFrame,
    *,
    stability_threshold: float = 0.70,
) -> pd.DataFrame:
    """Summarize sliding-window secondary-anchor persistence per user."""
    if windows.empty:
        return _empty_work_patterns()

    rows = []
    for user_id, group in windows.groupby("user_id", sort=True):
        ordered = group.sort_values("window_start", kind="stable").copy()
        candidate = ordered.loc[ordered["top_location_id"].notna()].copy()

        eligible_windows = int(len(ordered))
        candidate_windows = int(len(candidate))
        candidate_window_share = (
            float(candidate_windows / eligible_windows)
            if eligible_windows > 0
            else 0.0
        )

        if candidate.empty:
            rows.append(
                {
                    "user_id": str(user_id),
                    "home_tier": str(ordered["home_tier"].iloc[0]),
                    "window_days": int(ordered["window_days"].iloc[0]),
                    "eligible_windows": eligible_windows,
                    "candidate_windows": 0,
                    "candidate_window_share": candidate_window_share,
                    "distinct_top_locations": 0,
                    "dominant_location_id": pd.NA,
                    "dominant_window_share": np.nan,
                    "second_location_window_share": np.nan,
                    "switch_count": 0,
                    "longest_run_windows": 0,
                    "longest_run_share": np.nan,
                    "median_visit_day_share": np.nan,
                    "median_arrival_hour_concentration": np.nan,
                    "median_dominant_hour_shift_h": np.nan,
                    "window_pattern": "insufficient",
                }
            )
            continue

        locations = candidate["top_location_id"].astype(int).tolist()
        counts = Counter(locations)
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        dominant_location, dominant_count = ranked[0]
        second_count = ranked[1][1] if len(ranked) > 1 else 0
        dominant_share = float(dominant_count / candidate_windows)
        second_share = float(second_count / candidate_windows)
        switch_count = int(
            sum(left != right for left, right in zip(locations, locations[1:]))
        )
        longest_run = _longest_run(locations)

        dominant_windows = candidate.loc[
            candidate["top_location_id"].astype(int).eq(int(dominant_location))
        ].sort_values("window_start", kind="stable")
        centers = pd.to_numeric(
            dominant_windows["top_arrival_hour_center"], errors="coerce"
        ).dropna().tolist()
        center_shifts = [
            _circular_hour_distance(left, right)
            for left, right in zip(centers, centers[1:])
        ]
        valid_shifts = [value for value in center_shifts if np.isfinite(value)]

        if eligible_windows < 3 or candidate_windows < 2:
            pattern = "insufficient"
        elif dominant_share >= stability_threshold:
            pattern = "stable_secondary_anchor"
        elif len(ranked) >= 2 and second_count >= 2:
            pattern = "multi_anchor"
        else:
            pattern = "unstable"

        rows.append(
            {
                "user_id": str(user_id),
                "home_tier": str(ordered["home_tier"].iloc[0]),
                "window_days": int(ordered["window_days"].iloc[0]),
                "eligible_windows": eligible_windows,
                "candidate_windows": candidate_windows,
                "candidate_window_share": candidate_window_share,
                "distinct_top_locations": int(len(counts)),
                "dominant_location_id": int(dominant_location),
                "dominant_window_share": dominant_share,
                "second_location_window_share": second_share,
                "switch_count": switch_count,
                "longest_run_windows": longest_run,
                "longest_run_share": float(longest_run / candidate_windows),
                "median_visit_day_share": float(
                    candidate["top_visit_day_share"].median()
                ),
                "median_arrival_hour_concentration": float(
                    candidate["top_arrival_hour_concentration"].median()
                ),
                "median_dominant_hour_shift_h": (
                    float(np.median(valid_shifts)) if valid_shifts else np.nan
                ),
                "window_pattern": pattern,
            }
        )

    return pd.DataFrame(rows)


def compare_work_patterns_to_static(
    patterns: pd.DataFrame,
    assignments: pd.DataFrame,
) -> pd.DataFrame:
    """Compare dominant sliding-window secondary anchors to static OFFICE candidates."""
    if patterns.empty:
        return patterns.copy()

    office = assignments.loc[assignments["label"].eq(OFFICE_LABEL)].copy()
    static = office.pivot_table(
        index="user_id",
        columns="method",
        values="location_id",
        aggfunc="first",
    ).reset_index()
    emitted = office.loc[
        office["method"].eq(METHOD_FIXED) & office["emitted"].fillna(False).astype(bool),
        ["user_id", "location_id"],
    ].rename(columns={"location_id": "baseline_emitted_office_location_id"})

    out = patterns.merge(static, on="user_id", how="left").merge(
        emitted, on="user_id", how="left"
    )
    for method in METHODS:
        if method not in out.columns:
            out[method] = np.nan
        out[f"dominant_matches_{method}"] = (
            out["dominant_location_id"].notna()
            & out[method].notna()
            & out["dominant_location_id"].astype("Int64").eq(
                pd.to_numeric(out[method], errors="coerce").astype("Int64")
            )
        )

    out["dominant_matches_baseline_emitted_office"] = (
        out["dominant_location_id"].notna()
        & out["baseline_emitted_office_location_id"].notna()
        & out["dominant_location_id"].astype("Int64").eq(
            pd.to_numeric(
                out["baseline_emitted_office_location_id"], errors="coerce"
            ).astype("Int64")
        )
    )
    return out


def adaptive_work_sensitivity(
    semantic_stays: pd.DataFrame,
    home_evidence: pd.DataFrame,
    assignments: pd.DataFrame,
    *,
    window_days_values: Iterable[int] = (28, 42, 56),
    stability_thresholds: Iterable[float] = (0.60, 0.70, 0.80),
    step_days: int = PRIMARY_WORK_STEP_DAYS,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    window_frames = []
    summary_rows = []

    for window_days in window_days_values:
        windows = build_adaptive_work_windows(
            semantic_stays,
            home_evidence,
            window_days=int(window_days),
            step_days=step_days,
        )
        if not windows.empty:
            windows = windows.assign(window_days_setting=int(window_days))
            window_frames.append(windows)

        for threshold in stability_thresholds:
            patterns = summarize_adaptive_work_patterns(
                windows,
                stability_threshold=float(threshold),
            )
            compared = compare_work_patterns_to_static(patterns, assignments)
            if compared.empty:
                continue

            stable = compared["window_pattern"].eq("stable_secondary_anchor")
            sufficient = compared["window_pattern"].ne("insufficient")
            comparable_fixed = (
                sufficient & pd.to_numeric(compared.get(METHOD_FIXED), errors="coerce").notna()
            )
            summary_rows.append(
                {
                    "window_days": int(window_days),
                    "stability_threshold": float(threshold),
                    "users": int(compared["user_id"].nunique()),
                    "sufficient_users": int(sufficient.sum()),
                    "stable_secondary_anchor_users": int(stable.sum()),
                    "multi_anchor_users": int(
                        compared["window_pattern"].eq("multi_anchor").sum()
                    ),
                    "unstable_users": int(
                        compared["window_pattern"].eq("unstable").sum()
                    ),
                    "median_dominant_window_share": float(
                        pd.to_numeric(
                            compared.loc[sufficient, "dominant_window_share"],
                            errors="coerce",
                        ).median()
                    )
                    if sufficient.any()
                    else np.nan,
                    "fixed_office_comparable_users": int(comparable_fixed.sum()),
                    "dominant_matches_fixed_share": float(
                        compared.loc[
                            comparable_fixed,
                            "dominant_matches_fixed_window",
                        ].mean()
                    )
                    if comparable_fixed.any()
                    else np.nan,
                }
            )

    all_windows = (
        pd.concat(window_frames, ignore_index=True)
        if window_frames
        else pd.DataFrame()
    )
    return pd.DataFrame(summary_rows), all_windows


def synthetic_self_check() -> dict[str, object]:
    """Deterministic checks for HOME tiering and sliding-window switching."""
    assignments = pd.DataFrame(
        [
            {"user_id": "u1", "method": METHOD_FIXED, "label": HOME_LABEL, "location_id": 0, "score": 0.8, "support_days": 10, "emitted": False},
            {"user_id": "u1", "method": METHOD_HOWDE, "label": HOME_LABEL, "location_id": 0, "score": 0.7, "support_days": 10, "emitted": False},
            {"user_id": "u1", "method": METHOD_RECURRENCE, "label": HOME_LABEL, "location_id": 0, "score": 0.6, "support_days": 10, "emitted": False},
        ]
    )
    split_details = pd.DataFrame(
        [
            {"user_id": "u1", "method": METHOD_FIXED, "label": HOME_LABEL, "location_id_left": 0, "location_id_right": 0, "split": "first_second"},
            {"user_id": "u1", "method": METHOD_HOWDE, "label": HOME_LABEL, "location_id_left": 0, "location_id_right": 0, "split": "odd_even"},
        ]
    )
    holdout_details = pd.DataFrame(
        [
            {"user_id": "u1", "method": METHOD_FIXED, "label": HOME_LABEL, "location_id": 0, "seen_in_holdout": True, "heldout_top1": True},
        ]
    )
    dropout_details = pd.DataFrame(
        [
            {"user_id": "u1", "method": METHOD_FIXED, "label": HOME_LABEL, "location_id_reference": 0, "dropout_rate": 0.30, "seed": seed, "candidate_retained": True}
            for seed in (11, 23, 42)
        ]
    )
    evidence = build_home_consensus(
        assignments,
        split_details,
        holdout_details,
        dropout_details,
    )
    winner = home_consensus_winners(evidence).iloc[0]
    assert winner["home_tier"] == HOME_TIER_HIGH

    tz = "Asia/Shanghai"
    rows = []
    start = pd.Timestamp("2026-01-01", tz=tz)
    for day_idx in range(120):
        day = start + pd.Timedelta(days=day_idx)
        rows.append(
            {
                "user_id": "u1",
                "location_id": 0,
                "arrival_time_local": day,
                "departure_time_local": day + pd.Timedelta(hours=6),
                "duration_s": 6 * 3600,
                "latitude": 39.9,
                "longitude": 116.4,
            }
        )
        if day_idx % 2 == 0:
            secondary = 1 if day_idx < 60 else 2
            rows.append(
                {
                    "user_id": "u1",
                    "location_id": secondary,
                    "arrival_time_local": day + pd.Timedelta(hours=10),
                    "departure_time_local": day + pd.Timedelta(hours=16),
                    "duration_s": 6 * 3600,
                    "latitude": 39.91 + 0.01 * secondary,
                    "longitude": 116.41 + 0.01 * secondary,
                }
            )
    stays = pd.DataFrame(rows)
    windows = build_adaptive_work_windows(
        stays,
        evidence,
        window_days=28,
        step_days=14,
        min_observed_days=6,
    )
    patterns = summarize_adaptive_work_patterns(windows, stability_threshold=0.70)
    assert not windows.empty
    assert not patterns.empty
    assert int(patterns.iloc[0]["distinct_top_locations"]) >= 2

    return {
        "home_tier": str(winner["home_tier"]),
        "adaptive_windows": int(len(windows)),
        "distinct_secondary_anchors": int(
            patterns.iloc[0]["distinct_top_locations"]
        ),
        "status": "ok",
    }
