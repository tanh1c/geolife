"""Stage 10e — PRELIMINARY forward-holdout feasibility (NOT predictive validation).

Uses existing trusted frozen CP1 stay cache and private candidate tiers.
No fresh trajectory extraction, CP2 clustering, GPS-coordinate export, labels
or confidence calibration. Groups each user's stays by UTC calendar dates,
takes a predeclared first 70% observed UTC dates as training, then a later
holdout. Stays straddling the cutoff are EXCLUDED (not leaked to either split).

This is a support/exposure feasibility check only. A future validation MUST
refit per-user CP2 location clusters on TRAIN only, create evidence from TRAIN
only (including R), spatially align FUTURE to TRAIN candidate identities
without reclustering together, and assess same-location future behavior.
The currently cached Stage10a/10d values use full-history information and
MUST NOT be treated as leakage-free predictors in a forward holdout.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

EXPECTED_TIERS = {
    "HOME_CORE": 27,
    "OFFICE_CORE": 16,
    "HOME_PROBABLE": 5,
    "HOME_SPARSE_CANDIDATE": 4,
    "OFFICE_ROBUST_CANDIDATE": 3,
}
CANDIDATE_COLUMNS = {"user_id", "label", "tier", "location_id"}
STAY_COLUMNS = {"user_id", "arrival_time_utc", "departure_time_utc"}


def split_feasibility(
    stays: pd.DataFrame,
    candidates: pd.DataFrame,
    *,
    train_fraction: float = 0.70,
    expected_stays: int | None = 5821,
    expected_users: int | None = 136,
    enforce_tier_parity: bool = True,
) -> pd.DataFrame:
    """Return PRIVATE candidate feasibility, never print individual records."""
    if not 0.5 <= train_fraction <= 0.9:
        raise ValueError("train_fraction must be in [0.5, 0.9]")
    if STAY_COLUMNS - set(stays.columns):
        raise ValueError("Missing CP1 UTC stay timestamp columns")
    if CANDIDATE_COLUMNS - set(candidates.columns):
        raise ValueError("Missing candidate tier/identity columns")
    if expected_stays is not None and len(stays) != expected_stays:
        raise ValueError("Frozen CP1 count mismatch")
    s = stays[list(STAY_COLUMNS)].copy()
    if s["user_id"].isna().any() or s[["arrival_time_utc", "departure_time_utc"]].isna().any().any():
        raise ValueError("CP1 stay timestamps/user IDs may not be null")
    s["user_id"] = s["user_id"].astype(str)
    if expected_users is not None and s["user_id"].nunique() != expected_users:
        raise ValueError("Frozen CP1 stay-user count mismatch")
    s["arrival_time_utc"] = pd.to_datetime(s["arrival_time_utc"], utc=True, errors="raise")
    s["departure_time_utc"] = pd.to_datetime(s["departure_time_utc"], utc=True, errors="raise")
    if not s["departure_time_utc"].gt(s["arrival_time_utc"]).all():
        raise ValueError("Invalid CP1 stay time interval")

    c = candidates[list(CANDIDATE_COLUMNS)].copy()
    if c.isna().any().any():
        raise ValueError("Candidate identities may not be null")
    c["user_id"] = c["user_id"].astype(str)
    if c.duplicated(["user_id", "label", "location_id"]).any():
        raise ValueError("Duplicate candidate identity")
    if enforce_tier_parity and c["tier"].value_counts().to_dict() != EXPECTED_TIERS:
        raise ValueError("Stage10 tier count parity mismatch")
    if not set(c["user_id"]).issubset(set(s["user_id"])):
        raise ValueError("Some candidates have no frozen CP1 stays")

    rows = []
    for user, g in s.groupby("user_id", sort=True):
        days = sorted(g["arrival_time_utc"].dt.floor("D").unique())
        n_dates = len(days)
        if n_dates < 2:
            rows.append({
                "user_id": user, "observed_dates": n_dates,
                "train_stays": 0, "test_stays": 0,
                "train_dates": 0, "test_dates": 0,
                "cross_cutoff_stays_excluded": 0,
                "cutoff_utc_private": pd.NaT,
            })
            continue
        split_at = min(max(1, math.ceil(n_dates * train_fraction)), n_dates - 1)
        cutoff = pd.Timestamp(days[split_at])
        train = g.loc[g["departure_time_utc"].le(cutoff)]
        test = g.loc[g["arrival_time_utc"].ge(cutoff)]
        if not train.empty and not test.empty:
            assert train["departure_time_utc"].max() <= test["arrival_time_utc"].min()
        rows.append({
            "user_id": user,
            "observed_dates": n_dates,
            "train_stays": len(train),
            "test_stays": len(test),
            "train_dates": int(train["arrival_time_utc"].dt.floor("D").nunique()),
            "test_dates": int(test["arrival_time_utc"].dt.floor("D").nunique()),
            "cross_cutoff_stays_excluded": int(len(g) - len(train) - len(test)),
            "cutoff_utc_private": cutoff,
        })
    user_splits = pd.DataFrame(rows)
    out = c.merge(user_splits, on="user_id", how="left", validate="many_to_one")
    if out["observed_dates"].isna().any():
        raise ValueError("Candidate with no split/UTC dates")
    out["proxy_train_support_3dates"] = (
        out["train_dates"].ge(3) & out["train_stays"].ge(2)
    )
    out["proxy_future_support_2dates"] = (
        out["test_dates"].ge(2) & out["test_stays"].ge(2)
    )
    out["proxy_both_train_future"] = (
        out["proxy_train_support_3dates"] & out["proxy_future_support_2dates"]
    )
    return out


def aggregate_feasibility(rows: pd.DataFrame) -> dict:
    if rows.empty:
        raise ValueError("No candidate feasibility")
    def aggregate(group: pd.DataFrame) -> dict:
        return {
            "candidate_rows": int(len(group)),
            "train_3_utc_dates_proxy": int(group["proxy_train_support_3dates"].sum()),
            "future_2_utc_dates_proxy": int(group["proxy_future_support_2dates"].sum()),
            "both_train_and_future_proxy": int(group["proxy_both_train_future"].sum()),
            "candidates_with_cutoff_crossing_stays": int(
                group["cross_cutoff_stays_excluded"].gt(0).sum()
            ),
        }

    groups = [
        {"label": str(label), "tier": str(tier), **aggregate(g)}
        for (label, tier), g in rows.groupby(["label", "tier"], sort=True)
    ]
    return {
        "experiment": "stage10e_forward_holdout_feasibility_only",
        "validated_predictive_performance": False,
        "ground_truth_semantic_accuracy": None,
        "split": "per-user first 70% observed UTC arrival dates vs last 30%; straddling stays excluded",
        "overall": aggregate(rows),
        "groups": groups,
        "notes": (
            "UTC date counts are ONLY an opportunity proxy, not HOME/WORK-local "
            "observation-window support or a demonstrated train-only CP2 label. "
            "Candidate tiers were selected from full history; do not use this "
            "preflight to assert future identity retention, model accuracy or "
            "independent holdout. Next fit train-only clusters and features, "
            "spatially align later stays to trained locations."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-root", type=Path, default=Path("/mnt/geolife-data/cache/cp2_v2")
    )
    parser.add_argument(
        "--stays-cache", type=Path,
        default=Path("/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl"),
    )
    parser.add_argument("--train-fraction", type=float, default=0.70)
    args = parser.parse_args()
    f = args.cache_root / "10_evidence_v2_offline"
    candidate_path = f / "factorized_dimensions_private.pkl"
    if not candidate_path.is_file() or not args.stays_cache.is_file():
        parser.error("Trusted private Stage10d or frozen CP1 input unavailable")
    # Pickle only from the existing audited private Modal Volume.
    result = split_feasibility(
        pd.read_pickle(args.stays_cache),
        pd.read_pickle(candidate_path),
        train_fraction=args.train_fraction,
    )
    report = aggregate_feasibility(result)
    result.to_pickle(f / "forward_holdout_feasibility_private.pkl")
    (f / "forward_holdout_feasibility_aggregate.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
