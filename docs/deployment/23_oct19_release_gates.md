# GeoLife Mentor Beta — 19/10/2026 urgent release gate (NO APPLY)

**Current status: NOT LIVE, no HTTPS browser E2E, no AWS rollout authorization.** User wants a short owner-only preview on **19 Oct** and manually invited mentor access from **20 Oct**, with service closed and paid beta-only infrastructure torn down on **23 Oct** (all Asia/Ho_Chi_Minh, UTC+7). Keep the approved **EC2 + internal ALB + VPC Link** architecture. Owner consent to a planning budget around **USD 30** is **not permission to spend without review, not unlimited billing approval, and not any Terraform APPLY approval**. If the actual Singapore forecast exceeds USD 30, seek renewed owner approval.

## P0 IAM admin: unblock ELB read-only inventory

The operator reported `elasticloadbalancing:DescribeLoadBalancers AccessDenied` under the scoped `geolife-terraform` profile, principal `geolife-ops` in account `939169265033`. The AWS IAM administrator should review [the minimum read-only policy JSON](23_oct19_elb_readonly_preflight_policy.json) and, **only with authorization**, attach it to **the actual geolife-ops principal**, not the EC2 runtime instance role. This policy includes ONLY read-only ELBv2 Describe actions in Singapore and `Resource:"*"` because these inventory actions cannot practically be narrowed to one known future resource. It includes no ALB create/delete, IAM modification, or broad EC2 rights. Explicit DENY, SCP, permissions boundary or stale STS credentials may continue to block access; never work around them by changing execution identity.

Private PowerShell, **read-only only**, after IAM admin authorizes:

```powershell
$env:AWS_PROFILE='geolife-terraform'
$env:AWS_REGION='ap-southeast-1'
aws sts get-caller-identity
# Must match account 939169265033 and effective principal geolife-ops.
aws elbv2 describe-load-balancers --region ap-southeast-1 --output json
aws elbv2 describe-target-groups --region ap-southeast-1 --output json
aws elbv2 describe-account-limits --region ap-southeast-1 --output json
# Only if load balancers already exist / for reviewed listeners:
# aws elbv2 describe-listeners --load-balancer-arn <EXISTING-ALB-ARN> --region ap-southeast-1
```

Check planned names `geolife-mentor-beta-alb`, `geolife-mentor-beta-tg` for existing conflicts, quotas, listeners, and any tags from prior runs. If still AccessDenied, mark inventory UNVERIFIED and block APPLY. **Do not create dummy load balancers, targets or security groups to test collision.**

`ce:GetCostAndUsage` AccessDenied is **billing visibility UNVERIFIED**, not proof costs are zero and not strictly needed for technical Terraform PLAN. The billing/account owner may inspect AWS Billing directly, including current spend and free-tier eligibility; AWS Calculator can provide public Singapore forecast without granting a broad Cost Explorer policy to the deployer. Do not mix current account spend with expected *incremental beta* charges.

## Exact release artifacts (each stage separately approved)

- **Release candidate:** `release/mentor-beta-oct19-rc` was initially composed from PR #83 + all 11 PR #81 auth/frontend/API file changes; verify HEAD and integrated CI. The Docker image and React assets must be built from this exact integrated tree, never PR #83 alone. Documentation-only commits may advance SHA without changing Docker inputs; record exact SHA used.
- **Phase A Foundation:** original private 14 CREATE plan SHA `17a8b6d07667151a78cfb9ec72e003ac7de2f23e3e5b2cdab3d4eb22189474cf`. The plan was made in a different checkout than the RC. Before any APPLY verify exact Terraform source/config/provider/version/input/state match, or create a fresh saved plan and rerun the guard. Its S3 bucket starts empty and CloudFront initially has **NO beta API proxy**.
- **Corrected B1 ALB bridge:** original private 7 CREATE plan SHA `7c3207cbe630731e453e66ee22189018e1724c5e3d40100f5dc196ee9a731d57` with EC2 `ap-southeast-1a` subnet + 1b subnet and `attach_existing_target=false`. The older 8-create SHA beginning `5e8eab66` is **invalid/superseded: NEVER APPLY**.
- **B2 EC2 SG attach:** no plan yet. Only the ORIGINAL EC2 Terraform state can add the new backend-only SG in place. Strict guard: 1 UPDATE, 0 recreate/replace/unrelated drift. Do not alter original SG with 0 inbound.
- **B3 target registration:** no plan yet. After approved EC2 start and private beta container is ready, a **separate** guarded plan adds exactly 1 EC2 target to ALB.
- **B4 API Gateway HTTP API + VPC Link:** no live saved plan; after internal ALB/listener exist, plan JWT issuer/audience/scope `geolife-demo/read` with only two GET routes and an ALB-SG ingress **only from VPC Link SG**. Review plan and request separate APPLY authorization.
- **B5 CloudFront API origin update + frontend:** no live saved plan. Only after healthy target / JWT security pass, review CloudFront UPDATE, upload reviewed S3 frontend assets, configure Cognito managed-login domain/callback and admin-create-only owner/tester account(s), test via public CloudFront HTTPS.

**Before EACH APPLY**, report exact file hash, AWS principal/region, private plan action guard, IAM permissions, dependencies, rollback, and estimated incremental spend. APPLY needs the owner's **explicit stage-specific consent**; budget consent by itself is insufficient.

## P0 runtime test, do not mistake CI for live acceptance

- Dockerfile intentionally defaults `GEOLIFE_PRIVATE_DEMO=1`, but `GEOLIFE_PUBLIC_BETA=1` is an **explicit runtime env-file setting**, not enabled in the default image. Do not build an insecure image with public-beta hardcoded ON; pass reviewed `--env-file` when deploying the separate private-ip:18080 beta container via SSM, **after** the AWS gate.
- Authenticate manually invited owner by Cognito Hosted UI Authorization Code + PKCE over HTTPS; verify invalid/missing JWT 401, wrong tester group/scope and cross-fixture access 403, valid `/v3/beta/me` 200, synthetic Top-3, booking simulation UI, logout/re-login, browser CSP/CORS and CloudFront no-cache on API. Exactly **four synthetic fixture owners** maximum until reviewed code changes; no real GeoLife GPS or historical participant ownership.
- Verify Target Group `healthy` and ALB only reachable through reviewed private path; container restart/reboot, host telemetry, CloudWatch logs, and private error alert. Single EC2 remains a single point of failure.
- If any indispensable IAM or live E2E gate remains blocked, explicitly report **19 Oct owner preview AT RISK**. Never label the site live based only on a PLAN PASS / CI PASS.

## Spending / teardown

Using a deliberately conservative **120-hour planning envelope** for 19–23 Oct, example Singapore `c7i-flex.large` at public third-party `$0.0978/hour` would be about `$11.74` **EC2 alone**; a billed public IPv4 at `$0.005/hour` would be about `$0.60`. This is NOT a verified account quote or complete estimate. Add **Singapore ALB hourly + LCU, EBS, API Gateway and any VPC Link/AZ transfer charges, CloudFront PAYG, S3, Cognito, CloudWatch, ECR, SQS and taxes**; include provisioned-but-idle hours BEFORE the browser site opens. Actual start and close hours on Oct 19/23 are still unspecified: do not silently assume the full 120h or any different clock time as the contractual uptime interval. Obtain private billing review and scenario before APPLY; AWS Budget alerts do not cap charges.

**Owner must assign a teardown operator and exact closure clock time (23 Oct, UTC+7).** Tear down in reviewed dependency order: prevent new beta traffic, remove CloudFront API origin/route, drain/deregister target, stop beta workload, detach only beta SG through original EC2 state, destroy HTTP API/VPC Link and internal ALB/TG/SG, stop original EC2 if permitted and idle, then decide CloudFront/Cognito/S3 destruction separately (do not delete SSM/S2b baseline or original research data). Verify no hourly ALB/VPC/API resources linger and track residual storage costs.

Official references: https://docs.aws.amazon.com/service-authorization/latest/reference/list_elbv2.html ; https://aws.amazon.com/elasticloadbalancing/pricing/ ; https://calculator.aws/ ; https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html .

**This runbook and IAM policy are source-controlled proposals ONLY. No IAM grant, ECR push, Cognito user creation, AWS APPLY, EC2 start or public go-live was executed by this change.**
