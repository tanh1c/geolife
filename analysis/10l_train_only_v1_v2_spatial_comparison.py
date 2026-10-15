"""Stage 10l — TRAIN-only Evidence v1/v2 paired FUTURE observability audit.

Uses frozen CP2 emitted anchors at retrospective 70/30 cutoff. TRAIN-only
v1 S/M/H/O/C components are recomputed and checked against Stage10f. R is a
new *TRAIN-only* nine-mask sensitivity proxy: 10/20/30% per-user observed UTC
arrival dates randomly masked at 3 deterministic seeds each; refit frozen CP2
on remaining TRAIN stays, count SAME label emitted with all-member <=200m
compatible TRAIN geometry. This R is NOT Stage05 full-history dropout R.

The existing experimental score formula cbrt(C*O*R)*sqrt(H) is invoked as-is.
Singleton rankers have undefined C, so NO v2 score, no imputation. A true
head-to-head is computed ONLY on identical scored candidates with >=1 FUTURE
unique-TRAIN spatially supported relevant date. Unresolved stays abstain.
No semantic HOME/OFFICE ground truth, calibration, population validity,
production tier change, nor statistical significance is claimed.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from geolife.model import HomeOfficeConfig
from geolife.model import home_office as cp2


JOIN = ["user_id", "label", "train_location_id"]
DROPOUT_RATES = (0.10, 0.20, 0.30)
DROPOUT_SEEDS = (0, 1, 2)
N_TRIALS = len(DROPOUT_RATES) * len(DROPOUT_SEEDS)
FRACTION = 0.70


def _load(alias: str, name: str):
    path = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(alias, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Stage10l missing sibling source: {name}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _unique(frame: pd.DataFrame, *, name: str) -> pd.DataFrame:
    missing = set(JOIN) - set(frame.columns)
    if missing:
        raise ValueError(f"{name}: missing identity {sorted(missing)}")
    out = frame.copy()
    out["user_id"] = out["user_id"].astype(str)
    if out[JOIN].isna().any().any() or out.duplicated(JOIN).any():
        raise ValueError(f"{name}: null/duplicate user-label-location key")
    return out


def _reference70(stage10j: dict) -> dict:
    if (
        stage10j.get("experiment") != "stage10j_forward_cutoff_sensitivity"
        or stage10j.get("fractions") != [.6, .7, .8]
    ):
        raise ValueError("Stage10j reference is invalid")
    matches = [
        row for row in stage10j.get("results", [])
        if row.get("train_fraction") == FRACTION
    ]
    if len(matches) != 1:
        raise ValueError("Stage10j 70% reference unavailable")
    return matches[0]


def _geom_members(semantic: pd.DataFrame, candidate) -> pd.DataFrame:
    return semantic.loc[
        semantic["user_id"].astype(str).eq(str(candidate.user_id))
        & semantic["location_id"].eq(int(candidate.location_id))
    ]


def _seed(user: str, rate: float, replicate: int) -> int:
    source = f"stage10l-train-only|{user}|{rate:.2f}|{replicate}"
    return int.from_bytes(hashlib.sha256(source.encode()).digest()[:8], "big")


def mask_train_dates(
    train_user: pd.DataFrame, *, rate: float, seed: int
) -> pd.DataFrame:
    """Remove complete observed UTC arrival dates, never consult FUTURE."""
    utc_dates = train_user["arrival_time_utc"].dt.floor("D")
    distinct = pd.DatetimeIndex(sorted(utc_dates.unique()))
    if not len(distinct):
        return train_user.iloc[0:0].copy()
    n_drop = max(1, math.ceil(rate * len(distinct)))
    if n_drop >= len(distinct):
        return train_user.iloc[0:0].copy()
    positions = np.random.default_rng(seed).choice(
        len(distinct), size=n_drop, replace=False
    )
    return train_user.loc[~utc_dates.isin(distinct[positions])].copy()


def train_only_mask_robustness(
    train: pd.DataFrame,
    emitted: pd.DataFrame,
    semantic: pd.DataFrame,
    *,
    stage_f,
    stage_k,
    config: HomeOfficeConfig,
) -> pd.DataFrame:
    """Return 9/9-trial TRAIN-only emission plus geometry retention fraction."""
    if N_TRIALS != 9 or config.location_max_diameter_m != 200:
        raise ValueError("Frozen protocol requires 9 masks and 200m geometry")
    keys = _unique(
        emitted.rename(columns={"location_id": "train_location_id"}),
        name="TRAIN emissions",
    )
    records = []
    for user, group in keys.groupby("user_id", sort=True):
        original_stays = train.loc[train["user_id"].astype(str).eq(user)]
        if original_stays.empty:
            raise ValueError("TRAIN emission user has no TRAIN stays")
        retained = Counter({(str(r.label), int(r.train_location_id)): 0
                            for r in group.itertuples(index=False)})
        for rate in DROPOUT_RATES:
            for replicate in DROPOUT_SEEDS:
                masked = mask_train_dates(
                    original_stays, rate=rate,
                    seed=_seed(user, rate, replicate),
                )
                if masked.empty:
                    continue
                perturb_emissions, perturb_semantic = stage_f.train_only_emissions(
                    masked, config=config
                )
                by_label = {
                    str(r.label): r for r in perturb_emissions.itertuples(index=False)
                } if not perturb_emissions.empty else {}
                for original in group.itertuples(index=False):
                    repl = by_label.get(str(original.label))
                    if repl is None:
                        continue
                    identity = stage_k.anchor_geometry(
                        _geom_members(semantic, original),
                        _geom_members(perturb_semantic, repl),
                        threshold_m=config.location_max_diameter_m,
                    )
                    if identity == "strict_compatible":
                        retained[(str(original.label), int(original.train_location_id))] += 1
        for original in group.itertuples(index=False):
            count = retained[(str(original.label), int(original.train_location_id))]
            records.append({
                "user_id": user, "label": str(original.label),
                "train_location_id": int(original.train_location_id),
                "train_mask_trial_count": N_TRIALS,
                "train_mask_same_anchor_count": int(count),
                "train_mask_stability_R": count / N_TRIALS,
            })
    result = _unique(pd.DataFrame(records), name="TRAIN dropout R")
    if (
        len(result) != len(keys)
        or not result["train_mask_stability_R"].between(0, 1).all()
    ):
        raise ValueError("TRAIN-only dropout robustness parity failed")
    return result


def build_paired_private(
    stays: pd.DataFrame,
    stage10f_private: pd.DataFrame,
    stage10i_private: pd.DataFrame,
    stage10j_reference: dict,
) -> pd.DataFrame:
    cfg = HomeOfficeConfig()
    if (
        cfg.clustering_method != "complete_link"
        or cfg.location_max_diameter_m != 200
        or cfg.support_saturation_dates != 5
    ):
        raise ValueError("Frozen CP2 v1/v2 protocol drift")
    ten_f = _load("stage10f_10l", "10f_train_only_forward_validation.py")
    ten_h = _load("stage10h_10l", "10h_train_only_component_audit.py")
    ten_i = _load("stage10i_10l", "10i_future_spatial_observability.py")
    ten_k = _load("stage10k_10l", "10k_paired_anchor_common_future_audit.py")
    ten_v2 = _load("stage10_v2_10l", "10_evidence_v2_experiment.py")

    early = _unique(stage10f_private, name="Stage10f")
    spatial = _unique(stage10i_private, name="Stage10i")
    expected = _reference70(stage10j_reference)
    if expected["train_fraction"] != FRACTION:
        raise ValueError("Expected frozen 70% reference")

    observed = ten_i.summarize_spatial(spatial)
    if (
        observed["overall"] != expected["overall"]
        or {r["label"]: r for r in observed["labels"]}
        != {r["label"]: r for r in expected["labels"]}
    ):
        raise ValueError("Stage10i/10j 70% spatial aggregate parity failed")
    if len(early) != expected["overall"]["train_emitted"]:
        raise ValueError("Stage10f/10j 70% emission parity failed")

    components = ten_h.build_train_only_features(
        stays, early, train_fraction=FRACTION, config=cfg
    )
    components = _unique(components, name="Stage10h rebuilt")
    joined = components.merge(
        spatial[JOIN + [
            "observed_future_window_dates", "unique_anchor_supported_dates",
            "same_anchor_supported_dates", "other_anchor_supported_dates",
        ]],
        on=JOIN, how="outer", indicator=True, validate="one_to_one",
    )
    if not joined["_merge"].eq("both").all():
        raise ValueError("Stage10h/Stage10i private candidate identity drift")
    joined = joined.drop(columns="_merge")
    if not (
        joined["future_observed_window_dates"].eq(
            joined["observed_future_window_dates"]
        ).all()
        and joined["future_same_anchor_window_dates"].eq(
            joined["same_anchor_supported_dates"]
        ).all()
    ):
        raise ValueError("Stage10f/10i relevant-window date parity failed")

    train, _future, _split = ten_f.partition_stays(
        stays, train_fraction=FRACTION
    )
    emitted, semantic = ten_f.train_only_emissions(train, config=cfg)
    expected_keys = set(map(tuple, joined[JOIN].itertuples(index=False, name=None)))
    actual_keys = set(
        (str(x.user_id), str(x.label), int(x.location_id))
        for x in emitted.itertuples(index=False)
    )
    if actual_keys != expected_keys:
        raise ValueError("Stage10l train emission lineage drift")

    r = train_only_mask_robustness(
        train, emitted, semantic, stage_f=ten_f, stage_k=ten_k, config=cfg
    )
    joined = joined.merge(r, on=JOIN, how="outer",
                          indicator=True, validate="one_to_one")
    if not joined["_merge"].eq("both").all():
        raise ValueError("Missing TRAIN mask stability for candidate")
    joined = joined.drop(columns="_merge")
    if len(joined) != expected["overall"]["train_emitted"]:
        raise ValueError("TRAIN comparison cohort size drift")

    peer = joined["train_eligible_location_count"].to_numpy(int)
    top = joined["train_dwell_share"].to_numpy(float)
    difference = joined["train_share_margin"].to_numpy(float)
    second = top - difference
    valid_peer = peer >= 2
    if (
        np.any(peer < 1)
        or np.any(~np.isclose(second[peer == 1], 0, atol=1e-10))
        or np.any(second[valid_peer] <= 0)
        or np.any(second[valid_peer] > top[valid_peer])
    ):
        raise ValueError("TRAIN-only ranker peer provenance invalid")
    # Explicit undefined C for rankers with one eligible location.
    v2_input = pd.DataFrame({
        "user_id": joined["user_id"],
        "label": joined["label"],
        "location_id": joined["train_location_id"],
        "tier": "TRAIN_CP2_EMITTED",
        "exposure_regime": "TRAIN_ONLY",
        "top_share": top,
        "runner_up_share": np.where(valid_peer, second, np.nan),
        "candidate_support_days": joined["train_support_dates"],
        "opportunity_days": joined["train_observed_opportunity_dates"],
        "identity_stability": joined["train_mask_stability_R"],
    })
    scored = ten_v2.score_evidence_v2(v2_input)
    if (
        not scored.loc[valid_peer, "v2_status"].eq("ok").all()
        or not scored.loc[~valid_peer, "v2_status"].eq(
            "missing_or_invalid_runner_up"
        ).all()
    ):
        raise ValueError("TRAIN-only original v2 scorer coverage drift")
    # Same row order as joined/v2_input: no row selection or tuning using FUTURE.
    joined["evidence_v2_train_only"] = scored["evidence_v2"].to_numpy()
    joined["evidence_v2_status"] = scored["v2_status"].to_numpy()
    joined["future_time_observable"] = joined["observed_future_window_dates"].ge(1)
    joined["future_unique_spatial_observable"] = joined[
        "unique_anchor_supported_dates"
    ].ge(1)
    joined["future_same_anchor_reappears_spatial"] = joined[
        "same_anchor_supported_dates"
    ].ge(1)
    if (
        (joined["future_unique_spatial_observable"] &
         ~joined["future_time_observable"]).any()
        or (joined["future_same_anchor_reappears_spatial"] &
            ~joined["future_unique_spatial_observable"]).any()
    ):
        raise ValueError("FUTURE observability states impossible")
    joined["fair_head_to_head_cohort"] = (
        joined["future_unique_spatial_observable"]
        & joined["evidence_v2_train_only"].notna()
    )
    return joined


def _median(sub: pd.DataFrame, col: str, min_group: int):
    valid = pd.to_numeric(sub[col], errors="coerce").dropna()
    if len(sub) < min_group or len(valid) < min_group:
        return None
    return round(float(valid.median()), 6)


def _concordance(group: pd.DataFrame, score: str, *, min_group: int):
    """Tied-pair half-credit ranking of *anchor recurrence*, not accuracy."""
    yes = group.loc[group["future_same_anchor_reappears_spatial"], score].to_numpy(float)
    no = group.loc[~group["future_same_anchor_reappears_spatial"], score].to_numpy(float)
    if len(yes) < min_group or len(no) < min_group:
        return None
    comparison = yes[:, None] - no[None, :]
    return round(
        float((comparison > 1e-12).mean() +
              .5 * (np.abs(comparison) <= 1e-12).mean()), 6
    )


def summarize_head_to_head(rows: pd.DataFrame, *, min_group: int = 5) -> dict:
    if min_group < 5:
        raise ValueError("Require min_group>=5")
    if rows.empty or len(rows) != 44 or rows[JOIN].duplicated().any():
        raise ValueError("Stage10l expects unique frozen 70% TRAIN cohort")
    needed = {"train_evidence_strength", "evidence_v2_train_only",
              "evidence_v2_status", "future_time_observable",
              "future_unique_spatial_observable",
              "future_same_anchor_reappears_spatial", "train_mask_stability_R"}
    if needed - set(rows):
        raise ValueError("Stage10l scored or spatial columns missing")
    def one(g):
        time = g.loc[g["future_time_observable"]]
        spatial = time.loc[time["future_unique_spatial_observable"]]
        comparison = spatial.loc[spatial["evidence_v2_train_only"].notna()]
        yes = comparison.loc[comparison["future_same_anchor_reappears_spatial"]]
        no = comparison.loc[~comparison["future_same_anchor_reappears_spatial"]]
        return {
            "emitted": int(len(g)),
            "time_observable": int(len(time)),
            "spatially_observable": int(len(spatial)),
            "time_observable_spatially_unresolved": int(len(time) - len(spatial)),
            "same_anchor_in_spatial_cohort": int(
                spatial["future_same_anchor_reappears_spatial"].sum()
            ),
            "v2_scorable_all_emitted": int(g["evidence_v2_train_only"].notna().sum()),
            "v2_scorable_spatial": int(len(comparison)),
            "v2_missing_spatial": int(len(spatial) - len(comparison)),
            "train_mask_R_median": _median(g, "train_mask_stability_R", min_group),
            "v2_unavailable_reasons": dict(sorted(
                (str(k), int(v))
                for k, v in g.loc[g["evidence_v2_train_only"].isna(),
                                  "evidence_v2_status"].value_counts().items()
            )),
            "fair_comparison": {
                "n": int(len(comparison)),
                "reappeared": int(len(yes)),
                "other_train_anchor": int(len(no)),
                "median_v1_reappeared": _median(yes, "train_evidence_strength", min_group),
                "median_v1_other": _median(no, "train_evidence_strength", min_group),
                "median_v2_reappeared": _median(yes, "evidence_v2_train_only", min_group),
                "median_v2_other": _median(no, "evidence_v2_train_only", min_group),
                "pairwise_recurrence_concordance_v1": _concordance(
                    comparison, "train_evidence_strength", min_group=min_group
                ),
                "pairwise_recurrence_concordance_v2": _concordance(
                    comparison, "evidence_v2_train_only", min_group=min_group
                ),
                "ranking_comparison_estimable": (
                    len(yes) >= min_group and len(no) >= min_group
                ),
            },
        }

    result = {
        "experiment": "stage10l_train_only_evidence_v1_v2_common_spatial_cohort",
        "stage10i_10j_70pct_parity": True,
        "train_only_candidate_features": True,
        "train_mask_protocol": {
            "drop_utc_arrival_date_fractions": list(DROPOUT_RATES),
            "deterministic_replicates_each_fraction": len(DROPOUT_SEEDS),
            "trials_per_candidate": N_TRIALS,
            "spatial_compatibility_m": 200,
            "future_observations_used_for_R": False,
        },
        "v1_score": "(S+M+H)/3, unchanged frozen CP2",
        "v2_score": "cbrt(C*O*R_train_mask)*sqrt(H), original hypothesis",
        "original_stage05_R_reused": False,
        "missing_C_imputed": False,
        "ground_truth_semantic_accuracy": None,
        "calibrated_probability": None,
        "independent_validation": False,
        "production_replacement": False,
        "overall": one(rows),
        "labels": [
            {"label": str(label), **one(g)}
            for label, g in rows.groupby("label", sort=True)
        ],
        "train_peer_groups": [
            {"label": str(name), **one(g)}
            for name, g in rows.groupby("train_peer_group", sort=True)
        ],
        "notes": (
            "V1 and v2 are ranked only on the EXACT same TRAIN-emitted anchors "
            "with FUTURE >=1 relevant 600s/date uniquely assigned to a frozen "
            "TRAIN cluster and usable TRAIN-only C/O/R/H. Singleton rankers "
            "have unavailable C; v2 coverage is selected and does not represent "
            "all users. Spatially unresolved and unobserved periods abstain, "
            "not false labels. R is a new predeclared TRAIN-only nine-mask "
            "stability proxy, not equivalent to Stage05 full-history R. "
            "Pairwise score concordance tests anchor-reappearance ordering, "
            "NOT HOME/OFFICE semantics or calibrated correctness, and is "
            "suppressed when fewer than min_group reappeared or other cases. "
            "No tuning, statistical significance, deployed score change, "
            "CP1 re-extraction or independent replication."
        ),
    }
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stays-cache", type=Path, default=Path(
        "/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl"
    ))
    parser.add_argument("--cache-root", type=Path, default=Path(
        "/mnt/geolife-data/cache/cp2_v2"
    ))
    args = parser.parse_args()
    root = args.cache_root / "10_evidence_v2_offline"
    needed = {
        "CP1": args.stays_cache,
        "Stage10f": root / "train_only_forward_candidates_private.pkl",
        "Stage10i": root / "future_spatial_observability_private.pkl",
        "Stage10j": root / "cutoff_sensitivity_aggregate.json",
    }
    absent = [key for key, value in needed.items() if not value.is_file()]
    if absent:
        parser.error(f"Missing trusted Modal prerequisite: {absent}")
    stays = pd.read_pickle(args.stays_cache)
    if len(stays) != 5821 or stays["user_id"].astype(str).nunique() != 136:
        raise ValueError("Frozen CP1 5821/136 parity failed")
    frame = build_paired_private(
        stays,
        pd.read_pickle(needed["Stage10f"]),
        pd.read_pickle(needed["Stage10i"]),
        json.loads(needed["Stage10j"].read_text(encoding="utf-8")),
    )
    report = summarize_head_to_head(frame)
    root.mkdir(parents=True, exist_ok=True)
    frame.to_pickle(root / "train_only_v1_v2_paired_private.pkl")
    (root / "train_only_v1_v2_paired_aggregate.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
