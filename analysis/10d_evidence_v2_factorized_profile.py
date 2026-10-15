"""Stage 10d: factorized evidence availability, NOT a scalar confidence.

Join the private Stage 10a scored feature cache to the private Stage 10c
eligible-runner-up provenance cache (trusted Modal Volume only). Report
opportunity/support, dropout candidate stability and competitor dominance as
SEPARATE evidence dimensions. No imputation, normalized tier score, precision,
calibration, semantic correctness or production changes.

Only aggregate statistics, with group score medians suppressed below a
minimum group/valid-count threshold, are printed. User IDs and location IDs
remain exclusively in the private Volume.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


JOIN_COLUMNS = ("user_id", "label", "tier", "exposure_regime", "location_id")
SCORED_REQUIRED = set(JOIN_COLUMNS) | {
    "top_share", "runner_up_share", "candidate_support_days",
    "opportunity_days", "identity_stability", "evidence_v2",
}
PROVENANCE_REQUIRED = set(JOIN_COLUMNS) | {"eligible_competitor_status"}
ALLOWED_PROVENANCE = {"sole_eligible_location", "has_eligible_runner_up"}


def build_factorized_profile(
    scored: pd.DataFrame,
    provenance: pd.DataFrame,
) -> pd.DataFrame:
    """Return PRIVATE one-row-per-candidate evidence dimensions."""
    if SCORED_REQUIRED - set(scored.columns):
        raise ValueError("Stage10a scored input has missing required columns")
    if PROVENANCE_REQUIRED - set(provenance.columns):
        raise ValueError("Stage10c runner-up provenance has missing required columns")
    if scored.empty or provenance.empty:
        raise ValueError("No candidates provided")
    left = scored.copy()
    right = provenance.copy()
    for frame in (left, right):
        frame["user_id"] = frame["user_id"].astype(str)
        if frame[list(JOIN_COLUMNS)].isna().any().any():
            raise ValueError("Null candidate identities")
        if frame.duplicated(list(JOIN_COLUMNS)).any():
            raise ValueError("Duplicate candidate identities")
    if not right["eligible_competitor_status"].isin(ALLOWED_PROVENANCE).all():
        raise ValueError("Unknown eligible competitor status")

    data = left.merge(
        right[list(JOIN_COLUMNS) + ["eligible_competitor_status"]],
        on=list(JOIN_COLUMNS),
        how="outer",
        validate="one_to_one",
        indicator=True,
    )
    if not data["_merge"].eq("both").all():
        raise ValueError("Stage10a vs Stage10c candidate lineage mismatch")
    data = data.drop(columns="_merge")

    def numerical(name: str) -> np.ndarray:
        return pd.to_numeric(data[name], errors="coerce").to_numpy(dtype=float)

    top = numerical("top_share")
    peer = numerical("runner_up_share")
    support = numerical("candidate_support_days")
    opportunity = numerical("opportunity_days")
    stability = numerical("identity_stability")
    original = numerical("evidence_v2")
    status = data["eligible_competitor_status"].to_numpy()
    singleton = status == "sole_eligible_location"
    with_peer = status == "has_eligible_runner_up"

    if (not np.all(singleton | with_peer)
        or np.any(np.isfinite(peer[singleton]))
        or not np.all(np.isfinite(peer[with_peer]))):
        raise ValueError("Stage10a runner-up contradicts Stage10c provenance")

    valid_temporal = (
        np.isfinite(support) & np.isfinite(opportunity)
        & (opportunity >= 1) & (support >= 1) & (support <= opportunity)
        & (support == np.floor(support))
        & (opportunity == np.floor(opportunity))
    )
    if not valid_temporal.all():
        raise ValueError("Stage10a opportunity exposure invalid")
    valid_robustness = np.isfinite(stability) & (stability >= 0) & (stability <= 1)
    valid_peer = (
        with_peer & np.isfinite(top) & (top > 0) & (top <= 1)
        & np.isfinite(peer) & (peer > 0) & (peer <= top)
    )
    if not (valid_peer[with_peer].all() and (~valid_peer[singleton]).all()):
        raise ValueError("Observed eligible second-rank feature invalid")
    if not np.array_equal(np.isfinite(original), valid_peer & valid_robustness):
        raise ValueError("Original v2-score availability disagrees with inputs")

    out = data[list(JOIN_COLUMNS) + ["eligible_competitor_status"]].copy()
    out["observed_date_coverage"] = support / opportunity
    out["support_factor"] = np.minimum(support / 5.0, 1.0)
    out["identity_stability"] = np.where(valid_robustness, stability, np.nan)
    out["relative_peer_dominance"] = np.where(
        valid_peer, top / np.where(valid_peer, top + peer, 1.0), np.nan
    )
    out["temporal_evidence_available"] = True
    out["identity_stability_available"] = valid_robustness
    out["peer_dominance_available"] = valid_peer
    out["original_evidence_v2_available"] = np.isfinite(original)
    return out


def aggregate_factorized(
    features: pd.DataFrame, *, min_group: int = 5,
) -> dict:
    if min_group < 2:
        raise ValueError("min_group must be >= 2")
    required = {
        "label", "tier", "exposure_regime",
        "observed_date_coverage", "support_factor",
        "identity_stability", "relative_peer_dominance",
        "temporal_evidence_available", "identity_stability_available",
        "peer_dominance_available", "original_evidence_v2_available",
        "eligible_competitor_status",
    }
    if required - set(features.columns):
        raise ValueError("Factorized dimensions missing")

    def med(g: pd.DataFrame, column: str):
        observed = pd.to_numeric(g[column], errors="coerce").dropna()
        if len(g) < min_group or len(observed) < min_group:
            return None
        return round(float(observed.median()), 6)

    def counts(g: pd.DataFrame):
        return {
            "candidate_rows": int(len(g)),
            "temporal_available": int(g["temporal_evidence_available"].sum()),
            "identity_stability_available": int(g["identity_stability_available"].sum()),
            "peer_dominance_available": int(g["peer_dominance_available"].sum()),
            "original_full_score_available": int(g["original_evidence_v2_available"].sum()),
            "sole_eligible_location": int(
                g["eligible_competitor_status"].eq("sole_eligible_location").sum()
            ),
        }

    groups = []
    for (label, tier, regime), group in features.groupby(
        ["label", "tier", "exposure_regime"], sort=True, dropna=False
    ):
        groups.append({
            "label": str(label),
            "tier": str(tier),
            "exposure_regime": str(regime),
            **counts(group),
            "median_observed_date_coverage": med(group, "observed_date_coverage"),
            "median_support_factor": med(group, "support_factor"),
            "median_identity_stability": med(group, "identity_stability"),
            "median_relative_peer_dominance": med(group, "relative_peer_dominance"),
        })
    return {
        "experiment": "evidence_v2_factorized_dimensions",
        "calibrated_probability": None,
        "single_evidence_v2_score_replacement": False,
        "overall": counts(features),
        "groups": groups,
        "notes": (
            "Temporal coverage/support, robustness and relative peer dominance "
            "are different evidence dimensions. The latter is inapplicable for "
            "sole eligible locations under the observed CP2 gate, not assumed "
            "1.0. No score is recalibrated; no correctness/held-out validation."
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
    scored_path = folder / "candidate_scored_private.pkl"
    provenance_path = folder / "runner_up_provenance_private.pkl"
    if not scored_path.is_file() or not provenance_path.is_file():
        parser.error("Missing trusted private Stage10a/Stage10c cache files")
    # Never load pickle from uploads or an untrusted location.
    frame = build_factorized_profile(
        pd.read_pickle(scored_path), pd.read_pickle(provenance_path)
    )
    if len(frame) != 55:
        raise ValueError("Stage10 55-candidate reference count drift")
    report = aggregate_factorized(frame, min_group=args.min_group)
    frame.to_pickle(folder / "factorized_dimensions_private.pkl")
    (folder / "factorized_dimensions_aggregate.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
