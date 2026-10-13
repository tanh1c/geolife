# Recovery — partially completed AWS Free plan Terraform apply

**Incident:** original `t3.medium` EC2 rejected with
`InvalidParameterCombination: The specified instance type is not eligible for Free Tier`.
Terraform **did create and record** four resources: ECR repository, ECR lifecycle
policy, CloudWatch log group and zero-ingress EC2 Security Group. No GeoLife EC2
instance was created. This is an expected, recoverable Terraform partial apply;
it is **NOT** an instruction to destroy/recreate the four existing resources.

AWS EC2 Free plan (accounts created on/after 2025-07-15) includes
`c7i-flex.large` (2 vCPU, 4 GiB, x86_64) and `m7i-flex.large`
(2 vCPU, 8 GiB, x86_64). These are **eligible billing SKUs, not
unlimited zero-cost EC2**. Verify account/region/AZ and Free plan credits.
The default is now `c7i-flex.large`, which preserves original 4-GiB memory
and Python/Docker x86_64 compatibility.

Source: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-free-tier-usage.html

## 0. Stop: preserve existing state and cloud resources

Never run any of these in recovery: `terraform destroy`,
`terraform state rm`, `terraform import` on the four known resources,
`terraform apply tfplan` with the **old** plan, `rm terraform.tfstate`,
or repeat `init` from a different empty working directory.

Stay on the **same machine, local Terraform workspace/backend, same
`infra/terraform/terraform.tfstate`**, with the previously successful
`geolife-terraform` credential-process profile. A second state could
attempt to recreate the already-provisioned repository/log group/SG.

State files and backups are sensitive. Do not paste or upload them.

## 1. IAM policy change by the account IAM administrator (AWS Console)

The old **deployer IAM inline policy** contains an explicit
`DenyUnapprovedEC2Sizes` statement listing only `t3.medium`/similar.
An explicit `Deny` overrides any `Allow`, so changing Terraform alone
will fail with `UnauthorizedOperation`.

Open **AWS Console → IAM → User groups → geolife-deployers → Permissions**,
locate the exact custom inline policy used for Terraform. Edit the JSON in
the policy editor. Replace *only* the allowed values in
`Sid = "DenyUnapprovedEC2Sizes"` with:

```json
"StringNotEqualsIfExists": {
  "ec2:InstanceType": [
    "c7i-flex.large",
    "m7i-flex.large"
  ]
}
```

Alternatively paste the updated full template
`infra/iam/geolife-deployer-permission-set.template.json` after replacing
`REPLACE_ACCOUNT_ID` with your real account ID, keeping any
existing project constraints that are stricter. Do **not** attach
AdministratorAccess / AmazonEC2FullAccess, and do not remove the
project-wide explicit-deny guard.

If another permission boundary / SCP applies, confirm it also permits the
selected Free-plan type. Our Free-plan single-account setup currently does
not create AWS Organizations or an SCP.

## 2. Verify eligible instance and AZ before choosing the type

Use Windows PowerShell (read-only AWS CLI operations):

```powershell
$env:AWS_PROFILE = "geolife-terraform"
$env:AWS_REGION = "ap-southeast-1"

aws sts get-caller-identity

aws ec2 describe-instance-types `
  --region ap-southeast-1 `
  --instance-types c7i-flex.large m7i-flex.large `
  --query "InstanceTypes[].{Type:InstanceType,FreeTier:FreeTierEligible,RAMMiB:MemoryInfo.SizeInMiB,CPU:VCpuInfo.DefaultVCpus,Architectures:ProcessorInfo.SupportedArchitectures}" `
  --output json

aws ec2 describe-instance-type-offerings `
  --region ap-southeast-1 `
  --location-type availability-zone `
  --filters "Name=location,Values=ap-southeast-1a" "Name=instance-type,Values=c7i-flex.large" `
  --query "InstanceTypeOfferings[].{Type:InstanceType,Zone:Location}" `
  --output table
```

Gate: chosen `c7i-flex.large` must be `FreeTierEligible=true`, compatible
with `x86_64` and present in `ap-southeast-1a` (selected subnet AZ).
If unavailable, **stop** and check `m7i-flex.large` with a matching offering
query; do not change subnet, region or EC2 type arbitrarily.

## 3. Pull the fix; keep the local state intact

In the same local GeoLife clone where partial `apply` happened:

```powershell
git fetch origin
git switch feature/track-b1-aws-deployment
git pull --ff-only origin feature/track-b1-aws-deployment

# Same Terraform directory/workspace, no new backend:
# Data-source entries may also appear; filter to managed resources:
terraform -chdir=infra/terraform state list | Where-Object { $_ -notmatch '^data\\.' }

# Optional additional local backup, outside Git repo:
$backup = Join-Path $HOME "geolife-terraform-state-backup.json"
terraform -chdir=infra/terraform state pull | Set-Content -Path $backup -Encoding utf8
# Protect this file and delete securely only once recovery is complete.
```

Expected **managed-resource** state entries (4 addresses):

```text
aws_cloudwatch_log_group.api
aws_ecr_lifecycle_policy.api
aws_ecr_repository.api
aws_security_group.instance
```

Edit **only** `instance_type` in your EXISTING ignored
`infra/terraform/terraform.tfvars` (do not copy the example over it;
it has account-specific VPC/subnet values):

```hcl
instance_type = "c7i-flex.large"
```

Keep existing `vpc_id`, `subnet_id`, `aws_region`,
`instance_profile_name`, and project/environment values unchanged.

## 4. Fresh plan after the failure; no apply yet

```powershell
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform validate

# Generate a brand-new saved plan from the intact partial-apply state:
terraform -chdir=infra/terraform plan -out=tfplan
terraform -chdir=infra/terraform show tfplan
```

**Required exact outcome** (unless actual AWS drift is separately reviewed):

```text
Plan: 1 to add, 0 to change, 0 to destroy.
```

Only `aws_instance.api` may have an action `create`. Four already-existing
resources must be unchanged. If Terraform proposes recreate/replace/change
an existing SG/ECR/CloudWatch resource, **STOP** and send the action summaries
and redacted diff; don't run apply.

Review that `aws_instance.api` specifies `c7i-flex.large`,
the already-created Security Group ID, the pre-created IAM instance
profile, encrypted gp3 20-GiB EBS, `associate_public_ip_address = true`
(outbound only, SG inbound zero), IMDSv2 required, and matching VPC subnet.

Always verify the local AWS identity is `user/geolife-ops`, not root.
A successful plan does **not** guarantee `iam:PassRole` / EC2 launch
is allowed: that is checked during `apply`.

## 5. Apply only after deliberate operator approval

The user must review the plan and Free-plan budget/credit use, then
**explicitly choose to execute**:

```powershell
terraform -chdir=infra/terraform apply tfplan
```

It must create only EC2. No automatic rollback/recreate of the other four
resources is expected. If it fails, preserve state and full sanitized error
code; do not retry blindly.

After a successful apply, check actual EC2 and SSM state, then verify the
existing Security Group still has `IpPermissions: []` before any ECR/Docker
deployment.

Use the main handoff `docs/deployment/08_aws_ssm_deployment_handoff.md`
for EC2, SSM, Docker deployment and final resource teardown.
