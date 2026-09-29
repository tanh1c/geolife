"""Observation-support-controlled audit for the frozen 03b A/B cohort."""

from __future__ import annotations

import argparse
import json
import os
import zipfile
from collections import Counter
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pandas as pd


BASE03A_PATH = Path("analysis/03a_user_behavior_deep_dive.py")
BASE03B_PATH = Path("analysis/03b_mobile_work_hypothesis_audit.py")
ARTIFACT_DIR = Path("artifacts/03b1")
EXPECTED_PARITY = {
    "candidates": 23,
    "multiple_anchor": 23,
    "office_abstained": 23,
    "office_emitted": 0,
}
MOBILITY_METRICS = [
    "cleaned_distance_km",
    "movement_duration_proxy_h",
    "boundary_count",
    "stay_count",
    "recurring_location_count",
]
ROUTE_METRICS = [
    "transition_count_per_day",
    "distinct_edge_count_per_day",
    "recurrent_edge_count_per_day",
    "edge_entropy",
    "top_edge_frequency",
]
MOTORIZED_MODES = {"bus", "car", "taxi", "subway", "train", "motorcycle"}
ACTIVE_MODES = {"walk", "bike", "run"}


def _load_module(name: str, path: Path) -> object:
    spec = spec_from_file_location(name, path)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _private_root(root: Path) -> Path:
    configured = os.environ.get("GEOLIFE_03B1_CACHE_DIR")
    private = (
        Path(configured).expanduser()
        if configured
        else root / ARTIFACT_DIR
    ).resolve()
    private.mkdir(parents=True, exist_ok=True)
    return private


def _prepare_frozen_groups(base03a: object, base03b: object, zip_path: Path, root: Path):
    stays, point_days = base03b._materialize_with_private_cache(base03a, zip_path, root)
    with zipfile.ZipFile(zip_path) as archive:
        release_users = base03a._release_users(archive)

    baseline = base03a.build_baseline_user_audit(release_users, stays)
    resolved = base03a.resolve_stay_timezones(stays).dropna(subset=["timezone_id"])
    clustered, _ = base03a.cluster_behavior_locations(resolved, 200.0)
    daily = base03b._local_daily(base03a, clustered, point_days)

    features = base03a.build_user_behavior_features(
        clustered,
        base03a._point_days_for_behavior(point_days),
    )
    features = base03a._enrich_features(
        features,
        daily,
        base03a.compute_schedule_stability(daily),
        baseline,
    )
    candidates = base03a.assign_behavioral_candidates(features)
    office = baseline.loc[baseline["label"].eq("OFFICE")]
    group_a = set(candidates.loc[candidates["mobile_work_like_candidate"], "user_id"])
    parity = {
        "candidates": len(group_a),
        "multiple_anchor": int(
            candidates.loc[
                candidates["user_id"].isin(group_a), "recurring_location_count"
            ].ge(3).sum()
        ),
        "office_abstained": int(
            office.loc[
                office["user_id"].isin(group_a), "reject_reason"
            ].ne("emitted").sum()
        ),
        "office_emitted": int(
            office.loc[
                office["user_id"].isin(group_a), "reject_reason"
            ].eq("emitted").sum()
        ),
    }
    assert parity == EXPECTED_PARITY

    matched = base03b.match_office_abstained_controls(candidates, baseline)
    assert len(matched) == 23
    assert matched["candidate_user_id"].nunique() == 23
    assert matched["control_user_id"].nunique() == 23
    return clustered, daily, matched, parity


def _sample_equalized_days(
    daily: pd.DataFrame,
    left_user: str,
    right_user: str,
    *,
    quality_column: str,
    rng: np.random.Generator,
):
    source = daily.loc[daily[quality_column]].copy()
    left = source.loc[source["user_id"].eq(left_user)].copy()
    right = source.loc[source["user_id"].eq(right_user)].copy()
    left["_is_weekday"] = left["local_weekday"].lt(5)
    right["_is_weekday"] = right["local_weekday"].lt(5)

    left_parts = []
    right_parts = []
    for is_weekday in (True, False):
        left_stratum = left.loc[left["_is_weekday"].eq(is_weekday)]
        right_stratum = right.loc[right["_is_weekday"].eq(is_weekday)]
        n = min(len(left_stratum), len(right_stratum))
        if n == 0:
            continue
        left_idx = rng.choice(left_stratum.index.to_numpy(), size=n, replace=False)
        right_idx = rng.choice(right_stratum.index.to_numpy(), size=n, replace=False)
        left_parts.append(left_stratum.loc[left_idx])
        right_parts.append(right_stratum.loc[right_idx])

    left_sample = pd.concat(left_parts, ignore_index=True) if left_parts else left.iloc[0:0].copy()
    right_sample = (\n        pd.concat(right_parts, ignore_index=True)\n        if right_parts\n        else right.iloc[0:0].copy()\n    )
    return (
        left_sample.drop(columns=["_is_weekday"], errors="ignore"),
        right_sample.drop(columns=["_is_weekday"], errors="ignore"),
    )


def _mean_day_metrics(days: pd.DataFrame) -> dict[str, float]:
    result = {}
    for metric in MOBILITY_METRICS:
        values = pd.to_numeric(days.get(metric), errors="coerce")
        result[metric] = float(values.mean()) if len(values) else float("nan")
    return result


def _day_edge_table(clustered: pd.DataFrame, daily: pd.DataFrame) -> pd.DataFrame:
    usable = daily.loc[
        daily["usable_for_motif"],
        ["user_id", "local_date", "local_weekday"],
    ].drop_duplicates()
    source = clustered.merge(usable, on=["user_id", "local_date"], how="inner")
    rows = []
    for (user_id, local_date), day in source.groupby(["user_id", "local_date"], sort=True):
        locations = (
            day.sort_values("arrival_time_local", kind="stable")["location_id"]
            .astype(int)
            .tolist()
        )
        edges = [
            f"L{left}->L{right}"
            for left, right in zip(locations, locations[1:], strict=False)
            if left != right
        ]
        rows.append(
            {
                "user_id": user_id,
                "local_date": local_date,
                "local_weekday": int(day["local_weekday"].iloc[0]),
                "edge_counts": dict(Counter(edges)),
            }
        )
    return pd.DataFrame(
        rows,
        columns=["user_id", "local_date", "local_weekday", "edge_counts"],
    )


def _sample_equalized_edge_days(
    edge_days: pd.DataFrame,
    left_user: str,
    right_user: str,
    *,
    rng: np.random.Generator,
):
    left = edge_days.loc[edge_days["user_id"].eq(left_user)].copy()
    right = edge_days.loc[edge_days["user_id"].eq(right_user)].copy()
    left["_is_weekday"] = left["local_weekday"].lt(5)
    right["_is_weekday"] = right["local_weekday"].lt(5)

    left_parts = []
    right_parts = []
    for is_weekday in (True, False):
        left_stratum = left.loc[left["_is_weekday"].eq(is_weekday)]
        right_stratum = right.loc[right["_is_weekday"].eq(is_weekday)]
        n = min(len(left_stratum), len(right_stratum))
        if n == 0:
            continue
        left_idx = rng.choice(left_stratum.index.to_numpy(), size=n, replace=False)
        right_idx = rng.choice(right_stratum.index.to_numpy(), size=n, replace=False)
        left_parts.append(left_stratum.loc[left_idx])
        right_parts.append(right_stratum.loc[right_idx])

    left_sample = pd.concat(left_parts, ignore_index=True) if left_parts else left.iloc[0:0].copy()
    right_sample = pd.concat(right_parts, ignore_index=True) if right_parts else right.iloc[0:0].copy()
    return (
        left_sample.drop(columns=["_is_weekday"], errors="ignore"),
        right_sample.drop(columns=["_is_weekday"], errors="ignore"),
    )


def _route_metrics(days: pd.DataFrame) -> dict[str, float]:
    n_days = len(days)
    if n_days == 0:
        return {metric: float("nan") for metric in ROUTE_METRICS}

    counts = Counter()
    edge_days = Counter()
    for mapping in days["edge_counts"]:
        mapping = mapping if isinstance(mapping, dict) else {}
        counts.update(mapping)
        edge_days.update(mapping.keys())

    total = sum(counts.values())
    distinct = len(counts)
    recurrent = sum(day_count >= 2 for day_count in edge_days.values())
    if total:
        shares = np.asarray(list(counts.values()), dtype=float) / total
        entropy = float(-(shares * np.log2(shares)).sum())
        top_frequency = float(shares.max())
    else:
        entropy = 0.0
        top_frequency = 0.0

    return {
        "transition_count_per_day": float(total / n_days),
        "distinct_edge_count_per_day": float(distinct / n_days),
        "recurrent_edge_count_per_day": float(recurrent / n_days),
        "edge_entropy": entropy,
        "top_edge_frequency": top_frequency,
    }


def _paired_bootstrap(
    daily: pd.DataFrame,
    edge_days: pd.DataFrame,
    matched: pd.DataFrame,
    *,
    seed: int,
    n_bootstraps: int,
):
    rng = np.random.default_rng(seed)
    mobility_rows = []
    route_rows = []
    support_rows = []

    for pair_index, pair in enumerate(matched.itertuples(index=False), start=1):
        left_user = str(pair.candidate_user_id)
        right_user = str(pair.control_user_id)
        left_temporal = daily.loc[
            daily["user_id"].eq(left_user) & daily["usable_for_temporal_profile"]
        ]
        right_temporal = daily.loc[
            daily["user_id"].eq(right_user) & daily["usable_for_temporal_profile"]
        ]
        left_motif = edge_days.loc[edge_days["user_id"].eq(left_user)]
        right_motif = edge_days.loc[edge_days["user_id"].eq(right_user)]

        support_rows.append(
            {
                "pair_index": pair_index,
                "candidate_user_id": left_user,
                "control_user_id": right_user,
                "candidate_temporal_days": len(left_temporal),
                "control_temporal_days": len(right_temporal),
                "candidate_motif_days": len(left_motif),
                "control_motif_days": len(right_motif),
            }
        )

        for bootstrap_index in range(n_bootstraps):
            left_days, right_days = _sample_equalized_days(
                daily,
                left_user,
                right_user,
                quality_column="usable_for_temporal_profile",
                rng=rng,
            )
            if len(left_days) and len(left_days) == len(right_days):
                left_metrics = _mean_day_metrics(left_days)
                right_metrics = _mean_day_metrics(right_days)
                for metric in MOBILITY_METRICS:
                    mobility_rows.append(
                        {
                            "pair_index": pair_index,
                            "bootstrap": bootstrap_index,
                            "metric": metric,
                            "controlled_days": len(left_days),
                            "candidate_value": left_metrics[metric],
                            "control_value": right_metrics[metric],
                            "difference": left_metrics[metric] - right_metrics[metric],
                        }
                    )

            left_route, right_route = _sample_equalized_edge_days(
                edge_days,
                left_user,
                right_user,
                rng=rng,
            )
            if len(left_route) >= 2 and len(left_route) == len(right_route):
                left_metrics = _route_metrics(left_route)
                right_metrics = _route_metrics(right_route)
                for metric in ROUTE_METRICS:
                    route_rows.append(
                        {
                            "pair_index": pair_index,
                            "bootstrap": bootstrap_index,
                            "metric": metric,
                            "controlled_days": len(left_route),
                            "candidate_value": left_metrics[metric],
                            "control_value": right_metrics[metric],
                            "difference": left_metrics[metric] - right_metrics[metric],
                        }
                    )

    return pd.DataFrame(mobility_rows), pd.DataFrame(route_rows), pd.DataFrame(support_rows)


def _bootstrap_summary(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(
            columns=[
                "metric",
                "eligible_pairs",
                "controlled_days_median",
                "paired_difference_median",
                "ci95_low",
                "ci95_high",
                "probability_difference_gt_0",
            ]
        )

    replicate = (
        rows.groupby(["metric", "bootstrap"], as_index=False)
        .agg(
            paired_difference=("difference", "median"),
            eligible_pairs=("pair_index", "nunique"),
            controlled_days=("controlled_days", "median"),
        )
    )
    result = []
    for metric, group in replicate.groupby("metric", sort=True):
        diffs = pd.to_numeric(group["paired_difference"], errors="coerce").dropna()
        result.append(
            {
                "metric": metric,
                "eligible_pairs": int(group["eligible_pairs"].median()),
                "controlled_days_median": float(group["controlled_days"].median()),
                "paired_difference_median": float(diffs.median()) if len(diffs) else np.nan,
                "ci95_low": float(diffs.quantile(0.025)) if len(diffs) else np.nan,
                "ci95_high": float(diffs.quantile(0.975)) if len(diffs) else np.nan,
                "probability_difference_gt_0": float((diffs > 0).mean()) if len(diffs) else np.nan,
            }
        )
    return pd.DataFrame(result)


def _sample_to_duration(
    segments: pd.DataFrame,
    target_s: float,
    *,
    rng: np.random.Generator,
) -> pd.DataFrame:
    if target_s <= 0 or segments.empty:
        return segments.iloc[0:0].copy()

    source = segments.copy()
    source["duration_s"] = (
        pd.to_datetime(source["end_time"], utc=True)
        - pd.to_datetime(source["start_time"], utc=True)
    ).dt.total_seconds()
    source = source.loc[source["duration_s"].gt(0)].copy()
    if source.empty:
        return source

    order = rng.permutation(len(source))
    remaining = float(target_s)
    rows = []
    for position in order:
        row = source.iloc[int(position)].copy()
        duration = float(row["duration_s"])
        if remaining <= 0:
            break
        used = min(duration, remaining)
        fraction = used / duration
        row["duration_s"] = used
        row["distance_m"] = float(row["distance_m"]) * fraction
        rows.append(row)
        remaining -= used
    return pd.DataFrame(rows)


def _transport_metrics(segments: pd.DataFrame) -> dict[str, float]:
    if segments.empty:
        return {
            "distance_km_per_hour": float("nan"),
            "motorized_distance_share": float("nan"),
            "active_distance_share": float("nan"),
        }
    duration_h = float(segments["duration_s"].sum() / 3600)
    total_distance = float(segments["distance_m"].sum())
    mode = segments["mode"].astype(str).str.lower()
    return {
        "distance_km_per_hour": (
            total_distance / 1000 / duration_h if duration_h > 0 else float("nan")
        ),
        "motorized_distance_share": (
            float(segments.loc[mode.isin(MOTORIZED_MODES), "distance_m"].sum() / total_distance)
            if total_distance > 0
            else 0.0
        ),
        "active_distance_share": (
            float(segments.loc[mode.isin(ACTIVE_MODES), "distance_m"].sum() / total_distance)
            if total_distance > 0
            else 0.0
        ),
    }


def _transport_bootstrap(
    base03a: object,
    base03b: object,
    zip_path: Path,
    matched: pd.DataFrame,
    private_03b_root: Path,
    *,
    seed: int,
    n_bootstraps: int,
    min_hours: float,
):
    users = set(matched["candidate_user_id"]) | set(matched["control_user_id"])
    labels = base03b._mode_labels(zip_path, users)
    windows = base03b.canonicalize_mode_windows(labels)
    segments = base03b._cleaned_mode_segments(
        base03a,
        zip_path,
        users,
        windows,
        private_03b_root / "mode_segment_cache",
    )
    if segments.empty:
        return pd.DataFrame(), pd.DataFrame()

    segments = segments.copy()
    segments["duration_s"] = (
        pd.to_datetime(segments["end_time"], utc=True)
        - pd.to_datetime(segments["start_time"], utc=True)
    ).dt.total_seconds()

    rng = np.random.default_rng(seed + 100003)
    rows = []
    support_rows = []
    metrics = ["distance_km_per_hour", "motorized_distance_share", "active_distance_share"]

    for pair_index, pair in enumerate(matched.itertuples(index=False), start=1):
        left = segments.loc[segments["user_id"].eq(pair.candidate_user_id)]
        right = segments.loc[segments["user_id"].eq(pair.control_user_id)]
        left_h = float(left["duration_s"].sum() / 3600) if len(left) else 0.0
        right_h = float(right["duration_s"].sum() / 3600) if len(right) else 0.0
        target_h = min(left_h, right_h)

        support_rows.append(
            {
                "pair_index": pair_index,
                "candidate_user_id": pair.candidate_user_id,
                "control_user_id": pair.control_user_id,
                "candidate_labeled_h": left_h,
                "control_labeled_h": right_h,
                "controlled_labeled_h": target_h,
                "eligible": target_h >= min_hours,
            }
        )
        if target_h < min_hours:
            continue

        target_s = target_h * 3600
        for bootstrap_index in range(n_bootstraps):
            left_sample = _sample_to_duration(left, target_s, rng=rng)
            right_sample = _sample_to_duration(right, target_s, rng=rng)
            left_metrics = _transport_metrics(left_sample)
            right_metrics = _transport_metrics(right_sample)
            for metric in metrics:
                rows.append(
                    {
                        "pair_index": pair_index,
                        "bootstrap": bootstrap_index,
                        "metric": metric,
                        "controlled_hours": target_h,
                        "candidate_value": left_metrics[metric],
                        "control_value": right_metrics[metric],
                        "difference": left_metrics[metric] - right_metrics[metric],
                    }
                )
    return pd.DataFrame(rows), pd.DataFrame(support_rows)


def _transport_summary(rows: pd.DataFrame) -> pd.DataFrame:
    if rows.empty:
        return pd.DataFrame(
            columns=[
                "metric",
                "eligible_pairs",
                "controlled_hours_median",
                "paired_difference_median",
                "ci95_low",
                "ci95_high",
                "probability_difference_gt_0",
            ]
        )
    replicate = (
        rows.groupby(["metric", "bootstrap"], as_index=False)
        .agg(
            paired_difference=("difference", "median"),
            eligible_pairs=("pair_index", "nunique"),
            controlled_hours=("controlled_hours", "median"),
        )
    )
    result = []
    for metric, group in replicate.groupby("metric", sort=True):
        diffs = group["paired_difference"].dropna()
        result.append(
            {
                "metric": metric,
                "eligible_pairs": int(group["eligible_pairs"].median()),
                "controlled_hours_median": float(group["controlled_hours"].median()),
                "paired_difference_median": float(diffs.median()) if len(diffs) else np.nan,
                "ci95_low": float(diffs.quantile(0.025)) if len(diffs) else np.nan,
                "ci95_high": float(diffs.quantile(0.975)) if len(diffs) else np.nan,
                "probability_difference_gt_0": float((diffs > 0).mean()) if len(diffs) else np.nan,
            }
        )
    return pd.DataFrame(result)


def _signal_status(summary: pd.DataFrame, metrics: list[str]) -> dict[str, str]:
    rows = summary.set_index("metric") if not summary.empty else pd.DataFrame()
    result = {}
    for metric in metrics:
        if rows.empty or metric not in rows.index:
            result[metric] = "unavailable"
            continue
        row = rows.loc[metric]
        low = float(row["ci95_low"])
        high = float(row["ci95_high"])
        if low > 0:
            result[metric] = "A_higher"
        elif high < 0:
            result[metric] = "B_higher"
        else:
            result[metric] = "overlaps_zero"
    return result


def _render_report(summary: dict[str, object]) -> str:
    mobility = pd.DataFrame(summary.get("mobility_summary", []))
    route = pd.DataFrame(summary.get("route_summary", []))
    transport = pd.DataFrame(summary.get("transport_summary", []))
    support = summary.get("support", {})

    def table(frame: pd.DataFrame) -> str:
        if frame.empty:
            return "_No eligible evidence._"
        columns = [
            column
            for column in [
                "metric",
                "eligible_pairs",
                "controlled_days_median",
                "controlled_hours_median",
                "paired_difference_median",
                "ci95_low",
                "ci95_high",
                "probability_difference_gt_0",
            ]
            if column in frame.columns
        ]
        shown = frame.loc[:, columns].copy()
        for column in shown.select_dtypes(include=[np.number]).columns:
            shown[column] = shown[column].map(
                lambda value: "" if pd.isna(value) else f"{float(value):.4f}"
            )
        header = "| " + " | ".join(columns) + " |"
        separator = "| " + " | ".join(["---"] * len(columns)) + " |"
        rows = [
            "| " + " | ".join(str(row[column]) for column in columns) + " |"
            for _, row in shown.iterrows()
        ]
        return "\n".join([header, separator, *rows])

    next_step = summary.get(\n        "next_step",\n        "Review the controlled evidence before changing production or notebook-03 semantics.",\n    )\n\n    return f"""# 03b.1 Observation-support-controlled audit

## Status
Research-only follow-up to 03b. No production Home/Office rule, occupation label,\nor semantic work-role classifier is created.

## Question
03b found a robust 23-user Group A cohort, but Group A had substantially denser\nobservation support than matched Group B.

After forcing each A/B pair to contribute the same amount of usable observation\nexposure, do descriptive mobility and independent route differences persist?

## Frozen parity
The input cohort remains 23 / 23 / 23 / 0 for candidates / multiple-anchor /\nOFFICE-abstained / OFFICE-emitted.

## Exposure-control design
- matched A/B pairs: {support.get("matched_pairs", "n/a")};
- bootstrap repetitions: {summary.get("n_bootstraps", "n/a")};
- temporal days are downsampled within each pair and within weekday/weekend strata;
- route evidence is separately downsampled on usable-for-motif days;
- transportation evidence, where both members have labels, is controlled to the\n  same matched labeled hours.

The sampling changes exposure, not the frozen candidate definition.

## Mobility results
These metrics are descriptive and overlap with candidate construction. They test\nobservation confounding but are not independent semantic validation.

{table(mobility)}

## Route / transition results
These are the main support-controlled independent structure checks.

{table(route)}

## Transportation-mode results
Only pairs with enough labeled exposure on both sides are included. Mode-transition\ncounts are intentionally omitted because segment resampling breaks temporal ordering.

{table(transport)}

## Signal status
Route: {summary.get("route_signal_status", {})}

Transport: {summary.get("transport_signal_status", {})}

## Interpretation
{summary.get("interpretation", "not evaluated")}

A persistent difference after exposure control means richer observation alone does\nnot fully explain that measured difference. It still does not establish a semantic\ndistributed/mobile-work class.

## What cannot be concluded
- no candidate is proven to be a mobile worker;
- no occupation is inferred;
- no OFFICE ground truth exists in GeoLife;
- construction-overlapping mobility metrics are not treated as independent validation;
- sparse transportation labels remain auxiliary evidence.

## Decision
{summary.get("decision", "semantic decision deferred")}

## Next step
{next_step}
"""


def run_audit(
    zip_path: Path,
    root: Path,
    *,
    seed: int,
    n_bootstraps: int,
    min_transport_hours: float,
) -> dict[str, object]:
    base03a = _load_module("behavior_03a_03b1", BASE03A_PATH)
    base03b = _load_module("behavior_03b_03b1", BASE03B_PATH)
    clustered, daily, matched, parity = _prepare_frozen_groups(
        base03a, base03b, zip_path, root
    )
    edge_days = _day_edge_table(clustered, daily)

    mobility_rows, route_rows, support_rows = _paired_bootstrap(
        daily,
        edge_days,
        matched,
        seed=seed,
        n_bootstraps=n_bootstraps,
    )
    mobility_summary = _bootstrap_summary(mobility_rows)
    route_summary = _bootstrap_summary(route_rows)

    private = _private_root(root)
    configured_03b = os.environ.get("GEOLIFE_03B_CACHE_DIR")
    private_03b = (
        Path(configured_03b).expanduser().resolve()
        if configured_03b
        else (root / "artifacts" / "03b").resolve()
    )
    transport_rows, transport_support = _transport_bootstrap(
        base03a,
        base03b,
        zip_path,
        matched,
        private_03b,
        seed=seed,
        n_bootstraps=n_bootstraps,
        min_hours=min_transport_hours,
    )
    transport_summary = _transport_summary(transport_rows)

    route_status = _signal_status(route_summary, ROUTE_METRICS)
    transport_status = _signal_status(
        transport_summary,
        ["distance_km_per_hour", "motorized_distance_share", "active_distance_share"],
    )
    primary_route = [
        route_status.get("transition_count_per_day"),
        route_status.get("edge_entropy"),
        route_status.get("recurrent_edge_count_per_day"),
    ]
    positive_route = sum(status == "A_higher" for status in primary_route)
    if positive_route >= 2:
        interpretation = (
            "At least two predeclared route-structure metrics remain higher in "
            "Group A after equalizing usable-day exposure. Observation density "
            "alone therefore does not fully explain the descriptive route difference."
        )
    elif all(status == "overlaps_zero" for status in primary_route):
        interpretation = (
            "The primary route-structure differences overlap zero after exposure "
            "control. Observation density is a plausible explanation for much of "
            "the original A/B difference."
        )
    else:
        interpretation = (
            "Support-controlled route evidence is mixed: some differences persist "
            "while others overlap zero."
        )

    summary = {
        "run_status": "complete",
        "seed": seed,
        "n_bootstraps": n_bootstraps,
        "min_transport_hours": min_transport_hours,
        "parity": parity,
        "support": {
            "matched_pairs": int(len(matched)),
            "temporal_pairs_with_any_controlled_days": int(
                support_rows[
                    support_rows[["candidate_temporal_days", "control_temporal_days"]]
                    .min(axis=1)
                    .gt(0)
                ]["pair_index"].nunique()
            ),
            "motif_pairs_with_any_controlled_days": int(
                support_rows[
                    support_rows[["candidate_motif_days", "control_motif_days"]]
                    .min(axis=1)
                    .gt(0)
                ]["pair_index"].nunique()
            ),
            "transport_pairs_eligible": int(
                transport_support.loc[transport_support["eligible"], "pair_index"].nunique()
            )
            if not transport_support.empty
            else 0,
        },
        "mobility_summary": mobility_summary.to_dict("records"),
        "route_summary": route_summary.to_dict("records"),
        "transport_summary": transport_summary.to_dict("records"),
        "route_signal_status": route_status,
        "transport_signal_status": transport_status,
        "interpretation": interpretation,
        "decision": "semantic decision deferred",
        "next_step": (
            "Use this audit only to decide whether the 03b descriptive cohort "
            "remains worth studying after exposure control. Do not modify frozen "
            "Home/Office semantics without independent semantic validation."
        ),
    }

    support_rows.to_csv(private / "pair_support.csv", index=False)
    mobility_rows.to_csv(private / "mobility_bootstrap.csv", index=False)
    route_rows.to_csv(private / "route_bootstrap.csv", index=False)
    mobility_summary.to_csv(private / "mobility_summary.csv", index=False)
    route_summary.to_csv(private / "route_summary.csv", index=False)
    transport_support.to_csv(private / "transport_support.csv", index=False)
    transport_rows.to_csv(private / "transport_bootstrap.csv", index=False)
    transport_summary.to_csv(private / "transport_summary.csv", index=False)
    (private / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    report_path = root / "reports" / "03b1_observation_support_controlled_audit.md"
    report_path.write_text(_render_report(summary), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--n-bootstraps", type=int, default=500)
    parser.add_argument("--min-transport-hours", type=float, default=1.0)
    args = parser.parse_args()

    summary = run_audit(
        args.zip,
        Path.cwd(),
        seed=args.seed,
        n_bootstraps=args.n_bootstraps,
        min_transport_hours=args.min_transport_hours,
    )
    print("03b.1 parity:", summary["parity"])
    print("03b.1 interpretation:", summary["interpretation"])
    print("03b.1 decision:", summary["decision"])


if __name__ == "__main__":
    main()
