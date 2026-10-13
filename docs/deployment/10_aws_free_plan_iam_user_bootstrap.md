# AWS Free plan (no Organizations) — GeoLife IAM user bootstrap

**Choose this instead of IAM Identity Center organization instance if you wish
to preserve the AWS $200 Free Tier credits.** AWS states that creating/joining an
Organization causes immediate Free Tier credit expiration and conversion to
pay-as-you-go. Do not click "Enable IAM Identity Center with AWS Organizations".

References:
- https://aws.amazon.com/free/free-tier-faqs/
- https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html
- https://docs.aws.amazon.com/singlesignon/latest/userguide/account-instances-identity-center.html

The restricted alternative for a **single-account learning project**:
an IAM **user** with Console sign-in and MFA, scoped IAM **group policies**,
and AWS CLI **`aws login`** (AWS CLI >=2.32.0), which uses temporary
credentials and does not require permanent access keys. This is a practical
Free-plan alternative, not the same federation control plane as AWS SSO.

## 1. Existing IAM user: finish provisioning, no access key

Your existing `IAM → Users → geolife-ops` is valid for this alternative.
On the user page:

1. **Security credentials** → **Console sign-in** → **Enable console access**.
   Set strong unique password; never use the account root login for daily work.
2. **Multi-factor authentication (MFA)** → **Assign MFA device**; use FIDO2
   security key/passkey if available, otherwise authenticator app.
3. Under **Access keys**, leave **zero** keys. Do not click Create access key.
4. Check no `AdministratorAccess`, `PowerUserAccess`, generic
   `AmazonEC2FullAccess`, or `IAMFullAccess` policies are attached.
5. Ensure the AWS account root user also has MFA and its own recovery setup.

## 2. IAM groups (these are NOT SSO permission sets)

For the existing two groups:

- `geolife-operators`: attach only the scoped custom **inline policy**
  from `infra/iam/geolife-operator-permission-set.template.json`.
- `geolife-deployers`: attach the scoped custom **inline policy**
  from `infra/iam/geolife-deployer-permission-set.template.json`.

Replace `REPLACE_ACCOUNT_ID` with the exact account ID in **both**
templates before pasting JSON. They target `ap-southeast-1` and
`geolife-mle-dev` resource names. These JSON templates work as IAM group
inline policies as well as SSO permission-set inline policies: only the
attachment UI changes.

**Important:** If `geolife-ops` belongs to both IAM groups, the effective
permissions are the UNION of both policies, not two separately selectable roles.
For least privilege, keep `geolife-ops` in **operators** for daily use;
the account administrator temporarily adds the user to **deployers** only
for Terraform apply/teardown, and removes it afterward. A dedicated
`sts:AssumeRole` deployment-role setup with MFA can replace this manual
membership workflow if you need more formal JIT separation.

These policies are **starting templates** for one restricted dev account:
verify intended region and repository, evaluate with IAM Policy Simulator,
and adjust only specific denied API actions. The EC2-creation policy has
some Region-scoped actions that cannot be fully tied to one resource before
it exists. Neither group is an IAM admin.

## 3. Allow temporary AWS CLI login without IAM user access keys

AWS CLI v2.32.0+ supports `aws login` using console credentials:

https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sign-in.html

IAM administrator: AWS IAM → Users → geolife-ops → Add permissions.
Attach AWS-managed `SignInLocalDevelopmentAccess` or instead attach
a **narrower inline policy for same-device login only**:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "signin:AuthorizeOAuth2Access",
      "signin:CreateOAuth2Token"
    ],
    "Resource": "arn:aws:signin:ap-southeast-1:REPLACE_ACCOUNT_ID:oauth2/public-client/localhost"
  }]
}
```

The narrowed policy does not allow the `remote` OAuth public client.
The managed policy is an acceptable AWS-documented fallback if a
region/client-scope mismatch prevents successful login; it grants
OAuth sign-in, **not** general EC2 or IAM administrative API permissions.
Both approaches still require the resource-specific group policies.

On your own local machine:

```bash
aws --version  # must be >= aws-cli/2.32.0
aws login --profile geolife-ops
# Use the newly enabled IAM console login, not the root identity.
aws sts get-caller-identity --profile geolife-ops
aws configure list --profile geolife-ops  # credential TYPE should be login
```

If Terraform's AWS provider doesn't directly recognize the CLI login profile,
use an AWS CLI credential-process bridge in `~/.aws/config`:

```ini
[profile geolife-terraform]
region = ap-southeast-1
credential_process = aws configure export-credentials --profile geolife-ops --format process
```

Then locally:

```bash
export AWS_PROFILE=geolife-terraform
export AWS_REGION=ap-southeast-1
aws sts get-caller-identity
terraform -chdir=infra/terraform init
terraform -chdir=infra/terraform validate
terraform -chdir=infra/terraform plan
```

No permanent keys are placed in `~/.aws/credentials`. The temporary
AWS CLI login cache is a sensitive credential store: secure your laptop,
lock screen/disk, never send its contents to chat, and run
`aws logout --profile geolife-ops` when finished.

## 4. EC2 service role still requires a one-time Console bootstrap

An existing AWS administrator must separately create the
`geolife-mle-dev-ec2-role` EC2 role/instance profile, attaching only
`AmazonSSMManagedInstanceCore`, a **GeoLife-ECR-repository-only** pull
policy, and a **GeoLife-CloudWatch-loggroup-only** writer policy.

Follow **Section 2** of
`docs/deployment/09_aws_iam_identity_center_bootstrap.md` for the exact
EC2 service-role policy JSON. This is not a user login/CLI identity.

Terraform reads `instance_profile_name = "geolife-mle-dev-ec2-role"`
and the project deployer group has **only** exact `iam:PassRole` on the
matching EC2 role. It is not allowed to create/modify IAM roles.

## 5. Operational billing safeguards

- Visit AWS **Billing and Cost Management → Credits** to confirm actual
  remaining credit and expiration date; Free plan can end due to time
  even when credit remains. No AWS Organizations creation.
- Create an AWS Budget for the project. Budgets alert, not hard-stop.
- Verify the Free plan allows your selected EC2 instance type/usage;
  `t3.medium` is **NOT** Free-plan eligible and was rejected by EC2. Use the new x86_64 default `c7i-flex.large` (4 GiB) only after verifying account/AZ eligibility. See [partial apply recovery](11_aws_free_plan_partial_apply_recovery.md) if ECR/CloudWatch/SG were already created before the EC2 failure.
- The proposed EC2 host has a public IPv4 address for outbound HTTPS but
  **zero inbound SG rules**; its EBS/ECR/logging and IPv4 usage can consume
  credits. Never call Terraform `apply` before approving the plan.
- Do not copy historical GeoLife stay cache or per-user HOME/OFFICE positions
  onto AWS. Initial demo uses fully synthetic GPS only.

## Free plan EC2 policy refresh

The `geolife-deployers` IAM Group policy template in `infra/iam/` was updated to explicitly allow only `c7i-flex.large` and `m7i-flex.large` in its instance-type deny guard. An IAM administrator **must update the existing group policy in AWS Console**; committing the JSON template on GitHub does not change live IAM. Never enable full EC2 or IAM permissions as a workaround. The updated EC2 sizes may consume credits while running.

## Next operator checkpoint

Send **only**:
1. Confirmation that IAM Console access is enabled and MFA is assigned
   to `geolife-ops`;
2. Whether you can run `aws login --profile geolife-ops` on your machine;
3. Sanitized account/role and the exact AWS error action if any (no tokens,
   passwords, complete credential cache, Terraform state or GPS data).
