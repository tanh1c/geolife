# GeoLife S2b — Failed Terraform apply recovery, 2026-10-17

**Status:** HARD HOLD / NO-GO for repeat apply. User-provided local operator report: AWS `AccessDenied` during three first resource creation calls: `s3:CreateBucket`, `dynamodb:CreateTable`, `sqs:CreateQueue`. Terraform operator principal is IAM user `geolife-ops`, reached through profile `geolife-terraform`; it is NOT the EC2 execution role `geolife-mle-dev-ec2-role`. Operator says private state lists only `data.aws_caller_identity.current`, no created managed Terraform resources, and EC2 remains stopped. **The assistant has not independently inspected AWS**, so absence of state entries is not sufficient proof that no AWS resources exist. Preserve old private state/plan/logs for investigation. No AWS modifications, Terraform apply, IAM grants or EC2 start were made by this PR.

## 1. Impact and identity boundaries

The failure is in the **deployer's AWS IAM capabilities**. It does **not** mean the CP1/CP2 model is wrong, the S2b code should be rewritten, or the EC2 runtime role needs `CreateBucket`, `CreateTable` or `CreateQueue`.

- **Deployer principal `geolife-ops`:** may be granted strictly temporary/resource-scoped permissions to provision the *known S2b stack*, after administrative review.
- **EC2 runtime role `geolife-mle-dev-ec2-role`:** will eventually need only runtime read/write actions on the S2b S3/DynamoDB/SQS resources **after** infrastructure provisioning and separate approval. Must not receive create/delete infrastructure, broad AdministratorAccess or wildcard resource access.
- **Human billing administrator:** should independently verify USD 10 trial budget and USD 2 buffer before another apply. Previous operator preflight reported missing Cost Explorer visibility. No later evidence has closed that gate.

## 2. Reconcile cloud objects READ-ONLY before any new plan

Existing Terraform state with only data sources means Terraform did not *record* a created managed resource, **not** that remote AWS APIs positively confirm absence. Check specific deterministic names in ap-southeast-1. Script below uses read-only `HeadBucket`, `DescribeTable`, `GetQueueUrl` (jobs and DLQ) and `DescribeAlarms`; AWS credentials remain on the operator's local machine.

```powershell
git fetch origin
git switch feature/track-b1-s2b-aws-sqs-serving
git pull --ff-only
python -m pip install -e ".[dev]"

$awsProfile = "geolife-terraform"
$expectedAccount = (aws sts get-caller-identity --profile $awsProfile --query Account --output text).Trim()
python scripts/s2b_failed_apply_inventory_readonly.py --profile $awsProfile --expected-account $expectedAccount
if ($LASTEXITCODE -ne 0) { throw "NO-GO: at least one AWS resource exists or check lacks read permissions" }
```

Output contains **only** resource categories and `ABSENT` / `PRESENT` / `UNKNOWN`, not full names/ARNs/account IDs. Exact S2b targets:
- Bucket: `geolife-mle-s2b-dev-<ACCOUNT_ID>-ap-southeast-1`.
- Table: `geolife-mle-s2b-dev-jobs`.
- SQS queues: `geolife-mle-s2b-dev-jobs`, `geolife-mle-s2b-dev-dlq`.
- CloudWatch alarm: `geolife-mle-s2b-dev-dlq-not-empty`.

**Interpretation:** If all five are `ABSENT`, the script says `READY_FOR_NEW_PLAN_REVIEW_ONLY` (**NOT** permission to apply). If **any** resource is `PRESENT`, halt and reconcile Terraform state / existing cloud object ownership with a human before touching it. If any is `UNKNOWN`, halt and request strictly scoped *read* access or have a permitted administrator inspect it. A 403 on S3 `HeadBucket` is **UNKNOWN**, never proof of nonexistence. Do not blindly `terraform import`, `state rm`, delete resources or create replacement names.

Optional `terraform -chdir=<privateRoot> state list` confirms local state only; never assume it is authoritative for remote orphaned objects after errors.

## 3. Deployer IAM review — 3 missing permissions are not the full list

AWS documented action mappings show additional operations Terraform may invoke when configuring the approved 10 objects:

| Service | Review-only provision/config actions | Resource scope |
|---|---|---|
| S3 | `s3:CreateBucket`, `s3:PutBucketPublicAccessBlock`, `s3:PutEncryptionConfiguration`, `s3:PutLifecycleConfiguration`, `s3:PutBucketPolicy` plus corresponding Get/Tag permissions | Exact synthetic bucket only |
| DynamoDB | `dynamodb:CreateTable`, `DescribeTable`, `UpdateTimeToLive`, `DescribeTimeToLive`, `UpdateContinuousBackups`, `DescribeContinuousBackups`, `TagResource` | Exact S2b jobs table only |
| SQS | `sqs:CreateQueue`, `GetQueueAttributes`, `GetQueueUrl`, `SetQueueAttributes` (DLQ redrive allow), `TagQueue`, `ListQueueTags` | Exact S2b jobs and DLQ ARNs |
| CloudWatch | `cloudwatch:PutMetricAlarm`, `DescribeAlarms`, `TagResource` | Exact S2b DLQ alarm ARN |

**REVIEW-ONLY template:** [`15_s2b_deployer_iam_review_template.json`](15_s2b_deployer_iam_review_template.json). It deliberately contains a `_comment` field and `<ACCOUNT_ID>` placeholders so it **cannot be pasted unmodified into IAM**. Before any use, an IAM administrator must strip `_comment`, replace account placeholder **privately**, inspect the full policy, consider actual provider version/required tags, check IAM permissions boundaries/SCPs, use IAM Policy Simulator/Access Analyzer where possible, and approve only the least privileges on the deployer (`geolife-ops`). This draft is **not** an unconditional or guaranteed-complete grant. **Do not automatically attach it.**

The Terraform root's `outputs.tf` contains a *different* policy: `manual_ec2_iam_policy_json`, which only covers runtime permissions on existing resources. **Do not confuse it with deployer creation permissions**. Deploy-time delete/cleanup permissions, if later necessary, require a separately reviewed cleanup policy; don't broadly grant them by default.

Use [AWS S3 bucket permissions](https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html), [DynamoDB IAM authorization](https://docs.aws.amazon.com/service-authorization/latest/reference/list_dynamodb.html), [SQS IAM authorization](https://docs.aws.amazon.com/service-authorization/latest/reference/list_sqs.html), [CloudWatch IAM authorization](https://docs.aws.amazon.com/service-authorization/latest/reference/list_cloudwatch.html). AWS provider `default_tags` can require service tagging permissions beyond the three Create actions.

## 4. Recover preflight & do not reuse failed saved plan

1. Confirm existing IAM operator principal / AWS account / `ap-southeast-1`, SSM-only EC2 STOPPED and all SGs inbound zero. Preserve the original private failed-plan and state snapshot. Never paste credentials, plan JSON or account IDs into repo/chat.
2. Run **read-only AWS inventory**. If anything is `PRESENT` or `UNKNOWN`, **NO-GO** until reconciled; absence of Terraform state alone is not enough.
3. Close the **cost gate**: human checks actual AWS Billing/Cost Explorer (or a narrowly authorized read-only cost API) and alerts USD 5/USD 8, projected S2b costs and USD 2 cushion. **No auto-enforced hard USD 10 limit.** If still unavailable, **NO-GO**.
4. Have a permitted IAM administrator review temporary narrow *deployer* policy for `geolife-ops`, not EC2. Do not apply it before approved scope/billing review; report only `deployer_create_permissions_reviewed=yes/no`.
5. In the original private Terraform directory containing the tracked local state, recheck config/version/provider, run a **fresh** `terraform plan -out=<new private plan>` and `terraform show -json` after IAM is updated. DO NOT reuse the **saved plan used by the failed apply**; revalidate all 10 expected creates / zero changes/destroys and run corrected `scripts/s2b_plan_guard.py` on the unchanged new JSON.
6. Stop for a **new human GO/NO-GO review** of remote absence, IAM policy, billing and plan. **Do not retry `terraform apply`** just because the three old errors are resolved.

**Post-failed-apply success condition:** Only a fresh post-failure inventory `ABSENT`, completed budget verification, reviewed narrow IAM permission, and fresh clean plan/guard can authorize human decision on a new apply. This document itself never authorizes creation.

## 5. Worklog and results

On this review turn, only documentation/read-only helper/test changes are pushed to PR #78. No AWS account has been accessed or modified by the assistant. No IAM policy was attached. No S3, DDB, SQS or CloudWatch resources were provisioned, and no `terraform apply` was executed by the assistant. Live outcome is **NO-GO until operator reconciliation**.

**Official references:** [Terraform apply failures](https://developer.hashicorp.com/terraform/tutorials/cli/apply), [AWS IAM least privilege](https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html), and AWS service authorization references linked above.
