"""Private Modal-cache adapter for Stage-10 Evidence v2 research.

Reads only TRUSTED existing pickle artifacts on a private Modal Volume. This
script does not recompute CP1/stays, mutate the frozen CP2, or copy user GPS to
GitHub/AWS. Private joined per-user rows never go to stdout.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd


EXPECTED_TIERS = {
    "HOME_CORE": 27,
    "OFFICE_CORE": 16,
    "HOME_PROBABLE": 5,
    "HOME_SPARSE_CANDIDATE": 4,
    "OFFICE_ROBUST_CANDIDATE": 3,
}


def load_scorer():
    path = Path(__file__).with_name("10_evidence_v2_experiment.py")
    spec = importlib.util.spec_from_file_location("stage10_evidence_v2", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Cannot import evidence v2 scorer")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def required_cache_files(root: Path) -> dict[str, Path]:
    return {
        "diagnostics": root / "08b_exposure_bias_audit" / "gate_diagnostics_private.pkl",
        "home_expansion": root / "08a_home_coverage_expansion" / "home_expansion_evidence_private.pkl",
        "sparse_home": root / "08c_exposure_aware_policy" / "sparse_home_support_candidates_private.pkl",
        "dense_home": root / "08c_exposure_aware_policy" / "dense_home_concentration_candidates_private.pkl",
        "dense_office": root / "08c_exposure_aware_policy" / "dense_office_near_miss_candidates_private.pkl",
        "dropout": root / "05_home_office_reliability_validation" / "dropout_details_private.pkl",
    }


def _validate(frame: pd.DataFrame, name: str, cols: set[str]) -> None:
    missing = cols.difference(frame.columns)
    if missing:
        raise ValueError(f"{name}: missing columns: {sorted(missing)}")


def _identity(frame: pd.DataFrame, name: str, id_col: str) -> pd.DataFrame:
    _validate(frame, name, {"user_id", id_col})
    out = frame.copy()
    if out["user_id"].isna().any() or out[id_col].isna().any():
        raise ValueError(f"{name}: candidate identity contains missing values")
    out["user_id"] = out["user_id"].astype(str)
    ids = pd.to_numeric(out[id_col], errors="raise")
    if not np.isfinite(ids).all() or (ids < 0).any() or (ids != np.floor(ids)).any():
        raise ValueError(f"{name}: invalid location id")
    out[id_col] = ids.astype(int)
    if out["user_id"].duplicated().any():
        raise ValueError(f"{name}: duplicate user candidates")
    return out


def _one_label_diag(diag: pd.DataFrame, label: str) -> pd.DataFrame:
    out = diag.loc[diag["label"].astype(str).eq(label)].copy()
    out["user_id"] = out["user_id"].astype(str)
    if out["user_id"].duplicated().any():
        raise ValueError(f"Duplicate gate diagnostics for {label}")
    return out.set_index("user_id", verify_integrity=True)


def _fixed_dropout_stability(dropout: pd.DataFrame) -> dict[tuple[str, str, int], float]:
    """Reference *identity* retention across all fixed-window dropout trials.

    Stage-05 dropout does not cover the 2-of-2 SPARSE HOME ranker; no fallback
    score is invented. This is research input, NOT an independent validation
    outcome; later held-out checks must be disjoint from these trials.
    """
    _validate(
        dropout, "dropout",
        {
            "user_id", "method", "label", "location_id_reference",
            "candidate_retained",
        },
    )
    fixed = dropout.loc[dropout["method"].astype(str).eq("fixed_window")].copy()
    fixed = fixed.loc[fixed["location_id_reference"].notna()].copy()
    fixed["user_id"] = fixed["user_id"].astype(str)
    fixed["location_id_reference"] = pd.to_numeric(
        fixed["location_id_reference"], errors="raise"
    ).astype(int)
    if fixed["candidate_retained"].isna().any():
        raise ValueError("Dropout reference must not contain unknown retained status")
    retained = fixed["candidate_retained"]
    if not retained.isin((True, False, 0, 1)).all():
        raise ValueError("Dropout retained status must be boolean")
    fixed["candidate_retained"] = retained.astype(bool)
    group = fixed.groupby(
        ["user_id", "label", "location_id_reference"], sort=False
    )["candidate_retained"].agg(["size", "mean"])
    # Stage 05 declares 3 rates x 3 seeds, thus only full 9-trial evidence.
    return {
        (str(user), str(label), int(loc)): float(row["mean"])
        for (user, label, loc), row in group.iterrows()
        if int(row["size"]) == 9
    }


def build_candidate_features(
    diagnostics: pd.DataFrame,
    home_expansion: pd.DataFrame,
    sparse_home: pd.DataFrame,
    dense_home: pd.DataFrame,
    dense_office: pd.DataFrame,
    dropout: pd.DataFrame,
    *,
    enforce_reference_counts: bool = True,
) -> pd.DataFrame:
    """Join same-location and label-native fields; fail closed on namespace drift."""
    _validate(
        diagnostics, "diagnostics",
        {
            "user_id", "label", "production_HOME", "production_OFFICE",
            "eligible_location_id", "raw_top_location_id",
            "relevant_dwell_share", "share_margin", "relevant_dates",
            "raw_top_relevant_share", "raw_top_share_margin",
            "raw_top_relevant_dates",
            "home_opportunity_dates", "office_opportunity_dates",
            "home_exposure_regime", "office_exposure_regime",
        },
    )
    home_diag = _one_label_diag(diagnostics, "HOME")
    office_diag = _one_label_diag(diagnostics, "OFFICE")
    expansion = _identity(
        home_expansion.loc[
            home_expansion["home_expansion_tier"].astype(str).eq("HOME_PROBABLE")
        ], "home_expansion", "location_id",
    )
    home_dense = _identity(dense_home, "dense_home", "candidate_location_id")
    home_sparse = _identity(sparse_home, "sparse_home", "candidate_location_id")
    office_robust = _identity(
        dense_office.loc[dense_office["robust_policy_candidate"].eq(True)],
        "dense_office", "candidate_location_id",
    )
    if set(zip(expansion.user_id, expansion.location_id)) != set(
        zip(home_dense.user_id, home_dense.candidate_location_id)
    ):
        raise ValueError("08a HOME_PROBABLE identity differs from 08c dense HOME")
    stability = _fixed_dropout_stability(dropout)
    rows: list[dict] = []

    def append_candidate(user: str, label: str, location: int, tier: str, source: str):
        table = home_diag if label == "HOME" else office_diag
        if user not in table.index:
            raise ValueError(f"{source}: candidate missing in gate diagnostics")
        d = table.loc[user]
        sparse = tier == "HOME_SPARSE_CANDIDATE"
        id_key = "raw_top_location_id" if sparse else "eligible_location_id"
        actual = pd.to_numeric(pd.Series([d[id_key]]), errors="coerce").iloc[0]
        if pd.isna(actual) or int(actual) != int(location):
            raise ValueError(f"{source}: candidate not the matching same-namespace {id_key}")
        s_key = "raw_top_relevant_share" if sparse else "relevant_dwell_share"
        m_key = "raw_top_share_margin" if sparse else "share_margin"
        days_key = "raw_top_relevant_dates" if sparse else "relevant_dates"
        prefix = "home" if label == "HOME" else "office"
        top = float(d[s_key])
        margin = float(d[m_key])
        runner_up = top - margin
        # A missing runner-up in Stage-08b is encoded as margin==top;
        # do NOT quietly treat this as a known second-best of zero.
        if np.isclose(runner_up, 0.0, atol=1e-12):
            runner_up = np.nan
        rows.append(
            {
                "user_id": user,
                "label": label,
                "location_id": int(location),
                "tier": tier,
                "exposure_regime": str(d[f"{prefix}_exposure_regime"]),
                "top_share": top,
                "runner_up_share": runner_up,
                "candidate_support_days": int(d[days_key]),
                "opportunity_days": int(d[f"{prefix}_opportunity_dates"]),
                "identity_stability": (
                    np.nan if sparse else
                    stability.get((user, label, int(location)), np.nan)
                ),
                "source_policy": source,
            }
        )

    for label, table in (("HOME", home_diag), ("OFFICE", office_diag)):
        selected = table.loc[table[f"production_{label}"].astype("boolean").fillna(False)]
        for user, row in selected.iterrows():
            if pd.isna(row["eligible_location_id"]):
                raise ValueError("Production candidate missing eligible ID")
            append_candidate(
                str(user), label, int(row["eligible_location_id"]),
                f"{label}_CORE", "frozen_cp2_v2",
            )
    for row in expansion.itertuples(index=False):
        append_candidate(row.user_id, "HOME", int(row.location_id), "HOME_PROBABLE", "08a_08c")
    for row in home_sparse.itertuples(index=False):
        append_candidate(
            row.user_id, "HOME", int(row.candidate_location_id),
            "HOME_SPARSE_CANDIDATE", "08c_sparse_2of2",
        )
    for row in office_robust.itertuples(index=False):
        append_candidate(
            row.user_id, "OFFICE", int(row.candidate_location_id),
            "OFFICE_ROBUST_CANDIDATE", "08c_dense_robust",
        )
    result = pd.DataFrame(rows)
    if result.empty:
        raise ValueError("No research candidates")
    if result.duplicated(["user_id", "label"]).any():
        raise ValueError("Same user/label appears in multiple candidate tiers")
    counts = {str(k): int(v) for k, v in result["tier"].value_counts().items()}
    if enforce_reference_counts and counts != EXPECTED_TIERS:
        raise ValueError(
            "Stage-08a/08c lineage or frozen parity drift: "
            f"tier counts {counts}, expected {EXPECTED_TIERS}"
        )
    return result


def load_private_features(
    root: Path, *, enforce_reference_counts: bool = True
) -> pd.DataFrame:
    paths = required_cache_files(root)
    missing = [name for name, path in paths.items() if not path.is_file()]
    if missing:
        raise FileNotFoundError(f"Missing PRIVATE Stage artifacts: {sorted(missing)}")
    # Pickle can execute code: all files must originate only from the trusted
    # frozen Modal Volume and never from a user upload or untrusted download.
    frames = {name: pd.read_pickle(path) for name, path in paths.items()}
    return build_candidate_features(
        **frames, enforce_reference_counts=enforce_reference_counts
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache-root", type=Path,
        default=Path("/mnt/geolife-data/cache/cp2_v2"),
    )
    parser.add_argument("--min-group", type=int, default=5)
    args = parser.parse_args()
    features = load_private_features(args.cache_root)
    score = load_scorer()
    scored = score.score_evidence_v2(features)
    report = score.aggregate_report(scored, min_group=args.min_group)

    # Private artifacts remain on the existing PRIVATE Modal Volume. No GPS
    # coordinates in these tables, but candidate user IDs/labels are sensitive.
    out = args.cache_root / "10_evidence_v2_offline"
    out.mkdir(parents=True, exist_ok=True)
    features.to_pickle(out / "candidate_features_private.pkl")
    scored.to_pickle(out / "candidate_scored_private.pkl")
    (out / "aggregate_summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
