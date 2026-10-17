# Track B1 S2b — USD 10 pre-apply gate (AWS Singapore, synthetic-only)

**Recorded approval:** 2026-10-16: user approves an **up-to-USD-10 total S2b experiment**, `ap-southeast-1`, existing EC2 **SSM-only** endpoint, **synthetic-only** input. Approval to **inspect plan** does **not** authorize unreviewed IAM changes, immediate AWS resource creation, or a public endpoint. **Status of this document: READY FOR OPERATOR PREFLIGHT; ZERO AWS MUTATIONS BY ASSISTANT.** PR #78 is stacked on PR #77.

**Primary sources:** [AWS Budgets can lag charges](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html), [AWS Budgets actions](https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-controls.html), [Terraform saved plan contains sensitive values](https://developer.hashicorp.com/terraform/cli/commands/plan), [IAM policy simulation caveats](https://docs.aws.amazon.com/cli/latest/reference/iam/simulate-principal-policy.html).

## 0. Safety boundary: what is approved and what is NOT

Allowed **now**: `aws sso login` on your own machine, **read-only** AWS identity/EC2/SG/SSM/IAM/Budgets/Cost Explorer requests, isolated local `terraform init/validate/plan`, local JSON plan guard, IAM documentation review, plan handoff with **redacted summary only**.

**Not allowed yet / not performed:** `terraform apply` / `destroy`, `aws ec2 start-instances` or security group modifications, IAM role/policy changes, `budgets create-budget`, public HTTP access, S3/SQS/DynamoDB creation, using historical GeoLife user GPS, writing secrets to repo or sending raw `tfplan`, `tfstate`, private keys or bearer tokens to ChatGPT. No AWS connection is available to the assistant to run infrastructure commands.

**Budget is a human operational ceiling, not automatically enforced:** AWS Budgets updates a few times daily and can notify after costs have accrued. Create **manual alerts** at USD 5 (50%) and USD 8 (80%), optionally a forecast alert. **Stop experiment and deprovision manually at / before USD 8 observed spend** to leave a USD 2 cushion. Treat the 10 USD limit as *incremental project trial spend*; existing EC2/EBS/public IPv4/storage charges must be included in cost review. No guaranteed hard cap. If existing account costs consume the budget, **NO-GO**. Keep one short ~30-minute EC2 run window, no always-on worker. Compare account-wide budget against projected costs; an account-wide budget cannot isolate additional cost from this experiment by itself.

## 1. Preflight checklist (all must be GO before apply)

| Gate | Concrete check | Stop condition |
| --- | --- | --- |
| AWS identity | `aws sts get-caller-identity` reports **expected 12-digit account**, matching operator's known GeoLife deployment account | Wrong/unknown account, wrong SSO role/profile |
| Region | **ap-southeast-1**, all future Terraform provider variables explicit | Any other region |
| Existing EC2 | Known EC2 ID, instance type/SSM role, **state running/stopped known** | Unidentified EC2, instance already incurring unexpected charge |
| Network | All **attached** Security Groups have **zero ingress**. Backend remains localhost through encrypted SSM tunnel | Any ingress rule, API gateway/public ALB/port 8000 opened |
| SSM | If running, SSM PingStatus=Online; if stopped, **document "not tested"**, do not start during plan | Running but SSM not Online |
| IAM | Read existing instance profile/role and inspect attached/inline policies **read-only**; no new permissions yet | Unexpected broad privileges; `iam:*`, `s3:*`, `Resource:*` planned for S2b |
| Cost | Operator has visible **USD 10** experiment budget accounting for all charges, email alerts at **5/8 USD**, current AWS Cost Explorer/Billing checked, cost cushion available | No alerts/cost data, pre-existing spend too high or price unknown |
| Terraform state | Fresh root copied **outside Git** to protected `$HOME/geolife-private/s2b-...`; not original Terraform EC2 root | Existing state/resources in the chosen directory, collision with previous test |
| Terraform plan | Exactly **10 creates / 0 update / 0 delete**; only approved S2b resource types. `s2b_plan_guard.py` returns GO_FOR_MANUAL_REVIEW_ONLY_NOT_APPLY | Unknown resource, unexpected action, account/region mismatch |
| Data/security | S3 private+SSE-S3, DynamoDB TTL, SQS SSE+DLQ; only enum synthetic fixtures; no actual GPS | Raw GeoLife data sent to AWS or authentication bypass |
| Operator review | Human has reviewed the **whole** plan and narrow IAM grants locally, before a separate explicit `apply` step | Plan contents or role privileges not understood |

**Important:** AWS plan approval and account budget approval are not the same as *actual* resource permission to apply. A successful plan guard **never grants apply authority**.

## 2. Local Windows PowerShell: read-only account / network / budget check

Use **Windows PowerShell or PowerShell 7**, AWS CLI v2 and Terraform CLI installed locally. The following steps do **not** create AWS resources. Run in the GeoLife repository root. No real account ID/instance ID is embedded in source or committed.

```powershell
git fetch origin
git switch feature/track-b1-s2b-aws-sqs-serving
git pull --ff-only

aws --version
terraform -version
python --version

# Set LOCAL variables to known identities from the previous GeoLife EC2/SSM deployment.
$awsProfile = "YOUR_EXISTING_AWS_SSO_PROFILE"
$expectedAccount = "YOUR_12_DIGIT_AWS_ACCOUNT_ID"
$instanceId = "i-YOUR_EXISTING_EC2_ID"
$region = "ap-southeast-1"

aws sso login --profile $awsProfile
aws sts get-caller-identity --profile $awsProfile --region $region

# Only describes IAM/network/SSM/budgets; never starts EC2, changes IAM or applies Terraform.
.\scripts\s2b_preflight_readonly.ps1 -AwsProfile $awsProfile -ExpectedAccountId $expectedAccount -InstanceId $instanceId -Region $region
```

Do NOT paste the full caller identity, account ID, IAM role ARN or budget details in public chat. Report only: `account matched / region matched / EC2 running|stopped / SG inbound count=0 / SSM Online|not testable / role reviewed / budget alerts ready|pending`.

If the role or Budgets read permission is denied, stop and request the **specific read-only** authorization, not broad AdministratorAccess. AWS Budgets API is served via its global endpoint; the preflight script explicitly queries budget data through `us-east-1` while checking EC2/SSM in Singapore. **If no 10 USD cost budget/alerts exist, configure/verify through AWS Billing console as a separate operator action, and do not apply S2b until alerts and remaining spend are verified.** The script only reads existing budgets.

## 3. Build Terraform plan in an isolated, private directory (NO apply)

For S2b, NEVER run plan/apply against the existing `infra/terraform` root used for EC2. Copy **only** this PR's `infra/terraform/async_s2b/*.tf` files to a fresh protected directory outside Git. This is intentional: even the Terraform local state/provider metadata and saved plan remain outside the repository. Keep the isolated directory for a later separately approved apply.

```powershell
# From the checked-out PR #78 repo root; use the validated profile/account above.
$privateRoot = Join-Path $HOME "geolife-private"
New-Item -ItemType Directory -Path $privateRoot -Force | Out-Null
$tfDir = Join-Path $privateRoot ("s2b-plan-" + (Get-Date -Format "yyyyMMdd-HHmmss"))
New-Item -ItemType Directory -Path $tfDir | Out-Null
Copy-Item "infra/terraform/async_s2b/*.tf" -Destination $tfDir

# Explicitly select the SAME AWS SSO profile / region that passed preflight.
$env:AWS_PROFILE = $awsProfile
$env:AWS_REGION = "ap-southeast-1"
$env:AWS_DEFAULT_REGION = "ap-southeast-1"

$planFile = Join-Path $tfDir "s2b.tfplan"
$planJson = Join-Path $tfDir "s2b-plan-private.json"

terraform "-chdir=$tfDir" init -backend=false -input=false
if ($LASTEXITCODE -ne 0) { throw "NO-GO: terraform init failed" }

terraform "-chdir=$tfDir" validate
if ($LASTEXITCODE -ne 0) { throw "NO-GO: terraform validate failed" }

terraform "-chdir=$tfDir" plan -input=false "-out=$planFile"
if ($LASTEXITCODE -ne 0) { throw "NO-GO: terraform plan failed" }

# Plan binary/JSON are SENSITIVE and must stay OUTSIDE Git and chat uploads.
terraform "-chdir=$tfDir" show -json $planFile | Out-File -FilePath $planJson -Encoding utf8
if ($LASTEXITCODE -ne 0) { throw "NO-GO: cannot decode plan" }

python scripts/s2b_plan_guard.py $planJson --expected-account $expectedAccount
if ($LASTEXITCODE -ne 0) { throw "NO-GO: unexpected resources/region/actions" }

# Human still needs to inspect the plan privately:
terraform "-chdir=$tfDir" show $planFile
```

Expected **guard** output: `decision=GO_FOR_MANUAL_REVIEW_ONLY_NOT_APPLY`, `expected_resources_to_create=10`, `changes={create:10,update:0,delete:0}`, `terraform_apply_authorized=false`. If the plan prints any replacement or existing resource modification, stop immediately. The guard deliberately fails closed on different prefix, account, region, missing S3 public-access controls, unsafe SQS encryption, paid DynamoDB PITR or CloudWatch alarm actions. **The guard is not a substitute for human review.**

**Do not run** `terraform apply`, `terraform destroy`, `aws iam put-role-policy`, `aws iam attach-role-policy`, `aws ec2 start-instances` or `aws budgets create-budget` as part of this pre-apply packet.

## 4. EXACT Terraform resource allowlist (10 new creates, nothing else)

1. `aws_s3_bucket.payloads` — private synthetic payload bucket, `force_destroy=false`
2. `aws_s3_bucket_public_access_block.payloads` — all four public-access blocks true
3. `aws_s3_bucket_server_side_encryption_configuration.payloads` — SSE-S3 AES256
4. `aws_s3_bucket_lifecycle_configuration.payloads` — synthetic prefix expires after one day (eventual)
5. `aws_s3_bucket_policy.payloads` — reject insecure transport
6. `aws_dynamodb_table.jobs` — on-demand, TTL `expires_at`, no PITR
7. `aws_sqs_queue.dead_letter` — SSE-SQS DLQ
8. `aws_sqs_queue.jobs` — SSE-SQS Standard, visibility 120 s, max receives 3
9. `aws_sqs_queue_redrive_allow_policy.dlq` — only this test queue allowed
10. `aws_cloudwatch_metric_alarm.dlq_not_empty` — alarm **without SNS recipient** (status inspected manually)

If any planned action is IAM creation, policy attachment, Security Group change, EC2 creation/restart, API Gateway/ALB, new NAT/public network, KMS customer-managed key or more resources: **NO-GO**.

## 5. IAM rights review — intentionally NOT granted by Terraform

Current code needs only these **synthetic test** operations after approved provisioning. Terraform [S2b root IAM policy output](../../infra/terraform/async_s2b/outputs.tf) creates JSON for human review, **not** an IAM policy attachment:

| Caller | Actions | Resource scope |
| --- | --- | --- |
| API service | `s3:PutObject` | new bucket `/synthetic/*` |
| API service | `dynamodb:GetItem`, `dynamodb:PutItem` | new test DynamoDB jobs table |
| API service | `sqs:SendMessage` | new test SQS queue |
| Worker | `s3:GetObject`, `s3:DeleteObject` | same `/synthetic/*` objects |
| Worker | `dynamodb:GetItem`, `dynamodb:UpdateItem` | same DynamoDB table |
| Worker | `sqs:ReceiveMessage`, `sqs:DeleteMessage`, `sqs:GetQueueAttributes` | same SQS queue |

The combined role is acceptable **only if both API and worker are actually running on the same approved SSM-only EC2 host**. Do not grant `iam:*`, `s3:*`, `dynamodb:*`, `sqs:*`, `Resource:*`, wildcard account, or unrelated buckets/tables/queues. IAM does not become authorized just because Terraform outputs policy JSON. Review existing attached and inline policies; only a person with approved IAM access can provision the minimal scoped grant **after** plan approval.

Optional read-only inspection of existing policies from the role identified in preflight:

```powershell
# The preflight script already performs these read-only queries and prints counts.
# If you need deeper review, use AWS IAM console on the SAME confirmed account.
# Do NOT change IAM from this runbook.
```

IAM policy simulator can help check a proposed policy, but AWS explicitly warns the simulator may differ from live enforcement; also, the exact new S3/SQS/DDB resource ARNs are not fully known until planned resource names and account match. There is **no automatic IAM attach** or extra permissions requested in this PR.

## 6. Review checklist — report ONLY redacted, non-sensitive results

Share this **text-only** summary with your reviewer/assistant, NOT `terraform show -json` or the saved plan:

```text
S2B_PREFLIGHT_REPORT
Region: ap-southeast-1
Expected AWS account: matched / NOT matched (do not paste account number)
EC2 state: stopped / running / other
EC2 SG inbound: 0 / nonzero
SSM online: yes / not testable while stopped / no
Existing EC2 IAM role: reviewed / pending (no ARN)
10 USD cost budget alerts at 5 and 8: configured / pending
Existing account cost and 2 USD buffer: checked / pending
Terraform private isolated directory: yes / no
Terraform plan guard: GO_FOR_MANUAL_REVIEW_ONLY_NOT_APPLY / REJECTED
Plan: 10 to add, 0 to change, 0 to destroy / OTHER
New public ingress or IAM changes in Terraform: none / detected
AWS infrastructure mutations executed: NONE
Explicit APPLY approval: NOT requested yet
```

**Gate for a subsequent step** (not part of this document): after this report and a sanitized cost estimate are reviewed, obtain another explicit **plan-specific** go/no-go before anyone runs `terraform apply`. The user has approved budget and scope but explicitly prohibited creating resources before checking the plan.

## 6A. Actual operator findings + corrected guard (2026-10-17)

Operator reported, using existing `geolife-terraform` identity: **EC2 stopped, all attached SG inbound rules zero, EC2 policies reviewed** (managed SSM and inline ECR-pull/CloudWatch-log writers only), and S2b Terraform plan **10 create / 0 update / 0 destroy**, with private plan saved outside repository. S3 public-block/SSE, DynamoDB on-demand/TTL and no CloudWatch alarm notification targets checked manually. **No apply, IAM grant, EC2 start, or new resource creation was performed.**

Two blockers remain:

1. **Plan guard false NO-GO in old revision:** The real `terraform show -json` contained `data.aws_caller_identity.current.account_id` in `prior_state.values.root_module.resources` instead of `planned_values.root_module.resources`. This is a documented Terraform JSON representation. Fixed `scripts/s2b_plan_guard.py` to read BOTH representations from the **original unchanged plan JSON**, require every observed identity to match the expected operator account and reject any existing *managed* resources in prior state. Added tests reproducing prior-state-only identity, mismatched accounts, unexpectedly existing managed state and absent identity. **Do not treat the operator's temporary in-memory account injection as evidence of a passing official plan guard.**
2. **Cost visibility not verified:** The current operating identity lacks Cost Explorer read permission, so the pre-existing AWS charges and USD 2 reserve have **not** been independently verified. User's 10 USD approval does not resolve this. AWS Budgets alerts are delayed and do not cap spending.

### Re-run corrected guard against the SAME saved private plan

**Do not regenerate/rewrite the JSON to inject account ID, and do not run plan/apply anew merely to work around the old script.** First update the local code and verify the existing plan's source Terraform snapshot is unchanged. From repository root, with the same variables created during previous preflight:

```powershell
git fetch origin
git switch feature/track-b1-s2b-aws-sqs-serving
git pull --ff-only
python -m pytest -q tests/test_s2b_plan_guard.py

# Reuse previously saved original plan JSON OUTSIDE Git:
$existingPlanJson = "YOUR_PRIVATE_S2B_PLAN_DIRECTORY\\s2b-plan-private.json"
python scripts/s2b_plan_guard.py $existingPlanJson --expected-account $expectedAccount
if ($LASTEXITCODE -ne 0) { throw "NO-GO: original unchanged S2b plan rejected" }
```

Expected `GO_FOR_MANUAL_REVIEW_ONLY_NOT_APPLY`. This is **NOT** a final GO for Terraform apply; plan may be stale and account cost/IAM must still be reviewed.

### Close the cost gate without broad IAM permissions (preferred)

Use **AWS Billing and Cost Management Console** under an identity already authorized to view AWS charges. Open [Cost Explorer](https://console.aws.amazon.com/costmanagement/home#/cost-explorer) or Billing/Bills, select the **same account**, inspect **month-to-date actual estimated costs**, charges by EC2/EBS/public IPv4/CloudWatch/ECR, credits/free-tier conditions, projected extra half-hour compute and S2b services, and the AWS Budgets alarm emails at **USD 5 and 8**. Save a **sanitized** report `cost_checked=yes, estimated remaining headroom >=2 USD beyond planned experiment`; no billing screenshots or full account data are required in chat.

Cost Explorer UI has no request fee, whereas Cost Explorer **API pagination costs USD 0.01/request**; enabling Cost Explorer for a new account can take about 24 hours to populate current-month data. AWS may report billing with at least one-day delay and billing can differ from Cost Explorer. Check [official pricing](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html), [data-refresh timing](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-enable.html), and [access policies](https://docs.aws.amazon.com/cost-management/latest/userguide/ce-access.html).

If the operator **specifically needs automated read-only cost access**, ask a billing administrator to consider granting `ce:GetCostAndUsage` to **`geolife-ops`**, appropriately restricted by any available billing-view and organizational permissions. Do **not** grant it to EC2 runtime role, and do not grant `ce:*` or billing-admin permissions just to complete preflight. A Cost Explorer service/console entitlement or organization member-account restriction may still block it; the billing administrator can instead verify costs in Console. No IAM policy is modified by this PR.

If accurate billed cost and reserve are unavailable, **NO-GO for apply** despite 10/0/0 plan. Once the corrected guard PASS and independent cost gate PASS, return the *redacted* summary for plan-specific human review. **Never send raw Terraform plan/state, AWS IDs, IAM policy JSON or tokens.**

## 7. Retention/teardown and pricing caveats

DynamoDB TTL deletion is asynchronous and S3 lifecycle expiry is eventual. S3 `force_destroy=false` deliberately prevents silent destruction of a nonempty bucket. Therefore manually clean synthetic objects and confirm DLQ/table contents before a later, separately approved Terraform destroy. Existing EC2/EBS, public IPv4, ECR and CloudWatch costs remain outside the new S2b Terraform root and must be checked separately. Stop any manually started EC2 after the short experiment. AWS Budgets notifications are **not a hard spending cap**.

The existing [S2b implementation handoff](13_s2b_aws_sqs_synthetic_handoff.md) remains the reference for *post-apply* SSM worker and latency benchmark instructions. This pre-apply document never grants permission to carry out those steps.
