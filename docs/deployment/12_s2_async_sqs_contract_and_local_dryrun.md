# Track B1 Checkpoint 3 — S2a async SQS contract and local dry run

**Date:** 2026-10-16  
**Status:** offline design + standalone synthetic unit-test simulator. **NO SQS queue, worker, API job endpoint, private storage or additional AWS resource has been deployed.** S2a cannot satisfy the original async deliverable until S2b runs against actual AWS SQS and measures real sync/async latency.

**Roadmap:** Original B1 Checkpoint 3 remains mandatory after S1 private Destination Recommendation MVP; see the [Unified Master Roadmap in PR #75](https://github.com/tanh1c/geolife/pull/75). No change to frozen CP1/CP2, Evidence v1, AWS SSM-only deployment, or GeoLife data policy.

## 1. Intended public-facing job API (future; NOT implemented)

```text
Authenticated caller
  POST /v2/jobs  (Idempotency-Key, synthetic-only request data)
    -> Validate auth/limits, derive account owner server-side
    -> Write payload to private encrypted TTL object storage
    -> Write job record/status to private metadata storage
    -> SendMessage(SQS): {"job_id": "<opaque UUID>"} ONLY
    -> HTTP 202 { job_id, status:"pending" }

  Worker (private IAM role, synthetic-only)
    -> ReceiveMessage(job pointer)
    -> Resolve owner & encrypted payload internally
    -> Atomic claim / idempotency guard + fixed model version
    -> Store result/status (encrypted & TTL); delete message
    -> transient failure -> retry with visibility timeout / DLQ

  Authenticated caller
  GET /v2/jobs/{job_id}
    -> Verify session AND same-account ownership server-side
    -> pending / running / succeeded / failed / expired
    -> 404 for unknown or foreign job, no foreign-owner enumeration
```

The API accepts **no client-supplied GeoLife `dataset_user_id`**, no user-selected file path and no bearer token/credentials in job IDs. The local research simulator does not expose these HTTP routes yet; do not claim otherwise.

## 2. Contract acceptance gates and safeguards

| Aspect | Contract / future check |
| --- | --- |
| SQS message payload | **ONLY `{"job_id": "opaque-string"}`**; no GPS, account ID, payload_ref, inference result, coordinates, raw request, auth token or bearer session |
| AuthN + AuthZ | Require existing private demo account (future replace with Cognito/OIDC). `(principal, job_id)` lookup must enforce per-user ownership. Foreign and unknown jobs should both return 404 |
| Payload and results | Private encrypted object storage with explicit IAM; TTL/lifecycle cleanup, no permanent GeoLife participant cache. For synthetic test, only `private-test://...` handles |
| Job lifecycle | pending → running → succeeded OR retry → failed, immutable terminal state and replay-safe processor |
| SQS at-least-once | Duplicate delivery must not execute completed job twice or corrupt result. SQS Standard delivery is **at least once**, not exactly once; use idempotent state transitions |
| Retry / DLQ | Handle visibility timeout and retry budget, test injected transient/permanent worker failures and DLQ visibility; do not log exception bodies containing user GPS |
| Production guardrails | No API public ingress; SSM-only EC2 and currently scoped IAM unchanged. S2b requires approved roles/queues/storage and budget; don't assume free tier |
| Privacy | Sanitized metrics/logs only: model ID, queue age, counts, approved status codes, no per-user labels or coordinates |
| Backpressure | Limit size, concurrency, TTL, worker retry storm and storage growth; SQS message size does not bound private upload bytes |
| Cleanup | Teardown plan for test queue, DLQ, private bucket, object versions, logs/KMS key costs and persisted encrypted payloads |

## 3. What is actually implemented in S2a

- `src/geolife/serving/job_simulation.py`: pure stdlib **in-memory mock**; private ledger stores `payload_ref` and account owner, queued messages are job ID pointers only.
- `SyntheticAsyncQueue.submit` deduplicates `(owner, idempotency_key)`, refuses changed payload on key reuse, and uses a bounded TTL.
- `read_for_owner` returns the same absent response for non-existent, expired or foreign jobs; no account supplied through message.
- `process_one` models duplicate/at-least-once, retry budget, an in-memory dead-letter list and terminal state; it invokes `synthetic_worker`, which does **not** run CP1/CP2 or handle real GPS.
- `tests/test_s2_async_job_contract.py` covers queue-message privacy, duplicate/replay, isolation, TTL, retries, DLQ and invalid input/result contracts.
- `scripts/demo_s2_async_contract_synthetic.py` outputs aggregate **simulation-only** success counts and clearly marks `live_sqs_provisioned=false`.

Important omissions of the mock: no real SQS visibility timer, network call, persistence, multi-worker concurrency, encryption, real worker/Lambda, IAM, queue metrics, callback or latency benchmark. Passing its tests must never be represented as Checkpoint 3 completed.

## 4. Local-only reproducibility (optional; Windows PowerShell)

```powershell
git fetch origin
git switch feature/track-b1-s2-async-local-contract
python -m pip install -e ".[dev]"
python -m pytest -q tests/test_s2_async_job_contract.py
python scripts/demo_s2_async_contract_synthetic.py
```

Expected JSON flags: `mode=offline_sqs_contract_simulation_NOT_REAL_AWS`, `synthetic_only=true`, `queue_pointer_only=true`, `live_sqs_provisioned=false`, `jobs_succeeded=1`, `attempts=1`, `sync_async_latency_benchmark=null`, `production_ready=false`. No AWS credentials, queues, Modal Volume, frontend or GeoLife cache needed.

## 5. S2b acceptance after separate AWS authorization

1. Estimate AWS cost in `ap-southeast-1` for Standard SQS, DLQ, object storage/KMS, job metadata store, worker/Lambda and logs, plus idle leftovers. Budget and IAM permissions **must be approved first**.
2. Implement actual `POST /v2/jobs` and owner-protected `GET /v2/jobs/{job_id}` in versioned API; write synthetic GPS request to encrypted TTL storage and point SQS only to the opaque ID.
3. Implement idempotent worker and durable state with conditional update/lease, bounded request body and retry DLQ; prove A account cannot read B job.
4. Run controlled synthetic sync and async on **equivalent input**; report sync full response latency, async enqueue ACK, queue wait, worker duration and **full time-to-result** separately. Do not falsely compare 202 ACK to completed sync inference.
5. Add CloudWatch privacy-safe metrics and DLQ alarm then move to S3 sprint monitoring/drift. Do not infer real-time drift from historic GeoLife data.

**Official references:** [AWS SQS at-least-once](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html), [visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html), [DLQs](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html), [SQS best practices](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-best-practices.html).

**No deployment or permission change is authorized by this documentation.**
