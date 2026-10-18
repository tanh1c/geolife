# GeoLife — Unified Master Roadmap: Track B1 đầy đủ + hướng sản phẩm mới

**Ngày hợp nhất:** 2026-10-15  
**Trạng thái:** ROADMAP / ACCEPTANCE PLAN, **không** có nghĩa các hạng mục chưa thực hiện đã PASS.  
**Source of truth:** (1) *đề bài Track MLE Home/Office/POI Inference — Track B1* do mentor giao, Checkpoint 1–3, cùng bonus; (2) [roadmap post-AWS 15/10 ưu tiên destination](2026-10-15_evidence_v2_candidate_tiers_destination_recommendation.md); (3) tài liệu triển khai/kiểm thử hiện có của repository. Các số liệu Modal/AWS thực nghiệm là **operator-reported**, khác với CI synthetic.

## 0. Nguyên tắc hợp nhất — KHÔNG bỏ nghĩa vụ đề bài

**Hai workstreams bổ trợ nhau, không thay thế nhau:**

- **B1 contract closure**: đạt đầy đủ deliverables Checkpoint 1, 2, 3; checkpoint 3 vẫn yêu cầu async SQS + so sánh sync/async + monitoring dashboard + simulated drift + E2E.
- **Product/research extension**: theo roadmap ưu tiên 15/10, làm **Private Destination Recommendation MVP trước**, định vị các POI, đồng thời nghiên cứu application identity/Cognito/OIDC và bảo mật từng lớp để sau này hỗ trợ người dùng thực. Evidence v2 Stage10a–10l là **research audit đã khép lại và không deploy**.
- Các hoạt động tạo cloud resources, public ingress, quyền IAM mới, dữ liệu người dùng thực và privacy-sensitive exports cần **phê duyệt riêng + cost guardrail**; update roadmap không tự cấp quyền triển khai.
- Có thể làm **song song trên nhánh/PR độc lập**, nhưng tuyệt đối không tuyên bố Track B1 hoàn tất nếu Checkpoint 3 chưa đạt, hoặc coi recommendation là bằng chứng HOME/OFFICE semantic accuracy.

## 1. Ma trận đầy đủ: đề bài ban đầu → bằng chứng hiện có → việc còn thiếu

### Checkpoint 1 (Tuần 1–2) — model & API Spec

| Yêu cầu gốc | Trạng thái ngày 15/10 | Bằng chứng / việc còn phải xác nhận |
| --- | --- | --- |
| Repo, môi trường, IaC/Terraform setup | **DONE** | Có cấu trúc src/model/API/tests và Terraform. Terraform thuộc AWS deployment đã chạy sau CP1. |
| Microsoft GeoLife ingestion & GPS noise/speed cleaning | **DONE** | Audit 18.670 `.plt` trajectory files, parity 5.821 stays, 136 users có stays. |
| GMT/UTC trong PLT → local time trước khi áp heuristic | **DONE** | Nâng cấp per-stay IANA timezone theo tọa độ, thay cho quy tắc Asia/Shanghai toàn cục. |
| Stay detection (time/distance thresholds) + tuning | **DONE** | Frozen 300 s continuity / 200 m radius / 20 phút dwell; CP1 sensitivity 27 cấu hình và same-second audit. |
| Night HOME / weekday OFFICE heuristic | **DONE** | Complete-link 200 m recurring clusters, frozen HOME 27, OFFICE 16; hợp lệ khi đủ ngưỡng, có abstain. |
| OpenAPI/Swagger `/v1/classify/{user_id}`, typed schema/errors, versioning & examples | **DONE** | API spec YAML, FastAPI v1 compatibility, v2 serving contract và regression tests; cần **đồng bộ tài liệu v1 còn nhắc Beijing-only**. |
| `confidence` heuristic được định nghĩa rõ | **DONE** | `evidence_strength=(S+M+min(days/5,1))/3`, không calibrated probability; v2 score offline **không promote**. |
| Manual plausibility review | **DONE, sample-limited** | Purposive HOME/OFFICE/abstain review; không có ground-truth accuracy, không tuyên bố tỷ lệ đúng %. |

**CP1 acceptance:** nguồn code và OpenAPI build/test PASS, frozen privacy-safe aggregate parity; report giới hạn manual check. **Remaining doc polish:** tránh legacy timezone/geography drift.

### Checkpoint 2 (Tuần 3–4) — AWS deploy, variants, deploy strategy

| Yêu cầu gốc | Trạng thái ngày 15/10 | Gap / acceptance |
| --- | --- | --- |
| FastAPI implementation + Docker image | **DONE** | Restricted Docker `GEOLIFE_PRIVATE_DEMO=1`, signed-off PR #72. |
| AWS running callable public **hoặc** internal endpoint | **DONE for restricted internal demo** | PR #73 merged `cb4fe7ca`; ECR digest pinned, EC2 c7i-flex.large via SSM-only tunnel, no SG ingress. No public deployment. Verify stopped/remaining billable AWS resources separately. |
| Hai model versions có hành vi khác nhau | **DONE, adapted comparator** | Frozen complete-link 200m baseline vs DBSCAN 100m candidate, synthetic distinctness test. **Deviation**: đề bài ví dụ per-stay heuristic v1 vs DBSCAN clustered v2; per-stay-v1 standalone vẫn chưa implement. Đề nghị mentor xác nhận cặp comparator thích nghi là đủ; nếu không, thêm minimal per-stay benchmark branch, không thay baseline. |
| Version inventory / registry hoặc naming alternative | **DONE minimum, improve docs** | Git SHA/image digest/release ID + model variant naming; chưa có MLflow/S3 model registry, không bắt buộc nếu mentor chấp nhận naming convention. Tạo bản comparison manifest rõ two variants/config/hash. |
| Ít nhất một deploy strategy chạy thực tế | **DONE: application-level sticky canary** | Operator-reported baseline→100% DBSCAN→rollback synthetic HTTP PASS trên AWS. Chưa đo tỷ lệ 90/10 qua nhiều accounts; nếu mentor yêu cầu, test 100+ **synthetic distinct account IDs** với lưu lượng đủ, thống kê account-level allocation và confidence interval; không coi một account 50 requests là 50 independent assignments. |
| Học/giải thích Shadow / Canary / Blue-green | **PARTIAL** | Có Canary đang chạy; bổ sung **bảng so sánh và sơ đồ** 3 cách trong demo/mentor slides; Shadow và Blue-green chỉ cần giải thích, không cần cả hai triển khai vì đề bài yêu cầu *ít nhất một*. |
| CI/CD | **DONE CI/build/test; deployment automation limited** | Python tests, Docker smoke và Terraform formatting; manual ECR push/SSM deployment handoff. Không gọi đây là CD fully automated. |

**CP2 acceptance:** model endpoint chạy restricted AWS, metadata phiên bản, proof canary/rollback, tài liệu so sánh ba strategy và bảo vệ dữ liệu. Không buộc public ingress.

### Checkpoint 3 (Tuần 5–6) — **chưa hoàn thành, không được defer khỏi Track B1 completion**

| Yêu cầu gốc | Trạng thái ngày 15/10 | Minimum acceptance chưa đạt |
| --- | --- | --- |
| Sync request-response & client observed latency | **DONE** | Synthetic baseline 50/50, p50/p95/p99 127/157/179 ms qua SSM; không concurrent load. |
| Async SQS → worker/Lambda → store result → poll/callback | **NOT IMPLEMENTED** | `POST /v2/jobs` returns 202 + job ID; encrypted restricted TTL store; **SQS message carries pointer/job ID ONLY, never raw GPS**; worker idempotent, status pending/running/succeeded/failed, DLQ/retries, `GET /v2/jobs/{id}` authenticated & resource owner scoped; tests of error and duplication. |
| Real sync vs async latency comparison | **NOT DONE** | Same synthetic payloads/workload/machine region: record sync end-to-end p50/p95/p99 vs async enqueue acknowledgment **and** queue wait/process/full-completion separately (do not compare ack with sync result as equal workloads); report timeout/error/throughput/queue depth. |
| Monitoring latency/error rate / operational logs | **PARTIAL** | Request counters and latency histogram in source; CloudWatch log stream observed. Need instrument/collect per model/route, time-window p50/p95/p99, 4xx/5xx, abstention, job states, SQS queue/DLQ and safe aggregate sizes; no GPS/user IDs/tokens in logs/metrics labels. |
| CloudWatch/Grafana dashboard + basic alert | **NOT DONE** | Actual dashboard screenshots, latency/error/queue charts, alarm test with controlled synthetic failure; no false claims of production observability. |
| Basic drift via chronological trajectory replay | **NOT DONE** | Privacy-safe offline chronological replay, compare feature distributions across fixed windows and detect injected synthetic shift; dashboard mark `simulated_offline_replay`, never "live production drift" (GeoLife static 2007–2012). |
| End-to-end mentor demo & slides | **PARTIAL** | Complete narrative GPS request→auth→sync inference→canary→async job→log→dashboard/drift; runbook, scoped cost / teardown proof, limitations and architecture. |

**CP3 release gate:** **ALL** async, sync-v-async comparative numbers, operational dashboard and offline simulated drift artifacts PASS before marking entire six-week Track B1 **DONE**. AWS additional resources require prior budget/IAM/security review.

### Bổ sung/bonus và phạm vi dữ liệu

| Yêu cầu gốc | Trạng thái | Hướng hoàn tất |
| --- | --- | --- |
| Stay-point threshold tuning | **DONE** | Preserve CP1 baseline and research scope. |
| Heuristic-vs-DBSCAN benchmark | **PARTIAL** | Two clustering variants compared; document the difference vs mentor's original *per-stay-vs-cluster* comparator and get mentor acceptance; optional implement old direct heuristic to close exact gap. |
| POI categories via reverse geocode / H3 | **BONUS NOT DONE** | Test small licensed/reference POI lookup, coordinate reference/time alignment and explicit UNKNOWN; old/historical POI labels must not be inferred from current maps without caveat. No need for accurate category if source/licence unavailable. |
| Privacy risk analysis: geohash coarsening, k-anonymity | **PARTIAL** | Threat model/authenticated scope/3-decimal rounding implemented/documented; **rounding/geohash != anonymity**, k-anonymity not proven. Add qualitative attack scenarios, compare coarsening utility vs privacy and scoped k-anonymity only if mathematically/privacy justified; default keep sensitive markers restricted. |
| Gowalla/Brightkite comparator only | **NOT DONE in repo** | One separate lightweight notebook/sample and summary: check-in events do NOT provide dense dwell duration, compare inter-observation gaps, unique active days, repeat-place, sparsity and missingness (units carefully defined). **No end-to-end HOME/OFFICE pipeline**, no semantic ground truth claim. Official Stanford SNAP sources: [Gowalla](https://snap.stanford.edu/data/loc-gowalla.html), [Brightkite](https://snap.stanford.edu/data/loc-brightkite.html). Check license/ethics and avoid exporting per-user coordinates. |

## 2. Lịch thực hiện tích hợp (ưu tiên mới nhưng đạt đủ contract)

Các "Sprint" ở đây là **thứ tự thực thi đề xuất, không gán ngày bắt buộc** hoặc khẳng định Track B1 hoàn tất đúng sáu tuần.

| Sprint | Workstream và chủ đề | P0/P1 deliverable | Acceptance gates (cần bằng chứng) |
| --- | --- | --- | --- |
| **S0 — Close verified baseline** | Chốt PR #73 merged, review PR #74 docs nếu được, giữ CP1/CP2 v1; kiểm tra AWS cost resources | Handoff + model manifest + sửa legacy docs; 1 sơ đồ Shadow/Canary/Blue-green | CI PASS, no public ingress/data exposure, cost/shutdown inspected |
| **S1 — Product priority** | **Private Destination Recommendation MVP** theo roadmap ưu tiên mới; song song viết AuthN/AuthZ design | Synthetic/consented Top-3, baseline frequency/recency, origin/time/weekday/context, reasons & abstention; held-out Hit@K, Recall@K, no-suggestion | No data leakage/semantic label invention; ranking is **not** HOME/OFFICE confidence; no user data AWS |
| **S2 — CP3 async required** | SQS + private encrypted TTL storage + worker + GET jobs | Working status transition, auth owner isolation, retries/DLQ, safe queue pointer, idempotency, no GPS logs | Demo `POST → queue → worker → result → poll`, duplicate/failure tests, sync-vs-async benchmark |
| **S3 — CP3 observability required** | CloudWatch dashboard, metrics, alerts, simulated offline drift | Per-version latency p50/p95/p99/error/abstention & queue, replay chart, safe alert | Dashboard screenshot, tested alarm, reproducible injected drift, explicit simulated label |
| **S4 — Full-track gap closure** | Gowalla/Brightkite small comparator, privacy risk memo, 3 deployment strategies diagram, original comparator evaluation with mentor | Comparison notebook + threat model + POI bonus if feasible/approved | No semantic claims from check-ins; documentation quality check; bonus identified separately |
| **S5 — Final acceptance** | Full demo + presentation 6-week deliverables and extensions | README reproducibility, architecture, sync/async/recommender/security demonstration and metrics, QA signoff | CP1, CP2, CP3 ALL independently marked done or transparently pending; teardown/cost proof |

**Parallel research/security workstream (does NOT block S1 offline synthetic research):**
- **A:** Diagram `OIDC identity (iss+sub) → app_user_id → data ownership`, OAuth 2.0 authorization code + PKCE, Cognito User Pool synthetic test A/B, threat model, BFF vs SPA, API JWT verification/authz; keep research GeoLife IDs disconnected.
- **B:** Compare current SSM-only private backend with future public HTTPS edge/API Gateway → VPC Link/private backend, SG least privilege, WAF/rate/body limits/TLS/consent, budget.
- **Gate:** do **not** deploy Cognito or public ingress before separate user approval, spending estimate and privacy/security review. Once approved, demo synthetic OIDC login and negative 401/403/object-level tests.
- **Product privacy:** numeric CP2 evidence index stays internal; UI may display interpretable observed/inferred/abstained reasons, NOT artificial percent confidence. API public DTO should omit sensitive score/IDs/coordinates when appropriate, not just CSS-hide.

## 3. Minimum demo scripts / definition of DONE

**Scenario A — model contract:** Upload **synthetic** GPS, see HOME/OFFICE/OTHER_RECURRING or abstain, correct response metadata, evidence as heuristic internal only. v1 OpenAPI spec reviewable. No real historical user identity mapping.

**Scenario B — release control:** SSM-only internal AWS service, manifest of two variants, baseline→DBSCAN canary→rollback, synthetic safe CloudWatch log. One of three strategies implemented, differences of all three explained. If requiring 10% traffic, distinct-account bucket test with fixed salt and no privacy leak.

**Scenario C — recommendation:** anonymous synthetic fixture or authenticated test user's own consented places, time-contextual Top-3 destination ranking and reason, recorded Hit@3/Recall@3 and no-suggestion with chronological held-out observations. HOME/WORK not promoted from unlabeled check-ins.

**Scenario D — asynchronous delivery:** Same synthetic request through `POST /v2/jobs`, poll authorized `GET /v2/jobs/{id}`, worker response, DLQ negative case; client measured time to result and initial ACK separately.

**Scenario E — monitoring/drift:** CloudWatch dashboard with model-specific p50/p95/p99, error, no-suggestion/abstention and SQS DLQ/queue lag; injected synthetic deviation and offline chronological replay clearly labeled simulated. Failure alarm test with sanitized logs.

**Scenario F — privacy/auth:** Demonstrate anonymous request rejection and test user A↔B isolation, no GPS in queue/logs, scope of demo SQLite vs future Cognito principal; cost and access boundary recorded; no public private GeoLife data.

**Track completion rule:** When Checkpoints 1, 2 and **3** meet the original acceptance criteria above and final demo packet exists, mark original B1 DONE. Destination Recommendation, Cognito/OIDC and POI bonus are distinct extension outcomes; extra research cannot count as a substitute for missing async/monitoring.

## 4. Integration details & official documentation

- [Original Track B1 historical plan](track_b1_delivery_roadmap.md): preserves 2026-10-12 pivot and deferred EDA list as historical.
- [Agreed post-AWS product roadmap](2026-10-15_evidence_v2_candidate_tiers_destination_recommendation.md): maintain new priorities and mentor security feedback.
- [CP1 baseline validation](../design/02_staypoint_baseline_validation.md), [OpenAPI v1 contract](../design/02_checkpoint1_api_spec.md), [manual plausibility](../evaluation/01_home_office_manual_plausibility.md).
- [Model versioning](../deployment/02_model_versioning.md), [metrics foundation](../deployment/03_monitoring_foundation.md), [AWS operator handoff](../deployment/08_aws_ssm_deployment_handoff.md).
- [AWS SQS queue type/reliability](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-queue-types.html), [dead letter queue](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html), [CloudWatch metric/dashboard/alarms](https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/GettingSetup.html).
- [Cognito OAuth code+PKCE](https://docs.aws.amazon.com/cognito/latest/developerguide/federation-endpoints-oauth-grants.html), [Cognito managed login](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-managed-login.html), [API Gateway JWT](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html), [private VPC integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-private.html).
- [Stanford SNAP Gowalla](https://snap.stanford.edu/data/loc-gowalla.html), [Brightkite](https://snap.stanford.edu/data/loc-brightkite.html): both are sparse check-in datasets, not sustained GPS stay traces.

**Non-goals of this roadmap PR:** No code, production model score, CP1/CP2 threshold, API contract, Terraform apply, new AWS resources, real-person account signup, or GeoLife historic private-data access is changed merely by documenting the above.
