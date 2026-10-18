# S2b partial apply recovery — S3 GetBucketCORS AccessDenied

**Date:** 2026-10-17. **Operator-reported AWS state:** A second S2b `terraform apply` created S3 bucket, DynamoDB jobs table, both SQS queues, DLQ redrive allow policy and CloudWatch alarm, then failed when Terraform's read-after-create S3 bucket refresh required `s3:GetBucketCORS` on the deployment IAM user `geolife-ops`. Terraform's *private* state records completed resources. EC2 remains STOPPED, no deployment worker/API operating. **The assistant has not run AWS commands or independently inspected state**. No retry, delete, import, or IAM mutation was performed by this documentation update.

**AWS source:** [GetBucketCors requires s3:GetBucketCORS](https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketCors.html). HashiCorp [Terraform apply failures save partial state; no automatic rollback](https://developer.hashicorp.com/terraform/cli/commands/apply). Never apply the original 10-create saved plan again — a partial state demands a new refresh/plan with the same private working directory.

## 1. Stop and preserve partial state (mandatory)

Keep the original private Terraform folder and files outside Git. Do **not** delete the bucket, table, queues, DLQ, CloudWatch alarm, or run `terraform destroy`. Do **not** run `terraform state rm`, `terraform import`, disable refresh, or create a fresh empty state: these can orphan resources or attempt duplicate creations.

Operator executes **read-only, local-only**:

```powershell
$tfDir = Join-Path $HOME "geolife-private/s2b-plan-3y9c3j"
$env:AWS_PROFILE = "geolife-terraform"
$env:AWS_REGION = "ap-southeast-1"
$env:AWS_DEFAULT_REGION = "ap-southeast-1"

terraform "-chdir=$tfDir" state list
aws sts get-caller-identity --profile geolife-terraform --region ap-southeast-1
```

Expected **managed state resources**, according to operator report (not independently verified): `aws_s3_bucket.payloads`, `aws_dynamodb_table.jobs`, `aws_sqs_queue.jobs`, `aws_sqs_queue.dead_letter`, `aws_sqs_queue_redrive_allow_policy.dlq`, `aws_cloudwatch_metric_alarm.dlq_not_empty`. Four S3 configuration resources may still be pending. State list is not a remote existence check; validate read-only with S3/CloudWatch/DynamoDB/SQS AWS APIs as permissions permit. If an AWS resource exists but **has no matching state entry**, **STOP**, and resolve possible import/reconciliation with a human; never run an implicit duplicate create.

## 2. Fix operator IAM exactly once; keep EC2 role unchanged

An IAM administrator updates **customer-managed** `GeoLifeS2bDeployerTemporary` attached to IAM **user** `geolife-ops`, adding the documented read-after-create S3 operations to its existing S3 bucket resource statement, restricted to **only**:

`arn:aws:s3:::geolife-mle-s2b-dev-<ACCOUNT_ID>-ap-southeast-1`

```json
{
  "Sid": "S2bBucketReadBack",
  "Effect": "Allow",
  "Action": [
    "s3:GetBucketCORS",
    "s3:GetBucketWebsite",
    "s3:GetBucketLogging",
    "s3:GetBucketRequestPayment",
    "s3:GetAccelerateConfiguration",
    "s3:GetReplicationConfiguration",
    "s3:GetBucketObjectLockConfiguration"
  ],
  "Resource": "arn:aws:s3:::geolife-mle-s2b-dev-<ACCOUNT_ID>-ap-southeast-1"
}
```

**This is one statement, not a complete policy document.** Add it to the existing managed policy, or merge its Action array into the existing bucket statement. No `s3:*`, wildcard buckets, `iam:*`, EC2 restart or S3 CORS configuration change. AWS provider v5.x may read bucket metadata after creation even if those fields are not explicitly configured. Check the actual IAM policy version, attached user, permission boundary and any explicit deny. The [review-only deployer policy template](15_s2b_deployer_iam_review_template.json) is now updated with those read operations but still contains a non-IAM `_comment` and unresolved placeholder, and **must not be submitted verbatim**. User/administrator must approve IAM modification separately.

## 3. After IAM + budget verification, create a NEW partial-state plan (read-only)

Verify the experiment's **10 USD total budget**, alerts USD 5 / 8 and at least 2 USD headroom, now counting **already-created S3/SQS/DynamoDB/CloudWatch charges**. No hidden assumption AWS Budgets enforces spending.

Do not alter the Terraform configuration `.tf` or private `.terraform.lock.hcl` to force a clean plan. Run `terraform plan` in the **same existing private Terraform root**, from the state that the failed apply updated. Save a **new** plan, never reuse either previous saved plan:

```powershell
$tfDir = Join-Path $HOME "geolife-private/s2b-plan-3y9c3j"
$env:AWS_PROFILE = "geolife-terraform"
$env:AWS_REGION = "ap-southeast-1"
$env:AWS_DEFAULT_REGION = "ap-southeast-1"

# Read only existing state and IAM. Prevent mixing accounts.
terraform "-chdir=$tfDir" state list
$expectedAccount = (aws sts get-caller-identity --profile geolife-terraform --region ap-southeast-1 --query Account --output text).Trim()

$plan = Join-Path $tfDir "s2b-partial-recovery.tfplan"
$planJson = Join-Path $tfDir "s2b-partial-recovery-private.json"
terraform "-chdir=$tfDir" plan -input=false "-out=$plan"
if ($LASTEXITCODE -ne 0) { throw "NO-GO: Terraform plan failed; check IAM and remote state" }
terraform "-chdir=$tfDir" show -json $plan | Out-File $planJson -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "NO-GO: plan JSON failed" }

python scripts/s2b_plan_guard.py $planJson --expected-account $expectedAccount --allow-partial-state
if ($LASTEXITCODE -ne 0) { throw "NO-GO: partial-state guard rejected plan" }

terraform "-chdir=$tfDir" show $plan
```

**Guard behavior:** Normal `s2b_plan_guard.py` still requires a clean 10-create plan; the **explicit recovery flag** validates one of the same ten fixed resource addresses as prior state and a mixture of `no-op` for existing tracked resources and `create` for missing resources. It rejects any `update`, `replace`, `delete`, unknown resource/address, mismatched account, unsafe configured output, or changing ownership. This is deliberately conservative: if Terraform needs a real `update`, **STOP** and review the exact diff rather than weakening the guard. The output **always** says `terraform_apply_authorized=false`; it never auto-applies.

Example **only if state matches operator description exactly**: 6 `no-op`, 4 `create`, 0 `update`, 0 `delete`. **Do not force these numbers** if reality differs. If Terraform reports all resources already configured, there may be 10 no-op; that requires separate interpretation, not another apply.

## 4. Human decision gate before any further AWS mutation

After the new saved plan is safely reviewed on the operator's local machine, report **only** this redacted summary:

```text
S2B_PARTIAL_RECOVERY
Operator IAM GetBucketCORS and bucket metadata reads: granted / AccessDenied
Partial state resources: N managed (no IDs or ARNs)
Remote inventory: every relevant resource matches state / conflict / unknown
New plan guard: PASS / REJECTED
Plan actions: C create / N no-op / 0 update / 0 destroy
USD 10 trial actual+projected cost, 5/8 alerts and buffer: verified / not verified
EC2: stopped
SG inbound: 0
New apply permission: NOT GIVEN BY THIS DOCUMENT
```

If all conditions pass and an explicit plan-specific human authorization is given, **only then** apply that *new* saved plan once, using `terraform "-chdir=$tfDir" apply $plan`. Terraform apply of saved plan does not prompt again. If it fails, STOP and reconcile updated state again. Do not import or destroy blindly.

After infrastructure converges, follow [S2b authenticated worker/ECR/SSM handoff](13_s2b_aws_sqs_synthetic_handoff.md). Existing frozen CP1/CP2 and Evidence v1 are unchanged; no real GeoLife participant data may be uploaded.
