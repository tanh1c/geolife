# Terraform — GeoLife AWS SSM-only demo

**Checkpoint 2 source configuration (not deployed).** This Terraform root now
provisions one **short-lived internal** EC2 host, a private ECR repository,
CloudWatch Logs, a **pre-created SSM EC2 instance profile**, and a **zero-ingress**
security group. AWS resource creation happens only when the operator reviews a
plan and explicitly runs `terraform apply`. See
[the full local/IAM/SSM handoff](../../docs/deployment/08_aws_ssm_deployment_handoff.md).

No original GeoLife private cache, GPS trajectories, passwords or cloud
credentials are written to Terraform state or user data.

**Free plan IAM option:** preserving AWS Free Tier credits? Avoid creating AWS Organizations; use IAM user MFA and browser-based temporary AWS CLI login per [Free-plan bootstrap](../../docs/deployment/10_aws_free_plan_iam_user_bootstrap.md).

**IAM bootstrap prerequisite:** an existing account IAM administrator must
create the EC2 service role and instance profile `geolife-mle-dev-ec2-role`
through the AWS Console. A separate IAM Identity Center deployment permission
set may then use `iam:PassRole` on only that role; **Terraform no longer needs
`iam:CreateRole`, `iam:AttachRolePolicy`, `iam:PutRolePolicy` or
`iam:CreateInstanceProfile`**. Use the [Console IAM guide](../../docs/deployment/09_aws_iam_identity_center_bootstrap.md) and project-scoped permission-set templates in `infra/iam/`. Only the operator can
later provision a synthetic demo account on the EC2 host.

## Recovery after a partially completed Free-plan apply

If `t3.medium` was rejected as not Free Tier eligible, **do not delete your
local Terraform state, the already-created ECR repository, log group, ECR
lifecycle policy, or Security Group**. Use the recovery runbook
[11 — Partial apply recovery](../../docs/deployment/11_aws_free_plan_partial_apply_recovery.md).
The account IAM group's explicit deny list must be updated by an IAM
administrator before attempting a newly eligible instance type.

## Local validation / plan

```bash
cp infra/terraform/terraform.tfvars.example infra/terraform/terraform.tfvars
# Set vpc_id, subnet_id, region. Subnet must route to an Internet Gateway.
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -out=tfplan
terraform -chdir=infra/terraform show tfplan
```

**Charged resources if you apply:** EC2 (default c7i-flex.large, AWS Free-plan eligible type), public IPv4,
encrypted 20GiB gp3 volume, ECR storage/scanning, CloudWatch Logs and data
transfer. SSM itself doesn't require opened inbound ports. AWS Budgets should
be configured and account/region verified before apply. Never treat budget
notifications as a hard spend cap.

The instance sits in an operator-selected public subnet **but the security
group has no inbound rules**. Public IP is used only for outbound SSM/ECR/OS
patches on HTTPS: no public HTTP server, ALB, NAT gateway or DNS are created.
The browser connects by IAM-authorized SSM port forwarding to a container
bound on host localhost. This is **not an internet-facing deployment**.

Docker starts only after image push and private account provisioning through
SSM. CloudWatch Log Group retention is 7 days; Prometheus metrics are still
local/private and no monitoring dashboard/SQS worker exists yet.

## Non-production restrictions

- One instance and one writable demo-auth SQLite DB (not horizontally scalable).
- Default Docker image denies anonymous legacy /v1 and stateless /v2 inference.
- Historical GeoLife cache must not be copied to AWS without an explicit
  privacy/legal/data-access decision.
- Terraform backend is local in this training stage. Protect state from
  disclosure/loss; adopt encrypted remote backend/locking before collaboration.
- Use the AWS CLI/local account-verified ECR build script
  `scripts/aws_build_push_ecr.sh`, not plaintext access keys.
- Terminate/destroy paid resources immediately after the demo, after checking
  the explicit ECR image cleanup precondition.
