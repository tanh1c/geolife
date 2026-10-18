# S2b handoff: infrastructure DONE → EC2 runtime IAM / ECR image / SSM-only acceptance

**2026-10-17, operator-reported:** S2b isolated Terraform apply completed: **10 managed resources, no taint**. Read-only AWS verification: all four S3 Block Public Access flags, SSE-S3 AES256, 1-day `synthetic/` expiration, deny-insecure-transport bucket policy. EC2 **STOPPED**, SG zero ingress. **This is infrastructure-only acceptance**, not successful async serving. Workload must stay synthetic-only. Assistant has not accessed AWS.

## Phase 1 — Only runtime IAM (do not redeploy Terraform)

From the **same protected private S2b root**, retrieve its already-generated, tightly scoped EC2 **runtime** policy:

```powershell
$tfDir = Join-Path $HOME "geolife-private/s2b-plan-3y9c3j"
$env:AWS_PROFILE = "geolife-terraform"
$env:AWS_REGION = "ap-southeast-1"
$policyPath = Join-Path $tfDir "GeoLifeS2bRuntime.json"
$rawPolicy = terraform "-chdir=$tfDir" output -raw manual_ec2_iam_policy_json
if ($LASTEXITCODE -ne 0 -or -not $rawPolicy) { throw "Cannot retrieve S2b IAM policy" }
[System.IO.File]::WriteAllText($policyPath, $rawPolicy, [Text.UTF8Encoding]::new($false))
$runtimePolicy = Get-Content $policyPath -Raw | ConvertFrom-Json
if ($runtimePolicy.Statement.Count -ne 6) { throw "Review exact IAM document manually" }
```

Use a **billing/IAM-authorized administrator** to review this exact JSON privately, create a customer managed policy **`GeoLifeS2bRuntime`** and attach it to existing **`geolife-mle-dev-ec2-role`**, NOT to the Terraform operator `geolife-ops`. AWS console: IAM → Policies → Create policy → JSON → then IAM → Roles → `geolife-mle-dev-ec2-role` → Add permissions → Attach policies. It allows only `synthetic/*` S3 object Put/Get/Delete; DynamoDB jobs Get/Put/Update; and SQS jobs queue Send/Receive/Delete/GetQueueAttributes. No infrastructure creation/deletion, broad AWS role permission, new SG or public endpoint. **Review document instead of assuming the Statement count is an authorization test.**

IAM attachment and billing-verified EC2 start are operator actions, not actions executed by this PR. Keep deployer `GeoLifeS2bDeployerTemporary` and runtime `GeoLifeS2bRuntime` distinct. After successful provisioning, consider detaching the temporary deployer policy from `geolife-ops` (retain a reviewed separate teardown plan before any future cleanup).

## Phase 2 — Build from PR #78 without touching local PR #76

Use a **separate worktree**. Do not overwrite the user's current frontend workspace.

```powershell
git fetch origin
$buildDir = Join-Path $HOME "geolife-s2b-build"
if (-not (Test-Path $buildDir)) {
  git worktree add --detach $buildDir origin/feature/track-b1-s2b-aws-sqs-serving
}
git -C $buildDir rev-parse --short=12 HEAD
```

The serving image on PR #78 **now installs `.[aws]` (boto3)** and packages worker as `python -m geolife.serving.worker_cli`. The [existing ECR build/push script](../../scripts/aws_build_push_ecr.sh) runs in Git Bash/Linux and needs `AWS_REGION`, `ECR_REPOSITORY_URL` from **existing original EC2 Terraform/ECR output**, and `EXPECTED_AWS_ACCOUNT_ID` checked by STS. Use the **existing ECR repository**, not a new registry or bucket; only the S2b repo worktree should be used as build context. Confirm the Docker image architecture matches the EC2 host; on Windows x86-64 it is commonly `linux/amd64`, but verify rather than assume. Push an immutable `rev-<SHA>` tag, capture the returned `<ECR_REPOSITORY_URL>@sha256:<DIGEST>`, and deploy by **digest**, not `latest`. If the operator has insufficient ECR push privileges or there is an unexpected account/repo mismatch, STOP instead of changing role permissions broadly.

## Phase 3 — Private EC2 runtime (only after operator checks USD 10 budget and remaining headroom)

1. Verify actual total trial spending and the cost of a short EC2 runtime interval; AWS Budgets is not a hard cap. Start ONLY the approved existing EC2 from its stopped state (separate human action). SG inbound must remain zero. Verify SSM Online; Session Manager plugin installed on local machine. Do not expose Docker port 8000 publicly.
2. **Important container IMDSv2 precheck:** read-only `aws ec2 describe-instances --instance-ids <EXISTING_INSTANCE_ID> --query 'Reservations[].Instances[].MetadataOptions.{Tokens:HttpTokens,Hop:HttpPutResponseHopLimit}'`. Docker bridge networks with IMDSv2 response hop limit 1 may block boto3's EC2 instance-profile credential retrieval. AWS documents that container hosting may need hop limit 2. Either use an explicitly reviewed secure network design or adjust IMDS response hop limit with separate operator approval; **never insert static AWS credentials into containers** just to bypass this. When the approved host uses Linux Docker host networking, force Uvicorn to bind only `127.0.0.1` inside host networking and keep SG zero ingress; do not leave the Dockerfile's default `--host 0.0.0.0` with host networking.
3. Confirm existing private demo-auth SQLite file and parent directory are writable by container uid `10001`, without committing or exporting the database. Mount only the restricted demo auth directory into the API container. Ensure **`GEOLIFE_DEMO_AUTH_DB`** is an absolute path *inside* the container. Existing demo account login only, **no proof of GeoLife participant ownership**.
4. Store stable `GEOLIFE_S2B_HMAC_SECRET` (at least 32 bytes) and `GEOLIFE_S2B_ENABLE=1`, `GEOLIFE_S2B_TABLE`, `GEOLIFE_S2B_BUCKET`, `GEOLIFE_S2B_QUEUE_URL`, `AWS_REGION=ap-southeast-1` in an OS-protected private environment file, e.g. `/opt/geolife-s2b/runtime.env` with mode 0600. API and worker must use **identical** settings. Never put secret in Git/Terraform state, paste in chat, or print it in logs. No AWS access keys: rely on restricted EC2 instance role.
5. Pull the PR #78 image by **immutable ECR digest** using existing EC2 ECR pull permission. Keep worker and API isolated to private host. On standard Docker bridge with validated IMDS credential access: API host mapping must be `-p 127.0.0.1:8000:8000` (not `-p 8000:8000`); a worker can be run as a separate bounded container using:
   ```bash
   sudo docker run --rm --no-healthcheck --env-file /opt/geolife-s2b/runtime.env \
     '<ECR_URI>@sha256:<APPROVED_DIGEST>' \
     python -m geolife.serving.worker_cli --max-polls 100
   ```
   Run the worker **concurrently** with the API; it is a bounded process (does not automatically start as a system service). If IMDSv2 hop limit prevents credentials in bridged Docker, **stop** and resolve network/IMDS configuration by separate review; don't silently change instance metadata options. Worker needs outbound S3/DDB/SQS endpoints, not inbound listener ports.
6. From local machine, open SSM port forwarding to EC2's localhost:8000:
   ```powershell
   aws ssm start-session --profile geolife-terraform --region ap-southeast-1 `
     --target <EXISTING_INSTANCE_ID> `
     --document-name AWS-StartPortForwardingSession `
     --parameters '{"portNumber":["8000"],"localPortNumber":["8000"]}'
   ```
   This stays open while running the authenticated test in a different local terminal.
7. Authenticate using the existing private synthetic test account. With its 30-minute bearer session, verify `POST /v2/jobs` returns 202, foreign account polling returns 404, same-owner `GET /v2/jobs/{job_id}` reaches `succeeded`, and successful result contains no raw GPS, Evidence Score or GeoLife participant ID. Queue body must only contain `job_id`. Do **not** use historical GeoLife GPS or real production-user accounts. Check retried idempotency and DLQ by a controlled **synthetic-only** test.
8. Run `scripts/benchmark_s2b_private_synthetic.py` **locally** from the PR #78 worktree after installing its Python dependencies, with `GEOLIFE_DEMO_TOKEN` in the *private terminal environment*, not on CLI or in file uploads:
   ```powershell
   python scripts/benchmark_s2b_private_synthetic.py --base-url http://127.0.0.1:8000 --samples 5
   ```
   Record only aggregate p50/p95/p99 for **sync full inference**, **async 202 ACK**, **async full completion** and failure counts. These are sequential synthetic SSM timings, not production/concurrency SLOs.
9. Stop and remove worker/API containers, end SSM session and **stop EC2** promptly to honor budget. Do not delete private auth DB or Terraform state. Check S3/SQS/DDB synthetic objects, CloudWatch counts and AWS Billing. Resource teardown requires a separate reviewed, targeted cleanup plan (S3 force_destroy is false).

## Acceptance and follow-up

- **INFRA DONE (operator-reported):** 10 AWS resources, private S3 4 protections, EC2 stopped/zero inbound.
- **RUNTIME PENDING:** EC2 role policy attachment, image push by digest, SSM-only process boot and protected demo credentials.
- **S2B REAL AWS NOT YET DONE:** confirmed authenticated 202 → SQS → worker → owner-scoped succeeded polling, bounded retries/DLQ, and measured full sync/async latencies.
- **TRACK B1 CHECKPOINT 3 REMAINS OPEN:** subsequent CloudWatch latency/error dashboards plus chronological synthetic drift replay/alert.

References: [AWS instance-profile role permissions](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-instance-profile.html), [IMDSv2 container hop limit](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/instancedata-data-retrieval.html), [SSM port-forward](https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-working-with-sessions-start.html), [ECR image push](https://docs.aws.amazon.com/AmazonECR/latest/userguide/docker-push-ecr-image.html), [IAM role policy attachment](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_update-role-permissions.html).
