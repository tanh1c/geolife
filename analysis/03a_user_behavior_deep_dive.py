"""Private materialization for the behavior-first GeoLife EDA."""

from __future__ import annotations

import argparse
import io
import os
import re
import tempfile
import zipfile
from pathlib import Path

import numpy as np
import pandas as pd

from geolife.geo.distance import haversine_m
from geolife.staypoints import clean_trajectory_with_audit, detect_staypoints

ARTIFACT_DIR = Path("artifacts/03a")
STAY_CACHE = ARTIFACT_DIR / "stays_baseline_v1.pkl"
POINT_DAY_CACHE = ARTIFACT_DIR / "cleaned_point_daily_metrics.pkl"
EXPECTED_STAYS = 5_821
EXPECTED_STAY_USERS = 136
EXPECTED_RELEASE_USERS = 182
CHECKPOINT_EVERY = 500
FROZEN_CP1 = {
    "same_second_radius_m": 10.0,
    "max_gap_s": 300.0,
    "hard_speed_guard_kmh": 1200.0,
    "distance_threshold_m": 200.0,
    "min_dwell_s": 1200.0,
}
FROZEN_CLEANING_KWARGS = {
    key: FROZEN_CP1[key]
    for key in ("same_second_radius_m", "max_gap_s", "hard_speed_guard_kmh")
}
FROZEN_STAY_KWARGS = {
    key: FROZEN_CP1[key] for key in ("distance_threshold_m", "min_dwell_s")
}
STAY_COLUMNS = [
    "user_id",
    "source_file",
    "sequence_id",
    "arrival_time_utc",
    "departure_time_utc",
    "duration_s",
    "latitude",
    "longitude",
    "n_points",
]
POINT_DAY_COLUMNS = [
    "user_id",
    "local_date",
    "point_count",
    "observed_span_s",
    "largest_gap_s",
    "has_large_gap",
    "cleaned_travel_distance_m",
    "movement_duration_s",
    "transition_count",
    "first_observed_hour",
    "last_observed_hour",
    "hour_coverage_count",
]
_MEMBER_RE = re.compile(r"(?:^|/)Data/(\d{3})/Trajectory/([^/]+\.plt)$")


def ensure_private_artifact_path(path: Path) -> None:
    """Reject EDA artifact writes outside the private artifact directory."""
    try:
        path.resolve().relative_to(ARTIFACT_DIR.resolve())
    except ValueError as error:
        raise ValueError("private artifacts must be written beneath artifacts/03a") from error


_POINT_DAY_HELPER_COLUMNS = ["_first_timestamp", "_last_timestamp", "_observed_hours"]


def _point_day_columns(*, include_helpers: bool = False) -> list[str]:
    return POINT_DAY_COLUMNS + (_POINT_DAY_HELPER_COLUMNS if include_helpers else [])


# CP1 audit rows are allocated to the UTC-local day of their event timestamp.
# This preserves terminal/discarded events that no retained row can carry.
def _audit_counts_by_day(audit: pd.DataFrame) -> pd.Series:
    if audit.empty:
        return pd.Series(dtype="int64")
    return audit.groupby(audit["timestamp"].dt.date, sort=True).size()


def _aggregate_point_days(point_days: pd.DataFrame) -> pd.DataFrame:
    """Merge per-PLT daily aggregates into exactly one row per user and day."""
    if point_days.empty:
        return _empty_point_days()

    rows = []
    for (user_id, local_date), day in point_days.groupby(["user_id", "local_date"], sort=True):
        first = day["_first_timestamp"].min()
        last = day["_last_timestamp"].max()
        rows.append(
            {
                "user_id": user_id,
                "local_date": local_date,
                "point_count": int(day["point_count"].sum()),
                "observed_span_s": float((last - first).total_seconds()) if pd.notna(first) else 0.0,
                "largest_gap_s": float(day["largest_gap_s"].max()),
                "has_large_gap": bool(day["has_large_gap"].any()),
                "cleaned_travel_distance_m": float(day["cleaned_travel_distance_m"].sum()),
                "movement_duration_s": float(day["movement_duration_s"].sum()),
                "transition_count": int(day["transition_count"].sum()),
                "first_observed_hour": int(day["first_observed_hour"].min()) if pd.notna(first) else pd.NA,
                "last_observed_hour": int(day["last_observed_hour"].max()) if pd.notna(last) else pd.NA,
                "hour_coverage_count": len({hour for hours in day["_observed_hours"] for hour in hours}),
            }
        )
    return pd.DataFrame(rows, columns=POINT_DAY_COLUMNS)


def _empty_stays() -> pd.DataFrame:
    return pd.DataFrame(columns=STAY_COLUMNS)


def _empty_point_days() -> pd.DataFrame:
    return pd.DataFrame(columns=POINT_DAY_COLUMNS)


def process_trajectory(
    user_id: str, source_file: str, raw: pd.DataFrame
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Apply frozen CP1 once and retain only stay and daily aggregate outputs."""
    cleaned, audit = clean_trajectory_with_audit(raw, **FROZEN_CLEANING_KWARGS)
    detected = detect_staypoints(cleaned, **FROZEN_STAY_KWARGS)

    if detected.empty:
        stays = _empty_stays()
    else:
        stays = detected.rename(
            columns={"arrival_time": "arrival_time_utc", "departure_time": "departure_time_utc"}
        ).assign(user_id=user_id, source_file=source_file)
        stays = stays.loc[:, STAY_COLUMNS]

    if cleaned.empty:
        return stays, _empty_point_days()

    points = cleaned.copy()
    points["local_date"] = points["timestamp"].dt.date
    points["local_hour"] = points["timestamp"].dt.hour
    audit_counts = _audit_counts_by_day(audit)
    rows = []
    for local_date, day in points.groupby("local_date", sort=True):
        timestamps = day["timestamp"]
        gaps = timestamps.diff().dt.total_seconds().iloc[1:]
        lat = day["latitude"].to_numpy(dtype=float)
        lon = day["longitude"].to_numpy(dtype=float)
        sequence_id = day["sequence_id"].to_numpy()
        if len(day) > 1:
            segments = np.asarray(haversine_m(lat[:-1], lon[:-1], lat[1:], lon[1:]), dtype=float)
            positive_same_sequence = (gaps.to_numpy(dtype=float) > 0) & (sequence_id[1:] == sequence_id[:-1])
            travel_m = float(segments[positive_same_sequence].sum())
            movement_duration_s = float(gaps.to_numpy(dtype=float)[positive_same_sequence].sum())
        else:
            travel_m = 0.0
            movement_duration_s = 0.0
        rows.append(
            {
                "user_id": user_id,
                "local_date": local_date,
                "point_count": len(day),
                "observed_span_s": float((timestamps.max() - timestamps.min()).total_seconds()),
                "largest_gap_s": float(gaps.max()) if not gaps.empty else 0.0,
                "has_large_gap": bool((gaps > 6 * 3600).any()),
                "cleaned_travel_distance_m": travel_m,
                "movement_duration_s": movement_duration_s,
                "transition_count": int(audit_counts.get(local_date, 0)),
                "first_observed_hour": int(day["local_hour"].min()),
                "last_observed_hour": int(day["local_hour"].max()),
                "hour_coverage_count": int(day["local_hour"].nunique()),
                "_first_timestamp": timestamps.min(),
                "_last_timestamp": timestamps.max(),
                "_observed_hours": frozenset(day["local_hour"]),
            }
        )
    return stays, pd.DataFrame(rows, columns=_point_day_columns(include_helpers=True))


def validate_materialization(
    stays: pd.DataFrame, point_days: pd.DataFrame, release_users: set[str]
) -> None:
    """Validate the frozen CP1 reconciliation before any cache is accepted."""
    assert len(release_users) == EXPECTED_RELEASE_USERS, (
        f"expected {EXPECTED_RELEASE_USERS} release users, got {len(release_users)}"
    )
    assert len(stays) == EXPECTED_STAYS, (
        f"expected {EXPECTED_STAYS:,} stays, got {len(stays):,}"
    )
    assert stays["user_id"].nunique() == EXPECTED_STAY_USERS, (
        f"expected {EXPECTED_STAY_USERS} users with a stay, got {stays['user_id'].nunique()}"
    )
    assert set(stays["user_id"]).issubset(release_users)
    assert set(point_days["user_id"]).issubset(release_users)
    assert not point_days.duplicated(["user_id", "local_date"]).any(), (
        "expected exactly one row per user and local date"
    )


def _write_pickle_atomically(frame: pd.DataFrame, path: Path) -> None:
    ensure_private_artifact_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as tmp:
        temporary_path = Path(tmp.name)
    try:
        frame.to_pickle(temporary_path)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def _zip_members(archive: zipfile.ZipFile) -> list[tuple[str, str, str]]:
    members = []
    for name in archive.namelist():
        match = _MEMBER_RE.search(name)
        if match:
            members.append((match.group(1), match.group(2), name))
    return sorted(members)


def _release_users(archive: zipfile.ZipFile) -> set[str]:
    return {
        match.group(1)
        for name in archive.namelist()
        if (match := re.search(r"(?:^|/)Data/(\d{3})(?:/|$)", name))
    }


def _read_zip_plt(archive: zipfile.ZipFile, member: str) -> pd.DataFrame:
    with archive.open(member) as raw_file:
        text = io.TextIOWrapper(raw_file, encoding="utf-8")
        frame = pd.read_csv(
            text,
            skiprows=6,
            header=None,
            names=["latitude", "longitude", "unused", "altitude_ft", "serial_date", "date", "time"],
        )
    frame["timestamp"] = pd.to_datetime(
        frame["date"].astype(str) + " " + frame["time"].astype(str),
        format="%Y-%m-%d %H:%M:%S",
        errors="coerce",
        utc=True,
    )
    return frame.loc[:, ["timestamp", "latitude", "longitude"]]


def materialize_frozen_cp1(
    zip_path: Path, stay_cache: Path = STAY_CACHE, point_day_cache: Path = POINT_DAY_CACHE
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Materialize private frozen-CP1 caches from the release ZIP."""
    ensure_private_artifact_path(stay_cache)
    ensure_private_artifact_path(point_day_cache)
    with zipfile.ZipFile(zip_path) as archive:
        release_users = _release_users(archive)
        if stay_cache.exists() and point_day_cache.exists():
            # These private caches are created locally by this runner; do not load untrusted pickles.
            stays = pd.read_pickle(stay_cache)
            point_days = pd.read_pickle(point_day_cache)
            try:
                validate_materialization(stays, point_days, release_users)
            except AssertionError:
                pass
            else:
                return stays, point_days

        stay_parts: list[pd.DataFrame] = []
        point_day_parts: list[pd.DataFrame] = []
        members = _zip_members(archive)
        for index, (user_id, _filename, member) in enumerate(members, start=1):
            stays, point_days = process_trajectory(user_id, member, _read_zip_plt(archive, member))
            if not stays.empty:
                stay_parts.append(stays)
            if not point_days.empty:
                point_day_parts.append(point_days)
            if index % CHECKPOINT_EVERY == 0:
                _write_pickle_atomically(
                    pd.concat(stay_parts, ignore_index=True) if stay_parts else _empty_stays(), stay_cache
                )
                _write_pickle_atomically(
                    pd.concat(point_day_parts, ignore_index=True)
                    if point_day_parts
                    else _empty_point_days(),
                    point_day_cache,
                )

    all_stays = pd.concat(stay_parts, ignore_index=True) if stay_parts else _empty_stays()
    all_point_day_parts = (
        pd.concat(point_day_parts, ignore_index=True)
        if point_day_parts
        else pd.DataFrame(columns=_point_day_columns(include_helpers=True))
    )
    all_point_days = _aggregate_point_days(all_point_day_parts)
    validate_materialization(all_stays, all_point_days, release_users)
    _write_pickle_atomically(all_stays, stay_cache)
    _write_pickle_atomically(all_point_days, point_day_cache)
    return all_stays, all_point_days


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["materialize"], required=True)
    parser.add_argument("--zip", type=Path, required=True)
    args = parser.parse_args()
    stays, _point_days = materialize_frozen_cp1(args.zip)
    print(
        f"validated {len(stays)} stays across {stays['user_id'].nunique()} users; "
        f"release universe {EXPECTED_RELEASE_USERS} users"
    )


if __name__ == "__main__":
    main()
