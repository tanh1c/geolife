"""Stage 06b: robustness audit for Stage-06 routine representations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture

PRIMARY_MIN_USABLE_DAYS = 6
PRIMARY_EDGE_REPEAT_DAYS = 3
PRIMARY_MOTIF_SHARE = 0.50
PRIMARY_MIN_HALF_DAYS = 3
PRIMARY_RANDOM_PARTITIONS = 200
PRIMARY_BOOTSTRAP_REPETITIONS = 1000

STRICT_GMM_MIN_ACTIVE_DAYS = 5
STRICT_GMM_MIN_TRANSITIONS = 8
STRICT_GMM_MIN_COMPONENT_WEIGHT = 0.20
STRICT_GMM_MIN_SEPARATION_H = 2.0
STRICT_GMM_MIN_BIC_GAIN = 10.0


@dataclass(frozen=True)
class RobustnessAudit:
    motif_primary: pd.DataFrame
    motif_sensitivity: pd.DataFrame
    support_tiers: pd.DataFrame
    split_distribution: pd.DataFrame
    split_aggregate: pd.DataFrame
    random_partition: pd.DataFrame
    departure_bootstrap: pd.DataFrame
    departure_bootstrap_summary: pd.DataFrame
    strict_modes: pd.DataFrame
    strict_mode_sensitivity: pd.DataFrame
    readiness: pd.DataFrame


def _user_day_counts(day_sequences: pd.DataFrame) -> pd.DataFrame:
    return (
        day_sequences.groupby("user_id", as_index=False)
        .agg(usable_days=("local_date", "nunique"))
    )


def supported_motif_comparator(
    day_sequences: pd.DataFrame,
    edge_summary: pd.DataFrame,
    *,
    min_usable_days: int = PRIMARY_MIN_USABLE_DAYS,
    edge_repeat_days: int = PRIMARY_EDGE_REPEAT_DAYS,
    motif_share: float = PRIMARY_MOTIF_SHARE,
    motif_min_active_days: int | None = None,
) -> pd.DataFrame:
    """Compare recurring OD and collapsed-sequence motifs on the same support universe."""
    if motif_min_active_days is None:
        motif_min_active_days = edge_repeat_days

    support = _user_day_counts(day_sequences)
    eligible = set(
        support.loc[
            support["usable_days"].ge(min_usable_days),
            "user_id",
        ].astype(str)
    )

    day = day_sequences.loc[
        day_sequences["user_id"].astype(str).isin(eligible)
    ]
    motif = (
        day.groupby(["user_id", "motif"], as_index=False)
        .agg(motif_active_days=("local_date", "nunique"))
    )
    if motif.empty:
        motif_users: set[str] = set()
    else:
        motif = motif.merge(
            support,
            on="user_id",
            how="left",
            validate="many_to_one",
        )
        motif["motif_share"] = motif["motif_active_days"] / motif["usable_days"]
        top = (
            motif.sort_values(
                ["user_id", "motif_active_days", "motif"],
                ascending=[True, False, True],
                kind="stable",
            )
            .groupby("user_id", as_index=False)
            .first()
        )
        motif_users = set(
            top.loc[
                top["motif_active_days"].ge(motif_min_active_days)
                & top["motif_share"].ge(motif_share),
                "user_id",
            ].astype(str)
        )

    od = edge_summary.loc[
        edge_summary["user_id"].astype(str).isin(eligible)
        & edge_summary["active_days"].ge(edge_repeat_days)
    ]
    od_users = set(od["user_id"].astype(str))

    return pd.DataFrame(
        [{
            "min_usable_days": int(min_usable_days),
            "edge_repeat_days": int(edge_repeat_days),
            "motif_min_active_days": int(motif_min_active_days),
            "motif_share_threshold": float(motif_share),
            "eligible_users": int(len(eligible)),
            "users_with_repeated_od": int(len(od_users)),
            "users_with_supported_collapsed_motif": int(len(motif_users)),
            "od_only_users": int(len(od_users - motif_users)),
            "motif_only_users": int(len(motif_users - od_users)),
            "both_users": int(len(od_users & motif_users)),
        }]
    )


def motif_comparator_sensitivity(
    day_sequences: pd.DataFrame,
    edge_summary: pd.DataFrame,
    *,
    min_usable_days_values: Iterable[int] = (4, 6, 10),
    repeat_days_values: Iterable[int] = (2, 3, 5),
) -> pd.DataFrame:
    rows = []
    for min_days in min_usable_days_values:
        for repeat_days in repeat_days_values:
            rows.append(
                supported_motif_comparator(
                    day_sequences,
                    edge_summary,
                    min_usable_days=int(min_days),
                    edge_repeat_days=int(repeat_days),
                    motif_min_active_days=int(repeat_days),
                ).iloc[0].to_dict()
            )
    return pd.DataFrame(rows)


def build_support_tiers(
    edge_summary: pd.DataFrame,
    day_sequences: pd.DataFrame,
) -> pd.DataFrame:
    support = _user_day_counts(day_sequences)
    support_users = set(
        support.loc[
            support["usable_days"].ge(PRIMARY_MIN_USABLE_DAYS),
            "user_id",
        ].astype(str)
    )
    rows = []
    for threshold, tier in ((2, "candidate"), (3, "supported"), (5, "strong")):
        edges = edge_summary.loc[edge_summary["active_days"].ge(threshold)]
        users = set(edges["user_id"].astype(str))
        rows.append(
            {
                "tier": tier,
                "edge_active_days_threshold": threshold,
                "edges": int(len(edges)),
                "users": int(len(users)),
                "users_with_6plus_usable_days": int(len(users & support_users)),
            }
        )
    return pd.DataFrame(rows)


def _edge_counts(
    transitions: pd.DataFrame,
    dates: set[object],
) -> dict[tuple[int, int], int]:
    subset = transitions.loc[transitions["local_date"].isin(dates)]
    if subset.empty:
        return {}
    counts = subset.groupby(
        ["origin_location_id", "destination_location_id"]
    ).size()
    return {
        (int(origin), int(destination)): int(value)
        for (origin, destination), value in counts.items()
    }


def _distribution(
    counts: dict[tuple[int, int], int],
    keys: list[tuple[int, int]],
) -> np.ndarray:
    values = np.asarray([counts.get(key, 0) for key in keys], dtype=float)
    return values / values.sum() if values.sum() > 0 else values


def distribution_metrics(
    left: dict[tuple[int, int], int],
    right: dict[tuple[int, int], int],
    *,
    top_k: int = 3,
) -> dict[str, object]:
    keys = sorted(set(left) | set(right))
    if not keys:
        return {
            "comparable": False,
            "jsd": np.nan,
            "weighted_jaccard": np.nan,
            "total_variation": np.nan,
            "top1_same": False,
            "topk_jaccard": np.nan,
        }

    p = _distribution(left, keys)
    q = _distribution(right, keys)
    if p.sum() <= 0 or q.sum() <= 0:
        return {
            "comparable": False,
            "jsd": np.nan,
            "weighted_jaccard": np.nan,
            "total_variation": np.nan,
            "top1_same": False,
            "topk_jaccard": np.nan,
        }

    m = 0.5 * (p + q)

    def kl(a: np.ndarray, b: np.ndarray) -> float:
        mask = a > 0
        return float(np.sum(a[mask] * np.log2(a[mask] / b[mask])))

    left_rank = sorted(left, key=lambda key: (-left[key], key))
    right_rank = sorted(right, key=lambda key: (-right[key], key))
    left_top = set(left_rank[:top_k])
    right_top = set(right_rank[:top_k])
    union = left_top | right_top

    return {
        "comparable": True,
        "jsd": float(0.5 * kl(p, m) + 0.5 * kl(q, m)),
        "weighted_jaccard": float(
            np.minimum(p, q).sum() / np.maximum(p, q).sum()
        ),
        "total_variation": float(0.5 * np.abs(p - q).sum()),
        "top1_same": bool(left_rank[0] == right_rank[0]),
        "topk_jaccard": (
            float(len(left_top & right_top) / len(union))
            if union
            else np.nan
        ),
    }


def chronological_split_distribution(
    transitions: pd.DataFrame,
    day_sequences: pd.DataFrame,
    *,
    min_half_days: int = PRIMARY_MIN_HALF_DAYS,
) -> pd.DataFrame:
    rows = []
    for user_id, day in day_sequences.groupby("user_id", sort=True):
        dates = sorted(day["local_date"].dropna().unique().tolist())
        middle = len(dates) // 2
        first = set(dates[:middle])
        second = set(dates[middle:])
        support_eligible = (
            len(first) >= min_half_days and len(second) >= min_half_days
        )
        base = {
            "user_id": str(user_id),
            "support_eligible": support_eligible,
            "first_half_days": len(first),
            "second_half_days": len(second),
        }
        if not support_eligible:
            rows.append({**base, **distribution_metrics({}, {})})
            continue

        user_t = transitions.loc[
            transitions["user_id"].astype(str).eq(str(user_id))
        ]
        rows.append(
            {
                **base,
                **distribution_metrics(
                    _edge_counts(user_t, first),
                    _edge_counts(user_t, second),
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_split_distribution(split: pd.DataFrame) -> pd.DataFrame:
    comparable = split.loc[split["comparable"].fillna(False).astype(bool)]
    return pd.DataFrame(
        [{
            "support_eligible_users": int(
                split["support_eligible"].fillna(False).astype(bool).sum()
            ),
            "comparable_users": int(len(comparable)),
            "same_top1_share": (
                float(comparable["top1_same"].mean())
                if len(comparable)
                else np.nan
            ),
            "median_jsd": (
                float(comparable["jsd"].median())
                if len(comparable)
                else np.nan
            ),
            "p25_jsd": (
                float(comparable["jsd"].quantile(0.25))
                if len(comparable)
                else np.nan
            ),
            "p75_jsd": (
                float(comparable["jsd"].quantile(0.75))
                if len(comparable)
                else np.nan
            ),
            "median_weighted_jaccard": (
                float(comparable["weighted_jaccard"].median())
                if len(comparable)
                else np.nan
            ),
            "median_total_variation": (
                float(comparable["total_variation"].median())
                if len(comparable)
                else np.nan
            ),
            "median_top3_jaccard": (
                float(comparable["topk_jaccard"].median())
                if len(comparable)
                else np.nan
            ),
        }]
    )


def random_partition_calibration(
    transitions: pd.DataFrame,
    day_sequences: pd.DataFrame,
    split: pd.DataFrame,
    *,
    repetitions: int = PRIMARY_RANDOM_PARTITIONS,
    seed: int = 42,
) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    rows = []

    for row in split.itertuples(index=False):
        if not bool(row.comparable):
            continue

        user_id = str(row.user_id)
        dates = np.asarray(
            sorted(
                day_sequences.loc[
                    day_sequences["user_id"].astype(str).eq(user_id),
                    "local_date",
                ].drop_duplicates().tolist()
            ),
            dtype=object,
        )
        user_t = transitions.loc[
            transitions["user_id"].astype(str).eq(user_id)
        ]
        samples = []
        for _ in range(repetitions):
            shuffled = dates.copy()
            rng.shuffle(shuffled)
            first = set(shuffled[: int(row.first_half_days)])
            second = set(shuffled[int(row.first_half_days) :])
            metrics = distribution_metrics(
                _edge_counts(user_t, first),
                _edge_counts(user_t, second),
            )
            if metrics["comparable"]:
                samples.append(float(metrics["jsd"]))

        if not samples:
            continue

        arr = np.asarray(samples, dtype=float)
        observed = float(row.jsd)
        rows.append(
            {
                "user_id": user_id,
                "chronological_jsd": observed,
                "random_jsd_median": float(np.median(arr)),
                "random_jsd_p95": float(np.quantile(arr, 0.95)),
                "chronological_minus_random_median_jsd": float(
                    observed - np.median(arr)
                ),
                "random_p_ge_chronological_jsd": float(
                    np.mean(arr >= observed)
                ),
                "chronological_above_random_p95_jsd": bool(
                    observed > np.quantile(arr, 0.95)
                ),
            }
        )
    return pd.DataFrame(rows)


def _circular_mean_hour(values: pd.Series) -> float:
    x = pd.to_numeric(values, errors="coerce").dropna().to_numpy(float)
    theta = 2 * np.pi * (x % 24.0) / 24.0
    if not len(theta):
        return np.nan
    angle = float(np.arctan2(np.mean(np.sin(theta)), np.mean(np.cos(theta))))
    if angle < 0:
        angle += 2 * np.pi
    return float(24 * angle / (2 * np.pi))


def _concentration(hours: np.ndarray) -> float:
    theta = 2 * np.pi * (hours % 24.0) / 24.0
    return float(np.hypot(np.mean(np.sin(theta)), np.mean(np.cos(theta))))


def edge_daily_hours(transitions: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for keys, group in transitions.groupby(
        [
            "user_id",
            "origin_location_id",
            "destination_location_id",
            "local_date",
        ],
        sort=True,
    ):
        user_id, origin, destination, local_date = keys
        rows.append(
            {
                "user_id": str(user_id),
                "origin_location_id": int(origin),
                "destination_location_id": int(destination),
                "local_date": local_date,
                "daily_departure_hour": _circular_mean_hour(
                    group["departure_hour"]
                ),
            }
        )
    return pd.DataFrame(rows)


def bootstrap_departure_concentration(
    transitions: pd.DataFrame,
    *,
    min_active_days: int = PRIMARY_EDGE_REPEAT_DAYS,
    repetitions: int = PRIMARY_BOOTSTRAP_REPETITIONS,
    seed: int = 42,
) -> pd.DataFrame:
    daily = edge_daily_hours(transitions)
    rng = np.random.default_rng(seed)
    rows = []

    for keys, group in daily.groupby(
        ["user_id", "origin_location_id", "destination_location_id"],
        sort=True,
    ):
        user_id, origin, destination = keys
        hours = group["daily_departure_hour"].dropna().to_numpy(float)
        if len(hours) < min_active_days:
            continue

        boot = np.empty(repetitions, dtype=float)
        for index in range(repetitions):
            boot[index] = _concentration(
                rng.choice(hours, size=len(hours), replace=True)
            )

        rows.append(
            {
                "user_id": str(user_id),
                "origin_location_id": int(origin),
                "destination_location_id": int(destination),
                "active_days": int(len(hours)),
                "support_tier": (
                    "strong"
                    if len(hours) >= 5
                    else "supported"
                    if len(hours) >= 3
                    else "candidate"
                ),
                "observed_concentration": _concentration(hours),
                "ci95_low": float(np.quantile(boot, 0.025)),
                "ci95_high": float(np.quantile(boot, 0.975)),
                "ci95_width": float(
                    np.quantile(boot, 0.975) - np.quantile(boot, 0.025)
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_departure_bootstrap(boot: pd.DataFrame) -> pd.DataFrame:
    if boot.empty:
        return pd.DataFrame()
    return (
        boot.groupby("support_tier", as_index=False)
        .agg(
            edges=("user_id", "size"),
            users=("user_id", "nunique"),
            median_active_days=("active_days", "median"),
            median_observed_concentration=("observed_concentration", "median"),
            median_ci95_low=("ci95_low", "median"),
            median_ci95_width=("ci95_width", "median"),
            edges_ci_low_ge_0_5=("ci95_low", lambda s: int((s >= 0.5).sum())),
            edges_ci_low_ge_0_7=("ci95_low", lambda s: int((s >= 0.7).sum())),
        )
    )


def _distance_h(left: float, right: float) -> float:
    delta = abs(left - right) % 24.0
    return float(min(delta, 24.0 - delta))


def strict_departure_modes(
    transitions: pd.DataFrame,
    *,
    min_active_days: int = STRICT_GMM_MIN_ACTIVE_DAYS,
    min_transitions: int = STRICT_GMM_MIN_TRANSITIONS,
    min_component_weight: float = STRICT_GMM_MIN_COMPONENT_WEIGHT,
    min_separation_h: float = STRICT_GMM_MIN_SEPARATION_H,
    min_bic_gain: float = STRICT_GMM_MIN_BIC_GAIN,
) -> pd.DataFrame:
    daily = edge_daily_hours(transitions)
    rows = []

    for keys, raw in transitions.groupby(
        ["user_id", "origin_location_id", "destination_location_id"],
        sort=True,
    ):
        user_id, origin, destination = keys
        group = daily.loc[
            daily["user_id"].eq(str(user_id))
            & daily["origin_location_id"].eq(int(origin))
            & daily["destination_location_id"].eq(int(destination))
        ]
        hours = group["daily_departure_hour"].dropna().to_numpy(float)
        if len(hours) < min_active_days or len(raw) < min_transitions:
            continue

        center = _circular_mean_hour(pd.Series(hours))
        unwrapped = ((hours - center + 12.0) % 24.0 - 12.0).reshape(-1, 1)
        distinct = int(np.unique(np.round(unwrapped.reshape(-1), 6)).size)
        max_k = max(1, min(3, len(hours) // 2, distinct))

        fits = []
        for k in range(1, max_k + 1):
            model = GaussianMixture(
                n_components=k,
                random_state=42,
                covariance_type="full",
                n_init=10,
            ).fit(unwrapped)
            fits.append((k, model, float(model.bic(unwrapped))))

        best_k, model, best_bic = min(fits, key=lambda item: item[2])
        bic1 = next(bic for k, _model, bic in fits if k == 1)
        centers = (center + model.means_.reshape(-1)) % 24.0
        separations = [
            _distance_h(float(centers[i]), float(centers[j]))
            for i in range(len(centers))
            for j in range(i + 1, len(centers))
        ]
        min_sep = float(min(separations)) if separations else np.nan
        min_weight = float(model.weights_.min())
        gain = float(bic1 - best_bic)

        strict_multi = bool(
            best_k >= 2
            and gain >= min_bic_gain
            and min_weight >= min_component_weight
            and np.isfinite(min_sep)
            and min_sep >= min_separation_h
        )

        rows.append(
            {
                "user_id": str(user_id),
                "origin_location_id": int(origin),
                "destination_location_id": int(destination),
                "active_days": int(len(hours)),
                "transition_count": int(len(raw)),
                "selected_components": int(best_k),
                "bic_gain_vs_1": gain,
                "min_component_weight": min_weight,
                "min_center_separation_h": min_sep,
                "strict_multimodal": strict_multi,
            }
        )
    return pd.DataFrame(rows)


def strict_mode_sensitivity(
    transitions: pd.DataFrame,
    *,
    min_active_days_values: Iterable[int] = (3, 5),
    min_bic_gain_values: Iterable[float] = (6.0, 10.0),
    min_weight_values: Iterable[float] = (0.15, 0.20),
    min_separation_values: Iterable[float] = (1.0, 2.0),
) -> pd.DataFrame:
    rows = []
    for active_days in min_active_days_values:
        for bic_gain in min_bic_gain_values:
            for weight in min_weight_values:
                for separation in min_separation_values:
                    modeled = strict_departure_modes(
                        transitions,
                        min_active_days=int(active_days),
                        min_transitions=max(6, int(active_days)),
                        min_component_weight=float(weight),
                        min_separation_h=float(separation),
                        min_bic_gain=float(bic_gain),
                    )
                    rows.append(
                        {
                            "min_active_days": int(active_days),
                            "min_bic_gain": float(bic_gain),
                            "min_component_weight": float(weight),
                            "min_separation_h": float(separation),
                            "modeled_edges": int(len(modeled)),
                            "modeled_users": (
                                int(modeled["user_id"].nunique())
                                if len(modeled)
                                else 0
                            ),
                            "strict_multimodal_edges": (
                                int(modeled["strict_multimodal"].sum())
                                if len(modeled)
                                else 0
                            ),
                            "strict_multimodal_users": (
                                int(
                                    modeled.loc[
                                        modeled["strict_multimodal"],
                                        "user_id",
                                    ].nunique()
                                )
                                if len(modeled)
                                else 0
                            ),
                        }
                    )
    return pd.DataFrame(rows)


def build_readiness_snapshot(
    day_sequences: pd.DataFrame,
    edge_summary: pd.DataFrame,
    motif_primary: pd.DataFrame,
    split_aggregate: pd.DataFrame,
    random_partition: pd.DataFrame,
    boot_summary: pd.DataFrame,
    strict_modes: pd.DataFrame,
) -> pd.DataFrame:
    support = _user_day_counts(day_sequences)
    strong_boot = (
        boot_summary.loc[boot_summary["support_tier"].eq("strong")]
        if len(boot_summary)
        else pd.DataFrame()
    )
    return pd.DataFrame(
        [{
            "supported_users": int(day_sequences["user_id"].nunique()),
            "users_with_6plus_usable_days": int(
                support["usable_days"].ge(PRIMARY_MIN_USABLE_DAYS).sum()
            ),
            "primary_repeated_od_users_same_support": int(
                motif_primary.iloc[0]["users_with_repeated_od"]
            ),
            "split_comparable_users": int(
                split_aggregate.iloc[0]["comparable_users"]
            ),
            "median_split_jsd": float(split_aggregate.iloc[0]["median_jsd"]),
            "median_split_weighted_jaccard": float(
                split_aggregate.iloc[0]["median_weighted_jaccard"]
            ),
            "users_chronological_jsd_above_random_p95": (
                int(
                    random_partition[
                        "chronological_above_random_p95_jsd"
                    ].sum()
                )
                if len(random_partition)
                else 0
            ),
            "strong_departure_edges": int(
                edge_summary["active_days"].ge(5).sum()
            ),
            "strong_bootstrap_edges": (
                int(strong_boot.iloc[0]["edges"])
                if len(strong_boot)
                else 0
            ),
            "strict_modeled_edges": int(len(strict_modes)),
            "strict_multimodal_edges": (
                int(strict_modes["strict_multimodal"].sum())
                if len(strict_modes)
                else 0
            ),
        }]
    )


def run_audit(
    day_sequences: pd.DataFrame,
    transitions: pd.DataFrame,
    edge_summary: pd.DataFrame,
) -> RobustnessAudit:
    motif_primary = supported_motif_comparator(day_sequences, edge_summary)
    motif_sensitivity = motif_comparator_sensitivity(day_sequences, edge_summary)
    support_tiers = build_support_tiers(edge_summary, day_sequences)
    split = chronological_split_distribution(transitions, day_sequences)
    split_aggregate = summarize_split_distribution(split)
    random = random_partition_calibration(
        transitions,
        day_sequences,
        split,
    )
    boot = bootstrap_departure_concentration(transitions)
    boot_summary = summarize_departure_bootstrap(boot)
    strict = strict_departure_modes(transitions)
    strict_sensitivity = strict_mode_sensitivity(transitions)
    readiness = build_readiness_snapshot(
        day_sequences,
        edge_summary,
        motif_primary,
        split_aggregate,
        random,
        boot_summary,
        strict,
    )
    return RobustnessAudit(
        motif_primary=motif_primary,
        motif_sensitivity=motif_sensitivity,
        support_tiers=support_tiers,
        split_distribution=split,
        split_aggregate=split_aggregate,
        random_partition=random,
        departure_bootstrap=boot,
        departure_bootstrap_summary=boot_summary,
        strict_modes=strict,
        strict_mode_sensitivity=strict_sensitivity,
        readiness=readiness,
    )


def synthetic_self_check() -> dict[str, object]:
    days = []
    transitions = []
    start = pd.Timestamp("2026-01-01")

    stable_pattern = [1, 1, 1, 1, 2, 2] * 2
    for i, destination in enumerate(stable_pattern):
        date = (start + pd.Timedelta(days=i)).date()
        days.append(
            {"user_id": "stable", "local_date": date, "motif": "L0→L1→L0"}
        )
        transitions.append(
            {
                "user_id": "stable",
                "local_date": date,
                "origin_location_id": 0,
                "destination_location_id": destination,
                "departure_hour": 8.0 + 0.1 * (i % 2),
            }
        )

    for i in range(12):
        date = (start + pd.Timedelta(days=30 + i)).date()
        destination = 1 if i < 6 else 2
        days.append(
            {
                "user_id": "shift",
                "local_date": date,
                "motif": "L0→L1" if i < 6 else "L0→L2",
            }
        )
        transitions.append(
            {
                "user_id": "shift",
                "local_date": date,
                "origin_location_id": 0,
                "destination_location_id": destination,
                "departure_hour": 9.0 if i < 6 else 15.0,
            }
        )

    day = pd.DataFrame(days)
    trans = pd.DataFrame(transitions)
    split = chronological_split_distribution(trans, day)
    stable = split.loc[split["user_id"].eq("stable")].iloc[0]
    shift = split.loc[split["user_id"].eq("shift")].iloc[0]
    assert float(stable["jsd"]) < 0.2
    assert float(shift["jsd"]) > 0.9

    random = random_partition_calibration(
        trans,
        day,
        split,
        repetitions=100,
        seed=7,
    )
    shift_random = random.loc[random["user_id"].eq("shift")].iloc[0]
    assert bool(shift_random["chronological_above_random_p95_jsd"])

    boot = bootstrap_departure_concentration(
        trans,
        repetitions=100,
        seed=7,
    )
    assert len(boot) > 0

    return {
        "stable_jsd": float(stable["jsd"]),
        "shifted_jsd": float(shift["jsd"]),
        "shift_detected_beyond_random_p95": bool(
            shift_random["chronological_above_random_p95_jsd"]
        ),
        "bootstrap_edges": int(len(boot)),
        "status": "ok",
    }
