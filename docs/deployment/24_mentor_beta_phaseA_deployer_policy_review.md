# Candidate ONLY — IAM admin review required

This file is a **proposed IAM policy**, not an authorization and not a guaranteed-complete Terraform provider permission set. It was derived from the Phase A 14-CREATE Terraform root and currently reported IAM denials. DO NOT attach or apply without an account-admin review and a read-only Policy Simulator pass.

Principal: IAM User `geolife-ops`, AWS account `939169265033`.

Application: **Phase A only** (S3 private site, CloudFront HTTPS/OAC/headers, Cognito User Pool Essentials, app client, managed login); excludes EC2/ELB, Lambda, API Gateway, VPC Link, ECR, IAM role/user writes and actual S3 frontend upload. This file does not replace separate approvals for those stages.

## Guardrails and known caveats

- S3 scope is the **one exact bucket** `geolife-mentor-beta-939169265033-site`. Object action is limited to delete/read for authorized teardown and review; **no object upload granted** for later frontend phase.
- Cognito actions are limited to region Singapore. A new pool requires `aws:RequestTag/Project=geolife-mle` and `aws:RequestTag/Environment=mentor-beta`; subsequent pool actions require existing resource tags. Confirm Terraform provider AWS 6.69.1 actually sends these tags in the create request and on generated pool before relying on these conditions. Incomplete tagging MUST fail closed. Some user pool action/resource combinations may have different authorization semantics: test via IAM simulator + service authorization table, don't weaken to broad `*` on denial.
- CloudFront is GLOBAL: deliberately **no** `aws:RequestedRegion=ap-southeast-1` for CloudFront operations. Create/List where ARN/resource-scoping isn't available use `Resource:"*"` for those specific actions; **this can allow creating other CloudFront resources** and is an unavoidable review concern with a shared IAM deployer. Distribution lifecycle relies on existing `Project/Environment` tags, so verify default tags are propagated. OAC and response-header policy resources use account-level ARN patterns because their resource IDs are assigned after CREATE. After APPLY, consider replacing wildcards with exact generated ARNs for ongoing maintenance, and detach the create policy after Oct 23 teardown.
- Cognito `CreateUserPool` with tags may require `cognito-idp:TagResource`; this draft grants only initially tagged requests for the project's pool ARN. Check the actual `CreateUserPool`+`TagResource` authorization path using simulation; an untagged request fails closed. `iam:PassRole` is intentionally **not** included; Terraform Phase A has no SMS or other IAM Role input. Provider-specific additional actions must be reviewed and added individually in a revised policy, never wildcard `cognito-idp:*` or `iam:*`.
- When CloudFront distribution is created with tags, underlying API authorization may involve `cloudfront:TagResource` and `CreateDistribution`. Initial `TagResource` is condition-locked to the two required request tags, while existing resources are condition-locked to their resource tags. Confirm the request tags are actually present when the provider creates the distribution; do not attempt real create as a policy test.
- Candidate includes selected read/create/rollback actions only, **not automatically approved destroy permission**. Rollback remains blocked without a tested state-backup plan and separately approved Oct 23 teardown; Cognito has deletion protection ACTIVE, S3 versioning enabled and `force_destroy=false`, CloudFront must disable then delete after full deployment.
- Check policy in AWS IAM Access Analyzer ValidatePolicy/Policy Simulator (READ-ONLY), with **service-appropriate resources and context**; simulate at least `s3:CreateBucket`, `cloudfront:CreateDistribution`, `cognito-idp:CreateUserPool` and relevant rollback actions. **A simulator PASS is necessary but not sufficient**; service quota, async propagation and Terraform provider API behavior still need monitoring.
- This policy excludes CloudFront `CreateInvalidation` / S3 `PutObject` because static frontend deployment belongs to a **separate upload stage**.
- User-approved initial spend planning envelope is ~USD 30 for Oct 19–23; cost visibility skipped at user's direction, but this is not unlimited AWS spending nor consent for any AWS APPLY.
- **No AWS IAM policy creation/attachment, Terraform APPLY or deployment was performed by adding this file.**

References:
https://docs.aws.amazon.com/service-authorization/latest/reference/list_cloudfront.html
https://docs.aws.amazon.com/service-authorization/latest/reference/list_cognito-idp.html
https://docs.aws.amazon.com/service-authorization/latest/reference/list_s3.html


## 2026-10-19 AWS Access Analyzer correction (candidate v2)

Admin CloudShell reported three `INVALID_ACTION` findings in the earlier candidate. They were IAM permission *names* mistakenly copied from REST API operation names. The corrected candidate removes those three invalid entries. No new permissions were needed because the corresponding valid IAM actions were already present:

| S3 API operation | IAM authorization action retained |
|---|---|
| `DeletePublicAccessBlock` (bucket) | `s3:PutBucketPublicAccessBlock` |
| `DeleteBucketEncryption` | `s3:PutEncryptionConfiguration` |
| `DeleteBucketTagging` | `s3:PutBucketTagging` |

Official reference: https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html ; https://docs.aws.amazon.com/AmazonS3/latest/API/API_DeleteBucketEncryption.html

**The original validation was FAIL. A fresh AWS Access Analyzer validation of THIS commit is REQUIRED; zero output in findings means no findings were returned, but still does not prove permissions are sufficient.** Follow with read-only IAM Policy Simulator tests of S3 exact bucket + CloudFront/Cognito create and rollback, including request tags. Do not attach the candidate policy or APPLY resources solely because syntax validation passes. This commit changes docs/policy only; it does not change saved Phase A Terraform files.
