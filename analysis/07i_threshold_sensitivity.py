"""Stage 07i: threshold sensitivity with BCL-primary semantic interpretation.

This stage responds to two methodological concerns:

1. Historical OSM snapshots for this GeoLife cohort are mostly 2008-2009,
   when OSM mapping completeness was sparse. OSM is therefore treated as
   support-only mapped context, never as a negative vote against BCL.
2. Current HOME/OFFICE and stable-secondary heuristics may be conservative.
   We audit predeclared threshold grids without selecting a new production
   threshold based on semantic agreement.

No production configuration is modified by this stage.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys
from typing import Iterable

import numpy as np
import pandas as pd

from geolife.model import HomeOfficeConfig


OFFICE_DATES_GRID = (2, 3, 5)
OFFICE_SHARE_GRID = (0.20, 0.30, 0.40)
OFFICE_MARGIN_GRID = (0.05, 0.10, 0.20)

BCL_RADII_M = (25.0, 50.0, 75.0, 100.0, 125.0, 150.0)
PRIMARY_BCL_RADIUS_M = 100.0
MAX_REUSED_BCL_RADIUS_M = 150.0

BASELINE_MOBILITY = {
    "window_days": 42,
    "step_days": 14,
    "min_observed_days": 6,
    "min_candidate_days": 3,
    "min_candidate_stays": 2,
    "stability_threshold": 0.70,
}


@dataclass(frozen=True)
class MobilitySensitivityConfig:
    name: str
    window_days: int = 42
    step_days: int = 14
    min_observed_days: int = 6
    min_candidate_days: int = 3
    min_candidate_stays: int = 2
    stability_threshold: float = 0.70
    family: str = "oat"
    changed_axis: str = "baseline"


def _load_module(filename: str, name: str):
    path = Path(__file__).with_name(filename)
    spec = spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {filename}")
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


STAGE05 = _load_module("05_home_office_reliability.py", "stage05_for_07i")
STAGE05B = _load_module("05b_home_consensus_adaptive_work.py", "stage05b_for_07i")
STAGE07G = _load_module("07g_bcl_poi_2008_alignment.py", "stage07g_for_07i")


def office_gate_grid() -> list[HomeOfficeConfig]:
    configs: list[HomeOfficeConfig] = []
    base = HomeOfficeConfig()
    for dates in OFFICE_DATES_GRID:
        for share in OFFICE_SHARE_GRID:
            for margin in OFFICE_MARGIN_GRID:
                configs.append(
                    replace(
                        base,
                        office_min_dates=int(dates),
                        office_min_share=float(share),
                        office_min_margin=float(margin),
                    )
                )
    return configs


def run_office_gate_sensitivity(
    semantic_stays: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Evaluate the fixed-window OFFICE gate on a predeclared 3x3x3 grid."""
    base_cfg = HomeOfficeConfig()
    base_assignments = STAGE05.infer_assignments(
        semantic_stays,
        config=base_cfg,
        methods=(STAGE05.METHOD_FIXED,),
    )
    base_office = base_assignments.loc[
        base_assignments["label"].eq("OFFICE")
    ].copy()
    base_emitted = base_office.loc[
        base_office["emitted"].fillna(False).astype(bool)
    ].copy()
    baseline_users = set(base_emitted["user_id"].astype(str))
    baseline_location = dict(
        zip(
            base_emitted["user_id"].astype(str),
            base_emitted["location_id"].astype(int),
        )
    )

    summaries: list[dict[str, object]] = []
    emitted_rows: list[pd.DataFrame] = []

    for cfg in office_gate_grid():
        assignments = STAGE05.infer_assignments(
            semantic_stays,
            config=cfg,
            methods=(STAGE05.METHOD_FIXED,),
        )
        office = assignments.loc[assignments["label"].eq("OFFICE")].copy()
        emitted = office.loc[
            office["emitted"].fillna(False).astype(bool)
        ].copy()
        emitted["user_id"] = emitted["user_id"].astype(str)
        emitted_users = set(emitted["user_id"])
        common = emitted.loc[emitted["user_id"].isin(baseline_users)]
        same_location = sum(
            int(row.location_id) == baseline_location.get(str(row.user_id))
            for row in common.itertuples(index=False)
        )

        summaries.append(
            {
                "office_min_dates": int(cfg.office_min_dates),
                "office_min_share": float(cfg.office_min_share),
                "office_min_margin": float(cfg.office_min_margin),
                "is_frozen_baseline": bool(
                    cfg.office_min_dates == base_cfg.office_min_dates
                    and np.isclose(cfg.office_min_share, base_cfg.office_min_share)
                    and np.isclose(cfg.office_min_margin, base_cfg.office_min_margin)
                ),
                "candidate_users": int(office["user_id"].nunique()),
                "emitted_users": int(len(emitted_users)),
                "baseline_emitted_retained": int(
                    len(emitted_users.intersection(baseline_users))
                ),
                "new_vs_baseline_emitted": int(
                    len(emitted_users.difference(baseline_users))
                ),
                "baseline_emitted_lost": int(
                    len(baseline_users.difference(emitted_users))
                ),
                "common_emitted_same_location": int(same_location),
            }
        )
        if not emitted.empty:
            copy = emitted[
                ["user_id", "location_id", "support_days", "score"]
            ].copy()
            copy["office_min_dates"] = int(cfg.office_min_dates)
            copy["office_min_share"] = float(cfg.office_min_share)
            copy["office_min_margin"] = float(cfg.office_min_margin)
            emitted_rows.append(copy)

    details = (
        pd.concat(emitted_rows, ignore_index=True)
        if emitted_rows
        else pd.DataFrame()
    )
    return pd.DataFrame(summaries), details


def mobility_oat_configs() -> list[MobilitySensitivityConfig]:
    base = MobilitySensitivityConfig(name="baseline")
    configs = [base]
    variations = {
        "window_days": (28, 56),
        "min_observed_days": (4, 8),
        "min_candidate_days": (2, 4),
        "min_candidate_stays": (1, 3),
        "stability_threshold": (0.60, 0.80),
    }
    for axis, values in variations.items():
        for value in values:
            configs.append(
                replace(
                    base,
                    name=f"{axis}={value}",
                    changed_axis=axis,
                    **{axis: value},
                )
            )
    return configs


def mobility_profile_configs() -> list[MobilitySensitivityConfig]:
    return [
        MobilitySensitivityConfig(
            name="relaxed",
            min_observed_days=4,
            min_candidate_days=2,
            min_candidate_stays=1,
            stability_threshold=0.60,
            family="profile",
            changed_axis="joint",
        ),
        MobilitySensitivityConfig(
            name="mildly_relaxed",
            min_observed_days=5,
            min_candidate_days=2,
            min_candidate_stays=2,
            stability_threshold=0.60,
            family="profile",
            changed_axis="joint",
        ),
        MobilitySensitivityConfig(
            name="baseline_profile",
            family="profile",
            changed_axis="joint",
        ),
        MobilitySensitivityConfig(
            name="strict",
            min_observed_days=8,
            min_candidate_days=4,
            min_candidate_stays=3,
            stability_threshold=0.80,
            family="profile",
            changed_axis="joint",
        ),
    ]


def all_mobility_configs() -> list[MobilitySensitivityConfig]:
    configs = mobility_oat_configs() + mobility_profile_configs()
    # Keep both baseline names because they serve separate OAT/profile tables.
    return configs


def run_mobility_config(
    semantic_stays: pd.DataFrame,
    home_evidence: pd.DataFrame,
    assignments: pd.DataFrame,
    config: MobilitySensitivityConfig,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    windows = STAGE05B.build_adaptive_work_windows(
        semantic_stays,
        home_evidence,
        window_days=int(config.window_days),
        step_days=int(config.step_days),
        min_observed_days=int(config.min_observed_days),
        min_candidate_days=int(config.min_candidate_days),
        min_candidate_stays=int(config.min_candidate_stays),
    )
    patterns = STAGE05B.summarize_adaptive_work_patterns(
        windows,
        stability_threshold=float(config.stability_threshold),
    )
    compared = STAGE05B.compare_work_patterns_to_static(patterns, assignments)
    return windows, compared


def summarize_mobility_config(
    patterns: pd.DataFrame,
    *,
    config: MobilitySensitivityConfig,
    baseline_patterns: pd.DataFrame,
) -> dict[str, object]:
    frame = patterns.copy()
    frame["user_id"] = frame["user_id"].astype(str)
    stable = frame.loc[
        frame["window_pattern"].eq("stable_secondary_anchor")
    ].copy()

    baseline = baseline_patterns.copy()
    baseline["user_id"] = baseline["user_id"].astype(str)
    baseline_stable = baseline.loc[
        baseline["window_pattern"].eq("stable_secondary_anchor")
    ].copy()
    baseline_users = set(baseline_stable["user_id"])
    current_users = set(stable["user_id"])
    baseline_locations = dict(
        zip(
            baseline_stable["user_id"],
            pd.to_numeric(
                baseline_stable["dominant_location_id"], errors="coerce"
            ).astype("Int64"),
        )
    )
    common = stable.loc[stable["user_id"].isin(baseline_users)]
    same_candidate = 0
    for row in common.itertuples(index=False):
        current = int(row.dominant_location_id)
        previous = baseline_locations.get(str(row.user_id))
        if previous is not None and pd.notna(previous):
            same_candidate += int(current == int(previous))

    counts = frame["window_pattern"].value_counts()
    return {
        "config_name": config.name,
        "family": config.family,
        "changed_axis": config.changed_axis,
        "window_days": int(config.window_days),
        "step_days": int(config.step_days),
        "min_observed_days": int(config.min_observed_days),
        "min_candidate_days": int(config.min_candidate_days),
        "min_candidate_stays": int(config.min_candidate_stays),
        "stability_threshold": float(config.stability_threshold),
        "users": int(frame["user_id"].nunique()),
        "stable_users": int(len(current_users)),
        "multi_anchor_users": int(counts.get("multi_anchor", 0)),
        "unstable_users": int(counts.get("unstable", 0)),
        "insufficient_users": int(counts.get("insufficient", 0)),
        "baseline_stable_retained": int(
            len(current_users.intersection(baseline_users))
        ),
        "new_stable_vs_baseline": int(
            len(current_users.difference(baseline_users))
        ),
        "baseline_stable_lost": int(
            len(baseline_users.difference(current_users))
        ),
        "common_stable_same_candidate": int(same_candidate),
        "median_dominant_window_share": (
            float(pd.to_numeric(stable["dominant_window_share"], errors="coerce").median())
            if not stable.empty
            else np.nan
        ),
    }


def build_bcl_metrics_to_150m(
    eligible_anchors: pd.DataFrame,
    classified_pois: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reuse Stage-07g extracted POIs up to its 150 m retrieval padding."""
    matches = STAGE07G.assign_pois_to_anchors(
        eligible_anchors,
        classified_pois,
        max_distance_m=MAX_REUSED_BCL_RADIUS_M,
    )
    metrics = STAGE07G.build_anchor_lexical_metrics(
        eligible_anchors,
        matches,
        thresholds_m=BCL_RADII_M,
    )
    return matches, metrics


def summarize_bcl_for_patterns(
    metrics: pd.DataFrame,
    patterns: pd.DataFrame,
    profiles: pd.DataFrame,
    *,
    config_name: str,
    family: str,
    radii_m: Iterable[float] = BCL_RADII_M,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    aligned = STAGE07G.align_mobility_roles(metrics, patterns, profiles)
    comparisons = STAGE07G.build_stable_secondary_lexical_comparisons(
        aligned,
        thresholds_m=radii_m,
    )
    summary = STAGE07G.summarize_stable_secondary_comparisons(
        comparisons,
        thresholds_m=radii_m,
    )
    if summary.empty:
        summary = pd.DataFrame(
            columns=[
                "threshold_m",
                "users",
                "candidate_context_users",
                "mean_peer_context_share",
                "mean_candidate_minus_peer_share",
                "bootstrap_95_low",
                "bootstrap_95_high",
                "candidate_beats_peer_share_users",
            ]
        )
    summary.insert(0, "family", family)
    summary.insert(0, "config_name", config_name)

    candidate_rows = aligned.loc[
        aligned.get("stable_secondary_anchor", False)
    ].copy()
    category_rows = []
    for threshold in radii_m:
        value = int(threshold)
        for category in ("business_name", "education", "retail_service"):
            column = f"{category}_within_{value}m"
            category_rows.append(
                {
                    "config_name": config_name,
                    "family": family,
                    "threshold_m": float(threshold),
                    "category": category,
                    "candidate_users": int(
                        candidate_rows[column].fillna(False).sum()
                    ) if column in candidate_rows else 0,
                    "evaluable_candidate_users": int(len(candidate_rows)),
                }
            )
    return summary, pd.DataFrame(category_rows)


def annotate_office_grid_with_bcl(
    office_grid: pd.DataFrame,
    office_emitted_details: pd.DataFrame,
    bcl_metrics: pd.DataFrame,
    *,
    threshold_m: float = PRIMARY_BCL_RADIUS_M,
) -> pd.DataFrame:
    """Attach BCL context only where emitted OFFICE candidates are evaluable.

    This is not full-cohort validation: BCL metrics cover the temporally
    eligible recurring non-HOME analysis universe only.
    """
    out = office_grid.copy()
    if office_emitted_details.empty:
        out["bcl_evaluable_emitted_users"] = 0
        out["bcl_context_emitted_users"] = 0
        out["bcl_business_name_emitted_users"] = 0
        return out

    metrics = bcl_metrics.copy()
    metrics["user_id"] = metrics["user_id"].astype(str)
    metrics["location_id"] = pd.to_numeric(
        metrics["location_id"], errors="raise"
    ).astype(int)

    key_cols = ["user_id", "location_id"]
    work_col = f"work_compatible_lexical_within_{int(threshold_m)}m"
    business_col = f"business_name_within_{int(threshold_m)}m"
    lookup = metrics[key_cols + [work_col, business_col]].drop_duplicates(key_cols)

    rows = []
    for grid in out.itertuples(index=False):
        subset = office_emitted_details.loc[
            office_emitted_details["office_min_dates"].eq(grid.office_min_dates)
            & np.isclose(
                office_emitted_details["office_min_share"],
                grid.office_min_share,
            )
            & np.isclose(
                office_emitted_details["office_min_margin"],
                grid.office_min_margin,
            )
        ].copy()
        merged = subset.merge(
            lookup,
            on=key_cols,
            how="inner",
            validate="one_to_one",
        )
        rows.append(
            {
                "office_min_dates": int(grid.office_min_dates),
                "office_min_share": float(grid.office_min_share),
                "office_min_margin": float(grid.office_min_margin),
                "bcl_evaluable_emitted_users": int(merged["user_id"].nunique()),
                "bcl_context_emitted_users": int(
                    merged[work_col].fillna(False).sum()
                ) if not merged.empty else 0,
                "bcl_business_name_emitted_users": int(
                    merged[business_col].fillna(False).sum()
                ) if not merged.empty else 0,
            }
        )
    return out.merge(
        pd.DataFrame(rows),
        on=["office_min_dates", "office_min_share", "office_min_margin"],
        how="left",
        validate="one_to_one",
    )


def bcl_primary_osm_support_summary(
    triangulation_panel: pd.DataFrame,
    *,
    threshold_m: float = PRIMARY_BCL_RADIUS_M,
) -> pd.DataFrame:
    """Reinterpret historical OSM as positive support only.

    OSM absence or candidate-vs-peer negative direction is never counted as
    contradiction because early historical mapping completeness is unknown.
    """
    panel = triangulation_panel.copy()
    value = int(threshold_m)
    bcl_diff = pd.to_numeric(
        panel[f"bcl_candidate_minus_peer_{value}m"], errors="coerce"
    )
    bcl_context = panel[f"bcl_candidate_context_{value}m"].fillna(False).astype(bool)
    osm_context = panel[f"osm_candidate_context_{value}m"].fillna(False).astype(bool)
    osm_diff = pd.to_numeric(
        panel[f"osm_candidate_minus_peer_{value}m"], errors="coerce"
    )

    bcl_positive = bcl_diff.gt(0)
    bcl_neutral = bcl_diff.eq(0)
    bcl_negative = bcl_diff.lt(0)

    return pd.DataFrame(
        [
            {
                "threshold_m": float(threshold_m),
                "users": int(len(panel)),
                "bcl_candidate_context_users": int(bcl_context.sum()),
                "bcl_candidate_favoring_users": int(bcl_positive.sum()),
                "bcl_neutral_users": int(bcl_neutral.sum()),
                "bcl_peer_favoring_users": int(bcl_negative.sum()),
                "bcl_favoring_with_osm_candidate_context_support": int(
                    (bcl_positive & osm_context).sum()
                ),
                "bcl_favoring_with_osm_candidate_favoring_support": int(
                    (bcl_positive & osm_diff.gt(0)).sum()
                ),
                "bcl_favoring_without_osm_mapped_candidate_context": int(
                    (bcl_positive & ~osm_context).sum()
                ),
                "behavior_strict_and_bcl_favoring_users": int(
                    (
                        panel["behavior_primary_support"].fillna(False)
                        & bcl_positive
                    ).sum()
                ),
                "behavior_directional_and_bcl_favoring_users": int(
                    (
                        panel["behavior_directional_majority"].fillna(False)
                        & bcl_positive
                    ).sum()
                ),
            }
        ]
    )


def synthetic_self_check() -> dict[str, object]:
    oat = mobility_oat_configs()
    assert len(oat) == 11
    assert any(
        cfg.changed_axis == "stability_threshold"
        and np.isclose(cfg.stability_threshold, 0.60)
        for cfg in oat
    )
    profiles = mobility_profile_configs()
    assert [cfg.name for cfg in profiles] == [
        "relaxed",
        "mildly_relaxed",
        "baseline_profile",
        "strict",
    ]
    assert len(office_gate_grid()) == 27
    assert max(BCL_RADII_M) == MAX_REUSED_BCL_RADIUS_M
    return {
        "status": "ok",
        "office_grid": 27,
        "mobility_oat": len(oat),
        "mobility_profiles": len(profiles),
        "max_bcl_radius_m": MAX_REUSED_BCL_RADIUS_M,
    }
