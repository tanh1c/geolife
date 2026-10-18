"""Private GeoLife chronological *stay-derived* offline drift replay.

Reads the existing trusted CP1 stay cache ONLY when invoked. No raw PLT rescan,
no model change, no AWS traffic. Emits month-level aggregates without identifiers,
coordinates, dates finer than a month, paths, or row-level data.

Observed distribution shift is NOT semantic/production drift or a validated alarm.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd

DEFAULT_CACHE = Path("/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl")
ALTERNATE_CACHE = Path("/mnt/geolife-data/cache/cp2_home_office/stays_baseline_v1.pkl")
DEFAULT_OUTPUT = Path("/tmp/geolife-chronological-drift")
FROZEN_STAYS = 5821
FROZEN_USERS = 136

FEATURES = {
    "local_arrival_period": ("night_00_05", "morning_06_11", "afternoon_12_17", "evening_18_23"),
    "dwell_duration": ("20_29m", "30_119m", "120m_plus"),
    "between_stay_distance": ("unobserved", "under_1km", "1_10km", "10km_plus"),
}
THRESHOLD_JS_BITS = 0.12


class ReplayGateError(Exception):
    """Static non-private validation gate."""


@dataclass(frozen=True)
class StayEvent:
    arrival_utc: datetime
    owner: str  # memory only; never serialized or printed
    local_arrival_period: str
    dwell_duration: str
    between_stay_distance: str


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 12742.0176 * math.asin(min(1, math.sqrt(a)))


def prepare_events(stays: pd.DataFrame, *, expected_frozen: bool = True) -> list[StayEvent]:
    required = {"user_id", "arrival_time_utc", "departure_time_utc",
                "duration_s", "latitude", "longitude"}
    if not required.issubset(stays.columns):
        raise ReplayGateError("CACHE_SCHEMA")
    if expected_frozen and (len(stays) != FROZEN_STAYS or stays.user_id.nunique() != FROZEN_USERS):
        raise ReplayGateError("FROZEN_CP1_PARITY")
    if stays.empty:
        raise ReplayGateError("EMPTY_CACHE")

    frame = stays.loc[:, sorted(required)].copy()
    if frame.isna().any().any():
        raise ReplayGateError("CACHE_MISSING_VALUES")
    try:
        frame["arrival_time_utc"] = pd.to_datetime(frame["arrival_time_utc"], utc=True, errors="raise")
        frame["departure_time_utc"] = pd.to_datetime(frame["departure_time_utc"], utc=True, errors="raise")
        for field in ("duration_s", "latitude", "longitude"):
            frame[field] = pd.to_numeric(frame[field], errors="raise")
    except (ValueError, TypeError):
        raise ReplayGateError("CACHE_TYPES") from None

    if (frame.departure_time_utc < frame.arrival_time_utc).any() or (frame.duration_s < 0).any():
        raise ReplayGateError("CACHE_TIME_ORDER")
    if not frame.latitude.between(-90, 90).all() or not frame.longitude.between(-180, 180).all():
        raise ReplayGateError("CACHE_COORDINATES")
    frame = frame.sort_values(["user_id", "arrival_time_utc", "departure_time_utc"],
                              kind="stable")
    try:
        from timezonefinder import TimezoneFinder
        resolver = TimezoneFinder(in_memory=True)
    except ImportError:
        raise ReplayGateError("TIMEZONEFINDER_UNAVAILABLE") from None

    events: list[StayEvent] = []
    last: dict[str, tuple[datetime, float, float]] = {}
    for row in frame.itertuples(index=False):
        owner = str(row.user_id)
        arrival = row.arrival_time_utc.to_pydatetime()
        departure = row.departure_time_utc.to_pydatetime()
        lat, lon = float(row.latitude), float(row.longitude)
        zone = resolver.timezone_at(lat=lat, lng=lon)
        if zone is None:
            raise ReplayGateError("TIMEZONE_UNRESOLVED")
        try:
            hour = arrival.astimezone(ZoneInfo(zone)).hour
        except (ValueError, KeyError):
            raise ReplayGateError("INVALID_TIMEZONE") from None

        period = FEATURES["local_arrival_period"][hour // 6]
        duration_minutes = float(row.duration_s) / 60
        dwell = ("20_29m" if duration_minutes < 30
                 else "30_119m" if duration_minutes < 120 else "120m_plus")
        transition = "unobserved"
        if owner in last:
            last_departure, last_lat, last_lon = last[owner]
            gap = arrival - last_departure
            if timedelta(0) <= gap <= timedelta(hours=24):
                km = _distance_km(last_lat, last_lon, lat, lon)
                transition = "under_1km" if km < 1 else "1_10km" if km < 10 else "10km_plus"
        last[owner] = (departure, lat, lon)
        events.append(StayEvent(arrival, owner, period, dwell, transition))
    return sorted(events, key=lambda e: e.arrival_utc)


def _hist(events: list[StayEvent]) -> dict[str, list[int]]:
    return {
        feature: [sum(getattr(e, feature) == category for e in events) for category in values]
        for feature, values in FEATURES.items()
    }


def js_bits(a: list[int], b: list[int]) -> float:
    """Jensen-Shannon divergence, bits; fixed 0.5 pseudocount to avoid log(0)."""
    if len(a) != len(b) or not a or min([*a, *b]) < 0:
        raise ValueError("Invalid histogram")
    pa = [(x + 0.5) / (sum(a) + 0.5 * len(a)) for x in a]
    pb = [(x + 0.5) / (sum(b) + 0.5 * len(b)) for x in b]
    return sum((p * math.log2(p / ((p + q) / 2))
                + q * math.log2(q / ((p + q) / 2))) / 2 for p, q in zip(pa, pb))


def replay(events: list[StayEvent], *, reference_months: int = 3,
           min_stays: int = 30, min_users: int = 5, min_days: int = 7,
           threshold_bits: float = THRESHOLD_JS_BITS) -> dict[str, object]:
    if reference_months < 1 or min_stays < 1 or min_users < 2 or min_days < 1:
        raise ValueError("Invalid support thresholds")
    if not (0 < threshold_bits < 1):
        raise ValueError("Invalid divergence threshold")
    if not events:
        raise ReplayGateError("EMPTY_EVENTS")
    ordered = sorted(events, key=lambda e: e.arrival_utc)
    months: dict[str, list[StayEvent]] = defaultdict(list)
    for event in ordered:
        if event.arrival_utc.utcoffset() != timedelta(0):
            raise ReplayGateError("NOT_UTC")
        months[event.arrival_utc.strftime("%Y-%m")].append(event)

    history = []
    for month, records in sorted(months.items()):
        support = len(records) >= min_stays and len({e.owner for e in records}) >= min_users
        support &= len({e.arrival_utc.date() for e in records}) >= min_days
        history.append((month, records, support))

    eligible = [(month, rows) for month, rows, ok in history if ok]
    if len(eligible) <= reference_months:
        raise ReplayGateError("INSUFFICIENT_SUPPORTED_WINDOWS")

    reference_records = [e for _, rows in eligible[:reference_months] for e in rows]
    reference = _hist(reference_records)
    reference_set = {month for month, _ in eligible[:reference_months]}
    streak = 0
    windows = []
    for month, rows, supported in history:
        if month in reference_set:
            status, divergences = "reference", None
        elif not supported:
            streak = 0
            status, divergences = "insufficient_support", None
        else:
            current = _hist(rows)
            divergences = {field: round(js_bits(reference[field], counts), 6)
                           for field, counts in current.items()}
            streak = streak + 1 if max(divergences.values()) >= threshold_bits else 0
            status = "observed_shift_candidate" if streak >= 2 else "observed"
        # Never serialize low-support rows, IDs, coordinates, or stay-level dates.
        windows.append({
            "month_utc": month, "status": status,
            "stays": len(rows) if supported else None,
            "histograms": _hist(rows) if supported else None,
            "js_bits": divergences,
        })

    # Separate, constructed histogram perturbation: never present as a GeoLife observation.
    fake = {name: [0] * len(categories) for name, categories in FEATURES.items()}
    for name, counts in reference.items():
        fake[name][min(range(len(counts)), key=lambda i: counts[i])] = 50
    simulated = []
    for i in range(2):
        score = max(js_bits(reference[name], counts) for name, counts in fake.items())
        simulated.append({
            "window": f"injected_{i + 1}",
            "js_max_bits": round(score, 6),
            "status": "simulated_alert" if i == 1 and score >= threshold_bits else
                      "simulated_warning" if score >= threshold_bits else "no_alert",
        })
    return {
        "scope": "private_geolife_stay_derived_chronological_replay",
        "status": "offline_diagnostic_not_production_drift",
        "time_axis": "UTC_month_of_CP1_stay_arrival",
        "reference_months_utc": sorted(reference_set),
        "config": {"reference_months": reference_months, "min_stays": min_stays,
                   "min_users": min_users, "min_days": min_days, "js_threshold_bits": threshold_bits,
                   "consecutive_windows": 2},
        "reference_histograms": reference,
        "feature_categories": {k: list(v) for k, v in FEATURES.items()},
        "windows": windows,
        "injected_simulation": {
            "kind": "constructed_histogram_shift_not_real_gps_or_model_drift",
            "windows": simulated,
        },
        "limitations": [
            "Derived CP1 stays, not raw point replay; cross-file CP1 boundaries unchanged",
            "Month-by-month cohort, sampling and geographic coverage can change",
            "Unobserved transitions are not zero-distance trips",
            "Frozen full-history HOME/OFFICE inference is not recomputed for monthly windows",
            "Observed flags are descriptive, not production alerts or semantic accuracy",
        ],
    }


def run_from_cache(cache: Path = DEFAULT_CACHE, **options: object) -> dict[str, object]:
    if not cache.is_file():
        raise ReplayGateError("PRIVATE_CP1_CACHE_MISSING")
    # Trusted existing private Modal pickle ONLY; never deserialize arbitrary uploads.
    stays = pd.read_pickle(cache)
    return replay(prepare_events(stays, expected_frozen=True), **options)


def save_aggregate(result: dict[str, object], output: Path) -> None:
    output.mkdir(parents=True, exist_ok=True)
    (output / "chronological_drift_aggregate.json").write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def plot_aggregate(result: dict[str, object], output: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    output.mkdir(parents=True, exist_ok=True)
    windows = [w for w in result["windows"] if w["js_bits"] is not None]
    if not windows:
        raise ReplayGateError("NO_CHARTABLE_WINDOWS")
    fig, ax = plt.subplots(figsize=(11, 4))
    for metric in FEATURES:
        ax.plot([w["month_utc"] for w in windows],
                [w["js_bits"][metric] for w in windows],
                marker="o", label=metric)
    ax.axhline(result["config"]["js_threshold_bits"], linestyle="--", label="Review threshold")
    ax.set(title="GeoLife CP1 stays — chronological distribution differences (offline)",
           ylabel="Jensen-Shannon divergence (bits)", xlabel="UTC month")
    ax.tick_params(axis="x", rotation=45)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output / "chronological_drift_js.png", dpi=160)
    plt.close(fig)

    demo = result["injected_simulation"]["windows"]
    fig, ax = plt.subplots(figsize=(5, 3))
    ax.plot([w["window"] for w in demo], [w["js_max_bits"] for w in demo], marker="o")
    ax.axhline(result["config"]["js_threshold_bits"], linestyle="--")
    ax.set(title="Synthetic histogram perturbation — NOT observed GeoLife drift",
           ylabel="Max JS bits", xlabel="Constructed window")
    fig.tight_layout()
    fig.savefig(output / "injected_alert_demo.png", dpi=160)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=DEFAULT_CACHE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    try:
        result = run_from_cache(args.cache)
        save_aggregate(result, args.out)
        plot_aggregate(result, args.out)
    except ReplayGateError as err:
        print(f"NOT RUN: {err}")
        return 2
    print(json.dumps({
        "status": "AGGREGATE_SAVED",
        "supported_post_reference_windows": sum(
            w["js_bits"] is not None for w in result["windows"]
        ),
        "injected_demo_status": result["injected_simulation"]["windows"][-1]["status"],
        "output_kind": "aggregate_json_and_two_png",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
