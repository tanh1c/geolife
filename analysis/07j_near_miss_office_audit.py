"""Stage 07j: targeted near-miss OFFICE audit.

Stage 07i showed that the frozen OFFICE gate is conservative in coverage:
- baseline 3 dates / .30 share / .10 margin -> 16 users;
- one-step margin relaxation (.10 -> .05) -> 18 users;
- one-step share relaxation (.30 -> .20) -> 23 users.

This stage audits ONLY the newly emitted users from those two one-step
relaxations and compares them with the frozen baseline OFFICE cohort.

No production gate is changed here and no new semantic score is created.
The audit reuses already-defined Stage-05 reliability stress tests plus
BCL-primary historical POI context.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


BASELINE_GATE = (3, 0.30, 0.10)
MARGIN_RELAX_GATE = (3, 0.30, 0.05)
SHARE_RELAX_GATE = (3, 0.20, 0.10)

METHOD_FIXED = "fixed_window"
METHOD_HOWDE = "howde_style"
METHOD_RECURRENCE = "recurrence"


def _normalize_user(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    if "user_id" not in out.columns:
        raise ValueError("frame missing user_id")
    out["user_id"] = out["user_id"].astype(str)
    return out


def _gate_mask(
    frame: pd.DataFrame,
    gate: tuple[int, float, float],
) -> pd.Series:
    dates, share, margin = gate
    return (
        pd.to_numeric(frame["office_min_dates"], errors="coerce").eq(dates)
        & np.isclose(
            pd.to_numeric(frame["office_min_share"], errors="coerce"),
            share,
        )
        & np.isclose(
            pd.to_numeric(frame["office_min_margin"], errors="coerce"),
            margin,
        )
    )


def build_audit_cohort(
    office_emitted_details: pd.DataFrame,
) -> pd.DataFrame:
    """Build frozen baseline + two one-step near-miss cohorts.

    Because all three configs use min_dates=3, share/margin changes do not
    alter candidate ranking. Candidate identity should therefore match the
    full-period fixed-window candidate from Stage 05.
    """
    details = _normalize_user(office_emitted_details)
    required = {
        "location_id",
        "support_days",
        "score",
        "office_min_dates",
        "office_min_share",
        "office_min_margin",
    }
    missing = required.difference(details.columns)
    if missing:
        raise ValueError(
            f"office sensitivity details missing columns: {sorted(missing)}"
        )

    groups = {}
    for name, gate in (
        ("baseline", BASELINE_GATE),
        ("margin_near", MARGIN_RELAX_GATE),
        ("share_near", SHARE_RELAX_GATE),
    ):
        subset = details.loc[_gate_mask(details, gate)].copy()
        subset["location_id"] = pd.to_numeric(
            subset["location_id"], errors="raise"
        ).astype(int)
        if subset["user_id"].duplicated().any():
            raise ValueError(f"duplicate emitted OFFICE users in {name}")
        groups[name] = subset

    baseline_users = set(groups["baseline"]["user_id"])
    margin_new = groups["margin_near"].loc[
        ~groups["margin_near"]["user_id"].isin(baseline_users)
    ].copy()
    share_new = groups["share_near"].loc[
        ~groups["share_near"]["user_id"].isin(baseline_users)
    ].copy()

    overlap = set(margin_new["user_id"]).intersection(share_new["user_id"])
    if overlap:
        raise ValueError(
            "one-step margin/share near-miss cohorts unexpectedly overlap: "
            f"{sorted(overlap)}"
        )

    parts = []
    for name, subset in (
        ("baseline", groups["baseline"]),
        ("margin_near", margin_new),
        ("share_near", share_new),
    ):
        keep = subset[
            ["user_id", "location_id", "support_days", "score"]
        ].copy()
        keep = keep.rename(
            columns={
                "location_id": "candidate_location_id",
                "support_days": "full_support_days",
                "score": "full_office_share",
            }
        )
        keep["audit_group"] = name
        parts.append(keep)

    cohort = pd.concat(parts, ignore_index=True)
    cohort["candidate_location_id"] = pd.to_numeric(
        cohort["candidate_location_id"], errors="raise"
    ).astype(int)
    cohort["full_support_days"] = pd.to_numeric(
        cohort["full_support_days"], errors="coerce"
    )
    cohort["full_office_share"] = pd.to_numeric(
        cohort["full_office_share"], errors="coerce"
    )
    return cohort.sort_values(
        ["audit_group", "user_id"], kind="stable"
    ).reset_index(drop=True)


def cohort_counts(cohort: pd.DataFrame) -> pd.DataFrame:
    order = ["baseline", "margin_near", "share_near"]
    counts = (
        cohort.groupby("audit_group", as_index=False)
        .agg(users=("user_id", "nunique"))
    )
    counts["audit_group"] = pd.Categorical(
        counts["audit_group"], categories=order, ordered=True
    )
    return counts.sort_values("audit_group").reset_index(drop=True)


def attach_static_method_evidence(
    cohort: pd.DataFrame,
    assignments: pd.DataFrame,
) -> pd.DataFrame:
    """Attach production HOME collision and OFFICE comparator identities."""
    panel = _normalize_user(cohort)
    source = _normalize_user(assignments)

    office = source.loc[source["label"].eq("OFFICE")].copy()
    pivot = (
        office.pivot_table(
            index="user_id",
            columns="method",
            values="location_id",
            aggfunc="first",
        )
        .rename(
            columns={
                METHOD_FIXED: "fixed_office_location_id",
                METHOD_HOWDE: "howde_office_location_id",
                METHOD_RECURRENCE: "recurrence_office_location_id",
            }
        )
        .reset_index()
    )
    panel = panel.merge(
        pivot,
        on="user_id",
        how="left",
        validate="one_to_one",
    )

    fixed = pd.to_numeric(
        panel["fixed_office_location_id"], errors="coerce"
    )
    mismatch = fixed.notna() & fixed.astype("Int64").ne(
        panel["candidate_location_id"].astype("Int64")
    )
    if mismatch.any():
        sample = panel.loc[
            mismatch,
            ["user_id", "candidate_location_id", "fixed_office_location_id"],
        ].head(5)
        raise ValueError(
            "near-miss candidate does not match frozen full-period fixed "
            f"candidate: {sample.to_dict(orient='records')}"
        )

    for method in ("howde", "recurrence"):
        column = f"{method}_office_location_id"
        values = pd.to_numeric(panel[column], errors="coerce")
        panel[f"{method}_available"] = values.notna()
        panel[f"{method}_matches_candidate"] = (
            values.astype("Int64").eq(
                panel["candidate_location_id"].astype("Int64")
            )
            & values.notna()
        )

    panel["static_comparator_match_count"] = (
        panel["howde_matches_candidate"].astype(int)
        + panel["recurrence_matches_candidate"].astype(int)
    )

    home = source.loc[
        source["label"].eq("HOME")
        & source["method"].eq(METHOD_FIXED)
        & source["emitted"].fillna(False).astype(bool),
        ["user_id", "location_id"],
    ].copy()
    home = home.rename(
        columns={"location_id": "production_home_location_id"}
    )
    if home["user_id"].duplicated().any():
        raise ValueError("production HOME must be one row per user")
    panel = panel.merge(home, on="user_id", how="left", validate="one_to_one")
    home_id = pd.to_numeric(
        panel["production_home_location_id"], errors="coerce"
    )
    panel["production_home_available"] = home_id.notna()
    panel["candidate_equals_production_home"] = (
        home_id.astype("Int64").eq(
            panel["candidate_location_id"].astype("Int64")
        )
        & home_id.notna()
    )
    return panel


def attach_split_half_evidence(
    panel: pd.DataFrame,
    split_details: pd.DataFrame,
) -> pd.DataFrame:
    out = _normalize_user(panel)
    details = _normalize_user(split_details)
    details = details.loc[
        details["method"].eq(METHOD_FIXED)
        & details["label"].eq("OFFICE")
    ].copy()

    for split in ("first_second", "odd_even"):
        subset = details.loc[details["split"].eq(split)].copy()
        if subset["user_id"].duplicated().any():
            raise ValueError(f"duplicate fixed OFFICE rows for split={split}")
        subset = subset[
            ["user_id", "location_id_left", "location_id_right"]
        ].rename(
            columns={
                "location_id_left": f"{split}_left_location_id",
                "location_id_right": f"{split}_right_location_id",
            }
        )
        out = out.merge(
            subset,
            on="user_id",
            how="left",
            validate="one_to_one",
        )
        left = pd.to_numeric(
            out[f"{split}_left_location_id"], errors="coerce"
        )
        right = pd.to_numeric(
            out[f"{split}_right_location_id"], errors="coerce"
        )
        candidate = out["candidate_location_id"].astype("Int64")
        out[f"{split}_both_halves_available"] = (
            left.notna() & right.notna()
        )
        out[f"{split}_left_matches_candidate"] = (
            left.astype("Int64").eq(candidate) & left.notna()
        )
        out[f"{split}_right_matches_candidate"] = (
            right.astype("Int64").eq(candidate) & right.notna()
        )
        out[f"{split}_both_match_candidate"] = (
            out[f"{split}_left_matches_candidate"]
            & out[f"{split}_right_matches_candidate"]
        )

    out["split_full_candidate_match_count"] = (
        out["first_second_both_match_candidate"].astype(int)
        + out["odd_even_both_match_candidate"].astype(int)
    )
    return out


def attach_holdout_evidence(
    panel: pd.DataFrame,
    holdout_details: pd.DataFrame,
) -> pd.DataFrame:
    out = _normalize_user(panel)
    details = _normalize_user(holdout_details)
    details = details.loc[
        details["method"].eq(METHOD_FIXED)
        & details["label"].eq("OFFICE")
    ].copy()
    if details["user_id"].duplicated().any():
        raise ValueError("duplicate fixed OFFICE holdout rows")

    columns = [
        "user_id",
        "location_id",
        "seen_in_holdout",
        "heldout_metric",
        "heldout_rank",
        "heldout_top1",
    ]
    details = details[columns].rename(
        columns={
            "location_id": "holdout_train_location_id",
            "seen_in_holdout": "candidate_seen_in_holdout",
            "heldout_metric": "heldout_weekday_day_share",
            "heldout_rank": "heldout_office_rank",
            "heldout_top1": "holdout_train_candidate_top1",
        }
    )
    out = out.merge(details, on="user_id", how="left", validate="one_to_one")

    train_id = pd.to_numeric(
        out["holdout_train_location_id"], errors="coerce"
    )
    out["holdout_train_candidate_available"] = train_id.notna()
    out["holdout_train_matches_full_candidate"] = (
        train_id.astype("Int64").eq(
            out["candidate_location_id"].astype("Int64")
        )
        & train_id.notna()
    )
    out["full_candidate_heldout_top1"] = (
        out["holdout_train_matches_full_candidate"]
        & out["holdout_train_candidate_top1"].fillna(False).astype(bool)
    )
    return out


def attach_dropout_evidence(
    panel: pd.DataFrame,
    dropout_details: pd.DataFrame,
) -> pd.DataFrame:
    out = _normalize_user(panel)
    details = _normalize_user(dropout_details)
    details = details.loc[
        details["method"].eq(METHOD_FIXED)
        & details["label"].eq("OFFICE")
    ].copy()

    reference = pd.to_numeric(
        details["location_id_reference"], errors="coerce"
    )
    candidate_map = dict(
        zip(out["user_id"], out["candidate_location_id"].astype(int))
    )
    details["_candidate_id"] = details["user_id"].map(candidate_map)
    valid = details["_candidate_id"].notna()
    mismatch = (
        valid
        & reference.notna()
        & reference.astype("Int64").ne(
            details["_candidate_id"].astype("Int64")
        )
    )
    if mismatch.any():
        raise ValueError(
            "dropout reference fixed candidate differs from audit candidate"
        )

    details = details.loc[valid].copy()
    details["candidate_retained"] = (
        details["candidate_retained"].fillna(False).astype(bool)
    )
    all_summary = (
        details.groupby("user_id", as_index=False)
        .agg(
            dropout_trials=("candidate_retained", "size"),
            dropout_candidate_retention=("candidate_retained", "mean"),
        )
    )
    out = out.merge(all_summary, on="user_id", how="left", validate="one_to_one")

    for rate in (0.10, 0.20, 0.30):
        subset = details.loc[
            np.isclose(
                pd.to_numeric(details["dropout_rate"], errors="coerce"),
                rate,
            )
        ]
        summary = (
            subset.groupby("user_id", as_index=False)
            .agg(retention=("candidate_retained", "mean"))
            .rename(
                columns={
                    "retention": f"dropout_retention_{int(rate*100)}pct"
                }
            )
        )
        out = out.merge(summary, on="user_id", how="left", validate="one_to_one")
    return out


def attach_time_shift_diagnostic(
    panel: pd.DataFrame,
    shift_details: pd.DataFrame,
) -> pd.DataFrame:
    """Attach 12h shift as a falsification diagnostic, not positive support."""
    out = _normalize_user(panel)
    details = _normalize_user(shift_details)
    details = details.loc[
        details["method"].eq(METHOD_FIXED)
        & details["label"].eq("OFFICE")
    ].copy()
    if details["user_id"].duplicated().any():
        raise ValueError("duplicate fixed OFFICE shift rows")
    details = details[
        ["user_id", "location_id_reference", "location_id_shifted"]
    ].rename(
        columns={
            "location_id_reference": "shift_reference_location_id",
            "location_id_shifted": "shifted_12h_location_id",
        }
    )
    out = out.merge(details, on="user_id", how="left", validate="one_to_one")
    ref = pd.to_numeric(out["shift_reference_location_id"], errors="coerce")
    mismatch = (
        ref.notna()
        & ref.astype("Int64").ne(
            out["candidate_location_id"].astype("Int64")
        )
    )
    if mismatch.any():
        raise ValueError("12h-shift reference differs from audit candidate")
    shifted = pd.to_numeric(out["shifted_12h_location_id"], errors="coerce")
    out["candidate_retained_after_12h_shift"] = (
        shifted.astype("Int64").eq(
            out["candidate_location_id"].astype("Int64")
        )
        & shifted.notna()
    )
    return out


def attach_bcl_context(
    panel: pd.DataFrame,
    bcl_metrics: pd.DataFrame,
) -> pd.DataFrame:
    out = _normalize_user(panel)
    metrics = _normalize_user(bcl_metrics)
    metrics["location_id"] = pd.to_numeric(
        metrics["location_id"], errors="raise"
    ).astype(int)

    wanted = [
        "user_id",
        "location_id",
        "work_compatible_lexical_within_100m",
        "business_name_within_100m",
        "education_within_100m",
        "retail_service_within_100m",
        "work_compatible_lexical_within_150m",
        "business_name_within_150m",
        "education_within_150m",
        "retail_service_within_150m",
    ]
    missing = set(wanted).difference(metrics.columns)
    if missing:
        raise ValueError(f"BCL metrics missing columns: {sorted(missing)}")

    lookup = metrics[wanted].rename(
        columns={"location_id": "candidate_location_id"}
    )
    if lookup.duplicated(["user_id", "candidate_location_id"]).any():
        raise ValueError("BCL candidate lookup must be unique")

    out = out.merge(
        lookup,
        on=["user_id", "candidate_location_id"],
        how="left",
        validate="one_to_one",
        indicator="_bcl_merge",
    )
    out["bcl_evaluable"] = out["_bcl_merge"].eq("both")
    out = out.drop(columns="_bcl_merge")
    return out


def build_near_miss_audit_panel(
    office_emitted_details: pd.DataFrame,
    assignments: pd.DataFrame,
    split_details: pd.DataFrame,
    holdout_details: pd.DataFrame,
    dropout_details: pd.DataFrame,
    shift_details: pd.DataFrame,
    bcl_metrics: pd.DataFrame,
) -> pd.DataFrame:
    panel = build_audit_cohort(office_emitted_details)
    panel = attach_static_method_evidence(panel, assignments)
    panel = attach_split_half_evidence(panel, split_details)
    panel = attach_holdout_evidence(panel, holdout_details)
    panel = attach_dropout_evidence(panel, dropout_details)
    panel = attach_time_shift_diagnostic(panel, shift_details)
    panel = attach_bcl_context(panel, bcl_metrics)
    return panel


def summarize_behavioral_robustness(panel: pd.DataFrame) -> pd.DataFrame:
    """Aggregate source-native reliability metrics by audit group."""
    rows = []
    for group, subset in panel.groupby("audit_group", sort=False):
        rows.append(
            {
                "audit_group": str(group),
                "users": int(len(subset)),
                "home_collision_users": int(
                    subset["candidate_equals_production_home"].fillna(False).sum()
                ),
                "howde_match_users": int(
                    subset["howde_matches_candidate"].fillna(False).sum()
                ),
                "recurrence_match_users": int(
                    subset["recurrence_matches_candidate"].fillna(False).sum()
                ),
                "both_static_comparators_match_users": int(
                    subset["static_comparator_match_count"].eq(2).sum()
                ),
                "first_second_both_match_users": int(
                    subset["first_second_both_match_candidate"].fillna(False).sum()
                ),
                "odd_even_both_match_users": int(
                    subset["odd_even_both_match_candidate"].fillna(False).sum()
                ),
                "both_split_tests_match_users": int(
                    subset["split_full_candidate_match_count"].eq(2).sum()
                ),
                "holdout_full_candidate_top1_users": int(
                    subset["full_candidate_heldout_top1"].fillna(False).sum()
                ),
                "median_dropout_retention": float(
                    pd.to_numeric(
                        subset["dropout_candidate_retention"], errors="coerce"
                    ).median()
                ),
                "mean_dropout_retention": float(
                    pd.to_numeric(
                        subset["dropout_candidate_retention"], errors="coerce"
                    ).mean()
                ),
                "candidate_retained_after_12h_shift_users": int(
                    subset["candidate_retained_after_12h_shift"].fillna(False).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_bcl_context(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for group, subset in panel.groupby("audit_group", sort=False):
        evaluable = subset.loc[subset["bcl_evaluable"].fillna(False)].copy()
        row = {
            "audit_group": str(group),
            "users": int(len(subset)),
            "bcl_evaluable_users": int(len(evaluable)),
        }
        for radius in (100, 150):
            for stem in (
                "work_compatible_lexical",
                "business_name",
                "education",
                "retail_service",
            ):
                column = f"{stem}_within_{radius}m"
                row[f"{stem}_{radius}m_users"] = int(
                    evaluable[column].fillna(False).sum()
                ) if not evaluable.empty else 0
        rows.append(row)
    return pd.DataFrame(rows)


def summarize_support_distribution(panel: pd.DataFrame) -> pd.DataFrame:
    return (
        panel.groupby("audit_group", as_index=False)
        .agg(
            users=("user_id", "nunique"),
            median_support_days=("full_support_days", "median"),
            min_support_days=("full_support_days", "min"),
            median_office_share=("full_office_share", "median"),
            min_office_share=("full_office_share", "min"),
            median_static_comparator_matches=(
                "static_comparator_match_count",
                "median",
            ),
            median_split_matches=("split_full_candidate_match_count", "median"),
            median_dropout_retention=(
                "dropout_candidate_retention",
                "median",
            ),
        )
    )


def private_signature_table(panel: pd.DataFrame) -> pd.DataFrame:
    """Compact private view for case review without inventing a total score."""
    columns = [
        "user_id",
        "audit_group",
        "candidate_location_id",
        "full_support_days",
        "full_office_share",
        "candidate_equals_production_home",
        "howde_matches_candidate",
        "recurrence_matches_candidate",
        "static_comparator_match_count",
        "first_second_both_match_candidate",
        "odd_even_both_match_candidate",
        "split_full_candidate_match_count",
        "holdout_train_matches_full_candidate",
        "candidate_seen_in_holdout",
        "heldout_office_rank",
        "full_candidate_heldout_top1",
        "dropout_candidate_retention",
        "dropout_retention_10pct",
        "dropout_retention_20pct",
        "dropout_retention_30pct",
        "candidate_retained_after_12h_shift",
        "bcl_evaluable",
        "work_compatible_lexical_within_100m",
        "business_name_within_100m",
        "work_compatible_lexical_within_150m",
        "business_name_within_150m",
    ]
    return panel[[column for column in columns if column in panel.columns]].copy()


def synthetic_self_check() -> dict[str, object]:
    rows = []
    for user, location, gate in (
        ("b", 1, BASELINE_GATE),
        ("m", 2, MARGIN_RELAX_GATE),
        ("s", 3, SHARE_RELAX_GATE),
    ):
        rows.append(
            {
                "user_id": user,
                "location_id": location,
                "support_days": 4,
                "score": 0.31 if user != "s" else 0.25,
                "office_min_dates": gate[0],
                "office_min_share": gate[1],
                "office_min_margin": gate[2],
            }
        )
    # Relaxed configs also contain the baseline emitted user.
    rows.extend(
        [
            {
                "user_id": "b",
                "location_id": 1,
                "support_days": 4,
                "score": 0.4,
                "office_min_dates": MARGIN_RELAX_GATE[0],
                "office_min_share": MARGIN_RELAX_GATE[1],
                "office_min_margin": MARGIN_RELAX_GATE[2],
            },
            {
                "user_id": "b",
                "location_id": 1,
                "support_days": 4,
                "score": 0.4,
                "office_min_dates": SHARE_RELAX_GATE[0],
                "office_min_share": SHARE_RELAX_GATE[1],
                "office_min_margin": SHARE_RELAX_GATE[2],
            },
        ]
    )
    cohort = build_audit_cohort(pd.DataFrame(rows))
    counts = dict(zip(cohort["audit_group"], cohort["user_id"]))
    assert set(cohort["audit_group"]) == {
        "baseline",
        "margin_near",
        "share_near",
    }
    assert len(cohort) == 3
    return {"status": "ok", "rows": len(cohort), "groups": len(counts)}
