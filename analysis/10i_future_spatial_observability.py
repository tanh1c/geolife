"""Offline Stage10i: spatial support during future HOME/OFFICE observation windows.

Reuses frozen CP2 from TRAIN only and Stage10f private outcomes. The returned
aggregate distinguishes a GPS-observed behavior window from one with a
uniquely matched TRAIN anchor. No semantic truth or score calibration.
Private rows and coordinates never leave the trusted Modal Volume.
"""

from __future__ import annotations
import argparse
import importlib.util
import json
from pathlib import Path
import sys

import pandas as pd
from geolife.model import HomeOfficeConfig
from geolife.model import home_office as cp2


def stage10f_module():
    source = Path(__file__).with_name("10f_train_only_forward_validation.py")
    spec = importlib.util.spec_from_file_location("stage10f_spatial", source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def audit_future_windows(candidates, aligned, config):
    """Construct private per-candidate observed vs uniquely matched future dates."""
    required = {
        "user_id", "label", "train_location_id", "future_observed_window_dates",
        "future_same_anchor_window_dates",
    }
    if required - set(candidates.columns):
        raise ValueError("Missing Stage10f candidate outcome columns")
    rows = []
    for label, group in candidates.groupby("label", sort=True):
        overlap = cp2._window_contributions(
            aligned, config=config, kind=label.lower()
        )
        if overlap.empty:
            dates = pd.DataFrame(columns=[
                "user_id", "behavior_date", "location_id", "overlap_s"
            ])
        else:
            dates = overlap.groupby(
                ["user_id", "behavior_date", "location_id"],
                as_index=False,
            )["overlap_s"].sum()
        for candidate in group.itertuples(index=False):
            user = str(candidate.user_id)
            location = int(candidate.train_location_id)
            own = dates.loc[dates["user_id"].astype(str).eq(user)]
            by_day = own.groupby("behavior_date")["overlap_s"].sum()
            opportunity = int(by_day.ge(config.min_relevant_date_overlap_s).sum())
            unique = own.loc[own["location_id"].ge(0)]
            unique_day = unique.groupby("behavior_date")["overlap_s"].sum()
            match_days = int(
                unique_day.ge(config.min_relevant_date_overlap_s).sum()
            )
            anchor = own.loc[own["location_id"].eq(location)]
            anchor_days = int(
                anchor["overlap_s"].ge(config.min_relevant_date_overlap_s).sum()
            )
            other = own.loc[
                own["location_id"].ge(0)
                & ~own["location_id"].eq(location)
            ]
            other_day = other.groupby("behavior_date")["overlap_s"].sum()
            other_days = int(
                other_day.ge(config.min_relevant_date_overlap_s).sum()
            )
            if (
                opportunity != int(candidate.future_observed_window_dates)
                or anchor_days != int(candidate.future_same_anchor_window_dates)
                or anchor_days > match_days or match_days > opportunity
            ):
                raise ValueError("Stage10f future window/date parity mismatch")
            rows.append({
                "user_id": user,
                "label": label,
                "train_location_id": location,
                "observed_future_window_dates": opportunity,
                "unique_anchor_supported_dates": match_days,
                "same_anchor_supported_dates": anchor_days,
                "other_anchor_supported_dates": other_days,
                "future_spatially_unresolved": opportunity >= 1 and match_days == 0,
                "future_without_candidate_reappearance": (
                    opportunity >= 1 and anchor_days == 0
                ),
            })
    return pd.DataFrame(rows)


def summarize_spatial(rows):
    def counts(g):
        assess = g.loc[g["observed_future_window_dates"].ge(1)]
        missed = assess.loc[assess["future_without_candidate_reappearance"]]
        return {
            "train_emitted": int(len(g)),
            "future_time_observable": int(len(assess)),
            "future_unique_spatial_observable": int(
                assess["unique_anchor_supported_dates"].ge(1).sum()
            ),
            "future_spatially_unresolved": int(
                assess["future_spatially_unresolved"].sum()
            ),
            "future_same_anchor_reappears": int(
                assess["same_anchor_supported_dates"].ge(1).sum()
            ),
            "future_anchor_not_observed": int(len(missed)),
            "nonreappeared_without_unique_spatial_support": int(
                missed["future_spatially_unresolved"].sum()
            ),
            "nonreappeared_with_other_unique_anchor": int(
                missed["other_anchor_supported_dates"].ge(1).sum()
            ),
        }
    return {
        "experiment": "stage10i_future_spatial_observability",
        "ground_truth_semantic_accuracy": None,
        "validated_evidence_v2": False,
        "overall": counts(rows),
        "labels": [
            {"label": str(label), **counts(g)}
            for label, g in rows.groupby("label", sort=True)
        ],
        "notes": (
            "A FUTURE time window can be observed with GPS even if no later stay "
            "is assignable to any unique TRAIN anchor. Matching is the original "
            "strict complete-link-compatible 200m Stage10f policy. No future "
            "locations are refitted. Lack of same-anchor observations is not "
            "ground-truth HOME/OFFICE error."
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cache-root", type=Path,
                   default=Path("/mnt/geolife-data/cache/cp2_v2"))
    p.add_argument("--stays-cache", type=Path,
                   default=Path("/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl"))
    p.add_argument("--train-fraction", type=float, default=0.70)
    args = p.parse_args()
    folder = args.cache_root / "10_evidence_v2_offline"
    reference = folder / "train_only_forward_candidates_private.pkl"
    if not reference.is_file() or not args.stays_cache.is_file():
        p.error("Trusted Stage10f result or private CP1 cache missing")
    stays = pd.read_pickle(args.stays_cache)
    if len(stays) != 5821 or stays["user_id"].astype(str).nunique() != 136:
        raise ValueError("Frozen CP1 parity failed")
    original = pd.read_pickle(reference)
    stage = stage10f_module()
    config = HomeOfficeConfig()
    train, future, _ = stage.partition_stays(
        stays, train_fraction=args.train_fraction
    )
    emissions, members = stage.train_only_emissions(train, config=config)
    future_semantic = cp2._resolve_stay_timezones(cp2._validate_stays(future))
    aligned = stage.align_to_train_locations(
        future_semantic, members,
        max_diameter_m=config.location_max_diameter_m
    )
    current = stage.evaluate_future_windows(emissions, aligned, config=config)
    keys = ["user_id", "label", "train_location_id"]
    joined = current.merge(original, on=keys, how="outer",
                           suffixes=("_new", "_old"), indicator=True,
                           validate="one_to_one")
    if not joined["_merge"].eq("both").all():
        raise ValueError("Train candidate identity drift from Stage10f")
    for name in ("train_evidence_strength", "future_observed_window_dates",
                 "future_same_anchor_window_dates"):
        if not (joined[f"{name}_new"] - joined[f"{name}_old"]).abs().le(1e-10).all():
            raise ValueError("Stage10f score/opportunity parity drift")
    private = audit_future_windows(original, aligned, config)
    if len(private) != 44:
        raise ValueError("Unexpected Stage10f candidate count")
    report = summarize_spatial(private)
    private.to_pickle(folder / "future_spatial_observability_private.pkl")
    (folder / "future_spatial_observability_aggregate.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
