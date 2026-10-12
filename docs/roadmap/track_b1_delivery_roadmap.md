# Track B1 — MLE delivery roadmap (post-EDA pivot)

Updated: 2026-10-12. Status: **IMPLEMENTATION PLAN, NOT A CLAIM OF DEPLOYMENT**.

## Objective and scope

Ship a reviewable, working MLE service from raw GPS request to HOME/OFFICE inference, versioned routing, async serving and operational metrics. The objective of the six-week brief is working engineering, **not** maximized semantic coverage or GeoLife ground-truth accuracy.

Freeze the current production reference while delivering infrastructure:

- CP1 fixed cleaning/stay-point semantics: same-second 10m, gap 300s, speed guard 1,200km/h, stay radius 200m, minimum dwell 20 minutes.
- CP2-v2 uses complete-link max diameter 200m, per-stay IANA timezones and abstention. Frozen full-release result: 5,821 stays, HOME 27, OFFICE 16.
- Stage 08c experimental tiers (HOME 36, OFFICE 19) **are not** production. Stage 09 file stitching (5,821 -> 5,831 stays; no new stay users or HOME/OFFICE emissions) is a research comparator, not a migration.

The existing **v1 API stays available** for backward compatibility. A more sensible **v2 serving contract** is specified in `docs/design/05_serving_api_v2_proposal.md`; it will be implemented and tested explicitly, not silently substituted for v1.

## Deliverables and gates (in execution order)

| Priority | Track / task | Existing status at pivot | Next implementation / acceptance gate |
|---|---|---|---|
| P0 | CP1/CP2 model and tests | DONE | Preserve direct-model parity and fixed semantics. |
| P0 | FastAPI + Swagger/OpenAPI v1 | DONE | Keep `/v1/classify/{user_id}` and `openapi.yaml` unchanged until v2 is implemented. |
| P0 | Containerization | IMPLEMENTED; Docker CI PASS on initial image, new v2 smoke run pending | Minimal Docker image excluding raw GeoLife data, non-root runtime, health smoke test in CI, documented local run. |
| P0 | Serving API v2 | IMPLEMENTED sync MVP on branch; AWS unverified | Implemented `POST /v2/inferences` as stateless POST (no user ID in URL), typed HOME/OFFICE emitted/abstained, OTHER_RECURRING, model provenance, 20k-point cap, privacy tests, generated OpenAPI. Remaining: reverse-proxy byte cap/auth/rate limits. |
| P0 | Two genuinely distinct model variants | IMPLEMENTED as complete-link 200m and DBSCAN 100m, tested synthetic distinctness; compare on fixed dataset before AWS | Implemented two real grouping variants, `cp2-v2-complete-link-200m` and `cp2-v2-dbscan-100m`, preserving the same CP1 + semantic gate. Synthetic chain fixture checks different location grouping. Exact historical brief's per-stay heuristic remains optional; version manifest and per-version comparison still TODO. |
| P0 | AWS deployment | TODO / user cloud credentials required | Pick a low-complexity runtime: one Docker host for sync MVP, IAM least privilege, HTTPS or restricted internal demo endpoint, cost alerts, explicit deploy/rollback script; verify endpoint externally. Do not claim free tier automatically. |
| P1 | One release strategy | IMPLEMENTED app-level deterministic canary + env rollback, not yet AWS-demonstrated | App-level deterministic canary routing is implemented via `GEOLIFE_ROLLOUT_MODE`/`GEOLIFE_CANARY_PERCENT`; rollback requires restart/redeploy, not a dynamic control. Per-version metrics and AWS validation are still TODO. |
| P1 | Shadow vs blue-green explanation | TODO | Document shadow logging without raw coordinates, and environment-level blue-green cutover; shadow must not affect returned response. |
| P1 | Async proof of concept | TODO | `POST /v2/jobs` -> private encrypted storage for payload + SQS pointer -> worker -> TTL result -> `GET /v2/jobs/{job_id}`; non-blocking idempotency, no GPS in queue message/log. AWS deploy after sync proves stable. |
| P1 | Latency and operational metrics | HTTP counters/latency histogram and synthetic sync p50/p95/p99 harness IMPLEMENTED on branch; dashboard/async comparison pending | p50/p95/p99 per model/route, error rate, abstention rate, safe request-size histogram; reproducible replay load benchmark for sync and async. |
| P1 | Basic drift/replay dashboard | TODO | Chronological GeoLife replay of **aggregated, privacy-safe** metrics, distribution-shift alert, CloudWatch dashboard, clear `simulated_offline_replay` label (not production drift). |
| P1 | End-to-end demo and mentor pack | TODO | Curl/Postman, public or internal AWS URL, model/version comparison, canary rollback, async polling, metrics screenshots, cost teardown, final architecture and reproducibility notes. |
| P2 | Historical POI enrichment / H3 category | BACKLOG | OPTIONAL: category only with verified data source/license/time alignment; otherwise return OTHER_RECURRING. |
| P2 | Privacy hardening | PARTLY DONE | Maintain location confidentiality: no request-body logs, no exact inferred coordinates, rate/body-size limits, retention and access policies. Review log hygiene and data lifecycle before AWS. |

## Work packages for short remaining schedule

**Package A — first runnable serving demo (highest priority):**
1. Dockerize existing v1 FastAPI with non-root image; build/test image in GitHub CI.
2. Implement and test v2 endpoint, freeze a single coherent schema, regenerate `openapi.yaml`.
3. Implement real alternative heuristic + version metadata; parity tests for each variant.
4. Start locally with Docker and run fixed synthetic smoke cases.

**Package B — production-like demo:**
5. Deploy to a single AWS host/service with HTTPS/restricted access and cost alert.
6. Add deterministic 10% canary and simple rollback; report traffic split and outputs.
7. Add SQS + worker + private TTL payload/result storage, compare sync/async latency.
8. Expose privacy-safe operational metrics and a time-ordered **simulated** drift replay; record dashboard.

**Definition of done:** a real callable deployed endpoint, at least two real distinguishable model variants, a working rollout strategy demo, an async flow with job status, latency/error charts, and a complete end-to-end README. A written plan or local Dockerfile alone is **not** deployment completion.

## Architecture choice / explicit tradeoffs

- Prefer **single Docker-based sync service** first. Simple, easy to demo and rollback. AWS EC2 size/price is to be verified against real memory usage (numpy/pandas/scikit-learn/timezonefinder are not tiny).
- Use app-level canary only as an inexpensive **simulation**; do not confuse it with load-balancer canary. Record which version served each request.
- For async, SQS holds pointers, not GPS arrays. Sensitive payloads and results require SSE encryption, restricted IAM, expirations and explicit cleanup.
- Avoid introducing MLflow and a full model registry platform just to version two deterministic heuristics. Use a checked-in manifest with Git SHA, config fingerprint and immutable release label; S3 can store version manifest/releases on AWS. Add MLflow only if necessary.
- No real-time "drift" inference from a static 2007–2012 dataset. Only offline chronological replay.

## Deferred EDA TODO — do not block serving

- [ ] **Cross-file universal user chronology comparator**: all .plt records per user sorted by timestamp, overlap/duplicate reconciliation, CP1 continuity segmentation; compare with targeted Stage 09.
- [ ] **CP1 parameter sensitivity after ingestion audit**: gap/dwell/radius isolated experiments; stay-user coverage and downstream label stability, not just number of stays.
- [ ] **Structured missingness**: overnight/work-window and block dropout vs random dropout, confidence/abstention sensitivity.
- [ ] **Trackintel implementation ablation**: duplicate handling, include_last and window semantics on equal input.
- [ ] **Experimental Stage 08c robustness** for four sparse HOME and three robust OFFICE additions; tiered labels remain research-only.
- [ ] **Historical POI categorization** only with properly licensed time-aligned POI and privacy review.

Do **not** execute these before the required Checkpoint 2/3 deliverables unless a blocking correctness issue appears.

## Safety/cost checkpoints before cloud apply

Do not commit GeoLife raw trajectories, precise derived HOME/OFFICE coordinates, private Volume caches, AWS credentials, Terraform state or API keys. Use budget alerts and confirm current AWS pricing/free-tier eligibility in the user's account before creating resources. Include teardown procedure. Do not expose publicly writable inference without authentication or safe network restrictions.


## Delivered Checkpoint 3 groundwork (2026-10-12)

- Added privacy-safe `geolife_http_requests_total` and `geolife_http_latency_seconds` Prometheus metrics labeled by route template, status, method, and allowlisted model variant. Metrics disabled without `GEOLIFE_METRICS_BEARER_TOKEN`; protected `GET /internal/metrics` (not public OpenAPI).
- Added `scripts/benchmark_sync.py`: HTTP client-side synthetic benchmark producing p50/p95/p99 latency, status counts, and baseline-vs-canary model counts; measurements need an actual running service and have **not** been claimed here.
- Async SQS, latency comparison, CloudWatch dashboard, and replay drift are still **TODO**. No GeoLife private cache or user trace is used by synthetic benchmarks.
