# Stage 10 — Evidence v2 offline audit (research-only, pre-validation)

**Status:** implementation scaffold with synthetic unit tests, **no GeoLife private-data evaluation yet**, no change to frozen CP1/CP2, API, IAM, Docker or AWS. This branch is separate from the AWS deployment PR #73.

## Research question

Can an explicit evidence-v2 candidate score better reflect variation in observation opportunity, dense/mobile concentration and candidate-identity stability, **without treating a heuristic score as a calibrated correctness probability**?

The frozen production emission remains **HOME 27 / OFFICE 16**. Stage 08a/08c tiered candidates are *not* silently promoted. Candidate selection must occur **before** v2 scoring, because CP2 v1 score is only assigned to already-emitted HOME/OFFICE.

## Input contract (private trusted table, one row per user/label/location)

`analysis/10_evidence_v2_experiment.py` requires a CSV with these columns:

| Column | Definition |
| --- | --- |
| `user_id`, `label`, `location_id` | Same-namespace CP2-v2 candidate identity; `label` is HOME or OFFICE *hypothesis*, not ground truth |
| `tier` | Explicit externally audited tier e.g. HOME_CORE, OFFICE_CORE, HOME_PROBABLE, HOME_SPARSE_CANDIDATE, OFFICE_ROBUST_CANDIDATE |
| `exposure_regime` | Stage 08b HOME/OFFICE-specific ZERO / SPARSE / MEDIUM / DENSE; preserve source and policy |
| `top_share` | Relevant time-window dwell share for the top candidate, in [0,1] |
| `runner_up_share` | Comparable top-2 share from *same ranking eligible set and label*; null if no known peer; do **not** encode an unknown runner-up as zero |
| `candidate_support_days` | Distinct relevant dates supporting the **same candidate** (integer), not total stay dates |
| `opportunity_days` | Days with an actual observed opportunity in that label-specific local behavior window, using the frozen Stage 08b definition; **not** the calendar span |
| `identity_stability` | [0,1] proportion retaining the **same candidate location** in predeclared robustness trials **not reused as the evaluation holdout**; missing if not measurable |

**Do not create row-level candidate tiers by tuning E2 thresholds.** Reuse existing Stage 08a/08c provenance, conflict gates, and Stage 05/07j robustness evidence. In particular, a mobile/route-only representation is not sufficient to invent an OFFICE label.

The input CSV remains **private**, outside Git and the Docker/ECR image, and must not include raw GPS or precise HOME/OFFICE coordinates. Work inside a trusted offline/Modal environment that already has the CP1/08b/08c caches; do not copy private user-level data to GitHub or AWS. The tool does not download or create private data.

## Hypothesis, not calibrated confidence

```text
C = top_share / (top_share + runner_up_share)
O = candidate_support_days / opportunity_days
R = identity_stability
H = min(candidate_support_days / 5, 1)
E_v2 = (C * O * R)^(1/3) * sqrt(H)
```

No score is emitted if any essential component is missing/invalid. A missing runner-up is treated as unknown, not as an automatic 100% top-1 victory. A 2-of-2 sparse observation has `O=1` but still has a lower `H=0.4`. `R=0` is a valid measured negative result, while `R=null` is unavailable.

This formula is an **unvalidated comparison hypothesis**, not an adopted replacement; the choices of combination, opportunity measure, five-day saturation and equal factors are not supported by HOME/OFFICE truth labels. Do not display a score as "75% confidence" or infer calibrated probabilities from its value.

The output is **aggregate JSON** grouped by label / tier / exposure regime. Score summaries for fewer than five rows are suppressed by default. No user ID or coordinates are printed. If individual groups are themselves considered sensitive, distribute only a further reviewed/coarsened aggregate.

## Quick local tests (Windows PowerShell)

From the root of the **separate research branch**:

```powershell
git switch feature/evidence-v2-offline-audit
python -m pytest -q tests/test_evidence_v2_experiment.py
```

The tests use generated synthetic rows, not GeoLife/Modal cache. The script can be smoke-tested with a separately prepared **private** CSV:

```powershell
python analysis/10_evidence_v2_experiment.py --input-csv "C:\\private-geolife\\candidate_features.csv"
```

Avoid printing or committing the input CSV, private user rows, any `auth.sqlite3`, AWS credentials, or `terraform.tfstate`. No AWS EC2 instance needs to be running for this offline stage.

## Acceptance plan (not complete)

1. **Private feature lineage adapter:** map frozen CP2 and Stage 08b opportunity diagnostics, Stage 08a HOME_PROBABLE, Stage 08c sparse/dense candidate outputs, Stage 05/07j identity robustness to the above contract. Validate candidate identity and time-window semantics. No real user rows committed. Do not silently fabricate `runner_up_share` or `identity_stability`.
2. **Parity gate:** original production CP1/CP2 label emission and source `evidence_strength` values are unchanged; reference HOME 27/OFFICE 16 (5,821 stays), separate opt-in candidate-tier counts HOME 36/OFFICE 19 only if lineage reproduces.
3. **Independent evaluation:** make an earlier-period evidence table and use a **different later period** to test exact candidate persistence. Avoid reusing the same split/heldout/dropout check as both input `R` and evaluation outcome.
4. **Ablations:** compare frozen old score on emitted labels, component-only features, relative dominance / opportunity / reliability separately, proposed v2 combination and missingness-aware alternatives. Report score coverage by sparse/dense and HOME/OFFICE, identity-retention ordering, temporal stability, candidate/tier rank flips and failure modes. No ground-truth accuracy or calibration claims unless genuine verified labels are acquired.
5. **Decision review:** retain or reject v2 after aggregate measurements. A formula that merely raises coverage or gives larger scores is not an improvement; candidate tiers and semantic inference remain separate from product destination-ranking likelihood.

Sources: `docs/eda/41_home_coverage_expansion.md`, `docs/eda/42_exposure_bias_audit.md`, `docs/eda/43_exposure_aware_policy.md`, `docs/eda/34_near_miss_office_audit.md`, `docs/eda/26_factorized_work_profiles.md`, and the post-AWS roadmap in PR #73.

**Next operator task:** run the synthetic tests on local, then prepare the private feature-lineage adapter in Modal. No AWS deployment, canary restart or EC2 cost is needed.
