"""Stage 07m: Trackintel semantic-only parity on frozen CP2-v2 locations.

This module contains only adapter and comparison logic. It intentionally does
not import Trackintel so the repository test suite does not gain a heavyweight
runtime dependency. The notebook pins Trackintel 1.4.2 and executes the actual
FREQ / OSNA implementation.

Primary experiment:
    frozen 5,821 CP1 stays
    -> production CP2-v2 per-stay timezone + complete-link 200 m locations
    -> same location_id namespace
    -> Trackintel location_identifier(FREQ/OSNA, pre_filter=False)
    -> candidate-identity comparison against production HOME/OFFICE

No comparator result is used to retune production thresholds.
"""

from __future__ import annotations

from itertools import product

import numpy as np
import pandas as pd


REQUIRED_SEMANTIC_COLUMNS = {
    "user_id",
    "location_id",
    "latitude",
    "longitude",
    "duration_s",
    "arrival_time_local",
    "departure_time_local",
}


def _dummy_utc_from_local_wall(value: object) -> pd.Timestamp:
    """Encode one timezone-aware local wall time as a dummy UTC timestamp."""

    ts = pd.Timestamp(value)
    if ts.tzinfo is None:
        raise ValueError("local wall-clock timestamp must be timezone-aware")
    return ts.tz_localize(None).tz_localize("UTC")


def build_trackintel_adapter(semantic_stays: pd.DataFrame) -> pd.DataFrame:
    """Build the Trackintel-facing staypoint table in the production namespace.

    started_at is local wall-clock time encoded in dummy UTC. finished_at
    preserves the true elapsed duration_s, which avoids DST clock changes
    changing stay weights inside Trackintel. finish_wall_delta_s reports the
    difference between that duration-preserving endpoint and the exact encoded
    local departure wall time.
    """

    missing = REQUIRED_SEMANTIC_COLUMNS.difference(semantic_stays.columns)
    if missing:
        raise ValueError(f"missing semantic stay columns: {sorted(missing)}")

    out = semantic_stays[
        [
            "user_id",
            "location_id",
            "latitude",
            "longitude",
            "duration_s",
            "arrival_time_local",
            "departure_time_local",
        ]
    ].copy()

    out["user_id"] = out["user_id"].astype(str)
    out["location_id"] = pd.to_numeric(out["location_id"], errors="raise").astype(int)
    out["duration_s"] = pd.to_numeric(out["duration_s"], errors="raise").astype(float)
    if (out["duration_s"] < 0).any():
        raise ValueError("duration_s must be non-negative")

    out["started_at"] = pd.DatetimeIndex(
        out["arrival_time_local"].map(_dummy_utc_from_local_wall)
    )
    out["finished_at"] = out["started_at"] + pd.to_timedelta(out["duration_s"], unit="s")
    out["_departure_wall_encoded"] = pd.DatetimeIndex(
        out["departure_time_local"].map(_dummy_utc_from_local_wall)
    )
    out["finish_wall_delta_s"] = (
        out["_departure_wall_encoded"] - out["finished_at"]
    ).dt.total_seconds()

    if (out["finished_at"] < out["started_at"]).any():
        raise RuntimeError("Trackintel adapter created a negative stay interval")

    return out[
        [
            "user_id",
            "started_at",
            "finished_at",
            "latitude",
            "longitude",
            "location_id",
            "duration_s",
            "finish_wall_delta_s",
        ]
    ].reset_index(drop=True)


def adapter_diagnostics(adapter: pd.DataFrame) -> pd.DataFrame:
    delta = pd.to_numeric(adapter["finish_wall_delta_s"], errors="coerce")
    return pd.DataFrame(
        [
            {
                "adapter_rows": int(len(adapter)),
                "users": int(adapter["user_id"].nunique()),
                "locations": int(adapter[["user_id", "location_id"]].drop_duplicates().shape[0]),
                "finish_wall_delta_nonzero": int(delta.fillna(0).ne(0).sum()),
                "finish_wall_delta_abs_max_s": float(delta.abs().max()) if len(delta) else np.nan,
            }
        ]
    )


def extract_trackintel_candidates(labeled_staypoints: pd.DataFrame, method: str) -> pd.DataFrame:
    """Reduce Trackintel staypoint purposes to one candidate location per label/user."""

    required = {"user_id", "location_id", "purpose"}
    missing = required.difference(labeled_staypoints.columns)
    if missing:
        raise ValueError(f"missing Trackintel output columns: {sorted(missing)}")

    frame = labeled_staypoints[["user_id", "location_id", "purpose"]].copy()
    frame["user_id"] = frame["user_id"].astype(str)
    frame["purpose"] = frame["purpose"].astype("string").str.lower()
    frame = frame.loc[frame["purpose"].isin(["home", "work"])].copy()
    if frame.empty:
        return pd.DataFrame(columns=["method", "user_id", "label", "location_id"])

    frame["label"] = frame["purpose"].map({"home": "HOME", "work": "OFFICE"})
    counts = frame.groupby(["user_id", "label"])["location_id"].nunique()
    bad = counts.loc[counts.gt(1)]
    if len(bad):
        raise RuntimeError(
            "Trackintel assigned more than one location to a semantic label: "
            + ", ".join(f"{idx}:{int(value)}" for idx, value in bad.items())
        )

    out = (
        frame.drop_duplicates(["user_id", "label", "location_id"])
        [["user_id", "label", "location_id"]]
        .copy()
    )
    out["location_id"] = pd.to_numeric(out["location_id"], errors="raise").astype(int)
    out.insert(0, "method", str(method))
    return out.sort_values(["method", "user_id", "label"], kind="stable").reset_index(drop=True)


def production_candidates(production_output: pd.DataFrame) -> pd.DataFrame:
    required = {"user_id", "label", "location_id"}
    missing = required.difference(production_output.columns)
    if missing:
        raise ValueError(f"missing production output columns: {sorted(missing)}")
    out = production_output[["user_id", "label", "location_id"]].copy()
    out["user_id"] = out["user_id"].astype(str)
    out["label"] = out["label"].astype(str).str.upper()
    out["location_id"] = pd.to_numeric(out["location_id"], errors="raise").astype(int)
    return out.drop_duplicates(["user_id", "label"]).reset_index(drop=True)


def build_candidate_comparison(
    universe_users: list[str] | set[str] | pd.Series,
    production: pd.DataFrame,
    comparator_candidates: pd.DataFrame,
) -> pd.DataFrame:
    """Create one row per method x user x HOME/OFFICE comparison state."""

    users = sorted({str(value) for value in universe_users})
    methods = sorted(comparator_candidates["method"].astype(str).unique())
    if not methods:
        raise ValueError("comparator_candidates contains no methods")

    base = pd.DataFrame(
        list(product(methods, users, ["HOME", "OFFICE"])),
        columns=["method", "user_id", "label"],
    )
    prod = production_candidates(production).rename(
        columns={"location_id": "production_location_id"}
    )
    comp = comparator_candidates[
        ["method", "user_id", "label", "location_id"]
    ].copy().rename(columns={"location_id": "comparator_location_id"})
    comp["user_id"] = comp["user_id"].astype(str)
    comp["label"] = comp["label"].astype(str).str.upper()

    out = base.merge(prod, on=["user_id", "label"], how="left").merge(
        comp, on=["method", "user_id", "label"], how="left"
    )
    out["production_emitted"] = out["production_location_id"].notna()
    out["comparator_selected"] = out["comparator_location_id"].notna()
    out["exact_location_match"] = (
        out["production_emitted"]
        & out["comparator_selected"]
        & out["production_location_id"].eq(out["comparator_location_id"])
    )

    conditions = [
        out["exact_location_match"],
        out["production_emitted"] & out["comparator_selected"],
        out["production_emitted"] & ~out["comparator_selected"],
        ~out["production_emitted"] & out["comparator_selected"],
    ]
    choices = ["both_same", "both_different", "production_only", "comparator_only"]
    out["status"] = np.select(conditions, choices, default="neither")
    return out


def summarize_agreement(comparison: pd.DataFrame) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for (method, label), group in comparison.groupby(["method", "label"], sort=True):
        production_n = int(group["production_emitted"].sum())
        comparator_n = int(group["comparator_selected"].sum())
        joint_n = int((group["production_emitted"] & group["comparator_selected"]).sum())
        exact_n = int(group["exact_location_match"].sum())
        rows.append(
            {
                "method": method,
                "label": label,
                "universe_users": int(group["user_id"].nunique()),
                "production_emitted_users": production_n,
                "comparator_selected_users": comparator_n,
                "joint_selected_users": joint_n,
                "exact_location_match_users": exact_n,
                "exact_rate_among_joint": exact_n / joint_n if joint_n else np.nan,
                "production_candidate_match_rate": exact_n / production_n if production_n else np.nan,
                "comparator_candidate_match_rate": exact_n / comparator_n if comparator_n else np.nan,
            }
        )
    return pd.DataFrame(rows)


def summarize_status_distribution(comparison: pd.DataFrame) -> pd.DataFrame:
    return (
        comparison.groupby(["method", "label", "status"], as_index=False)
        .size()
        .rename(columns={"size": "users"})
        .sort_values(["method", "label", "status"], kind="stable")
        .reset_index(drop=True)
    )


def summarize_reference_label(comparison: pd.DataFrame, label: str = "OFFICE") -> pd.DataFrame:
    target = str(label).upper()
    frame = comparison.loc[comparison["label"].eq(target)].copy()
    rows: list[dict[str, object]] = []
    for method, group in frame.groupby("method", sort=True):
        reference = group.loc[group["production_emitted"]]
        rows.append(
            {
                "method": method,
                "label": target,
                "production_reference_users": int(len(reference)),
                "comparator_selected_on_reference": int(reference["comparator_selected"].sum()),
                "exact_reference_candidate_matches": int(reference["exact_location_match"].sum()),
                "exact_reference_match_rate": float(reference["exact_location_match"].mean())
                if len(reference)
                else np.nan,
            }
        )
    return pd.DataFrame(rows)


def summarize_near_miss_work(
    near_miss_panel: pd.DataFrame,
    comparator_candidates: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare Trackintel WORK identity to the frozen Stage-07j near-miss candidate."""

    required = {"user_id", "audit_group", "candidate_location_id"}
    missing = required.difference(near_miss_panel.columns)
    if missing:
        raise ValueError(f"missing near-miss columns: {sorted(missing)}")

    near = near_miss_panel.loc[
        near_miss_panel["audit_group"].astype(str).ne("baseline"),
        ["user_id", "audit_group", "candidate_location_id"],
    ].copy()
    near["user_id"] = near["user_id"].astype(str)
    near["candidate_location_id"] = pd.to_numeric(
        near["candidate_location_id"], errors="raise"
    ).astype(int)

    work = comparator_candidates.loc[
        comparator_candidates["label"].astype(str).str.upper().eq("OFFICE"),
        ["method", "user_id", "location_id"],
    ].copy()
    methods = sorted(comparator_candidates["method"].astype(str).unique())

    expanded = pd.concat(
        [near.assign(method=method) for method in methods],
        ignore_index=True,
    )
    expanded = expanded.merge(
        work.rename(columns={"location_id": "comparator_work_location_id"}),
        on=["method", "user_id"],
        how="left",
    )
    expanded["comparator_work_selected"] = expanded["comparator_work_location_id"].notna()
    expanded["exact_near_miss_candidate_match"] = (
        expanded["comparator_work_selected"]
        & expanded["comparator_work_location_id"].eq(expanded["candidate_location_id"])
    )

    rows: list[dict[str, object]] = []
    for (method, group_name), group in expanded.groupby(
        ["method", "audit_group"], sort=True
    ):
        selected_n = int(group["comparator_work_selected"].sum())
        exact_n = int(group["exact_near_miss_candidate_match"].sum())
        rows.append(
            {
                "method": method,
                "audit_group": group_name,
                "near_miss_users": int(len(group)),
                "comparator_work_selected_users": selected_n,
                "exact_near_miss_candidate_matches": exact_n,
                "exact_match_rate_all": exact_n / len(group) if len(group) else np.nan,
                "exact_match_rate_selected": exact_n / selected_n if selected_n else np.nan,
            }
        )
    return expanded, pd.DataFrame(rows)


def synthetic_self_check() -> dict[str, object]:
    semantic = pd.DataFrame(
        {
            "user_id": ["u", "u"],
            "location_id": [0, 1],
            "latitude": [39.9, 39.91],
            "longitude": [116.4, 116.41],
            "duration_s": [3600.0, 7200.0],
            "arrival_time_local": [
                pd.Timestamp("2026-01-05 09:00", tz="Asia/Shanghai"),
                pd.Timestamp("2026-01-05 21:00", tz="Asia/Shanghai"),
            ],
            "departure_time_local": [
                pd.Timestamp("2026-01-05 10:00", tz="Asia/Shanghai"),
                pd.Timestamp("2026-01-05 23:00", tz="Asia/Shanghai"),
            ],
        }
    )
    adapter = build_trackintel_adapter(semantic)
    assert list(adapter["started_at"].dt.hour) == [9, 21]
    assert list((adapter["finished_at"] - adapter["started_at"]).dt.total_seconds()) == [
        3600.0,
        7200.0,
    ]

    production = pd.DataFrame(
        {"user_id": ["u"], "label": ["HOME"], "location_id": [1]}
    )
    comparator = pd.DataFrame(
        {
            "method": ["FREQ", "FREQ"],
            "user_id": ["u", "u"],
            "label": ["HOME", "OFFICE"],
            "location_id": [1, 0],
        }
    )
    comparison = build_candidate_comparison(["u"], production, comparator)
    assert comparison.loc[comparison["label"].eq("HOME"), "status"].iloc[0] == "both_same"
    assert comparison.loc[comparison["label"].eq("OFFICE"), "status"].iloc[0] == "comparator_only"

    return {
        "status": "ok",
        "adapter_rows": int(len(adapter)),
        "comparison_rows": int(len(comparison)),
    }
