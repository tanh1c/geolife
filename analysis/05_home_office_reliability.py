"""Behavioral reliability validation for GeoLife Home/Office inference.

This module intentionally starts after frozen CP1 stay detection and the frozen
complete-link 200 m spatial representation. It evaluates semantic reliability
without treating any heuristic as ground truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
import pandas as pd

from geolife.model import HomeOfficeConfig, infer_home_office
from geolife.model import home_office as home_office_model

METHOD_FIXED = "fixed_window"
METHOD_HOWDE = "howde_style"
METHOD_RECURRENCE = "recurrence"
METHODS = (METHOD_FIXED, METHOD_HOWDE, METHOD_RECURRENCE)
LABELS = ("HOME", "OFFICE")

HOWDE_HOME_HOURS = tuple(range(0, 6))
HOWDE_WORK_HOURS = tuple(range(9, 16))
HOWDE_MIN_DAILY_COVERAGE = 0.40
MIN_SUPPORT_DAYS = 3
MIN_RECURRING_STAYS = 2


@dataclass(frozen=True)
class ReliabilityBundle:
    assignments: pd.DataFrame
    baseline_emissions: pd.DataFrame
    cross_method: pd.DataFrame
    split_summary: pd.DataFrame
    split_details: pd.DataFrame
    holdout_summary: pd.DataFrame
    holdout_details: pd.DataFrame
    dropout_summary: pd.DataFrame
    dropout_details: pd.DataFrame
    time_shift_summary: pd.DataFrame
    time_shift_details: pd.DataFrame


def _empty_assignments() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "user_id",
            "method",
            "label",
            "location_id",
            "score",
            "support_days",
            "emitted",
        ]
    )


def summarize_locations(stays: pd.DataFrame) -> pd.DataFrame:
    """Summarize an already-clustered subset without changing location IDs."""
    if stays.empty:
        return pd.DataFrame(
            columns=[
                "user_id",
                "location_id",
                "latitude",
                "longitude",
                "stay_count",
                "active_local_dates",
                "total_dwell_h",
                "diameter_m",
            ]
        )

    frame = stays.copy()
    frame["arrival_time_local"] = pd.to_datetime(frame["arrival_time_local"])
    rows = []
    for (user_id, location_id), group in frame.groupby(
        ["user_id", "location_id"], sort=True
    ):
        rows.append(
            {
                "user_id": str(user_id),
                "location_id": int(location_id),
                "latitude": float(group["latitude"].median()),
                "longitude": float(group["longitude"].median()),
                "stay_count": int(len(group)),
                "active_local_dates": int(
                    group["arrival_time_local"].dt.date.nunique()
                ),
                "total_dwell_h": float(group["duration_s"].sum() / 3600.0),
                "diameter_m": np.nan,
            }
        )
    return pd.DataFrame(rows)


def _fixed_window_assignments(
    stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig,
) -> pd.DataFrame:
    """Rank current fixed-window candidates, including non-emitted top candidates."""
    locations = summarize_locations(stays)
    if stays.empty or locations.empty:
        return _empty_assignments()

    features = home_office_model._location_features(stays, locations, config=config)
    rows = []
    specs = (
        (
            "HOME",
            config.home_min_dates,
            config.home_min_share,
            config.home_min_margin,
        ),
        (
            "OFFICE",
            config.office_min_dates,
            config.office_min_share,
            config.office_min_margin,
        ),
    )
    for label, min_dates, min_share, min_margin in specs:
        top = home_office_model._top_candidate(
            features,
            label=label,
            min_dates=min_dates,
        )
        for row in top.itertuples(index=False):
            rows.append(
                {
                    "user_id": str(row.user_id),
                    "method": METHOD_FIXED,
                    "label": label,
                    "location_id": int(row.location_id),
                    "score": float(row.relevant_dwell_share),
                    "support_days": int(row.relevant_dates),
                    "emitted": bool(
                        row.relevant_dwell_share >= min_share
                        and row.share_margin >= min_margin
                    ),
                }
            )
    return pd.DataFrame(rows, columns=_empty_assignments().columns)


def _hourly_dominant_bins(stays: pd.DataFrame) -> pd.DataFrame:
    """Convert stay intervals to HoWDe-style dominant location per observed hour."""
    rows: list[dict[str, object]] = []
    for row in stays.itertuples(index=False):
        start = pd.Timestamp(row.arrival_time_local)
        end = pd.Timestamp(row.departure_time_local)
        if pd.isna(start) or pd.isna(end) or end <= start:
            continue
        cursor = start.floor("h")
        while cursor < end:
            next_hour = cursor + pd.Timedelta(hours=1)
            overlap_start = max(start, cursor)
            overlap_end = min(end, next_hour)
            overlap_s = float((overlap_end - overlap_start).total_seconds())
            if overlap_s > 0:
                rows.append(
                    {
                        "user_id": str(row.user_id),
                        "location_id": int(row.location_id),
                        "hour_start": cursor,
                        "local_date": cursor.date(),
                        "weekday": int(cursor.weekday()),
                        "hour": int(cursor.hour),
                        "overlap_s": overlap_s,
                    }
                )
            cursor = next_hour

    if not rows:
        return pd.DataFrame(
            columns=[
                "user_id",
                "hour_start",
                "local_date",
                "weekday",
                "hour",
                "location_id",
                "overlap_s",
            ]
        )

    raw = pd.DataFrame(rows)
    aggregated = (
        raw.groupby(
            [
                "user_id",
                "hour_start",
                "local_date",
                "weekday",
                "hour",
                "location_id",
            ],
            as_index=False,
        )["overlap_s"]
        .sum()
        .sort_values(
            ["user_id", "hour_start", "overlap_s", "location_id"],
            ascending=[True, True, False, True],
            kind="stable",
        )
    )
    return aggregated.drop_duplicates(["user_id", "hour_start"], keep="first")


def _howde_label_scores(
    bins: pd.DataFrame,
    locations: pd.DataFrame,
    *,
    label: str,
) -> pd.DataFrame:
    if label == "HOME":
        target_hours = HOWDE_HOME_HOURS
        day_filter = pd.Series(True, index=bins.index)
        primary = "mean_hour_fraction"
    elif label == "OFFICE":
        target_hours = HOWDE_WORK_HOURS
        day_filter = bins["weekday"].lt(5)
        primary = "visited_day_share"
    else:
        raise ValueError(label)

    target = bins.loc[day_filter & bins["hour"].isin(target_hours)].copy()
    if target.empty:
        return pd.DataFrame()

    coverage = (
        target.groupby(["user_id", "local_date"], as_index=False)["hour_start"]
        .nunique()
        .rename(columns={"hour_start": "observed_hours"})
    )
    required_hours = int(np.ceil(HOWDE_MIN_DAILY_COVERAGE * len(target_hours)))
    valid_days = coverage.loc[coverage["observed_hours"] >= required_hours].copy()
    if valid_days.empty:
        return pd.DataFrame()

    valid = target.merge(valid_days, on=["user_id", "local_date"], how="inner")
    per_day = (
        valid.groupby(["user_id", "local_date", "location_id"], as_index=False)
        .agg(
            location_hours=("hour_start", "nunique"),
            observed_hours=("observed_hours", "first"),
        )
    )
    per_day["hour_fraction"] = per_day["location_hours"] / per_day["observed_hours"]

    support = (
        valid_days.groupby("user_id", as_index=False)["local_date"]
        .nunique()
        .rename(columns={"local_date": "valid_days"})
    )
    scores = (
        per_day.groupby(["user_id", "location_id"], as_index=False)
        .agg(
            mean_hour_fraction=("hour_fraction", "mean"),
            visited_days=("local_date", "nunique"),
        )
        .merge(support, on="user_id", how="left")
    )
    scores["visited_day_share"] = scores["visited_days"] / scores["valid_days"]
    scores = scores.merge(
        locations[["user_id", "location_id", "stay_count"]],
        on=["user_id", "location_id"],
        how="left",
    )
    scores = scores.loc[
        scores["valid_days"].ge(MIN_SUPPORT_DAYS)
        & scores["stay_count"].ge(MIN_RECURRING_STAYS)
    ].copy()
    if scores.empty:
        return scores

    secondary = (
        "visited_day_share"
        if primary == "mean_hour_fraction"
        else "mean_hour_fraction"
    )
    return scores.sort_values(
        ["user_id", primary, secondary, "visited_days", "location_id"],
        ascending=[True, False, False, False, True],
        kind="stable",
    )


def _howde_style_assignments(stays: pd.DataFrame) -> pd.DataFrame:
    """Static full-period HoWDe-inspired ranker, not a reproduction of HoWDe."""
    locations = summarize_locations(stays)
    bins = _hourly_dominant_bins(stays)
    if locations.empty or bins.empty:
        return _empty_assignments()

    rows = []
    for label in LABELS:
        scores = _howde_label_scores(bins, locations, label=label)
        if scores.empty:
            continue
        top = scores.groupby("user_id", sort=True).head(1)
        for row in top.itertuples(index=False):
            score = (
                float(row.mean_hour_fraction)
                if label == "HOME"
                else float(row.visited_day_share)
            )
            rows.append(
                {
                    "user_id": str(row.user_id),
                    "method": METHOD_HOWDE,
                    "label": label,
                    "location_id": int(row.location_id),
                    "score": score,
                    "support_days": int(row.valid_days),
                    "emitted": False,
                }
            )
    return pd.DataFrame(rows, columns=_empty_assignments().columns)


def _recurrence_assignments(stays: pd.DataFrame) -> pd.DataFrame:
    """Schedule-light comparator: dwell-heavy HOME and weekday-recurrent alternate WORK."""
    if stays.empty:
        return _empty_assignments()
    frame = stays.copy()
    frame["arrival_time_local"] = pd.to_datetime(frame["arrival_time_local"])
    frame["local_date"] = frame["arrival_time_local"].dt.date
    frame["weekday"] = frame["arrival_time_local"].dt.weekday
    stats = (
        frame.groupby(["user_id", "location_id"], as_index=False)
        .agg(
            stay_count=("location_id", "size"),
            total_dwell_s=("duration_s", "sum"),
            active_days=("local_date", "nunique"),
        )
    )
    weekday = (
        frame.loc[frame["weekday"].lt(5)]
        .groupby(["user_id", "location_id"], as_index=False)["local_date"]
        .nunique()
        .rename(columns={"local_date": "weekday_days"})
    )
    stats = stats.merge(weekday, on=["user_id", "location_id"], how="left")
    stats["weekday_days"] = stats["weekday_days"].fillna(0).astype(int)
    stats = stats.loc[stats["stay_count"] >= MIN_RECURRING_STAYS].copy()
    if stats.empty:
        return _empty_assignments()

    rows = []
    for user_id, group in stats.groupby("user_id", sort=True):
        home = group.sort_values(
            ["total_dwell_s", "active_days", "stay_count", "location_id"],
            ascending=[False, False, False, True],
            kind="stable",
        ).iloc[0]
        total_dwell = float(group["total_dwell_s"].sum())
        rows.append(
            {
                "user_id": str(user_id),
                "method": METHOD_RECURRENCE,
                "label": "HOME",
                "location_id": int(home.location_id),
                "score": (
                    float(home.total_dwell_s / total_dwell)
                    if total_dwell > 0
                    else 0.0
                ),
                "support_days": int(home.active_days),
                "emitted": False,
            }
        )

        alternatives = group.loc[group["location_id"].ne(home.location_id)].copy()
        if alternatives.empty:
            continue
        work = alternatives.sort_values(
            [
                "weekday_days",
                "active_days",
                "stay_count",
                "total_dwell_s",
                "location_id",
            ],
            ascending=[False, False, False, False, True],
            kind="stable",
        ).iloc[0]
        if int(work.weekday_days) < MIN_SUPPORT_DAYS:
            continue
        max_weekday_days = max(int(group["weekday_days"].max()), 1)
        rows.append(
            {
                "user_id": str(user_id),
                "method": METHOD_RECURRENCE,
                "label": "OFFICE",
                "location_id": int(work.location_id),
                "score": float(work.weekday_days / max_weekday_days),
                "support_days": int(work.weekday_days),
                "emitted": False,
            }
        )
    return pd.DataFrame(rows, columns=_empty_assignments().columns)


def infer_assignments(
    stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
    methods: Iterable[str] = METHODS,
) -> pd.DataFrame:
    cfg = config or HomeOfficeConfig()
    requested = tuple(methods)
    frames = []
    if METHOD_FIXED in requested:
        frames.append(_fixed_window_assignments(stays, config=cfg))
    if METHOD_HOWDE in requested:
        frames.append(_howde_style_assignments(stays))
    if METHOD_RECURRENCE in requested:
        frames.append(_recurrence_assignments(stays))
    unknown = set(requested).difference(METHODS)
    if unknown:
        raise ValueError(f"unknown methods: {sorted(unknown)}")
    frames = [frame for frame in frames if not frame.empty]
    if not frames:
        return _empty_assignments()
    out = pd.concat(frames, ignore_index=True)
    return out.sort_values(
        ["method", "label", "user_id"], kind="stable"
    ).reset_index(drop=True)


def baseline_emission_parity(
    raw_stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
) -> pd.DataFrame:
    cfg = config or HomeOfficeConfig()
    baseline = infer_home_office(raw_stays, config=cfg)
    return (
        baseline.groupby("label", as_index=False)
        .agg(
            emitted_users=("user_id", "nunique"),
            emitted_rows=("location_id", "size"),
        )
        .sort_values("label", kind="stable")
        .reset_index(drop=True)
    )


def cross_method_agreement(assignments: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for label in LABELS:
        subset = assignments.loc[assignments["label"].eq(label)]
        for index, left in enumerate(METHODS):
            for right in METHODS[index + 1 :]:
                a = subset.loc[
                    subset["method"].eq(left),
                    ["user_id", "location_id"],
                ]
                b = subset.loc[
                    subset["method"].eq(right),
                    ["user_id", "location_id"],
                ]
                merged = a.merge(
                    b,
                    on="user_id",
                    suffixes=("_left", "_right"),
                )
                same = merged["location_id_left"].eq(merged["location_id_right"])
                rows.append(
                    {
                        "label": label,
                        "left_method": left,
                        "right_method": right,
                        "both_users": int(len(merged)),
                        "same_location_users": int(same.sum()),
                        "agreement_share": (
                            float(same.mean()) if len(merged) else np.nan
                        ),
                    }
                )
    return pd.DataFrame(rows)


def _date_split_mask(stays: pd.DataFrame, kind: str) -> pd.Series:
    dates = pd.to_datetime(stays["arrival_time_local"]).dt.date
    mask = pd.Series(False, index=stays.index)
    temp = stays[["user_id"]].copy()
    temp["local_date"] = dates
    for _, indices in temp.groupby("user_id").groups.items():
        user_dates = sorted(temp.loc[indices, "local_date"].unique())
        if kind == "first_second":
            cutoff = max(1, len(user_dates) // 2)
            left_dates = set(user_dates[:cutoff])
        elif kind == "odd_even":
            left_dates = {
                day
                for day in user_dates
                if pd.Timestamp(day).isocalendar().week % 2 == 1
            }
        elif kind == "train_holdout":
            cutoff = max(1, int(np.floor(len(user_dates) * 0.60)))
            left_dates = set(user_dates[:cutoff])
        else:
            raise ValueError(kind)
        mask.loc[indices] = temp.loc[indices, "local_date"].isin(left_dates)
    return mask


def _agreement_from_two(
    left: pd.DataFrame,
    right: pd.DataFrame,
    *,
    split_name: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    merged = left.merge(
        right,
        on=["user_id", "method", "label"],
        suffixes=("_left", "_right"),
    )
    if merged.empty:
        details = merged.assign(
            split=split_name,
            same_location=pd.Series(dtype=bool),
        )
    else:
        merged["same_location"] = merged["location_id_left"].eq(
            merged["location_id_right"]
        )
        merged["split"] = split_name
        details = merged
    summary = (
        details.groupby(["split", "method", "label"], as_index=False)
        .agg(
            both_halves=("user_id", "size"),
            same_location=("same_location", "sum"),
            agreement_share=("same_location", "mean"),
        )
        if not details.empty
        else pd.DataFrame(
            columns=[
                "split",
                "method",
                "label",
                "both_halves",
                "same_location",
                "agreement_share",
            ]
        )
    )
    return summary, details


def split_half_reliability(
    stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = config or HomeOfficeConfig()
    summaries = []
    details = []
    for split_name in ("first_second", "odd_even"):
        left_mask = _date_split_mask(stays, split_name)
        left = infer_assignments(stays.loc[left_mask].copy(), config=cfg)
        right = infer_assignments(stays.loc[~left_mask].copy(), config=cfg)
        summary, detail = _agreement_from_two(
            left,
            right,
            split_name=split_name,
        )
        summaries.append(summary)
        details.append(detail)
    return (
        pd.concat(summaries, ignore_index=True),
        pd.concat(details, ignore_index=True),
    )


def _holdout_location_metrics(stays: pd.DataFrame) -> pd.DataFrame:
    if stays.empty:
        return pd.DataFrame()
    frame = stays.copy()
    frame["arrival_time_local"] = pd.to_datetime(frame["arrival_time_local"])
    frame["local_date"] = frame["arrival_time_local"].dt.date
    frame["weekday"] = frame["arrival_time_local"].dt.weekday
    stats = (
        frame.groupby(["user_id", "location_id"], as_index=False)
        .agg(
            dwell_s=("duration_s", "sum"),
            active_days=("local_date", "nunique"),
            stay_count=("location_id", "size"),
        )
    )
    weekday = (
        frame.loc[frame["weekday"].lt(5)]
        .groupby(["user_id", "location_id"], as_index=False)["local_date"]
        .nunique()
        .rename(columns={"local_date": "weekday_days"})
    )
    stats = stats.merge(
        weekday,
        on=["user_id", "location_id"],
        how="left",
    )
    stats["weekday_days"] = stats["weekday_days"].fillna(0).astype(int)
    totals = (
        frame.groupby("user_id", as_index=False)
        .agg(
            total_dwell_s=("duration_s", "sum"),
            total_active_days=("local_date", "nunique"),
        )
    )
    weekday_totals = (
        frame.loc[frame["weekday"].lt(5)]
        .groupby("user_id", as_index=False)["local_date"]
        .nunique()
        .rename(columns={"local_date": "total_weekday_days"})
    )
    stats = (
        stats.merge(totals, on="user_id", how="left")
        .merge(weekday_totals, on="user_id", how="left")
    )
    stats["total_weekday_days"] = stats["total_weekday_days"].fillna(0)
    stats["dwell_share"] = np.where(
        stats["total_dwell_s"] > 0,
        stats["dwell_s"] / stats["total_dwell_s"],
        0.0,
    )
    stats["active_day_share"] = np.where(
        stats["total_active_days"] > 0,
        stats["active_days"] / stats["total_active_days"],
        0.0,
    )
    stats["weekday_day_share"] = np.where(
        stats["total_weekday_days"] > 0,
        stats["weekday_days"] / stats["total_weekday_days"],
        0.0,
    )
    stats["home_rank"] = (
        stats.groupby("user_id")["dwell_share"]
        .rank(method="min", ascending=False)
    )
    stats["office_rank"] = (
        stats.groupby("user_id")["weekday_day_share"]
        .rank(method="min", ascending=False)
    )
    return stats


def heldout_predictive_validity(
    stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = config or HomeOfficeConfig()
    train_mask = _date_split_mask(stays, "train_holdout")
    train = stays.loc[train_mask].copy()
    holdout = stays.loc[~train_mask].copy()
    assignments = infer_assignments(train, config=cfg)
    metrics = _holdout_location_metrics(holdout)
    details = assignments.merge(
        metrics,
        on=["user_id", "location_id"],
        how="left",
    )
    if details.empty:
        return pd.DataFrame(), details
    details["seen_in_holdout"] = details["stay_count"].fillna(0).gt(0)
    details["heldout_metric"] = np.where(
        details["label"].eq("HOME"),
        details["dwell_share"].fillna(0.0),
        details["weekday_day_share"].fillna(0.0),
    )
    details["heldout_rank"] = np.where(
        details["label"].eq("HOME"),
        details["home_rank"],
        details["office_rank"],
    )
    details["heldout_top1"] = details["heldout_rank"].eq(1)
    summary = (
        details.groupby(["method", "label"], as_index=False)
        .agg(
            train_candidates=("user_id", "size"),
            seen_in_holdout_share=("seen_in_holdout", "mean"),
            heldout_top1_share=("heldout_top1", "mean"),
            median_heldout_metric=("heldout_metric", "median"),
            median_heldout_rank=("heldout_rank", "median"),
        )
    )
    return summary, details


def dropout_robustness(
    stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
    rates: Iterable[float] = (0.10, 0.20, 0.30),
    seeds: Iterable[int] = (11, 23, 42),
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = config or HomeOfficeConfig()
    reference = infer_assignments(stays, config=cfg)
    details = []
    for rate in rates:
        if not 0.0 < rate < 1.0:
            raise ValueError("dropout rates must be in (0, 1)")
        for seed in seeds:
            rng = np.random.default_rng(seed)
            keep = rng.random(len(stays)) >= rate
            perturbed = infer_assignments(
                stays.loc[keep].copy(),
                config=cfg,
            )
            merged = reference.merge(
                perturbed,
                on=["user_id", "method", "label"],
                how="left",
                suffixes=("_reference", "_perturbed"),
            )
            merged["dropout_rate"] = float(rate)
            merged["seed"] = int(seed)
            merged["candidate_retained"] = merged[
                "location_id_reference"
            ].eq(merged["location_id_perturbed"])
            details.append(merged)
    detail = (
        pd.concat(details, ignore_index=True)
        if details
        else pd.DataFrame()
    )
    summary = (
        detail.groupby(
            ["dropout_rate", "method", "label"],
            as_index=False,
        )
        .agg(
            reference_candidates=("user_id", "size"),
            candidate_retention=("candidate_retained", "mean"),
        )
        if not detail.empty
        else pd.DataFrame()
    )
    return summary, detail


def time_shift_stress(
    stays: pd.DataFrame,
    *,
    hours: int = 12,
    config: HomeOfficeConfig | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    cfg = config or HomeOfficeConfig()
    reference = infer_assignments(stays, config=cfg)
    shifted = stays.copy()
    delta = pd.Timedelta(hours=hours)
    shifted["arrival_time_local"] = (
        pd.to_datetime(shifted["arrival_time_local"]) + delta
    )
    shifted["departure_time_local"] = (
        pd.to_datetime(shifted["departure_time_local"]) + delta
    )
    shifted_assignments = infer_assignments(shifted, config=cfg)
    detail = reference.merge(
        shifted_assignments,
        on=["user_id", "method", "label"],
        how="left",
        suffixes=("_reference", "_shifted"),
    )
    detail["shift_hours"] = int(hours)
    detail["candidate_retained"] = detail[
        "location_id_reference"
    ].eq(detail["location_id_shifted"])
    summary = (
        detail.groupby(
            ["shift_hours", "method", "label"],
            as_index=False,
        )
        .agg(
            reference_candidates=("user_id", "size"),
            candidate_retention=("candidate_retained", "mean"),
        )
        if not detail.empty
        else pd.DataFrame()
    )
    return summary, detail


def run_reliability_suite(
    raw_stays: pd.DataFrame,
    semantic_stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
) -> ReliabilityBundle:
    cfg = config or HomeOfficeConfig()
    assignments = infer_assignments(semantic_stays, config=cfg)
    baseline = baseline_emission_parity(raw_stays, config=cfg)
    split_summary, split_details = split_half_reliability(
        semantic_stays,
        config=cfg,
    )
    holdout_summary, holdout_details = heldout_predictive_validity(
        semantic_stays,
        config=cfg,
    )
    dropout_summary, dropout_details = dropout_robustness(
        semantic_stays,
        config=cfg,
    )
    shift_summary, shift_details = time_shift_stress(
        semantic_stays,
        config=cfg,
    )
    return ReliabilityBundle(
        assignments=assignments,
        baseline_emissions=baseline,
        cross_method=cross_method_agreement(assignments),
        split_summary=split_summary,
        split_details=split_details,
        holdout_summary=holdout_summary,
        holdout_details=holdout_details,
        dropout_summary=dropout_summary,
        dropout_details=dropout_details,
        time_shift_summary=shift_summary,
        time_shift_details=shift_details,
    )


def synthetic_self_check() -> dict[str, object]:
    """Small deterministic checks for semantic scoring helpers."""
    tz = "Asia/Shanghai"
    rows = []
    for day in pd.date_range(
        "2026-01-05",
        periods=10,
        freq="D",
        tz=tz,
    ):
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
        if day.weekday() < 5:
            rows.append(
                {
                    "user_id": "u1",
                    "location_id": 1,
                    "arrival_time_local": day + pd.Timedelta(hours=9),
                    "departure_time_local": day + pd.Timedelta(hours=16),
                    "duration_s": 7 * 3600,
                    "latitude": 39.91,
                    "longitude": 116.41,
                }
            )
    stays = pd.DataFrame(rows)
    recurrence = _recurrence_assignments(stays)
    howde = _howde_style_assignments(stays)
    assert int(
        recurrence.loc[
            recurrence["label"].eq("HOME"),
            "location_id",
        ].iloc[0]
    ) == 0
    assert int(
        recurrence.loc[
            recurrence["label"].eq("OFFICE"),
            "location_id",
        ].iloc[0]
    ) == 1
    assert int(
        howde.loc[
            howde["label"].eq("HOME"),
            "location_id",
        ].iloc[0]
    ) == 0
    assert int(
        howde.loc[
            howde["label"].eq("OFFICE"),
            "location_id",
        ].iloc[0]
    ) == 1
    return {
        "rows": len(stays),
        "recurrence_labels": len(recurrence),
        "howde_style_labels": len(howde),
        "status": "ok",
    }
