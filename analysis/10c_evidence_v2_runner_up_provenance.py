"""Stage 10c: runner-up *presence* provenance audit, not a score recalibration.

Stage 08b/CP2 use fillna(0) for a missing second eligible location. Stage 10a
conservatively treats top_share - share_margin == 0 as an unknown competitor.
To distinguish a *genuinely singleton eligible candidate set* from a data-join
error, reconstruct only the frozen CP2 semantic location features from a
TRUSTED CP1 stays cache (no raw GPS scans, no CP1 rerun, no EDA notebook rerun).
It retains the same label-specific candidate eligibility sets as Stage08b.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from geolife.model import HomeOfficeConfig, build_semantic_locations, infer_home_office
from geolife.model import home_office as cp2


BASE_COLUMNS = {
    "user_id", "label", "location_id", "tier", "exposure_regime",
    "top_share", "runner_up_share",
}

DEFAULT_STAYS = Path(
    "/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl"
)


def audit_runner_up(
    scored: pd.DataFrame,
    cp2_features: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
    atol: float = 1e-8,
) -> pd.DataFrame:
    """Return PRIVATE per-candidate audit (never print/commit this DataFrame)."""
    cfg = config or HomeOfficeConfig()
    missing = BASE_COLUMNS.difference(scored.columns)
    if missing:
        raise ValueError(f"Missing scored columns: {sorted(missing)}")
    required = {
        "user_id", "location_id", "stay_count",
        "home_dates", "home_dwell_s", "home_dwell_share",
        "office_dates", "office_dwell_s", "office_dwell_share",
    }
    if required - set(cp2_features.columns):
        raise ValueError(
            f"Missing CP2 features: {sorted(required - set(cp2_features.columns))}"
        )
    features = cp2_features.copy()
    features["user_id"] = features["user_id"].astype(str)
    frames = []
    for label in ("HOME", "OFFICE"):
        prefix = label.lower()
        for min_dates in (0, cfg.home_min_dates if label == "HOME"
                          else cfg.office_min_dates):
            if min_dates == 0:
                # Stage-08b raw ranking requires stay_count >=2 and dwell >0;
                # it does NOT require >=1 supported behavior dates.
                if label != "HOME":
                    continue
            subset = features.loc[
                (pd.to_numeric(features["stay_count"], errors="coerce") >= 2)
                & (pd.to_numeric(features[f"{prefix}_dates"], errors="coerce") >= min_dates)
                & (pd.to_numeric(features[f"{prefix}_dwell_s"], errors="coerce") > 0)
            ].copy()
            subset = subset.sort_values(
                [
                    "user_id", f"{prefix}_dwell_share", f"{prefix}_dates",
                    f"{prefix}_dwell_s", "stay_count", "location_id",
                ],
                ascending=[True, False, False, False, False, True],
                kind="stable",
            )
            subset["_rank"] = subset.groupby("user_id").cumcount() + 1
            subset["_peer_count"] = subset.groupby("user_id")["location_id"].transform("size")
            subset["_next_share"] = (
                subset.groupby("user_id")[f"{prefix}_dwell_share"].shift(-1)
            )
            subset["_next_loc"] = subset.groupby("user_id")["location_id"].shift(-1)
            subset["label"] = label
            subset["raw_ranking"] = min_dates == 0
            frames.append(subset.loc[
                subset["_rank"].eq(1),
                ["user_id", "label", "raw_ranking", "location_id",
                 f"{prefix}_dwell_share", "_peer_count", "_next_share", "_next_loc"],
            ].rename(columns={f"{prefix}_dwell_share": "_top_share"}))
    # The HOME and OFFICE shapes have matching columns after renaming.
    ranking = pd.concat(frames, ignore_index=True)
    if ranking.duplicated(["user_id", "label", "raw_ranking"]).any():
        raise ValueError("Duplicate top candidate for label / ranking regime")

    candidates = scored.copy()
    candidates["user_id"] = candidates["user_id"].astype(str)
    candidates["raw_ranking"] = candidates["tier"].eq("HOME_SPARSE_CANDIDATE")
    joined = candidates.merge(
        ranking,
        how="left",
        on=["user_id", "label", "raw_ranking"],
        suffixes=("", "_rank"),
        validate="one_to_one",
        indicator=True,
    )
    if not joined["_merge"].eq("both").all():
        raise ValueError("Candidate absent from reconstructed eligible ranking")
    left_loc = pd.to_numeric(joined["location_id"], errors="raise")
    right_loc = pd.to_numeric(joined["location_id_rank"], errors="raise")
    if not (left_loc == right_loc).all():
        raise ValueError("CP2-v2 location identity diverges from Stage10a")
    observed_top = pd.to_numeric(joined["top_share"], errors="raise").to_numpy(float)
    ranked_top = pd.to_numeric(joined["_top_share"], errors="raise").to_numpy(float)
    if not np.allclose(observed_top, ranked_top, atol=atol, rtol=0):
        raise ValueError("CP2-v2 top share diverges from Stage10a; aborting audit")

    peer_count = pd.to_numeric(joined["_peer_count"], errors="raise").to_numpy(int)
    expected_peer = pd.to_numeric(joined["_next_share"], errors="coerce").to_numpy(float)
    stage10_peer = pd.to_numeric(joined["runner_up_share"], errors="coerce").to_numpy(float)
    solitary = peer_count == 1
    multiple = peer_count >= 2
    if not np.all(solitary | multiple):
        raise ValueError("Invalid eligible competitor count")
    if not np.all(np.isnan(expected_peer[solitary])):
        raise ValueError("Singleton ranking unexpectedly had a runner-up")
    if not np.all(np.isfinite(expected_peer[multiple]) & (expected_peer[multiple] > 0)):
        raise ValueError("Multiple eligible locations must have a positive runner-up share")

    if not np.all(np.isnan(stage10_peer[solitary])):
        raise ValueError("Stage10a falsely has a known runner-up for a singleton")
    if not np.all(np.isfinite(stage10_peer[multiple])):
        raise ValueError("Stage10a lost an existing eligible runner-up")
    if not np.allclose(
        stage10_peer[multiple], expected_peer[multiple], atol=atol, rtol=0
    ):
        raise ValueError("Stage10a runner-up value differs from reconstructed ranking")

    joined["eligible_competitor_status"] = np.where(
        solitary, "sole_eligible_location", "has_eligible_runner_up"
    )
    joined["eligible_location_count"] = peer_count
    joined["reconstructed_runner_up_share"] = expected_peer
    return joined[[
        "user_id", "label", "tier", "exposure_regime", "location_id",
        "raw_ranking", "eligible_competitor_status", "eligible_location_count",
        "reconstructed_runner_up_share",
    ]]


def aggregate_report(audited: pd.DataFrame) -> dict:
    if audited.empty:
        raise ValueError("No candidate rows audited")
    groups = []
    for (label, tier, regime), g in audited.groupby(
        ["label", "tier", "exposure_regime"], sort=True
    ):
        groups.append({
            "label": str(label),
            "tier": str(tier),
            "exposure_regime": str(regime),
            "candidate_rows": int(len(g)),
            "sole_eligible_location": int(
                g["eligible_competitor_status"].eq("sole_eligible_location").sum()
            ),
            "has_eligible_runner_up": int(
                g["eligible_competitor_status"].eq("has_eligible_runner_up").sum()
            ),
        })
    return {
        "experiment": "evidence_v2_runner_up_provenance",
        "candidate_rows": int(len(audited)),
        "sole_eligible_location": int(
            audited["eligible_competitor_status"].eq("sole_eligible_location").sum()
        ),
        "has_eligible_runner_up": int(
            audited["eligible_competitor_status"].eq("has_eligible_runner_up").sum()
        ),
        "candidate_namespace_parity": True,
        "groups": groups,
        "notes": (
            "Singleton means no second location met the label/ranker-specific "
            "eligibility gate in observed stays, NOT no other possible place "
            "or a true zero probability of a competing HOME/OFFICE. This audit "
            "does not create or calibrate a new evidence score."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache-root", type=Path, default=Path("/mnt/geolife-data/cache/cp2_v2"))
    parser.add_argument("--stays-cache", type=Path, default=DEFAULT_STAYS)
    args = parser.parse_args()
    scored_path = args.cache_root / "10_evidence_v2_offline" / "candidate_scored_private.pkl"
    if not scored_path.is_file() or not args.stays_cache.is_file():
        parser.error(
            "Missing PRIVATE Stage10a scored artifact or trusted frozen stays cache"
        )
    # ONLY trust the already-audited private Modal Volume pickle inputs.
    scored = pd.read_pickle(scored_path)
    stays = pd.read_pickle(args.stays_cache)
    if len(stays) != 5821 or stays["user_id"].astype(str).nunique() != 136:
        raise ValueError("Frozen CP1 cache has drifted; aborting")
    cfg = HomeOfficeConfig()
    semantic, locations = build_semantic_locations(stays, config=cfg)
    if len(semantic) != 5821 or len(locations) != 2015:
        raise ValueError("Frozen CP2 location representation drifted; aborting")
    # This recomputes frozen inference for parity audit only; does NOT alter serving.
    production = infer_home_office(stays, config=cfg)
    counts = production["label"].value_counts().to_dict()
    if counts.get("HOME", 0) != 27 or counts.get("OFFICE", 0) != 16:
        raise ValueError("Frozen HOME/OFFICE production parity drifted; aborting")
    features = cp2._location_features(semantic, locations, config=cfg)
    audit = audit_runner_up(scored, features, config=cfg)
    if len(audit) != 55:
        raise ValueError("Stage10a 55-candidate tier parity drifted; aborting")
    summary = aggregate_report(audit)
    output = args.cache_root / "10_evidence_v2_offline"
    output.mkdir(parents=True, exist_ok=True)
    audit.to_pickle(output / "runner_up_provenance_private.pkl")
    (output / "runner_up_provenance_aggregate.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
