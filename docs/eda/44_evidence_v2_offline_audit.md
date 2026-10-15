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

## Modal private-cache adapter (Stage 10a; implemented, not yet executed on real data)

The adapter `analysis/10a_evidence_v2_private_adapter.py` uses exactly the
existing *trusted* cache files produced by `notebooks/05_home_office_reliability_validation.ipynb`,
`08a_home_coverage_expansion.ipynb`, `08b_exposure_bias_audit.ipynb`,
and `08c_exposure_aware_policy.ipynb`. It does **not** rescan raw GPS or re-run
CP1/CP2. These inputs are inside `/mnt/geolife-data/cache/cp2_v2/`:

```text
05_home_office_reliability_validation/dropout_details_private.pkl
08a_home_coverage_expansion/home_expansion_evidence_private.pkl
08b_exposure_bias_audit/gate_diagnostics_private.pkl
08c_exposure_aware_policy/sparse_home_support_candidates_private.pkl
08c_exposure_aware_policy/dense_home_concentration_candidates_private.pkl
08c_exposure_aware_policy/dense_office_near_miss_candidates_private.pkl
```

Dropout stability `R` is the **Stage-05 fixed-window exact-candidate
retention over all nine predeclared dropout trials** (3 dropout rates × 3
seeds). A missing/partial set or a mismatch of candidate identity gives
`R=unavailable`. For `HOME_SPARSE_CANDIDATE`, the fixed-window Stage-05
ranker requires 3 dates and cannot produce the 2-of-2 case: `R` is
**deliberately unavailable**, so the full v2 score stays unavailable. No
fake `R=1` or guessed 70% confidence.

The `runner_up_share` is reconstructed from Stage-08b eligible share/margin
or raw share/margin according to the candidate policy. Stage-08b fills a
missing runner-up with zero when computing margin: when margin equals top
share the adapter keeps **runner-up unknown**, and the v2 score is unavailable.
This is a known feature-coverage limitation, not evidence that the candidate
is wrong. Stable candidate identity is checked against the same CP2-v2
location namespace; Stage 08a probable identity must match Stage 08c dense
HOME. Cohort parity requires 27 HOME_CORE, 16 OFFICE_CORE, +5 probable HOME,
+4 sparse HOME, +3 robust OFFICE; **any drift stops the run**.

### Run in the existing Modal Jupyter environment

Use a terminal in Modal where the GeoLife private Volume is already mounted.
Clone the research branch into a **separate new checkout** to avoid changing
the existing `/root/geolife` main checkout used by older notebooks:

```bash
git clone --depth 1 --branch feature/evidence-v2-offline-audit \
  https://github.com/tanh1c/geolife.git /tmp/geolife-evidence-v2

python /tmp/geolife-evidence-v2/analysis/10a_evidence_v2_private_adapter.py \
  --cache-root /mnt/geolife-data/cache/cp2_v2
```

Preconditions: Python environment already has numpy and pandas; do not
`pip install` or rerun all notebooks unless these dependencies are actually
missing. The trusted `.pkl` files are read-only inputs (pickle must never come
from untrusted uploads). The adapter creates **only on the private Volume**:

```text
10_evidence_v2_offline/candidate_features_private.pkl
10_evidence_v2_offline/candidate_scored_private.pkl
10_evidence_v2_offline/aggregate_summary.json
```

It prints aggregate-only JSON containing group counts, score coverage, and
non-small-group median evidence scores (minimum 5 rows by default); no
user ID or coordinate is printed. Send only this sanitized JSON back for
review. **Do not print/upload any private pickle or per-user row.**

**Interpretation:** even with this adapter, v2 has **not** been validated
against future observations or independent semantic ground truth. Stage-05
full-period dropout must not be re-used as independent temporal validation.
The first private pass is a feature-lineage/coverage audit, NOT a proof the
new formula is better.

## Stage 10a — First Modal private-cache audit (operator-reported, 2026-10-15)

The operator successfully cloned commit `b134913`, passed all six cache preflight
checks, and ran the Stage 10a adapter on the frozen private Modal Volume.
Candidate-tier count parity: **55/55** (= HOME_CORE 27, OFFICE_CORE 16,
HOME_PROBABLE 5, HOME_SPARSE_CANDIDATE 4, OFFICE_ROBUST_CANDIDATE 3).
**Only 21/55 (38.2%)** obtained a full evidence-v2 heuristic; **34/55
(61.8%)** could not be scored under the strict four-component formula.
No coordinates/identifiers were exported.

| label / tier / regime | candidates | scorable | observed median v2 |
| --- | ---: | ---: | ---: |
| HOME_CORE DENSE | 16 | 7 | 0.859201 |
| HOME_CORE MEDIUM | 11 | 0 | suppressed / unavailable |
| HOME_PROBABLE DENSE | 5 | 4 | suppressed (under 5 scored) |
| HOME_SPARSE_CANDIDATE SPARSE | 4 | 0 | suppressed / unavailable |
| OFFICE_CORE DENSE | 11 | 7 | 0.674558 |
| OFFICE_CORE MEDIUM | 5 | 1 | suppressed |
| OFFICE_ROBUST_CANDIDATE DENSE | 3 | 2 | suppressed |

All 34 unscorable rows were reported under the Stage 10a *single-priority*
`missing_or_invalid_runner_up` reason. This reflects the adapter's
conservative interpretation of Stage-08b's filled-zero competitor; it is
**not** evidence that an emitted or near-miss location was semantically wrong.
The single-priority `v2_status` might mask simultaneous gaps in other
components (for instance, Stage-05 cannot produce an equivalent fixed-window
dropout R for the four 2-of-2 sparse HOME candidates).

**Interpretation / decision:** a full v2-score comparison against all
HOME/OFFICE tiers would be strongly selected toward candidates with an
observed runner-up; notably 0/11 MEDIUM HOME_CORE candidates are scorable.
**Do not replace evidence v1, impute missing runner-up as zero, assign a
probability, or promote tiers based on the 21 observed scores.**
Medians on the 7 DENSE HOME and 7 DENSE OFFICE scored cases cannot establish
general ranking quality or true semantic accuracy.

## Stage 10b — Multi-cause missingness audit (next, no EDA rerun)

New `analysis/10b_evidence_v2_missingness_audit.py` reuses the Stage-10a
`candidate_scored_private.pkl` already written to the trusted Modal Volume.
It reports **independent, overlapping** feature availability counts for
missing runner-up, invalid top-2 values, invalid observation opportunity,
and missing/invalid candidate-identity stability. It never prints private
user rows or coordinates; only aggregate JSON.

After updating the research clone on Modal (or cloning a new checkout), run:

```bash
python /tmp/geolife-evidence-v2-stage10a/analysis/10b_evidence_v2_missingness_audit.py \
  --cache-root /mnt/geolife-data/cache/cp2_v2
```

The final output is also saved on the private Volume as
`10_evidence_v2_offline/feature_availability_aggregate.json`. Send back only
that aggregate JSON. Stage 10b diagnoses availability: **it does not
change the proposed v2 formula, candidate tiers, frozen production, or test
time-separated semantic accuracy.**

**Next design decision after diagnostics:** determine whether absent
runner-up means an eligible singleton and propose an explicitly
missingness-aware feature representation/alternative score. Do not
equate no measured runner-up with a true zero competing destination.
Use independent chronological holdouts for ranking validation.
