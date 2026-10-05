"""Stage 08c: exposure-aware HOME/OFFICE policy experiment.

This stage compares predeclared exposure-aware candidate rules against the
frozen production baseline (HOME 27 / OFFICE 16). It does not modify production.

Rules are label-specific because Stage 08b showed different evidence regimes:
- sparse HOME retains recurrence signal but can be blocked by min_dates=3;
- dense HOME/OFFICE can have support but diluted absolute share/margin;
- sparse OFFICE has no Stage-05 comparator coverage, so it is not relaxed here.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


HOME_RELATIVE_DOMINANCE_FLOOR = 0.625
OFFICE_RELATIVE_DOMINANCE_FLOOR = 0.60


def relative_top2_dominance(
    top_share: pd.Series | np.ndarray,
    share_margin: pd.Series | np.ndarray,
) -> np.ndarray:
    """Return top / (top + runner-up), deriving runner-up from share margin."""
    top = np.asarray(pd.to_numeric(top_share, errors="coerce"), dtype=float)
    margin = np.asarray(pd.to_numeric(share_margin, errors="coerce"), dtype=float)
    second = top - margin
    denom = top + second
    out = np.full(len(top), np.nan, dtype=float)
    valid = np.isfinite(top) & np.isfinite(second) & (top >= 0) & (second >= 0) & (denom > 0)
    out[valid] = top[valid] / denom[valid]
    return out


def _production_location_map(
    production_output: pd.DataFrame,
    *,
    label: str,
) -> dict[str, int]:
    frame = production_output.copy()
    frame["user_id"] = frame["user_id"].astype(str)
    frame["label"] = frame["label"].astype(str).str.upper()
    subset = frame.loc[frame["label"].eq(label), ["user_id", "location_id"]].copy()
    if subset["user_id"].duplicated().any():
        raise ValueError(f"production {label} must be one row per user")
    return {
        str(row.user_id): int(row.location_id)
        for row in subset.itertuples(index=False)
    }


def _method_map(
    assignments: pd.DataFrame,
    *,
    label: str,
    method: str,
) -> dict[str, int]:
    frame = assignments.copy()
    frame["user_id"] = frame["user_id"].astype(str)
    subset = frame.loc[
        frame["label"].astype(str).str.upper().eq(label)
        & frame["method"].astype(str).eq(method),
        ["user_id", "location_id"],
    ].drop_duplicates("user_id")
    return {
        str(row.user_id): int(row.location_id)
        for row in subset.itertuples(index=False)
        if pd.notna(row.location_id)
    }


def sparse_home_support_candidates(
    diagnostics: pd.DataFrame,
    assignments: pd.DataFrame,
    production_output: pd.DataFrame,
) -> pd.DataFrame:
    """Conservative 2-of-2 HOME support rule for SPARSE users.

    Preconditions:
    - SPARSE HOME exposure;
    - blocked by global min_dates;
    - exactly two observed HOME opportunity dates;
    - raw top candidate supported on both dates;
    - baseline HOME share >= .50 and margin >= .20 still hold;
    - recurrence selects the same location;
    - candidate is not production OFFICE.

    The only relaxed production condition is absolute support dates: 3 -> 2.
    """
    home = diagnostics.loc[diagnostics["label"].astype(str).eq("HOME")].copy()
    home["user_id"] = home["user_id"].astype(str)
    recurrence = _method_map(assignments, label="HOME", method="recurrence")
    office = _production_location_map(production_output, label="OFFICE")

    raw_id = pd.to_numeric(home["raw_top_location_id"], errors="coerce")
    home["recurrence_location_id"] = home["user_id"].map(recurrence)
    home["production_office_location_id"] = home["user_id"].map(office)
    home["recurrence_matches_raw_top"] = (
        (
            pd.to_numeric(home["recurrence_location_id"], errors="coerce")
            .astype("Int64")
            .eq(raw_id.astype("Int64"))
        )
        & raw_id.notna()
    ).fillna(False)
    home["collides_with_production_office"] = (
        (
            pd.to_numeric(home["production_office_location_id"], errors="coerce")
            .astype("Int64")
            .eq(raw_id.astype("Int64"))
        )
        & raw_id.notna()
    ).fillna(False)

    mask = (
        home["home_exposure_regime"].astype(str).eq("SPARSE")
        & home["gate_status"].astype(str).eq("min_dates_blocked")
        & pd.to_numeric(home["home_opportunity_dates"], errors="coerce").eq(2)
        & pd.to_numeric(home["raw_top_relevant_dates"], errors="coerce").eq(2)
        & np.isclose(
            pd.to_numeric(home["raw_top_date_coverage"], errors="coerce"),
            1.0,
        )
        & pd.to_numeric(home["raw_top_relevant_share"], errors="coerce").ge(0.50)
        & pd.to_numeric(home["raw_top_share_margin"], errors="coerce").ge(0.20)
        & home["recurrence_matches_raw_top"]
        & ~home["collides_with_production_office"]
        & ~home["production_HOME"].astype("boolean").fillna(False).astype(bool)
    )

    out = home.loc[mask].copy()
    out["candidate_location_id"] = pd.to_numeric(
        out["raw_top_location_id"], errors="raise"
    ).astype(int)
    out["policy_candidate_type"] = "HOME_SPARSE_2OF2_RECURRENCE"
    return out.sort_values("user_id", kind="stable").reset_index(drop=True)


def dense_home_concentration_candidates(
    diagnostics: pd.DataFrame,
    home_expansion: pd.DataFrame,
) -> pd.DataFrame:
    """Test relative concentration on already-corroborated HOME_PROBABLE cases.

    The relative-dominance floor 0.625 is derived from the frozen HOME boundary:
    top=.50, margin=.20 => runner-up=.30 => .50/(.50+.30)=.625.
    """
    diag = diagnostics.loc[diagnostics["label"].astype(str).eq("HOME")].copy()
    diag["user_id"] = diag["user_id"].astype(str)

    exp = home_expansion.loc[
        home_expansion["home_expansion_tier"].astype(str).eq("HOME_PROBABLE")
    ].copy()
    exp["user_id"] = exp["user_id"].astype(str)
    exp["location_id"] = pd.to_numeric(exp["location_id"], errors="raise").astype(int)

    keep = [
        "user_id",
        "location_id",
        "home_expansion_tier",
        "external_exact_family_count",
        "collides_with_production_office",
    ]
    joined = diag.merge(
        exp[[c for c in keep if c in exp.columns]],
        on="user_id",
        how="inner",
        validate="one_to_one",
    )
    eligible_id = pd.to_numeric(joined["eligible_location_id"], errors="coerce")
    joined["candidate_matches_eligible_top"] = (
        eligible_id.astype("Int64").eq(joined["location_id"].astype("Int64"))
        & eligible_id.notna()
    )
    joined["relative_top2_dominance"] = relative_top2_dominance(
        joined["relevant_dwell_share"],
        joined["share_margin"],
    )

    dilution_status = {
        "share_blocked",
        "margin_blocked",
        "share_and_margin_blocked",
    }
    mask = (
        joined["home_exposure_regime"].astype(str).eq("DENSE")
        & joined["gate_status"].astype(str).isin(dilution_status)
        & joined["candidate_matches_eligible_top"]
        & pd.to_numeric(joined["relative_top2_dominance"], errors="coerce").ge(
            HOME_RELATIVE_DOMINANCE_FLOOR
        )
        & ~joined["collides_with_production_office"].fillna(False).astype(bool)
        & ~joined["production_HOME"].astype("boolean").fillna(False).astype(bool)
    )
    out = joined.loc[mask].copy()
    out["candidate_location_id"] = out["location_id"].astype(int)
    out["policy_candidate_type"] = "HOME_DENSE_RELATIVE_DOMINANCE"
    return out.sort_values("user_id", kind="stable").reset_index(drop=True)


def dense_office_near_miss_candidates(
    diagnostics: pd.DataFrame,
    near_miss_panel: pd.DataFrame,
) -> pd.DataFrame:
    """Test a robust dense-OFFICE concentration rule on the audited near misses.

    The relative-dominance floor 0.60 is derived from the frozen OFFICE boundary:
    top=.30, margin=.10 => runner-up=.20 => .30/(.30+.20)=.60.

    Robust candidate additionally requires:
    - dropout retention >= .80; and
    - at least one identity/robustness corroborator:
      static comparator match, split match, or held-out top-1.
    """
    diag = diagnostics.loc[diagnostics["label"].astype(str).eq("OFFICE")].copy()
    diag["user_id"] = diag["user_id"].astype(str)

    near = near_miss_panel.loc[
        near_miss_panel["audit_group"].astype(str).ne("baseline")
    ].copy()
    near["user_id"] = near["user_id"].astype(str)
    near["candidate_location_id"] = pd.to_numeric(
        near["candidate_location_id"], errors="raise"
    ).astype(int)

    joined = diag.merge(near, on="user_id", how="inner", validate="one_to_one")
    eligible_id = pd.to_numeric(joined["eligible_location_id"], errors="coerce")
    joined["candidate_matches_eligible_top"] = (
        eligible_id.astype("Int64")
        .eq(joined["candidate_location_id"].astype("Int64"))
        & eligible_id.notna()
    )
    joined["relative_top2_dominance"] = relative_top2_dominance(
        joined["relevant_dwell_share"],
        joined["share_margin"],
    )
    joined["robustness_corroborated"] = (
        pd.to_numeric(joined["static_comparator_match_count"], errors="coerce").fillna(0).ge(1)
        | pd.to_numeric(joined["split_full_candidate_match_count"], errors="coerce").fillna(0).ge(1)
        | joined["full_candidate_heldout_top1"].fillna(False).astype(bool)
    )

    candidate_pool = (
        joined["office_exposure_regime"].astype(str).eq("DENSE")
        & joined["candidate_matches_eligible_top"]
        & pd.to_numeric(joined["relative_top2_dominance"], errors="coerce").ge(
            OFFICE_RELATIVE_DOMINANCE_FLOOR
        )
        & ~joined["candidate_equals_production_home"].fillna(False).astype(bool)
        & ~joined["production_OFFICE"].astype("boolean").fillna(False).astype(bool)
    )
    joined["relative_dominance_pool"] = candidate_pool
    joined["robust_policy_candidate"] = (
        candidate_pool
        & pd.to_numeric(joined["dropout_candidate_retention"], errors="coerce").ge(0.80)
        & joined["robustness_corroborated"]
    )

    out = joined.loc[candidate_pool].copy()
    out["policy_candidate_type"] = np.where(
        out["robust_policy_candidate"],
        "OFFICE_DENSE_ROBUST_RELATIVE",
        "OFFICE_DENSE_RELATIVE_POOL_ONLY",
    )
    return out.sort_values(["robust_policy_candidate", "user_id"], ascending=[False, True], kind="stable").reset_index(drop=True)


def candidate_funnel(
    sparse_home: pd.DataFrame,
    dense_home: pd.DataFrame,
    dense_office: pd.DataFrame,
) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "policy_branch": "HOME_SPARSE_2OF2_RECURRENCE",
                "candidate_users": int(sparse_home["user_id"].nunique()),
            },
            {
                "policy_branch": "HOME_DENSE_RELATIVE_DOMINANCE",
                "candidate_users": int(dense_home["user_id"].nunique()),
            },
            {
                "policy_branch": "OFFICE_DENSE_RELATIVE_POOL",
                "candidate_users": int(dense_office["user_id"].nunique()),
            },
            {
                "policy_branch": "OFFICE_DENSE_ROBUST_RELATIVE",
                "candidate_users": int(
                    dense_office.loc[
                        dense_office["robust_policy_candidate"].fillna(False)
                    ]["user_id"].nunique()
                ),
            },
        ]
    )


def policy_coverage_summary(
    sparse_home: pd.DataFrame,
    dense_home: pd.DataFrame,
    dense_office: pd.DataFrame,
    *,
    baseline_home: int = 27,
    baseline_office: int = 16,
) -> pd.DataFrame:
    sparse_users = set(sparse_home["user_id"].astype(str))
    dense_users = set(dense_home["user_id"].astype(str))
    if sparse_users.intersection(dense_users):
        raise ValueError("sparse and dense HOME candidate branches overlap")

    robust_office = set(
        dense_office.loc[
            dense_office["robust_policy_candidate"].fillna(False),
            "user_id",
        ].astype(str)
    )

    return pd.DataFrame(
        [
            {
                "policy": "frozen_baseline",
                "HOME_coverage": int(baseline_home),
                "OFFICE_coverage": int(baseline_office),
                "new_HOME": 0,
                "new_OFFICE": 0,
                "production_changed": False,
            },
            {
                "policy": "tiered_home_08a_plus_sparse_support",
                "HOME_coverage": int(baseline_home + len(dense_users) + len(sparse_users)),
                "OFFICE_coverage": int(baseline_office),
                "new_HOME": int(len(dense_users) + len(sparse_users)),
                "new_OFFICE": 0,
                "production_changed": False,
            },
            {
                "policy": "exposure_aware_experimental_all",
                "HOME_coverage": int(baseline_home + len(dense_users) + len(sparse_users)),
                "OFFICE_coverage": int(baseline_office + len(robust_office)),
                "new_HOME": int(len(dense_users) + len(sparse_users)),
                "new_OFFICE": int(len(robust_office)),
                "production_changed": False,
            },
        ]
    )


def office_robustness_summary(dense_office: pd.DataFrame) -> pd.DataFrame:
    if dense_office.empty:
        return pd.DataFrame(
            [{
                "relative_pool_users": 0,
                "robust_policy_users": 0,
                "static_match_users": 0,
                "split_match_users": 0,
                "heldout_top1_users": 0,
                "dropout_ge_80pct_users": 0,
            }]
        )
    return pd.DataFrame(
        [{
            "relative_pool_users": int(dense_office["user_id"].nunique()),
            "robust_policy_users": int(
                dense_office["robust_policy_candidate"].fillna(False).sum()
            ),
            "static_match_users": int(
                pd.to_numeric(
                    dense_office["static_comparator_match_count"], errors="coerce"
                ).fillna(0).ge(1).sum()
            ),
            "split_match_users": int(
                pd.to_numeric(
                    dense_office["split_full_candidate_match_count"], errors="coerce"
                ).fillna(0).ge(1).sum()
            ),
            "heldout_top1_users": int(
                dense_office["full_candidate_heldout_top1"].fillna(False).sum()
            ),
            "dropout_ge_80pct_users": int(
                pd.to_numeric(
                    dense_office["dropout_candidate_retention"], errors="coerce"
                ).ge(0.80).sum()
            ),
        }]
    )


def synthetic_self_check() -> dict[str, object]:
    dominance = relative_top2_dominance(
        pd.Series([0.50, 0.30]),
        pd.Series([0.20, 0.10]),
    )
    assert np.isclose(dominance[0], HOME_RELATIVE_DOMINANCE_FLOOR)
    assert np.isclose(dominance[1], OFFICE_RELATIVE_DOMINANCE_FLOOR)
    return {
        "status": "ok",
        "home_relative_floor": HOME_RELATIVE_DOMINANCE_FLOOR,
        "office_relative_floor": OFFICE_RELATIVE_DOMINANCE_FLOOR,
    }
