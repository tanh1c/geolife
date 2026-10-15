"""TRAIN-only retrospective 60/70/80 cutoff sensitivity, aggregate-only.

Cutoffs share participants; NOT independent validations or semantic accuracy.
All clusters are learned only from earlier CP1 stays; FUTURE GPS is used
only to evaluate spatial/time-window reappearance. Private inputs stay Modal.
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


def _load(label, name):
    p = Path(__file__).with_name(name)
    spec = importlib.util.spec_from_file_location(label, p)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


def run_cutoffs(stays, fractions=(0.60, 0.70, 0.80)):
    if not fractions or len(set(fractions)) != len(fractions):
        raise ValueError("Fractions must be unique and nonempty")
    if not all(0.5 <= f <= 0.9 for f in fractions):
        raise ValueError("Each fraction must be between 0.5 and 0.9")
    stage_f = _load("stage10f_multi", "10f_train_only_forward_validation.py")
    stage_i = _load("stage10i_multi", "10i_future_spatial_observability.py")
    cfg = HomeOfficeConfig()
    results = []
    for fraction in fractions:
        train, future, split = stage_f.partition_stays(
            stays, train_fraction=fraction
        )
        emitted, train_semantic = stage_f.train_only_emissions(
            train, config=cfg
        )
        if emitted.empty or future.empty:
            raise ValueError("No emitted TRAIN anchor or FUTURE stays")
        fut = cp2._resolve_stay_timezones(cp2._validate_stays(future))
        aligned = stage_f.align_to_train_locations(
            fut, train_semantic, max_diameter_m=cfg.location_max_diameter_m
        )
        outcomes = stage_f.evaluate_future_windows(emitted, aligned, config=cfg)
        audit = stage_i.audit_future_windows(outcomes, aligned, cfg)
        spatial = stage_i.summarize_spatial(audit)
        base = stage_f.aggregate_forward(
            outcomes, split, aligned,
            n_train_users=int(train_semantic["user_id"].nunique()),
        )
        if (
            spatial["overall"]["future_time_observable"]
            != base["overall"]["future_window_assessable"]
            or spatial["overall"]["future_same_anchor_reappears"]
            != base["overall"]["future_same_anchor_reappears"]
        ):
            raise ValueError("TRAIN outcome vs spatial opportunity parity failed")
        results.append({
            "train_fraction": fraction,
            "train_users_with_stays": base["train_users_with_stays"],
            "future_stays": len(aligned),
            "users_with_cutoff_crossing_stays":
                base["users_with_cutoff_crossing_stays"],
            "overall": spatial["overall"],
            "labels": spatial["labels"],
        })
    return {
        "experiment": "stage10j_forward_cutoff_sensitivity",
        "independent_participant_replications": False,
        "calibrated_probability": None,
        "semantic_home_office_accuracy": None,
        "fractions": list(fractions),
        "results": results,
        "notes": (
            "Each fraction refits frozen CP2 clusters/labels on TRAIN only "
            "and uses FUTURE solely for time/spatial evaluation. The same "
            "users may contribute to nested splits; outcomes and denominators "
            "are correlated and may change. This is descriptive cutoff "
            "sensitivity, not model accuracy or independent replication."
        ),
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--stays-cache", type=Path, default=Path(
        "/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl"
    ))
    p.add_argument("--cache-root", type=Path, default=Path(
        "/mnt/geolife-data/cache/cp2_v2"
    ))
    args = p.parse_args()
    if not args.stays_cache.is_file():
        p.error("Missing trusted CP1 stays")
    data = pd.read_pickle(args.stays_cache)
    if len(data) != 5821 or data["user_id"].astype(str).nunique() != 136:
        raise ValueError("Frozen CP1 reference parity failed")
    result = run_cutoffs(data)
    folder = args.cache_root / "10_evidence_v2_offline"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "cutoff_sensitivity_aggregate.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
