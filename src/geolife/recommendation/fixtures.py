"""Generated fictional place visits. No GeoLife user/coordinate data or import.

All fixture place IDs are synthetic and all owners are app demo account IDs,
not Microsoft GeoLife pseudonymous participant identifiers.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .destination import Visit


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
