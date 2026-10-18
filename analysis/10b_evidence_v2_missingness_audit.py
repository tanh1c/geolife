"""Stage 10b: multi-cause feature availability audit (research-only).

Reads the pre-existing private Stage 10a candidate-scored pickle on the trusted
Modal Volume. Does not evaluate semantic correctness, score replacement,
candidate promotions or GPS. Never prints candidate IDs or coordinates.

Stage 10a's single v2_status code has priority ordering, which can hide more
than one reason for unscorable candidates. This audit counts *independent*
reasons and their co-occurrence without conflating them with wrong labels.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED = (
    "label", "tier", "exposure_regime", "top_share", "runner_up_share",
    "candidate_support_days", "opportunity_days", "identity_stability",
    "evidence_v2",
)


def blocker_flags(scored: pd.DataFrame) -> pd.DataFrame:
    missing = sorted(set(REQUIRED) - set(scored.columns))
    if missing:
        raise ValueError(f"Missing expected Stage10a columns: {missing}")
    frame = scored.copy()

    top = pd.to_numeric(frame["top_share"], errors="coerce").to_numpy(dtype=float)
    second = pd.to_numeric(
        frame["runner_up_share"], errors="coerce"
    ).to_numpy(dtype=float)
    support = pd.to_numeric(
        frame["candidate_support_days"], errors="coerce"
    ).to_numpy(dtype=float)
    opportunity = pd.to_numeric(
        frame["opportunity_days"], errors="coerce"
    ).to_numpy(dtype=float)
    stability = pd.to_numeric(
        frame["identity_stability"], errors="coerce"
    ).to_numpy(dtype=float)

    valid_top = np.isfinite(top) & (top > 0) & (top <= 1)
    known_runner_up = np.isfinite(second)
    valid_second = known_runner_up & (second >= 0) & (second <= top)
    valid_opportunity = (
        np.isfinite(support) & np.isfinite(opportunity)
        & (support >= 1) & (opportunity >= 1) & (support <= opportunity)
        & (support == np.floor(support))
        & (opportunity == np.floor(opportunity))
    )
    valid_stability = (
        np.isfinite(stability) & (stability >= 0) & (stability <= 1)
    )
    flags = pd.DataFrame(
        {
            "missing_runner_up": ~known_runner_up,
            "invalid_top_or_runner_up": ~(valid_top & valid_second)
            & known_runner_up,
            "invalid_observed_opportunity": ~valid_opportunity,
            "missing_or_invalid_identity_stability": ~valid_stability,
        },
        index=frame.index,
    )
    flags["blocker_count"] = flags.sum(axis=1).astype(int)
    flags["expected_scorable"] = flags["blocker_count"].eq(0)
    actual_scorable = pd.to_numeric(
        frame["evidence_v2"], errors="coerce"
    ).notna().to_numpy()
    if not np.array_equal(flags["expected_scorable"].to_numpy(), actual_scorable):
        raise ValueError(
            "Mismatch between input blockers and Stage10a scoring; "
            "verify formula/feature lineage before interpretation"
        )
    return flags


def multi_cause_report(scored: pd.DataFrame, *, min_group: int = 5) -> dict:
    if min_group < 2:
        raise ValueError("min_group must be >= 2")
    flags = blocker_flags(scored)

    def summarize(subset: pd.DataFrame) -> dict:
        return {
            "candidate_rows": int(len(subset)),
            "scorable_rows": int(subset["expected_scorable"].sum()),
            "missing_runner_up": int(subset["missing_runner_up"].sum()),
            "invalid_top_or_runner_up": int(subset["invalid_top_or_runner_up"].sum()),
            "invalid_observed_opportunity": int(
                subset["invalid_observed_opportunity"].sum()
            ),
            "missing_or_invalid_identity_stability": int(
                subset["missing_or_invalid_identity_stability"].sum()
            ),
            "multiple_blockers": int(subset["blocker_count"].ge(2).sum()),
        }

    total = summarize(flags)
    breakdown = []
    for (label, tier, regime), subset in scored.groupby(
        ["label", "tier", "exposure_regime"], sort=True, dropna=False
    ):
        stats = summarize(flags.loc[subset.index])
        breakdown.append(
            {
                "label": str(label),
                "tier": str(tier),
                "exposure_regime": str(regime),
                **stats,
                # No per-user rows or small-cohort score medians leave Modal.
                "score_median_suppressed": len(subset) < min_group
                or stats["scorable_rows"] < min_group,
            }
        )
    return {
        "experiment": "evidence_v2_multicause_feature_availability",
        "calibrated_probability": None,
        "counts_may_overlap": True,
        "overall": total,
        "groups": breakdown,
        "notes": (
            "Feature blockers can co-occur on one candidate. Missing data are "
            "not HOME/OFFICE incorrectness. Prior to rewriting any score, "
            "inspect top-2 identity/provenance and keep no-peer uncertainty "
            "separate from observed zero competition. No semantic accuracy "
            "or independent temporal holdout is evaluated here."
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
    path = args.cache_root / "10_evidence_v2_offline" / "candidate_scored_private.pkl"
    if not path.is_file():
        parser.error("Stage10a private candidate scored cache missing; run 10a first")
    # ONLY a trusted Stage10a-owned local Modal pickle, never an untrusted upload.
    scored = pd.read_pickle(path)
    result = multi_cause_report(scored, min_group=args.min_group)
    outfile = path.parent / "feature_availability_aggregate.json"
    outfile.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
