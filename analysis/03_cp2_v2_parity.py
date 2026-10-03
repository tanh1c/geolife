"""Parity/refreeze harness for CP2 v2 timezone-aware Home/Office production."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import pandas as pd

from geolife.model import HomeOfficeConfig, build_semantic_locations, infer_home_office


EXPECTED_CP1_STAYS = 5_821
EXPECTED_CP1_USERS = 136


def summarize_outputs(
    semantic_stays: pd.DataFrame,
    locations: pd.DataFrame,
    labels: pd.DataFrame,
) -> dict[str, int]:
    recurring = locations.loc[locations["stay_count"].ge(2)]
    return {
        "semantic_users": int(semantic_stays["user_id"].nunique()),
        "semantic_locations": int(len(locations)),
        "recurring_users": int(recurring["user_id"].nunique()),
        "recurring_locations": int(len(recurring)),
        "home_emitted": int(labels["label"].eq("HOME").sum()),
        "office_emitted": int(labels["label"].eq("OFFICE").sum()),
        "unique_emitted_users": int(labels["user_id"].astype(str).nunique()),
    }


def _normalize_utc(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, utc=True)


def _stay_key_frame(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.loc[
        :,
        [
            "user_id",
            "arrival_time_utc",
            "departure_time_utc",
            "latitude",
            "longitude",
        ],
    ].copy()
    out["user_id"] = out["user_id"].astype(str)
    out["arrival_time_utc"] = _normalize_utc(out["arrival_time_utc"])
    out["departure_time_utc"] = _normalize_utc(out["departure_time_utc"])
    out["latitude"] = pd.to_numeric(out["latitude"], errors="raise")
    out["longitude"] = pd.to_numeric(out["longitude"], errors="raise")
    return out


def _stay_key(row) -> tuple[str, str, str, str, str]:
    return (
        str(row.user_id),
        pd.Timestamp(row.arrival_time_utc).isoformat(),
        pd.Timestamp(row.departure_time_utc).isoformat(),
        format(float(row.latitude), ".12f"),
        format(float(row.longitude), ".12f"),
    )


def _stay_key_set(frame: pd.DataFrame) -> set[tuple[str, str, str, str, str]]:
    keys = _stay_key_frame(frame)
    return {_stay_key(row) for row in keys.itertuples(index=False)}


def _cluster_signature_map(
    semantic_stays: pd.DataFrame,
) -> dict[tuple[str, int], str]:
    required = {
        "user_id",
        "location_id",
        "arrival_time_utc",
        "departure_time_utc",
        "latitude",
        "longitude",
    }
    missing = required.difference(semantic_stays.columns)
    if missing:
        raise ValueError(f"semantic stay reference missing columns: {sorted(missing)}")

    normalized = semantic_stays.copy()
    normalized["user_id"] = normalized["user_id"].astype(str)
    normalized["arrival_time_utc"] = _normalize_utc(normalized["arrival_time_utc"])
    normalized["departure_time_utc"] = _normalize_utc(normalized["departure_time_utc"])

    mapping: dict[tuple[str, int], str] = {}
    for (user_id, location_id), group in normalized.groupby(
        ["user_id", "location_id"],
        sort=True,
    ):
        members = sorted(
            _stay_key(row)
            for row in group[
                [
                    "user_id",
                    "arrival_time_utc",
                    "departure_time_utc",
                    "latitude",
                    "longitude",
                ]
            ].itertuples(index=False)
        )
        payload = json.dumps(members, separators=(",", ":"), ensure_ascii=True)
        signature = hashlib.sha256(payload.encode("utf-8")).hexdigest()
        mapping[(str(user_id), int(location_id))] = signature
    return mapping


def _local_wall_time(value) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    if ts.tzinfo is not None:
        return ts.tz_localize(None)
    return ts


def _local_time_parity(
    production_stays: pd.DataFrame,
    reference_stays: pd.DataFrame,
) -> dict[str, object]:
    key_columns = [
        "user_id",
        "arrival_time_utc",
        "departure_time_utc",
        "latitude",
        "longitude",
    ]
    compare_columns = ["timezone_id", "arrival_time_local", "departure_time_local"]

    prod = production_stays.loc[:, key_columns + compare_columns].copy()
    ref = reference_stays.loc[:, key_columns + compare_columns].copy()
    for frame in (prod, ref):
        frame["user_id"] = frame["user_id"].astype(str)
        frame["arrival_time_utc"] = _normalize_utc(frame["arrival_time_utc"])
        frame["departure_time_utc"] = _normalize_utc(frame["departure_time_utc"])
        frame["latitude"] = pd.to_numeric(frame["latitude"], errors="raise")
        frame["longitude"] = pd.to_numeric(frame["longitude"], errors="raise")

    merged = prod.merge(
        ref,
        on=key_columns,
        how="outer",
        suffixes=("_production", "_reference"),
        indicator=True,
    )
    matched = merged.loc[merged["_merge"].eq("both")].copy()
    timezone_match = (
        matched["timezone_id_production"].astype(str)
        == matched["timezone_id_reference"].astype(str)
    )
    arrival_match = [
        _local_wall_time(prod_value) == _local_wall_time(ref_value)
        for prod_value, ref_value in zip(
            matched["arrival_time_local_production"],
            matched["arrival_time_local_reference"],
            strict=True,
        )
    ]
    departure_match = [
        _local_wall_time(prod_value) == _local_wall_time(ref_value)
        for prod_value, ref_value in zip(
            matched["departure_time_local_production"],
            matched["departure_time_local_reference"],
            strict=True,
        )
    ]
    return {
        "matched_stay_rows": int(len(matched)),
        "timezone_id_exact_match": bool(timezone_match.all()),
        "arrival_local_wall_time_exact_match": bool(all(arrival_match)),
        "departure_local_wall_time_exact_match": bool(all(departure_match)),
    }


def _location_membership_parity(
    production_stays: pd.DataFrame,
    reference_stays: pd.DataFrame,
) -> dict[str, object]:
    prod_map = _cluster_signature_map(production_stays)
    ref_map = _cluster_signature_map(reference_stays)
    prod_clusters = {(user_id, signature) for (user_id, _), signature in prod_map.items()}
    ref_clusters = {(user_id, signature) for (user_id, _), signature in ref_map.items()}
    return {
        "location_membership_exact_match": prod_clusters == ref_clusters,
        "clusters_only_production": len(prod_clusters - ref_clusters),
        "clusters_only_reference": len(ref_clusters - prod_clusters),
        "production_cluster_count": len(prod_clusters),
        "reference_cluster_count": len(ref_clusters),
    }


def _label_semantic_keys(
    labels: pd.DataFrame,
    semantic_stays: pd.DataFrame,
) -> set[tuple[str, str, str]]:
    signature_map = _cluster_signature_map(semantic_stays)
    keys: set[tuple[str, str, str]] = set()
    for row in labels.itertuples(index=False):
        lookup = (str(row.user_id), int(row.location_id))
        if lookup not in signature_map:
            raise ValueError(f"label points to missing semantic cluster: {lookup}")
        keys.add((str(row.user_id), str(row.label), signature_map[lookup]))
    return keys


def compare_reference(
    production_stays: pd.DataFrame,
    production_locations: pd.DataFrame,
    production_labels: pd.DataFrame,
    reference_stays: pd.DataFrame,
    reference_locations: pd.DataFrame,
    reference_labels: pd.DataFrame,
) -> dict[str, object]:
    prod_stay_keys = _stay_key_set(production_stays)
    ref_stay_keys = _stay_key_set(reference_stays)

    membership = _location_membership_parity(production_stays, reference_stays)
    local_time = _local_time_parity(production_stays, reference_stays)

    prod_label_keys = _label_semantic_keys(production_labels, production_stays)
    ref_label_keys = _label_semantic_keys(reference_labels, reference_stays)

    reference_recurring = reference_locations.loc[reference_locations["stay_count"].ge(2)]
    summary_match = {
        "semantic_users": int(production_stays["user_id"].nunique())
        == int(reference_stays["user_id"].nunique()),
        "semantic_locations": len(production_locations) == len(reference_locations),
        "recurring_users": int(
            production_locations.loc[
                production_locations["stay_count"].ge(2),
                "user_id",
            ].nunique()
        )
        == int(reference_recurring["user_id"].nunique()),
        "recurring_locations": int(production_locations["stay_count"].ge(2).sum())
        == int(reference_locations["stay_count"].ge(2).sum()),
        "home_emitted": int(production_labels["label"].eq("HOME").sum())
        == int(reference_labels["label"].eq("HOME").sum()),
        "office_emitted": int(production_labels["label"].eq("OFFICE").sum())
        == int(reference_labels["label"].eq("OFFICE").sum()),
    }

    result = {
        "semantic_stay_exact_match": prod_stay_keys == ref_stay_keys,
        "semantic_stay_only_production": len(prod_stay_keys - ref_stay_keys),
        "semantic_stay_only_reference": len(ref_stay_keys - prod_stay_keys),
        **local_time,
        **membership,
        "label_semantic_exact_match": prod_label_keys == ref_label_keys,
        "labels_only_production": len(prod_label_keys - ref_label_keys),
        "labels_only_reference": len(ref_label_keys - prod_label_keys),
        "summary_count_matches": summary_match,
    }
    result["all_parity_checks_pass"] = bool(
        result["semantic_stay_exact_match"]
        and result["timezone_id_exact_match"]
        and result["arrival_local_wall_time_exact_match"]
        and result["departure_local_wall_time_exact_match"]
        and result["location_membership_exact_match"]
        and result["label_semantic_exact_match"]
        and all(summary_match.values())
    )
    return result


def _load_frame(path: Path | None) -> pd.DataFrame | None:
    if path is None:
        return None
    if path.suffix == ".pkl":
        return pd.read_pickle(path)
    if path.suffix == ".parquet":
        return pd.read_parquet(path)
    if path.suffix == ".csv":
        return pd.read_csv(path)
    raise ValueError(f"unsupported reference format: {path}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stays", type=Path, required=True)
    parser.add_argument("--reference-semantic-stays", type=Path)
    parser.add_argument("--reference-locations", type=Path)
    parser.add_argument("--reference-labels", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    stays = pd.read_pickle(args.stays)
    if len(stays) != EXPECTED_CP1_STAYS or stays["user_id"].astype(str).nunique() != EXPECTED_CP1_USERS:
        raise AssertionError(
            f"expected {EXPECTED_CP1_STAYS} stays / {EXPECTED_CP1_USERS} users, "
            f"got {len(stays)} / {stays['user_id'].astype(str).nunique()}"
        )

    config = HomeOfficeConfig(
        clustering_method="complete_link",
        location_max_diameter_m=200.0,
    )
    semantic_stays, locations = build_semantic_locations(stays, config=config)
    labels = infer_home_office(stays, config=config)

    result: dict[str, object] = {
        "production_v2": summarize_outputs(semantic_stays, locations, labels),
        "all_input_stays_timezone_resolved": len(semantic_stays) == len(stays),
    }

    reference_frames = [
        _load_frame(args.reference_semantic_stays),
        _load_frame(args.reference_locations),
        _load_frame(args.reference_labels),
    ]
    if any(frame is not None for frame in reference_frames):
        if not all(frame is not None for frame in reference_frames):
            raise ValueError("provide all three reference artifacts or none")
        reference_stays, reference_locations, reference_labels = reference_frames
        result["notebook03_reference"] = summarize_outputs(
            reference_stays,
            reference_locations,
            reference_labels,
        )
        result["notebook03_parity"] = compare_reference(
            semantic_stays,
            locations,
            labels,
            reference_stays,
            reference_locations,
            reference_labels,
        )

    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
