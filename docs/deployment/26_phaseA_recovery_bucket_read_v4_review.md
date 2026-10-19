# GeoLife Mentor Beta — recovery IAM v4 CANDIDATE (READ ONLY proposal)

**Status: AWS update NOT performed. Owner/admin approval required. This policy is NOT an authorization to APPLY Terraform.**

## Trigger

Recovery `terraform plan` from the PARTIAL Phase A state failed during S3 refresh with `AccessDenied s3:GetBucketCORS` on `arn:aws:s3:::geolife-mentor-beta-939169265033-site`. Operator preserved partial state (bucket + CloudFront OAC + response headers policy), ran a separate DPAPI state backup with synthetic round-trip/hash check and reports no valid NEW plan. The partially written `mentor-beta-phaseA-recovery-20261019.tfplan` is INVALID. Never APPLY it or the initial 14-CREATE saved plan.

The AWS `GetBucketCors` API requires `s3:GetBucketCORS`. Terraform's `aws_s3_bucket` read path reads bucket policy, ACL, CORS, website and potentially further configuration in a single refresh sequence, even for an HCL bucket block that only specifies `bucket` and `force_destroy`. Therefore, addressing one missing read action at a time is inefficient.

References:
- https://docs.aws.amazon.com/AmazonS3/latest/API/API_GetBucketCors.html
- https://github.com/hashicorp/terraform-provider-aws/blob/main/internal/service/s3/bucket.go
- https://registry.terraform.io/providers/hashicorp/aws/6.69.1/docs/resources/s3_bucket

## Proposal

Build on v3 with ONE additional permission action in `BetaExactS3BucketLifecycle`:

```json
{
  "Effect": "Allow",
  "Action": "s3:GetBucket*",
  "Resource": "arn:aws:s3:::geolife-mentor-beta-939169265033-site"
}
```

The attached JSON contains this action in the pre-existing exact-bucket statement rather than adding a separate statement. It **only broadens read access for S3 bucket-level APIs on this ONE named bucket**, not other buckets, object contents, new IAM privileges, S3 writes, deletions, CloudFront or Cognito rights. The wildcard also includes future GetBucket-prefixed AWS IAM actions which may exceed currently known Terraform needs: this is a transparent least-privilege tradeoff to avoid repeated refresh denials on this single disposable beta bucket.

Keep `s3:GetEncryptionConfiguration` and all previous exact-bucket write/delete/read permissions unchanged. IAM `s3:GetBucket*` is NOT equivalent to `s3:*` and does NOT allow edits/deletions.

**This is a proactive READ permission only.** Provider v6.69.1 may additionally read resource tags using `s3:ListTagsForResource` or other non-`GetBucket*` APIs not included here; examine pinned provider source/trace or request an individually reviewed action if an independent permission is required. Do NOT broadly add `s3:*`. No guarantee the new plan will succeed without other independent issues.

## Review before admin updates IAM

1. Download the exact v4 JSON and run read-only `aws accessanalyzer validate-policy --policy-document file:///tmp/geolife-v4.json --policy-type IDENTITY_POLICY --region ap-southeast-1`.
2. Using `iam:SimulateCustomPolicy`, verify `s3:GetBucketCORS`, `s3:GetBucketWebsite`, `s3:GetBucketLogging`, `s3:GetBucketVersioning` are ALLOWED only on `arn:aws:s3:::geolife-mentor-beta-939169265033-site`; verify the same GetBucketCORS action on a different bucket is NOT allowed by the v4 candidate alone. Explicitly check if any unexpected broader action is exposed by wildcard.
3. Confirm IAM current managed policy default version equals the previously approved v3 candidate (scope & tags), then request **owner/admin explicit approval to move v3 -> v4**. Preserve v3 version for rollback. No standalone IAM policy attached; no `AdministratorAccess`.
4. Once v4 has been approved and attached/effective, perform only a new `terraform plan` from preserved PARTIAL state and pinned provider. Keep Terraform source, state, account, region, `api_gateway_origin=""` unchanged. Initial 14 CREATE plan and incomplete recovery output are **STALE/INVALID**, no retries. If full plan succeeds, save under a NEW private path, compute SHA-256, inspect create/update/delete/replace guards, check inventory/untracked resources and present the NEW plan for owner **separate explicit APPLY authorization**.
5. STOP on any further AWS IAM denial. Preserve local state and current DPAPI encrypted backup. No bridge, EC2 start, S2b mutation, API Gateway, uploads, Cognito user creation, Terraform destroy or merge.

This policy edit does NOT itself solve Cognito runtime TagResource uncertainty; v3 was updated manually on AWS and no Cognito-create API may be called except under a future separately approved Terraform APPLY.

DPAPI backup is profile-bound; off-device recovery risk remains. Future teardown Oct 23 requires separate approved changes.
