"""Private mobile/distributed-mobility hypothesis audit over frozen 03a evidence."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import zipfile
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import numpy as np
import pandas as pd

from geolife.geo.distance import haversine_m


BASE_PATH = Path("analysis/03a_user_behavior_deep_dive.py")


ARTIFACT_DIR = Path("artifacts/03b")
FEATURE_ROLES = {
    "construction_only": [
        "weekday usable days",
        "weekday distance",
        "weekday mobility repeatability",
        "recurring daytime locations",
        "no dominant frozen OFFICE",
    ],
    "independent_validation": [
        "mode composition",
        "mode transitions",
        "recurrent L* edges",
        "edge entropy",
        "sensitivity stability",
    ],
    "descriptive_not_independent": ["weekday-weekend movement contrast"],
}


def match_office_abstained_controls(features: pd.DataFrame, baseline_audit: pd.DataFrame) -> pd.DataFrame:
    """Select deterministic same-stratum OFFICE-abstained controls without replacement."""
    office_emitted = set(
        baseline_audit.loc[
            (baseline_audit["label"] == "OFFICE")
            & (baseline_audit["reject_reason"] == "emitted"),
            "user_id",
        ]
    )
    source = features.copy()
    source["office_abstained"] = ~source["user_id"].isin(office_emitted)
    comparable = source.loc[
        source["active_days"].ge(3)
        & source["usable_temporal_days"].ge(1)
        & source["cp1_stay_count"].gt(0)
    ].copy()
    candidates = comparable.loc[comparable["mobile_work_like_candidate"]].copy()
    controls = comparable.loc[
        ~comparable["mobile_work_like_candidate"]
        & comparable["office_abstained"]
        & comparable["recurring_location_count"].ge(3)
    ].copy()
    columns = ["active_days", "usable_temporal_days", "observed_span_h", "cp1_stay_count"]
    for column in columns:
        if column not in source:
            source[column] = 0.0
            candidates[column] = 0.0
            controls[column] = 0.0
    scale = source[columns].std(ddof=0).replace(0, 1.0).fillna(1.0)
    chosen: set[str] = set()
    rows = []
    for candidate in candidates.sort_values("user_id", kind="stable").itertuples(index=False):
        available = controls.loc[~controls["user_id"].isin(chosen)].copy()
        if available.empty:
            continue
        distance = ((available[columns] - pd.Series(candidate._asdict())[columns]) / scale).pow(2).sum(axis=1)
        control = available.assign(_distance=distance).sort_values(["_distance", "user_id"], kind="stable").iloc[0]
        chosen.add(str(control["user_id"]))
        values = candidate._asdict()
        rows.append(
            {
                "candidate_user_id": candidate.user_id,
                "control_user_id": control["user_id"],
                **{f"candidate_{column}": values[column] for column in columns},
                **{f"control_{column}": control[column] for column in columns},
            }
        )
    return pd.DataFrame(rows)


def canonicalize_mode_windows(labels: pd.DataFrame) -> pd.DataFrame:
    """Retain unambiguous half-open labels, excluding positive-duration mode overlap."""
    rows = []
    for user_id, user_labels in labels.groupby("user_id", sort=True):
        boundaries = sorted(set(user_labels["start_time"]) | set(user_labels["end_time"]))
        for start, end in zip(boundaries, boundaries[1:], strict=False):
            active = user_labels.loc[
                (user_labels["start_time"] <= start) & (user_labels["end_time"] >= end), "mode"
            ].unique()
            if len(active) == 1 and start < end:
                rows.append({"user_id": user_id, "start_time": start, "end_time": end, "mode": active[0]})
    windows = pd.DataFrame(rows, columns=["user_id", "start_time", "end_time", "mode"])
    if windows.empty:
        return windows
    merged = []
    for (_, mode), group in windows.groupby(["user_id", "mode"], sort=True):
        group = group.sort_values("start_time", kind="stable")
        current = group.iloc[0].to_dict()
        for row in group.iloc[1:].itertuples(index=False):
            if row.start_time == current["end_time"]:
                current["end_time"] = row.end_time
            else:
                merged.append(current)
                current = row._asdict()
        merged.append(current)
    return pd.DataFrame(merged, columns=["user_id", "start_time", "end_time", "mode"]).sort_values(
        ["user_id", "start_time"], kind="stable", ignore_index=True
    )


def match_mode_segments(segments: pd.DataFrame, windows: pd.DataFrame) -> pd.DataFrame:
    """Match only segments fully contained in one unambiguous half-open mode window."""
    rows = []
    for segment in segments.itertuples(index=False):
        matched = windows.loc[
            (windows["user_id"] == segment.user_id)
            & (windows["start_time"] <= segment.start_time)
            & (windows["end_time"] >= segment.end_time)
        ]
        if len(matched) == 1:
            rows.append({**segment._asdict(), "mode": matched.iloc[0]["mode"]})
    return pd.DataFrame(rows, columns=[*segments.columns, "mode"])


def build_transition_structure(stays: pd.DataFrame, usable_days: pd.DataFrame) -> pd.DataFrame:
    """Measure recurring directed L* transitions from usable days only."""
    supported = usable_days.loc[usable_days["usable_for_motif"], ["user_id", "local_date"]]
    source = stays.merge(supported, on=["user_id", "local_date"], how="inner")
    rows = []
    for user_id, user_stays in source.groupby("user_id", sort=True):
        edges = []
        for _, day in user_stays.groupby("local_date", sort=True):
            locations = day.sort_values("arrival_time_local", kind="stable")["location_id"].tolist()
            edges.extend(
                (f"L{left}→L{right}", day["local_date"].iloc[0])
                for left, right in zip(locations, locations[1:], strict=False)
                if left != right
            )
        edge_days = pd.DataFrame(edges, columns=["edge", "local_date"])
        counts = edge_days["edge"].value_counts() if not edge_days.empty else pd.Series(dtype=int)
        shares = counts / counts.sum() if not counts.empty else pd.Series(dtype=float)
        rows.append(
            {
                "user_id": user_id,
                "transition_count": len(edge_days),
                "distinct_edge_count": len(counts),
                "recurrent_edge_count": int(
                    sum(
                        edge_days.loc[edge_days["edge"] == edge, "local_date"].nunique() >= 2
                        for edge in counts.index
                    )
                )
                if not counts.empty
                else 0,
                "top_edge_frequency": float(shares.iloc[0]) if not shares.empty else 0.0,
                "edge_entropy": float(
                    -(shares[shares > 0] * np.log2(shares[shares > 0])).sum()
                )
                if not shares.empty
                else 0.0,
            }
        )
    return pd.DataFrame(rows)

def summarize_sensitivity(frozen: set[str], variants: dict[str, set[str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "variant": name,
                "candidate_count": len(members),
                "jaccard": len(frozen & members) / len(frozen | members) if frozen | members else 1.0,
                "retained": len(frozen & members),
                "added": len(members - frozen),
                "dropped": len(frozen - members),
            }
            for name, members in variants.items()
        ]
    )


def render_report(summary: dict[str, object]) -> str:
    parity = summary.get("parity", {})
    groups = summary.get("groups", {})
    return f"""# Mobile / distributed-work hypothesis audit

## Status
Research-only audit over frozen 03a evidence; no production classifier or individual semantic label is created.

## EXECUTIVE RESULT
Hypothesis decision: {summary.get('decision', 'mixed evidence')}. The frozen set has {parity.get('candidates', 0)} mobile-work-like candidates, with {parity.get('multiple_anchor', 0)} multiple-anchor, {parity.get('office_abstained', 0)} OFFICE-abstained, and {parity.get('office_emitted', 0)} OFFICE-emitted outcomes (`artifacts/03b/summary.json`).

## GROUP SIZES
Group A has {groups.get('A', 0)} candidates; Group B has {groups.get('B', 0)} matched OFFICE-abstained controls; Group C has {groups.get('C', 0)} fixed-location-like frozen OFFICE comparators (`artifacts/03b/summary.json`).

## INDEPENDENT EVIDENCE
Construction features are separated from independent validation: {', '.join(summary.get('feature_roles', {}).get('independent_validation', [])) or 'none'} (`artifacts/03b/summary.json`).

## TRANSPORT MODE RESULT
Mode results are reported only for transportation-labeled coverage and remain auxiliary movement evidence, never a role assignment (`artifacts/03b/mode_evidence.csv`).

## ROUTE / TRANSITION RESULT
Route evidence uses recurrent abstract `L*→L*` transitions, not coordinates or semantic anchors (`artifacts/03b/route_structure.csv`).

## WEEKDAY VS WEEKEND RESULT
Weekday/weekend contrasts are descriptive because weekday mobility contributes to the frozen wrapper (`artifacts/03b/weekday_weekend.csv`).

## SENSITIVITY RESULT
The frozen Group A remains primary; perturbations report count and Jaccard overlap rather than selecting a favorable variant (`artifacts/03b/sensitivity.csv`).

## NEGATIVE CONTROLS
Sparse, boundary-heavy, travel-heavy, weekend-heavy, and same-stratum controls remain falsification checks (`artifacts/03b/summary.json`).

## WHAT SUPPORTS THE HYPOTHESIS
Only independent evidence that separates Group A from matched controls without recurring in negative controls can support further study.

## WHAT WEAKENS THE HYPOTHESIS
Insufficient label coverage, non-recurrent transitions, sensitivity, or matching imbalance weakens the hypothesis.

## WHAT CANNOT BE CONCLUDED
No individual receives a job-role classification; no true workplace, HOME, accuracy, or semantic POI conclusion is made.

## RECOMMENDED NEXT STEP
Use the aggregate result only to decide whether a distributed-mobility regime warrants further research.

## Q1
Are candidates robust? See `artifacts/03b/sensitivity.csv`.

## Q2
Do candidates differ after matching? See `artifacts/03b/matched_controls.csv`.

## Q3
Do modes differ? See `artifacts/03b/mode_evidence.csv`.

## Q4
Do transitions recur? See `artifacts/03b/route_structure.csv`.

## Q5
Is weekday mobility stronger? See `artifacts/03b/weekday_weekend.csv`.

## Q6
Could controls explain it? See `artifacts/03b/summary.json`.

## Q7
How many have independent support? See `artifacts/03b/summary.json`.

## Q8
How many remain ambiguous? See `artifacts/03b/summary.json`.

## Q9
Does evidence justify further study? See the research-only decision above.

## Q10
What is still needed before a semantic label? External validation and an approved semantic evaluation design.
"""


def _base_module() -> object:
    spec = spec_from_file_location("behavior_03a", BASE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _local_daily(base: object, clustered: pd.DataFrame, point_days: pd.DataFrame) -> pd.DataFrame:
    return base.build_user_day_features(clustered, base._point_days_for_behavior(point_days))


def _weekday_weekend(daily: pd.DataFrame, clustered: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for user_id, days in daily.loc[daily["usable_for_temporal_profile"]].groupby("user_id", sort=True):
        row = {"user_id": user_id}
        for label, mask in (("weekday", days["local_weekday"] < 5), ("weekend", days["local_weekday"] >= 5)):
            subset = days.loc[mask]
            row[f"{label}_usable_days"] = len(subset)
            for column in ("cleaned_distance_km", "movement_duration_proxy_h", "boundary_count"):
                row[f"{label}_{column}"] = float(subset.get(column, pd.Series(dtype=float)).mean()) if len(subset) else np.nan
        row["weekday_weekend_distance_delta"] = row["weekday_cleaned_distance_km"] - row["weekend_cleaned_distance_km"]
        rows.append(row)
    return pd.DataFrame(rows)


def _group_summary(frame: pd.DataFrame, membership: dict[str, set[str]], columns: list[str]) -> dict[str, dict[str, float | int]]:
    result = {}
    for group, users in membership.items():
        subset = frame.loc[frame["user_id"].isin(users)]
        result[group] = {f"median_{column}": float(pd.to_numeric(subset.get(column), errors="coerce").median()) if column in subset else 0.0 for column in columns}
        result[group]["users"] = len(subset)
    return result


def _read_plt(archive: zipfile.ZipFile, member: str) -> pd.DataFrame:
    frame = pd.read_csv(
        io.TextIOWrapper(archive.open(member), encoding="utf-8"),
        skiprows=6,
        header=None,
        names=["latitude", "longitude", "unused", "altitude_ft", "serial_date", "date", "time"],
    )
    frame["timestamp"] = pd.to_datetime(
        frame["date"].astype(str) + " " + frame["time"].astype(str), utc=True, errors="coerce"
    )
    return frame.loc[:, ["timestamp", "latitude", "longitude"]]


def _mode_labels(zip_path: Path, members: set[str]) -> pd.DataFrame:
    rows = []
    with zipfile.ZipFile(zip_path) as archive:
        for name in archive.namelist():
            parts = name.split("/")
            if len(parts) < 2 or parts[-1] != "labels.txt" or parts[-2] not in members:
                continue
            text = io.TextIOWrapper(archive.open(name), encoding="utf-8")
            labels = pd.read_csv(text, skiprows=1, sep=r"\s+", names=["start_date", "start_clock", "end_date", "end_clock", "mode"])
            labels["start_time"] = pd.to_datetime(labels["start_date"] + " " + labels["start_clock"], utc=True, errors="coerce")
            labels["end_time"] = pd.to_datetime(labels["end_date"] + " " + labels["end_clock"], utc=True, errors="coerce")
            labels["user_id"] = parts[-2]
            rows.append(labels.loc[:, ["user_id", "start_time", "end_time", "mode"]])
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["user_id", "start_time", "end_time", "mode"])


def _cleaned_mode_segments(
    base: object,
    zip_path: Path,
    members: set[str],
    windows: pd.DataFrame,
    cache_root: Path,
    *,
    checkpoint_every: int = 25,
) -> pd.DataFrame:
    """Build frozen-CP1-cleaned labeled segments with a private resumable per-file cache."""
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_path = cache_root / "mode_segments_v1.pkl"
    completed_path = cache_root / "mode_segments_completed_v1.json"
    columns = [
        "user_id",
        "start_time",
        "end_time",
        "sequence_id",
        "distance_m",
        "mode",
        "source_key",
    ]
    if cache_path.exists():
        cached = pd.read_pickle(cache_path)
        cached = cached.reindex(columns=columns)
    else:
        cached = pd.DataFrame(columns=columns)
    completed = (
        set(json.loads(completed_path.read_text(encoding="utf-8")))
        if completed_path.exists()
        else set()
    )

    def checkpoint(pending: list[pd.DataFrame]) -> None:
        nonlocal cached
        if pending:
            cached = pd.concat([cached, *pending], ignore_index=True)
            cached = cached.drop_duplicates(
                subset=["source_key", "start_time", "end_time", "sequence_id", "mode"],
                keep="last",
            )
            pending.clear()
        tmp_cache = cache_path.with_suffix(".tmp.pkl")
        cached.to_pickle(tmp_cache)
        tmp_cache.replace(cache_path)
        tmp_completed = completed_path.with_suffix(".tmp.json")
        tmp_completed.write_text(
            json.dumps(sorted(completed), indent=2),
            encoding="utf-8",
        )
        tmp_completed.replace(completed_path)

    user_windows = {
        user_id: frame.sort_values("start_time", kind="stable").reset_index(drop=True)
        for user_id, frame in windows.groupby("user_id", sort=True)
        if user_id in members
    }
    pending: list[pd.DataFrame] = []
    with zipfile.ZipFile(zip_path) as archive:
        source_members = [
            item for item in base._zip_members(archive) if item[0] in members
        ]
        users = sorted({user_id for user_id, _filename, _member in source_members})
        user_position = {user_id: index + 1 for index, user_id in enumerate(users)}
        for file_index, (user_id, _filename, member) in enumerate(source_members, start=1):
            source_key = hashlib.sha256(member.encode("utf-8")).hexdigest()
            if source_key in completed:
                continue
            user_mode_windows = user_windows.get(user_id)
            raw = _read_plt(archive, member)
            timestamps = raw["timestamp"].dropna()
            should_clean = False
            if user_mode_windows is not None and len(timestamps) >= 2:
                raw_start = timestamps.min()
                raw_end = timestamps.max()
                should_clean = bool(
                    (
                        (user_mode_windows["start_time"] < raw_end)
                        & (user_mode_windows["end_time"] > raw_start)
                    ).any()
                )
            if should_clean:
                cleaned, _audit = base.clean_trajectory_with_audit(
                    raw, **base.FROZEN_CLEANING_KWARGS
                )
                if len(cleaned) >= 2:
                    segment = cleaned.assign(
                        start_time=cleaned["timestamp"].shift(),
                        start_latitude=cleaned["latitude"].shift(),
                        start_longitude=cleaned["longitude"].shift(),
                        start_sequence=cleaned["sequence_id"].shift(),
                    ).iloc[1:].copy()
                    segment = segment.loc[
                        (segment["sequence_id"] == segment["start_sequence"])
                        & (segment["timestamp"] > segment["start_time"])
                    ]
                    if not segment.empty:
                        segment["user_id"] = user_id
                        segment["end_time"] = segment["timestamp"]
                        segment["distance_m"] = haversine_m(
                            segment["start_latitude"].to_numpy(),
                            segment["start_longitude"].to_numpy(),
                            segment["latitude"].to_numpy(),
                            segment["longitude"].to_numpy(),
                        )
                        matched = match_mode_segments(
                            segment.loc[
                                :,
                                [
                                    "user_id",
                                    "start_time",
                                    "end_time",
                                    "sequence_id",
                                    "distance_m",
                                ],
                            ],
                            user_mode_windows,
                        )
                        if not matched.empty:
                            matched["source_key"] = source_key
                            pending.append(matched.reindex(columns=columns))
            completed.add(source_key)
            if file_index % checkpoint_every == 0:
                checkpoint(pending)
                print(
                    "mode segments: "
                    f"user {user_position[user_id]}/{len(users)}, "
                    f"file {file_index}/{len(source_members)}, "
                    f"cached segments {len(cached)}"
                )
        checkpoint(pending)
    result = cached.loc[cached["user_id"].isin(members)].copy()
    return result.drop(columns=["source_key"], errors="ignore").reset_index(drop=True)

def _mode_summary(segments: pd.DataFrame, membership: dict[str, set[str]], windows: pd.DataFrame) -> pd.DataFrame:
    member_rows = pd.DataFrame(
        [(user_id, group) for group, users in membership.items() for user_id in users],
        columns=["user_id", "group"],
    )
    label_duration = windows.assign(
        label_duration_h=(windows["end_time"] - windows["start_time"]).dt.total_seconds() / 3600
    ).merge(member_rows, on="user_id", how="inner")
    observed = segments.assign(
        observed_duration_h=(segments["end_time"] - segments["start_time"]).dt.total_seconds() / 3600
    ).merge(member_rows, on="user_id", how="inner")
    rows = []
    for group in membership:
        labels = label_duration.loc[label_duration["group"] == group]
        matched = observed.loc[observed["group"] == group]
        per_user_labels = labels.groupby("user_id")["label_duration_h"].sum()
        per_user_matched = matched.groupby("user_id").agg(
            duration_h=("observed_duration_h", "sum"), distance_km=("distance_m", lambda values: values.sum() / 1000)
        )
        total_distance = float(matched["distance_m"].sum())
        mode_distance = matched.groupby("mode")["distance_m"].sum() if not matched.empty else pd.Series(dtype=float)
        modes = {mode: float(value / total_distance) if total_distance else 0.0 for mode, value in mode_distance.items()}
        rows.append(
            {
                "group": group,
                "label_users": labels["user_id"].nunique(),
                "median_labeled_duration_h_per_user": float(per_user_labels.median()) if not per_user_labels.empty else 0.0,
                "canonical_labeled_duration_h": float(labels["label_duration_h"].sum()),
                "matched_users": matched["user_id"].nunique(),
                "median_matched_duration_h_per_user": float(per_user_matched["duration_h"].median()) if not per_user_matched.empty else 0.0,
                "median_matched_distance_km_per_user": float(per_user_matched["distance_km"].median()) if not per_user_matched.empty else 0.0,
                "matched_duration_h": float(matched["observed_duration_h"].sum()),
                "matched_distance_km": total_distance / 1000,
                "active_mode_distance_share": sum(modes.get(mode, 0.0) for mode in ("walk", "bike", "run")),
                "motorized_mode_distance_share": sum(modes.get(mode, 0.0) for mode in ("bus", "car", "taxi", "subway", "train", "motorcycle")),
                "mode_transitions": int(matched.sort_values(["user_id", "start_time"]).groupby("user_id")["mode"].apply(lambda values: values.ne(values.shift()).sum() - 1).clip(lower=0).sum()) if not matched.empty else 0,
            }
        )
    return pd.DataFrame(rows)


def _perturbed_candidates(
    features: pd.DataFrame, *, distance_factor: float = 1.0, weekday_minimum: int = 5
) -> set[str]:
    """Rerun the frozen wrapper expression with one declared threshold perturbation."""
    threshold = float(features["weekday_distance_km"].quantile(0.75)) * distance_factor
    selected = features.loc[
        features["weekday_usable_days"].ge(weekday_minimum)
        & features["weekday_mobility_repeatability"].ge(0.75)
        & features["weekday_distance_km"].ge(threshold)
        & features["recurring_daytime_locations"].ge(2)
        & ~features["office_dominant"]
    ]
    return set(selected["user_id"])


def _candidate_features_for_anchor(
    base: object,
    resolved: pd.DataFrame,
    point_days: pd.DataFrame,
    baseline: pd.DataFrame,
    threshold_m: float,
) -> pd.DataFrame:
    """Recompute clustering-dependent candidate inputs at a declared anchor threshold."""
    clustered, _ = base.cluster_behavior_locations(resolved, threshold_m)
    daily = _local_daily(base, clustered, point_days)
    features = base.build_user_behavior_features(
        clustered, base._point_days_for_behavior(point_days)
    )
    features = base._enrich_features(
        features,
        daily,
        base.compute_schedule_stability(daily),
        baseline,
    )
    return base.assign_behavioral_candidates(features)


def _support_balance(
    features: pd.DataFrame,
    membership: dict[str, set[str]],
    matched: pd.DataFrame,
) -> pd.DataFrame:
    columns = ["active_days", "usable_temporal_days", "observed_span_h", "cp1_stay_count"]
    rows = []
    for group, users in membership.items():
        subset = features.loc[features["user_id"].isin(users)]
        row: dict[str, object] = {"group": group, "users": len(subset)}
        for column in columns:
            values = pd.to_numeric(subset[column], errors="coerce").dropna()
            row[f"{column}_median"] = float(values.median()) if not values.empty else np.nan
            row[f"{column}_q25"] = float(values.quantile(0.25)) if not values.empty else np.nan
            row[f"{column}_q75"] = float(values.quantile(0.75)) if not values.empty else np.nan
        rows.append(row)
    matched_a = set(matched.get("candidate_user_id", pd.Series(dtype=str)))
    group_a = membership.get("A", set())
    rows.append(
        {
            "group": "A_matching_status",
            "users": len(group_a),
            "matched_pairs": len(matched),
            "unmatched_A": len(group_a - matched_a),
        }
    )
    return pd.DataFrame(rows)


def _negative_controls(
    features: pd.DataFrame,
    contrasts: pd.DataFrame,
    transitions: pd.DataFrame,
    candidates: set[str],
    group_b: set[str],
) -> pd.DataFrame:
    """Summarize falsification cohorts without assigning semantic labels."""
    non_candidates = set(features.loc[~features["user_id"].isin(candidates), "user_id"])
    support = pd.to_numeric(features["usable_temporal_days"], errors="coerce").fillna(0)
    distance = pd.to_numeric(
        features["distance_per_usable_day_km"], errors="coerce"
    ).fillna(0)
    supported_non_candidates = features.loc[
        features["user_id"].isin(non_candidates) & support.ge(6)
    ]
    travel_cutoff = float(
        pd.to_numeric(
            supported_non_candidates["distance_per_usable_day_km"], errors="coerce"
        ).quantile(0.9)
    ) if not supported_non_candidates.empty else np.inf
    weekend_ids = set(
        contrasts.loc[
            contrasts["weekday_weekend_distance_delta"].lt(0), "user_id"
        ]
    )
    sets = {
        "sparse_or_low_support": set(features.loc[support.lt(6), "user_id"]) - candidates,
        "boundary_heavy": set(
            features.loc[
                pd.to_numeric(features["cp1_boundary_count"], errors="coerce").fillna(0).gt(0),
                "user_id",
            ]
        ) - candidates,
        "travel_heavy_non_candidate": set(
            features.loc[distance.ge(travel_cutoff), "user_id"]
        ) - candidates,
        "weekend_heavy": weekend_ids - candidates,
        "matched_multiple_anchor_office_abstained": set(group_b),
    }
    joined = features.merge(
        transitions,
        on="user_id",
        how="left",
        validate="one_to_one",
    ).merge(
        contrasts.loc[:, ["user_id", "weekday_weekend_distance_delta"]],
        on="user_id",
        how="left",
        validate="one_to_one",
    )
    rows = []
    for name, users in sets.items():
        subset = joined.loc[joined["user_id"].isin(users)]
        rows.append(
            {
                "control": name,
                "users": len(users),
                "median_distance_per_usable_day_km": float(
                    pd.to_numeric(
                        subset["distance_per_usable_day_km"], errors="coerce"
                    ).median()
                )
                if not subset.empty
                else np.nan,
                "median_recurrent_edge_count": float(
                    pd.to_numeric(
                        subset.get("recurrent_edge_count"), errors="coerce"
                    ).median()
                )
                if not subset.empty
                else np.nan,
                "median_edge_entropy": float(
                    pd.to_numeric(subset.get("edge_entropy"), errors="coerce").median()
                )
                if not subset.empty
                else np.nan,
                "median_weekday_weekend_distance_delta": float(
                    pd.to_numeric(
                        subset.get("weekday_weekend_distance_delta"), errors="coerce"
                    ).median()
                )
                if not subset.empty
                else np.nan,
            }
        )
    return pd.DataFrame(rows)

def run_audit(zip_path: Path, root: Path, *, seed: int) -> dict[str, object]:
    base = _base_module()
    stays, point_days = base.materialize_frozen_cp1(zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        release_users = base._release_users(archive)
    baseline = base.build_baseline_user_audit(release_users, stays)
    resolved = base.resolve_stay_timezones(stays).dropna(subset=["timezone_id"])

    candidates = _candidate_features_for_anchor(
        base, resolved, point_days, baseline, 200.0
    )
    office = baseline.loc[baseline["label"].eq("OFFICE")]
    group_a = set(
        candidates.loc[candidates["mobile_work_like_candidate"], "user_id"]
    )
    parity = {
        "candidates": len(group_a),
        "multiple_anchor": int(
            candidates.loc[
                candidates["user_id"].isin(group_a), "recurring_location_count"
            ].ge(3).sum()
        ),
        "office_abstained": int(
            office.loc[
                office["user_id"].isin(group_a), "reject_reason"
            ].ne("emitted").sum()
        ),
        "office_emitted": int(
            office.loc[
                office["user_id"].isin(group_a), "reject_reason"
            ].eq("emitted").sum()
        ),
    }
    assert parity == {
        "candidates": 23,
        "multiple_anchor": 23,
        "office_abstained": 23,
        "office_emitted": 0,
    }

    clustered, _ = base.cluster_behavior_locations(resolved, 200.0)
    daily = _local_daily(base, clustered, point_days)
    matched = match_office_abstained_controls(candidates, baseline)
    group_b = set(matched["control_user_id"])
    basic_support = set(
        candidates.loc[
            candidates["active_days"].ge(3)
            & candidates["usable_temporal_days"].ge(1)
            & candidates["cp1_stay_count"].gt(0),
            "user_id",
        ]
    )
    group_c = set(
        office.loc[
            (office["reject_reason"] == "emitted")
            & office["user_id"].isin(basic_support),
            "user_id",
        ]
    )
    membership = {"A": group_a, "B": group_b, "C": group_c}

    usable = daily.loc[:, ["user_id", "local_date", "usable_for_motif"]]
    transitions = build_transition_structure(clustered, usable)
    contrasts = _weekday_weekend(daily, clustered)
    support_balance = _support_balance(candidates, membership, matched)

    labels = _mode_labels(zip_path, set().union(*membership.values()))
    windows = canonicalize_mode_windows(labels)
    private = root / ARTIFACT_DIR
    private.mkdir(parents=True, exist_ok=True)
    segments = _cleaned_mode_segments(
        base,
        zip_path,
        set().union(*membership.values()),
        windows,
        private / "mode_segment_cache",
    )
    mode_summary = _mode_summary(segments, membership, windows)

    candidates_100 = _candidate_features_for_anchor(
        base, resolved, point_days, baseline, 100.0
    )
    candidates_300 = _candidate_features_for_anchor(
        base, resolved, point_days, baseline, 300.0
    )
    variants = {
        "frozen_200m": group_a,
        "anchor_100m": set(
            candidates_100.loc[
                candidates_100["mobile_work_like_candidate"], "user_id"
            ]
        ),
        "anchor_300m": set(
            candidates_300.loc[
                candidates_300["mobile_work_like_candidate"], "user_id"
            ]
        ),
        "mobility_threshold_minus_10pct": _perturbed_candidates(
            candidates, distance_factor=0.9, weekday_minimum=5
        ),
        "mobility_threshold_plus_10pct": _perturbed_candidates(
            candidates, distance_factor=1.1, weekday_minimum=5
        ),
        "support_minus_1_weekday": _perturbed_candidates(
            candidates, distance_factor=1.0, weekday_minimum=4
        ),
        "support_plus_1_weekday": _perturbed_candidates(
            candidates, distance_factor=1.0, weekday_minimum=6
        ),
    }
    assert variants["frozen_200m"] == _perturbed_candidates(
        candidates, distance_factor=1.0, weekday_minimum=5
    )
    sensitivity = summarize_sensitivity(group_a, variants)
    controls = _negative_controls(
        candidates, contrasts, transitions, group_a, group_b
    )

    membership_frame = pd.DataFrame(
        [
            (user, group)
            for group, users in membership.items()
            for user in sorted(users)
        ],
        columns=["user_id", "group"],
    )
    membership_frame.to_csv(private / "group_membership.csv", index=False)
    matched.to_csv(private / "matched_controls.csv", index=False)
    support_balance.to_csv(private / "support_balance.csv", index=False)
    mode_summary.to_csv(private / "mode_evidence.csv", index=False)
    transitions.merge(
        membership_frame, on="user_id", how="inner"
    ).to_csv(private / "route_structure.csv", index=False)
    contrasts.merge(
        membership_frame, on="user_id", how="inner"
    ).to_csv(private / "weekday_weekend.csv", index=False)
    sensitivity.to_csv(private / "sensitivity.csv", index=False)
    controls.to_csv(private / "negative_controls.csv", index=False)

    summary = {
        "run_status": "complete",
        "seed": seed,
        "parity": parity,
        "groups": {key: len(value) for key, value in membership.items()},
        "feature_roles": FEATURE_ROLES,
        "support_balance": support_balance.to_dict("records"),
        "transport_mode": mode_summary.to_dict("records"),
        "transition_summary": _group_summary(
            transitions,
            membership,
            [
                "transition_count",
                "recurrent_edge_count",
                "top_edge_frequency",
                "edge_entropy",
            ],
        ),
        "weekday_weekend": _group_summary(
            contrasts, membership, ["weekday_weekend_distance_delta"]
        ),
        "sensitivity": sensitivity.to_dict("records"),
        "negative_controls": controls.to_dict("records"),
        "decision": "mixed evidence",
    }
    (private / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (root / "reports" / "03b_mobile_work_hypothesis_audit.md").write_text(
        render_report(summary),
        encoding="utf-8",
    )
    return summary

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    summary = run_audit(args.zip, Path.cwd(), seed=args.seed)
    print(f"validated frozen 03a parity: {summary['parity']}")
    print(f"03b hypothesis decision: {summary['decision']}")


if __name__ == "__main__":
    main()
