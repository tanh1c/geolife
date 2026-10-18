# GeoLife invite-only public demo — Phase 1: safe Cognito API foundation

Status: Code review only; NOT DEPLOYED. No AWS changes, Cognito users, EC2 starts or ingress approvals.

Architecture target: CloudFront/S3 HTTPS React -> Cognito User Pool managed login (OAuth Authorization Code + PKCE) -> API Gateway JWT authorizer (required custom scope) -> private VPC Link backend. Before provisioning, approve exact costs, SG routing, API throttling, TLS, headers, budget and cleanup.

Only administrator-created Cognito mentor/tester accounts. Disable self-service signup. Require group geolife-demo-testers and custom scope geolife-demo/read. Browser is a PUBLIC app client, no client secret. Use Cognito access token, not ID token, for API. JWT authorizer alone cannot guarantee token_use; backend separately verifies RS256, JWKS, issuer, client_id, exp, token_use=access, group and scope.

Environment variables (all off until approved):

  GEOLIFE_PUBLIC_BETA=1
  GEOLIFE_PRIVATE_DEMO=1
  GEOLIFE_COGNITO_REGION=ap-southeast-1
  GEOLIFE_COGNITO_USER_POOL_ID=<approved-pool>
  GEOLIFE_COGNITO_CLIENT_ID=<public-client-id>
  GEOLIFE_COGNITO_TESTER_GROUP=geolife-demo-testers
  GEOLIFE_COGNITO_SCOPE=geolife-demo/read
  GEOLIFE_BETA_SUBJECT_FIXTURE_MAP=<protected-json-sub-to-unique-demo_000..demo_003>

Last variable is server-only and must NEVER be committed or sent to browser. Subjects must map 1:1 to synthetic fixture owners. An OIDC subject does NOT prove ownership of a GeoLife research participant.

Public runtime allows ONLY GET /health, GET /v3/beta/me and GET /v3/beta/destination-suggestions. Existing v1/v2, legacy demo login, real GeoLife cache endpoint, jobs and metrics are blocked by fail-closed middleware. No original participant ID or coordinates in these beta responses. Do not host the old SQLite UI or mount historical cache on the public backend.

Current scope is ONLY backend API foundation and synthetic JWT tests. Next PR/task: SPA Cognito Code+PKCE login, strict state check, tokens kept in memory rather than localStorage, logout and short expiry handling; then wire to the existing React UI without using v2 SQLite routes. Real GPS ingestion requires a separate privacy/design review.

Deployment gate: Terraform plan and budget review, owner AWS resource approval, verify no EC2 public inbound, end-to-end HTTPS + JWT tests, 401/403 cross-user isolation, protected logs, no sign-up, test-account-only access, browser E2E and actual teardown. Keep main and EC2 unchanged until explicit approval.
## React integration (review branch)

Public beta builds with VITE_PUBLIC_BETA=1. Login uses Cognito managed login Authorization Code + PKCE S256 with one-time sessionStorage verifier/state (10-minute expiry); access tokens are kept only in React memory and never in localStorage. On callback the app strips code/state from URL and calls GET /v3/beta/me. Signed token verification and fixture authorization remain server-side. The original React UI appears only after Cognito login. On logout, clear React state and redirect to Cognito hosted logout. JWT revocation is not immediate and tokens may remain usable until expiry; require short lifetimes. Use registered exact callback/logout URL and validate token expiry via backend. No OAuth app client secret in browser.

Frontend PUBLIC build env variables: VITE_PUBLIC_BETA=1, VITE_COGNITO_DOMAIN=https://<approved-cognito-domain>, VITE_COGNITO_CLIENT_ID=<public-client-id>, VITE_COGNITO_SCOPE='openid geolife-demo/read', VITE_COGNITO_REDIRECT_URI=https://<approved-website>/ . These are public build config values, never credentials. Public CloudFront /v3/beta/* must forward Authorization to API; hosted Cognito OAuth token endpoint must support browser CORS; secure HTTPS required. Do not enable legacy /v2 proxy in public edge.

Browser functional acceptance (NOT RUN): invitation → managed-login → callback state/code verifier → /v3/beta/me → existing frontend Top-3 → simulated booking → logout; wrong user/group and expired token denied. Preserve existing internal SQLite demo path when VITE_PUBLIC_BETA is unset. Branding/right-to-distribute review remains separate.
