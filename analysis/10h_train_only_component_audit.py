"""Stage 10h: frozen CP2 v1 component audit from TRAIN-only stays.

Reconstruct earlier-only CP2 locations, ranks and label-window opportunity;
join to existing Stage10f private FUTURE outcomes by the *TRAIN* location IDs.
No all-history 55-tier features, Stage05 dropout R or future data enter TRAIN
feature computation. Report only aggregate medians; no score optimization,
HOME/OFFICE semantic truth, calibrated probability, or production changes.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from geolife.model import HomeOfficeConfig
from geolife.model import home_office as cp2


def _load_sibling(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(file))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load Stage10 dependency {file}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _window_opportunities(semantic: pd.DataFrame, *, label: str,
                          config: HomeOfficeConfig) -> dict[str, int]:
    overlap = cp2._window_contributions(
        semantic, config=config, kind=label.lower()
    )
    if overlap.empty:
        return {}
    daily = overlap.groupby(
        ["user_id", "behavior_date"], as_index=False
    )["overlap_s"].sum()
    daily = daily.loc[daily["overlap_s"].ge(config.min_relevant_date_overlap_s)]
    return {str(user): int(n) for user, n in daily.groupby("user_id").size().items()}


def build_train_only_features(
    stays: pd.DataFrame,
    prior_outcomes: pd.DataFrame,
    *,
    train_fraction: float = 0.70,
    config: HomeOfficeConfig | None = None,
) -> pd.DataFrame:
    """Private TRAIN-only evidence factors paired to Stage10f future outcomes."""
    cfg = config or HomeOfficeConfig()
    if cfg.clustering_method != "complete_link":
        raise ValueError("Only frozen complete-link CP2 baseline supported")

    ten_f = _load_sibling("research_stage10f", "10f_train_only_forward_validation.py")
    ten_g = _load_sibling("research_stage10g", "10g_train_score_recurrence_audit.py")
    outcomes = ten_g.validate_private_train_results(prior_outcomes)
    train, _, _ = ten_f.partition_stays(stays, train_fraction=train_fraction)
    semantic, locations = cp2.build_semantic_locations(train, config=cfg)
    if len(semantic) != len(train):
        raise ValueError("TRAIN timezone resolution parity failed")
    if semantic.empty:
        raise ValueError("No usable TRAIN semantic stays")
    features = cp2._location_features(semantic, locations, config=cfg)

    rows = []
    for label, min_dates, min_share, min_margin in (
        ("HOME", cfg.home_min_dates, cfg.home_min_share, cfg.home_min_margin),
        ("OFFICE", cfg.office_min_dates, cfg.office_min_share, cfg.office_min_margin),
    ):
        kind = label.lower()
        rankable = features.loc[
            features["stay_count"].ge(2)
            & features[f"{kind}_dates"].ge(min_dates)
            & features[f"{kind}_dwell_s"].gt(0)
        ]
        n_eligible = rankable.groupby("user_id").size().to_dict()
        top = cp2._top_candidate(features, label=label, min_dates=min_dates)
        emitted = cp2._emit_label(
            top, label=label, min_share=min_share, min_margin=min_margin,
            support_saturation_dates=cfg.support_saturation_dates,
        )
        opportunity = _window_opportunities(semantic, label=label, config=cfg)
        for cand in emitted.itertuples(index=False):
            user = str(cand.user_id)
            share, margin = float(cand.relevant_dwell_share), float(cand.share_margin)
            support = int(cand.relevant_dates)
            opp = int(opportunity.get(user, 0))
            peers = int(n_eligible.get(user, 0))
            if opp < support or peers < 1:
                raise ValueError("TRAIN support/opportunity or ranker lineage invalid")
            second = share - margin
            if peers == 1:
                if not np.isclose(second, 0, atol=1e-9):
                    raise ValueError("TRAIN singleton top2 margin parity failed")
                dominance = np.nan
            else:
                if not 0 < second <= share:
                    raise ValueError("TRAIN observed runner-up must be positive")
                dominance = share / (share + second)
            rows.append({
                "user_id": user,
                "label": label,
                "train_location_id": int(cand.location_id),
                "train_evidence_strength_reconstructed": float(cand.evidence_strength),
                "train_support_days_reconstructed": support,
                "train_eligible_location_count_reconstructed": peers,
                "train_dwell_share": share,
                "train_share_margin": margin,
                "train_support_factor": min(support / cfg.support_saturation_dates, 1.0),
                "train_observed_opportunity_dates": opp,
                "train_observed_date_coverage": support / opp,
                "train_relative_peer_dominance": dominance,
            })
    reconstructed = pd.DataFrame(rows)
    if reconstructed.empty or reconstructed.duplicated(
        ["user_id", "label", "train_location_id"]
    ).any():
        raise ValueError("No unique TRAIN emitted candidates reconstructed")
    merged = outcomes.merge(
        reconstructed,
        on=["user_id", "label", "train_location_id"],
        how="outer", indicator=True, validate="one_to_one",
    )
    if not merged["_merge"].eq("both").all():
        raise ValueError("Stage10f outcome/Stage10h TRAIN candidate identity mismatch")
    merged = merged.drop(columns="_merge")
    if not np.allclose(
        merged["train_evidence_strength"].to_numpy(float),
        merged["train_evidence_strength_reconstructed"].to_numpy(float),
        atol=1e-10, rtol=0,
    ):
        raise ValueError("Frozen TRAIN v1 evidence score parity failed")
    if not (
        merged["train_support_dates"].eq(merged["train_support_days_reconstructed"]).all()
        and merged["train_eligible_location_count"].eq(
            merged["train_eligible_location_count_reconstructed"]
        ).all()
    ):
        raise ValueError("TRAIN support or eligible peer-count parity failed")
    check = (
        merged["train_dwell_share"]
        + merged["train_share_margin"]
        + merged["train_support_factor"]
    ) / 3.0
    if not np.allclose(check, merged["train_evidence_strength"], atol=1e-10, rtol=0):
        raise ValueError("v1 three-component arithmetic parity failed")
    merged["train_peer_group"] = np.where(
        merged["train_eligible_location_count"].eq(1),
        "singleton_eligible", "multiple_eligible",
    )
    return merged


COMPONENTS = (
    "train_evidence_strength", "train_dwell_share", "train_share_margin",
    "train_support_factor", "train_observed_date_coverage",
    "train_relative_peer_dominance",
)


def aggregate_components(rows: pd.DataFrame, *, min_group: int = 5) -> dict:
    if min_group < 5:
        raise ValueError("min_group must be >=5 for privacy suppression")
    if rows.empty:
        raise ValueError("No reconstructed TRAIN candidate evidence")

    def med(subset: pd.DataFrame, name: str):
        valid = pd.to_numeric(subset[name], errors="coerce").dropna()
        return (
            round(float(valid.median()), 6)
            if len(subset) >= min_group and len(valid) >= min_group
            else None
        )

    def summary(subset: pd.DataFrame) -> dict:
        observable = subset.loc[subset["future_window_assessable"]]
        observed = observable.loc[observable["future_same_anchor_reappears"]]
        not_observed = observable.loc[~observable["future_same_anchor_reappears"]]
        return {
            "train_candidates": int(len(subset)),
            "future_assessable": int(len(observable)),
            "future_reappears": int(len(observed)),
            "future_not_reappears": int(len(not_observed)),
            "train_peer_dominance_available": int(
                subset["train_relative_peer_dominance"].notna().sum()
            ),
            "median_components_assessable": {
                name: med(observable, name) for name in COMPONENTS
            },
            "median_components_reappears": {
                name: med(observed, name) for name in COMPONENTS
            },
            "median_components_not_reappears": {
                name: med(not_observed, name) for name in COMPONENTS
            },
        }

    return {
        "experiment": "stage10h_train_only_v1_component_decomposition",
        "ground_truth_semantic_accuracy": None,
        "calibrated_probability": None,
        "v2_model_replacement": False,
        "train_only_component_parity": True,
        "overall": summary(rows),
        "labels": [
            {"label": str(label), **summary(g)}
            for label, g in rows.groupby("label", sort=True)
        ],
        "peer_groups": [
            {"label": str(label), "train_peer_group": str(peer), **summary(g)}
            for (label, peer), g in rows.groupby(
                ["label", "train_peer_group"], sort=True
            )
        ],
        "notes": (
            "All evidence dimensions are recomputed using TRAIN stays only "
            "and numerically checked against the existing Stage10f TRAIN v1 "
            "score. Medians describe selected future-observable subsets, NOT "
            "semantic accuracy, probability or causal impact. Peer dominance "
            "is unavailable for singleton eligible ranks; no C=1 imputation. "
            "Future spatial matching and observation opportunity remain "
            "confounders. This is single-split exploratory component audit."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-root", type=Path,
        default=Path("/mnt/geolife-data/cache/cp2_v2"),
    )
    parser.add_argument(
        "--stays-cache", type=Path,
        default=Path("/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl"),
    )
    parser.add_argument("--train-fraction", type=float, default=0.70)
    parser.add_argument("--min-group", type=int, default=5)
    args = parser.parse_args()
    root = args.cache_root / "10_evidence_v2_offline"
    outcomes_path = root / "train_only_forward_candidates_private.pkl"
    if not outcomes_path.is_file() or not args.stays_cache.is_file():
        parser.error("Missing trusted Modal Stage10f outcomes or CP1 stays cache")
    # Pickle inputs ONLY from the trusted private Modal Volume.
    stays = pd.read_pickle(args.stays_cache)
    if len(stays) != 5821 or stays["user_id"].astype(str).nunique() != 136:
        raise ValueError("Frozen CP1 stays parity failed")
    result = build_train_only_features(
        stays, pd.read_pickle(outcomes_path), train_fraction=args.train_fraction
    )
    if len(result) != 44:
        raise ValueError("Expected 44 TRAIN-only Stage10f candidates")
    aggregate = aggregate_components(result, min_group=args.min_group)
    result.to_pickle(root / "train_only_components_private.pkl")
    (root / "train_only_components_aggregate.json").write_text(
        json.dumps(aggregate, indent=2), encoding="utf-8"
    )
    print(json.dumps(aggregate, indent=2))


if __name__ == "__main__":
    main()
