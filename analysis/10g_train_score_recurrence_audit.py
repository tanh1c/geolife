"""Stage 10g — TRAIN-only frozen v1 evidence vs later observed reappearance.

Reads ONLY the already-generated, trusted Stage 10f private candidate results.
No GPS, source coordinates or full-period candidate/tier/robustness feature
is loaded. Distinguishes future relevance-window observability from a
candidate's observed same-location recurrence. No semantic truth, predictive
calibration, learned thresholds, tuning or v2 score replacement.

A stricter secondary diagnostic requires >=2 FUTURE relevant observation
dates and >=2 matched same-location relevant dates. This is NOT a model
promotion threshold and does not relabel any prior case.

Individual rows remain on the trusted Modal Volume. Printed JSON is
aggregate-only, suppressing per-group score summaries and rates for n<5.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED = {
    "user_id", "label", "train_location_id",
    "train_evidence_strength", "train_support_dates",
    "train_eligible_location_count", "future_observed_window_dates",
    "future_same_anchor_window_dates", "future_window_assessable",
    "future_same_anchor_reappears",
}
LABELS = {"HOME", "OFFICE"}


def validate_private_train_results(data: pd.DataFrame) -> pd.DataFrame:
    missing = REQUIRED - set(data.columns)
    if missing:
        raise ValueError(f"Stage10f required columns missing: {sorted(missing)}")
    if data.empty:
        raise ValueError("No Stage10f TRAIN emitted candidates")
    frame = data.copy()
    if frame[["user_id", "label", "train_location_id"]].isna().any().any():
        raise ValueError("Null train-only candidate identities")
    if not frame["label"].isin(LABELS).all():
        raise ValueError("Unexpected semantic candidate label")
    if frame.duplicated(["user_id", "label", "train_location_id"]).any():
        raise ValueError("Duplicate TRAIN candidate/label/location")
    for column in (
        "train_evidence_strength", "train_support_dates",
        "train_eligible_location_count", "future_observed_window_dates",
        "future_same_anchor_window_dates",
    ):
        frame[column] = pd.to_numeric(frame[column], errors="coerce")
        if frame[column].isna().any():
            raise ValueError(f"Invalid numerical feature: {column}")
    if not frame["train_evidence_strength"].between(0, 1).all():
        raise ValueError("TRAIN v1 score outside [0, 1]")
    for name, lower in [
        ("train_support_dates", 3),
        ("train_eligible_location_count", 1),
        ("future_observed_window_dates", 0),
        ("future_same_anchor_window_dates", 0),
    ]:
        values = frame[name].to_numpy(float)
        if not (np.isfinite(values).all() and (values >= lower).all()
                and np.equal(values, np.floor(values)).all()):
            raise ValueError(f"Invalid support count: {name}")
    if (
        frame["future_same_anchor_window_dates"] >
        frame["future_observed_window_dates"]
    ).any():
        raise ValueError("Future exact-anchor dates exceed observed opportunity")
    if (not frame["future_window_assessable"].isin((True, False)).all()
        or not frame["future_same_anchor_reappears"].isin((True, False)).all()):
        raise ValueError("Future observation/retention flags must be boolean")
    expected_assessable = frame["future_observed_window_dates"].ge(1)
    expected_retained = (
        expected_assessable & frame["future_same_anchor_window_dates"].ge(1)
    )
    if (
        not (frame["future_window_assessable"] == expected_assessable).all()
        or not (frame["future_same_anchor_reappears"] == expected_retained).all()
    ):
        raise ValueError("Future flags disagree with Stage10f date counts")
    frame["train_competitor_group"] = np.where(
        frame["train_eligible_location_count"].eq(1),
        "singleton_eligible",
        "multiple_eligible",
    )
    frame["future_2date_assessable"] = frame["future_observed_window_dates"].ge(2)
    frame["future_2date_reappears"] = (
        frame["future_2date_assessable"]
        & frame["future_same_anchor_window_dates"].ge(2)
    )
    return frame


def aggregate_train_score(
    checked: pd.DataFrame,
    *,
    min_group: int = 5,
) -> dict:
    if min_group < 5:
        raise ValueError("min_group must be at least 5 for aggregate protection")

    def median_if_k(frame: pd.DataFrame, column: str):
        if len(frame) < min_group:
            return None
        return round(float(frame[column].median()), 6)

    def report_one(g: pd.DataFrame) -> dict:
        assessable = g.loc[g["future_window_assessable"]]
        retained = assessable.loc[assessable["future_same_anchor_reappears"]]
        absent = assessable.loc[~assessable["future_same_anchor_reappears"]]
        stable_two = g.loc[g["future_2date_assessable"]]
        retained_two = stable_two.loc[stable_two["future_2date_reappears"]]
        return {
            "train_emitted_candidates": int(len(g)),
            "future_assessable_1date": int(len(assessable)),
            "future_reappears_1date": int(len(retained)),
            "future_not_reappears_1date": int(len(absent)),
            "future_assessable_2dates": int(len(stable_two)),
            "future_reappears_2dates": int(len(retained_two)),
            "retention_share_1date": (
                round(len(retained) / len(assessable), 6)
                if len(assessable) >= min_group else None
            ),
            "retention_share_2dates": (
                round(len(retained_two) / len(stable_two), 6)
                if len(stable_two) >= min_group else None
            ),
            "median_train_v1_score_assessable": median_if_k(
                assessable, "train_evidence_strength"
            ),
            "median_train_v1_score_reappears": median_if_k(
                retained, "train_evidence_strength"
            ),
            "median_train_v1_score_not_reappears": median_if_k(
                absent, "train_evidence_strength"
            ),
            "median_train_support_days_assessable": median_if_k(
                assessable, "train_support_dates"
            ),
            "median_future_observed_dates_assessable": median_if_k(
                assessable, "future_observed_window_dates"
            ),
        }

    groups = []
    for (label, competitor), g in checked.groupby(
        ["label", "train_competitor_group"], sort=True
    ):
        groups.append({
            "label": str(label),
            "train_competitor_group": str(competitor),
            **report_one(g),
        })
    labels = [
        {"label": str(label), **report_one(g)}
        for label, g in checked.groupby("label", sort=True)
    ]
    return {
        "experiment": "stage10g_train_v1_score_vs_future_anchor_reappearance",
        "ground_truth_semantic_accuracy": None,
        "calibrated_probability": None,
        "experimental_evidence_v2_evaluated": False,
        "source_model_score": "frozen CP2 v1 computed from TRAIN stays only",
        "score_comparison_is_exploratory": True,
        "overall": report_one(checked),
        "labels": labels,
        "train_competitor_groups": groups,
        "notes": (
            "This is a conditional retrospective 70/30 single-split analysis "
            "of exact TRAIN anchor reappearance, not HOME/OFFICE correctness. "
            "A missing future match may reflect mobility change, sparse GPS, "
            "or restrictive/ambiguous spatial alignment. The 2-date diagnostic "
            "requires both >=2 future observed behavior dates and >=2 matching "
            "candidate dates, and is NOT interchangeable with 1-date retention. "
            "Medians compare potentially selected groups with no statistical "
            "significance or independent-user adjustment; no thresholds tuned "
            "on future outcomes. Full-history Stage10a v2/Stage05 R not used."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-root", type=Path,
        default=Path("/mnt/geolife-data/cache/cp2_v2"),
    )
    parser.add_argument("--min-group", type=int, default=5)
    args = parser.parse_args()
    folder = args.cache_root / "10_evidence_v2_offline"
    path = folder / "train_only_forward_candidates_private.pkl"
    if not path.is_file():
        parser.error("Missing trusted private Stage10f candidate result")
    # Pickle must originate exclusively from the trusted private Modal Volume.
    checked = validate_private_train_results(pd.read_pickle(path))
    report = aggregate_train_score(checked, min_group=args.min_group)
    (folder / "train_only_score_recurrence_aggregate.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
