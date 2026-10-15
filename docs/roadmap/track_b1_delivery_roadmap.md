# Track B1 — MLE delivery roadmap (post-EDA pivot)

> **Current checkpoint (2026-10-15):** Original 2026-10-12 roadmap below is a historical plan. For verified-vs-pending Track B1 checkpoints, see **[2026-10-15 delivery/research status update](#2026-10-15--roadmap-checkpoint-what-is-done-and-what-remains)** at the end, [milestone report](../../reports/milestone/2026-10-15_progress_update_vi.md) and AWS [PR #73](https://github.com/tanh1c/geolife/pull/73). Stage10 offline Evidence v2 was concluded without score migration; see [Stage10 research decision](../eda/45_evidence_v2_final_decision.md). Do not treat older TODO rows as current deployment status.

Updated: 2026-10-12. Status: **IMPLEMENTATION PLAN, NOT A CLAIM OF DEPLOYMENT**.

## Objective and scope

Ship a reviewable, working MLE service from raw GPS request to HOME/OFFICE inference, versioned routing, async serving and operational metrics. The objective of the six-week brief is working engineering, **not** maximized semantic coverage or GeoLife ground-truth accuracy.

Freeze the current production reference while delivering infrastructure:

- CP1 fixed cleaning/stay-point semantics: same-second 10m, gap 300s, speed guard 1,200km/h, stay radius 200m, minimum dwell 20 minutes.
- CP2-v2 uses complete-link max diameter 200m, per-stay IANA timezones and abstention. Frozen full-release result: 5,821 stays, HOME 27, OFFICE 16.
- Stage 08c experimental tiers (HOME 36, OFFICE 19) **are not** production. Stage 09 file stitching (5,821 -> 5,831 stays; no new stay users or HOME/OFFICE emissions) is a research comparator, not a migration.

The existing **v1 API stays in code** for backward-compatible Python parity tests but is blocked in the restricted Docker/demo deployment. A more sensible **v2 serving contract** is specified in `docs/design/05_serving_api_v2_proposal.md`; it will be implemented and tested explicitly, not silently substituted for v1.

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


## Authenticated two-mode GeoLife map demo (2026-10-13)

Implemented **on the delivery feature branch**: a private admin-provisioned account mapped to one GeoLife 000–181 pseudonymous ID, revocable 30-minute bearer sessions, two routes for fresh uploaded GPS versus the existing private CP1 stay cache, and an opt-in map with rounded HOME/OFFICE/OTHER_RECURRING markers. The experimental demo is intended for internal use; there is no verified identity of the original dataset contributors and no AWS deployment.

Additional TODO before internet-facing use: external auth and HTTPS ingress policy for old compatibility endpoints, security review, rate/body-size limits, secrets and permission hardening, retention policy, self-hosted tiles or third-party map privacy review. See \`docs/deployment/04_authenticated_geolife_map_demo.md\`. Dataset users without stays may return a valid abstention; semantic POI categories remain out-of-scope.


## Immediate merge gate — private CP1 real-data E2E

- [x] Local browser/synthetic account, new PLT, HOME, abstention and map interactions tested by operator (2026-10-13); Python CI and Docker smoke also PASS.
- [x] Prepare `scripts/modal_real_data_e2e.py` and synthetic auditor tests on serving branch. **This is tooling only, not Modal proof.**
- [x] **Real-data E2E PASS (2026-10-13, operator-provided Modal output)**: frozen CP1/CP2 counts (5,821 stays, 136 stay users, HOME 27, OFFICE 16; 2,015 locations, 716 recurring, 104 recurring users), 4/4 user-case types, authenticated map parity, no cross-ID override, session revocation and synthetic new-GPS path. See `docs/deployment/06_modal_real_data_e2e_result.md`.
- [ ] Review internal-only security and privacy restrictions on disclosure of even 3-decimal HOME/OFFICE map coordinates before approving merge.
- [ ] Review/merge PR #72; only after that begin AWS deployment work on a separate branch.

See `docs/deployment/05_modal_real_data_e2e.md`.

## 2026-10-13 — Restricted internal-demo security review

Review: `docs/deployment/07_security_review_pre_merge.md`. The previous parallel anonymous inference endpoints are now blocked in Docker/private demo runtime (`GEOLIFE_PRIVATE_DEMO=1` or configured auth DB), while standalone v1 Python parity remains available. Added no-store/CSP/clickjacking headers, declared-content-length 3 MiB rejection, Docker regression checks, and security test coverage. **Residual public-deployment blockers:** no independently verified identity of GeoLife original participants; historical HOME/OFFICE coordinates remain sensitive even after rounding; trusted pickle supply chain; chunked body cap, TLS/restricted ingress, rate limiting, centralized account lifecycle and cloud secret/IAM controls. Merge only as internal research code after review and green CI; public AWS exposure is not approved.


## 2026-10-15 — Roadmap checkpoint: what is done and what remains

The original delivery plan above is superseded by this **factual addendum for status**; the original tasks/acceptance criteria still explain project intent. Operator-reported AWS and private Modal acceptance is distinct from GitHub CI. No private GPS dataset or production deployment is implied.

| Workstream | Measured / verified by 2026-10-15 | Remaining acceptance |
| --- | --- | --- |
| P0 serving/FastAPI | PR #72 merged to `main`; authenticated internal-only FastAPI v2 map with synthetic/new-GPS and private dataset mode under scoped accounts; CP1/CP2 frozen baseline, alternate complete-link 200m vs DBSCAN 100m | Keep public security restrictions; private data not deployed to AWS |
| P0 Docker & API CI | Python CI and Docker smoke PASS for merged PR #72 and current open PR #73 (head `b5528042`) | Release review/merge PR #73 only after human approval |
| P0 AWS single-host sync serving | Operator-reported ECR digest-pinned container served authenticated synthetic inference via local SSM port-forward to EC2; SG ingress []; CloudWatch log stream populated | No public HTTPS/Internet ingress; current post-test EC2 shutdown/billing state unverified |
| P1 authenticated rollout | Operator-reported baseline→100% DBSCAN canary→baseline rollback all succeed on one sticky synthetic account, 50/50, 50/50, 10/10 requests | **90/10 routing distribution across multiple synthetic accounts unverified**; no zero-downtime blue-green/shadow implementation |
| P1 latency benchmark | p50/p95/p99 from client over SSM: baseline 127/157/179 ms, 100%-DBSCAN 146/273/512 ms, rollback 127/201/234 ms | Concurrent/replay load, throughput, error budget, true external network latency not measured |
| P1 observability | App HTTP counters and latency histogram, protected internal metrics and CloudWatch log events | CloudWatch dashboard, collection of p50/p95/p99 by version, uptime/error/abstention plots and a privacy-safe simulated chronological drift replay **not deployed** |
| P1 async jobs | Not started as deployed flow | SQS pointer-only queue, encrypted/TTL private payload and results, async worker, idempotency/retries/DLQ, polling `/v2/jobs/{id}`, sync-vs-async comparison |
| Offline Evidence v2 study | Stage10a–10l operator-reported complete; [decision record](../eda/45_evidence_v2_final_decision.md); PR #74 open, CI/docker smoke PASS at prior head `ceddc4f` | **Do not promote** scalar v2; no new 10m on only nine comparable cases |
| HOME/OFFICE coverage EDA | Prior Stage08a/08c tiered candidates HOME 36 / OFFICE 19 research-only; Stage09 stitching comparator 5,831 vs frozen 5,821 stays had no additional stay users or emissions | **Separate future research**: cross-file trajectory chronology/duplication audit → eligibility waterfall → controlled gate sensitivity → independent semantic labels |

### Recommended next execution order

1. **Finish Track B1 sync demo handoff first:** review PR #73 with current CI, preserve Terraform state/image digest and verify AWS runtime/billable assets are stopped/teardown as intended. If required by evaluator, test per-account sticky 90/10 with many synthetic accounts; a 100% canary test does not establish 90/10. Do not restart EC2 just to repeat already-passed synthetic baseline/100% tests.
2. **Implement P1 async SQS POC** after scoped privacy/IAM/cost review: `POST /v2/jobs` creates a unique job ID; store a synthetic-only request in encrypted restricted TTL storage; publish job ID/pointer to SQS (never GPS bodies); worker processes idempotently; `GET /v2/jobs/{job_id}` requires auth; record queued/running/succeeded/failed and retry/DLQ behaviour; demonstrate against real restricted service and benchmark sync vs async. No historical per-user GeoLife private data.
3. **Complete monitoring/mentor demo pack:** Prometheus metrics/sanitized CloudWatch logs, model/version-specific latency/error/abstain aggregates, cost/teardown proof, synthetic replay marked `simulated_offline_replay`, screen recording or screenshots, architecture and privacy boundaries. Do not label static GeoLife replay as live production drift.
4. **Then reopen EDA as a separate workstream:** user-level global chronology across `.plt` files, duplicate overlap/stitching validity, CP1 stay-user and CP2 emission waterfall by exposure group, one-variable strict threshold sensitivity on a frozen control, outcome/abstention tracking, never automatically migrate research tiers to production. Acquire independent semantic truth for actual accuracy/scoring claims.

**Roadmap decision:** Track B1 has progressed beyond “infrastructure ready” to **restricted private AWS sync demo demonstrated**. It has **not** met the full original definition of done requiring async jobs and dashboard/replay. Stage10 v2 audit is **research-closed** rather than successful score replacement. Neither PR #73 nor PR #74 should be auto-merged or used to change production policy in this documentation update.
