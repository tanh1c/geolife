"""Stage 06d: support-indexed window feasibility before change detection.

Stage 06c showed that fixed calendar windows add little usable support as the
calendar span grows. Stage 06d holds usable-day support fixed instead and
treats elapsed calendar span as an eligibility constraint.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
import pandas as pd


SUPPORT_DAYS = (6, 8, 10)
MAX_SPAN_DAYS = (56, 84)
PRIMARY_RANDOM_PARTITIONS = 200
PRIMARY_BOOTSTRAP_REPETITIONS = 300

MIN_COMPARABLE_PAIRS = 20
MIN_UNIQUE_USERS = 10
MIN_SPEARMAN = 0.50
MAX_NULL_EXCEEDANCE_SHARE = 0.10
MAX_CI_WIDTH_OVER_IQR = 1.0

PRIMARY_FEATURES = (
    "cleaned_distance_km_per_usable_day",
    "active_location_count_per_usable_day",
)


def _load_stage06c():
    path = Path(__file__).with_name(
        "06c_change_detection_representation_feasibility.py"
    )
    spec = spec_from_file_location("stage06c_base_for_06d", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load Stage 06c base from {path}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


BASE = _load_stage06c()
STABILITY_FEATURES = BASE.STABILITY_FEATURES


@dataclass(frozen=True)
class SupportWindowAudit:
    day_records: pd.DataFrame
    windows: pd.DataFrame
    coverage: pd.DataFrame
    adjacent_pairs: pd.DataFrame
    random_partition: pd.DataFrame
    test_retest: pd.DataFrame
    bootstrap: pd.DataFrame
    bootstrap_summary: pd.DataFrame
    readiness: pd.DataFrame
    exact_od_baseline: pd.DataFrame
    decision: pd.DataFrame


def _sorted_records(day_records: pd.DataFrame) -> pd.DataFrame:
    records = BASE._dates(day_records)
    records["user_id"] = records["user_id"].astype(str)
    return records.sort_values(
        ["user_id", "local_date"],
        kind="stable",
    ).reset_index(drop=True)


def _block_subset(
    records: pd.DataFrame,
    user_id: str,
    support_days: int,
    block_index: int,
) -> pd.DataFrame:
    user = records.loc[
        records["user_id"].astype(str).eq(str(user_id))
    ].sort_values("local_date", kind="stable")
    start = int(block_index) * int(support_days)
    stop = start + int(support_days)
    return user.iloc[start:stop].copy()


def build_support_windows(
    day_records: pd.DataFrame,
    *,
    support_days_values: Iterable[int] = SUPPORT_DAYS,
    max_span_days_values: Iterable[int] = MAX_SPAN_DAYS,
) -> pd.DataFrame:
    """Partition each user into non-overlapping fixed-support usable-day blocks."""
    records = _sorted_records(day_records)
    rows = []

    for user_id, user in records.groupby("user_id", sort=True):
        user = user.sort_values("local_date", kind="stable").reset_index(drop=True)

        for support_days in support_days_values:
            support_days = int(support_days)
            if support_days <= 0:
                raise ValueError("support_days must be positive")

            complete_blocks = len(user) // support_days
            for block_index in range(complete_blocks):
                start_i = block_index * support_days
                stop_i = start_i + support_days
                block = user.iloc[start_i:stop_i].copy()

                start = pd.Timestamp(block["local_date"].iloc[0])
                end = pd.Timestamp(block["local_date"].iloc[-1])
                span_days = int((end - start).days + 1)
                summary = BASE.summarize_days(
                    block,
                    calendar_window_days=max(1, span_days),
                )

                for max_span_days in max_span_days_values:
                    max_span_days = int(max_span_days)
                    if max_span_days <= 0:
                        raise ValueError("max_span_days must be positive")
                    rows.append(
                        {
                            "user_id": str(user_id),
                            "support_days": support_days,
                            "max_span_days": max_span_days,
                            "block_index": int(block_index),
                            "block_start": start.date(),
                            "block_end": end.date(),
                            "calendar_span_days": span_days,
                            "span_eligible": bool(span_days <= max_span_days),
                            "calendar_density": float(support_days / span_days),
                            **summary,
                        }
                    )

    return pd.DataFrame(rows)


def summarize_coverage(windows: pd.DataFrame) -> pd.DataFrame:
    """Summarize complete blocks, cap eligibility, and adjacent-pair coverage."""
    columns = [
        "support_days",
        "max_span_days",
        "complete_blocks",
        "eligible_blocks",
        "rejected_span_blocks",
        "users_with_complete_block",
        "users_with_eligible_block",
        "users_with_adjacent_eligible_pair",
        "adjacent_eligible_pairs",
        "median_calendar_span_eligible_block",
        "median_calendar_density_eligible_block",
    ]
    if windows.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for (support_days, max_span_days), group in windows.groupby(
        ["support_days", "max_span_days"],
        sort=True,
    ):
        eligible = group.loc[group["span_eligible"].fillna(False).astype(bool)]
        users_with_pairs = set()
        pair_count = 0

        for user_id, user in eligible.groupby("user_id", sort=True):
            indexes = set(user["block_index"].astype(int))
            pairs = sum((index + 1) in indexes for index in indexes)
            if pairs:
                users_with_pairs.add(str(user_id))
                pair_count += pairs

        rows.append(
            {
                "support_days": int(support_days),
                "max_span_days": int(max_span_days),
                "complete_blocks": int(len(group)),
                "eligible_blocks": int(len(eligible)),
                "rejected_span_blocks": int(len(group) - len(eligible)),
                "users_with_complete_block": int(group["user_id"].nunique()),
                "users_with_eligible_block": int(eligible["user_id"].nunique()),
                "users_with_adjacent_eligible_pair": int(len(users_with_pairs)),
                "adjacent_eligible_pairs": int(pair_count),
                "median_calendar_span_eligible_block": (
                    float(eligible["calendar_span_days"].median())
                    if len(eligible)
                    else np.nan
                ),
                "median_calendar_density_eligible_block": (
                    float(eligible["calendar_density"].median())
                    if len(eligible)
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows, columns=columns)


def build_adjacent_pairs(
    day_records: pd.DataFrame,
    windows: pd.DataFrame,
) -> pd.DataFrame:
    """Compare consecutive complete support blocks; never bridge an invalid block."""
    columns = [
        "user_id",
        "support_days",
        "max_span_days",
        "left_block_index",
        "right_block_index",
        "left_block_start",
        "right_block_start",
        "left_calendar_span_days",
        "right_calendar_span_days",
        "exact_edge_jsd",
    ]
    for feature in STABILITY_FEATURES:
        columns.extend([f"left__{feature}", f"right__{feature}"])

    if windows.empty:
        return pd.DataFrame(columns=columns)

    records = _sorted_records(day_records)
    eligible = windows.loc[windows["span_eligible"].fillna(False).astype(bool)]
    rows = []

    for (user_id, support_days, max_span_days), group in eligible.groupby(
        ["user_id", "support_days", "max_span_days"],
        sort=True,
    ):
        lookup = {
            int(row.block_index): row
            for row in group.itertuples(index=False)
        }
        for index in sorted(lookup):
            if index + 1 not in lookup:
                continue

            left = lookup[index]
            right = lookup[index + 1]
            left_days = _block_subset(
                records, str(user_id), int(support_days), index
            )
            right_days = _block_subset(
                records, str(user_id), int(support_days), index + 1
            )

            left_edges = Counter(
                edge for values in left_days["edges"] for edge in values
            )
            right_edges = Counter(
                edge for values in right_days["edges"] for edge in values
            )

            row = {
                "user_id": str(user_id),
                "support_days": int(support_days),
                "max_span_days": int(max_span_days),
                "left_block_index": int(index),
                "right_block_index": int(index + 1),
                "left_block_start": left.block_start,
                "right_block_start": right.block_start,
                "left_calendar_span_days": int(left.calendar_span_days),
                "right_calendar_span_days": int(right.calendar_span_days),
                "exact_edge_jsd": BASE._jsd(left_edges, right_edges),
            }
            for feature in STABILITY_FEATURES:
                row[f"left__{feature}"] = getattr(left, feature)
                row[f"right__{feature}"] = getattr(right, feature)
            rows.append(row)

    return pd.DataFrame(rows, columns=columns)


def _absdiff(left: object, right: object) -> float:
    values = pd.to_numeric(pd.Series([left, right]), errors="coerce")
    if values.isna().any():
        return np.nan
    return float(abs(values.iloc[0] - values.iloc[1]))


def random_partition_calibration(
    day_records: pd.DataFrame,
    adjacent_pairs: pd.DataFrame,
    *,
    repetitions: int = PRIMARY_RANDOM_PARTITIONS,
    seed: int = 42,
) -> pd.DataFrame:
    """Calibrate adjacent-block changes against random balanced k-vs-k splits."""
    columns = [
        "user_id",
        "support_days",
        "max_span_days",
        "left_block_index",
        "metric",
        "observed_difference",
        "random_median",
        "random_p95",
        "random_p_ge_observed",
        "observed_above_random_p95",
    ]
    if adjacent_pairs.empty:
        return pd.DataFrame(columns=columns)

    records = _sorted_records(day_records)
    rng = np.random.default_rng(seed)
    rows = []

    for pair in adjacent_pairs.itertuples(index=False):
        support_days = int(pair.support_days)
        left = _block_subset(
            records,
            str(pair.user_id),
            support_days,
            int(pair.left_block_index),
        )
        right = _block_subset(
            records,
            str(pair.user_id),
            support_days,
            int(pair.right_block_index),
        )
        pool = pd.concat([left, right], ignore_index=True)
        if len(pool) != 2 * support_days:
            continue

        nulls = {feature: [] for feature in STABILITY_FEATURES}
        exact_null = []

        for _ in range(repetitions):
            order = rng.permutation(len(pool))
            random_left = pool.iloc[order[:support_days]]
            random_right = pool.iloc[order[support_days:]]

            left_summary = BASE.summarize_days(
                random_left,
                calendar_window_days=max(
                    1, int(pair.left_calendar_span_days)
                ),
            )
            right_summary = BASE.summarize_days(
                random_right,
                calendar_window_days=max(
                    1, int(pair.right_calendar_span_days)
                ),
            )

            for feature in STABILITY_FEATURES:
                value = _absdiff(
                    left_summary[feature],
                    right_summary[feature],
                )
                if np.isfinite(value):
                    nulls[feature].append(value)

            left_edges = Counter(
                edge for values in random_left["edges"] for edge in values
            )
            right_edges = Counter(
                edge for values in random_right["edges"] for edge in values
            )
            jsd = BASE._jsd(left_edges, right_edges)
            if np.isfinite(jsd):
                exact_null.append(jsd)

        metrics = {
            feature: (
                _absdiff(
                    getattr(pair, f"left__{feature}"),
                    getattr(pair, f"right__{feature}"),
                ),
                nulls[feature],
            )
            for feature in STABILITY_FEATURES
        }
        metrics["exact_edge_jsd"] = (
            float(pair.exact_edge_jsd),
            exact_null,
        )

        for metric, (observed, values) in metrics.items():
            if not np.isfinite(observed) or not values:
                continue
            arr = np.asarray(values, dtype=float)
            p95 = float(np.quantile(arr, 0.95))
            rows.append(
                {
                    "user_id": str(pair.user_id),
                    "support_days": support_days,
                    "max_span_days": int(pair.max_span_days),
                    "left_block_index": int(pair.left_block_index),
                    "metric": metric,
                    "observed_difference": float(observed),
                    "random_median": float(np.median(arr)),
                    "random_p95": p95,
                    "random_p_ge_observed": float(
                        np.mean(arr >= observed)
                    ),
                    "observed_above_random_p95": bool(
                        observed > p95
                    ),
                }
            )

    return pd.DataFrame(rows, columns=columns)


def _spearman(left: pd.Series, right: pd.Series) -> float:
    pair = pd.DataFrame(
        {
            "left": pd.to_numeric(left, errors="coerce"),
            "right": pd.to_numeric(right, errors="coerce"),
        }
    ).dropna()
    if (
        len(pair) < 3
        or pair["left"].nunique() < 2
        or pair["right"].nunique() < 2
    ):
        return np.nan
    return float(pair["left"].rank().corr(pair["right"].rank()))


def summarize_test_retest(
    adjacent_pairs: pd.DataFrame,
    random_partition: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "support_days",
        "max_span_days",
        "feature",
        "comparable_pairs",
        "users",
        "spearman_test_retest",
        "median_abs_difference",
        "median_random_abs_difference",
        "chronological_above_random_p95_share",
    ]
    if adjacent_pairs.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for (support_days, max_span_days), group in adjacent_pairs.groupby(
        ["support_days", "max_span_days"],
        sort=True,
    ):
        for feature in STABILITY_FEATURES:
            pair = pd.DataFrame(
                {
                    "user_id": group["user_id"],
                    "left": pd.to_numeric(
                        group[f"left__{feature}"],
                        errors="coerce",
                    ),
                    "right": pd.to_numeric(
                        group[f"right__{feature}"],
                        errors="coerce",
                    ),
                }
            ).dropna()
            calibration = random_partition.loc[
                random_partition["support_days"].eq(support_days)
                & random_partition["max_span_days"].eq(max_span_days)
                & random_partition["metric"].eq(feature)
            ]
            rows.append(
                {
                    "support_days": int(support_days),
                    "max_span_days": int(max_span_days),
                    "feature": feature,
                    "comparable_pairs": int(len(pair)),
                    "users": int(pair["user_id"].nunique()),
                    "spearman_test_retest": _spearman(
                        pair["left"], pair["right"]
                    ),
                    "median_abs_difference": (
                        float(
                            (pair["left"] - pair["right"])
                            .abs()
                            .median()
                        )
                        if len(pair)
                        else np.nan
                    ),
                    "median_random_abs_difference": (
                        float(calibration["random_median"].median())
                        if len(calibration)
                        else np.nan
                    ),
                    "chronological_above_random_p95_share": (
                        float(
                            calibration[
                                "observed_above_random_p95"
                            ].mean()
                        )
                        if len(calibration)
                        else np.nan
                    ),
                }
            )

    return pd.DataFrame(rows, columns=columns)


def bootstrap_window_uncertainty(
    day_records: pd.DataFrame,
    windows: pd.DataFrame,
    *,
    repetitions: int = PRIMARY_BOOTSTRAP_REPETITIONS,
    seed: int = 42,
) -> pd.DataFrame:
    columns = [
        "user_id",
        "support_days",
        "max_span_days",
        "block_index",
        "feature",
        "calendar_span_days",
        "observed",
        "ci95_low",
        "ci95_high",
        "ci95_width",
    ]
    if windows.empty:
        return pd.DataFrame(columns=columns)

    records = _sorted_records(day_records)
    eligible = windows.loc[windows["span_eligible"].fillna(False).astype(bool)]
    rng = np.random.default_rng(seed)
    rows = []

    for window in eligible.itertuples(index=False):
        days = _block_subset(
            records,
            str(window.user_id),
            int(window.support_days),
            int(window.block_index),
        ).reset_index(drop=True)
        if len(days) != int(window.support_days):
            continue

        samples = {feature: [] for feature in STABILITY_FEATURES}
        for _ in range(repetitions):
            draw = days.iloc[
                rng.integers(0, len(days), size=len(days))
            ]
            summary = BASE.summarize_days(
                draw,
                calendar_window_days=max(
                    1, int(window.calendar_span_days)
                ),
            )
            for feature in STABILITY_FEATURES:
                value = summary[feature]
                if np.isfinite(value):
                    samples[feature].append(float(value))

        for feature, values in samples.items():
            observed = pd.to_numeric(
                pd.Series([getattr(window, feature)]),
                errors="coerce",
            ).iloc[0]
            if pd.isna(observed) or not values:
                continue
            arr = np.asarray(values, dtype=float)
            low, high = np.quantile(arr, [0.025, 0.975])
            rows.append(
                {
                    "user_id": str(window.user_id),
                    "support_days": int(window.support_days),
                    "max_span_days": int(window.max_span_days),
                    "block_index": int(window.block_index),
                    "feature": feature,
                    "calendar_span_days": int(
                        window.calendar_span_days
                    ),
                    "observed": float(observed),
                    "ci95_low": float(low),
                    "ci95_high": float(high),
                    "ci95_width": float(high - low),
                }
            )

    return pd.DataFrame(rows, columns=columns)


def summarize_bootstrap(bootstrap: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "support_days",
        "max_span_days",
        "feature",
        "windows",
        "users",
        "median_ci95_width",
        "observed_iqr",
        "median_ci95_width_over_observed_iqr",
    ]
    if bootstrap.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for (support_days, max_span_days, feature), group in bootstrap.groupby(
        ["support_days", "max_span_days", "feature"],
        sort=True,
    ):
        iqr = float(
            group["observed"].quantile(0.75)
            - group["observed"].quantile(0.25)
        )
        ci_width = float(group["ci95_width"].median())
        rows.append(
            {
                "support_days": int(support_days),
                "max_span_days": int(max_span_days),
                "feature": feature,
                "windows": int(len(group)),
                "users": int(group["user_id"].nunique()),
                "median_ci95_width": ci_width,
                "observed_iqr": iqr,
                "median_ci95_width_over_observed_iqr": (
                    float(ci_width / iqr)
                    if iqr > 0
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows, columns=columns)


def build_exact_od_baseline(
    adjacent_pairs: pd.DataFrame,
    random_partition: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "support_days",
        "max_span_days",
        "comparable_pairs",
        "users",
        "median_chronological_jsd",
        "median_random_jsd",
        "chronological_above_random_p95_share",
    ]
    if adjacent_pairs.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for (support_days, max_span_days), pairs in adjacent_pairs.groupby(
        ["support_days", "max_span_days"],
        sort=True,
    ):
        exact = pd.to_numeric(
            pairs["exact_edge_jsd"],
            errors="coerce",
        ).dropna()
        calibration = random_partition.loc[
            random_partition["support_days"].eq(support_days)
            & random_partition["max_span_days"].eq(max_span_days)
            & random_partition["metric"].eq("exact_edge_jsd")
        ]
        rows.append(
            {
                "support_days": int(support_days),
                "max_span_days": int(max_span_days),
                "comparable_pairs": int(len(exact)),
                "users": int(
                    pairs.loc[
                        pairs["exact_edge_jsd"].notna(),
                        "user_id",
                    ].nunique()
                ),
                "median_chronological_jsd": (
                    float(exact.median())
                    if len(exact)
                    else np.nan
                ),
                "median_random_jsd": (
                    float(calibration["random_median"].median())
                    if len(calibration)
                    else np.nan
                ),
                "chronological_above_random_p95_share": (
                    float(
                        calibration[
                            "observed_above_random_p95"
                        ].mean()
                    )
                    if len(calibration)
                    else np.nan
                ),
            }
        )

    return pd.DataFrame(rows, columns=columns)


def build_readiness_table(
    test_retest: pd.DataFrame,
    bootstrap_summary: pd.DataFrame,
    *,
    min_pairs: int = MIN_COMPARABLE_PAIRS,
    min_users: int = MIN_UNIQUE_USERS,
    min_spearman: float = MIN_SPEARMAN,
    max_null_exceedance_share: float = MAX_NULL_EXCEEDANCE_SHARE,
    max_ci_width_over_iqr: float = MAX_CI_WIDTH_OVER_IQR,
) -> pd.DataFrame:
    if test_retest.empty:
        return test_retest.copy()

    out = test_retest.merge(
        bootstrap_summary[
            [
                "support_days",
                "max_span_days",
                "feature",
                "median_ci95_width_over_observed_iqr",
            ]
        ],
        on=["support_days", "max_span_days", "feature"],
        how="left",
        validate="one_to_one",
    )
    out["primary_feature"] = out["feature"].isin(PRIMARY_FEATURES)
    out["pair_coverage_ok"] = out["comparable_pairs"].ge(min_pairs)
    out["user_coverage_ok"] = out["users"].ge(min_users)
    out["coverage_ok"] = (
        out["pair_coverage_ok"] & out["user_coverage_ok"]
    )
    out["rank_stability_ok"] = out[
        "spearman_test_retest"
    ].ge(min_spearman)
    out["null_calibration_ok"] = out[
        "chronological_above_random_p95_share"
    ].le(max_null_exceedance_share)
    out["bootstrap_uncertainty_ok"] = out[
        "median_ci95_width_over_observed_iqr"
    ].le(max_ci_width_over_iqr)
    out["candidate_for_stage07"] = out[
        [
            "coverage_ok",
            "rank_stability_ok",
            "null_calibration_ok",
            "bootstrap_uncertainty_ok",
        ]
    ].fillna(False).all(axis=1)
    return out


def build_decision_table(readiness: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "support_days",
        "max_span_days",
        "candidate_features",
        "candidate_primary_features",
        "stage07_ready",
    ]
    if readiness.empty:
        return pd.DataFrame(columns=columns)

    rows = []
    for (support_days, max_span_days), group in readiness.groupby(
        ["support_days", "max_span_days"],
        sort=True,
    ):
        passing = group.loc[
            group["candidate_for_stage07"].fillna(False).astype(bool)
        ]
        primary = passing.loc[
            passing["primary_feature"].fillna(False).astype(bool)
        ]
        rows.append(
            {
                "support_days": int(support_days),
                "max_span_days": int(max_span_days),
                "candidate_features": int(len(passing)),
                "candidate_primary_features": int(len(primary)),
                "stage07_ready": bool(len(primary) >= 1),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def run_audit(
    day_sequences: pd.DataFrame,
    transitions: pd.DataFrame,
    point_days: pd.DataFrame,
    *,
    support_days_values: Iterable[int] = SUPPORT_DAYS,
    max_span_days_values: Iterable[int] = MAX_SPAN_DAYS,
    random_partitions: int = PRIMARY_RANDOM_PARTITIONS,
    bootstrap_repetitions: int = PRIMARY_BOOTSTRAP_REPETITIONS,
    seed: int = 42,
) -> SupportWindowAudit:
    day_records = BASE.build_day_records(
        day_sequences,
        transitions,
        point_days,
    )
    windows = build_support_windows(
        day_records,
        support_days_values=support_days_values,
        max_span_days_values=max_span_days_values,
    )
    coverage = summarize_coverage(windows)
    adjacent_pairs = build_adjacent_pairs(day_records, windows)
    random_partition = random_partition_calibration(
        day_records,
        adjacent_pairs,
        repetitions=random_partitions,
        seed=seed,
    )
    test_retest = summarize_test_retest(
        adjacent_pairs,
        random_partition,
    )
    bootstrap = bootstrap_window_uncertainty(
        day_records,
        windows,
        repetitions=bootstrap_repetitions,
        seed=seed,
    )
    bootstrap_summary = summarize_bootstrap(bootstrap)
    readiness = build_readiness_table(
        test_retest,
        bootstrap_summary,
    )
    return SupportWindowAudit(
        day_records=day_records,
        windows=windows,
        coverage=coverage,
        adjacent_pairs=adjacent_pairs,
        random_partition=random_partition,
        test_retest=test_retest,
        bootstrap=bootstrap,
        bootstrap_summary=bootstrap_summary,
        readiness=readiness,
        exact_od_baseline=build_exact_od_baseline(
            adjacent_pairs,
            random_partition,
        ),
        decision=build_decision_table(readiness),
    )
