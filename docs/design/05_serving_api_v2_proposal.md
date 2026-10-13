# Serving API v2 — contract proposal for Track B1 delivery

Status: **SYNC v2 MVP IMPLEMENTED ON FEATURE BRANCH**; async/rate-limiting/413/503 are still planned. Date: 2026-10-12.

Implemented in `src/geolife/api/v2.py`: `POST /v2/inferences`, `GET /v2/model-info`, `GET /health/ready`, real complete-link 200m and DBSCAN 100m model configurations, env-controlled deterministic canary, and typed privacy-safe responses. OpenAPI was generated from FastAPI and committed at `openapi.yaml`. This is **code/CI, not an AWS deployment**.

## What is wrong with v1 for serving?

Current `POST /v1/classify/{user_id}` is implemented and meets the original mentor shorthand, but `user_id` in a URL is unnecessary for stateless GPS processing and may be recorded in infrastructure access logs. It also returns generic recurring locations as `POI`, even though no real POI category has been validated. Finally `confidence` is an engineering evidence score, not a calibrated probability. Keep v1 for backward compatibility, but design the deployable contract around the actual semantics.

## Public v2 API

| Method | Endpoint | Purpose | Priority |
|---|---|---|---|
| POST | `/v2/inferences` | Stateless raw GPS -> cleaning/stays/recurring locations/HOME/OFFICE/OTHER_RECURRING | IMPLEMENTED |
| GET | `/health` | Existing live probe (legacy) | DONE |
| GET | `/health/ready` | Process/config readiness probe (not external dependency health), no GPS data | IMPLEMENTED |
| GET | `/v2/model-info` | Supported variants, configured rollout, release ID (injected by environment), no PII | IMPLEMENTED |
| POST | `/v2/jobs` | Async request submission; returns 202 and job ID | P1 |
| GET | `/v2/jobs/{job_id}` | Status pending/running/completed/failed/expired | P1 |

`v2` is an **API schema** version. Model variant (`per-stay-heuristic-v1`, `cp2-v2-complete-link`, optional tested `dbscan` comparator) is a **different** version axis; container/app release SHA is a third axis. Existing CP2-v2 uses **complete-link**, not DBSCAN; do not relabel it.

### Request

```json
{
  "client_request_id": "example-123",
  "points": [
    {"timestamp_utc": "2009-01-05T13:00:00Z", "latitude": 39.9042, "longitude": 116.4074},
    {"timestamp_utc": "2009-01-05T13:04:00Z", "latitude": 39.9042, "longitude": 116.4074}
  ]
}
```

- `client_request_id` optional, opaque, ASCII token with length limit; never a raw email or real-world user identifier. Generate a server `request_id` for telemetry when absent.
- `points`: chronological order not required (CP1 sorts); each point requires timezone-aware ISO-8601 datetime and coordinates in range; server normalizes to UTC. No `user_id` in path or body.
- Allow a valid but insufficient sequence to return 200 with HOME/OFFICE abstentions. Do not reject short histories merely because the model would abstain.
- The implemented Pydantic field enforces **max 20,000 GPS points** for sync request (HTTP **422** if exceeded). A reverse-proxy **byte-size cap** and HTTP 413 are still TODO; there is no async alternative yet.
- Do not expose threshold overrides or require timezone supplied by client: use per-stay coordinate -> IANA timezone policy.
- Duplicate timestamps and gaps handled by frozen CP1 cleaning, not by request schema.

### Example response — mixed emission and abstention

```json
{
  "request_id": "f65b7522-2acf-4b4d-a921-726ed9af4671",
  "api_version": "v2",
  "model": {
    "model_id": "geolife-home-office",
    "model_version": "cp2-v2-complete-link",
    "release_id": "git-sha-or-image-digest"
  },
  "observation": {
    "raw_points": 150,
    "detected_stays": 6,
    "recurring_locations": 2
  },
  "predictions": {
    "HOME": {
      "status": "emitted",
      "location_ref": "L0",
      "evidence_score": 0.81,
      "evidence_method": "dwell_share_margin_date_support"
    },
    "OFFICE": {
      "status": "abstained",
      "reason": "insufficient_semantic_evidence"
    }
  },
  "other_recurring_places": [
    {
      "location_ref": "L1",
      "visit_share": 0.2,
      "semantic_type": "OTHER_RECURRING"
    }
  ]
}
```

The example above demonstrates **schema shape only**, not an actual measured model response.

- Always provide separate HOME and OFFICE outcomes; valid abstention is **200**, not 404/422.
- A non-HOME/non-OFFICE recurring cluster is `OTHER_RECURRING`, not a verified restaurant, school, office or POI category.
- `evidence_score` = existing model heuristic `evidence_strength` when selected. It is not accuracy, posterior probability or cross-version calibrated confidence.
- `visit_share` is recurrence-based only; do not call it semantic confidence.
- `location_ref` is **request-scoped** and is not stable across models or reruns.
- Do not output precise HOME/OFFICE/OTHER coordinates, source files, raw trajectories or IANA timezone locations in the standard response.
- No broad failure reason inferred from non-selection unless supported by the existing CP2 diagnostic gate; otherwise use `insufficient_semantic_evidence`.

## Contract & error semantics

| HTTP | When | Response |
|---|---|---|
| 200 | Valid sync request, including full/partial abstention | Typed predictions + version + aggregate support |
| 202 | Async accepted, job ID returned | Status URL; no raw data |
| 413 | Planned proxy-level byte limit (NOT IMPLEMENTED) | Sanitized rejection |
| 422 | Invalid timestamps, shape or coordinate ranges | Sanitized validation details; never input values |
| 429 | Planned rate limiting (NOT IMPLEMENTED) | Structured retry response |
| 503 | Planned unavailable-version/queue behavior (NOT IMPLEMENTED) | Sanitized service error |
| 500 | Unexpected implementation error | Generic server error |

The response includes an opaque server-generated request UUID; a request-ID header and production ingress controls remain TODO. Current `openapi.yaml` documents the implemented sync routes and statuses (200/422/500), **not** proposed 202/413/429/503 behavior.

## Versioning / rollout semantics

- Model names must describe an *implemented* algorithm. A heuristic on individual stays and clustered recurring-location model are different variants. Production CP2-v2 is `complete_link_200m` until changed in code through review.
- Version- and route-tagged metrics: requests, error status, latency histograms, emitted HOME/OFFICE, abstentions; never label disagreement as accuracy.
- Canary **implemented (app-level demo)**: deterministic HMAC hash on an optional opaque request token selects the candidate according to `GEOLIFE_CANARY_PERCENT` (default 10) when `GEOLIFE_ROLLOUT_MODE=canary`. Response reports model variant. Rollback uses `GEOLIFE_ROLLOUT_MODE=baseline` and process restart/redeploy, not an instant dynamic admin toggle. Do not confuse it with load-balancer weighted traffic.
- Shadow (**TODO**): send the same request in memory to both models, return only baseline, record aggregate disagreement without positions/raw payload.
- Blue-green (**TODO**): two independently deployed environments with contract parity, smoke test green before flipping upstream traffic.

## Privacy/security

Do not log request JSON, precise locations, raw user IDs, job bodies or coordinates. Validation errors must suppress `input`, Pydantic `ctx`, and variable values. Use HTTPS, authentication or restricted network access, bounded request size, request timeout, concurrency limits, private encryption/TTL for async, per-model release provenance. CORS is off unless a specific trusted origin is needed. Job ID is a random opaque token, never derived from user location.

## Acceptance tests and remaining gates

1. v1 unchanged and its tests still pass.
2. v2 accepts UTC-aware GPS and results match the same underlying CP1+CP2 functions for a deterministic fixture.
3. HOME/OFFICE both present with emitted/abstained union; no forced HOME/OFFICE to increase coverage.
4. `OTHER_RECURRING` is not advertised as externally validated POI category.
5. No exact inferred location coordinate or raw GPS in public responses/logs/errors.
6. Max points and body limits; naive datetime and invalid coordinate return 422/413 as appropriate.
7. Returned selected model variant and release ID are inspectable.
8. OpenAPI generated from the running app matches committed `openapi.yaml`.
9. Multiple variants have real, tested independent implementation; never call the current complete-link production method `DBSCAN`.
10. Sync/async and canary changes only routing/execution, not hidden CP1 threshold overrides.


## Local v2 smoke (implemented)

```bash
GEOLIFE_ROLLOUT_MODE=baseline uvicorn geolife.api.app:app --host 127.0.0.1 --port 8000
curl http://127.0.0.1:8000/v2/model-info
curl -X POST http://127.0.0.1:8000/v2/inferences -H 'Content-Type: application/json' \\
  -d '{"points":[{"timestamp_utc":"2009-01-05T13:00:00Z","latitude":39.9042,"longitude":116.4074}]}'
```

Canary mode: set `GEOLIFE_ROLLOUT_MODE=canary`, `GEOLIFE_CANARY_PERCENT=10`, `GEOLIFE_CANARY_SALT=<private random value>` before starting. To roll back, restart with `GEOLIFE_ROLLOUT_MODE=baseline`. No API option allows external callers to force the variant.
