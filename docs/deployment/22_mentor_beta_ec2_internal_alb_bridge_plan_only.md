# EC2 + internal ALB + API Gateway VPC Link — MLE runtime reuse

**Status: CODE / OFFLINE TERRAFORM VALIDATE ONLY. NOT PLANNED, NOT APPLIED, NOT LIVE.** This stacked Draft PR depends on PR #82 (foundation + API root), and PR #81 (Cognito/React + synthetic-only backend). It does not grant permission to start the existing EC2, modify network, change IAM, push images or merge PRs.

## Architecture and critical runtime separation

```text
Invite-only browser
  -> CloudFront HTTPS/S3 React (Phase A: PR #82, no API behavior until second approval)
  -> Cognito managed login Authorization Code + PKCE (only admin-created testers)
  -> HTTPS /v3/beta/* CloudFront no-cache/Authorization forwarded
  -> API Gateway HTTP API: JWT issuer/audience + geolife-demo/read scope
  -> AWS VPC Link (SG: outbound only to internal ALB SG on TCP 80)
  -> INTERNAL ALB, 2 selected AZ subnets (SG: inbound only from VPC Link SG)
  -> EC2 instance i-0dfcfa110c0fd8af1 PRIVATE IP:18080 (2nd backend SG: ALB SG only)
  -> separate synthetic-only FastAPI Docker container with GEOLIFE_PUBLIC_BETA=1

Existing EC2 loopback 127.0.0.1:8000 SSM-only API + SQS/worker remains unchanged.
Old EC2 security group STILL has zero inbound; no public EC2 ingress allowed.
```

ALB is `internal=true` with no internet-facing address and a zero-public-ingress SG. It connects only to the app's **separate dedicated port 18080 on the existing instance's private IPv4**; do not change the current SSM-only Docker binding `127.0.0.1:8000`. The ALB health check GET `/health` is only used internally. Existing instance may have a public IPv4 for egress, but the new inbound rule's *source is only the ALB SG*, never `0.0.0.0/0`. This architecture reuses the EC2 host/ECR serving stack. The proposed public `/v3/beta/*` endpoints are currently **synthetic fixture** recommendations, not personalized historical GeoLife records or real ride bookings. No GeoLife raw GPS/cache is mounted in public runtime.

## Terraform state ownership — three separate reviews

**B1: `infra/terraform/mentor_beta_bridge` (new isolated state)**
- READ ONLY prerequisite: exact target instance ID, VPC, and two reviewed subnet IDs in different AZs. The subnets do not have to be assumed from a default VPC; confirm actual CIDR, routing, account, AZ, and available IPv4 space. The ALB `internal=true` designation is key even if reviewed subnets happen to be public-routed.
- CREATE ONLY: internal ALB, ALB security group, EC2 beta-only additional SG, one restricted ALB->backend egress rule, one restricted backend<-ALB ingress rule, HTTP target group, registered EXISTING EC2 instance target, internal HTTP listener (8 resources). No EC2 resource/import/SG mutation here.
- The bridge ALB SG deliberately uses **standalone security-group rules** (no inline ingress). API root owns the one later ALB ingress rule from VPC Link SG. Do not add conflicting inline SG rules in other Terraform roots.
- EC2 is STOPPED now; target state will be unhealthy until later owner-approved EC2 start/container readiness. Terraform creation/plan is NOT a health-check PASS or runtime test.

**B2: existing `infra/terraform` root with ORIGINAL EXISTING STATE**
- Variable `mentor_beta_backend_security_group_id` defaults to `""`, so pre-existing SSM-only mode is unchanged. After B1 is actually applied and the additional backend SG ID is known, operator may prepare a **separate saved PLAN ONLY** with that exact value.
- `vpc_security_group_ids` becomes original SSM-only SG + one additional ALB-only backend SG. The old SG's `ingress=[]` remains literally untouched. **No creation or changes to the existing EC2 state are authorized today.**
- `scripts/mentor_beta_bridge_plan_guard.py --phase ec2-attach --backend-sg <sg-id>` must accept exactly ONE in-place `aws_instance.api` UPDATE adding only that SG, 0 create/destroy/replace and no other instance attributes changed. If original state is unavailable, or Terraform detects old drift/replacement, **STOP**, do not import/reset/reconcile without separate approval.

**B3: existing PR #82 `infra/terraform/mentor_beta_api` root (new isolated state)**
- Its `data.aws_lb.private` and `data.aws_lb_listener.backend` read **the already applied B1 output ARN(s)**; new `aws_vpc_security_group_ingress_rule.alb_from_vpc_link` admits ONLY the VPC Link SG to the ALB SG TCP listener port.
- HTTP API JWT authorizer requires Cognito resource-server scope `geolife-demo/read`. Backend independently validates Cognito access token RS256, issuer, client ID, scope, group and subject-to-unique synthetic fixture mapping from PR #81.
- Root preconditions check account, selected VPC, ALB internal mode, listener/SG and >=2 VPC Link subnet AZs. User-provided VPC Link SG egress already limited to ALB SG port. No direct API path exists to EC2 outside this chain.
- CloudFront Phase A `api_gateway_origin` remains EMPTY unless a separate approved UPDATE plan later adds the API Gateway default hostname and protected `/v3/beta/*` path. None of this is allowed until all gates are met.

## EC2 runtime change AFTER separate AWS and spend approvals

Current deployed baseline uses `docker -p 127.0.0.1:8000:8000`, which is unreachable from ALB by design. Do NOT change it. A second beta container can instead map:

```bash
# Illustration only. DO NOT RUN before approved bridge, approved EC2 SG attach and Cognito provisioning.
# Confirm private IP from read-only EC2 DescribeInstances; no invented IPs.
# Use a digest-pinned image from PR #81 or later with Cognito public-beta routes.
sudo docker run -d --name geolife-mentor-beta --restart unless-stopped \
  -p "${EC2_PRIVATE_IP}:18080:8000" \
  --env-file /opt/geolife-private/mentor-beta.env \
  --read-only --tmpfs /tmp:rw,noexec,nosuid,size=64m \
  "${REVIEWED_IMAGE_DIGEST}"
```

`mentor-beta.env` must have `GEOLIFE_PUBLIC_BETA=1`, `GEOLIFE_PRIVATE_DEMO=1`, issuer/client ID and the **server-private** Cognito `sub -> synthetic fixture` map. Do not mount GeoLife GPS, SQLite historical participant cache, auth credentials of older demos, or `.aws` files. Check whether another container/worker can coexist on the existing instance RAM; this is a single EC2 host, **not high availability**. Never run beta container with `--network host` and `uvicorn --host 0.0.0.0` without a separate approved safety review.

## Operator PLAN-ONLY gates (NO APPLY, IAM or resource mutation)

1. Wait for PR #82 / #81 review and AWS owner release gate. Identify exact existing instance, existing Terraform state, VPC ID, two AZ subnet IDs, ALB routing & price. Ensure no duplicate ALB/TG/SG names. Confirm permissions via read-only AWS only. No assumption from stale docs.
2. In a private checkout, on this exact branch, run targeted `terraform fmt -check`, `init -backend=false`, `validate` for `mentor_beta_bridge`. If the original Terraform root fails fmt due to older S2b files, do not run global fmt or edit unrelated files.
3. For bridge: only after read-only checks, run **saved Terraform PLAN ONLY** with explicit VPC/subnet values, protected state and private plan/JSON. Run `python scripts/mentor_beta_bridge_plan_guard.py --phase bridge --plan-json <PRIVATE-JSON>`. Expected strictly 8 CREATE, 0 UPDATE/DELETE/REPLACE, `apply_approved=false`. Do not claim PLAN PASS until actual operator run.
4. For existing EC2 root: planning the second SG requires the backend SG ID that **does not exist yet**; postpone. After B1 APPLY separately approved, use the ORIGINAL Terraform state and plan with one optional SG; pass strict `ec2-attach` guard. Do not add SG using ad hoc CLI, outside state or an imported duplicate.
5. API root Phase B PLAN must use real reviewed internal ALB/listener outputs after B1; it is NOT READY now. Must separately guard its expected creates and verify no public SG rule or unintended routes.
6. Before any future APPLY: account-spend review, Singapore per-hour ALB/LCU, EC2 compute+EBS+public IPv4, API Gateway, VPC link, CloudFront PAYG/S3/Cognito costs; choose **4h / 48h / 30d** demo exposure and teardown deadline. Budget alerts do not hard-cap cost. Validate scoped IAM actions rather than adding `*` privileges.
7. After individual owner-authorized APPLYs: bring up EC2 only in approved window, SSM deploy digest-pinned beta image at PRIVATE IP:18080, check `/health` via ALB TG, then API JWT 401/403 and 2-tester isolation, CloudFront real browser Cognito PKCE E2E, synthetic Top-3/booking and monitoring. Verify EC2 port 18080 cannot be accessed directly from Internet. No original participant data in AWS.

**Teardown:** disable CloudFront protected origin, stop/remove beta container, detach additional SG via separately reviewed existing EC2 Terraform in-place plan, delete API/VPC Link and ALB bridge roots in dependency order, destroy Cognito/S3/CloudFront only if approved and after backups/protected state checks. Do not destroy the original SSM EC2/ECR/S2b state. ALB has hourly costs even while EC2 stopped.

Official technical references: https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-private.html , https://docs.aws.amazon.com/elasticloadbalancing/latest/application/application-load-balancers.html , https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/lb_target_group_attachment , https://aws.amazon.com/elasticloadbalancing/pricing/ .

**Acceptance now: implementation + offline Terraform validation only. No real AWS plan, no cost approval, no APPLY, no live authentication, no real GeoLife web access.**