# Phase A partial APPLY recovery — proposed IAM v3, REVIEW ONLY

> **STOP:** Terraform Phase A 2026-10-19 APPLY failed with PARTIAL AWS resources and PARTIAL Terraform state. The owner authorization was **only for saved plan SHA `517fb94adcae4e8a80821c8f82a05dd0bbcc71dbabe08a30a8746aed0b92a10c`**, now STALE because three resources were created/tracked. **Never reapply that binary plan**, never delete/import/recreate state, never attempt cleanup automatically. Future remaining-resources APPLY needs a NEW plan, SHA, guard and SEPARATE owner approval.

This is a **draft full replacement of the previously attached** `GeoLifeMentorBetaPhaseADeployer` managed policy, **not** an IAM update performed by ChatGPT. Admin must compare this document to AWS current default version before reviewing/applying. The earlier v2 remains in `docs/deployment/24_mentor_beta_phaseA_deployer_policy_CANDIDATE.json`.

## Confirmed failure evidence (from local operator, no log re-run)

- `s3:GetBucketAcl`: AccessDenied during Terraform AWS S3 bucket lifecycle/refresh. Add **only exact-beta-bucket** read permission.
- `s3:GetBucketPolicyStatus`: AccessDenied during follow-up bucket verification (may not be first APPLY failure). Add **only exact-beta-bucket** read permission.
- `cognito-idp:TagResource`: AccessDenied during `CreateUserPool`; reported authorization resource `arn:aws:cognito-idp:ap-southeast-1:939169265033:userpool/*`. Candidate v2 already had `TagResource` on `userpool/ap-southeast-1_*`, guarded by both `aws:RequestTag/Project` and `aws:RequestTag/Environment`; the earlier simulation used a fabricated concrete pool ID and did **not** reproduce the create-time `userpool/*` authorization shape. Candidate v3 **proposes changing only this one Resource pattern** from `arn:aws:cognito-idp:ap-southeast-1:939169265033:userpool/ap-southeast-1_*` to `arn:aws:cognito-idp:ap-southeast-1:939169265033:userpool/*` while retaining Singapore/account and both request-tag conditions. It is a **hypothesis**, NOT verified as the unique root cause: missing request-tag context, SCP or IAM evaluation can also block.

## Proposed changes v2 -> v3

1. Add `s3:GetBucketAcl` and `s3:GetBucketPolicyStatus` to `BetaExactS3BucketLifecycle`, resource `arn:aws:s3:::geolife-mentor-beta-939169265033-site`.
2. Broaden **only** `BetaCognitoInitialPoolTags.Resource` from `userpool/ap-southeast-1_*` to `userpool/*` under account `939169265033` in `ap-southeast-1`; retain exact `aws:RequestTag/Project=geolife-mle`, `aws:RequestTag/Environment=mentor-beta`, and `aws:RequestedRegion=ap-southeast-1`.
3. No changes to CloudFront permission, other Cognito lifecycle statements, EC2, IAM PassRole, S2b, Terraform HCL or state.

**SECURITY WARNING:** This `TagResource` allowance is *not limited to the beta pool by name*; even with request-tag checks, a principal may tag a pre-existing user pool with `Project=geolife-mle, Environment=mentor-beta` and subsequently satisfy tag-based lifecycle permissions. Admin must explicitly accept or devise a stronger control (for example, a separate controlled short-lived bootstrap permission with prompt removal), check whether other Cognito pools exist, and avoid keeping this bootstrap permission attached after Phase A. The existing v2's userpool ID prefix would also cover normally formatted Singapore pool IDs; do not assume ARN widening alone definitively solves the error.

## Admin READ-ONLY validation before IAM version edit

- Download **the new v3 candidate from this exact commit**, run `aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY --policy-document file:///tmp/... `. Error and security findings are NO-GO pending review.
- Run `iam simulate-custom-policy` against (a) exact S3 bucket for `GetBucketAcl` and `GetBucketPolicyStatus`, (b) Cognito `TagResource` for the `...:userpool/*` authorization resource and for a placeholder `...:userpool/ap-southeast-1_EXAMPLE`; use Singapore and exact request tag context, then repeat without tag context (should DENY). Simulation success may **not** predict actual CreateUserPool nested tag evaluation.
- Review CloudTrail logs for failed `CreateUserPool` `AccessDenied` if visible (read-only); do not log credentials, PII, full request payload or secrets. Confirm `CreateUserPool` tags from provider `default_tags`: Project=geolife-mle, Environment=mentor-beta, DataClass=synthetic-only, ManagedBy=terraform.
- If checks are satisfactory and owner grants **separate IAM-policy-update approval**, admin changes the *existing managed policy's default version*, not attaching unrelated broad policies. No modification on `geolife-ops` is needed for `iam:SimulatePrincipalPolicy`; AWS admin can test it.

## Phase A recovery and new owner approval

- Preserve `infra/terraform/mentor_beta_foundation/terraform.tfstate`, backup `C:\Users\LG\geolife-private\mentor-beta-state-backups\phaseA-20261019T040627159Z-exit1.dpapi`, associated scripts and log. Do not commit any of them.
- **Observed** partial state contains exactly S3 site bucket, CloudFront OAC and CloudFront response headers policy. Confirm those three objects via read-only inventory and compare to state; check for untracked Cognito pool or CloudFront distribution **read-only** (not assume absent solely because state omits).
- After approved IAM repair, use same isolated root/provider 6.69.1, run **READ-ONLY fresh Terraform PLAN from current state** and save it privately, inspect `terraform show -json` for changes and ensure no unintended UPDATE/DELETE/REPLACE. A new plan MAY have less than 11 CREATE depending on drift or provider refresh; don't assume a count.
- Present NEW plan binary SHA256, action counts, AWS identity, resources, costs, state backup plan to owner for **separate explicit approval**. Prior Phase A APPLY consent is now **consumed**; it does not approve running a new plan.
- On new approval only: execute guarded APPLY, back up both success and failure state with DPAPI, verify SHA/decryption, STOP before subsequent phases. If any API action denied, STOP and capture the exact action.
- Teardown remains separately approval-gated. DPAPI CurrentUser machine/profile-loss risk accepted for first attempt; state itself should not leave the private workspace.

References:
- https://docs.aws.amazon.com/AmazonS3/latest/userguide/using-with-s3-policy-actions.html
- https://docs.aws.amazon.com/cognito/latest/developerguide/tagging.html
- https://docs.aws.amazon.com/service-authorization/latest/reference/list_amazoncognitouserpools.html
