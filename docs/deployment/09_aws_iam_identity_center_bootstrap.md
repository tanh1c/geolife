# AWS IAM Identity Center bootstrap — Existing AWS Organizations ONLY

**STOP if you are on the AWS Free plan with credits:** creating/joining an AWS Organization can immediately expire remaining AWS Free Tier credits. Use the [Free-plan IAM User + MFA + temporary AWS CLI login](10_aws_free_plan_iam_user_bootstrap.md) instead. The section below is appropriate only when an AWS Organization already exists and billing consequences have been evaluated.

**Purpose:** create a distinct, short-lived SSO identity for GeoLife and a
separate narrowly scoped EC2 **service role**, with no AdministratorAccess,
IAM user access keys, full-account PowerUserAccess, or permission to create
arbitrary IAM roles in the deployment identity.

**Operator/admin action only. No IAM resources are automatically created by
this repository.** Links to live [IAM Identity Center AWS docs](https://docs.aws.amazon.com/singlesignon/latest/userguide/).

## Architecture / names

| Item | Name |
|---|---|
| Workforce login (IAM Identity Center user) | `geolife-ops` (use your own accessible email) |
| Group, provision / teardown | `geolife-deployers` |
| Group, session / operations | `geolife-operators` |
| Permission set (temporary) | `GeoLifeDevDeployer` |
| Permission set (daily) | `GeoLifeDevOperator` |
| EC2 service role + instance profile | `geolife-mle-dev-ec2-role` |
| Region / environment | `ap-southeast-1` / `dev` |
| ECR repository | `geolife-mle-dev-api` |
| CloudWatch log group | `/geolife/dev/api` |

IAM Identity Center login is for the human operator; the service role belongs
to EC2 and is assumed automatically by `ec2.amazonaws.com`. No SSH key or
permanent AWS access key is needed.

## 0. Before enabling Identity Center

- Login to [AWS Console](https://console.aws.amazon.com/) with an existing
  bootstrap administrator, **not** as root for day-to-day work.
- Confirm the actual AWS account and billing plan. On a standalone Free Tier
  account, creating an AWS Organization can change the billing plan and expire
  credits: read the console warning BEFORE enabling an **organization** instance.
- For assigning **AWS account access permission sets**, use an **organization
  instance**, not an account instance. Account instances are for applications,
  not AWS account permission sets. If an organization instance already exists,
  use it; don't create another one.
- IAM Identity Center *home Region* may differ from the EC2 region. Select the
  existing Identity Center Region when administering users; use
  `ap-southeast-1` for deployment resources.

## 1. Create a login

AWS Console search: **IAM Identity Center** → **Users** → **Add user**.

- Username: `geolife-ops`; email: one you control.
- Invite/activate by email; choose a unique password.
- IAM Identity Center → Settings → Authentication → Multi-factor
  authentication → use **Always on** or equivalent required MFA, and
  require registration. Prefer a phishing-resistant security key / passkey.
- Do NOT go into IAM → Users → Create user with an access key for this workflow.

AWS Identity Center → **Groups** → **Create group** (two groups named above).
Add `geolife-ops` to both. A deployment user can later be removed from the
deployer group after provision while retaining operator access.

## 2. Bootstrap the EC2 instance service role ONCE as account IAM admin

Open AWS Console → **IAM** → **Roles** → **Create role**:

1. Trusted entity: **AWS service**, use case **EC2**.
2. Attach **AmazonSSMManagedInstanceCore** only. ECR pull access is provided by
   a project-repository-scoped inline policy below, not account-wide ECR read.
3. Name `geolife-mle-dev-ec2-role`. Add project/environment tags.
4. Create role. The AWS EC2-role console workflow creates an **instance
   profile with the same name** automatically.
5. IAM → Roles → project EC2 role → Add permissions → Create inline policy → JSON.
   Name it `GeoLifeDevEcrPull` and paste:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "ecr:GetAuthorizationToken",
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecr:BatchGetImage",
        "ecr:GetDownloadUrlForLayer",
        "ecr:BatchCheckLayerAvailability"
      ],
      "Resource": "arn:aws:ecr:ap-southeast-1:REPLACE_ACCOUNT_ID:repository/geolife-mle-dev-api"
    }
  ]
}
```

6. Under the same EC2 role, create another inline policy named
   `GeoLifeDevCloudWatchWriter` with this JSON:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Sid": "WriteGeoLifeDevLogStream",
    "Effect": "Allow",
    "Action": [
      "logs:CreateLogStream",
      "logs:DescribeLogStreams",
      "logs:PutLogEvents"
    ],
    "Resource": "arn:aws:logs:ap-southeast-1:REPLACE_ACCOUNT_ID:log-group:/geolife/dev/api:*"
  }]
}
```

Replace `REPLACE_ACCOUNT_ID` with your actual 12-digit ID. Inline policy
name: `GeoLifeDevCloudWatchWriter`. No `logs:CreateLogGroup` (Terraform
creates it), no IAM write, no S3 and no historical GeoLife data access.

The EC2 role is **not** the human identity and should not be made trustable
by arbitrary IAM users. Only EC2 service principal can assume it.

## 3. Create two custom permission sets (no AdministratorAccess)

AWS Console → **IAM Identity Center** → **Multi-account permissions** →
**Permission sets** → **Create permission set** → **Custom permission set**.

For the first set:

- Name: `GeoLifeDevDeployer`
- Session duration: 1 hour (temporary; this role creates/destroys infrastructure)
- Policies: **Inline policy** → JSON. Paste the template from
  `infra/iam/geolife-deployer-permission-set.template.json`, after replacing
  every `REPLACE_ACCOUNT_ID` with the correct 12-digit AWS account ID.
- Don't attach `AdministratorAccess`, `PowerUserAccess`, `IAMFullAccess`,
  `AmazonEC2FullAccess`, or `AmazonEC2ContainerRegistryFullAccess`.

For the second set:

- Name: `GeoLifeDevOperator`
- Session duration: 1–4 hours.
- Use `infra/iam/geolife-operator-permission-set.template.json` with the
  same account-ID replacement.

These are **project-specific templates**, not a blanket AWS admin role.
They must be reviewed for the real account, VPC/subnet, tags and AWS policy
simulator/CloudTrail feedback. The deployer template explicitly:
- restricts service APIs to selected EC2 write, ECR repo write, CloudWatch
  log group and a single public AL2023 AMI parameter;
- restricts `iam:PassRole` to exactly `geolife-mle-dev-ec2-role` and
  `iam:PassedToService=ec2.amazonaws.com`;
- grants **no** `iam:CreateRole`, `iam:PutRolePolicy`,
  `iam:AttachRolePolicy`, `iam:CreateUser`, `iam:CreateAccessKey`,
  or Organizations write actions;
- restricts deployment actions to Singapore region (EC2 write is currently
  region-scoped and permitted instance types are constrained, rather than
  fine-scoped to the future-created EC2 ARN; tighten the resource tag/VPC
  conditions after first successful plan).
  
The operator can start SSM sessions only on instances tagged
`Project=geolife-mle`, use approved SSM session documents and read the
GeoLife dev logs/ECR metadata. It cannot create or delete EC2/ECR/IAM.
An SSM shell may have powerful OS rights **inside the target EC2 host**, so
only a trusted operator should receive this permission set.

## 4. Assign the permission sets to the right AWS account

IAM Identity Center → **AWS accounts** → select the target account →
**Assign users or groups** → select **Groups**.

Assign `geolife-deployers` → `GeoLifeDevDeployer` and
`geolife-operators` → `GeoLifeDevOperator`. Assign groups, not the login
directly. The portal displays two roles the user can switch between.

If you modify the inline policy later, re-provision the permission set for
the target AWS account if the console requests it.

## 5. Local AWS CLI profiles (NO AWS access keys)

Install AWS CLI v2 and Session Manager plugin. Run:

```bash
aws configure sso --profile geolife-deployer
# Choose the AWS access portal start URL, its SSO region, target account
# and GeoLifeDevDeployer permission set.
aws configure sso --profile geolife-operator
# Choose GeoLifeDevOperator.

aws sso login --profile geolife-deployer
aws sts get-caller-identity --profile geolife-deployer

aws sso login --profile geolife-operator
aws sts get-caller-identity --profile geolife-operator
```

To plan or apply Terraform, explicitly choose the temporary deployer role:

```bash
export AWS_PROFILE=geolife-deployer
export AWS_REGION=ap-southeast-1
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan -out=tfplan
# Stop; review cost, resources, permissions and plan before apply.
```

For SSM sessions later, use `AWS_PROFILE=geolife-operator`.
Never share the portal password, MFA code, AWS access keys, CLI SSO token
cache, auth SQLite file, credentials, Terraform state or GPS cache in chat.

## 6. Mandatory scope / cost gates

- Make an AWS Budget alert and verify billing model. Budgets alert does
  **not** automatically stop charges.
- Prefer a dedicated **project AWS member account** for stronger account-level
  billing/permission isolation when your organization supports one.
- `terraform apply` is **operator-only**, after reviewing plan and expenses.
- PR #73 does not create IAM identities/roles, run apply or upload data.
- Historical GeoLife HOME/OFFICE data must not be uploaded to AWS before an
  independent privacy/permission decision. The first AWS demo is synthetic-only.
- Delete project compute/ECR/log resources when the demo ends, following the
  teardown procedure; do not delete the SSO/bootstrap identities automatically.

References:
- https://docs.aws.amazon.com/singlesignon/latest/userguide/howtocreatepermissionset.html
- https://docs.aws.amazon.com/singlesignon/latest/userguide/assignusers.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_passrole.html
- https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html
- https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager-getting-started-restrict-access.html
