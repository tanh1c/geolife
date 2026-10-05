# Stage 07k — Blinded historical-imagery adjudication

## Purpose

Stage 07j left 9 one-step OFFICE near-miss users in abstention.

Stage 07k creates a reproducible manual historical-imagery review workflow for those candidates using Google Earth Pro or another historical-imagery viewer.

This stage does not download imagery, does not identify employers, and does not emit OFFICE labels.

## Why historical imagery is useful here

BCL POI 2008 is the primary historical POI source, but only 2 / 9 near-miss candidates are BCL-evaluable.

Historical satellite/aerial imagery can provide a different evidence family:

- whether a built structure existed at the candidate at the relevant time;
- broad visible morphology / land-use context;
- whether the candidate lies inside the same visible complex.

It cannot reliably identify employment, occupation, tenant identity, or a company name.

## Review blinding

The visual review must be independent of Stage-07j behavioral/BCL results.

Therefore the KML and review CSV intentionally exclude:

- user id;
- margin-near vs share-near group;
- HoWDe / recurrence matches;
- split-half results;
- held-out results;
- dropout retention;
- BCL context.

Each candidate receives a deterministic blinded audit id such as `I01`.

The mapping back to user/candidate evidence is stored separately in:

`historical_imagery_unblinding_key_private.pkl`

and should not be opened until visual classification is complete.

## Spatial reconstruction

Stage 07k rebuilds CP2-v2 semantic locations from the frozen CP1 stays using:

- complete-link clustering;
- 200 m maximum location diameter;
- per-stay resolved local timezone behavior already frozen in CP2-v2.

For each Stage-07j candidate it attaches:

- exact semantic-location centroid;
- production HOME reference centroid when available;
- candidate-to-HOME distance;
- observation start date;
- median distinct local observation date;
- observation end date;
- number of active local dates;
- number of stays.

The median distinct local observation date is the initial target date for historical imagery.

## KML artifacts

Private KML outputs:

- `near_miss_9_blinded_historical_imagery_review_private.kml`;
- `baseline16_blinded_historical_imagery_reference_private.kml`;
- `all25_blinded_historical_imagery_review_private.kml`.

Each candidate contains:

- blinded audit id;
- exact candidate point;
- HOME reference marker when available;
- 50 m ring;
- 100 m ring;
- 150 m ring;
- start / median / end observation dates.

Coordinates are private research artifacts and are not committed to the repository.

## Review order

Primary review:

- the 9 near-miss candidates.

Optional reference review:

- the frozen 16 OFFICE candidates.

The 16-user reference cohort is not ground truth. It is only useful for understanding what the existing production OFFICE policy looks like under the same visual rubric.

## Fixed visual rubric

Exactly one `visual_context_class` should be selected:

1. `large_office_commercial_like_complex`
2. `education_campus`
3. `healthcare_institutional`
4. `industrial_warehouse`
5. `residential_compound`
6. `transport_infrastructure`
7. `mixed_urban_block`
8. `construction_vacant`
9. `recreation_green_space`
10. `other_visible_structure`
11. `ambiguous`

These are visual-context classes only.

Even `large_office_commercial_like_complex` does not prove OFFICE.

## Manual fields

The blinded review manifest contains:

- `imagery_available`: yes / no / unclear;
- `imagery_date_used`;
- `imagery_date_offset_days`;
- `imagery_quality`;
- `structure_present`: yes / no / unclear;
- `visual_context_class`;
- `visual_context_confidence`: high / medium / low;
- `candidate_inside_same_complex`: yes / no / unclear;
- `historical_name_evidence`;
- `present_day_name_aid`;
- `review_notes`.

The actual historical imagery date must be recorded because an exact-date image may not exist.

## Present-day reverse geocoding

A present-day Baidu/Amap/Google-style name may be recorded only in `present_day_name_aid`.

It is not historical evidence.

A historical name should be entered only when there is separate period-appropriate evidence.

## Interpretation

Useful positive contextual evidence includes:

- a clearly visible campus/institutional/commercial-like complex existing near the candidate during the candidate's observation period;
- the candidate lying inside that visible complex.

Useful contradictory context may include:

- vacant/construction land at the relevant date;
- obvious transport-only context;
- clear residential morphology.

However imagery quality and temporal offset must always qualify the interpretation.

## Outputs

Cache root:

`/mnt/geolife-data/cache/cp2_v2/07k_historical_imagery_review/`

Private:

- all three KML files;
- all-25 blind manifest;
- 9-user near-miss blind manifest;
- 16-user baseline blind manifest;
- near-miss priority audit ids;
- unblinding key;
- spatial context panel.

Non-sensitive rubric:

- `historical_imagery_review_rubric.csv`.

## Decision boundary

Stage 07k itself does not change OFFICE production.

After manual review, a separate unblinding step may compare visual context with Stage-07j behavioral persistence and BCL evidence.

No user should be promoted from imagery alone.
