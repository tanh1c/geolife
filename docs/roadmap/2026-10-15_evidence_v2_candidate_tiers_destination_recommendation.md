# GeoLife — post-AWS-serving roadmap: evidence v2, candidate tiers, destination recommendations

**Decision checkpoint:** 2026-10-15  
**Source lineage:** originally prepared on `feature/track-b1-aws-deployment` (PR #73, merged into `main` on 2026-10-15).  
**Status (2026-10-15):** living priority roadmap. AWS restricted SSM-only demo review/PR #73 is merged; Stage 10a–10l Evidence v2 offline audit concluded without production score replacement (PR #74 still subject to separate review). Destination Recommendation is the next **product experiment**, while the mentor-requested application-user identity/security work is a **parallel design + synthetic-only PoC** and a gate for any future public/multi-user exposure. No Cognito resources, OAuth/OIDC login, public API, external user linking, or new deployment are claimed.

## 0. Current verified state and immediate priority

Reported by operator (local AWS/Modal verification, not independently executed by GitHub CI):

- Track B1 private synthetic demo is running on AWS Singapore EC2 `c7i-flex.large`, through **SSM port forwarding**, with a zero-inbound Security Group and outbound HTTPS/443 only.
- Docker image is pinned to ECR digest `sha256:a8ffb7a871616ecb7000772ca9ccdbc79a8cdaa65a21462c6baafce6421bdef5`.
- SSM is Online; authenticated synthetic `demo_000` browser flow, `/health` and `/demo` work; anonymous protected request is rejected.
- CloudWatch group `/geolife/dev/api` has log events in stream `geolife-demo`. An earlier Git Bash CLI error was **MSYS path conversion** of `/geolife/dev/api`, **not missing IAM permission**; it was resolved by `MSYS_NO_PATHCONV=1`. **Do not widen IAM** based on that incident.
- **AWS baseline → canary 100% → rollback smoke: PASS (operator-reported, synthetic, SSM tunnel).** Baseline: 50/50 HTTP 200, complete-link 50/50, p50/p95/p99 **127/157/179 ms**. Canary 100%: 50/50 HTTP 200, DBSCAN 50/50, **146/273/512 ms**. Rollback: 10/10 HTTP 200, complete-link 10/10, **127/201/234 ms**. Post-rollback `/health` = 200 and `/v2/model-info` reports `baseline` with configured `canary_percent=10` (inactive under baseline mode). Tunnel/client latency included; tests are single-account, not concurrent or real-user workload. 100% canary tail latency was higher in this run, without a general causal performance conclusion. **Still unverified:** actual 90/10 account-sticky split across multiple synthetic accounts.
- GeoLife historical coordinates/private CP1 cache are **not** deployed to AWS. This is *not* a public API or a production user-identity system.
- PR #72 and PR #73 (restricted authenticated serving plus AWS sync-demo source/handoff) merged into `main`; PR #74 (research audit) remains separate and is not a production score migration.
- EC2, EBS, public IPv4, logs and ECR may consume AWS credits while present/running. Preserve local Terraform state; stop compute when not actively testing.

**Updated operator checkpoint:** PR #73 code/handoff has been reviewed and merged; no extra AWS apply or EC2 restart was performed by merging. Stage10a–10l was completed offline (the proposed scalar v2 was **not** promoted). Do not redo completed baseline/100% canary/rollback tests unnecessarily. The next product experiment is a **private, synthetic-first destination recommender** with explainable Top-K output. In parallel, review application user identity (OIDC/OAuth/Cognito synthetic test accounts) and layered API security **on paper and in isolated local/test resources only**, before any decision to expose a public endpoint. AWS EC2 shutdown and billable-resource state still require explicit live verification. Preserve ECR digest, auth DB, secrets, Terraform state and zero-inbound infrastructure. See `docs/deployment/08_aws_ssm_deployment_handoff.md`.

## 1. Decisions frozen — do not silently change

1. **CP1 + CP2-v2 baseline remains frozen:** CP1 cleaning/stays; CP2 per-stay IANA local timezone + complete-link 200 m, existing HOME/OFFICE gates, abstention. Real-cache aggregate reference: 5,821 stays, 136 stay users, **27 HOME**, **16 OFFICE**. No global threshold adjustment and no reclassification in the production response merely due to a new score.
2. Existing `evidence_strength` is `(relevant_dwell_share + share_margin + min(relevant_dates / 5, 1)) / 3`, computed **only for emitted results** after the emission gates. API v1 calls it `confidence` (legacy); v2 and authenticated demo correctly call it `evidence_score`. It is a heuristic evidence index, **not a calibrated correctness probability**. Do not show as `80% probability that this is HOME/WORK`.
3. Keep `OTHER_RECURRING` distinct from semantically verified POIs, HOME or OFFICE. A recurring secondary anchor, repeated route, mobile/shift-like work pattern or comparator agreement **does not alone prove OFFICE**.
4. No historical per-user GPS or inferred HOME/OFFICE coordinates to AWS or a public-facing endpoint without explicit privacy/license, identity, access-control and threat-model approval. SSM-only demo retains zero inbound; no opening port 8000/80/443 as a shortcut.
5. Stage 08a–08c candidates remain experimental tiers and must never silently inflate the frozen 27/16 counts.

## 2. Proposed offline experiment: `evidence_strength_v2` (NOT adopted)

**Motivation:** old score weights dwell share, top-2 margin and support dates equally without calibration. It penalizes dense/mobile users when many locations dilute share/margin and ignores opportunity coverage, held-out identity persistence, structured GPS missingness and external corroboration.

**Do NOT immediately replace production formula or add guessed percent confidence.** Build an offline `v1 vs v2` evaluation first. Candidate input must be generated *before* scoring: score changes by themselves cannot recover abstained near-label cases.

**Candidate explanatory features (separately reported; define missing semantics):**

- `C`: relative top-vs-runner-up concentration, e.g. `top_share / (top_share + runner_up_share)`; track support/exposure and the no-runner-up case explicitly (a solitary top result is not automatically reliable).
- `O`: relevant-date opportunity coverage: number of opportunity dates supporting the **same** candidate divided by observed opportunity dates for HOME or OFFICE; require independent evidence, minimum support, and record zero/unknown denominator.
- `R`: same-*candidate-identity* robustness across pre-declared dropout/split/held-out tests. Require no leakage from held-out period to the predictor used on that period. If tests are not computable on a short new-GPS request, return `unavailable` with reason; do **not** fill with 1.0.
- `H`: support saturation `min(candidate_support_days / 5, 1)`, plus explicit exposure count/missingness so that 2/2 observations is not confused with 20/20.

**Candidate hypothesis, *not* a frozen formula:** `E_v2 = (C * O * R)^(1/3) * sqrt(H)` when all inputs are valid. The 1/3, square-root, denominator choices and equal importance are unvalidated design choices. Compare against simpler alternatives and a feature-only/tier-based decision before selecting any formula. Do **not** treat `E_v2` as a probability or use score cutoffs for promotion until justified.

**Evaluation gates on private existing stays/artifacts (no raw PLT rescan unless upstream integrity requires one):**

- Match the original 27 HOME / 16 OFFICE emission decisions exactly in baseline mode; preserve v1 response parity.
- Compare score ranks/distributions by HOME vs OFFICE and SPARSE / MEDIUM / DENSE observation regimes, opportunity counts and missingness.
- Check whether stable *same-location* candidates tend to rank above unstable candidates under predeclared split/holdout/dropout checks. Avoid validating the score on the *same* perturbations used to construct `R`: use independent temporal holdouts or clearly label in-sample diagnostics.
- Robustness of the ranking across nearby reasonable score definitions and score missingness/coverage for short on-request GPS.
- Report abstentions, candidate-tier coverage and failure modes; no invented accuracy, Brier score, calibration, ROC-AUC, F1 or percent-correct without independently verified HOME/OFFICE labels.

**Deliverable proposed:** standalone analysis/code + regression tests + aggregate comparison report under `docs/eda/`; `evidence_score_v2` must be opt-in/versioned and separated from the frozen model until reviewed.


### Stage 10 audit outcome (added 2026-10-15; supersedes the proposed experiment above)

Stage 10a–10l **finished as offline research**; the proposed scalar Evidence v2 was **not deployed**. For the Stage08 tiered 55 hypotheses, 21/55 had all original v2 components; 34/55 lacked an *eligible* runner-up, a real structural feature-availability limitation. At the fixed 70/30 TRAIN/FUTURE study, 44 TRAIN anchors emitted, 43 were FUTURE time-observable, 31 uniquely spatially observable, 25 saw the same selected TRAIN anchor and 6 an alternative TRAIN anchor; 12 time-observable remained spatially unresolved. Conditional 25/31 observed recurrence **is not semantic accuracy**. The strict TRAIN-only head-to-head had 11/44 v2-scorable and only 9 FUTURE spatially observable v2-scorable (7 recurrence, 2 other-anchor); the predeclared ranking-concordance comparison was not estimable.

Decision: frozen CP2 complete-link 200m, HOME27/OFFICE16 and existing v1 score remain unchanged; v1 is a heuristic index, not a probability. Do **not** fill missing C, add unsupported percent-confidence badges, relax emission gates, or deploy v2. Full analysis: [Stage10 decision record in PR #74](https://github.com/tanh1c/geolife/blob/feature/evidence-v2-offline-audit/docs/eda/45_evidence_v2_final_decision.md) (subject to PR #74 review/merge).

## 3. Candidate tiers (offline / opt-in, not production labels)

Avoid assigning arbitrary 90/70/55% probabilities to a tier. Output `label_hypothesis`, `tier`, `evidence_components`, `source_policy`, `limitations`, and `calibrated_probability: null` by default.

| Source / tested group | Research result | Proposed status |
| --- | ---: | --- |
| Frozen production HOME | 27 | `HOME_CORE`, unchanged |
| Frozen production OFFICE | 16 | `OFFICE_CORE`, unchanged |
| Stage 08a independently corroborated dense HOME | +5 | `HOME_PROBABLE` (not CORE) |
| Stage 08c SPARSE HOME 2-of-2 opportunity + recurrence | +4 | `HOME_SPARSE_CANDIDATE` |
| Stage 08c DENSE OFFICE near miss: relative dominance + dropout + identity corroboration | +3 from 9 audited near misses | `OFFICE_ROBUST_CANDIDATE` |
| Stage 03a/06/07 factorized mobile/multi-anchor/route patterns | descriptive cohorts, e.g. 23 mobility-complexity users | `RECURRING_ANCHOR` / `ROUTE_REGION`, **not OFFICE** |

Research tiered coverage could be HOME **36**, OFFICE **19**, *not production emission counts*. The three OFFICE cases do **not** authorize relaxing all nine near misses. Most Stage-07j near misses failed independent persistence tests.

**Next research acceptance:** repeat Stage 08c robustness for 4 sparse HOME + 3 robust OFFICE on temporally separated or structured missingness tests, preserve no-collision safeguards and audit upstream stay/location namespace mismatches before any opt-in serving candidate response.

Sources: `docs/eda/41_home_coverage_expansion.md`, `docs/eda/42_exposure_bias_audit.md`, `docs/eda/43_exposure_aware_policy.md`, `docs/eda/34_near_miss_office_audit.md`, `docs/eda/26_factorized_work_profiles.md`, `docs/learning-journal-vi.md`.

## 4. Long-term product direction: private destination recommendation module

**Distinct questions:**
- Semantic inference: *which observed anchor resembles HOME/OFFICE, with abstention?*
- Destination recommendation: *given current location, local time, weekday and opted-in personal trip/routine history, where might this user want to go next?*

Proposed integration:

```text
Consenting app user / mobile UI
       -> App backend (real identity and permissions)
       -> Destination recommendation API
          ├─ Frozen CP2 semantic evidence + separately tagged candidates
          ├─ Stage 06 OD transitions / local departure-time routines
          ├─ Stage 07 multi-anchor / route / shifted-schedule representation
          └─ Contextual ranking (current origin, time, weekday, recency, feedback)
       -> Top-K suggestions + reason + user confirmation
```

Example: at 07:00 on a weekday, suggest a frequently chosen destination (possibly user-confirmed work address) **only** if origin/time/routine context supports it; never infer `OFFICE` from the clock alone. Distinguish `suggested destination` from `verified office`.

**First MVP:** local/private synthetic fixture, user-confirmed saved places, Top-3 destination ranking; compare chronological held-out Hit@K/Recall@K and no-suggestion rate against a simple frequency/recency baseline. No ground-truth HOME/OFFICE accuracy claim from GeoLife. Candidate tiers may help ranking but must not be presented as verified labels. No live public app integration or identity linking in this phase.

**Future networking (not deployed):** keep EC2/service private, expose authenticated HTTPS through an audited app backend/API Gateway plus private integration (e.g. VPC Link + internal load balancer), with scoped service auth, consent, deletion, audit, rate limiting, secrets, privacy review, and cost assessment. Do not turn the SSM-only EC2 into a public endpoint by adding inbound SG rules.


## 4A. User-facing evidence and rank: presentation policy (mentor discussion, proposed)

**Goal:** do not mislead a user with a numeric evidence index like `0.87` or a badge `87% confidence`. A numeric CP2 v1 score is a heuristic *after* a HOME/OFFICE anchor passes baseline emission gates, not a calibrated probability. **Hiding the score alone does not improve model validity**: ranking or qualitative levels can also mislead unless their meaning is bounded.

- **Suggested UI labels (not semantic ground truth):** `Có thể là nhà`, `Có thể là nơi làm việc`, `Địa điểm thường ghé`, `Chưa đủ dữ liệu để xác định`; user-confirmed saved places must be explicitly distinguished from inferred labels. Respect current abstention: if HOME/OFFICE abstains, do not fill it from `OTHER_RECURRING`.
- **Show reasons rather than fake probabilities:** observations in relevant local time window, date support, repeat occurrences, whether there are multiple competing eligible locations, unavailable/partial data. Avoid exposing precise personal coordinates, raw histories, or unverified labels without authorization and consent.
- **Ranking belongs to the *destination recommender***: Top-1/Top-2/Top-3 means ordering by predeclared contextual prediction features (frequency, recency, relevant time, origin, destination transitions, explicit user feedback); it does **not** mean the first location is truly HOME, OFFICE or an 80% likely next destination. Compare chronological held-out Hit@K/Recall@K and no-suggestion rates to a simple baseline before shipping. Different semantic categories cannot be casually compared on an uncalibrated CP2 evidence-score scale.
- **Qualitative tiers only if rule and meaning are documented:** e.g. `quan sát nhiều lần` is a count-based descriptive label, **not** `độ tin cậy cao` or `xác suất đúng cao`; missing data and singleton-eligible cases require explicit `unknown` / `insufficient`, not silent `high`.
- **Compatibility boundary:** keep existing internal v1/v2 CP2 scores and API parity unchanged in this roadmap PR. A future versioned **public-facing response DTO** may omit raw `evidence_score` / legacy `confidence` entirely, rather than merely hiding a value that remains in browser network responses. Review API contracts, auth and regression tests before changing JSON fields.
- **UI acceptance:** on synthetic example, a user can tell observed vs inferred vs user-confirmed vs unavailable; no `% correct`, numeric evidence badge, unsupported confidence ranking, cross-user data leaks, or HOME/OFFICE fabricated from abstain.

## 4B. Mentor feedback — application identity, OAuth/OIDC, private/public network and layered API security

**Status: prospective design / research PoC, NOT deployed.** The existing demo uses server-provisioned `demo_000`-style accounts, password-hashed records and revocable short-lived bearer sessions in private SQLite; server-side `account_id → dataset_user_id` mapping is for a **restricted historical research demonstration only**. It does **not** establish that the account holder is an original GeoLife research participant. AWS IAM user/groups/EC2 instance roles control **infrastructure operators**, not end-user login.

### Correct technical vocabulary

| Mentor shorthand | Precise interpretation / needed boundary |
| --- | --- |
| “Cơ chế auth mới” | Separate **Authentication (AuthN: who logged in)** from **Authorization (AuthZ: what this principal may access)**; need both, not just a login button. |
| “Thiếu step OAuth để biết user ID là ai” | Use **OpenID Connect (OIDC)** for identity on top of **OAuth 2.0 Authorization Code + PKCE** for the interactive app. An authenticated `iss + sub` identifies a user principal at that issuer, **not** ownership of GeoLife `user_id`. OAuth scopes authorize API operations; OIDC ID token provides identity claims. |
| “AWS Cognito test user” | Trial **Amazon Cognito User Pool** test accounts with Cognito domain/managed login and a public test app client. User Pool provides tokens; **Identity Pool/IAM credentials are NOT necessary** for this app-user identity PoC. A Cognito User Pool is different from AWS operator IAM identity. |
| “Private network / public nhiều layer bảo mật” | **Private endpoint** (reachable from designated VPC/VPN/SSM paths only) and **public HTTPS API with a private backend integration** are distinct patterns. Network/SG/firewall rules control reachability; authentication controls principal identity; per-user authorization controls data. None substitutes for the others. |
| “Secure API” | HTTPS/TLS, WAF/rate and size limits, token validation, route scopes, per-user resource authorization, least privilege, audit/retention, key management, monitoring, abuse tests and private-data access policy. |

### Proposed identity flow — synthetic only at first

```text
Web user (synthetic test account)
  -> Cognito User Pool managed login / hosted sign-in
  -> OAuth 2.0 authorization code + PKCE, OIDC
  -> valid tokens / optional BFF secure server session
  -> API gateway/authorized backend validates access token
  -> issuer + subject (iss, sub) mapped to internal app_user_id
  -> AuthZ checks scope + ownership/consent for each requested resource
  -> private recommender/inference backend returns only authorized synthetic data
```

- For web browser, prefer Cognito **managed login + Authorization Code/PKCE**. Compare a **Backend-for-Frontend (BFF)** using `Secure`, `HttpOnly`, `SameSite` session cookies and CSRF controls versus a SPA with carefully managed tokens; do not place long-lived access/refresh tokens in browser `localStorage` as an architectural default. Use `state` and `nonce` where appropriate and registered HTTPS redirect/logout URLs; minimize scopes and token lifetimes.
- API expects a valid **access token** (not an ID token used interchangeably); validate JWT signature/JWKS, issuer, client/audience, expiry, `token_use=access` in Cognito-aware code, and required scopes/roles. If using API Gateway HTTP API JWT authorizer, require route scopes and implement backend AuthZ: built-in JWT authorizer cannot be assumed to distinguish ID and access tokens in every configuration. Consider revocation window/short access-token TTL.
- Internal resource ownership must be server-side, e.g. `(issuer, sub) → app_user_id → owned/consented resources`; ignore user-supplied `dataset_user_id` for access decisions. **Cognito authentication never proves a new account owns GeoLife pseudonymous ID `000`**. Keep historical GeoLife cache inaccessible to public test accounts. User-provided GPS data requires consent, purpose limitation and retention/deletion plan.
- OAuth/OIDC proof of concept must prove negative cases: no/expired/tampered token => 401, valid token without privilege => 403, incorrect issuer/audience/client and wrong scope denied, test account A cannot read B’s objects (including changing URL/body fields), logout/revocation behavior documented, and secrets/tokens/GPS not included in logs. `401` vs `403` should have stable privacy-safe responses.

### Network architectures — research options, not a current AWS change

**Option A — keep internal demo private (current):**
```text
Authorized operator -> AWS SSM encrypted port-forward
  -> EC2 loopback FastAPI Docker (SG inbound = 0)
```
Do not open EC2 ports, change Security Groups or send historical GPS to AWS.

**Option B — future public web app with private application backend (requires separate approval):**
```text
User browser --HTTPS/TLS--> public edge / API Gateway (JWT authorizer,
  throttling; WAF if supported/configured) --private VPC Link integration-->
private ALB/ECS/EC2 app --service IAM/auth checks--> private data
Cognito User Pool managed sign-in/OIDC is a separate auth endpoint
Backend security groups allow only necessary internal paths
```
A **public API with private VPC integration** is reachable from the internet at the *public gateway*; it is **not** a “Private API Gateway endpoint.” A truly private API Gateway REST endpoint is reachable using VPC endpoint/network paths only. Select one based on actual product exposure and operational cost, never by adding EC2 SG inbound rules as a shortcut.

**Layers/checkpoints:** identity (Cognito/OIDC); application authorization with `iss + sub` and resource ownership; HTTPS/TLS; optional AWS WAF/managed rules and abuse/rate controls, supported API Gateway rate/burst throttling; VPC/subnet/security groups and least-privilege IAM; timeouts/body-byte & chunked caps, safe CORS/CSRF if browser cookies, sanitized logs/metrics, CloudWatch monitoring and short sensitive-data retention. Verify exact service support and **AWS cost** of Cognito MAUs, API Gateway, ALB/VPC Link, WAF, certificates/domains, private endpoints and storage before enabling anything.

### Prioritized security deliverables and acceptance gates

1. **P0 design/spec only (in parallel with private recommender MVP):** threat model of inferred HOME/OFFICE and GPS, distinction `app_user_id` vs pseudonymous research ID, access matrix (account/test/owner/admin), network topology A vs B, token/session lifecycle, public/no-public boundary and cost estimate. Produce sequence diagram, API auth contract and user-consent/data-retention policy; no AWS apply.
2. **P1 local/sandbox Cognito synthetic identity PoC (requires budget approval for new cloud assets):** manually or IaC-provisioned isolated User Pool and minimal test app client, managed login + PKCE/OIDC, test account A/B, one protected synthetic-only endpoint, `iss/sub` mapping, scope + object-level authorization, and 401/403/IDOR regression tests; never enable self-service access to historical GeoLife identities. Keep restricted EC2 SG zero inbound.
3. **P2 future public ingress/security review:** explicit user approval and privacy/legal consent check, approved network architecture, TLS, WAF/rate/body limits, backend private integration, secret storage/rotation, audit and CloudWatch alerts, multi-account tests and cost/teardown. External penetration/security review before any real-user public launch.
4. **Non-goals in this update:** no production Cognito integration, no IAM permission widening, no new public API, no Terraform apply, no real-user GPS storage, no switch to Evidence v2, no public GeoLife participant lookup.

**Official AWS references:** [Cognito managed login](https://docs.aws.amazon.com/cognito/latest/developerguide/cognito-user-pools-managed-login.html), [OAuth grants and PKCE](https://docs.aws.amazon.com/cognito/latest/developerguide/federation-endpoints-oauth-grants.html), [JWT verifying](https://docs.aws.amazon.com/cognito/latest/developerguide/amazon-cognito-user-pools-using-tokens-verifying-a-jwt.html), [API Gateway JWT authorizers](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-jwt-authorizer.html), [HTTP API private VPC integration](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-private.html), [Private REST API](https://docs.aws.amazon.com/apigateway/latest/developerguide/apigateway-private-apis.html), [API Gateway throttling](https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-throttling.html).

## 5. Priority, handoff and explicit non-goals (updated 2026-10-15, after PR #73 merge and Stage10 closure)

1. **DONE — AWS restricted sync demo code/handoff and release review:** PR #73 merged into `main` as `cb4fe7ca`. Synthetic-only SSM demo, 100% canary and rollback passed as operator-reported evidence. This does **not** expose any public API or authorize historical GPS transfer. **Remaining operational check**: verify EC2/EBS/public IPv4/ECR/CloudWatch live resources and AWS cost after shutdown; optional multi-account 90/10 allocation only if required for demo acceptance.
2. **DONE — Evidence v2 offline study Stage10a–10l:** no v2 production migration, no calibrated semantic correctness and no evidence of v2 outperforming v1 on representative cohort. Stage10 decision documented in PR #74, still requiring separate review/merge. Keep frozen v1 and abstentions; do not promote research tiers.
3. **NEXT — destination recommendation MVP, internal/private and synthetic-first:** user-consented or synthetic saved places, context-based Top-3 suggestions, *recommender* ranking reasons (not HOME/OFFICE confidence), chronological Hit@K/Recall@K and no-suggestion versus frequency/recency. UI hides numeric evidence index and displays descriptive observed/inferred/unavailable states. Do not publish individual GeoLife trajectories or conflate `OTHER_RECURRING` with verified destinations.
4. **PARALLEL DESIGN — mentor-requested identity + API security:** document AuthN/AuthZ split and `iss/sub` app principal mapping, OIDC OAuth Code+PKCE, Cognito **User Pool test users**, network A (SSM private) vs B (public HTTPS edge → private backend), WAF/firewall/rate/byte limits, data ownership and privacy. Build synthetic Cognito/login/API PoC only with separate budget and resource approval. **Not a dependency for the offline recommender test**, but mandatory review before any real-user/multi-tenant web app or public exposure.
5. **LATER / SEPARATE APPROVAL — public API, async SQS, monitoring expansion and larger infrastructure:** follow explicit track and budget/security sign-off. SQS pointer-only, encrypted TTL storage and worker are not implicitly started by this roadmap; public networking never means opening EC2 8000/80/443 directly.
6. **DEFER — EDA coverage/strict gate sensitivity:** separate offline research issue/PR after destination MVP/priority delivery; cross-file trajectory assembly and eligibility waterfall before changing CP1/CP2 thresholds; independent semantic truth required for accuracy claims.

**Reproduction reference only — baseline benchmark already completed (Windows PowerShell):**

```powershell
$env:AWS_PROFILE = "geolife-terraform"
$env:AWS_REGION = "ap-southeast-1"
aws sts get-caller-identity
$EC2_ID = terraform -chdir=infra/terraform output -raw ec2_instance_id
aws ssm start-session --target $EC2_ID --document-name AWS-StartPortForwardingSession --parameters '{"portNumber":["8000"],"localPortNumber":["18000"]}'
```

Keep that terminal open; in a **second** PowerShell terminal at repo root, only when `http://127.0.0.1:18000/health` returns 200, run:

```powershell
python scripts/benchmark_authenticated_demo.py --url http://127.0.0.1:18000 --account demo_000 --requests 50 --warmup 5
```

**Historical benchmark instructions (already completed):** Password is entered interactively; share only sanitized benchmark JSON. One sticky synthetic account samples one model, not rollout-wide 10% traffic. The baseline/100%-canary/rollback tests above are complete; do not repeat them or edit the private `runtime.env` unless conducting a new, explicitly scoped acceptance test.
