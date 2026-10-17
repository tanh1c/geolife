# S2b — Resolve 5 security-sensitive refresh drift entries without bypassing the guard

**Date:** 2026-10-17. **Decision:** Prefer Terraform **refresh-only state reconciliation** over loosening security-drift gates. This is an operator-run workflow; this PR does **not** access AWS, change IAM/EC2/S3/SQS/DynamoDB, modify local Terraform state, or run Terraform apply.

## Current verified vs unverified

Operator reports after backing up state and untainting the single S3 bucket: **6 untainted managed S2b resources**, EC2 STOPPED, zero SG inbound. Existing saved normal plan at private path `s2b-after-untaint.tfplan` reports **4 creates / 6 no-ops / 0 update / 0 destroy**, but strict guard rejects five `resource_drift` observations:

- CloudWatch metric alarm: `alarm_actions`, `ok_actions`, `insufficient_data_actions`, `tags`.
- DynamoDB table: `tags`.
- S3 bucket: metadata and encryption-related fields.
- SQS jobs / DLQ: `redrive-allow` and `tags`.

The operator directly checked AWS: S3 SSE-S3 AES256, metric alarm no notification actions, queues SSE and redrive configured to the correct queue. Existing public-access blocks / object emptiness were checked in earlier handoff. **This is local operator evidence only**. Not all drift details or resource IDs were shared; do not assume any difference is harmless. `resource_drift` describes refreshed state differences while `resource_changes` describes planned remote operations. Security-sensitive drift remains **NO-GO** for the fingerprint-based override.

## One-pass state-only recovery (Windows PowerShell, S2b private state only)

**Preconditions:** IAM identity correct account `939169265033`; only Singapore `ap-southeast-1`; S2b private root with original `.tf`, `.terraform.lock.hcl`, state; exact six previously created resource identities known and present; enough **actual** remaining experiment budget within USD 10 inclusive of costs already accrued. Do not run any resource-changing apply yet. Keep EC2 stopped and SG zero inbound.

1. Back up current local state **again**, after the earlier `untaint`, in a private folder. Do not hand-edit JSON, change providers, or use a new Terraform state. Check currently tracked managed addresses and account/region.
2. Run `terraform plan -refresh-only -input=false -out=<PRIVATE_PATH>/s2b-state-refresh.tfplan`. The plan proposes a **state-only** synchronization with AWS, not remote S2b resource creation or destruction. Review `terraform show <saved-refresh-plan>` **privately**. Review each observed changed field and the resources listed. **STOP** if any managed resource would disappear from state, be renamed/replaced, change account/region/ID, or if observed S3/queue/DDB/alarm security configuration is incorrect.
3. Ensure independently read-only AWS evidence matches refreshed state for the security-sensitive values: S3 SSE AES256 and block all public access, expected synthetic tags, SQS SSE and DLQ redrive, DynamoDB on-demand/TTL, no CloudWatch notification actions. Normal AWS/provider-computed tags and empty/null API representations may be recorded as state differences, but do **not** auto-treat them as safe.
4. **Only if the refresh-only plan is safe and approved for a state-only mutation**, apply **that specific saved refresh-only plan**, `terraform -chdir=<private-root> apply <private-refresh-plan>`. This updates **Terraform state and outputs only**, **does not change AWS resources**. It is not the same as the normal `apply` that creates S3 configuration resources. Saved plan apply will not prompt, so review step 2 first.
5. Immediately re-check `terraform state list` (must still be six exact S2b managed addresses) and identity; any unexpected count/identity => STOP.
6. Create a **new normal plan** (not the now-stale `s2b-after-untaint.tfplan`) from this refreshed private state. Run current unchanged strict `scripts/s2b_plan_guard.py --allow-partial-state` on its untouched JSON **without `--reviewed-drift-digest`**. Expected under unchanged AWS/config: **4 create / 6 no-op / 0 update / 0 destroy**, and **no meaningful `resource_drift`**. Review exact four creates: S3 public-access-block, bucket encryption configuration, 1-day lifecycle and deny-insecure-transport bucket policy. **NO AWS apply yet.**
7. If normal plan still reports any security-sensitive drift, a resource replacement/delete/update, a security mismatch or unknown resource, **STOP** and investigate. Do **not** turn off refresh with `-refresh=false`, edit state, use `-target`, weaken guard or replay prior saved plans. Check billed costs/5-and-8 USD alerts before any later resource-creating apply.

## Copy-paste commands — DO NOT run normal Terraform apply

From repository root, with the **same** private S2b Terraform directory:

```powershell
git fetch origin
git switch feature/track-b1-s2b-aws-sqs-serving
git pull --ff-only

$tfDir = Join-Path $HOME "geolife-private/s2b-plan-3y9c3j"
$env:AWS_PROFILE = "geolife-terraform"
$env:AWS_REGION = "ap-southeast-1"
$env:AWS_DEFAULT_REGION = "ap-southeast-1"

$account = (aws sts get-caller-identity --profile geolife-terraform --region ap-southeast-1 --query Account --output text).Trim()
if ($account -ne "939169265033") { throw "NO-GO: unexpected AWS account" }

# Backup after untaint, BEFORE ANY state-only operation. Keep outside Git.
$statePath = Join-Path $tfDir "terraform.tfstate"
if (-not (Test-Path $statePath)) { throw "NO-GO: missing local Terraform state" }
$backupPath = Join-Path $tfDir ("state-pre-refresh-only-" + (Get-Date -Format "yyyyMMdd-HHmmss") + ".backup")
Copy-Item $statePath $backupPath
terraform "-chdir=$tfDir" state list

$refreshPlan = Join-Path $tfDir "s2b-state-refresh.tfplan"
terraform "-chdir=$tfDir" plan -refresh-only -input=false "-out=$refreshPlan"
if ($LASTEXITCODE -ne 0) { throw "NO-GO: refresh-only plan failed" }

# HUMAN SAFETY GATE: review the state-only refresh; do not accept removals,
# unexpected identity changes, insecure state or changes outside the six objects.
terraform "-chdir=$tfDir" show $refreshPlan
if ($LASTEXITCODE -ne 0) { throw "NO-GO: cannot inspect refresh-only plan" }

# ONLY after independently validating the refresh-only plan above.
$ack = Read-Host "State-only refresh reviewed: same 6 resource identities and secure settings? Type STATE_ONLY"
if ($ack -cne "STATE_ONLY") { throw "Stopped before modifying Terraform state" }
terraform "-chdir=$tfDir" apply $refreshPlan
if ($LASTEXITCODE -ne 0) { throw "NO-GO: state-only refresh apply failed" }

# Verify exactly the six known managed S2b addresses remain.
$stateAddresses = @(terraform "-chdir=$tfDir" state list)
if ($LASTEXITCODE -ne 0) { throw "NO-GO: state list failed" }
$managed = @($stateAddresses | Where-Object { $_ -match "^aws_" })
$expected = @(
  "aws_s3_bucket.payloads",
  "aws_dynamodb_table.jobs",
  "aws_sqs_queue.jobs",
  "aws_sqs_queue.dead_letter",
  "aws_sqs_queue_redrive_allow_policy.dlq",
  "aws_cloudwatch_metric_alarm.dlq_not_empty"
)
if (($managed.Count -ne 6) -or (@(Compare-Object ($managed | Sort-Object) ($expected | Sort-Object)).Count -gt 0)) {
  throw "NO-GO: unexpected managed resource count/address after refresh"
}

$normalPlan = Join-Path $tfDir "s2b-after-state-refresh.tfplan"
$normalJson = Join-Path $tfDir "s2b-after-state-refresh-private.json"
terraform "-chdir=$tfDir" plan -input=false "-out=$normalPlan"
if ($LASTEXITCODE -ne 0) { throw "NO-GO: normal plan failed" }
terraform "-chdir=$tfDir" show -json $normalPlan | Out-File $normalJson -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "NO-GO: cannot export normal plan" }
python scripts/s2b_plan_guard.py $normalJson --expected-account $account --allow-partial-state
if ($LASTEXITCODE -ne 0) { throw "NO-GO: strict guard rejected after state-only refresh" }
terraform "-chdir=$tfDir" show $normalPlan
```

**Precautions:** The PowerShell state list check confirms *addresses*, not remote IDs; the separate human review must confirm those IDs remain unchanged. Do not upload saved plans, state or JSON to GitHub or ChatGPT. If the budget cap or AWS resource identity is uncertain, stop before `STATE_ONLY`. After normal guard PASS, report redacted state/plan/cost summary for a later, separate decision about creating the four remaining S3 configuration resources.

## Official rationale and references

- [HashiCorp refresh-only procedure](https://developer.hashicorp.com/terraform/tutorials/state/refresh)
- [Terraform refresh command deprecated due to blind state mutation](https://developer.hashicorp.com/terraform/cli/commands/refresh)
- [Terraform plan modes](https://developer.hashicorp.com/terraform/cli/commands/plan)
- [Terraform apply saved plan skips confirmation](https://developer.hashicorp.com/terraform/cli/commands/apply)

**Stop status:** The AWS S2b infrastructure is still partially provisioned. The state-only sync and final normal resource-creating apply remain actions for the operator, not code run by the assistant.
