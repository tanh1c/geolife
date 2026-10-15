# GeoLife — post-AWS-serving roadmap: evidence v2, candidate tiers, destination recommendations

**Decision checkpoint:** 2026-10-15  
**Branch:** `feature/track-b1-aws-deployment` (PR #73)  
**Status:** planning / experiment proposal. This document does **not** claim any model-policy migration or recommender implementation.

## 0. Current verified state and immediate priority

Reported by operator (local AWS/Modal verification, not independently executed by GitHub CI):

- Track B1 private synthetic demo is running on AWS Singapore EC2 `c7i-flex.large`, through **SSM port forwarding**, with a zero-inbound Security Group and outbound HTTPS/443 only.
- Docker image is pinned to ECR digest `sha256:a8ffb7a871616ecb7000772ca9ccdbc79a8cdaa65a21462c6baafce6421bdef5`.
- SSM is Online; authenticated synthetic `demo_000` browser flow, `/health` and `/demo` work; anonymous protected request is rejected.
- CloudWatch group `/geolife/dev/api` has log events in stream `geolife-demo`. An earlier Git Bash CLI error was **MSYS path conversion** of `/geolife/dev/api`, **not missing IAM permission**; it was resolved by `MSYS_NO_PATHCONV=1`. **Do not widen IAM** based on that incident.
- **AWS baseline → canary 100% → rollback smoke: PASS (operator-reported, synthetic, SSM tunnel).** Baseline: 50/50 HTTP 200, complete-link 50/50, p50/p95/p99 **127/157/179 ms**. Canary 100%: 50/50 HTTP 200, DBSCAN 50/50, **146/273/512 ms**. Rollback: 10/10 HTTP 200, complete-link 10/10, **127/201/234 ms**. Post-rollback `/health` = 200 and `/v2/model-info` reports `baseline` with configured `canary_percent=10` (inactive under baseline mode). Tunnel/client latency included; tests are single-account, not concurrent or real-user workload. 100% canary tail latency was higher in this run, without a general causal performance conclusion. **Still unverified:** actual 90/10 account-sticky split across multiple synthetic accounts.
- GeoLife historical coordinates/private CP1 cache are **not** deployed to AWS. This is *not* a public API or a production user-identity system.
- PR #72 (restricted authenticated serving/demo) merged; PR #73 (AWS/deployment) remains open.
- EC2, EBS, public IPv4, logs and ECR may consume AWS credits while present/running. Preserve local Terraform state; stop compute when not actively testing.

**Next operator checkpoint:** baseline, 100% DBSCAN canary and rollback were demonstrated through SSM. Review the resulting evidence and PR #73 CI/release scope. If a real 10% deployment allocation is required for Checkpoint 2, provision enough synthetic accounts and measure per-account routing under `canary_percent=10` (a single sticky account cannot estimate the split); label this as a separate, pending acceptance gate. Avoid keeping EC2 running merely to re-run existing baseline/100% smoke; when idle, stop it. Only after delivery priorities are cleared begin the private/offline `evidence_strength_v2` investigation. Keep pinned ECR digest, auth DB, secrets, Terraform state and restricted network unchanged. See `docs/deployment/08_aws_ssm_deployment_handoff.md`.

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

## 5. Priority, handoff and explicit non-goals

1. **NOW — close AWS release review:** Baseline latency, DBSCAN at 100% canary, rollback, SSM-only auth and CloudWatch stream have **operator-reported PASS** evidence. Preserve and review it in PR #73; verify CI and secure internal-only scope. **Pending separately:** optional/acceptance-dependent 90/10 account-sticky distribution across many synthetic accounts, which was **not** measured by the one-account 100% canary smoke. Do not claim public deployment, production-grade performance or concurrent-load coverage. Stop EC2 when idle and review billable leftovers. Merge PR #73 only with explicit human approval.
2. **NEXT — research-only score/candidate study:** separate branch/PR; build offline candidate feature table, define missingness and score variants, preserve frozen baseline, run independent temporal robustness checks and write aggregate evaluation.
3. **LATER — destination module:** build versioned internal ranking API and synthetic demonstrations; evaluate future-trip ranking independently of semantic label accuracy.
4. **DEFER — public exposure / SQS / product launch:** follow agreed Track B1 milestones, security/identity/privacy/billing reviews and separate authorization. No blanket IAM grants, public port openings or historical GeoLife release.

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
