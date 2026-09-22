# Checkpoint 1 API specification — Track B1

Status: **mentor-facing contract aligned with Track B1**

This document is the Checkpoint 1 API contract. It is intentionally separate from the
internal stay-event endpoint used by the later production parity notebook.

## Goal

Expose a versioned classification contract for one user's raw GPS sequence:

```text
raw GPS points
-> CP1 cleaning
-> stay-point detection
-> recurring locations
-> HOME / OFFICE / POI
-> heuristic confidence
```

The API contract is designed in OpenAPI and is served by FastAPI/Swagger.

## Endpoint

```http
POST /v1/classify/{user_id}
```

Versioning is part of the URL through `/v1`.

### Path parameter

- `user_id`: user identifier for the supplied sequence.

## Request schema

The request body contains a sequence of GPS observations:

```json
{
  "points": [
    {
      "timestamp_utc": "2009-01-05T13:00:00Z",
      "latitude": 39.9042,
      "longitude": 116.4074
    },
    {
      "timestamp_utc": "2009-01-05T13:05:00Z",
      "latitude": 39.9042,
      "longitude": 116.4074
    }
  ]
}
```

Although the mentor shorthand says "lat/lng sequence", timestamp is required because
stay-point detection needs dwell time and HOME/OFFICE heuristics need local behavioral
time. GeoLife `.plt` timestamps are treated as UTC/GMT at ingestion.

Each point must satisfy:

- timezone-aware ISO-8601 `timestamp_utc`;
- latitude in `[-90, 90]`;
- longitude in `[-180, 180]`.

Unknown request fields are rejected.

## Processing semantics

The mentor-facing endpoint reuses the frozen production stages:

1. CP1 trajectory cleaning:
   - invalid-coordinate handling;
   - same-second compact consolidation;
   - temporal-gap continuity boundaries;
   - conservative hard-speed continuity guard;
2. CP1 stay-point detection:
   - distance threshold: 200 m;
   - minimum dwell: 1200 s;
3. geography/timezone gate:
   - Beijing-focused v1 cohort;
   - only in-region stays are converted to `Asia/Shanghai`;
4. recurring-location inference;
5. HOME/OFFICE heuristic;
6. generic POI emission for recurring locations that are not emitted as HOME/OFFICE.

The production recurring-location default remains complete-link 200 m. DBSCAN remains
available as the Track B1 comparison model and is benchmarked separately.

## Response schema

Example:

```json
{
  "user_id": "042",
  "api_version": "v1",
  "model_contract": "cp2-v1",
  "locations": [
    {
      "label": "HOME",
      "location_id": 0,
      "confidence": 0.81,
      "confidence_method": "home_office_evidence"
    },
    {
      "label": "POI",
      "location_id": 2,
      "confidence": 0.22,
      "confidence_method": "poi_visit_share"
    }
  ],
  "abstentions": [
    {
      "label": "OFFICE",
      "reason": "insufficient_semantic_evidence"
    }
  ]
}
```

The API does not return precise inferred HOME/OFFICE/POI coordinates.

## Confidence semantics

`confidence` is a **heuristic score, not a calibrated probability**.

### HOME / OFFICE

For HOME/OFFICE, the public `confidence` field is the existing evidence-strength score:

```text
support_factor = min(relevant_dates / 5, 1)

confidence =
(relevant_dwell_share + share_margin + support_factor) / 3
```

It summarizes:

- share of semantic dwell associated with the behavioral window;
- separation from the second-ranked location;
- support across distinct relevant dates.

### POI

A generic POI is another recurring location that is not emitted as HOME/OFFICE.

Its v1 heuristic confidence is:

```text
poi_visit_share =
stay_count_at_location / total_semantic_stays
```

This represents recurrence/visit share only.

"POI" here means a generic recurring point of interest. Semantic POI categorization
such as restaurant/school/shop via reverse geocoding or H3 remains a Checkpoint 2 bonus.

## Abstention

Valid requests can return no HOME or OFFICE label when evidence is weak.

Stable reasons include:

- `insufficient_stay_history`;
- `out_of_scope_geography`;
- `insufficient_recurring_history`;
- `insufficient_semantic_evidence`.

Abstention is a valid model result, not an HTTP error.

## Status codes

- **200** — valid request; may contain emitted locations and/or abstentions;
- **422** — malformed timestamp, coordinate, body, or path input;
- **500** — unexpected server failure.

## Swagger / OpenAPI artifacts

FastAPI exposes:

- Swagger UI: `/docs`;
- runtime OpenAPI JSON: `/openapi.json`.

The repository also commits the mentor-reviewable standalone artifact:

- `openapi.yaml`.

Regenerate it with:

```bash
python scripts/export_openapi.py
```

## Internal compatibility endpoint

The repository retains:

```http
POST /v1/home-office/infer
```

for stay-event HTTP ↔ direct-model parity checks from the earlier implementation.

That endpoint is marked deprecated in FastAPI and is **not** the primary Track B1
Checkpoint 1 contract. The mentor-facing contract is `/v1/classify/{user_id}`.

## Evaluation note

GeoLife does not provide authoritative HOME/OFFICE labels. Therefore the project must
not claim absolute supervised accuracy.

Checkpoint evaluation uses:

- threshold sensitivity;
- abstention and parity checks;
- manual plausibility review on a small user sample.

The manual-review protocol is documented in
`docs/evaluation/01_home_office_manual_plausibility.md`.
