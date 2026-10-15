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

## Stage 10b — Measured multi-cause availability on the trusted Modal Volume

**Operator-reported, 2026-10-15:** `Stage 10b completed`; 55
candidate hypotheses, 21 with complete proposed v2 scores. The independent
feature-blocker totals were:

| Blocker | Number |
| --- | ---: |
| Missing runner-up | 34 |
| Invalid top / known runner-up value | 0 |
| Invalid observed opportunity | 0 |
| Missing/invalid identity stability | 4 |
| Multiple simultaneous blockers | 4 |

**All four** missing stability values belong to Stage-08c's sparse 2-of-2
HOME tier, and overlap with the missing-runner-up subset. Thus the exact
34 unscorable rows cannot be explained by missing stability alone, and
no invalid opportunity exposure was found.

Regime-level patterns: HOME_CORE MEDIUM 11/11 missing runner-up (0/11
scorable); HOME_CORE DENSE 9/16; OFFICE_CORE DENSE 4/11; OFFICE_CORE
MEDIUM 4/5; HOME_PROBABLE DENSE 1/5; OFFICE_ROBUST_CANDIDATE DENSE 1/3;
sparse HOME 4/4 (plus missing stability 4/4). These counts indicate a
nonrandom availability problem and prohibit interpreting the 21 observed
scores as a representative sample.

**Policy remains frozen:** no changes to production score, semantic labels
or Stage-08c candidate acceptance, no fabricated 0% competitor, no
calibrated accuracy claims.

## Stage 10c — Exact eligible-runner-up provenance audit (next)

Stage 10c is implemented in `analysis/10c_evidence_v2_runner_up_provenance.py`.
Stage 08b's `share_margin` stores a **zero-filled** runner-up when only
one eligible location exists in the relevant ranker. A near-zero
`top_share - share_margin` is therefore ambiguous without revisiting
the candidate eligibility set. Instead of guessing a zero competitor,
Stage 10c reconstructs the frozen CP2-v2 spatial representation from
the **existing 5,821 trusted CP1 stays** (not raw PLT, no stay-detection
rerun, no full notebook-EDA rerun), and rebuilds only the location-window
features and exact eligible ranking:

- HOME_CORE / HOME_PROBABLE / OFFICE_CORE / OFFICE_ROBUST_CANDIDATE:
  fixed-window rank with frozen `min_dates=3`;
- HOME_SPARSE_CANDIDATE: Stage-08b unconstrained raw rank with
  `stay_count >= 2`, window dwell > 0, and **no** minimum dates.

The audit checks exact CP1/CP2 reference totals, the candidate location
namespace, top share and runner-up share for every one of the 55 candidates.
If any candidate mismatches, it **fails closed** rather than reporting
a misleading count. The output distinguishes
`sole_eligible_location` from `has_eligible_runner_up` and exports
only aggregate counts. Even a singleton rank does **not** prove the
person has no alternative destination: it only says no *other observed*
location passed that label's specific evidence gates.

Use a Modal Jupyter Python cell to fetch the latest research branch in its
separate checkout and then run:

```bash
python /tmp/geolife-evidence-v2-stage10a/analysis/10c_evidence_v2_runner_up_provenance.py \
  --cache-root /mnt/geolife-data/cache/cp2_v2 \
  --stays-cache /mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl
```

Input: existing trusted private `candidate_scored_private.pkl` and
`stays_baseline_v1.pkl`. Output, staying only on the private Volume:

```text
10_evidence_v2_offline/runner_up_provenance_private.pkl
10_evidence_v2_offline/runner_up_provenance_aggregate.json
```

Do **not** upload either private pickle or per-user details. Share only
the aggregate JSON if the parity checks pass. This audit does **not**
modify `evidence_strength_v2`, CP2 inference, data privacy controls
or the deployed API. After the result, compare a missingness-aware,
factorized evidence representation rather than naively forcing every
case through a relative-top-two geometric mean; separate sparse HOME
stability evaluation remains necessary.

## Stage 10c — Measured runner-up provenance (operator-reported, 2026-10-15)

The operator ran Stage 10c successfully after installing `timezonefinder==9.0.0`
in the Modal notebook interpreter. The frozen CP2 representation and all
**55 candidate identities/shares passed exact namespace/ranking parity**.
The 34 missing second-rank values found in Stage 10a/10b correspond to
**34 candidates with precisely one eligible location** under the respective
CP2 ranker; the other **21 candidates have an eligible runner-up**.
They are not caused by a broken 08b → 10a join.

| Tier / regime | Only one eligible location | Has eligible second |
| --- | ---: | ---: |
| HOME_CORE DENSE | 9 | 7 |
| HOME_CORE MEDIUM | 11 | 0 |
| HOME_PROBABLE DENSE | 1 | 4 |
| HOME_SPARSE_CANDIDATE SPARSE | 4 | 0 |
| OFFICE_CORE DENSE | 4 | 7 |
| OFFICE_CORE MEDIUM | 4 | 1 |
| OFFICE_ROBUST_CANDIDATE DENSE | 1 | 2 |
| **Total** | **34** | **21** |

**Important interpretation:** "one eligible location" is conditional on the
label-specific ranker and its support-date/stay-count gates, in the history
we managed to observe. It does **not** imply the person has only one
real-life destination, or that competing HOME/OFFICE hypotheses have 0%
probability. In particular, all 11 MEDIUM HOME_CORE candidates lack an
eligible peer despite having an emitted HOME.

**Decision recorded:** No production change to v1 or v2; no automatic
`C=1` for singletons; do not create arbitrary probabilities by applying
a different denominator. Move to separately reported factorized evidence
dimensions with independent later temporal validation.

## Stage 10d — Factorized evidence dimensions (new offline study, not a replacement)

Stage 10d reads **only existing trusted private** Stage 10a `candidate_scored_private.pkl`
and Stage 10c `runner_up_provenance_private.pkl`. It produces
individually typed/availability-gated evidence *dimensions*, rather than
trying to force all 55 candidates into one scalar:

- `observed_date_coverage = candidate_support_days / opportunity_days`;
- `support_factor = min(candidate_support_days / 5, 1)` (two different temporal
  descriptions; not independent accuracy probabilities);
- `identity_stability`, if Stage-05 exact-candidate dropout evidence exists;
- `relative_peer_dominance = top_share / (top_share + runner_up_share)`,
  **only** when Stage 10c proves there is a second eligible location.

All rows retain `eligible_competitor_status`; a singleton's relative
dominance is **inapplicable/unknown**, not 1.0. If Stage 10a vs Stage 10c
candidate identity or score feature availability disagrees, stop instead
of emitting a report. CI uses *only synthetic* fixtures.

On an existing Modal Jupyter kernel, fetch the latest research branch
into the separate checkout and run:

```bash
python /tmp/geolife-evidence-v2-stage10a/analysis/10d_evidence_v2_factorized_profile.py \
  --cache-root /mnt/geolife-data/cache/cp2_v2
```

Private output (do not share):
`10_evidence_v2_offline/factorized_dimensions_private.pkl`.

Only share reviewed aggregate JSON printed and saved as:
`10_evidence_v2_offline/factorized_dimensions_aggregate.json`.

**Open question:** How should candidate quality be assessed under an
independent *future-period* identity-retention test, when the original
period has exactly one eligible location? Until that study, report a
multi-dimensional evidence profile and candidate tier, **not a percent
confidence nor a cross-tier calibrated quality ranking**.


## Stage 10d — Measured factorized evidence on private Modal data

Operator reported `Stage 10d completed`, exact Stage 10a/10c private
candidate namespace match, and an aggregate report with:

- `candidate_rows=55`, **temporal availability 55/55**;
- **identity stability available 51/55**, the four unavailable all
  `HOME_SPARSE_CANDIDATE` under the mismatched Stage-05 >=3-day fixed-window
  dropout regime;
- **relative peer dominance available 21/55** (the 21 candidates having an
  observed eligible second location; the other 34 are proven singletons of
  the eligibility set);
- **old experimental scalar formula available 21/55**; it is not adopted.

Selected medians (aggregate-only; suppressed when fewer than five
observations in a group or for a given component):

| Tier / exposure | observed-date coverage | support factor | identity stability | conditional peer dominance |
| --- | ---: | ---: | ---: | ---: |
| HOME_CORE DENSE (n=16) | 0.684659 | 1 | 1 | 0.864435 (7 observed peers) |
| HOME_CORE MEDIUM (n=11) | 1 | 0.8 | 0.888889 | unavailable |
| HOME_PROBABLE DENSE (n=5) | 0.294118 | 1 | 1 | suppressed (4 peers) |
| OFFICE_CORE DENSE (n=11) | 0.565217 | 1 | 1 | 0.810376 (7 peers) |
| OFFICE_CORE MEDIUM (n=5) | 0.666667 | 0.8 | 1 | suppressed (1 peer) |

`HOME_SPARSE_CANDIDATE` (n=4) and `OFFICE_ROBUST_CANDIDATE` (n=3)
have component-level median values withheld due to the predeclared
five-observation minimum, not due to a claim about quality.

**Interpretation / decision:** Support factor saturating at >=5 dates
cannot by itself distinguish `HOME_PROBABLE` DENSE with observed-date
coverage median 0.294118 from HOME_CORE DENSE median 0.684659. Likewise,
full formula missingness is a peer-eligibility structural issue,
not necessarily weak HOME/WORK evidence. Component-level medians may be
computed on different subsets and must not be interpreted as comparative
HOME/OFFICE accuracy, statistical significance or calibrated probabilities.

No scalar `evidence_strength_v2` replacement, change to frozen production
HOME=27 / OFFICE=16, or automatic candidate-tier promotion is approved.

## Stage 10e — Forward-holdout feasibility only (next operator task)

Before attempting to estimate out-of-time candidate retention, we must
verify enough earlier/later observational support **without leaking future
stays into training features or spatial clustering**. Current Stage 10a–10d
feature sets and Stage-05 dropout stability use the full historical period;
therefore they cannot be treated as fully past-only predictor features for
a forward holdout.

`analysis/10e_forward_holdout_preflight.py` reads *existing trusted* private
`stays_baseline_v1.pkl` and the Stage 10d factorized candidate
cache. It makes a retrospective, predeclared **70%/30% split of each
user's distinct observed UTC arrival dates**, excludes stays crossing
the cutoff, and reports only an aggregate feasibility breakdown by tier.
These are **UTC observational proxy counts**, not label-specific
HOME-night/weekday-OFFICE opportunity days and not evidence that the
training period would have emitted the same candidate. A user/tier
with at least 3 earlier UTC dates + 2 future UTC dates is counted as
`both_train_and_future_proxy`, not `correctly predicted`.

Run on the existing trusted Modal Volume after updating the separate
research checkout:

```bash
python /tmp/geolife-evidence-v2-stage10a/analysis/10e_forward_holdout_preflight.py \
  --cache-root /mnt/geolife-data/cache/cp2_v2 \
  --stays-cache /mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl
```

The script checks frozen 5,821-stay/136-user counts and the existing
55 candidate-tier counts, prints **only aggregate JSON**, and saves on
the private Modal Volume:

```text
10_evidence_v2_offline/forward_holdout_feasibility_private.pkl
10_evidence_v2_offline/forward_holdout_feasibility_aggregate.json
```

For **later actual forward validation** (not implemented here):
(1) resolve IANA local-time behavior opportunity dates strictly from TRAIN
stays; (2) fit CP2 complete-link clusters on TRAIN only and select new
TRAIN-specific candidates/tiers; (3) derive temporal/stability evidence
only using TRAIN; (4) assign FUTURE stays to the fitted training locations
using a predeclared spatial alignment/tolerance without refitting clusters
on future data; (5) score exact identity recurrence and HOME/OFFICE
time-window behavior in FUTURE, with abstention and missingness;
(6) stratify by label, sparse/dense and no-peer eligibility.
Global all-period location IDs or Stage-10a full-period labels must not
be smuggled in as training predictions. Even success on this surrogate
evaluation does **not** prove semantic HOME/OFFICE correctness without
verified semantic ground truth.
