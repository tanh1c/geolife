"""Stage 10f — chronological TRAIN-only CP2 anchor persistence (research only).

- Per-user split on 70% of observed UTC arrival dates; cutoff-crossing stays
  excluded from BOTH folds.
- Fit complete-link 200m CP2 semantic clusters and HOME/OFFICE emission using
  only TRAIN stays; never import full-history candidate labels/coordinates
  or full-history dropout stability as predictors.
- Resolve FUTURE local time but DO NOT fit clusters on FUTURE. A future stay
  matches a training location only if it lies within 200m of EVERY training
  stay in that location (complete-link-compatible extension), and only one
  train location qualifies; otherwise mark unmatched/ambiguous.
- Evaluate same-TRAIN-anchor future HOME-night / OFFICE-weekday-window
  reappearance conditioned on observed future window support (>=600 seconds).
- No ground-truth HOME/OFFICE labels, calibrated correctness, score-v2
  replacement, public release or new GPS stay extraction.
- Private row-level output remains ONLY in the trusted existing Modal Volume.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

from geolife.geo.distance import haversine_m
from geolife.model import HomeOfficeConfig, build_semantic_locations
from geolife.model import home_office as cp2


UNMATCHED_ID = -1
AMBIGUOUS_ID = -2
EXPECTED_CP1_STAYS = 5821
EXPECTED_USERS = 136


def partition_stays(
    stays: pd.DataFrame, *, train_fraction: float = 0.70
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Keep only non-straddling stays in earlier/later folds per UTC arrival-date."""
    if not 0.5 <= train_fraction <= 0.9:
        raise ValueError("train_fraction must be between 0.5 and 0.9")
    frame = cp2._validate_stays(stays)  # same CP2 input schema/UTC parsing
    earlier, later, records = [], [], []
    for user, g in frame.groupby("user_id", sort=True):
        dates = sorted(g["arrival_time_utc"].dt.floor("D").unique())
        if len(dates) < 2:
            records.append({
                "user_id": user, "observed_utc_dates": len(dates),
                "train_stays": 0, "future_stays": 0,
                "cutoff_crossing_excluded": 0, "cutoff_private": pd.NaT,
            })
            continue
        split_at = min(max(1, math.ceil(len(dates) * train_fraction)), len(dates) - 1)
        cutoff = pd.Timestamp(dates[split_at])
        train = g.loc[g["departure_time_utc"].le(cutoff)]
        future = g.loc[g["arrival_time_utc"].ge(cutoff)]
        if not train.empty:
            earlier.append(train)
        if not future.empty:
            later.append(future)
        records.append({
            "user_id": user, "observed_utc_dates": len(dates),
            "train_stays": int(len(train)), "future_stays": int(len(future)),
            "cutoff_crossing_excluded": int(len(g) - len(train) - len(future)),
            "cutoff_private": cutoff,
        })
    train_frame = (
        pd.concat(earlier, ignore_index=True)
        if earlier else frame.iloc[0:0].copy()
    )
    future_frame = (
        pd.concat(later, ignore_index=True)
        if later else frame.iloc[0:0].copy()
    )
    split_table = pd.DataFrame(records)
    if len(train_frame) + len(future_frame) + int(
        split_table["cutoff_crossing_excluded"].sum()
    ) > len(frame):
        raise ValueError("Duplicate stay allocation")
    # CP2 train must not contain an observation ending after test begins.
    for user in set(train_frame["user_id"]) & set(future_frame["user_id"]):
        t = train_frame.loc[train_frame["user_id"].eq(user), "departure_time_utc"]
        f = future_frame.loc[future_frame["user_id"].eq(user), "arrival_time_utc"]
        if t.max() > f.min():
            raise ValueError("Temporal leakage across train/future")
    return train_frame, future_frame, split_table


def align_to_train_locations(
    future_semantic: pd.DataFrame,
    train_semantic: pd.DataFrame,
    *,
    max_diameter_m: float = 200.0,
) -> pd.DataFrame:
    """Spatially project future stays to FROZEN TRAIN cluster member sets.

    The method is intentionally conservative; it does not rerun complete-link
    with future stays nor guarantee new temporally discovered clusters.
    """
    if max_diameter_m <= 0:
        raise ValueError("max_diameter_m must be positive")
    required = {"user_id", "location_id", "latitude", "longitude"}
    if required - set(train_semantic.columns):
        raise ValueError("Missing training semantic cluster members")
    if (required - {"location_id"}) - set(future_semantic.columns):
        raise ValueError("Missing future stay coordinates")
    future = future_semantic.copy()
    future["location_id"] = UNMATCHED_ID
    future["spatial_match_status"] = "not_matched"
    reference = {
        str(user): {int(loc): group[["latitude", "longitude"]].to_numpy(dtype=float)
                    for loc, group in u.groupby("location_id")}
        for user, u in train_semantic.groupby("user_id")
    }
    for idx, stay in future.iterrows():
        options = []
        for location_id, points in reference.get(str(stay["user_id"]), {}).items():
            distances = np.asarray(
                haversine_m(
                    float(stay["latitude"]), float(stay["longitude"]),
                    points[:, 0], points[:, 1],
                ), dtype=float,
            )
            if (distances <= max_diameter_m + 1e-6).all():
                options.append(location_id)
        if len(options) == 1:
            future.at[idx, "location_id"] = options[0]
            future.at[idx, "spatial_match_status"] = "matched"
        elif len(options) > 1:
            future.at[idx, "location_id"] = AMBIGUOUS_ID
            future.at[idx, "spatial_match_status"] = "ambiguous"
    return future


def train_only_emissions(
    train: pd.DataFrame, *,
    config: HomeOfficeConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Exactly CP2 frozen _top_candidate and _emit_label, on TRAIN only."""
    semantic, locations = build_semantic_locations(train, config=config)
    if len(semantic) != len(train):
        raise ValueError("Some TRAIN stays failed timezone resolution")
    if semantic.empty:
        return cp2._empty_output(), semantic
    features = cp2._location_features(semantic, locations, config=config)
    outputs = []
    for label, min_dates, min_share, min_margin in (
        ("HOME", config.home_min_dates, config.home_min_share, config.home_min_margin),
        ("OFFICE", config.office_min_dates, config.office_min_share, config.office_min_margin),
    ):
        top = cp2._top_candidate(features, label=label, min_dates=min_dates)
        emitted = cp2._emit_label(
            top, label=label, min_share=min_share, min_margin=min_margin,
            support_saturation_dates=config.support_saturation_dates,
        )
        if not emitted.empty:
            eligible_count = (
                (features["stay_count"] >= 2)
                & (features[f"{label.lower()}_dates"] >= min_dates)
                & (features[f"{label.lower()}_dwell_s"] > 0)
            )
            by_user = features.loc[eligible_count].groupby("user_id").size()
            emitted["train_eligible_location_count"] = (
                emitted["user_id"].map(by_user).astype(int)
            )
            outputs.append(emitted)
    if not outputs:
        return cp2._empty_output(), semantic
    return pd.concat(outputs, ignore_index=True), semantic


def evaluate_future_windows(
    train_emissions: pd.DataFrame,
    aligned_future: pd.DataFrame,
    *,
    config: HomeOfficeConfig,
) -> pd.DataFrame:
    """Assess observed same-place window recurrence, not semantic correctness."""
    if train_emissions.empty:
        return pd.DataFrame()
    results = []
    for label, candidates in train_emissions.groupby("label"):
        kind = label.lower()
        contrib = cp2._window_contributions(aligned_future, config=config, kind=kind)
        if contrib.empty:
            observed_dates = {}
            candidate_dates = {}
            candidate_dwell = {}
            total_dwell = {}
        else:
            date_totals = (
                contrib.groupby(["user_id", "behavior_date"], as_index=False)["overlap_s"]
                .sum()
            )
            observed_dates = (
                date_totals.loc[date_totals["overlap_s"].ge(config.min_relevant_date_overlap_s)]
                .groupby("user_id").size().to_dict()
            )
            agg = cp2._aggregate_window(
                contrib, prefix=kind,
                min_date_overlap_s=config.min_relevant_date_overlap_s,
            )
            candidate_dates = {
                (str(x.user_id), int(x.location_id)): int(getattr(x, f"{kind}_dates"))
                for x in agg.itertuples(index=False)
            }
            candidate_dwell = {
                (str(x.user_id), int(x.location_id)): float(getattr(x, f"{kind}_dwell_s"))
                for x in agg.itertuples(index=False)
            }
            total_dwell = contrib.groupby("user_id")["overlap_s"].sum().to_dict()
        for row in candidates.itertuples(index=False):
            user, loc = str(row.user_id), int(row.location_id)
            opp = int(observed_dates.get(user, 0))
            n_dates = int(candidate_dates.get((user, loc), 0))
            dwell = float(candidate_dwell.get((user, loc), 0))
            denom = float(total_dwell.get(user, 0))
            results.append({
                "user_id": user, "label": label, "train_location_id": loc,
                "train_evidence_strength": float(row.evidence_strength),
                "train_support_dates": int(row.relevant_dates),
                "train_eligible_location_count": int(row.train_eligible_location_count),
                "future_observed_window_dates": opp,
                "future_same_anchor_window_dates": n_dates,
                "future_same_anchor_window_dwell_share": (
                    dwell / denom if denom > 0 else np.nan
                ),
                "future_window_assessable": opp >= 1,
                "future_same_anchor_reappears": opp >= 1 and n_dates >= 1,
            })
    return pd.DataFrame(results)


def aggregate_forward(
    private_eval: pd.DataFrame,
    partition: pd.DataFrame,
    aligned_future: pd.DataFrame,
    *,
    n_train_users: int,
) -> dict:
    """Print only aggregate totals, including abstentions and sparse holdout."""
    def summarize(subset: pd.DataFrame) -> dict:
        available = subset.loc[subset["future_window_assessable"]]
        return {
            "train_emitted_candidates": int(len(subset)),
            "future_window_assessable": int(len(available)),
            "future_same_anchor_reappears": int(
                available["future_same_anchor_reappears"].sum()
            ),
            "future_window_unassessable": int(len(subset) - len(available)),
            "train_sole_eligible_anchor": int(
                subset["train_eligible_location_count"].eq(1).sum()
            ),
            "train_multiple_eligible_anchors": int(
                subset["train_eligible_location_count"].ge(2).sum()
            ),
        }

    if private_eval.empty:
        overall = {
            "train_emitted_candidates": 0, "future_window_assessable": 0,
            "future_same_anchor_reappears": 0, "future_window_unassessable": 0,
            "train_sole_eligible_anchor": 0, "train_multiple_eligible_anchors": 0,
        }
        groups = []
    else:
        overall = summarize(private_eval)
        groups = [
            {"label": str(label), **summarize(g)}
            for label, g in private_eval.groupby("label", sort=True)
        ]
    return {
        "experiment": "stage10f_train_only_future_anchor_reappearance",
        "ground_truth_semantic_accuracy": None,
        "calibrated_probability": None,
        "train_only_spatial_clusters": True,
        "future_refitting": False,
        "per_user_split": "70% early UTC observed arrival dates, 30% later; straddling stays excluded",
        "train_users_with_stays": n_train_users,
        "users_with_cutoff_crossing_stays": int(
            partition["cutoff_crossing_excluded"].gt(0).sum()
        ),
        "spatial_future_stays": {
            str(k): int(v)
            for k, v in aligned_future["spatial_match_status"].value_counts().items()
        },
        "overall": overall,
        "labels": groups,
        "notes": (
            "Retrospective observed exact train-anchor future window reappearance, "
            "not semantic HOME/OFFICE truth or a prospective app destination hit-rate. "
            "Outcomes depend on observed future GPS, time-window opportunity, "
            "strict complete-link-compatible matching, and per-user date split. "
            "No full-period Stage10a tier, candidate ID, or dropout R was used "
            "to select/train predictions. Train-only score-to-retention comparisons "
            "and independent replication remain separate future work."
        ),
    }


def forward_validate(
    stays: pd.DataFrame,
    *,
    train_fraction: float = 0.70,
    config: HomeOfficeConfig | None = None,
) -> tuple[dict, pd.DataFrame, pd.DataFrame]:
    """Evaluate all users, not future-selected Stage10a candidate subset."""
    cfg = config or HomeOfficeConfig()
    if cfg.clustering_method != "complete_link":
        raise ValueError("Only frozen complete-link train geometry is supported")
    train, future, partitions = partition_stays(stays, train_fraction=train_fraction)
    if train.empty or future.empty:
        raise ValueError("No usable train and future stays")
    train_emitted, train_semantic = train_only_emissions(train, config=cfg)
    future_semantic = cp2._resolve_stay_timezones(cp2._validate_stays(future))
    if len(future_semantic) != len(future):
        raise ValueError("Some FUTURE stays failed timezone resolution")
    future_aligned = align_to_train_locations(
        future_semantic, train_semantic, max_diameter_m=cfg.location_max_diameter_m
    )
    evaluated = evaluate_future_windows(
        train_emitted, future_aligned, config=cfg
    )
    report = aggregate_forward(
        evaluated, partitions, future_aligned,
        n_train_users=int(train_semantic["user_id"].nunique()),
    )
    return report, evaluated, partitions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--stays-cache", type=Path,
        default=Path("/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl"),
    )
    parser.add_argument(
        "--cache-root", type=Path,
        default=Path("/mnt/geolife-data/cache/cp2_v2"),
    )
    parser.add_argument("--train-fraction", type=float, default=0.70)
    args = parser.parse_args()
    if not args.stays_cache.is_file():
        parser.error("Missing trusted frozen CP1 stays cache")
    # Pickle input ONLY from trusted user-controlled Modal Volume.
    stays = pd.read_pickle(args.stays_cache)
    if len(stays) != EXPECTED_CP1_STAYS or stays["user_id"].astype(str).nunique() != EXPECTED_USERS:
        raise ValueError("CP1 parity drift; abort")
    report, evaluated, partitions = forward_validate(
        stays, train_fraction=args.train_fraction
    )
    out = args.cache_root / "10_evidence_v2_offline"
    out.mkdir(parents=True, exist_ok=True)
    # Includes user IDs and exact train cluster IDs: strictly private, not to Git.
    evaluated.to_pickle(out / "train_only_forward_candidates_private.pkl")
    partitions.to_pickle(out / "train_only_forward_partitions_private.pkl")
    (out / "train_only_forward_aggregate.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
