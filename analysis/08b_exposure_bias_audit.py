"""Stage 08b: observation-density / exposure-bias audit for HOME/OFFICE.

The frozen production policy remains HOME 27 / OFFICE 16.

This stage asks whether a single global semantic gate behaves differently across
users with very different observation exposure. It is diagnostic only: no
threshold is changed here.

Exposure is measured from frozen CP1 semantic stays, with emphasis on the number
of behavior-window opportunity dates actually observed for each user rather
than raw trajectory-file count alone.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from geolife.model import HomeOfficeConfig
from geolife.model import home_office as home_office_model


REGIME_ORDER = ["ZERO", "SPARSE", "MEDIUM", "DENSE"]


def _canonical_users(values: pd.Series) -> pd.Series:
    return values.astype(str)


def _opportunity_summary(
    semantic_stays: pd.DataFrame,
    *,
    config: HomeOfficeConfig,
    kind: str,
) -> pd.DataFrame:
    """Summarize dates/hours where the user is actually observed in a target window."""

    contrib = home_office_model._window_contributions(
        semantic_stays,
        config=config,
        kind=kind,
    )
    prefix = "home" if kind == "home" else "office"
    if contrib.empty:
        return pd.DataFrame(
            columns=[
                "user_id",
                f"{prefix}_opportunity_dates",
                f"{prefix}_opportunity_hours",
            ]
        )

    per_day = (
        contrib.groupby(["user_id", "behavior_date"], as_index=False)["overlap_s"]
        .sum()
    )
    eligible_days = (
        per_day.loc[per_day["overlap_s"].ge(config.min_relevant_date_overlap_s)]
        .groupby("user_id", as_index=False)["behavior_date"]
        .nunique()
        .rename(columns={"behavior_date": f"{prefix}_opportunity_dates"})
    )
    hours = (
        per_day.groupby("user_id", as_index=False)["overlap_s"]
        .sum()
        .rename(columns={"overlap_s": f"{prefix}_opportunity_s"})
    )
    hours[f"{prefix}_opportunity_hours"] = (
        hours[f"{prefix}_opportunity_s"] / 3600.0
    )
    hours = hours.drop(columns=f"{prefix}_opportunity_s")
    return hours.merge(eligible_days, on="user_id", how="left").fillna(
        {f"{prefix}_opportunity_dates": 0}
    )


def assign_exposure_regime(values: pd.Series) -> pd.Series:
    """ZERO for no opportunity; positive users split by percentile into thirds.

    This is an audit stratification, not a production threshold. Ties receive
    the same average percentile and therefore remain in the same regime.
    """

    numeric = pd.to_numeric(values, errors="coerce").fillna(0.0)
    result = pd.Series("ZERO", index=values.index, dtype="object")
    positive = numeric.gt(0)
    if not positive.any():
        return result

    pct = numeric.loc[positive].rank(method="average", pct=True)
    result.loc[positive & numeric.index.isin(pct.loc[pct.le(1 / 3)].index)] = "SPARSE"
    result.loc[positive & numeric.index.isin(pct.loc[pct.gt(1 / 3) & pct.le(2 / 3)].index)] = "MEDIUM"
    result.loc[positive & numeric.index.isin(pct.loc[pct.gt(2 / 3)].index)] = "DENSE"
    return result


def build_user_exposure_profiles(
    semantic_stays: pd.DataFrame,
    locations: pd.DataFrame,
    production_output: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
) -> pd.DataFrame:
    cfg = config or HomeOfficeConfig()
    stays = semantic_stays.copy()
    stays["user_id"] = _canonical_users(stays["user_id"])

    local_dates = stays["arrival_time_local"].map(lambda value: pd.Timestamp(value).date())
    temp = stays[["user_id", "duration_s"]].copy()
    temp["local_date"] = local_dates

    base = (
        temp.groupby("user_id", as_index=False)
        .agg(
            total_stays=("duration_s", "size"),
            active_local_dates=("local_date", "nunique"),
            total_dwell_h=("duration_s", lambda s: float(s.sum() / 3600.0)),
            first_local_date=("local_date", "min"),
            last_local_date=("local_date", "max"),
        )
    )
    base["observation_span_days"] = [
        int((pd.Timestamp(last) - pd.Timestamp(first)).days + 1)
        for first, last in zip(
            base["first_local_date"], base["last_local_date"], strict=True
        )
    ]

    loc = locations.copy()
    loc["user_id"] = _canonical_users(loc["user_id"])
    recurring = (
        loc.loc[pd.to_numeric(loc["stay_count"], errors="coerce").ge(2)]
        .groupby("user_id", as_index=False)
        .agg(recurring_locations=("location_id", "nunique"))
    )
    base = base.merge(recurring, on="user_id", how="left")
    base["recurring_locations"] = base["recurring_locations"].fillna(0).astype(int)

    home_opp = _opportunity_summary(stays, config=cfg, kind="home")
    office_opp = _opportunity_summary(stays, config=cfg, kind="office")
    for frame in (home_opp, office_opp):
        if not frame.empty:
            frame["user_id"] = _canonical_users(frame["user_id"])

    base = base.merge(home_opp, on="user_id", how="left").merge(
        office_opp, on="user_id", how="left"
    )
    for col in [
        "home_opportunity_dates",
        "home_opportunity_hours",
        "office_opportunity_dates",
        "office_opportunity_hours",
    ]:
        base[col] = pd.to_numeric(base[col], errors="coerce").fillna(0.0)
    base["home_opportunity_dates"] = base["home_opportunity_dates"].astype(int)
    base["office_opportunity_dates"] = base["office_opportunity_dates"].astype(int)

    prod = production_output[["user_id", "label"]].copy()
    prod["user_id"] = _canonical_users(prod["user_id"])
    prod["label"] = prod["label"].astype(str).str.upper()
    emitted = (
        prod.assign(value=True)
        .pivot_table(
            index="user_id",
            columns="label",
            values="value",
            aggfunc="max",
            fill_value=False,
        )
        .reset_index()
    )
    for label in ("HOME", "OFFICE"):
        if label not in emitted:
            emitted[label] = False
    emitted = emitted.rename(
        columns={"HOME": "production_HOME", "OFFICE": "production_OFFICE"}
    )
    base = base.merge(
        emitted[["user_id", "production_HOME", "production_OFFICE"]],
        on="user_id",
        how="left",
    )
    base["production_HOME"] = base["production_HOME"].fillna(False).astype(bool)
    base["production_OFFICE"] = base["production_OFFICE"].fillna(False).astype(bool)

    base["home_exposure_regime"] = assign_exposure_regime(
        base["home_opportunity_dates"]
    )
    base["office_exposure_regime"] = assign_exposure_regime(
        base["office_opportunity_dates"]
    )

    return base.sort_values("user_id", kind="stable").reset_index(drop=True)


def _unconstrained_top_candidate(
    features: pd.DataFrame,
    *,
    label: str,
) -> pd.DataFrame:
    prefix = "home" if label == "HOME" else "office"
    dwell_col = f"{prefix}_dwell_s"
    dates_col = f"{prefix}_dates"
    share_col = f"{prefix}_dwell_share"

    eligible = features.loc[
        pd.to_numeric(features["stay_count"], errors="coerce").ge(2)
        & pd.to_numeric(features[dwell_col], errors="coerce").gt(0)
    ].copy()
    if eligible.empty:
        return pd.DataFrame()

    eligible = eligible.sort_values(
        ["user_id", share_col, dates_col, dwell_col, "stay_count", "location_id"],
        ascending=[True, False, False, False, False, True],
        kind="stable",
    )
    eligible["_rank"] = eligible.groupby("user_id").cumcount() + 1
    top = eligible.loc[eligible["_rank"].eq(1)].copy()
    second = eligible.loc[
        eligible["_rank"].eq(2), ["user_id", share_col]
    ].rename(columns={share_col: "_raw_second_share"})
    top = top.merge(second, on="user_id", how="left")
    top["_raw_second_share"] = top["_raw_second_share"].fillna(0.0)
    top["raw_top_share_margin"] = top[share_col] - top["_raw_second_share"]
    top["raw_top_relevant_share"] = top[share_col]
    top["raw_top_relevant_dates"] = top[dates_col].astype(int)
    top["raw_top_relevant_dwell_h"] = top[dwell_col] / 3600.0
    return top


def _classify_gate_status(
    *,
    opportunity_dates: int,
    has_raw_candidate: bool,
    has_eligible_candidate: bool,
    share: float | None,
    margin: float | None,
    min_share: float,
    min_margin: float,
) -> str:
    if int(opportunity_dates) <= 0:
        return "no_observed_opportunity"
    if not has_raw_candidate:
        return "no_recurring_candidate"
    if not has_eligible_candidate:
        return "min_dates_blocked"

    share_ok = bool(pd.notna(share) and float(share) >= min_share)
    margin_ok = bool(pd.notna(margin) and float(margin) >= min_margin)
    if share_ok and margin_ok:
        return "emitted"
    if not share_ok and not margin_ok:
        return "share_and_margin_blocked"
    if not share_ok:
        return "share_blocked"
    return "margin_blocked"


def build_gate_diagnostics(
    semantic_stays: pd.DataFrame,
    locations: pd.DataFrame,
    profiles: pd.DataFrame,
    *,
    config: HomeOfficeConfig | None = None,
) -> pd.DataFrame:
    cfg = config or HomeOfficeConfig()
    features = home_office_model._location_features(
        semantic_stays, locations, config=cfg
    )

    rows: list[pd.DataFrame] = []
    for label in ("HOME", "OFFICE"):
        prefix = "home" if label == "HOME" else "office"
        min_dates = cfg.home_min_dates if label == "HOME" else cfg.office_min_dates
        min_share = cfg.home_min_share if label == "HOME" else cfg.office_min_share
        min_margin = cfg.home_min_margin if label == "HOME" else cfg.office_min_margin
        opp_col = f"{prefix}_opportunity_dates"
        regime_col = f"{prefix}_exposure_regime"

        raw = _unconstrained_top_candidate(features, label=label)
        if raw.empty:
            raw_view = pd.DataFrame(columns=["user_id"])
        else:
            raw_view = raw[
                [
                    "user_id",
                    "location_id",
                    "raw_top_relevant_share",
                    "raw_top_share_margin",
                    "raw_top_relevant_dates",
                    "raw_top_relevant_dwell_h",
                ]
            ].rename(columns={"location_id": "raw_top_location_id"})

        eligible = home_office_model._top_candidate(
            features,
            label=label,
            min_dates=min_dates,
        )
        if eligible.empty:
            eligible_view = pd.DataFrame(columns=["user_id"])
        else:
            eligible_view = eligible[
                [
                    "user_id",
                    "location_id",
                    "relevant_dwell_share",
                    "share_margin",
                    "relevant_dates",
                    "relevant_dwell_h",
                ]
            ].rename(columns={"location_id": "eligible_location_id"})

        base = profiles[
            [
                "user_id",
                "total_stays",
                "active_local_dates",
                "observation_span_days",
                "recurring_locations",
                opp_col,
                regime_col,
                f"production_{label}",
            ]
        ].copy()
        base = base.merge(raw_view, on="user_id", how="left").merge(
            eligible_view, on="user_id", how="left"
        )
        base["label"] = label
        base["has_raw_candidate"] = base["raw_top_location_id"].notna()
        base["has_eligible_candidate"] = base["eligible_location_id"].notna()
        base["raw_top_date_coverage"] = np.where(
            pd.to_numeric(base[opp_col], errors="coerce").gt(0),
            pd.to_numeric(base["raw_top_relevant_dates"], errors="coerce").fillna(0)
            / pd.to_numeric(base[opp_col], errors="coerce"),
            np.nan,
        )
        base["eligible_date_coverage"] = np.where(
            pd.to_numeric(base[opp_col], errors="coerce").gt(0),
            pd.to_numeric(base["relevant_dates"], errors="coerce").fillna(0)
            / pd.to_numeric(base[opp_col], errors="coerce"),
            np.nan,
        )

        base["gate_status"] = [
            _classify_gate_status(
                opportunity_dates=int(opp),
                has_raw_candidate=bool(raw_flag),
                has_eligible_candidate=bool(eligible_flag),
                share=share,
                margin=margin,
                min_share=min_share,
                min_margin=min_margin,
            )
            for opp, raw_flag, eligible_flag, share, margin in zip(
                base[opp_col],
                base["has_raw_candidate"],
                base["has_eligible_candidate"],
                base["relevant_dwell_share"],
                base["share_margin"],
                strict=True,
            )
        ]
        rows.append(base)

    out = pd.concat(rows, ignore_index=True)
    return out.sort_values(["label", "user_id"], kind="stable").reset_index(drop=True)


def summarize_gate_by_regime(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label in ("HOME", "OFFICE"):
        prefix = "home" if label == "HOME" else "office"
        regime_col = f"{prefix}_exposure_regime"
        opp_col = f"{prefix}_opportunity_dates"
        subset = diagnostics.loc[diagnostics["label"].eq(label)].copy()

        for regime in REGIME_ORDER:
            group = subset.loc[subset[regime_col].eq(regime)]
            if group.empty:
                continue
            status = group["gate_status"].value_counts()
            emitted = int(status.get("emitted", 0))
            rows.append(
                {
                    "label": label,
                    "exposure_regime": regime,
                    "users": int(len(group)),
                    "median_total_stays": float(group["total_stays"].median()),
                    "median_active_dates": float(group["active_local_dates"].median()),
                    "median_opportunity_dates": float(group[opp_col].median()),
                    "raw_candidate_users": int(group["has_raw_candidate"].sum()),
                    "eligible_candidate_users": int(
                        group["has_eligible_candidate"].sum()
                    ),
                    "emitted_users": emitted,
                    "emission_rate": float(emitted / len(group)),
                    "min_dates_blocked": int(status.get("min_dates_blocked", 0)),
                    "share_blocked": int(status.get("share_blocked", 0)),
                    "margin_blocked": int(status.get("margin_blocked", 0)),
                    "share_and_margin_blocked": int(
                        status.get("share_and_margin_blocked", 0)
                    ),
                    "no_observed_opportunity": int(
                        status.get("no_observed_opportunity", 0)
                    ),
                    "no_recurring_candidate": int(
                        status.get("no_recurring_candidate", 0)
                    ),
                }
            )
    return pd.DataFrame(rows)


def summarize_exposure_limited_cases(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label in ("HOME", "OFFICE"):
        prefix = "home" if label == "HOME" else "office"
        opp_col = f"{prefix}_opportunity_dates"
        subset = diagnostics.loc[
            diagnostics["label"].eq(label)
            & diagnostics["gate_status"].eq("min_dates_blocked")
        ].copy()
        rows.append(
            {
                "label": label,
                "min_dates_blocked_users": int(len(subset)),
                "blocked_with_all_observed_opportunities_supporting_raw_top": int(
                    np.isclose(
                        pd.to_numeric(
                            subset["raw_top_date_coverage"], errors="coerce"
                        ),
                        1.0,
                    ).sum()
                ),
                "blocked_with_raw_top_coverage_ge_80pct": int(
                    pd.to_numeric(
                        subset["raw_top_date_coverage"], errors="coerce"
                    ).ge(0.80).sum()
                ),
                "median_opportunity_dates": (
                    float(subset[opp_col].median()) if len(subset) else np.nan
                ),
                "median_raw_top_share": (
                    float(
                        pd.to_numeric(
                            subset["raw_top_relevant_share"], errors="coerce"
                        ).median()
                    )
                    if len(subset)
                    else np.nan
                ),
            }
        )
    return pd.DataFrame(rows)


def _safe_spearman(left: pd.Series, right: pd.Series) -> float:
    frame = pd.DataFrame(
        {
            "left": pd.to_numeric(left, errors="coerce"),
            "right": pd.to_numeric(right, errors="coerce"),
        }
    ).dropna()
    if len(frame) < 3 or frame["left"].nunique() < 2 or frame["right"].nunique() < 2:
        return np.nan
    return float(frame["left"].corr(frame["right"], method="spearman"))


def exposure_association_summary(diagnostics: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for label in ("HOME", "OFFICE"):
        prefix = "home" if label == "HOME" else "office"
        opp_col = f"{prefix}_opportunity_dates"
        group = diagnostics.loc[diagnostics["label"].eq(label)].copy()
        emitted = group["gate_status"].eq("emitted").astype(int)

        metrics = [
            ("total_stays_vs_emission", group["total_stays"], emitted),
            ("opportunity_dates_vs_emission", group[opp_col], emitted),
            (
                "opportunity_dates_vs_raw_top_share",
                group[opp_col],
                group["raw_top_relevant_share"],
            ),
            (
                "opportunity_dates_vs_eligible_share",
                group[opp_col],
                group["relevant_dwell_share"],
            ),
            (
                "opportunity_dates_vs_eligible_margin",
                group[opp_col],
                group["share_margin"],
            ),
        ]
        for metric, left, right in metrics:
            rows.append(
                {
                    "label": label,
                    "metric": metric,
                    "spearman_rho": _safe_spearman(left, right),
                }
            )
    return pd.DataFrame(rows)


def method_coverage_by_regime(
    assignments: pd.DataFrame,
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    frame = assignments.copy()
    frame["user_id"] = _canonical_users(frame["user_id"])
    frame["label"] = frame["label"].astype(str).str.upper()
    methods = sorted(frame["method"].astype(str).unique())

    rows: list[dict[str, object]] = []
    for label in ("HOME", "OFFICE"):
        regime_col = (
            "home_exposure_regime" if label == "HOME" else "office_exposure_regime"
        )
        user_regime = profiles[["user_id", regime_col]].copy()
        for regime in REGIME_ORDER:
            universe = set(
                user_regime.loc[user_regime[regime_col].eq(regime), "user_id"]
            )
            if not universe:
                continue
            for method in methods:
                selected = set(
                    frame.loc[
                        frame["label"].eq(label)
                        & frame["method"].eq(method)
                        & frame["user_id"].isin(universe),
                        "user_id",
                    ]
                )
                rows.append(
                    {
                        "label": label,
                        "exposure_regime": regime,
                        "method": method,
                        "users": int(len(universe)),
                        "selected_users": int(len(selected)),
                        "selection_rate": float(len(selected) / len(universe)),
                    }
                )
    return pd.DataFrame(rows)


def fixed_comparator_agreement_by_regime(
    assignments: pd.DataFrame,
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    frame = assignments.copy()
    frame["user_id"] = _canonical_users(frame["user_id"])
    frame["label"] = frame["label"].astype(str).str.upper()

    rows: list[dict[str, object]] = []
    for label in ("HOME", "OFFICE"):
        regime_col = (
            "home_exposure_regime" if label == "HOME" else "office_exposure_regime"
        )
        prof = profiles[["user_id", regime_col]].copy()
        fixed = frame.loc[
            frame["label"].eq(label) & frame["method"].eq("fixed_window"),
            ["user_id", "location_id"],
        ].rename(columns={"location_id": "fixed_location_id"})

        for comparator in ("howde_style", "recurrence"):
            comp = frame.loc[
                frame["label"].eq(label) & frame["method"].eq(comparator),
                ["user_id", "location_id"],
            ].rename(columns={"location_id": "comparator_location_id"})
            merged = prof.merge(fixed, on="user_id", how="left").merge(
                comp, on="user_id", how="left"
            )
            both = merged["fixed_location_id"].notna() & merged[
                "comparator_location_id"
            ].notna()
            merged["exact"] = both & merged["fixed_location_id"].eq(
                merged["comparator_location_id"]
            )

            for regime in REGIME_ORDER:
                group = merged.loc[merged[regime_col].eq(regime)]
                joint = int(
                    (
                        group["fixed_location_id"].notna()
                        & group["comparator_location_id"].notna()
                    ).sum()
                )
                exact = int(group["exact"].sum())
                if len(group) == 0:
                    continue
                rows.append(
                    {
                        "label": label,
                        "exposure_regime": regime,
                        "comparator": comparator,
                        "users": int(len(group)),
                        "joint_selected": joint,
                        "exact_matches": exact,
                        "exact_rate_joint": (
                            float(exact / joint) if joint else np.nan
                        ),
                    }
                )
    return pd.DataFrame(rows)


def home_expansion_by_regime(
    home_expansion_evidence: pd.DataFrame,
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    if home_expansion_evidence.empty:
        return pd.DataFrame()
    exp = home_expansion_evidence.copy()
    exp["user_id"] = _canonical_users(exp["user_id"])
    joined = exp.merge(
        profiles[
            [
                "user_id",
                "home_exposure_regime",
                "home_opportunity_dates",
                "total_stays",
                "active_local_dates",
            ]
        ],
        on="user_id",
        how="left",
        validate="many_to_one",
    )
    return (
        joined.groupby(
            ["home_expansion_tier", "home_exposure_regime"],
            as_index=False,
        )
        .agg(
            candidates=("user_id", "size"),
            median_home_opportunity_dates=("home_opportunity_dates", "median"),
            median_total_stays=("total_stays", "median"),
            median_active_dates=("active_local_dates", "median"),
            median_external_exact_families=(
                "external_exact_family_count",
                "median",
            ),
        )
        .sort_values(
            ["home_expansion_tier", "home_exposure_regime"],
            kind="stable",
        )
    )


def office_near_miss_by_regime(
    near_miss_panel: pd.DataFrame,
    profiles: pd.DataFrame,
) -> pd.DataFrame:
    if near_miss_panel.empty:
        return pd.DataFrame()
    near = near_miss_panel.loc[
        near_miss_panel["audit_group"].astype(str).ne("baseline"),
        ["user_id", "audit_group"],
    ].drop_duplicates().copy()
    near["user_id"] = _canonical_users(near["user_id"])
    joined = near.merge(
        profiles[
            [
                "user_id",
                "office_exposure_regime",
                "office_opportunity_dates",
                "total_stays",
                "active_local_dates",
            ]
        ],
        on="user_id",
        how="left",
        validate="one_to_one",
    )
    return (
        joined.groupby(
            ["audit_group", "office_exposure_regime"], as_index=False
        )
        .agg(
            users=("user_id", "size"),
            median_office_opportunity_dates=("office_opportunity_dates", "median"),
            median_total_stays=("total_stays", "median"),
            median_active_dates=("active_local_dates", "median"),
        )
        .sort_values(
            ["audit_group", "office_exposure_regime"], kind="stable"
        )
    )


def build_bias_hypothesis_snapshot(
    regime_summary: pd.DataFrame,
    exposure_limited: pd.DataFrame,
    associations: pd.DataFrame,
) -> pd.DataFrame:
    """Small descriptive snapshot; no automatic causal/bias verdict."""

    rows: list[dict[str, object]] = []
    for label in ("HOME", "OFFICE"):
        subset = regime_summary.loc[regime_summary["label"].eq(label)]
        sparse = subset.loc[subset["exposure_regime"].eq("SPARSE")]
        dense = subset.loc[subset["exposure_regime"].eq("DENSE")]
        limited = exposure_limited.loc[exposure_limited["label"].eq(label)]
        assoc = associations.loc[
            associations["label"].eq(label)
            & associations["metric"].eq("opportunity_dates_vs_emission")
        ]

        rows.append(
            {
                "label": label,
                "sparse_emission_rate": (
                    float(sparse["emission_rate"].iloc[0])
                    if len(sparse)
                    else np.nan
                ),
                "dense_emission_rate": (
                    float(dense["emission_rate"].iloc[0])
                    if len(dense)
                    else np.nan
                ),
                "opportunity_dates_vs_emission_spearman": (
                    float(assoc["spearman_rho"].iloc[0])
                    if len(assoc)
                    else np.nan
                ),
                "min_dates_blocked_users": (
                    int(limited["min_dates_blocked_users"].iloc[0])
                    if len(limited)
                    else 0
                ),
                "min_dates_blocked_with_full_observed_coverage": (
                    int(
                        limited[
                            "blocked_with_all_observed_opportunities_supporting_raw_top"
                        ].iloc[0]
                    )
                    if len(limited)
                    else 0
                ),
            }
        )
    return pd.DataFrame(rows)


def synthetic_self_check() -> dict[str, object]:
    regimes = assign_exposure_regime(pd.Series([0, 1, 2, 10, 20, 40]))
    assert regimes.iloc[0] == "ZERO"
    assert set(regimes.iloc[1:]).issubset({"SPARSE", "MEDIUM", "DENSE"})

    assert (
        _classify_gate_status(
            opportunity_dates=2,
            has_raw_candidate=True,
            has_eligible_candidate=False,
            share=None,
            margin=None,
            min_share=0.50,
            min_margin=0.20,
        )
        == "min_dates_blocked"
    )
    assert (
        _classify_gate_status(
            opportunity_dates=10,
            has_raw_candidate=True,
            has_eligible_candidate=True,
            share=0.60,
            margin=0.25,
            min_share=0.50,
            min_margin=0.20,
        )
        == "emitted"
    )
    assert (
        _classify_gate_status(
            opportunity_dates=10,
            has_raw_candidate=True,
            has_eligible_candidate=True,
            share=0.40,
            margin=0.25,
            min_share=0.50,
            min_margin=0.20,
        )
        == "share_blocked"
    )

    return {"status": "ok", "regimes": sorted(set(regimes))}
