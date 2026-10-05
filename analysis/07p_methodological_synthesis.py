"""Stage 07p: final methodological synthesis for CP2-v2 HOME/OFFICE.

This stage consumes aggregate outputs already produced by Stage 05 and
Stages 07i/07j/07l/07m/07n/07o. It does not rerun raw GPS processing or semantic
inference. The goal is to make the evidence hierarchy and final policy decision
reproducible from cached aggregate artifacts.

No user-level private data are required.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd


REQUIRED_FILES = {
    "05_cross_method": "05_home_office_reliability_validation/cross_method_agreement.csv",
    "05_holdout": "05_home_office_reliability_validation/holdout_summary.csv",
    "05_dropout": "05_home_office_reliability_validation/dropout_summary.csv",
    "07i_office_gate": "07i_threshold_sensitivity/office_gate_sensitivity.csv",
    "07j_behavior": "07j_near_miss_office_audit/behavioral_robustness.csv",
    "07j_bcl": "07j_near_miss_office_audit/bcl_context_summary.csv",
    "07l_policy": "07l_imagery_unblinding_synthesis/policy_snapshot.csv",
    "07m_agreement": "07m_trackintel_semantic_parity/agreement_summary.csv",
    "07m_near_miss": "07m_trackintel_semantic_parity/near_miss_work_summary.csv",
    "07n_stay": "07n_trackintel_end_to_end/stay_match_summary.csv",
    "07n_location": "07n_trackintel_end_to_end/location_geometry_summary.csv",
    "07n_semantic": "07n_trackintel_end_to_end/semantic_candidate_summary.csv",
    "07o_suite": "07o_literature_comparator_suite/literature_suite_summary.csv",
    "07o_pavan_rank": "07o_literature_comparator_suite/pavan_rank_summary.csv",
    "07o_pavan_feature": "07o_literature_comparator_suite/pavan_feature_summary.csv",
    "07o_near_miss": "07o_literature_comparator_suite/scitepress_near_miss_summary.csv",
}


def load_aggregate_inputs(cache_root: Path) -> dict[str, pd.DataFrame]:
    cache_root = Path(cache_root)
    frames: dict[str, pd.DataFrame] = {}
    missing: list[str] = []

    for name, relative in REQUIRED_FILES.items():
        path = cache_root / relative
        if not path.exists():
            if name in {"07o_near_miss"}:
                continue
            missing.append(str(path))
            continue
        frames[name] = pd.read_csv(path)

    if missing:
        raise FileNotFoundError(
            "Stage 07p requires previously measured aggregate caches:\n"
            + "\n".join(missing)
        )
    return frames


def _one(frame: pd.DataFrame, mask: pd.Series, description: str) -> pd.Series:
    subset = frame.loc[mask]
    if len(subset) != 1:
        raise ValueError(f"{description}: expected exactly one row, found {len(subset)}")
    return subset.iloc[0]


def _fixed_cross_method(frames: dict[str, pd.DataFrame], label: str, right: str) -> pd.Series:
    frame = frames["05_cross_method"]
    return _one(
        frame,
        frame["label"].astype(str).eq(label)
        & frame["left_method"].astype(str).eq("fixed_window")
        & frame["right_method"].astype(str).eq(right),
        f"Stage 05 {label} fixed_window vs {right}",
    )


def _fixed_holdout(frames: dict[str, pd.DataFrame], label: str) -> pd.Series:
    frame = frames["05_holdout"]
    return _one(
        frame,
        frame["method"].astype(str).eq("fixed_window")
        & frame["label"].astype(str).eq(label),
        f"Stage 05 fixed_window {label} holdout",
    )


def _fixed_dropout30(frames: dict[str, pd.DataFrame], label: str) -> pd.Series:
    frame = frames["05_dropout"]
    rate = pd.to_numeric(frame["dropout_rate"], errors="coerce")
    return _one(
        frame,
        frame["method"].astype(str).eq("fixed_window")
        & frame["label"].astype(str).eq(label)
        & np.isclose(rate, 0.30),
        f"Stage 05 fixed_window {label} dropout 30%",
    )


def validate_measured_inputs(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Hard-check the measured lineage that Stage 07p is intended to synthesize."""

    checks: list[dict[str, object]] = []

    def add(name: str, actual: object, expected: object, *, atol: float = 1e-9) -> None:
        if isinstance(expected, float):
            passed = bool(np.isclose(float(actual), expected, atol=atol, rtol=0))
        else:
            passed = bool(actual == expected)
        checks.append(
            {
                "check": name,
                "actual": actual,
                "expected": expected,
                "passed": passed,
            }
        )

    home_rec = _fixed_cross_method(frames, "HOME", "recurrence")
    office_rec = _fixed_cross_method(frames, "OFFICE", "recurrence")
    add("05 HOME fixed-vs-recurrence same", int(home_rec["same_location_users"]), 35)
    add("05 HOME fixed-vs-recurrence overlap", int(home_rec["both_users"]), 42)
    add("05 OFFICE fixed-vs-recurrence same", int(office_rec["same_location_users"]), 6)
    add("05 OFFICE fixed-vs-recurrence overlap", int(office_rec["both_users"]), 25)

    home_hold = _fixed_holdout(frames, "HOME")
    office_hold = _fixed_holdout(frames, "OFFICE")
    add("05 HOME heldout top1", float(home_hold["heldout_top1_share"]), 0.50)
    add("05 OFFICE heldout top1", float(office_hold["heldout_top1_share"]), 0.42105263157894735)

    home_drop = _fixed_dropout30(frames, "HOME")
    office_drop = _fixed_dropout30(frames, "OFFICE")
    add("05 HOME dropout30", float(home_drop["candidate_retention"]), 0.8166666666666667)
    add("05 OFFICE dropout30", float(office_drop["candidate_retention"]), 0.7888888888888889)

    gate = frames["07i_office_gate"]
    dates = pd.to_numeric(gate["office_min_dates"], errors="coerce")
    share = pd.to_numeric(gate["office_min_share"], errors="coerce")
    margin = pd.to_numeric(gate["office_min_margin"], errors="coerce")
    base = _one(
        gate,
        dates.eq(3) & np.isclose(share, 0.30) & np.isclose(margin, 0.10),
        "07i frozen OFFICE gate",
    )
    margin_relax = _one(
        gate,
        dates.eq(3) & np.isclose(share, 0.30) & np.isclose(margin, 0.05),
        "07i margin relaxation",
    )
    share_relax = _one(
        gate,
        dates.eq(3) & np.isclose(share, 0.20) & np.isclose(margin, 0.10),
        "07i share relaxation",
    )
    add("07i baseline OFFICE", int(base["emitted_users"]), 16)
    add("07i margin-relax OFFICE", int(margin_relax["emitted_users"]), 18)
    add("07i share-relax OFFICE", int(share_relax["emitted_users"]), 23)

    behavior = frames["07j_behavior"]
    margin_near = _one(
        behavior, behavior["audit_group"].astype(str).eq("margin_near"), "07j margin_near"
    )
    share_near = _one(
        behavior, behavior["audit_group"].astype(str).eq("share_near"), "07j share_near"
    )
    add("07j margin users", int(margin_near["users"]), 2)
    add("07j share users", int(share_near["users"]), 7)
    add("07j margin both splits", int(margin_near["both_split_tests_match_users"]), 0)
    add("07j share both splits", int(share_near["both_split_tests_match_users"]), 1)
    add("07j margin heldout top1", int(margin_near["holdout_full_candidate_top1_users"]), 0)
    add("07j share heldout top1", int(share_near["holdout_full_candidate_top1_users"]), 2)

    policy = frames["07l_policy"].iloc[0]
    add("07l near-miss users", int(policy["near_miss_users"]), 9)
    add("07l office-like imagery", int(policy["office_like_imagery_users"]), 1)
    add("07l institutional imagery", int(policy["institutional_daytime_imagery_users"]), 3)
    add("07l both split tests", int(policy["both_split_tests_users"]), 1)
    add("07l heldout top1", int(policy["heldout_top1_users"]), 2)
    add("07l BCL work context 150m", int(policy["bcl_work_context_150m_users"]), 0)

    m = frames["07m_agreement"]
    m_home = _one(
        m,
        m["method"].astype(str).eq("OSNA") & m["label"].astype(str).eq("HOME"),
        "07m OSNA HOME",
    )
    m_office = _one(
        m,
        m["method"].astype(str).eq("OSNA") & m["label"].astype(str).eq("OFFICE"),
        "07m OSNA OFFICE",
    )
    add("07m OSNA HOME exact", int(m_home["exact_location_match_users"]), 27)
    add("07m OSNA OFFICE exact", int(m_office["exact_location_match_users"]), 11)

    nstay = frames["07n_stay"]
    cp1 = _one(
        nstay, nstay["source_inventory"].astype(str).eq("CP1"), "07n CP1 stay match"
    )
    ti = _one(
        nstay, nstay["source_inventory"].astype(str).eq("TRACKINTEL"), "07n TI stay match"
    )
    add("07n CP1 strong-match rate", float(cp1["strong_match_rate"]), 2125 / 5821)
    add("07n TI strong-match rate", float(ti["strong_match_rate"]), 2088 / 2157)

    nsem = frames["07n_semantic"]
    n_home = _one(
        nsem,
        nsem["variant"].astype(str).eq("dbscan200")
        & nsem["label"].astype(str).eq("HOME"),
        "07n dbscan200 HOME",
    )
    n_office = _one(
        nsem,
        nsem["variant"].astype(str).eq("dbscan200")
        & nsem["label"].astype(str).eq("OFFICE"),
        "07n dbscan200 OFFICE",
    )
    add("07n HOME within200", int(n_home["within_200m"]), 21)
    add("07n OFFICE within200", int(n_office["within_200m"]), 9)

    suite = frames["07o_suite"]
    sk = _one(
        suite,
        suite["comparator"].astype(str).eq("SCIKIT_MOBILITY_1_3_1_HOME")
        & suite["label"].astype(str).eq("HOME"),
        "07o scikit HOME",
    )
    sc_home = _one(
        suite,
        suite["comparator"].astype(str).eq("SCITEPRESS_WORK_REST_STYLE")
        & suite["label"].astype(str).eq("HOME"),
        "07o SCITEPRESS HOME",
    )
    sc_office = _one(
        suite,
        suite["comparator"].astype(str).eq("SCITEPRESS_WORK_REST_STYLE")
        & suite["label"].astype(str).eq("OFFICE"),
        "07o SCITEPRESS OFFICE",
    )
    gh = _one(
        suite,
        suite["comparator"].astype(str).eq("ARXIV2302_GEOHASH_STAY_HOUR"),
        "07o geohash HOME",
    )
    add("07o scikit HOME agreement", int(sk["agreement_count"]), 26)
    add("07o SCITEPRESS HOME agreement", int(sc_home["agreement_count"]), 25)
    add("07o SCITEPRESS OFFICE agreement", int(sc_office["agreement_count"]), 15)
    add("07o geohash HOME within200", int(gh["agreement_count"]), 20)

    result = pd.DataFrame(checks)
    if not result["passed"].all():
        failed = result.loc[~result["passed"]]
        raise AssertionError(
            "Stage 07p measured-lineage validation failed:\n"
            + failed.to_string(index=False)
        )
    return result


def build_home_evidence_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    fixed_rec = _fixed_cross_method(frames, "HOME", "recurrence")
    fixed_howde = _fixed_cross_method(frames, "HOME", "howde_style")
    hold = _fixed_holdout(frames, "HOME")
    drop = _fixed_dropout30(frames, "HOME")

    m = frames["07m_agreement"]
    osna = _one(
        m,
        m["method"].astype(str).eq("OSNA") & m["label"].astype(str).eq("HOME"),
        "07m OSNA HOME",
    )

    n = frames["07n_semantic"]
    n200 = _one(
        n,
        n["variant"].astype(str).eq("dbscan200") & n["label"].astype(str).eq("HOME"),
        "07n dbscan200 HOME",
    )

    suite = frames["07o_suite"]
    sk = _one(
        suite, suite["comparator"].astype(str).eq("SCIKIT_MOBILITY_1_3_1_HOME"), "07o scikit"
    )
    gh = _one(
        suite, suite["comparator"].astype(str).eq("ARXIV2302_GEOHASH_STAY_HOUR"), "07o geohash"
    )
    sc = _one(
        suite,
        suite["comparator"].astype(str).eq("SCITEPRESS_WORK_REST_STYLE")
        & suite["label"].astype(str).eq("HOME"),
        "07o SCITEPRESS HOME",
    )

    rows = [
        ("internal cross-method", "05", "fixed vs HoWDe exact", int(fixed_howde["same_location_users"]), int(fixed_howde["both_users"]), "supports"),
        ("internal cross-method", "05", "fixed vs recurrence exact", int(fixed_rec["same_location_users"]), int(fixed_rec["both_users"]), "supports"),
        ("internal persistence", "05", "fixed heldout top-1", float(hold["heldout_top1_share"]), np.nan, "mixed"),
        ("internal perturbation", "05", "fixed 30% dropout retention", float(drop["candidate_retention"]), np.nan, "supports"),
        ("external implementation", "07m", "Trackintel OSNA exact vs HOME-27", int(osna["exact_location_match_users"]), 27, "strong_support"),
        ("end-to-end implementation", "07n", "Trackintel DBSCAN200+OSNA within 200m", int(n200["within_200m"]), 27, "supports"),
        ("literature comparator", "07o", "scikit-mobility-style exact", int(sk["agreement_count"]), 27, "strong_support"),
        ("literature comparator", "07o", "geohash adaptation within 200m", int(gh["agreement_count"]), 27, "conditional_support"),
        ("literature comparator", "07o", "SCITEPRESS-style exact", int(sc["agreement_count"]), 27, "strong_support"),
    ]
    return pd.DataFrame(
        rows,
        columns=["evidence_family", "stage", "metric", "value", "denominator", "interpretation"],
    )


def build_office_evidence_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    fixed_howde = _fixed_cross_method(frames, "OFFICE", "howde_style")
    fixed_rec = _fixed_cross_method(frames, "OFFICE", "recurrence")
    hold = _fixed_holdout(frames, "OFFICE")
    drop = _fixed_dropout30(frames, "OFFICE")

    m = frames["07m_agreement"]
    osna = _one(
        m,
        m["method"].astype(str).eq("OSNA") & m["label"].astype(str).eq("OFFICE"),
        "07m OSNA OFFICE",
    )

    n = frames["07n_semantic"]
    n200 = _one(
        n,
        n["variant"].astype(str).eq("dbscan200") & n["label"].astype(str).eq("OFFICE"),
        "07n dbscan200 OFFICE",
    )

    suite = frames["07o_suite"]
    sc = _one(
        suite,
        suite["comparator"].astype(str).eq("SCITEPRESS_WORK_REST_STYLE")
        & suite["label"].astype(str).eq("OFFICE"),
        "07o SCITEPRESS OFFICE",
    )

    rows = [
        ("internal cross-method", "05", "fixed vs HoWDe exact", int(fixed_howde["same_location_users"]), int(fixed_howde["both_users"]), "supports"),
        ("internal cross-method", "05", "fixed vs recurrence exact", int(fixed_rec["same_location_users"]), int(fixed_rec["both_users"]), "weak"),
        ("internal persistence", "05", "fixed heldout top-1", float(hold["heldout_top1_share"]), np.nan, "mixed"),
        ("internal perturbation", "05", "fixed 30% dropout retention", float(drop["candidate_retention"]), np.nan, "supports"),
        ("external implementation", "07m", "Trackintel OSNA exact vs OFFICE-16", int(osna["exact_location_match_users"]), 16, "supports"),
        ("end-to-end implementation", "07n", "Trackintel DBSCAN200+OSNA within 200m", int(n200["within_200m"]), 16, "mixed"),
        ("literature comparator", "07o", "SCITEPRESS-style exact", int(sc["agreement_count"]), 16, "supports_but_overselects"),
    ]
    return pd.DataFrame(
        rows,
        columns=["evidence_family", "stage", "metric", "value", "denominator", "interpretation"],
    )


def build_near_miss_policy_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    behavior = frames["07j_behavior"]
    bcl = frames["07j_bcl"]
    rows = []

    for group in ("margin_near", "share_near"):
        b = _one(behavior, behavior["audit_group"].astype(str).eq(group), f"07j {group}")
        c = _one(bcl, bcl["audit_group"].astype(str).eq(group), f"07j BCL {group}")
        rows.append(
            {
                "audit_group": group,
                "users": int(b["users"]),
                "howde_exact": int(b["howde_match_users"]),
                "recurrence_exact": int(b["recurrence_match_users"]),
                "both_split_tests": int(b["both_split_tests_match_users"]),
                "heldout_top1": int(b["holdout_full_candidate_top1_users"]),
                "median_dropout_retention": float(b["median_dropout_retention"]),
                "bcl_evaluable": int(c["bcl_evaluable_users"]),
                "bcl_work_context_150m": int(c["work_compatible_lexical_150m_users"]),
            }
        )

    policy = frames["07l_policy"].iloc[0]
    rows.append(
        {
            "audit_group": "all_near_miss_imagery_snapshot",
            "users": int(policy["near_miss_users"]),
            "howde_exact": np.nan,
            "recurrence_exact": np.nan,
            "both_split_tests": int(policy["both_split_tests_users"]),
            "heldout_top1": int(policy["heldout_top1_users"]),
            "median_dropout_retention": np.nan,
            "bcl_evaluable": int(policy["bcl_evaluable_users"]),
            "bcl_work_context_150m": int(policy["bcl_work_context_150m_users"]),
        }
    )
    return pd.DataFrame(rows)


def build_pipeline_sensitivity_summary(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    stay = frames["07n_stay"]
    loc = frames["07n_location"]
    sem = frames["07n_semantic"]

    cp1 = _one(stay, stay["source_inventory"].astype(str).eq("CP1"), "07n CP1")
    ti = _one(stay, stay["source_inventory"].astype(str).eq("TRACKINTEL"), "07n TI")

    loc100 = _one(
        loc,
        loc["variant"].astype(str).eq("dbscan100")
        & loc["scope"].astype(str).eq("recurring_production_locations"),
        "07n DBSCAN100 recurring",
    )
    loc200 = _one(
        loc,
        loc["variant"].astype(str).eq("dbscan200")
        & loc["scope"].astype(str).eq("recurring_production_locations"),
        "07n DBSCAN200 recurring",
    )

    h200 = _one(
        sem,
        sem["variant"].astype(str).eq("dbscan200")
        & sem["label"].astype(str).eq("HOME"),
        "07n DBSCAN200 HOME",
    )
    o200 = _one(
        sem,
        sem["variant"].astype(str).eq("dbscan200")
        & sem["label"].astype(str).eq("OFFICE"),
        "07n DBSCAN200 OFFICE",
    )

    return pd.DataFrame(
        [
            {"layer": "stay extraction", "metric": "CP1 -> Trackintel strong-match rate", "value": float(cp1["strong_match_rate"]), "interpretation": "major upstream divergence"},
            {"layer": "stay extraction", "metric": "Trackintel -> CP1 strong-match rate", "value": float(ti["strong_match_rate"]), "interpretation": "Trackintel approximately subset of CP1"},
            {"layer": "location geometry", "metric": "DBSCAN100 recurring anchors within 200m", "value": float(loc100["within_200m"]) / float(loc100["production_locations"]), "interpretation": "substantial spatial correspondence"},
            {"layer": "location geometry", "metric": "DBSCAN200 recurring anchors within 200m", "value": float(loc200["within_200m"]) / float(loc200["production_locations"]), "interpretation": "substantial spatial correspondence"},
            {"layer": "semantic candidate", "metric": "DBSCAN200 HOME within 200m / HOME-27", "value": float(h200["within_200m"]) / 27.0, "interpretation": "HOME comparatively robust"},
            {"layer": "semantic candidate", "metric": "DBSCAN200 OFFICE within 200m / OFFICE-16", "value": float(o200["within_200m"]) / 16.0, "interpretation": "OFFICE more representation-sensitive"},
        ]
    )


def build_final_policy_snapshot(frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    gate = frames["07i_office_gate"]
    dates = pd.to_numeric(gate["office_min_dates"], errors="coerce")
    share = pd.to_numeric(gate["office_min_share"], errors="coerce")
    margin = pd.to_numeric(gate["office_min_margin"], errors="coerce")

    margin_relax = _one(
        gate,
        dates.eq(3) & np.isclose(share, 0.30) & np.isclose(margin, 0.05),
        "07i margin relaxation",
    )
    share_relax = _one(
        gate,
        dates.eq(3) & np.isclose(share, 0.20) & np.isclose(margin, 0.10),
        "07i share relaxation",
    )

    policy = frames["07l_policy"].iloc[0]

    return pd.DataFrame(
        [
            {
                "production_HOME": 27,
                "production_OFFICE": 16,
                "office_margin_relax_extra_users": int(margin_relax["new_vs_baseline_emitted"]),
                "office_share_relax_extra_users": int(share_relax["new_vs_baseline_emitted"]),
                "near_miss_users_audited": int(policy["near_miss_users"]),
                "near_miss_both_split_tests": int(policy["both_split_tests_users"]),
                "near_miss_heldout_top1": int(policy["heldout_top1_users"]),
                "near_miss_bcl_work_context_150m": int(policy["bcl_work_context_150m_users"]),
                "change_home_gate": False,
                "change_office_gate": False,
                "promote_near_miss": False,
                "final_policy": "freeze_HOME_27_OFFICE_16",
            }
        ]
    )


def build_claim_boundary() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "claim_type": "supported",
                "claim": "HOME candidate identity is strongly convergent across internal and external heuristic families.",
            },
            {
                "claim_type": "supported",
                "claim": "OFFICE is more method- and representation-sensitive than HOME and benefits from explicit abstention.",
            },
            {
                "claim_type": "supported",
                "claim": "The frozen OFFICE gate is conservative in coverage, but one-step relaxations lack sufficient robustness/context evidence for global promotion.",
            },
            {
                "claim_type": "supported",
                "claim": "Trackintel end-to-end disagreement is driven substantially by upstream stay-inventory construction, not semantic selection alone.",
            },
            {
                "claim_type": "supported",
                "claim": "Several share-near OFFICE candidates are temporally plausible under multiple external heuristics but remain insufficiently robust for production.",
            },
            {
                "claim_type": "not_supported",
                "claim": "HOME/OFFICE semantic accuracy is known from GeoLife ground truth.",
            },
            {
                "claim_type": "not_supported",
                "claim": "A POI/context match proves employment or workplace function.",
            },
            {
                "claim_type": "not_supported",
                "claim": "Trackintel, scikit-mobility, geohash, or SCITEPRESS outputs are ground truth.",
            },
            {
                "claim_type": "not_supported",
                "claim": "The nine OFFICE near-miss candidates should be promoted because external heuristics often select them.",
            },
        ]
    )


def synthetic_self_check() -> dict[str, object]:
    policy = build_claim_boundary()
    assert set(policy["claim_type"]) == {"supported", "not_supported"}
    assert len(policy) >= 8
    return {"status": "ok", "claim_rows": int(len(policy))}
