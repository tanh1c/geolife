"""Generated fictional place visits. No GeoLife user/coordinate data or import.

All fixture place IDs are synthetic and all owners are app demo account IDs,
not Microsoft GeoLife pseudonymous participant identifiers.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from functools import cache

from .destination import Visit


@cache
def commute_points() -> tuple[dict[str, object], ...]:
    tz = timezone(timedelta(hours=7))
    home = (21.03, 105.82)
    office = (21.05, 105.85)
    cafe = (21.045, 105.835)
    gym = (21.04, 105.84)
    points = []
    for day in range(1, 24):
        date = datetime(2026, 9, day, tzinfo=tz)
        stays = [(0, 6, home), (21, 24, home)]
        if date.weekday() < 5:
            stays.append((9, 17, office))
            if day % 4 == 0:
                stays.append((12, 13, cafe))
            if day % 3 == 0:
                stays.append((18, 19, gym))
        for start, end, (latitude, longitude) in stays:
            for minute in range(start * 60, end * 60, 5):
                if (latitude, longitude) == office and day % 4 == 0 and 12 * 60 <= minute < 13 * 60:
                    continue
                observed = date + timedelta(minutes=minute)
                jitter = (minute // 5 % 3 - 1) * 0.00001
                points.append({
                    "timestamp_utc": observed.astimezone(timezone.utc).isoformat(),
                    "latitude": latitude + jitter,
                    "longitude": longitude - jitter,
                })
    return tuple(sorted(points, key=lambda point: point["timestamp_utc"]))


@cache
def commute_visits() -> tuple[Visit, ...]:
    from geolife.api.schemas import ClassifyRequest
    from geolife.api.service import raw_request_to_stay_frame
    from geolife.model import infer_home_office

    stays = raw_request_to_stay_frame("synthetic", ClassifyRequest.model_validate({"points": commute_points()}))
    labeled = infer_home_office(stays)
    coordinates = {"HOME": (21.03, 105.82), "OFFICE": (21.05, 105.85)}
    places = {
        row.label: f"s0_{row.label.lower()}"
        for row in labeled.itertuples()
        if row.label in coordinates
        and abs(row.latitude - coordinates[row.label][0]) < 0.001
        and abs(row.longitude - coordinates[row.label][1]) < 0.001
    }
    tz = timezone(timedelta(hours=7))
    visits = []
    for day in range(1, 24):
        date = datetime(2026, 9, day, tzinfo=tz)
        if date.weekday() < 5:
            if "OFFICE" in places:
                visits.append(Visit("demo_000", places["OFFICE"], date.replace(hour=8), "s0_home"))
            if day % 4 == 0:
                visits.append(Visit("demo_000", "s0_cafe", date.replace(hour=12), "s0_office"))
            if day % 3 == 0:
                visits.append(Visit("demo_000", "s0_gym", date.replace(hour=19), "s0_office"))
        else:
            visits.append(Visit("demo_000", "s0_park", date.replace(hour=10), "s0_home"))
        if "HOME" in places:
            visits.append(Visit("demo_000", places["HOME"], date.replace(hour=18), "s0_office"))
    return tuple(visits)


def fixture_visits() -> tuple[Visit, ...]:
    tz = timezone(timedelta(hours=7))
    start = datetime(2026, 9, 1, 8, tzinfo=tz)
    records: list[Visit] = []
    # Four completely fictional independent owners. API provisioned demo
    # accounts only have access to their own owner_id's events.
    for ix in range(4):
        owner = f"demo_{ix:03d}"
        labels = [f"s{ix}_library", f"s{ix}_market",
                  f"s{ix}_gym", f"s{ix}_cafe", f"s{ix}_park"]
        for day in range(21):
            morning = labels[0] if day % 5 else labels[3]
            evening = labels[1] if day % 3 else labels[2]
            # Deliberately include a never-before-observed held-out target
            # for account 003, so offline evaluation measures cold-start misses.
            if ix == 3 and day == 14:
                evening = "s3_unseen_station"
            records.extend([
                Visit(
                    owner_id=owner, place_id=morning,
                    observed_at=start + timedelta(days=day),
                    origin_place_id=f"s{ix}_starting_point",
                ),
                Visit(
                    owner_id=owner, place_id=evening,
                    observed_at=start + timedelta(days=day, hours=10),
                    origin_place_id=labels[0],
                ),
            ])
    return tuple(records)
