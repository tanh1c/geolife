"""Stage 10k — paired TRAIN-anchor identity and common-FUTURE audit (research only).

Refit frozen CP2 for 60/70/80 TRAIN; compare emitted user-label pairs using
TRAIN-only geometry (never compare cluster integer IDs across fits). Project the
same nested later FUTURE stays into each frozen TRAIN geometry for paired tests.
Do not infer semantic truth from recurrence, spatial matching, or abstentions.

Trusted CP1/Stage10j inputs and private paired rows remain on Modal Volume.
Only aggregate JSON is printed. No production baseline or AWS changes.
"""
from __future__ import annotations

import argparse
from collections import Counter
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

from geolife.geo.distance import haversine_m
from geolife.model import HomeOfficeConfig
from geolife.model import home_office as cp2


FRACTIONS = (0.60, 0.70, 0.80)
PAIRS = ((0.60, 0.70), (0.70, 0.80), (0.60, 0.80))
KEYS = ("user_id", "label")
STAY_KEYS = (
    "user_id", "arrival_time_utc", "departure_time_utc",
    "duration_s", "latitude", "longitude",
)


def _load(alias: str, filename: str):
    source = Path(__file__).with_name(filename)
    spec = importlib.util.spec_from_file_location(alias, source)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _keyed(frame: pd.DataFrame) -> dict:
    if frame.empty:
        return {}
    missing = set(KEYS) - set(frame.columns)
    if missing:
        raise ValueError(f"Candidate keys missing: {sorted(missing)}")
    if frame.duplicated(list(KEYS)).any():
        raise ValueError("Duplicate user-label emitted in one TRAIN cutoff")
    return {
        (str(row.user_id), str(row.label)): row
        for row in frame.itertuples(index=False)
    }


def assert_nested_future(early: pd.DataFrame, late: pd.DataFrame) -> None:
    """Later cutoff's exact stay multiset must be a subset of earlier FUTURE."""
    a = early.groupby(list(STAY_KEYS), dropna=False).size()
    b = late.groupby(list(STAY_KEYS), dropna=False).size()
    if (b > a.reindex(b.index, fill_value=0)).any():
        raise ValueError("FUTURE is not nested; cannot pair a common horizon")


def anchor_geometry(
    left: pd.DataFrame, right: pd.DataFrame, *, threshold_m: float,
) -> str:
    """Cross-member geometry: compatible / fully separated / indeterminate.

    A partial overlap is *not* automatically a changed physical location.
    A matching location_id integer does not establish physical identity.
    """
    if left.empty or right.empty:
        raise ValueError("Cannot compare empty TRAIN clusters")
    a = left[["latitude", "longitude"]].to_numpy(dtype=float)
    b = right[["latitude", "longitude"]].to_numpy(dtype=float)
    distance = np.asarray(haversine_m(
        a[:, 0, None], a[:, 1, None],
        b[None, :, 0], b[None, :, 1],
    ), dtype=float)
    if not np.isfinite(distance).all():
        raise ValueError("Nonfinite TRAIN cluster distances")
    if float(distance.max()) <= threshold_m + 1e-6:
        return "strict_compatible"
    if float(distance.min()) > threshold_m + 1e-6:
        return "fully_separated"
    return "partial_overlap_uncertain"


def _members(semantic: pd.DataFrame, candidate) -> pd.DataFrame:
    return semantic.loc[
        semantic["user_id"].astype(str).eq(str(candidate.user_id))
        & semantic["location_id"].eq(int(candidate.location_id))
    ]


def _assert_reference(current: dict, expected: dict, fraction: float):
    if expected.get("train_fraction") != fraction:
        raise ValueError(f"Stage10j fraction mismatch at {fraction}")
    for key in ("train_users_with_stays", "future_stays",
                "users_with_cutoff_crossing_stays"):
        if current[key] != expected[key]:
            raise ValueError(f"Stage10j {key} parity failed at {fraction}")
    for label in ("overall",):
        if current[label] != expected[label]:
            raise ValueError(f"Stage10j {label} parity failed at {fraction}")
    expected_labels = {x["label"]: x for x in expected["labels"]}
    actual_labels = {x["label"]: x for x in current["labels"]}
    if actual_labels != expected_labels:
        raise ValueError(f"Stage10j label parity failed at {fraction}")


def _reference_rows(reference: dict) -> dict:
    if (
        reference.get("experiment") != "stage10j_forward_cutoff_sensitivity"
        or reference.get("fractions") != list(FRACTIONS)
    ):
        raise ValueError("Stage10j aggregate is missing/changed")
    results = reference.get("results", [])
    if len(results) != len(FRACTIONS):
        raise ValueError("Stage10j fraction results are incomplete")
    return {float(item["train_fraction"]): item for item in results}


def _state(row) -> str:
    if int(row.observed_future_window_dates) == 0:
        return "no_time_window"
    if int(row.same_anchor_supported_dates) >= 1:
        return "same_anchor"
    if int(row.unique_anchor_supported_dates) == 0:
        return "spatial_unresolved"
    if int(row.other_anchor_supported_dates) >= 1:
        return "other_train_anchor"
    return "unique_mixed_without_supported_other"


def _discordance(rows: list[dict], *, require_both_spatial=False) -> dict:
    subset = [
        row for row in rows
        if row["geometry"] == "strict_compatible"
        and row["early_state"] != "no_time_window"
        and (not require_both_spatial or (
            row["early_unique"] and row["late_unique"]
        ))
    ]
    counts = Counter()
    for row in subset:
        a = row["early_state"] == "same_anchor"
        b = row["late_state"] == "same_anchor"
        counts[
            "both_reappear" if a and b else
            "early_only" if a else
            "late_only" if b else "neither"
        ] += 1
    return {
        "paired_n": len(subset),
        "both_reappear": counts["both_reappear"],
        "early_only": counts["early_only"],
        "late_only": counts["late_only"],
        "neither": counts["neither"],
    }


def _status_overlap(aligned: pd.DataFrame, label: str, cfg) -> dict:
    contrib = cp2._window_contributions(
        aligned, config=cfg, kind=label.lower()
    )
    if contrib.empty:
        return {}
    result = {}
    for user, g in contrib.groupby("user_id", sort=False):
        result[str(user)] = {
            "unmatched": float(g.loc[g["location_id"].eq(-1), "overlap_s"].sum()),
            "ambiguous": float(g.loc[g["location_id"].eq(-2), "overlap_s"].sum()),
            "unique": float(g.loc[g["location_id"].ge(0), "overlap_s"].sum()),
        }
    return result


def _unresolved_detail(status: dict) -> str:
    if status.get("unique", 0) > 0:
        return "unique_overlap_below_qualified_date_support"
    unmatched = status.get("unmatched", 0) > 0
    ambiguous = status.get("ambiguous", 0) > 0
    if unmatched and ambiguous:
        return "unmatched_and_ambiguous_overlap"
    if unmatched:
        return "unmatched_overlap_only"
    if ambiguous:
        return "ambiguous_overlap_only"
    return "none_with_relevant_overlap"


def _aggregate_pair(rows: list[dict], *, first: float, second: float,
                    shared_stays: int, labels: bool = True) -> dict:
    states = Counter(row["emission_transition"] for row in rows)
    geometry = Counter(row["geometry"] for row in rows if row["geometry"])
    observed = [
        x for x in rows if x["emission_transition"] == "both_emitted"
        and x["early_state"] != "no_time_window"
    ]
    both_spatial = sum(x["early_unique"] and x["late_unique"] for x in observed)
    early_only_spatial = sum(
        x["early_unique"] and not x["late_unique"] for x in observed
    )
    late_only_spatial = sum(
        x["late_unique"] and not x["early_unique"] for x in observed
    )
    neither_spatial = sum(
        not x["early_unique"] and not x["late_unique"] for x in observed
    )
    result = {
        "early_train_fraction": first,
        "late_train_fraction": second,
        "common_future_stays": shared_stays,
        "emitted_union_user_labels": len(rows),
        "emission_transition": {
            name: states[name]
            for name in ("both_emitted", "early_only", "late_only")
        },
        "both_emitted_geometry": {
            name: geometry[name]
            for name in ("strict_compatible", "partial_overlap_uncertain",
                         "fully_separated")
        },
        "both_emitted_common_future_time_observable": len(observed),
        "paired_unique_spatial_opportunity": {
            "both": int(both_spatial),
            "early_only": int(early_only_spatial),
            "late_only": int(late_only_spatial),
            "neither": int(neither_spatial),
        },
        "strict_compatible_recurrence_on_common_time": _discordance(rows),
        "strict_compatible_recurrence_on_both_spatial": _discordance(
            rows, require_both_spatial=True
        ),
        "early_common_future_states": dict(sorted(Counter(
            r["early_state"] for r in observed
        ).items())),
        "late_common_future_states": dict(sorted(Counter(
            r["late_state"] for r in observed
        ).items())),
        "unresolved_early_details": dict(sorted(Counter(
            r["early_unresolved_detail"] for r in observed
            if r["early_state"] == "spatial_unresolved"
        ).items())),
        "unresolved_late_details": dict(sorted(Counter(
            r["late_unresolved_detail"] for r in observed
            if r["late_state"] == "spatial_unresolved"
        ).items())),
    }
    if labels:
        result["labels"] = [
            {"label": label, **_aggregate_pair(
                [r for r in rows if r["label"] == label],
                first=first, second=second, shared_stays=shared_stays,
                labels=False
            )}
            for label in ("HOME", "OFFICE")
        ]
        # common_future_stays in label blocks repeats the shared denominator,
        # not a count of HOME/ OFFICE stays.
    return result


def run_paired_audit(stays: pd.DataFrame, stage10j_reference: dict):
    """Return only aggregate report plus private user-label paired diagnostics."""
    stage_f = _load("stage10f_10k", "10f_train_only_forward_validation.py")
    stage_i = _load("stage10i_10k", "10i_future_spatial_observability.py")
    expected = _reference_rows(stage10j_reference)
    cfg = HomeOfficeConfig()
    if cfg.clustering_method != "complete_link" or cfg.location_max_diameter_m != 200:
        raise ValueError("Frozen CP2 complete-link 200m required")

    models = {}
    for fraction in FRACTIONS:
        train, future, partition = stage_f.partition_stays(
            stays, train_fraction=fraction
        )
        emitted, semantic = stage_f.train_only_emissions(train, config=cfg)
        if emitted.empty or future.empty:
            raise ValueError(f"No TRAIN emission/FUTURE at cutoff {fraction}")
        future_semantic = cp2._resolve_stay_timezones(cp2._validate_stays(future))
        aligned = stage_f.align_to_train_locations(
            future_semantic, semantic, max_diameter_m=cfg.location_max_diameter_m
        )
        outcomes = stage_f.evaluate_future_windows(emitted, aligned, config=cfg)
        audit = stage_i.audit_future_windows(outcomes, aligned, cfg)
        spatial = stage_i.summarize_spatial(audit)
        base = stage_f.aggregate_forward(
            outcomes, partition, aligned,
            n_train_users=int(semantic["user_id"].nunique()),
        )
        if (
            base["overall"]["future_window_assessable"]
            != spatial["overall"]["future_time_observable"]
            or base["overall"]["future_same_anchor_reappears"]
            != spatial["overall"]["future_same_anchor_reappears"]
        ):
            raise ValueError("Stage10f/10i parity failed")
        current = {
            "train_users_with_stays": base["train_users_with_stays"],
            "future_stays": len(aligned),
            "users_with_cutoff_crossing_stays": base["users_with_cutoff_crossing_stays"],
            "overall": spatial["overall"],
            "labels": spatial["labels"],
        }
        _assert_reference(current, expected[fraction], fraction)
        models[fraction] = {
            "future": future, "semantic": semantic, "emitted": emitted,
        }

    private_rows = []
    pair_reports = []
    for first, second in PAIRS:
        earlier, later = models[first], models[second]
        assert_nested_future(earlier["future"], later["future"])
        common_future = later["future"]
        shared_semantic = cp2._resolve_stay_timezones(
            cp2._validate_stays(common_future)
        )
        if len(shared_semantic) != len(common_future):
            raise ValueError("FUTURE timezone resolution drift")
        audits = {}
        emissions = {}
        status = {}
        for name, model in (("early", earlier), ("late", later)):
            aligned = stage_f.align_to_train_locations(
                shared_semantic, model["semantic"],
                max_diameter_m=cfg.location_max_diameter_m,
            )
            predictions = stage_f.evaluate_future_windows(
                model["emitted"], aligned, config=cfg
            )
            audited = stage_i.audit_future_windows(predictions, aligned, cfg)
            emissions[name] = _keyed(model["emitted"])
            audits[name] = _keyed(audited)
            status[name] = {
                label: _status_overlap(aligned, label, cfg)
                for label in ("HOME", "OFFICE")
            }
        rows = []
        keys = sorted(set(emissions["early"]) | set(emissions["late"]))
        for user, label in keys:
            key = (user, label)
            e = emissions["early"].get(key)
            l = emissions["late"].get(key)
            if e is None or l is None:
                rows.append({
                    "user_id": user, "label": label,
                    "emission_transition": "early_only" if l is None else "late_only",
                    "geometry": None,
                    "early_state": None, "late_state": None,
                    "early_unique": False, "late_unique": False,
                    "early_unresolved_detail": None,
                    "late_unresolved_detail": None,
                })
                continue
            identity = anchor_geometry(
                _members(earlier["semantic"], e),
                _members(later["semantic"], l),
                threshold_m=cfg.location_max_diameter_m,
            )
            early_row, late_row = audits["early"][key], audits["late"][key]
            early_state = _state(early_row)
            late_state = _state(late_row)
            if (
                int(early_row.observed_future_window_dates)
                != int(late_row.observed_future_window_dates)
            ):
                raise ValueError("Paired common FUTURE time-window parity failed")
            rows.append({
                "user_id": user, "label": label,
                "emission_transition": "both_emitted",
                "geometry": identity,
                "early_state": early_state, "late_state": late_state,
                "early_unique": int(early_row.unique_anchor_supported_dates) >= 1,
                "late_unique": int(late_row.unique_anchor_supported_dates) >= 1,
                "early_unresolved_detail": _unresolved_detail(
                    status["early"][label].get(user, {})
                ) if early_state == "spatial_unresolved" else None,
                "late_unresolved_detail": _unresolved_detail(
                    status["late"][label].get(user, {})
                ) if late_state == "spatial_unresolved" else None,
            })
        for row in rows:
            row["early_train_fraction"] = first
            row["late_train_fraction"] = second
        private_rows.extend(rows)
        pair_reports.append(_aggregate_pair(
            rows, first=first, second=second,
            shared_stays=len(common_future),
        ))
    report = {
        "experiment": "stage10k_paired_anchor_common_future_audit",
        "stage10j_aggregate_parity": True,
        "train_only_frozen_cp2": True,
        "future_refitting": False,
        "independent_participant_replications": False,
        "semantic_home_office_accuracy": None,
        "calibrated_probability": None,
        "fractions": list(FRACTIONS),
        "pairs": pair_reports,
        "notes": (
            "Matched by user and label, never by cross-cutoff location_id. "
            "Strict compatible means every cross-cluster TRAIN member pair is "
            "within 200m; partial overlap remains uncertain, not a move. "
            "Each pair projects exactly the same later-cutoff FUTURE stays "
            "against its two separately frozen TRAIN models. Counts conditional "
            "on matched emission, time and spatial opportunity use different "
            "denominators; neither is semantic accuracy. Cross-cutoff checks "
            "reuse users, and unmatched GPS cannot distinguish new travel "
            "from jitter/200m conservative mismatch."
        ),
    }
    return report, pd.DataFrame(private_rows)


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
    reference = root / "cutoff_sensitivity_aggregate.json"
    if not args.stays_cache.is_file() or not reference.is_file():
        parser.error("Trusted CP1 stays or Stage10j aggregate missing")
    stays = pd.read_pickle(args.stays_cache)  # user-owned private Modal Volume only
    if len(stays) != 5821 or stays["user_id"].astype(str).nunique() != 136:
        raise ValueError("Frozen CP1 reference 5821/136 parity failed")
    stage10j = json.loads(reference.read_text(encoding="utf-8"))
    result, private = run_paired_audit(stays, stage10j)
    root.mkdir(parents=True, exist_ok=True)
    private.to_pickle(root / "paired_anchor_common_future_private.pkl")
    (root / "paired_anchor_common_future_aggregate.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
