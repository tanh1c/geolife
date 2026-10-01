"""Stage 06c: feasibility audit for change-detection representations.

This stage stays upstream of change-point detection. It compares coarse,
support-normalized calendar-window features with support-matched random
partitions so sparse observation is not mistaken for temporal change.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

WINDOW_DAYS = (28, 42, 56)
PRIMARY_MIN_USABLE_DAYS = 6
PRIMARY_RANDOM_PARTITIONS = 200
PRIMARY_BOOTSTRAP_REPETITIONS = 300
PRIMARY_REPEATED_EDGE_DAYS = 2

TIME_BINS = (
    ("time_00_06_share", 0.0, 6.0),
    ("time_06_12_share", 6.0, 12.0),
    ("time_12_18_share", 12.0, 18.0),
    ("time_18_24_share", 18.0, 24.0),
)

STABILITY_FEATURES = (
    "active_location_count",
    "active_location_count_per_usable_day",
    "transition_count_per_usable_day",
    "edge_entropy",
    "normalized_edge_entropy",
    "top_edge_share",
    "repeated_edge_count",
    "repeated_edge_count_per_usable_day",
    "departure_time_concentration",
    "cleaned_distance_km_per_usable_day",
    "movement_duration_proxy_h_per_usable_day",
    "time_00_06_share",
    "time_06_12_share",
    "time_12_18_share",
    "time_18_24_share",
)


@dataclass(frozen=True)
class FeasibilityAudit:
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


def _dates(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "local_date" in out:
        out["local_date"] = pd.to_datetime(out["local_date"], errors="coerce").dt.date
    return out


def _locations(value: object) -> tuple[int, ...]:
    if isinstance(value, (tuple, list, np.ndarray)):
        return tuple(int(x) for x in value)
    return tuple()


def _concentration(values: Sequence[float]) -> float:
    x = np.asarray(values, dtype=float)
    x = x[np.isfinite(x)]
    if not len(x):
        return np.nan
    theta = 2 * np.pi * (x % 24.0) / 24.0
    return float(np.hypot(np.sin(theta).mean(), np.cos(theta).mean()))


def build_day_records(
    day_sequences: pd.DataFrame,
    transitions: pd.DataFrame,
    point_days: pd.DataFrame,
) -> pd.DataFrame:
    """Build one private row per Stage-06 usable day."""
    required = {
        "day_sequences": (day_sequences, {"user_id", "local_date", "sequence"}),
        "transitions": (
            transitions,
            {
                "user_id",
                "local_date",
                "origin_location_id",
                "destination_location_id",
                "departure_hour",
            },
        ),
        "point_days": (
            point_days,
            {
                "user_id",
                "local_date",
                "cleaned_travel_distance_m",
                "movement_duration_s",
            },
        ),
    }
    for name, (frame, columns) in required.items():
        missing = columns.difference(frame.columns)
        if missing:
            raise ValueError(f"{name} missing required columns: {sorted(missing)}")

    day = _dates(day_sequences)
    trans = _dates(transitions)
    points = _dates(point_days)
    for frame in (day, trans, points):
        frame["user_id"] = frame["user_id"].astype(str)

    if day.duplicated(["user_id", "local_date"]).any():
        raise ValueError("day_sequences must be unique by user/local_date")
    if points.duplicated(["user_id", "local_date"]).any():
        raise ValueError("point_days must be unique by user/local_date")

    payload = {}
    for keys, group in trans.groupby(["user_id", "local_date"], sort=True):
        edges = tuple(
            (int(o), int(d))
            for o, d in zip(
                group["origin_location_id"],
                group["destination_location_id"],
                strict=False,
            )
        )
        hours = tuple(
            float(x)
            for x in pd.to_numeric(group["departure_hour"], errors="coerce").dropna()
        )
        payload[(str(keys[0]), keys[1])] = (edges, hours)

    point_lookup = points.set_index(["user_id", "local_date"])
    rows = []
    for row in day.itertuples(index=False):
        key = (str(row.user_id), row.local_date)
        edges, hours = payload.get(key, (tuple(), tuple()))
        try:
            point = point_lookup.loc[key]
        except KeyError:
            distance_km = np.nan
            movement_h = np.nan
        else:
            distance = pd.to_numeric(
                pd.Series([point["cleaned_travel_distance_m"]]), errors="coerce"
            ).iloc[0]
            movement = pd.to_numeric(
                pd.Series([point["movement_duration_s"]]), errors="coerce"
            ).iloc[0]
            distance_km = float(distance / 1000.0) if pd.notna(distance) else np.nan
            movement_h = float(movement / 3600.0) if pd.notna(movement) else np.nan
        rows.append(
            {
                "user_id": key[0],
                "local_date": key[1],
                "location_ids": _locations(row.sequence),
                "edges": edges,
                "departure_hours": hours,
                "cleaned_distance_km": distance_km,
                "movement_duration_proxy_h": movement_h,
            }
        )
    return pd.DataFrame(rows).sort_values(["user_id", "local_date"]).reset_index(drop=True)


def _jsd(left: Counter, right: Counter) -> float:
    keys = sorted(set(left) | set(right))
    if not keys:
        return np.nan
    p = np.asarray([left.get(k, 0) for k in keys], dtype=float)
    q = np.asarray([right.get(k, 0) for k in keys], dtype=float)
    if p.sum() <= 0 or q.sum() <= 0:
        return np.nan
    p /= p.sum()
    q /= q.sum()
    m = 0.5 * (p + q)

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    return float(0.5 * kl(p, m) + 0.5 * kl(q, m))


def summarize_days(
    days: pd.DataFrame,
    *,
    calendar_window_days: int,
    repeated_edge_days: int = PRIMARY_REPEATED_EDGE_DAYS,
) -> dict[str, float | int]:
    n = int(len(days))
    if not n:
        return {
            "usable_day_count": 0,
            "calendar_coverage_share": 0.0,
            "movement_day_coverage": 0.0,
            **{feature: np.nan for feature in STABILITY_FEATURES},
        }

    locations: set[int] = set()
    edge_counts: Counter = Counter()
    edge_days: Counter = Counter()
    hours: list[float] = []
    for row in days.itertuples(index=False):
        locations.update(row.location_ids)
        edge_counts.update(row.edges)
        edge_days.update(set(row.edges))
        hours.extend(row.departure_hours)

    total = int(sum(edge_counts.values()))
    distinct = int(len(edge_counts))
    repeated = int(sum(v >= repeated_edge_days for v in edge_days.values()))
    if total:
        shares = np.asarray(list(edge_counts.values()), dtype=float) / total
        entropy = float(-(shares * np.log2(shares)).sum())
        normalized_entropy = float(entropy / np.log2(distinct)) if distinct > 1 else 0.0
        top_share = float(shares.max())
    else:
        entropy = normalized_entropy = top_share = 0.0

    dep = np.asarray(hours, dtype=float)
    dep = dep[np.isfinite(dep)]
    time_shares = {
        name: float(np.mean((dep >= lower) & (dep < upper))) if len(dep) else 0.0
        for name, lower, upper in TIME_BINS
    }

    distance = pd.to_numeric(days["cleaned_distance_km"], errors="coerce")
    movement = pd.to_numeric(days["movement_duration_proxy_h"], errors="coerce")
    movement_complete = bool(distance.notna().all() and movement.notna().all())
    active_locations = int(len(locations))

    return {
        "usable_day_count": n,
        "calendar_coverage_share": float(n / calendar_window_days),
        "movement_day_coverage": float((distance.notna() & movement.notna()).mean()),
        "active_location_count": active_locations,
        "active_location_count_per_usable_day": float(active_locations / n),
        "transition_count_per_usable_day": float(total / n),
        "edge_entropy": entropy,
        "normalized_edge_entropy": normalized_entropy,
        "top_edge_share": top_share,
        "repeated_edge_count": repeated,
        "repeated_edge_count_per_usable_day": float(repeated / n),
        "departure_time_concentration": _concentration(dep),
        "cleaned_distance_km_per_usable_day": (
            float(distance.sum() / n) if movement_complete else np.nan
        ),
        "movement_duration_proxy_h_per_usable_day": (
            float(movement.sum() / n) if movement_complete else np.nan
        ),
        **time_shares,
    }


def build_calendar_windows(
    day_records: pd.DataFrame,
    *,
    window_days_values: Iterable[int] = WINDOW_DAYS,
) -> pd.DataFrame:
    records = _dates(day_records)
    rows = []
    for user_id, user in records.groupby("user_id", sort=True):
        observed = pd.to_datetime(user["local_date"], errors="coerce").dropna()
        if observed.empty:
            continue
        first, last = observed.min().normalize(), observed.max().normalize()
        for width in window_days_values:
            width = int(width)
            start, index = first, 0
            while start <= last:
                end = start + pd.Timedelta(days=width - 1)
                dates = pd.to_datetime(user["local_date"], errors="coerce")
                subset = user.loc[dates.between(start, end, inclusive="both")]
                rows.append(
                    {
                        "user_id": str(user_id),
                        "window_days": width,
                        "window_index": index,
                        "window_start": start.date(),
                        "window_end": end.date(),
                        **summarize_days(subset, calendar_window_days=width),
                    }
                )
                start, index = end + pd.Timedelta(days=1), index + 1
    return pd.DataFrame(rows)


def summarize_coverage(
    windows: pd.DataFrame,
    *,
    min_usable_days: int = PRIMARY_MIN_USABLE_DAYS,
) -> pd.DataFrame:
    rows = []
    for width, group in windows.groupby("window_days", sort=True):
        eligible = group.loc[group["usable_day_count"].ge(min_usable_days)]
        users, pair_count = set(), 0
        for user_id, user in eligible.groupby("user_id", sort=True):
            indexes = set(user["window_index"].astype(int))
            pairs = sum((i + 1) in indexes for i in indexes)
            if pairs:
                users.add(str(user_id))
                pair_count += pairs
        rows.append(
            {
                "window_days": int(width),
                "total_calendar_windows": int(len(group)),
                "nonempty_windows": int(group["usable_day_count"].gt(0).sum()),
                "eligible_windows": int(len(eligible)),
                "users_with_eligible_window": int(eligible["user_id"].nunique()),
                "users_with_adjacent_eligible_pair": int(len(users)),
                "adjacent_eligible_pairs": int(pair_count),
                "median_usable_days_eligible_window": (
                    float(eligible["usable_day_count"].median()) if len(eligible) else np.nan
                ),
                "median_calendar_coverage_eligible_window": (
                    float(eligible["calendar_coverage_share"].median())
                    if len(eligible)
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def _subset(records: pd.DataFrame, row: object) -> pd.DataFrame:
    dates = pd.to_datetime(records["local_date"], errors="coerce")
    return records.loc[
        dates.between(pd.Timestamp(row.window_start), pd.Timestamp(row.window_end), inclusive="both")
    ]


def build_adjacent_pairs(
    day_records: pd.DataFrame,
    windows: pd.DataFrame,
    *,
    min_usable_days: int = PRIMARY_MIN_USABLE_DAYS,
) -> pd.DataFrame:
    columns = [
        "user_id",
        "window_days",
        "left_window_index",
        "right_window_index",
        "left_window_start",
        "right_window_start",
        "left_usable_days",
        "right_usable_days",
        "exact_edge_jsd",
    ]
    for feature in STABILITY_FEATURES:
        columns.extend([f"left__{feature}", f"right__{feature}"])

    records = _dates(day_records)
    eligible = windows.loc[windows["usable_day_count"].ge(min_usable_days)]
    rows = []
    for (user_id, width), group in eligible.groupby(["user_id", "window_days"], sort=True):
        lookup = {int(r.window_index): r for r in group.itertuples(index=False)}
        user = records.loc[records["user_id"].astype(str).eq(str(user_id))]
        for index in sorted(lookup):
            if index + 1 not in lookup:
                continue
            left, right = lookup[index], lookup[index + 1]
            left_days, right_days = _subset(user, left), _subset(user, right)
            left_edges = Counter(edge for values in left_days["edges"] for edge in values)
            right_edges = Counter(edge for values in right_days["edges"] for edge in values)
            row = {
                "user_id": str(user_id),
                "window_days": int(width),
                "left_window_index": index,
                "right_window_index": index + 1,
                "left_window_start": left.window_start,
                "right_window_start": right.window_start,
                "left_usable_days": int(left.usable_day_count),
                "right_usable_days": int(right.usable_day_count),
                "exact_edge_jsd": _jsd(left_edges, right_edges),
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
    columns = [
        "user_id",
        "window_days",
        "left_window_index",
        "metric",
        "observed_difference",
        "random_median",
        "random_p95",
        "random_p_ge_observed",
        "observed_above_random_p95",
    ]
    records = _dates(day_records)
    rng, rows = np.random.default_rng(seed), []

    for pair in adjacent_pairs.itertuples(index=False):
        user = records.loc[records["user_id"].astype(str).eq(str(pair.user_id))]
        start = pd.Timestamp(pair.left_window_start)
        end = pd.Timestamp(pair.right_window_start) + pd.Timedelta(days=int(pair.window_days) - 1)
        dates = pd.to_datetime(user["local_date"], errors="coerce")
        pool = user.loc[dates.between(start, end, inclusive="both")].reset_index(drop=True)
        left_n, right_n = int(pair.left_usable_days), int(pair.right_usable_days)
        if len(pool) != left_n + right_n:
            continue

        nulls = {feature: [] for feature in STABILITY_FEATURES}
        exact_null = []
        for _ in range(repetitions):
            order = rng.permutation(len(pool))
            left = pool.iloc[order[:left_n]]
            right = pool.iloc[order[left_n : left_n + right_n]]
            left_summary = summarize_days(left, calendar_window_days=int(pair.window_days))
            right_summary = summarize_days(right, calendar_window_days=int(pair.window_days))
            for feature in STABILITY_FEATURES:
                value = _absdiff(left_summary[feature], right_summary[feature])
                if np.isfinite(value):
                    nulls[feature].append(value)
            left_edges = Counter(edge for values in left["edges"] for edge in values)
            right_edges = Counter(edge for values in right["edges"] for edge in values)
            value = _jsd(left_edges, right_edges)
            if np.isfinite(value):
                exact_null.append(value)

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
        metrics["exact_edge_jsd"] = (float(pair.exact_edge_jsd), exact_null)
        for metric, (observed, values) in metrics.items():
            if not np.isfinite(observed) or not values:
                continue
            arr = np.asarray(values, dtype=float)
            p95 = float(np.quantile(arr, 0.95))
            rows.append(
                {
                    "user_id": str(pair.user_id),
                    "window_days": int(pair.window_days),
                    "left_window_index": int(pair.left_window_index),
                    "metric": metric,
                    "observed_difference": float(observed),
                    "random_median": float(np.median(arr)),
                    "random_p95": p95,
                    "random_p_ge_observed": float(np.mean(arr >= observed)),
                    "observed_above_random_p95": bool(observed > p95),
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
    if len(pair) < 3 or pair["left"].nunique() < 2 or pair["right"].nunique() < 2:
        return np.nan
    return float(pair["left"].rank().corr(pair["right"].rank()))


def summarize_test_retest(
    adjacent_pairs: pd.DataFrame,
    random_partition: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "window_days",
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
    for width, group in adjacent_pairs.groupby("window_days", sort=True):
        for feature in STABILITY_FEATURES:
            pair = pd.DataFrame(
                {
                    "user_id": group["user_id"],
                    "left": pd.to_numeric(group[f"left__{feature}"], errors="coerce"),
                    "right": pd.to_numeric(group[f"right__{feature}"], errors="coerce"),
                }
            ).dropna()
            calibration = random_partition.loc[
                random_partition["window_days"].eq(width)
                & random_partition["metric"].eq(feature)
            ]
            rows.append(
                {
                    "window_days": int(width),
                    "feature": feature,
                    "comparable_pairs": int(len(pair)),
                    "users": int(pair["user_id"].nunique()),
                    "spearman_test_retest": _spearman(pair["left"], pair["right"]),
                    "median_abs_difference": (
                        float((pair["left"] - pair["right"]).abs().median())
                        if len(pair)
                        else np.nan
                    ),
                    "median_random_abs_difference": (
                        float(calibration["random_median"].median())
                        if len(calibration)
                        else np.nan
                    ),
                    "chronological_above_random_p95_share": (
                        float(calibration["observed_above_random_p95"].mean())
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
    min_usable_days: int = PRIMARY_MIN_USABLE_DAYS,
    repetitions: int = PRIMARY_BOOTSTRAP_REPETITIONS,
    seed: int = 42,
) -> pd.DataFrame:
    columns = [
        "user_id",
        "window_days",
        "window_index",
        "feature",
        "usable_day_count",
        "observed",
        "ci95_low",
        "ci95_high",
        "ci95_width",
    ]
    records = _dates(day_records)
    rng, rows = np.random.default_rng(seed), []
    eligible = windows.loc[windows["usable_day_count"].ge(min_usable_days)]
    for window in eligible.itertuples(index=False):
        user = records.loc[records["user_id"].astype(str).eq(str(window.user_id))]
        days = _subset(user, window).reset_index(drop=True)
        if len(days) < min_usable_days:
            continue
        samples = {feature: [] for feature in STABILITY_FEATURES}
        for _ in range(repetitions):
            draw = days.iloc[rng.integers(0, len(days), size=len(days))]
            summary = summarize_days(draw, calendar_window_days=int(window.window_days))
            for feature in STABILITY_FEATURES:
                value = summary[feature]
                if np.isfinite(value):
                    samples[feature].append(float(value))
        for feature, values in samples.items():
            observed = pd.to_numeric(
                pd.Series([getattr(window, feature)]), errors="coerce"
            ).iloc[0]
            if pd.isna(observed) or not values:
                continue
            arr = np.asarray(values, dtype=float)
            low, high = np.quantile(arr, [0.025, 0.975])
            rows.append(
                {
                    "user_id": str(window.user_id),
                    "window_days": int(window.window_days),
                    "window_index": int(window.window_index),
                    "feature": feature,
                    "usable_day_count": int(window.usable_day_count),
                    "observed": float(observed),
                    "ci95_low": float(low),
                    "ci95_high": float(high),
                    "ci95_width": float(high - low),
                }
            )
    return pd.DataFrame(rows, columns=columns)


def summarize_bootstrap(bootstrap: pd.DataFrame) -> pd.DataFrame:
    columns = [
        "window_days",
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
    for (width, feature), group in bootstrap.groupby(["window_days", "feature"], sort=True):
        iqr = float(group["observed"].quantile(0.75) - group["observed"].quantile(0.25))
        ci_width = float(group["ci95_width"].median())
        rows.append(
            {
                "window_days": int(width),
                "feature": feature,
                "windows": int(len(group)),
                "users": int(group["user_id"].nunique()),
                "median_ci95_width": ci_width,
                "observed_iqr": iqr,
                "median_ci95_width_over_observed_iqr": (
                    float(ci_width / iqr) if iqr > 0 else np.nan
                ),
            }
        )
    return pd.DataFrame(rows, columns=columns)


def build_exact_od_baseline(
    adjacent_pairs: pd.DataFrame,
    random_partition: pd.DataFrame,
) -> pd.DataFrame:
    columns = [
        "window_days",
        "comparable_pairs",
        "users",
        "median_chronological_jsd",
        "median_random_jsd",
        "chronological_above_random_p95_share",
    ]
    if adjacent_pairs.empty:
        return pd.DataFrame(columns=columns)
    rows = []
    for width, pairs in adjacent_pairs.groupby("window_days", sort=True):
        exact = pd.to_numeric(pairs["exact_edge_jsd"], errors="coerce").dropna()
        calibration = random_partition.loc[
            random_partition["window_days"].eq(width)
            & random_partition["metric"].eq("exact_edge_jsd")
        ]
        rows.append(
            {
                "window_days": int(width),
                "comparable_pairs": int(len(exact)),
                "users": int(pairs.loc[pairs["exact_edge_jsd"].notna(), "user_id"].nunique()),
                "median_chronological_jsd": float(exact.median()) if len(exact) else np.nan,
                "median_random_jsd": (
                    float(calibration["random_median"].median()) if len(calibration) else np.nan
                ),
                "chronological_above_random_p95_share": (
                    float(calibration["observed_above_random_p95"].mean())
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
    min_pairs: int = 20,
    min_spearman: float = 0.50,
    max_null_exceedance_share: float = 0.10,
    max_ci_width_over_iqr: float = 1.0,
) -> pd.DataFrame:
    out = test_retest.merge(
        bootstrap_summary[
            ["window_days", "feature", "median_ci95_width_over_observed_iqr"]
        ],
        on=["window_days", "feature"],
        how="left",
        validate="one_to_one",
    )
    out["coverage_ok"] = out["comparable_pairs"].ge(min_pairs)
    out["rank_stability_ok"] = out["spearman_test_retest"].ge(min_spearman)
    out["null_calibration_ok"] = out["chronological_above_random_p95_share"].le(
        max_null_exceedance_share
    )
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


def run_audit(
    day_sequences: pd.DataFrame,
    transitions: pd.DataFrame,
    point_days: pd.DataFrame,
    *,
    window_days_values: Iterable[int] = WINDOW_DAYS,
    min_usable_days: int = PRIMARY_MIN_USABLE_DAYS,
    random_partitions: int = PRIMARY_RANDOM_PARTITIONS,
    bootstrap_repetitions: int = PRIMARY_BOOTSTRAP_REPETITIONS,
    seed: int = 42,
) -> FeasibilityAudit:
    day_records = build_day_records(day_sequences, transitions, point_days)
    windows = build_calendar_windows(day_records, window_days_values=window_days_values)
    coverage = summarize_coverage(windows, min_usable_days=min_usable_days)
    adjacent_pairs = build_adjacent_pairs(
        day_records, windows, min_usable_days=min_usable_days
    )
    random_partition = random_partition_calibration(
        day_records,
        adjacent_pairs,
        repetitions=random_partitions,
        seed=seed,
    )
    test_retest = summarize_test_retest(adjacent_pairs, random_partition)
    bootstrap = bootstrap_window_uncertainty(
        day_records,
        windows,
        min_usable_days=min_usable_days,
        repetitions=bootstrap_repetitions,
        seed=seed,
    )
    bootstrap_summary = summarize_bootstrap(bootstrap)
    return FeasibilityAudit(
        day_records=day_records,
        windows=windows,
        coverage=coverage,
        adjacent_pairs=adjacent_pairs,
        random_partition=random_partition,
        test_retest=test_retest,
        bootstrap=bootstrap,
        bootstrap_summary=bootstrap_summary,
        readiness=build_readiness_table(test_retest, bootstrap_summary),
        exact_od_baseline=build_exact_od_baseline(adjacent_pairs, random_partition),
    )
