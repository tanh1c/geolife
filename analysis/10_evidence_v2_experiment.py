"""Offline research-only evidence v2 candidate scorer.

Accepts an already-audited PRIVATE candidate feature table (same CP2-v2 location
namespace). No raw GeoLife GPS, coordinates, passwords or identifiers are emitted.
Does not modify CP1/CP2 inference, emission gates, or any FastAPI endpoint.

The proposed formula is an *unvalidated heuristic*, NOT semantic correctness
probability: E2 = cbrt(C * O * R) * sqrt(H). An unavailable robustness R is
reported as missing, not filled with 1. Independent time-held-out evaluation is
required before choosing a score or using it in serving.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED = frozenset(
    {
        "user_id",
        "label",
        "location_id",
        "tier",
        "exposure_regime",
        "top_share",
        "runner_up_share",
        "candidate_support_days",
        "opportunity_days",
        "identity_stability",
    }
)

NUMERIC = (
    "top_share",
    "runner_up_share",
    "candidate_support_days",
    "opportunity_days",
    "identity_stability",
)


def score_evidence_v2(candidates: pd.DataFrame) -> pd.DataFrame:
    """Score preselected candidate *hypotheses*, including previously abstained ones.

    Candidate selection and tier assignment MUST occur separately under recorded
    Stage 08a/08c rules. Stable identity and opportunity coverage must come from
    auditable upstream analyses, not be inferred from the desired label.
    """
    missing = REQUIRED.difference(candidates.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    out = candidates.copy()
    if out.empty:
        return out.assign(
            relative_dominance=pd.Series(dtype=float),
            opportunity_coverage=pd.Series(dtype=float),
            support_factor=pd.Series(dtype=float),
            evidence_v2=pd.Series(dtype=float),
            v2_status=pd.Series(dtype=str),
        )
    if out[["user_id", "label", "location_id"]].isna().any().any():
        raise ValueError("Candidate identity may not be null")
    if not out["label"].isin(("HOME", "OFFICE")).all():
        raise ValueError("Only HOME/OFFICE hypotheses can use semantic evidence v2")
    if out.duplicated(["user_id", "label", "location_id"]).any():
        raise ValueError("Duplicate candidate identity within a label is not allowed")

    for column in NUMERIC:
        out[column] = pd.to_numeric(out[column], errors="coerce").astype(float)

    top = out["top_share"].to_numpy()
    peer = out["runner_up_share"].to_numpy()
    n_days = out["candidate_support_days"].to_numpy()
    opportunities = out["opportunity_days"].to_numpy()
    reliability = out["identity_stability"].to_numpy()

    # A missing runner-up is *unknown*, not evidence of complete top-1 dominance.
    valid_dominance = (
        np.isfinite(top) & np.isfinite(peer) & (top > 0) & (top <= 1)
        & (peer >= 0) & (peer <= top)
    )
    c = np.full(len(out), np.nan)
    c[valid_dominance] = top[valid_dominance] / (
        top[valid_dominance] + peer[valid_dominance]
    )

    # Observed opportunity dates count actual HOME/WORK-window observation.
    # Missing/zero denominators are not treated as a perfect 100% opportunity ratio.
    valid_opportunity = (
        np.isfinite(n_days) & np.isfinite(opportunities)
        & (opportunities >= 1) & (n_days >= 1) & (n_days <= opportunities)
        & (n_days == np.floor(n_days))
        & (opportunities == np.floor(opportunities))
    )
    o = np.full(len(out), np.nan)
    h = np.full(len(out), np.nan)
    o[valid_opportunity] = n_days[valid_opportunity] / opportunities[valid_opportunity]
    h[valid_opportunity] = np.minimum(n_days[valid_opportunity] / 5, 1.0)

    valid_reliability = np.isfinite(reliability) & (reliability >= 0) & (reliability <= 1)
    usable = valid_dominance & valid_opportunity & valid_reliability

    # No silent imputation of missing robustness and no score for unvalidated inputs.
    score = np.full(len(out), np.nan)
    score[usable] = np.cbrt(c[usable] * o[usable] * reliability[usable]) * np.sqrt(
        h[usable]
    )

    status = np.full(len(out), "ok", dtype=object)
    status[~valid_reliability] = "missing_or_invalid_stability"
    status[~valid_opportunity] = "missing_or_invalid_opportunity"
    status[~valid_dominance] = "missing_or_invalid_runner_up"
    out["relative_dominance"] = c
    out["opportunity_coverage"] = o
    out["support_factor"] = h
    out["evidence_v2"] = score
    out["v2_status"] = status
    return out


def aggregate_report(scored: pd.DataFrame, *, min_group: int = 5) -> dict:
    """Report only non-identifying, aggregate statistics; small scores suppressed."""
    if min_group < 2:
        raise ValueError("min_group must be at least 2")
    if not {"label", "tier", "exposure_regime", "v2_status", "evidence_v2"}.issubset(
        scored.columns
    ):
        raise ValueError("Call score_evidence_v2 first")

    groups: list[dict] = []
    for (label, tier, regime), group in scored.groupby(
        ["label", "tier", "exposure_regime"], dropna=False, sort=True
    ):
        valid = group["evidence_v2"].dropna()
        # Only disaggregated score statistics are suppressed. Aggregate counts
        # alone are not private-user coordinates or unverified performance metrics.
        groups.append(
            {
                "label": str(label),
                "tier": str(tier),
                "exposure_regime": str(regime),
                "candidate_rows": int(len(group)),
                "scorable_rows": int(len(valid)),
                "v2_status_counts": {
                    str(k): int(v) for k, v in group["v2_status"].value_counts().items()
                },
                "median_evidence_v2": (
                    round(float(valid.median()), 6)
                    if len(group) >= min_group and len(valid) >= min_group
                    else None
                ),
            }
        )
    return {
        "experiment": "evidence_v2_hypothesis_only",
        "calibrated_probability": None,
        "scoring_formula": "cbrt(C*O*R)*sqrt(H)",
        "candidate_rows": int(len(scored)),
        "scorable_rows": int(scored["evidence_v2"].notna().sum()),
        "groups": groups,
        "notes": (
            "Not ground-truth HOME/OFFICE accuracy. Requires independent temporal "
            "holdout; R must not use the same holdout on which the score is assessed. "
            "Groups with fewer than min_group rows have no score statistics."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-csv", type=Path, required=True,
        help="Trusted PRIVATE candidate feature CSV; never commit it.",
    )
    parser.add_argument(
        "--min-group", type=int, default=5,
        help="Suppress score statistics for groups smaller than this (min 2).",
    )
    args = parser.parse_args()
    if not args.input_csv.is_file():
        parser.error("Input CSV not found")
    scored = score_evidence_v2(pd.read_csv(args.input_csv, dtype={"user_id": str}))
    print(json.dumps(aggregate_report(scored, min_group=args.min_group), indent=2))


if __name__ == "__main__":
    main()
