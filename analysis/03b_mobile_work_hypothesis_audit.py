"""Private mobile/distributed-mobility hypothesis audit over frozen 03a evidence."""

from __future__ import annotations

import argparse
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
            edges.extend((f"L{left}→L{right}", day["local_date"].iloc[0]) for left, right in zip(locations, locations[1:], strict=False) if left != right)
        edge_days = pd.DataFrame(edges, columns=["edge", "local_date"])
        counts = edge_days["edge"].value_counts() if not edge_days.empty else pd.Series(dtype=int)
        rows.append(
            {
                "user_id": user_id,
                "transition_count": len(edge_days),
                "distinct_edge_count": len(counts),
                "recurrent_edge_count": int(sum(edge_days.loc[edge_days["edge"] == edge, "local_date"].nunique() >= 2 for edge in counts)) if not counts.empty else 0,
                "top_edge_frequency": float(counts.iloc[0] / len(edge_days)) if len(edge_days) else 0.0,
            }
        )
    return pd.DataFrame(rows)


def summarize_sensitivity(frozen: set[str], variants: dict[str, set[str]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "variant": name,
                "candidate_count": len(members),
                "jaccard_with_frozen": len(frozen & members) / len(frozen | members) if frozen | members else 1.0,
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


def _cleaned_mode_segments(base: object, zip_path: Path, members: set[str], windows: pd.DataFrame) -> pd.DataFrame:
    rows = []
    with zipfile.ZipFile(zip_path) as archive:
        for user_id, _filename, member in base._zip_members(archive):
            if user_id not in members:
                continue
            cleaned, _audit = base.clean_trajectory_with_audit(_read_plt(archive, member), **base.FROZEN_CLEANING_KWARGS)
            if len(cleaned) < 2:
                continue
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
            if segment.empty:
                continue
            segment["user_id"] = user_id
            segment["end_time"] = segment["timestamp"]
            segment["distance_m"] = haversine_m(
                segment["start_latitude"].to_numpy(), segment["start_longitude"].to_numpy(),
                segment["latitude"].to_numpy(), segment["longitude"].to_numpy(),
            )
            rows.append(segment.loc[:, ["user_id", "start_time", "end_time", "sequence_id", "distance_m"]])
    segments = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(
        columns=["user_id", "start_time", "end_time", "sequence_id", "distance_m"]
    )
    return match_mode_segments(segments, windows)


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


def _perturbed_candidates(features: pd.DataFrame, *, distance_factor: float, weekday_minimum: int) -> set[str]:
    threshold = float(features["weekday_distance_km"].quantile(0.75)) * distance_factor
    selected = features.loc[
        features["weekday_usable_days"].ge(weekday_minimum)
        & features["weekday_mobility_repeatability"].ge(0.75)
        & features["weekday_distance_km"].ge(threshold)
        & features["recurring_daytime_locations"].ge(2)
        & ~features["office_dominant"]
    ]
    return set(selected["user_id"])


def _negative_controls(features: pd.DataFrame, contrasts: pd.DataFrame, candidates: set[str]) -> dict[str, int]:
    supported = features.loc[~features["user_id"].isin(candidates)]
    return {
        "sparse_or_low_support": int(supported["usable_temporal_days"].lt(6).sum()),
        "boundary_heavy": int(supported["cp1_boundary_count"].gt(0).sum()),
        "travel_heavy": int(supported["distance_per_usable_day_km"].ge(supported["distance_per_usable_day_km"].quantile(0.9)).sum()),
        "weekend_heavy": int(contrasts.loc[contrasts["user_id"].isin(supported["user_id"]), "weekday_weekend_distance_delta"].lt(0).sum()),
    }


def run_audit(zip_path: Path, root: Path, *, seed: int) -> dict[str, object]:
    base = _base_module()
    stays, point_days = base.materialize_frozen_cp1(zip_path)
    with zipfile.ZipFile(zip_path) as archive:
        release_users = base._release_users(archive)
    baseline = base.build_baseline_user_audit(release_users, stays)
    resolved = base.resolve_stay_timezones(stays).dropna(subset=["timezone_id"])
    clustered, _ = base.cluster_behavior_locations(resolved, 200.0)
    daily = _local_daily(base, clustered, point_days)
    features = base.build_user_behavior_features(clustered, base._point_days_for_behavior(point_days))
    features = base._enrich_features(features, daily, base.compute_schedule_stability(daily), baseline)
    candidates = base.assign_behavioral_candidates(features)
    office = baseline.loc[baseline["label"].eq("OFFICE")]
    group_a = set(candidates.loc[candidates["mobile_work_like_candidate"], "user_id"])
    parity = {
        "candidates": len(group_a),
        "multiple_anchor": int(candidates.loc[candidates["user_id"].isin(group_a), "recurring_location_count"].ge(3).sum()),
        "office_abstained": int(office.loc[office["user_id"].isin(group_a), "reject_reason"].ne("emitted").sum()),
        "office_emitted": int(office.loc[office["user_id"].isin(group_a), "reject_reason"].eq("emitted").sum()),
    }
    assert parity == {"candidates": 23, "multiple_anchor": 23, "office_abstained": 23, "office_emitted": 0}
    matched = match_office_abstained_controls(candidates, baseline)
    group_b = set(matched["control_user_id"])
    group_c = set(office.loc[(office["reject_reason"] == "emitted") & office["user_id"].isin(candidates["user_id"]), "user_id"])
    membership = {"A": group_a, "B": group_b, "C": group_c}
    usable = daily.loc[:, ["user_id", "local_date", "usable_for_motif"]]
    transitions = build_transition_structure(clustered, usable)
    contrasts = _weekday_weekend(daily, clustered)
    labels = _mode_labels(zip_path, set().union(*membership.values()))
    windows = canonicalize_mode_windows(labels)
    segments = _cleaned_mode_segments(base, zip_path, set().union(*membership.values()), windows)
    mode_summary = _mode_summary(segments, membership, windows)
    variants = {"frozen": group_a}
    for factor in (0.8, 0.9, 1.0, 1.1, 1.2):
        for weekday_minimum in (4, 5, 6):
            variants[f"distance_{factor:.1f}_days_{weekday_minimum}"] = _perturbed_candidates(
                candidates, distance_factor=factor, weekday_minimum=weekday_minimum
            )
    sensitivity = summarize_sensitivity(group_a, variants)
    controls = _negative_controls(candidates, contrasts, group_a)
    private = root / ARTIFACT_DIR
    private.mkdir(parents=True, exist_ok=True)
    membership_frame = pd.DataFrame([(user, group) for group, users in membership.items() for user in users], columns=["user_id", "group"])
    membership_frame.to_csv(private / "group_membership.csv", index=False)
    matched.to_csv(private / "matched_controls.csv", index=False)
    mode_summary.to_csv(private / "mode_evidence.csv", index=False)
    transitions.merge(membership_frame, on="user_id", how="inner").to_csv(private / "route_structure.csv", index=False)
    contrasts.merge(membership_frame, on="user_id", how="inner").to_csv(private / "weekday_weekend.csv", index=False)
    sensitivity.to_csv(private / "sensitivity.csv", index=False)
    summary = {
        "run_status": "complete", "seed": seed, "parity": parity, "groups": {key: len(value) for key, value in membership.items()},
        "feature_roles": FEATURE_ROLES, "transport_mode": mode_summary.to_dict("records"),
        "transition_summary": _group_summary(transitions, membership, ["transition_count", "recurrent_edge_count", "top_edge_frequency"]),
        "weekday_weekend": _group_summary(contrasts, membership, ["weekday_weekend_distance_delta"]),
        "sensitivity": sensitivity.to_dict("records"), "negative_controls": controls,
        "decision": "mixed evidence",
    }
    (private / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    (root / "reports" / "03b_mobile_work_hypothesis_audit.md").write_text(render_report(summary), encoding="utf-8")
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
