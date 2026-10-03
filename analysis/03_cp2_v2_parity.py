"""Parity/refreeze harness for CP2 v2 timezone-aware Home/Office production."""

from __future__ import annotations

import argparse
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
    }


def _location_key(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.loc[:, ["user_id", "location_id", "latitude", "longitude"]].copy()


def compare_reference(
    production_stays: pd.DataFrame,
    production_locations: pd.DataFrame,
    production_labels: pd.DataFrame,
    reference_stays: pd.DataFrame,
    reference_locations: pd.DataFrame,
    reference_labels: pd.DataFrame,
) -> dict[str, object]:
    prod_stay_keys = set(
        zip(
            production_stays["user_id"].astype(str),
            pd.to_datetime(production_stays["arrival_time_utc"], utc=True),
            pd.to_datetime(production_stays["departure_time_utc"], utc=True),
            strict=True,
        )
    )
    ref_stay_keys = set(
        zip(
            reference_stays["user_id"].astype(str),
            pd.to_datetime(reference_stays["arrival_time_utc"], utc=True),
            pd.to_datetime(reference_stays["departure_time_utc"], utc=True),
            strict=True,
        )
    )

    prod_locations = _location_key(production_locations)
    ref_locations = _location_key(reference_locations)
    location_match = prod_locations.merge(
        ref_locations,
        on=["user_id", "location_id"],
        how="outer",
        suffixes=("_production", "_reference"),
        indicator=True,
    )
    exact_location_rows = location_match.loc[
        location_match["_merge"].eq("both")
        & location_match["latitude_production"].sub(location_match["latitude_reference"]).abs().le(1e-10)
        & location_match["longitude_production"].sub(location_match["longitude_reference"]).abs().le(1e-10)
    ]

    label_cols = ["user_id", "label", "location_id"]
    prod_label_keys = set(map(tuple, production_labels.loc[:, label_cols].astype({"user_id": str}).to_numpy()))
    ref_label_keys = set(map(tuple, reference_labels.loc[:, label_cols].astype({"user_id": str}).to_numpy()))

    return {
        "semantic_stay_exact_match": prod_stay_keys == ref_stay_keys,
        "semantic_stay_only_production": len(prod_stay_keys - ref_stay_keys),
        "semantic_stay_only_reference": len(ref_stay_keys - prod_stay_keys),
        "location_row_count_match": len(production_locations) == len(reference_locations),
        "exact_user_location_rows": int(len(exact_location_rows)),
        "expected_user_location_rows": int(len(location_match.loc[location_match["_merge"].eq("both")])),
        "label_exact_match": prod_label_keys == ref_label_keys,
        "labels_only_production": len(prod_label_keys - ref_label_keys),
        "labels_only_reference": len(ref_label_keys - prod_label_keys),
    }


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
        result["notebook03_parity"] = compare_reference(
            semantic_stays,
            locations,
            labels,
            reference_frames[0],
            reference_frames[1],
            reference_frames[2],
        )

    rendered = json.dumps(result, indent=2, sort_keys=True)
    print(rendered)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
