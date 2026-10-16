# Track B1 S2b — AWS SQS synthetic-only deployment handoff

**2026-10-16. Status: CODE + TERRAFORM ONLY, NOT DEPLOYED.** PR #78 is stacked on S2a PR #77. No Terraform apply, AWS permissions, EC2 restart, Cloud credentials, network rules or actual SQS queues changed.

## Architecture: what will run after explicit AWS approval

Authenticated user (restricted internal demo session) submits POST /v2/jobs with a unique Idempotency-Key and an enum fixture such as three_night_home. The request **cannot contain raw user GPS, GeoLife participant IDs or arbitrary file paths**. The server derives the account ID from its verified SQLite demo session, stores the fixed synthetic fixture JSON encrypted in a private S3 bucket, creates an owner-bound DynamoDB job record (15-minute visibility TTL), and sends an SQS Standard message containing **only an opaque job_id**. It returns HTTP 202 plus a polling Location header.

A bounded worker uses SQS ReceiveMessage to get job_id, conditionally claims the DynamoDB job with a lease token, fetches the S3 synthetic fixture, invokes the existing GeoLife CP1/CP2 model on hard-coded *fictional* GPS generated in memory, then writes only aggregate status (HOME/OFFICE emitted/abstained, stay count and model version). On success it deletes the SQS message and best-effort removes the S3 payload. The authenticated GET /v2/jobs/{job_id} endpoint enforces owner and TTL; unknown/foreign/expired jobs all return 404. No Evidence Score or coordinates in the public response.

## Files in this PR

- src/geolife/serving/aws_s2b.py — guarded boto3 S3/DynamoDB/SQS adapter, conditional worker lease, at-least-once retry, DLQ and owner-bound HMAC idempotency.
- src/geolife/api/async_jobs.py and openapi.yaml — POST/GET job API, disabled by default unless GEOLIFE_S2B_ENABLE=1, existing restricted bearer AuthN required.
- scripts/run_s2b_synthetic_worker.py — bounded polling worker, no account credentials printed.
- scripts/benchmark_s2b_private_synthetic.py — samples **complete sync response**, **async HTTP 202 ACK** and **async full time-to-result** separately. Never equate ACK latency with completed inference.
- infra/terraform/async_s2b/ — independent Terraform state root for private SSE-S3 bucket with 1-day lifecycle, DynamoDB TTL/PAY_PER_REQUEST, encrypted SQS Standard + DLQ, CloudWatch DLQ alarm. No public API, new EC2, SG ingress, role creation or IAM attachment. IAM policy JSON is an **output for human review only**.
- tests/test_s2b_aws_synthetic_integration.py — mocked AWS moto checks, not real AWS.

## Security limitations and explicit acceptance gates

SQS Standard is at least once and may redeliver. Worker uses DynamoDB conditional state and lease fencing; once the lease expires, duplicate computation is still possible but a stale token cannot overwrite a newer result. Worker visibility 120 seconds and lease 110 seconds are sized for synthetic toy inference **only**. Production or heavier jobs require heartbeat, visibility extension, per-user admission limits and independent operational review.

DynamoDB TTL is eventual: reads check expires_at explicitly. S3 lifecycle expiration (one day) is asynchronous and **does not guarantee a fifteen-minute physical erase**. Failed SQS sends after a successful S3/DDB write may require repeating the same idempotency key; a stranded synthetic object remains until lifecycle cleanup. Worker deletes S3 on normal success. **Never upload private GeoLife cache or actual user GPS into this research experiment.** The demo account mapping to GeoLife 000 is not proof of ownership.

The new resources and existing EC2/EBS/public-IPv4/logging can incur real charges. S3/DynamoDB/SQS encryption uses AWS-managed service encryption, not separately billed customer KMS keys. Terraform only emits scoped IAM policy JSON; operator must separately review/attach it to an approved instance identity. The CloudWatch alarm has no notification recipient until approved. Do not expose Vite or FastAPI to a public port or copy tokens to GitHub.

## Local test without AWS

In Windows PowerShell from repository root:

    git fetch origin
    git switch feature/track-b1-s2b-aws-sqs-serving
    python -m pip install -e ".[dev]"
    python -m pytest -q tests/test_s2_async_job_contract.py tests/test_s2b_aws_synthetic_integration.py
    terraform -chdir=infra/terraform/async_s2b init -backend=false -input=false
    terraform -chdir=infra/terraform/async_s2b validate

Python CI runs moto and the Terraform root is validated without apply. The tests require no AWS account or Modal Volume. The CP1/CP2 private baseline remains unchanged.

## Operator approval and actual AWS demo (NOT YET RUN)

**First obtain explicit approval of AWS cost/scope/role policy and storage cleanup.** The operator must verify the AWS account, chosen ap-southeast-1 region, existing EC2/SSM state and costs, and review the S2b Terraform plan. Plan/apply uses only infra/terraform/async_s2b as its state root; never import or modify the original EC2 Terraform state. Do not enable extra inbound SG or public endpoint.

After plan approval: apply only this root; review the manual_ec2_iam_policy_json Terraform output; use a specifically permitted IAM change to grant S3/DynamoDB/SQS access to the already approved EC2 execution identity; store a stable 32+-byte GEOLIFE_S2B_HMAC_SECRET in a protected operator mechanism, never repo/tfvars/log. Set GEOLIFE_S2B_ENABLE=1 and scoped bucket/table/queue URL only inside the SSM-restricted EC2 process. Start FastAPI and bounded worker, then connect via SSM tunnel to localhost:8000.

Verify: (1) successful authenticated job creation/202 and polling, (2) account A cannot poll B, (3) job replay/idempotency, (4) synthetic worker failure and DLQ, (5) actual CloudWatch counts; run the private benchmark using a short-lived GEOLIFE_DEMO_TOKEN environment variable, not CLI argument. Capture sanitized latencies separately: sync p50/p95/p99, async ACK p50/p95/p99 and async full completion p50/p95/p99, failure rates, number of requests. This is single-worker sequential synthetic evidence, **not** production load.

On completion shut down as approved, delete test resources only after saving redacted reports, inspect DynamoDB/S3/queues and existing EC2/EBS/ECR/public IPv4 cost exposure. S2b is not accepted until actual AWS runs and metrics are confirmed. Original Checkpoint 3 monitoring dashboard + simulated chronological drift are still future tasks.

## Official references

- [SQS Standard at-least-once](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/standard-queues-at-least-once-delivery.html)
- [Visibility timeout](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-visibility-timeout.html)
- [Dead-letter queues](https://docs.aws.amazon.com/AWSSimpleQueueService/latest/SQSDeveloperGuide/sqs-dead-letter-queues.html)
- [DynamoDB conditional operations](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Expressions.ConditionExpressions.html)
- [DynamoDB TTL eventual deletion](https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/TTL.html)
- [S3 SSE-S3](https://docs.aws.amazon.com/AmazonS3/latest/userguide/default-bucket-encryption.html)
- [S3 asynchronous lifecycle](https://docs.aws.amazon.com/AmazonS3/latest/userguide/lifecycle-expire-general-considerations.html)
