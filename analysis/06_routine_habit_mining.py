"""Stage 06: routine / habit mining on frozen behavior locations.

This stage intentionally avoids HOME/OFFICE semantics. It mines supported
daily location sequences, directed OD recurrence, cyclic departure-time
regularity, departure-time multimodality, and split-half routine stability.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.mixture import GaussianMixture


PRIMARY_REPEAT_DAYS = 2
PRIMARY_MIN_HALF_DAYS = 3
PRIMARY_TIME_MODEL_TRANSITIONS = 6
TIME_MODEL_RANDOM_STATE = 42


@dataclass(frozen=True)
class RoutineAudit:
    day_sequences: pd.DataFrame
    transitions: pd.DataFrame
    edge_summary: pd.DataFrame
    user_summary: pd.DataFrame
    split_half: pd.DataFrame
    sensitivity: pd.DataFrame


def circular_hour_stats(values) -> tuple[float, float]:
    x = pd.to_numeric(pd.Series(values), errors="coerce").dropna().to_numpy(float)
    if len(x) == 0:
        return np.nan, np.nan
    theta = 2 * np.pi * (x % 24) / 24
    s, c = float(np.mean(np.sin(theta))), float(np.mean(np.cos(theta)))
    concentration = float(np.hypot(s, c))
    angle = float(np.arctan2(s, c))
    if angle < 0:
        angle += 2 * np.pi
    return 24 * angle / (2 * np.pi), concentration


def fit_departure_time_modes(
    values,
    *,
    min_transitions: int = PRIMARY_TIME_MODEL_TRANSITIONS,
    max_components: int = 3,
    random_state: int = TIME_MODEL_RANDOM_STATE,
) -> dict[str, object]:
    hours = pd.to_numeric(pd.Series(values), errors="coerce").dropna().to_numpy(float) % 24
    if len(hours) < min_transitions:
        return {
            "time_model_supported": False,
            "time_mode_count": pd.NA,
            "time_mode_centers": tuple(),
            "time_mode_weights": tuple(),
            "bic_gain_vs_1": np.nan,
        }

    center, _ = circular_hour_stats(hours)
    unwrapped = (((hours - center + 12) % 24) - 12).reshape(-1, 1)
    distinct = int(np.unique(np.round(unwrapped.reshape(-1), 6)).size)
    max_k = max(1, min(max_components, len(hours) // 2, distinct))

    fits = []
    for k in range(1, max_k + 1):
        model = GaussianMixture(
            n_components=k,
            covariance_type="full",
            random_state=random_state,
            n_init=5,
        ).fit(unwrapped)
        fits.append((k, model, float(model.bic(unwrapped))))

    best_k, best_model, best_bic = min(fits, key=lambda item: item[2])
    bic_1 = next(bic for k, _model, bic in fits if k == 1)
    centers = (center + best_model.means_.reshape(-1)) % 24
    weights = best_model.weights_.reshape(-1)
    order = np.argsort(centers)

    return {
        "time_model_supported": True,
        "time_mode_count": int(best_k),
        "time_mode_centers": tuple(float(v) for v in centers[order]),
        "time_mode_weights": tuple(float(v) for v in weights[order]),
        "bic_gain_vs_1": float(bic_1 - best_bic),
    }


def _eligible_days(daily_support: pd.DataFrame) -> pd.DataFrame:
    required = {"user_id", "local_date", "usable_for_motif"}
    missing = required.difference(daily_support.columns)
    if missing:
        raise ValueError(f"daily_support missing required columns: {sorted(missing)}")
    out = daily_support.loc[
        daily_support["usable_for_motif"].fillna(False).astype(bool),
        ["user_id", "local_date"],
    ].drop_duplicates()
    out["user_id"] = out["user_id"].astype(str)
    return out


def build_supported_day_sequences(
    clustered_stays: pd.DataFrame,
    daily_support: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = {
        "user_id", "location_id", "arrival_time_utc", "departure_time_utc",
        "arrival_time_local", "departure_time_local",
    }
    missing = required.difference(clustered_stays.columns)
    if missing:
        raise ValueError(f"clustered_stays missing required columns: {sorted(missing)}")

    stays = clustered_stays.copy()
    stays["user_id"] = stays["user_id"].astype(str)
    stays["arrival_time_utc"] = pd.to_datetime(stays["arrival_time_utc"], utc=True)
    stays["departure_time_utc"] = pd.to_datetime(stays["departure_time_utc"], utc=True)
    stays["local_date"] = stays["arrival_time_local"].map(
        lambda value: value.date() if pd.notna(value) else pd.NaT
    )
    stays = stays.merge(
        _eligible_days(daily_support).assign(_eligible_day=True),
        on=["user_id", "local_date"],
        how="inner",
        validate="many_to_one",
    )

    sequence_rows, transition_rows = [], []
    for (user_id, local_date), day in stays.groupby(["user_id", "local_date"], sort=True):
        day = day.sort_values(
            ["arrival_time_utc", "departure_time_utc", "location_id"],
            kind="stable",
        )
        segments = []
        for row in day.itertuples(index=False):
            location_id = int(row.location_id)
            if segments and segments[-1]["location_id"] == location_id:
                segments[-1]["departure_time_utc"] = max(
                    segments[-1]["departure_time_utc"], row.departure_time_utc
                )
                segments[-1]["departure_time_local"] = row.departure_time_local
            else:
                segments.append({
                    "location_id": location_id,
                    "arrival_time_utc": row.arrival_time_utc,
                    "departure_time_utc": row.departure_time_utc,
                    "departure_time_local": row.departure_time_local,
                })

        sequence = tuple(seg["location_id"] for seg in segments)
        sequence_rows.append({
            "user_id": str(user_id),
            "local_date": local_date,
            "weekday": int(pd.Timestamp(local_date).weekday()),
            "sequence": sequence,
            "motif": "→".join(f"L{x}" for x in sequence),
            "segment_count": len(sequence),
            "transition_count": max(0, len(sequence) - 1),
        })

        for index, (left, right) in enumerate(zip(segments, segments[1:]), start=1):
            departure = left["departure_time_local"]
            departure_hour = (
                float(departure.hour)
                + float(departure.minute) / 60
                + float(departure.second) / 3600
            )
            transition_rows.append({
                "user_id": str(user_id),
                "local_date": local_date,
                "weekday": int(pd.Timestamp(local_date).weekday()),
                "transition_index": index,
                "origin_location_id": int(left["location_id"]),
                "destination_location_id": int(right["location_id"]),
                "edge": f"L{int(left['location_id'])}→L{int(right['location_id'])}",
                "departure_hour": departure_hour,
                "transition_gap_h": float(
                    (right["arrival_time_utc"] - left["departure_time_utc"]).total_seconds()
                    / 3600
                ),
            })

    return (
        pd.DataFrame(sequence_rows),
        pd.DataFrame(transition_rows),
    )


def summarize_edges(
    transitions: pd.DataFrame,
    day_sequences: pd.DataFrame,
    *,
    time_model_min_transitions: int = PRIMARY_TIME_MODEL_TRANSITIONS,
) -> pd.DataFrame:
    if transitions.empty:
        return pd.DataFrame()

    support = day_sequences.groupby("user_id", as_index=False).agg(
        usable_motif_days=("local_date", "nunique")
    )
    rows = []
    for (user_id, origin, destination), group in transitions.groupby(
        ["user_id", "origin_location_id", "destination_location_id"],
        sort=True,
    ):
        mean_hour, concentration = circular_hour_stats(group["departure_hour"])
        rows.append({
            "user_id": str(user_id),
            "origin_location_id": int(origin),
            "destination_location_id": int(destination),
            "edge": f"L{int(origin)}→L{int(destination)}",
            "transition_count": int(len(group)),
            "active_days": int(group["local_date"].nunique()),
            "weekday_active_days": int(
                group.loc[group["weekday"].lt(5), "local_date"].nunique()
            ),
            "weekend_active_days": int(
                group.loc[group["weekday"].ge(5), "local_date"].nunique()
            ),
            "departure_mean_hour": mean_hour,
            "departure_concentration": concentration,
            **fit_departure_time_modes(
                group["departure_hour"],
                min_transitions=time_model_min_transitions,
            ),
        })

    out = pd.DataFrame(rows).merge(support, on="user_id", validate="many_to_one")
    out["edge_day_share"] = out["active_days"] / out["usable_motif_days"]
    out["repeated_edge"] = out["active_days"].ge(PRIMARY_REPEAT_DAYS)
    totals = out.groupby("user_id")["transition_count"].transform("sum")
    out["transition_share"] = out["transition_count"] / totals
    return out.sort_values(
        [
            "user_id", "active_days", "transition_count",
            "departure_concentration", "origin_location_id",
            "destination_location_id",
        ],
        ascending=[True, False, False, False, True, True],
        kind="stable",
    ).reset_index(drop=True)


def _entropy(counts: pd.Series) -> float:
    x = pd.to_numeric(counts, errors="coerce").dropna().to_numpy(float)
    if len(x) == 0 or x.sum() <= 0:
        return 0.0
    p = x / x.sum()
    return float(-(p * np.log2(p)).sum())


def summarize_users(edge_summary: pd.DataFrame, day_sequences: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for user_id, days in day_sequences.groupby("user_id", sort=True):
        edges = edge_summary.loc[edge_summary["user_id"].eq(str(user_id))]
        motifs = days["motif"].value_counts()
        usable_days = int(days["local_date"].nunique())
        top_motif_frequency = (
            float(motifs.iloc[0] / usable_days) if usable_days and not motifs.empty else 0.0
        )

        if edges.empty:
            rows.append({
                "user_id": str(user_id),
                "usable_motif_days": usable_days,
                "transition_days": 0,
                "total_transitions": 0,
                "distinct_edges": 0,
                "repeated_edges": 0,
                "top_edge_day_share": 0.0,
                "top_edge_transition_share": 0.0,
                "edge_entropy": 0.0,
                "median_repeated_departure_concentration": np.nan,
                "time_model_supported_edges": 0,
                "multimodal_time_edges": 0,
                "exact_top_motif_frequency": top_motif_frequency,
                "exact_motif_repeatable_half": bool(top_motif_frequency >= 0.5),
                "has_repeated_edge": False,
            })
            continue

        repeated = edges.loc[edges["repeated_edge"]]
        modeled = edges.loc[edges["time_model_supported"].fillna(False).astype(bool)]
        top = edges.iloc[0]
        rows.append({
            "user_id": str(user_id),
            "usable_motif_days": usable_days,
            "transition_days": int(
                days.loc[days["transition_count"].gt(0), "local_date"].nunique()
            ),
            "total_transitions": int(edges["transition_count"].sum()),
            "distinct_edges": int(len(edges)),
            "repeated_edges": int(len(repeated)),
            "top_edge_day_share": float(top["edge_day_share"]),
            "top_edge_transition_share": float(top["transition_share"]),
            "edge_entropy": _entropy(edges["transition_count"]),
            "median_repeated_departure_concentration": (
                float(repeated["departure_concentration"].median())
                if not repeated.empty else np.nan
            ),
            "time_model_supported_edges": int(len(modeled)),
            "multimodal_time_edges": int(
                pd.to_numeric(modeled["time_mode_count"], errors="coerce").ge(2).sum()
            ),
            "exact_top_motif_frequency": top_motif_frequency,
            "exact_motif_repeatable_half": bool(top_motif_frequency >= 0.5),
            "has_repeated_edge": bool(len(repeated)),
        })
    return pd.DataFrame(rows)


def _top_edge(transitions: pd.DataFrame, dates: set) -> tuple[tuple[int, int] | None, int]:
    subset = transitions.loc[transitions["local_date"].isin(dates)]
    if subset.empty:
        return None, 0
    ranked = (
        subset.groupby(
            ["origin_location_id", "destination_location_id"],
            as_index=False,
        )
        .agg(
            active_days=("local_date", "nunique"),
            transition_count=("edge", "size"),
        )
        .sort_values(
            [
                "active_days", "transition_count",
                "origin_location_id", "destination_location_id",
            ],
            ascending=[False, False, True, True],
            kind="stable",
        )
    )
    row = ranked.iloc[0]
    return (
        (int(row["origin_location_id"]), int(row["destination_location_id"])),
        int(row["active_days"]),
    )


def split_half_routine_stability(
    transitions: pd.DataFrame,
    day_sequences: pd.DataFrame,
    *,
    min_half_days: int = PRIMARY_MIN_HALF_DAYS,
) -> pd.DataFrame:
    rows = []
    for user_id, days in day_sequences.groupby("user_id", sort=True):
        dates = sorted(days["local_date"].dropna().unique())
        midpoint = len(dates) // 2
        first_dates, second_dates = set(dates[:midpoint]), set(dates[midpoint:])
        eligible = len(first_dates) >= min_half_days and len(second_dates) >= min_half_days
        if not eligible:
            rows.append({
                "user_id": str(user_id),
                "eligible": False,
                "first_half_days": len(first_dates),
                "second_half_days": len(second_dates),
                "first_top_edge": pd.NA,
                "second_top_edge": pd.NA,
                "same_top_edge": pd.NA,
                "first_top_active_days": 0,
                "second_top_active_days": 0,
            })
            continue
        user_transitions = transitions.loc[transitions["user_id"].eq(str(user_id))]
        first_edge, first_active = _top_edge(user_transitions, first_dates)
        second_edge, second_active = _top_edge(user_transitions, second_dates)
        rows.append({
            "user_id": str(user_id),
            "eligible": True,
            "first_half_days": len(first_dates),
            "second_half_days": len(second_dates),
            "first_top_edge": first_edge,
            "second_top_edge": second_edge,
            "same_top_edge": bool(
                first_edge is not None and second_edge is not None and first_edge == second_edge
            ),
            "first_top_active_days": first_active,
            "second_top_active_days": second_active,
        })
    return pd.DataFrame(rows)


def recurrence_sensitivity(
    edge_summary: pd.DataFrame,
    user_summary: pd.DataFrame,
    *,
    repeat_day_thresholds: Iterable[int] = (2, 3, 5),
    concentration_thresholds: Iterable[float] = (0.3, 0.5, 0.7),
) -> pd.DataFrame:
    rows = []
    for repeat_days in repeat_day_thresholds:
        repeated = edge_summary.loc[edge_summary["active_days"].ge(int(repeat_days))]
        for concentration in concentration_thresholds:
            regular = repeated.loc[
                repeated["departure_concentration"].ge(float(concentration))
            ]
            per_user = repeated.groupby("user_id").size() if len(repeated) else pd.Series(dtype=int)
            rows.append({
                "repeat_days": int(repeat_days),
                "departure_concentration_threshold": float(concentration),
                "supported_users": int(user_summary["user_id"].nunique()),
                "users_with_repeated_edge": int(repeated["user_id"].nunique()),
                "users_with_repeated_regular_edge": int(regular["user_id"].nunique()),
                "median_repeated_edges_per_repeated_user": (
                    float(per_user.median()) if len(per_user) else 0.0
                ),
            })
    return pd.DataFrame(rows)


def aggregate_report_tables(
    edge_summary: pd.DataFrame,
    user_summary: pd.DataFrame,
    split_half: pd.DataFrame,
) -> dict[str, pd.DataFrame]:
    coverage = pd.DataFrame([{
        "supported_users": int(user_summary["user_id"].nunique()),
        "users_with_any_transition": int(user_summary["total_transitions"].gt(0).sum()),
        "users_with_repeated_edge_ge2_days": int(user_summary["has_repeated_edge"].sum()),
        "users_with_exact_motif_ge50pct": int(user_summary["exact_motif_repeatable_half"].sum()),
        "median_usable_motif_days": float(user_summary["usable_motif_days"].median()),
        "median_distinct_edges": float(user_summary["distinct_edges"].median()),
    }])

    repeated = edge_summary.loc[edge_summary["active_days"].ge(PRIMARY_REPEAT_DAYS)]
    modes = pd.DataFrame([{
        "repeated_edges": int(len(repeated)),
        "repeated_edge_users": int(repeated["user_id"].nunique()),
        "median_departure_concentration": (
            float(repeated["departure_concentration"].median()) if len(repeated) else np.nan
        ),
        "time_model_supported_edges": int(
            repeated["time_model_supported"].fillna(False).astype(bool).sum()
        ),
        "multimodal_time_edges": int(
            pd.to_numeric(repeated["time_mode_count"], errors="coerce").ge(2).sum()
        ),
    }])

    eligible = split_half.loc[split_half["eligible"].fillna(False).astype(bool)]
    both = eligible.loc[
        eligible["first_top_edge"].notna() & eligible["second_top_edge"].notna()
    ]
    stability = pd.DataFrame([{
        "split_eligible_users": int(len(eligible)),
        "users_with_top_edge_both_halves": int(len(both)),
        "same_top_edge_users": int(both["same_top_edge"].fillna(False).astype(bool).sum()),
        "same_top_edge_share": (
            float(both["same_top_edge"].fillna(False).astype(bool).mean())
            if len(both) else np.nan
        ),
    }])
    return {
        "coverage": coverage,
        "departure_time_modes": modes,
        "split_half_stability": stability,
    }


def run_audit(clustered_stays: pd.DataFrame, daily_support: pd.DataFrame) -> RoutineAudit:
    day_sequences, transitions = build_supported_day_sequences(
        clustered_stays, daily_support
    )
    edges = summarize_edges(transitions, day_sequences)
    users = summarize_users(edges, day_sequences)
    split = split_half_routine_stability(transitions, day_sequences)
    return RoutineAudit(
        day_sequences=day_sequences,
        transitions=transitions,
        edge_summary=edges,
        user_summary=users,
        split_half=split,
        sensitivity=recurrence_sensitivity(edges, users),
    )


def synthetic_self_check() -> dict[str, object]:
    tz = "Asia/Shanghai"
    start = pd.Timestamp("2026-01-05", tz=tz)
    stays, support = [], []

    for index in range(14):
        day = start + pd.Timedelta(days=index)
        support.append({
            "user_id": "u1",
            "local_date": day.date(),
            "usable_for_motif": True,
        })
        stays.append({
            "user_id": "u1",
            "location_id": 0,
            "arrival_time_utc": day.tz_convert("UTC"),
            "departure_time_utc": (day + pd.Timedelta(hours=7)).tz_convert("UTC"),
            "arrival_time_local": day,
            "departure_time_local": day + pd.Timedelta(hours=7),
        })
        if day.weekday() < 5:
            stays.extend([
                {
                    "user_id": "u1",
                    "location_id": 1,
                    "arrival_time_utc": (day + pd.Timedelta(hours=8)).tz_convert("UTC"),
                    "departure_time_utc": (day + pd.Timedelta(hours=17)).tz_convert("UTC"),
                    "arrival_time_local": day + pd.Timedelta(hours=8),
                    "departure_time_local": day + pd.Timedelta(hours=17),
                },
                {
                    "user_id": "u1",
                    "location_id": 0,
                    "arrival_time_utc": (day + pd.Timedelta(hours=18)).tz_convert("UTC"),
                    "departure_time_utc": (day + pd.Timedelta(hours=23)).tz_convert("UTC"),
                    "arrival_time_local": day + pd.Timedelta(hours=18),
                    "departure_time_local": day + pd.Timedelta(hours=23),
                },
            ])
        elif index in (5, 12):
            stays.append({
                "user_id": "u1",
                "location_id": 2,
                "arrival_time_utc": (day + pd.Timedelta(hours=12)).tz_convert("UTC"),
                "departure_time_utc": (day + pd.Timedelta(hours=15)).tz_convert("UTC"),
                "arrival_time_local": day + pd.Timedelta(hours=12),
                "departure_time_local": day + pd.Timedelta(hours=15),
            })

    audit = run_audit(pd.DataFrame(stays), pd.DataFrame(support))
    top = audit.edge_summary.iloc[0]
    eligible = audit.split_half.loc[audit.split_half["eligible"]]
    assert int(top["active_days"]) >= 10
    assert float(top["departure_concentration"]) > 0.95
    assert bool(top["repeated_edge"])
    assert not eligible.empty and bool(eligible.iloc[0]["same_top_edge"])
    return {
        "supported_days": int(audit.day_sequences["local_date"].nunique()),
        "transitions": int(len(audit.transitions)),
        "distinct_edges": int(len(audit.edge_summary)),
        "top_edge_active_days": int(top["active_days"]),
        "top_edge_departure_concentration": float(top["departure_concentration"]),
        "split_same_top_edge": bool(eligible.iloc[0]["same_top_edge"]),
        "status": "ok",
    }
