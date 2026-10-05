"""Stage 07l: unblind historical-imagery review and synthesize near-miss OFFICE evidence.

Inputs:
- completed blinded Stage-07k review CSV (9 near-miss candidates);
- Stage-07k private unblinding key;
- Stage-07j private audit panel.

This stage does not create a composite OFFICE score and does not promote users.
It joins existing evidence families and reports transparent cross-tabs/signatures.
"""

from __future__ import annotations

from pathlib import Path
import importlib.util
import sys
import numpy as np
import pandas as pd


OFFICE_LIKE_CLASSES = {
    "large_office_commercial_like_complex",
}

INSTITUTIONAL_DAYTIME_CLASSES = {
    "education_campus",
    "healthcare_institutional",
    "industrial_warehouse",
}

CONTRADICTORY_CLASSES = {
    "residential_compound",
    "transport_infrastructure",
    "construction_vacant",
    "recreation_green_space",
}

INDETERMINATE_CLASSES = {
    "mixed_urban_block",
    "other_visible_structure",
    "ambiguous",
}


def _load_07k():
    path = Path(__file__).with_name("07k_historical_imagery_review.py")
    spec = importlib.util.spec_from_file_location("stage07k_for_07l", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load Stage 07k helper")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STAGE07K = _load_07k()


def classify_visual_bucket(value: object) -> str:
    label = str(value).strip()
    if label in OFFICE_LIKE_CLASSES:
        return "office_like"
    if label in INSTITUTIONAL_DAYTIME_CLASSES:
        return "institutional_or_daytime_compatible"
    if label in CONTRADICTORY_CLASSES:
        return "office_contradictory_context"
    if label in INDETERMINATE_CLASSES:
        return "indeterminate"
    if label == "":
        return "missing"
    raise ValueError(f"unknown visual context class: {label}")


def validate_review_file(review: pd.DataFrame) -> pd.DataFrame:
    checked = STAGE07K.validate_completed_review(review)
    if checked["audit_id"].duplicated().any():
        raise ValueError("review audit_id must be unique")
    expected = 9
    if len(checked) != expected:
        raise ValueError(f"expected {expected} reviewed near-miss rows, got {len(checked)}")
    missing_class = checked["visual_context_class"].astype(str).str.strip().eq("")
    if missing_class.any():
        raise ValueError("all 9 near-miss rows require visual_context_class")
    checked = checked.copy()
    checked["visual_bucket"] = checked["visual_context_class"].map(classify_visual_bucket)
    return checked


def build_unblinded_panel(
    review: pd.DataFrame,
    unblinding_key: pd.DataFrame,
    audit_panel: pd.DataFrame,
) -> pd.DataFrame:
    review = validate_review_file(review)

    key = unblinding_key.copy()
    if key["audit_id"].duplicated().any():
        raise ValueError("unblinding key audit_id must be unique")
    near_key = key.loc[
        key["audit_group"].isin(["margin_near", "share_near"])
    ].copy()
    if len(near_key) != 9:
        raise ValueError(f"expected 9 near-miss rows in unblinding key, got {len(near_key)}")

    review_ids = set(review["audit_id"].astype(str))
    key_ids = set(near_key["audit_id"].astype(str))
    if review_ids != key_ids:
        raise ValueError(
            "review IDs do not exactly match Stage-07k near-miss IDs; "
            f"review_only={sorted(review_ids-key_ids)}, key_only={sorted(key_ids-review_ids)}"
        )

    panel = review.merge(
        near_key,
        on="audit_id",
        how="inner",
        validate="one_to_one",
    )

    audit = audit_panel.copy()
    audit["user_id"] = audit["user_id"].astype(str)
    audit = audit.loc[
        audit["audit_group"].isin(["margin_near", "share_near"])
    ].copy()
    if audit["user_id"].duplicated().any():
        raise ValueError("Stage-07j near-miss audit panel must be one row per user")

    # The unblinding key already carries a compact evidence subset; merge the
    # richer Stage-07j panel after dropping duplicate columns to avoid suffix
    # ambiguity.
    join_cols = ["user_id", "audit_group", "candidate_location_id"]
    extra_cols = [
        col for col in audit.columns
        if col not in set(panel.columns) and col not in {"audit_id"}
    ]
    panel = panel.merge(
        audit[join_cols + [c for c in extra_cols if c not in join_cols]],
        on=join_cols,
        how="left",
        validate="one_to_one",
    )
    if len(panel) != 9:
        raise ValueError("unblinded panel must contain exactly 9 near-miss users")
    return panel.sort_values("audit_id").reset_index(drop=True)


def summarize_visual_context(panel: pd.DataFrame) -> pd.DataFrame:
    out = (
        panel.groupby(
            ["audit_group", "visual_bucket", "visual_context_class"],
            as_index=False,
            dropna=False,
        )
        .agg(users=("audit_id", "nunique"))
    )
    return out.sort_values(
        ["audit_group", "visual_bucket", "visual_context_class"]
    ).reset_index(drop=True)


def summarize_behavior_by_visual_bucket(panel: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (group, bucket), subset in panel.groupby(
        ["audit_group", "visual_bucket"], sort=True
    ):
        rows.append(
            {
                "audit_group": str(group),
                "visual_bucket": str(bucket),
                "users": int(len(subset)),
                "howde_match_users": int(
                    subset["howde_matches_candidate"].fillna(False).sum()
                ),
                "recurrence_match_users": int(
                    subset["recurrence_matches_candidate"].fillna(False).sum()
                ),
                "both_split_tests_users": int(
                    pd.to_numeric(
                        subset["split_full_candidate_match_count"],
                        errors="coerce",
                    ).eq(2).sum()
                ),
                "heldout_top1_users": int(
                    subset["full_candidate_heldout_top1"].fillna(False).sum()
                ),
                "median_dropout_retention": float(
                    pd.to_numeric(
                        subset["dropout_candidate_retention"],
                        errors="coerce",
                    ).median()
                ),
                "bcl_evaluable_users": int(
                    subset["bcl_evaluable"].fillna(False).sum()
                ),
                "bcl_work_context_100m_users": int(
                    subset.get(
                        "work_compatible_lexical_within_100m",
                        pd.Series(False, index=subset.index),
                    ).fillna(False).sum()
                ),
                "bcl_business_name_100m_users": int(
                    subset.get(
                        "business_name_within_100m",
                        pd.Series(False, index=subset.index),
                    ).fillna(False).sum()
                ),
                "bcl_work_context_150m_users": int(
                    subset.get(
                        "work_compatible_lexical_within_150m",
                        pd.Series(False, index=subset.index),
                    ).fillna(False).sum()
                ),
                "bcl_business_name_150m_users": int(
                    subset.get(
                        "business_name_within_150m",
                        pd.Series(False, index=subset.index),
                    ).fillna(False).sum()
                ),
            }
        )
    return pd.DataFrame(rows)


def summarize_cross_source_signatures(panel: pd.DataFrame) -> pd.DataFrame:
    """Transparent signatures; no total score or promotion rule."""
    frame = panel.copy()
    frame["howde_match"] = frame["howde_matches_candidate"].fillna(False).astype(bool)
    frame["recurrence_match"] = frame["recurrence_matches_candidate"].fillna(False).astype(bool)
    frame["both_splits"] = pd.to_numeric(
        frame["split_full_candidate_match_count"], errors="coerce"
    ).eq(2)
    frame["heldout_top1"] = frame["full_candidate_heldout_top1"].fillna(False).astype(bool)
    frame["dropout_perfect"] = pd.to_numeric(
        frame["dropout_candidate_retention"], errors="coerce"
    ).eq(1.0)
    frame["bcl_work_150m"] = frame.get(
        "work_compatible_lexical_within_150m",
        pd.Series(False, index=frame.index),
    ).fillna(False).astype(bool)
    frame["bcl_business_150m"] = frame.get(
        "business_name_within_150m",
        pd.Series(False, index=frame.index),
    ).fillna(False).astype(bool)

    group_cols = [
        "audit_group",
        "visual_bucket",
        "howde_match",
        "recurrence_match",
        "both_splits",
        "heldout_top1",
        "dropout_perfect",
        "bcl_work_150m",
        "bcl_business_150m",
    ]
    return (
        frame.groupby(group_cols, as_index=False, dropna=False)
        .agg(users=("audit_id", "nunique"))
        .sort_values(["audit_group", "users"], ascending=[True, False])
        .reset_index(drop=True)
    )


def private_case_matrix(panel: pd.DataFrame) -> pd.DataFrame:
    wanted = [
        "audit_id",
        "user_id",
        "audit_group",
        "candidate_location_id",
        "full_support_days",
        "full_office_share",
        "visual_context_class",
        "visual_bucket",
        "visual_context_confidence",
        "candidate_inside_same_complex",
        "imagery_date_used",
        "imagery_quality",
        "howde_matches_candidate",
        "recurrence_matches_candidate",
        "split_full_candidate_match_count",
        "full_candidate_heldout_top1",
        "dropout_candidate_retention",
        "bcl_evaluable",
        "work_compatible_lexical_within_100m",
        "business_name_within_100m",
        "work_compatible_lexical_within_150m",
        "business_name_within_150m",
        "candidate_equals_production_home",
        "candidate_home_distance_m",
        "present_day_name_aid",
        "review_notes",
    ]
    return panel[[c for c in wanted if c in panel.columns]].copy()


def policy_snapshot(panel: pd.DataFrame) -> pd.DataFrame:
    """Aggregate audit summary only; does not recommend auto-promotion."""
    return pd.DataFrame(
        [
            {
                "near_miss_users": int(len(panel)),
                "margin_near_users": int(panel["audit_group"].eq("margin_near").sum()),
                "share_near_users": int(panel["audit_group"].eq("share_near").sum()),
                "office_like_imagery_users": int(panel["visual_bucket"].eq("office_like").sum()),
                "institutional_daytime_imagery_users": int(
                    panel["visual_bucket"].eq("institutional_or_daytime_compatible").sum()
                ),
                "office_contradictory_imagery_users": int(
                    panel["visual_bucket"].eq("office_contradictory_context").sum()
                ),
                "indeterminate_imagery_users": int(panel["visual_bucket"].eq("indeterminate").sum()),
                "both_split_tests_users": int(
                    pd.to_numeric(
                        panel["split_full_candidate_match_count"], errors="coerce"
                    ).eq(2).sum()
                ),
                "heldout_top1_users": int(
                    panel["full_candidate_heldout_top1"].fillna(False).sum()
                ),
                "perfect_dropout_users": int(
                    pd.to_numeric(
                        panel["dropout_candidate_retention"], errors="coerce"
                    ).eq(1.0).sum()
                ),
                "bcl_evaluable_users": int(panel["bcl_evaluable"].fillna(False).sum()),
                "bcl_work_context_150m_users": int(
                    panel.get(
                        "work_compatible_lexical_within_150m",
                        pd.Series(False, index=panel.index),
                    ).fillna(False).sum()
                ),
            }
        ]
    )


def synthetic_self_check() -> dict[str, object]:
    review = pd.DataFrame(
        [
            {
                "audit_id": "I01",
                "imagery_available": "yes",
                "imagery_date_used": "approx 2008",
                "imagery_date_offset_days": "",
                "imagery_quality": "high",
                "structure_present": "yes",
                "visual_context_class": "large_office_commercial_like_complex",
                "visual_context_confidence": "medium",
                "candidate_inside_same_complex": "yes",
                "historical_name_evidence": "",
                "present_day_name_aid": "",
                "review_notes": "",
            }
        ]
    )
    assert classify_visual_bucket(
        review.loc[0, "visual_context_class"]
    ) == "office_like"
    assert classify_visual_bucket("education_campus") == "institutional_or_daytime_compatible"
    assert classify_visual_bucket("residential_compound") == "office_contradictory_context"
    assert classify_visual_bucket("mixed_urban_block") == "indeterminate"
    return {"status": "ok", "bucket_rules": 4}
