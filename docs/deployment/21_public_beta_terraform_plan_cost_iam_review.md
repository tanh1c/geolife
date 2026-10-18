# Mentor beta — Terraform PLAN ONLY (2026-10-18)

**STATUS: NOT DEPLOYED / NO SAVED PLAN / NO APPLY AUTHORIZATION.** This PR adds two isolated Terraform roots, plan guard, IAM/billing runbook. It does not alter existing EC2, S2b, CloudWatch resources or Terraform states. API/browser code is in Draft PR #81; no real participant GPS, accounts, credentials, or private GeoLife cache may be published.

## Chosen staged architecture

Phase A **foundation**: HTTPS CloudFront default domain + private S3 bucket (OAC, no public ACL), Cognito Essentials User Pool admin-create-only (no self signup), managed login, one public/no-secret SPA client with Authorization Code + PKCE, custom scope geolife-demo/read and group geolife-demo-testers. Initial CloudFront has **NO /v3/beta API proxy**. The S3 bucket starts empty, so **the resulting URL is NOT a functioning website until reviewed frontend assets are uploaded**.

Phase B **private backend**: CloudFront same-origin path /v3/beta/* (cache disabled, passes Authorization) -> API Gateway HTTP API JWT authorizer & required scope -> VPC Link -> reviewed **existing internal ALB listener** -> separately provisioned/routable FastAPI instance with PR #81 beta mode. Phase B is **BLOCKED TODAY**: current EC2 is SSM-only, has zero inbound, no ALB/listener/port target in its Terraform, and is stopped. Cannot simply attach API Gateway to EC2 loopback 127.0.0.1. This PR does NOT provision/attach ALB, change EC2 SG or start EC2. Network migration/isolated backend + ALB/target group requires a separate plan and explicit owner approval. The API Gateway API origin must be added to Phase A via a **second reviewed Terraform UPDATE** after Phase B passes its gates; the initial strict create-only guard deliberately rejects that update.

Published website URL being reachable does not grant API access. Only manually invited Cognito test accounts with the tester group, correct scope, valid access token, and explicit server-private Cognito sub -> synthetic fixture owner mapping may request data. No GeoLife ID ownership inferred from Cognito. Existing SQLite/internal demo, v1/v2 routes, S2b jobs, metrics and historical cache remain unavailable in the public beta app mode.

## Phase A private plan commands (Windows PowerShell; DO NOT APPLY)

Run from an **isolated checkout entirely under a private non-Git working directory**: create the private parent directory locally, then clone/fetch the PR branch there without resetting active worktrees. This keeps Terraform's default local state, .terraform provider downloads, saved plan and plan JSON away from the main repo. The missing private folder is NOT an AWS blocker: local directory creation is permitted. Verify the exact branch SHA and an empty isolated state before planning. Use the IAM-authorized operator; no new AWS privileges should be added by the agent.

### Minimum hard gates for PLAN versus additional APPLY review

**Before initial Phase A PLAN (hard STOP only when violated):**
- Verified STS account 939169265033, provider region ap-southeast-1, exact PR-reviewed code, isolated empty Terraform state, and no *known* existing conflicting named foundation resources.
- Cognito ListUserPools and DescribeUserPoolDomain indicate no intended pool/domain (already ABSENT at 2026-10-18 preflight); S3 HeadBucket returned 404 for the exact intended name (preliminary negative probe, not a reservation or absolute guarantee).
- Do not proceed if a probe reports a definite existing conflict, if known Terraform state already manages the resources, or if the actual Terraform plan encounters AccessDenied/errors. Do not perform any AWS mutation to test names.

**Useful but NOT required to produce a saved PLAN:**
- `cloudfront:ListDistributions` lists *account-owned distributions*, while this design creates a **new distribution with AWS-assigned ID/hostname**, not a fixed distribution ID. Its denial means account inventory UNVERIFIED; it is not evidence of an actual CloudFront collision. Separately check name collisions of custom OAC and response-header policy before any APPLY when allowed.
- `s3:ListAllMyBuckets` lists only *buckets owned by the caller's account* and cannot prove global bucket-name availability. A precise `HeadBucket` 404 is useful preflight evidence, but not an atomic global reservation: S3 may still reject CREATE later. Never claim global uniqueness guaranteed from either call.
- `ce:GetCostAndUsage` is a *billing visibility* permission, not a Terraform plan prerequisite. Mark current account spend, Free Tier and billing eligibility **UNVERIFIED**; require owner/admin billing review and Singapore cost estimate **before APPLY**, without blocking non-mutating plan.
- If any of these three optional reads is AccessDenied, record the denial in sanitized evidence and continue PLAN ONLY. Do not request extra IAM solely to satisfy these optional queries.

**No plan means NOT RUN, not Terraform PLAN FAIL.** A successful local format/init/validate is not a successful remote saved PLAN.

```powershell
$env:AWS_PROFILE='geolife-terraform'
$env:AWS_REGION='ap-southeast-1'
aws sts get-caller-identity
terraform -chdir=infra/terraform/mentor_beta_foundation fmt -check
terraform -chdir=infra/terraform/mentor_beta_foundation init
terraform -chdir=infra/terraform/mentor_beta_foundation validate
# Use private absolute paths; never write plan/state into Git.
terraform -chdir=infra/terraform/mentor_beta_foundation plan -out='C:\Users\LG\geolife-private\mentor-beta\foundation.tfplan'
terraform -chdir=infra/terraform/mentor_beta_foundation show -json 'C:\Users\LG\geolife-private\mentor-beta\foundation.tfplan' > 'C:\Users\LG\geolife-private\mentor-beta\foundation-plan.json'
python scripts/mentor_beta_plan_guard.py --plan-json 'C:\Users\LG\geolife-private\mentor-beta\foundation-plan.json'
Get-FileHash 'C:\Users\LG\geolife-private\mentor-beta\foundation.tfplan' -Algorithm SHA256
```

Only report sanitized resource type counts/create-only guard, STS account+region, SHA256 and blockers. Terraform plan JSON and state can contain resource metadata and must remain private. A successful plan/guard is **NOT** approval to APPLY. Hash approval must refer to the exact immutable private saved plan, not re-planned output. Plan-only is permitted; IAM writes, creation, EC2 start, public ingress, DNS activation, account invitations and billing consumption are NOT.

## Explicit gates / separation of responsibilities

1. **AWS identity & state**: STS account must be 939169265033, region ap-southeast-1. Verify isolated private local state empty, Cognito pool/domain negative results and the precise S3 HeadBucket result. Other account-wide inventory/quotas are UNVERIFIED if denied and must be resolved before APPLY as applicable, but do not block initial non-mutating PLAN. Never equate 404 with guaranteed future S3 bucket reservation.
2. **Scoped IAM deployer**: Cognito UserPool/Create/Get/Describe/Delete, UserPoolClient, UserPoolDomain, UserGroup, ResourceServer, ManagedLoginBranding; CloudFront Distribution/OriginAccessControl/ResponseHeadersPolicy and relevant Get/List/Tag/Update/Delete; S3 create/list bucket and secure Get/Put bucket policy, encryption, versioning, public-access block. Admin must review exact AWS action/resource/condition applicability. Never grant `iam:*`, `ec2:AuthorizeSecurityGroupIngress`, broad s3:* on all buckets or let automation attach IAM. IAM for Phase B (API Gateway, VPC link, scoped SG Create and egress only) needs separate owner review.
3. **No signup**: `admin_create_user_config.allow_admin_create_user_only=true`; admin-created accounts only, with group membership and custom OAuth scope. Use Cognito *User Pool*, not Identity Pool. Use PKCE and exact HTTPS callback/logout; access-token lifetime 15 min. Authentication is not proof of original GeoLife research participant ownership.
4. **Public edge**: website TLS CloudFront, OAC private S3, managed security response headers, 2 paths only in API Gateway and backend strict allowlist. Confirm CloudFront forwarding of Authorization and query string with disabled cache; no `/v1`/`/v2`/`/internal/metrics` proxy. WAF, request throttles/byte caps, costs and branding clearance must be reviewed before serving internet traffic.
5. **Private ingress**: Phase B needs actual VPC ID, >=2 VPC Link subnets across AZs, internal ALB ARN/listener/SG, a target group, healthy service port and *separately approved* attachment/connectivity. VPC Link egress SG is not sufficient by itself; ALB SG + backend SG must explicitly permit only intended east-west flows. Original EC2 SG remains zero inbound in the original state until a dedicated migration review.
6. **Tests**: PR #81 integrated React Cognito login E2E with real invited mentor/tester users, PKCE state and callback, 401/403 invalid token/scope/group, cross-account IDOR, private IP exposure, CORS/CSP, asset rights, login/logout, backend stop/restart, rate/timeout/body limits, safe logging. Existing CLI Python CI PASS is NOT live Cognito E2E.

## Cost assessment (not an actual Singapore quote or spending cap)

| Component | Cost mechanism | Decision |
|---|---|---|
| Cognito Essentials direct user-pool users | AWS advertises up to 10,000 MAU/month free tier per eligible account/org; availability and billing must be verified | Likely low for invited testers, **not guaranteed $0** |
| CloudFront HTTPS | This root creates traditional pay-as-you-go distribution, **not automatically Free flat-rate plan**. Free flat-rate $0/mo and Pro $15/mo are separate choices with limitations | Compare PAYG with available Free plan before APPLY |
| S3 static files | Stored bytes, versioned objects and requests | Limit upload/storage; private OAC |
| API Gateway HTTP API | Per-request charges, data transfer | Add in Phase B only; 5 rps/10 burst are NOT cost cap |
| Internal ALB | Hourly plus LCUs, billed even if EC2 stopped | Primary fixed-cost blocker for short demo |
| EC2, EBS, IPv4, ECR and CloudWatch | Compute+storage+logs and IPv4 ($0.005 per address-hour standard rate) | Existing account usage separate; stopping EC2 does not delete ALB |

AWS published **US East illustration** ALB hourly base $0.0225 -> 4h=$0.09, 48h=$1.08, 720h=$16.20 **base only, NOT Singapore pricing**; exclude LCU, EC2 and transfer. Request exact `ap-southeast-1` AWS Pricing Calculator scenarios for 4h live demo, 48h tester weekend and 30-day 24/7 access, plus S3/CloudFront/API Gateway/ALB/VPC link/IPv4/EBS/Cognito. Compare a Lambda-backed synthetic API to avoid ALB fixed hours, but that requires a separate runtime conversion; not silently substituted for the EC2 goal. S2b Billing WAIVED BY OWNER applies only to S2b trial and **does not waive this public beta**.

Owner must explicitly approve maximum planned duration, expected budget, teardown deadline and AWS resource scope before APPLY. AWS Budgets alerts are notifications, not a hard spend limit.

Official sources:
https://aws.amazon.com/cognito/pricing/
https://aws.amazon.com/cloudfront/pricing/
https://aws.amazon.com/elasticloadbalancing/pricing/
https://aws.amazon.com/vpc/pricing/
https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-private.html
https://docs.aws.amazon.com/AmazonCloudFront/latest/DeveloperGuide/private-content-restricting-access-to-s3.html

**2026-10-18 local preflight**: STS verified, Cognito pool/domain negative, precise S3 HeadBucket 404; CloudFront list/S3 ListAllMyBuckets/Cost Explorer denied. Saved plan **NOT RUN**. Following this gate clarification, proceed to an isolated **PLAN ONLY** without expanding IAM; all three denied optional reads remain UNVERIFIED and must be reported. No go-live or APPLY approved.