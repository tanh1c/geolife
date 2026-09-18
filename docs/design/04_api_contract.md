# CP3 API contract — Home / Office inference

Date: 2026-09-18  
Status: VALIDATED — contract, FastAPI layer, tests, OpenAPI/privacy checks, and full-release HTTP ↔ direct-model parity have passed.

## Goal

Expose the frozen CP2 v1 Home / Office baseline through a small, explicit HTTP API without changing model semantics.

The API layer is responsible for:

- validating transport/schema concerns;
- converting a request into the frozen production model input;
- surfacing abstention explicitly;
- preserving privacy by not returning precise inferred Home/Office coordinates;
- keeping HTTP/OpenAPI behavior deterministic and testable.

The API layer is **not** allowed to retune CP2 thresholds or reinterpret evidence strength.

## Scope boundary

### Input starts at CP1 stay events

v1 accepts already-detected stay events, not raw GPS points.

Reason:

- raw trajectory cleaning + stay detection is expensive and is already a separately validated CP1 stage;
- request-time raw-GPS inference would combine ingestion, cleaning, stay detection, semantic inference and serving in one endpoint;
- the first serving checkpoint should isolate the semantic serving contract.

A future batch/async endpoint may accept raw trajectories, but that is outside CP3 v1.

### One user per request

`POST /v1/home-office/infer` carries exactly one `user_id` and a list of stays for that user.

This avoids accidental cross-user mixing and makes abstention semantics unambiguous.

## Frozen upstream model semantics

The API calls the existing CP2 production implementation with the default `HomeOfficeConfig`.

Frozen CP2 v1 semantics include:

- Beijing-focused cohort: 100 km reference radius;
- user eligibility: >=80% stay share and >=80% dwell share inside radius;
- only in-region stays receive `Asia/Shanghai` semantic time;
- recurring locations: per-user complete linkage, max diameter 200 m;
- Home window: 21:00–06:00 local;
- Office window: weekdays 09:00–17:00 local;
- Home gate: >=3 relevant dates, share >=0.50, margin >=0.20;
- Office gate: >=3 relevant dates, share >=0.30, margin >=0.10;
- evidence strength is heuristic, not a probability.

The HTTP API does not expose threshold overrides in v1.

## Endpoint

### `GET /health`

Purpose: process/readiness smoke check.

Response:

```json
{
  "status": "ok",
  "service": "geolife-home-office-api",
  "api_version": "v1",
  "model_contract": "cp2-v1"
}
```

### `POST /v1/home-office/infer`

Request:

```json
{
  "user_id": "042",
  "stays": [
    {
      "arrival_time_utc": "2009-01-05T13:00:00Z",
      "departure_time_utc": "2009-01-05T14:30:00Z",
      "latitude": 39.90,
      "longitude": 116.40
    }
  ]
}
```

The API derives `duration_s` from arrival/departure timestamps. Clients do not provide duration separately, avoiding disagreement between interval endpoints and duration.

## Request validation

Each stay must satisfy:

- arrival and departure are timezone-aware ISO-8601 datetimes;
- departure > arrival;
- latitude in [-90, 90];
- longitude in [-180, 180].

Request-level requirements:

- `user_id` is non-empty;
- at least one stay is present;
- all stays inherit the request `user_id`.

Malformed schema/time/coordinate input is an HTTP **422** validation error.

Valid but insufficient/out-of-scope behavioral evidence is **not** an HTTP error; it returns HTTP 200 with explicit abstention.

## Response contract

The response always contains results for both semantic labels:

```json
{
  "user_id": "042",
  "model_contract": "cp2-v1",
  "results": [
    {
      "label": "HOME",
      "status": "emitted",
      "location_id": 0,
      "evidence_strength": 0.81,
      "relevant_dwell_share": 0.74,
      "share_margin": 0.51,
      "relevant_dates": 8,
      "relevant_dwell_h": 33.4
    },
    {
      "label": "OFFICE",
      "status": "abstained",
      "reason": "insufficient_semantic_evidence"
    }
  ]
}
```

## Abstention reasons

v1 uses a small stable enum:

- `out_of_scope_geography`
  - the user's stay/dwell history does not satisfy the frozen Beijing-focused cohort, so no semantic-time inference is attempted;
- `insufficient_recurring_history`
  - the user enters the semantic cohort but has no recurring location with >=2 stays;
- `insufficient_semantic_evidence`
  - recurring history exists, but the frozen Home/Office support/share/margin gate is not met.

Abstention is a valid model result, not an exception.

## Partial emission

HOME and OFFICE are evaluated separately.

Allowed examples:

- HOME emitted, OFFICE abstained;
- HOME abstained, OFFICE emitted;
- both emitted;
- both abstained.

The API must not force HOME and OFFICE to be different locations. If CP2 emits both with the same `location_id`, the API preserves that result.

## Evidence semantics

For an emitted label, expose:

- `location_id`;
- `evidence_strength`;
- `relevant_dwell_share`;
- `share_margin`;
- `relevant_dates`;
- `relevant_dwell_h`.

Do **not** name `evidence_strength` confidence probability or correctness probability.

The API does not return exact inferred coordinates in v1.

## Privacy

Request bodies contain location history and are sensitive.

Contract rules:

- do not include request bodies in application logs by default;
- do not return precise Home/Office latitude/longitude;
- do not persist request payloads in the serving layer;
- validation errors should describe schema problems without echoing the full stay history.

The client already supplies stay coordinates, but omitting inferred semantic coordinates reduces downstream accidental disclosure and logging risk.

## POI scope

CP2 production semantics currently freeze HOME and OFFICE plus abstention.

The API must not rename every non-Home/non-Office recurring location to `POI`. A future POI/OTHER contract requires its own semantics and validation.

## Determinism and parity

The HTTP layer must preserve the model result.

Acceptance criteria include:

- direct production inference and HTTP inference agree on emitted labels/evidence for the same stay table;
- no request-level parameter can silently alter frozen CP2 defaults;
- OpenAPI documents both emitted and abstained response shapes.

## Error model

- 200: valid request, including full/partial abstention;
- 422: malformed input;
- 500: unexpected server failure only.

Do not use 404/409/422 to represent weak model evidence.

## TDD gate

Before implementation, RED tests should lock:

1. health schema;
2. valid emitted response;
3. explicit geography abstention;
4. recurring-history abstention;
5. partial Home/Office emission;
6. timezone-naive timestamp rejection;
7. invalid interval/coordinates rejection;
8. response omission of precise inferred coordinates;
9. same-location Home/Office preservation;
10. OpenAPI path/schema presence;
11. HTTP/direct-model parity on a deterministic fixture.

Only then implement `src/geolife/api/`.


## Implementation status

Implemented production files:

- `src/geolife/api/schemas.py`;
- `src/geolife/api/service.py`;
- `src/geolife/api/app.py`;
- `src/geolife/api/__init__.py`.

The API package exposes:

- `GET /health`;
- `POST /v1/home-office/infer`;
- OpenAPI at `/openapi.json`;
- interactive docs at `/docs`.

Acceptance tests cover:

- health schema;
- partial Home/Office emission;
- explicit geography abstention;
- explicit recurring-history abstention;
- same-location Home/Office preservation;
- timezone-naive rejection;
- invalid interval/coordinate rejection;
- empty request rejection;
- OpenAPI route presence;
- direct-model ↔ HTTP parity on a deterministic fixture;
- omission of precise inferred coordinates;
- validation-error input scrubbing;
- rejection of request-time threshold overrides.

The release-level validation notebook is:

`notebooks/04_api_contract_validation.ipynb`

It reuses the private 5,821-stay CP2 cache and replays all 136 users through the API one user at a time. The final gate is exact emitted-key/evidence parity with direct production inference and aggregate counts of 27 HOME / 16 OFFICE.


## Full-release HTTP parity result

Notebook `04_api_contract_validation.ipynb` was run on the private cached table of **5,821 stays across 136 users**.

Direct production model:

- HOME: **27**;
- OFFICE: **16**;
- emitted rows: **43**;
- unique emitted users: **36**.

HTTP replay, one user per request:

- HOME: **27**;
- OFFICE: **16**;
- emitted rows: **43**;
- unique emitted users: **36**.

The notebook also verified:

- exact emitted `(user_id, label)` key parity;
- exact location-id parity;
- relevant-date parity;
- numerical parity for evidence strength, relevant-dwell share, share margin and relevant dwell hours;
- validation/privacy smoke checks.

Result: **full-release HTTP ↔ direct-model parity PASS**.

### Abstention distribution

Across the 136 valid per-user requests, each semantic label always returns either emitted or abstained.

HOME:

- emitted: 27;
- `out_of_scope_geography`: 39;
- `insufficient_recurring_history`: 24;
- `insufficient_semantic_evidence`: 46.

OFFICE:

- emitted: 16;
- `out_of_scope_geography`: 39;
- `insufficient_recurring_history`: 24;
- `insufficient_semantic_evidence`: 57.

These are serving/model-outcome counts, not error rates or accuracy measurements.

### Partial-emission warning found during replay

The full HTTP replay exposed a pandas `FutureWarning` when the production model concatenated one emitted frame with one empty frame for users who emitted only HOME or only OFFICE.

The result values were correct, but the warning indicated a future dtype-behavior risk.

The production code was amended to concatenate only non-empty emission frames, and a regression test was added. This does not change frozen CP2 semantics or parity counts.
