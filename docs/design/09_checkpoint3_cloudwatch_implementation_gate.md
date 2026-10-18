# Checkpoint 3 — proposed CloudWatch implementation sequence (NOT AUTHORIZED)

Depends on approval of [transport and cost review](08_checkpoint3_cloudwatch_transport_cost_review.md). PR #79 contains **local-only** lifecycle events and fictional drift replay; the follow-up EMF prototype is also local-only. Everything below is **review-only and unexecuted**: no AWS operation, Terraform change, IAM attachment or EC2 start is authorized.

1. **Freeze observable contract locally:** write RED tests for mapping each of the five event types to only the seven proposed CloudWatch names/units/dimensions; omit `None` durations, reject dynamic labels, GPS/job/account/token/exception text, and prove exactly 16 maximum metric identities. API `accepted`/SubmitPersistAndSend and worker lease/attempt/terminal events must both have an explicit sink. Retain existing HTTP `/internal/metrics` as a separate protected signal; do not claim its values are in CloudWatch. Simulate lost/duplicate/out-of-order delivery and worker exit without changing job state.
2. **Transport review checkpoint:** prototype one privacy-safe EMF event→line serializer in local tests, with `model` and terminal `outcome` dimensions only, timestamp in UTC milliseconds, fixed namespace and metric unit. Choose one dedicated S2b telemetry log group (proposed 7-day retention) and two distinct streams/stream prefixes for S2b API and worker, not `/geolife/dev/api`. Docker `awslogs` and a best-effort recorder must be enabled explicitly for both containers; local in-memory recorder is not that transport. Confirm SDK/CloudWatch EMF extraction constraints and document what happens if logging fails or a process exits before flush. If EMF cannot satisfy a bounded, reviewable path, compare a batch-limited `PutMetricData` prototype instead; do not silently enable both.
3. **Price and security approval:** IAM admin reviews only log-stream actions on the proposed new group for the EC2 runtime role (or `cloudwatch:PutMetricData` with namespace condition if that option wins). Operator verifies current AWS account, ap-southeast-1, SG zero inbound, immutable image digest, existing DLQ alarm/no notifications, EC2 stopped, current spend and shared free tier. Price all 16 potential series, new API+worker log bytes, group retention, dashboard SKU (currently unverified), GetMetricData/API calls and any *optional* alarm using the region catalog/Calculator. Agree a short synthetic trial budget and an owner-controlled EC2 stop. No extra alarm for the first trial; use the existing DLQ alarm.
4. **Plan-only gate:** prepare only the approved new log group/retention and dashboard if required, with smallest diff on the Checkpoint 3 branch; no S2b Terraform root or earlier PR edits. Save Terraform plan outside Git, assert allowlisted creates only and zero update/delete/replace/IAM/SG/public resources. Review any manual IAM policy text and dashboard widgets before separate apply permission; fail closed on unknown pricing, plan drift, over-budget or missing log sink. Terraform `validate` alone never authorizes apply.
5. **Separately approved synthetic-only cloud trial:** deploy by immutable digest in private SSM session, confirm S2b API and worker telemetry stream, extraction of bounded metrics and freshness, native SQS queue/DLQ depth, existing alarm state, and dashboard for sanitized fixture runs. Demonstrate `missing/stale` is distinct from `0` during worker shutdown; measure observed metric/log cost and log redaction. No real GeoLife traces, external ingress or production alert claim. Stop/remove only new trial containers, close tunnel, stop EC2 at the agreed end and verify state. Remove only new Checkpoint 3 resources under an approved teardown plan; preserve existing S2b queues, state and original API group. Store sanitized PASS/FAIL/NOT RUN evidence in a later PR commit after CI.

## Unexecuted Docker configuration for a future private trial

The dedicated **proposed** log group is `/geolife/dev/s2b-telemetry` (Standard log class, 7-day retention, created ahead of containers by an approved operator). Preserve the original `/geolife/dev/api` group and old API container. These are options to add to each separately approved S2b `docker run`, not commands to execute now:

```text
S2b API:    -e GEOLIFE_S2B_EMF_ENABLE=1 --log-driver awslogs --log-opt awslogs-region=ap-southeast-1 --log-opt awslogs-group=/geolife/dev/s2b-telemetry --log-opt awslogs-stream=s2b-api-<unique-run-id> --log-opt awslogs-create-group=false
S2b worker: -e GEOLIFE_S2B_EMF_ENABLE=1 --log-driver awslogs --log-opt awslogs-region=ap-southeast-1 --log-opt awslogs-group=/geolife/dev/s2b-telemetry --log-opt awslogs-stream=s2b-worker-<unique-run-id> --log-opt awslogs-create-group=false
```

Use a unique, non-sensitive run ID (for example a short UTC timestamp) for each API and bounded worker start; the approved IAM below matches only these prefixes. Set existing S2b resource/secret variables through the existing protected SSM-only process, never CLI text, Docker log options or Git. Never put request bodies, auth tokens or exception text on either stream. `awslogs` transports **all** stdout/stderr, not just EMF. `EmfRecorder` writes and flushes each publishable event (`leased` with unavailable duration is omitted); Python flush is not proof of Docker delivery or CloudWatch extraction. A process crash, Docker forwarding failure or IAM denial may still lose telemetry after a successful job. The worker CLI also writes one aggregate poll-count line, which is not EMF. Do not infer clean extraction from local tests.

## IAM policy for IAM-admin review only

Replace `<ACCOUNT_ID>` only after checking the target identity, existing instance profile and new log-group ARN. This is **not** an attachment instruction and does not grant group creation, retention changes, log reads, `cloudwatch:PutMetricData`, or any permission on `/geolife/dev/api`. [AWS service authorization](https://docs.aws.amazon.com/service-authorization/latest/reference/list_logs.html) specifies log-group resource type for `DescribeLogStreams` and log-stream type for `CreateLogStream`/`PutLogEvents`.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DescribeOnlyS2bTelemetryGroup",
      "Effect": "Allow",
      "Action": "logs:DescribeLogStreams",
      "Resource": "arn:aws:logs:ap-southeast-1:<ACCOUNT_ID>:log-group:/geolife/dev/s2b-telemetry"
    },
    {
      "Sid": "WriteOnlyS2bApiAndWorkerStreams",
      "Effect": "Allow",
      "Action": ["logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": [
        "arn:aws:logs:ap-southeast-1:<ACCOUNT_ID>:log-group:/geolife/dev/s2b-telemetry:log-stream:s2b-api-*",
        "arn:aws:logs:ap-southeast-1:<ACCOUNT_ID>:log-group:/geolife/dev/s2b-telemetry:log-stream:s2b-worker-*"
      ]
    }
  ]
}
```

## Dashboard definition and extraction checks (review only)

Final event mapping: `accepted` → `Accepted`, `SubmitPersistAndSend`; `leased` → `FirstLeaseWait` only when available; `attempt_failed` → `AttemptFailed`, `WorkerAttempt` when duration exists; `succeeded` → `Terminal`, `TerminalDuration` when available, `WorkerAttempt`; `failed` → `Terminal`, `TerminalDuration` when available, **never** `WorkerAttempt`. A post-commit SQS ACK failure emits an `AttemptFailed` count with no second terminal or worker-duration sample; it includes an operational post-processing failure, not necessarily failed inference. Duplicate SQS delivery of a terminal job emits no additional lifecycle metric. All counts remain best-effort/non-durable; EMF extraction can duplicate delivery.

One proposed CloudWatch dashboard, **no alarm or notification**: [review-only dashboard JSON](checkpoint3_s2b_dashboard_review.json) supplies a complete static CloudWatch `DashboardBody` for the five bounded metric widgets. It creates nothing; validate in an approved account and obtain the dashboard quote before use. The actual queue name is not baked into this proposal, so native SQS job/DLQ metrics and existing alarm state require verified queue names before any dashboard revision or apply. Review the following widget boundaries in `ap-southeast-1`:

| Widget | Definition | No-data interpretation |
| --- | --- | --- |
| New jobs and terminal outcomes | `GeoLife/SyntheticS2b` `Accepted` by each fixed model; `Terminal` by model and `outcome` (`succeeded`/`failed`), period 300 s, `Sum`. | Missing series is stale/unpublished, **not** zero success/failure. |
| Attempt errors and durations | `AttemptFailed` `Sum` by model; `SubmitPersistAndSend`, `FirstLeaseWait`, `WorkerAttempt`, `TerminalDuration` by model, 300 s `p50`/`p95` where samples suffice; keep units `Count`/`Milliseconds`. | Sparse fixtures make percentiles unreliable or absent. |
| Native queue and transport | Review JSON includes `AWS/Logs` `IncomingBytes`, `IncomingLogEvents`, `EMFParsingErrors`, `EMFValidationErrors`, `EMFDisabledErrors` with `LogGroupName=/geolife/dev/s2b-telemetry`, `Sum`, 300 s. Actual `AWS/SQS` queue depth, oldest age, DLQ visible count and existing alarm state are proposed separately until verified queue names are substituted. | SQS values are approximate; no extraction-error data does **not** prove ingestion. Check log bytes/lines and metric freshness as well. |

Verify both API/worker streams appear and contain only bounded EMF fields; compare their local expected event counts to `IncomingLogEvents` and extracted metric series. Inspect `AWS/Logs` `EMFParsingErrors`, `EMFValidationErrors`, `EMFDisabledErrors` (each `LogGroupName` dimension, `Sum`) and any extraction policy; nonzero means fail closed. A zero error value without fresh EMF lines and corresponding `GeoLife/SyntheticS2b` metrics is **not** success. EMF timestamps must be UTC epoch milliseconds within CloudWatch's 14-day-past/2-hour-future window; local fixed test timestamps do not exercise live ingestion. EMF delivery can duplicate metrics, so sums are best effort, not exactly-once counts. Existing protected `/internal/metrics` stays private and is not part of this dashboard.

## Terraform proposal, preflight and teardown gate

A **future** isolated Checkpoint 3 Terraform root would manage only `aws_cloudwatch_log_group` `/geolife/dev/s2b-telemetry` with 7-day retention and, **only after dashboard price confirmation**, one `aws_cloudwatch_dashboard` containing the widgets above. Do not edit or plan the existing EC2 root or S2b SQS root; do not add an IAM role, alarm, public endpoint, SG change or notification. No Terraform plan was executed for this local prototype. Save any future plan outside Git, inspect its JSON for exactly these approved creates and **zero** updates/replacements/deletes, compare live account/region/state/IAM before separately requesting apply authority. An unknown dashboard SKU or unapproved estimated spend is NO-GO; prefer a console mockup with no resource created until quoted.

Before a trial, operator confirms account, `ap-southeast-1`, stopped EC2, zero inbound SG, SSM-only access, immutable reviewed image digest, scoped instance role, clean local tests/CI, proposed log group retention, dashboard quote, account-shared free tier and a separately approved experiment budget (including SQS, EC2/EBS/public IPv4, metrics, log ingestion/storage, dashboard and query/API use). Limit the hypothetical workload to **100 new synthetic jobs/day**, at most three worker attempts/job, and projected **0.1 GB/month** new API+worker logs until measured; these are review assumptions, **not** trial authorization. Fail closed on other plan actions, unbounded streams/dimensions, raw GPS, credentials, an extraction error, missing/stale metrics presented as zero or budget drift.

For a separately approved trial only: record sanitized expected vs extracted counts, S2b streams, `IncomingBytes`, metric freshness and charges; shut down only new trial containers and close the tunnel at the **agreed end of related checks** (do not repeatedly stop/start EC2); verify EC2 stopped then. Request separate teardown approval for **only** Checkpoint 3 dashboard/log group and IAM addition after evidence is saved and retention reviewed; preserve S2b Terraform state, original API group, queues/DLQ and alarm. Confirm remaining resources and bill with the operator. No action in this paragraph has been executed.

**Acceptance gates:** local EMF/metric contract and privacy tests PASS; separately approved plan/cost/IAM PASS; SSM synthetic transport/dashboards observed end-to-end; no unwanted dimensions/log secrets; freshness and missing-data behavior verified; operator records teardown and bill. Until all hold, **Checkpoint 3 CloudWatch is NOT DEPLOYED / NOT ACCEPTED**. Fictional offline drift alerts remain local simulation, not live anomaly detection.
