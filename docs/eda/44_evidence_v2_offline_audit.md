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


## Stage 10e — Measured chronological UTC feasibility (operator-reported)

The operator executed the 70/30 retrospective UTC arrival-date preflight
and returned `Stage 10e completed`, aggregate-only. **52/55 (94.5%)**
full-history candidate hypotheses meet the coarse proxy of at least three
earlier observed UTC dates plus two later observed UTC dates:

| Full-history tier (post-hoc stratum only) | Pass both UTC proxies | Total |
| --- | ---: | ---: |
| HOME_CORE | 27 | 27 |
| OFFICE_CORE | 16 | 16 |
| HOME_PROBABLE | 5 | 5 |
| OFFICE_ROBUST_CANDIDATE | 3 | 3 |
| HOME_SPARSE_CANDIDATE | 1 | 4 |
| **Total** | **52** | **55** |

Aggregate: 54/55 meet early UTC support; 52/55 meet late UTC support;
three HOME_CORE candidate rows involve at least one stay crossing the per-user cutoff; such stays are excluded from both folds. The aggregate does not provide the exact number of crossing stays. **This is NOT 52 validated predictions**:
the tiers were selected with full history and dates are UTC proxy
observations, not HOME-night/OFFICE-weekday-window opportunities. Sparse
HOME cannot be judged by a pooled dense-majority result; only 1 of 4
passes the coarse preflight.

**Decision:** sufficiently many historical core cases exist to justify
a TRAIN-only forward-validation experiment, but do not evaluate the existing
Stage10a/10d full-history scores on future data as if they were train-time
predictions.

## Stage 10f — TRAIN-only spatial/time-window reappearance (next)

`analysis/10f_train_only_forward_validation.py` performs a **new
independent temporal-behavior evaluation on ALL 136 CP1 stay users**,
without using the selected full-history Stage10a candidate list as input:

1. Split each user's cached CP1 stays by the same predeclared first 70%
   distinct UTC arrival dates, leaving the last 30% for FUTURE; exclude
   stays crossing cutoff, never use later timestamps or GPS to fit train.
2. Run frozen `HomeOfficeConfig()` and complete-link 200 m clustering
   **only on TRAIN**, and execute the exact CP2 HOME/OFFICE emit gates and
   v1 train evidence heuristic, within the new TRAIN namespace.
3. For each FUTURE GPS stay, resolve IANA local time but **do not re-cluster**:
   assign to a unique training anchor only when the future stay lies within
   200 m of **every training stay centroid** in the cluster (complete-link
   compatible extension). Unknown or multiply compatible stays abstain
   from assignment.
4. Evaluate whether the already-emitted TRAIN anchor reappears in the
   matching later HOME-night or OFFICE-weekday window, counting a relevant
   date only with at least 600 s observed overlap; report future-window
   observation opportunity separately from absence of matched recurrence.
5. Print only aggregate `train_emitted_candidates`,
   `future_window_assessable`,
   `future_same_anchor_reappears`, and unmatched/ambiguous assignments,
   grouped by HOME/OFFICE. Keep full row-level assessment and cutoff
   timestamps private inside the Modal Volume.

The outcome tests **same physical place and relevant-hour reappearance**,
not verified semantic label correctness. Some real future HOME/OFFICE
locations may fail conservative 200 m alignment due to GPS jitter,
relocation or changed activity; no unmatched stay is forcibly relabeled.
No new global 27/16 emission count is promised for the 70% TRAIN slice.
Neither Stage10a full-history tiers nor Stage05 full-period dropout stability
are used as predictor inputs. A 70/30 retrospective date cutoff does
consult the observation timeline to choose the test period; therefore
this is **retrospective temporal testing**, not a prospective online
service simulation.

**Modal Jupyter / Terminal** (existing checkout; after fetching latest
research branch):

```bash
python /tmp/geolife-evidence-v2-stage10a/analysis/10f_train_only_forward_validation.py \
  --stays-cache /mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl \
  --cache-root /mnt/geolife-data/cache/cp2_v2 \
  --train-fraction 0.70
```

Ensure `PYTHONPATH=/tmp/geolife-evidence-v2-stage10a/src` and the
frozen CP2 dependency `timezonefinder==9.0.0` are available.

Private outputs:
`10_evidence_v2_offline/train_only_forward_candidates_private.pkl`,
`train_only_forward_partitions_private.pkl`.

Share only `10_evidence_v2_offline/train_only_forward_aggregate.json`
or the printed aggregate JSON, **not** any private pkl/user/stay records.

**Still later, not Stage10f:** compare predeclared *TRAIN-only* evidence
rankings against future identity/window recurrence, include all abstentions
and exposure strata, investigate sparse 2/2 separately, and repeat across
multiple temporal cutoffs or new users. Do not claim semantic accuracy,
ROC-AUC/precision, calibration or superiority of the proposed
`cbrt(C*O*R)*sqrt(H)` formula without valid independent evidence.


## Stage 10f — Measured TRAIN-only future anchor reappearance

**Operator-reported Modal run completed**, with TRAIN-only CP2 complete-link
clusters and no refitting locations using FUTURE GPS. The historical CP1
dataset includes 136 users with stays; **114 users retained TRAIN stays**.
Across these training users, frozen CP2 emitted **44** anchors (HOME 27,
OFFICE 17); the TRAIN-only count and identities are **not** expected to
match the full-period HOME 27 / OFFICE 16 reference.

| Outcome | HOME | OFFICE | Total |
| --- | ---: | ---: | ---: |
| TRAIN emitted anchors | 27 | 17 | 44 |
| Later HOME-night / OFFICE-weekday window assessable | 27 | 16 | 43 |
| Same TRAIN anchor reappeared in later relevant window on >=1 supported date | 17 | 8 | 25 |
| Assessable but not observed again under strict geometry + time-window | 10 | 8 | 18 |
| Later window unassessable | 0 | 1 | 1 |
| TRAIN only one eligible anchor | 22 | 11 | 33 |
| TRAIN multiple eligible anchors | 5 | 6 | 11 |

**Conditional observed anchor reappearance** = 25/43 (58.1%) overall,
17/27 (63.0%) HOME and 8/16 (50.0%) OFFICE, each **conditional on a
future observed relevant local time window**. This is **NOT** verified
HOME/OFFICE semantic accuracy or percentage confidence. Reappearance
threshold is only one later behavior date at the same TRAIN location
with >=600 seconds relevant local-window observation; it is not a
strong multi-day routine persistence test.

Spatial alignment of **all 1,656 FUTURE stays**, including stays outside
HOME/OFFICE time windows: **595 uniquely matched** (35.9%),
**859 unmatched** (51.9%) and **202 ambiguous** (12.2%).
The denominator is future stays, NOT 44 emitted anchor predictions.
Reasons for unmatched include previously unseen places, changed
behavior, GPS uncertainty and conservative 200m-to-every-TRAIN-member
matching. Ambiguous means more than one TRAIN cluster is compatible:
do not coerce an arbitrary anchor identity. **18/43 failures to observe
the anchor again cannot be equated to 18 false semantic labels.**

Three USERS (not necessarily three stays) had a stay crossing their
training cutoff; these stays were excluded. No full-history Stage10a
tier/score or Stage05 dropout was used to make the TRAIN-only
predictions, so Stage10f is a valid retrospective behavioral
reappearance check within the predeclared split. The split is still
based on the complete observed timeline, not a deployed online model
at a calendar-fixed cutoff. Spatial matching assumptions and
small office cohorts limit generalization.

**Decision:** do not replace CP2's v1 score, install the hypothetical
geometric Evidence v2, promote Stage08c tiers or call any of these
percentages semantic accuracy. Keep this as evidence of future
behavioral observability/anchor persistence and inspect ranking
comparisons using ONLY TRAIN-derived features.

## Stage 10g — Frozen TRAIN evidence v1 vs future reappearance (next)

`analysis/10g_train_score_recurrence_audit.py` **does not re-run GPS/CP2**
and reads ONLY
`10_evidence_v2_offline/train_only_forward_candidates_private.pkl`
created by Stage10f. Its predeclared *exploratory* comparisons include:

- TRAIN CP2 `evidence_strength` median among candidate anchors
  observed again vs not observed again, **only among future assessable**,
  with a five-row suppression threshold;
- the same conditional 1-date matching for HOME, OFFICE and
  TRAIN singleton-vs-multiple-eligible anchor groups;
- a **secondary stricter** time-window diagnostic: require >=2 future
  observed relevant dates to assess and >=2 same-anchor future
  relevant dates to mark recurrence. Do not confuse this with the
  earlier one-date definition;
- TRAIN support-day and future observed-window date counts to reveal
  differences in observation opportunity.

No v2 score is tested: Stage10a/10d v2 and Stage05 dropout features
were built on full history and cannot be used as leakage-free TRAIN
predictors. This is **not** a supervised score optimization, label
probability calibration, ROC accuracy benchmark or proof of v1
generalization. Even a difference in median scores can be driven by
strict spatial matching and uneven future observation.

On the existing trusted Modal environment (after updating the
separate research checkout):

```bash
python /tmp/geolife-evidence-v2-stage10a/analysis/10g_train_score_recurrence_audit.py \
  --cache-root /mnt/geolife-data/cache/cp2_v2
```

Only aggregate printed JSON and
`10_evidence_v2_offline/train_only_score_recurrence_aggregate.json`
can be shared. Never print/upload candidate user IDs or private
per-user pickle artifacts.

Next deeper work (not implemented by 10g): identify the contribution
of spatial non-matching specifically within future label windows,
and test train-only temporal/competitor components against later
recurrence using independent date cutoffs. Preserve abstention when
future GPS does not allow a valid spatial identity match.


## Stage 10g — Measured frozen TRAIN v1 score and FUTURE recurrence

**Operator-reported private Modal run (2026-10-15):** `Stage 10g completed`.
It reused only Stage10f outcomes derived from frozen **TRAIN-only** CP2
HOME/OFFICE emissions. Observed exact-anchor future reappearance at
>=1 local behavior-window support date was **25/43 (58.1395%)** among
43 future-assessable anchors; **14/36 (38.8889%)** passed the separate
>=2-future-observation-dates and >=2-future-anchor-dates test.

| TRAIN label | emitted | 1-date future observed / reappeared | 2-date future observed / reappeared | v1 median if reappears (1-day) | v1 median if not |
| --- | ---: | ---: | ---: | ---: | ---: |
| HOME | 27 | 27 / 17 | 21 / 10 | 0.866667 | 0.809177 |
| OFFICE | 17 | 16 / 8 | 15 / 4 | 0.691932 | 0.637519 |
| Total (pooled) | 44 | 43 / 25 | 36 / 14 | 0.797806 | 0.687676 |

**Descriptive only:** The v1 TRAIN evidence medians are greater for
future-reappearing than for future-unobserved anchors in both labels;
the observed difference is HOME +0.057490 and OFFICE +0.054413.
The pooled difference +0.110130 should **not** be interpreted as an
improvement over the per-label estimates: HOME and OFFICE have
different score distributions, recurrence baselines and denominators.
There are only 43 future-assessable anchors, potentially with
correlated HOME/OFFICE labels across users; no statistical uncertainty,
independent repeated cutoff, calibration, semantic truth or causal
feature attribution has been established.

**TRAIN singleton/multiple eligible comparisons:**
HOME singleton 13/22 recurrence within >=1 later relevant date,
multiple eligible 4/5; OFFICE singleton 5/10, multiple eligible 3/6.
HOME multiple-eligible anchors have median TRAIN support **10 days**
versus 4 days among singleton HOME anchors, so the recurrence
difference cannot be ascribed to having a rival anchor. Small subgroup
outcome-conditioned medians are appropriately suppressed.

**Important limitation:** The 1-day and 2-day recurrence percentages
refer to **different eligible future-observation subsets**. For
instance, 25/43 vs 14/36 is not a matched-sample degradation rate.
Moreover, 859/1656 FUTURE stays were unmatched and 202/1656 had
ambiguous train-anchor spatial compatibility under Stage10f's strict
200m rule. Thus non-reappearance cannot be equated to false semantic
HOME or OFFICE classification.

**Decision:** Keep original frozen `evidence_strength` v1 for
production. Do not claim better than v2: the old experimental Stage10a
v2 score uses full-history evidence and was NOT tested in Stage10g.
The observed v1 median separation motivates comparing its individual
TRAIN-only ingredients, not optimizing a scalar yet.

## Stage 10h — TRAIN-only v1 component decomposition (next)

New `analysis/10h_train_only_component_audit.py` reads the trusted
private frozen CP1 stay cache and Stage10f's private TRAIN candidate
outcomes. It **rebuilds CP2 only on the earlier TRAIN fold**, then
computes and retains these TRAIN-only quantities:

- `train_dwell_share` (v1 S), `train_share_margin` (v1 M)
  and `train_support_factor` (v1 H) with exact frozen
  `v1=(S+M+H)/3` parity checks;
- local HOME-night / weekday-OFFICE train observation opportunity
  dates and `train_observed_date_coverage`, keeping all FUTURE
  observations out of candidate features;
- `train_relative_peer_dominance` ONLY when >=2 locations meet
  the TRAIN eligible ranker; singleton has `null`, **never C=1**.

The script checks every TRAIN candidate key, v1 score, support count
and eligible location count against the saved Stage10f private output
and stops on any mismatch. It prints **only aggregate median components**
for all future-assessable, reappeared and non-reappeared subsets by
HOME/OFFICE and TRAIN singleton/multiple eligible status, suppressing
group medians with fewer than five observations.

Run in Modal after updating the separate research checkout:

```bash
PYTHONPATH=/tmp/geolife-evidence-v2-stage10a/src \
python /tmp/geolife-evidence-v2-stage10a/analysis/10h_train_only_component_audit.py \
  --stays-cache /mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl \
  --cache-root /mnt/geolife-data/cache/cp2_v2 \
  --train-fraction 0.70
```

The existing `timezonefinder==9.0.0` dependency is required because
TRAIN CP2 clustering uses original IANA timezone resolution. Private
candidate-level data is saved only as
`10_evidence_v2_offline/train_only_components_private.pkl`;
send only the printed JSON, also saved as
`train_only_components_aggregate.json`. No raw GPS, coordinate,
user ID or private per-candidate row should be posted.

**Still not done:** independent across-cutoff replication, uncertainty
estimation, stratified spatial matching audit, TRAIN-only robustness R
for sparse HOME, or genuine semantic ground-truth validation. Stage10h
is component *description* on a 70/30 retrospective holdout, **not**
v2 formula adoption or a feature-importance causal experiment.


## Stage 10h — Measured TRAIN-only v1 component decomposition

**Operator-reported private Modal run completed.**
`train_only_component_parity=true` against all 44 Stage10f
TRAIN-fitted emitted candidates; 43 have observable FUTURE
label windows and 25 show >=1-date exact TRAIN-anchor recurrence.
Peer dominance, defined only when a second TRAIN-eligible
location exists, is available for **11/44** (HOME 5, OFFICE 6).
For the **33 singleton TRAIN-eligible ranks** the frozen v1
`share_margin = top_share - 0 = top_share` is a known CP2
policy convention, NOT a separately measured competing
place. Thus `v1 = (2*S+H)/3` for these singletons and
margin cannot be interpreted as independent corroboration.

Selected conditional median TRAIN features (aggregate only;
reappears = 25, not reappears = 18 across the label mixture):

| TRAIN feature | Reappears | Not reappears |
| --- | ---: | ---: |
| Frozen v1 evidence | 0.797806 | 0.687676 |
| Relevant-window dwell share (S) | 0.799735 | 0.660261 |
| Share margin (M) | 0.697787 | 0.575030 |
| Saturating date support (H) | 1.0 | 0.8 |
| Observed opportunity date coverage (O) | 0.666667 | 0.674242 |
| Conditional peer dominance (C) | 0.904487 (only peers) | suppressed |

**Within-label** median coverage is higher among reappearing
than non-reappearing candidates (HOME 0.846154 vs 0.732143;
OFFICE 0.555556 vs 0.485294), despite pooled O medians
0.666667 vs 0.674242 reversing direction. The pool therefore
cannot be treated as evidence of no temporal-opportunity effect.
HOME median H is 0.8 in both groups, while OFFICE median H
is 1.0 vs 0.8. This is descriptive on different small
subsets, not causal feature importance or statistical significance.

TRAIN singleton group: HOME 22 (13 later recur) with
median S/M 0.918217 in those who recur vs 0.812859
in those not observed again; OFFICE singleton 11 (10
assessable, 5 recur) with S/M medians 0.661880 vs
0.459741. These equal S/M values are **arithmetic
duplication** under singleton margin behavior, not extra evidence.
The multiple-eligible groups (HOME 5, OFFICE 6) have
suppressed conditioned medians due to sample size.

**Decision:** Frozen production `evidence_strength`, complete-link
clustering, full-history 27 HOME / 16 OFFICE emissions and
Stage08a/08c research candidate tiers stay unchanged. Do not
replace v1 or optimize scalar v2 yet; v2 Stage10a–10d
was full-period and was NOT evaluated as a TRAIN-only
predictor. Stage10h verifies its *TRAIN feature lineage*
and the need for missingness-aware C without claiming v2
predictive superiority.

## Stage 10i — FUTURE spatial opportunity audit (next)

Stage 10f marked future time-window *observability*
using GPS HOME-night / OFFICE-weekday overlap even when
a future stay could not be assigned uniquely to any
TRAIN location. Given only 595/1656 future stays
uniquely matched anywhere, Stage 10g/10h anchor
nonreappearance is confounded by **spatial** observation
in addition to temporal opportunity.

`analysis/10i_future_spatial_observability.py`
reruns the strictly TRAIN-only frozen CP2 inference
and the unchanged future **evaluation-only** spatial
alignment, asserting exact Stage10f cached candidate
identities, v1 score, window and same-anchor date counts.
For each TRAIN-emitted candidate and label-specific
local behavior window it separately counts:

- `future_time_observable`: >=1 future relevant
  local behavior date with >=600s GPS overlap;
- `future_unique_spatial_observable`: >=1 such
  date with >=600s of future GPS assigned to
  some uniquely compatible TRAIN anchor;
- `future_spatially_unresolved`: future time observed,
  but **zero** uniquely spatially supported future
  behavior dates;
- `future_same_anchor_reappears`: later window
  matches the original TRAIN candidate;
- among those without exact recurrence, cases with
  no unique train-location support and cases with
  sufficient support for an OTHER unique train anchor.

No ambiguous or unmatched future stay is forced into
an existing anchor. As a result, the output clarifies
whether a missing future same-anchor observation may
be **unassessable spatially** despite being assessable
in time. This remains an imperfect proxy; location
change and GPS sampling effects are not semantically labeled.

On the trusted Modal Jupyter environment after fetching
the research branch:

```bash
PYTHONPATH=/tmp/geolife-evidence-v2-stage10a/src \
python /tmp/geolife-evidence-v2-stage10a/analysis/10i_future_spatial_observability.py \
  --cache-root /mnt/geolife-data/cache/cp2_v2 \
  --stays-cache /mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl \
  --train-fraction 0.70
```

Private output:
`10_evidence_v2_offline/future_spatial_observability_private.pkl`.
Only the aggregate printed JSON or
`10_evidence_v2_offline/future_spatial_observability_aggregate.json`
is appropriate to share. No raw GPS/user/coordinates,
no automatic HOME/OFFICE label correction.


## Stage 10i — Measured future time-vs-spatial observability

**Operator-reported private Modal execution completed**, 2026-10-15.
TRAIN-only frozen 70/30 candidate/label parity with Stage10f passed.
All 44 emitted TRAIN candidates retained; 43 had FUTURE GPS in a
relevant HOME-night or OFFICE-weekday behavior window, but only **31
of those 43** had at least one future relevant behavior date with
>=600 seconds of GPS uniquely compatible with *some* frozen TRAIN
complete-link-200m location. Exactly 25 showed >=1-date same TRAIN
candidate location; the other six had enough unique observations
assigned to *other* TRAIN locations (not the originally emitted one).
The remaining 12 were FUTURE-time-window observable but had **zero
spatially resolvable relevant days**.

| Metric | HOME | OFFICE | Total |
| --- | ---: | ---: | ---: |
| TRAIN emitted | 27 | 17 | 44 |
| FUTURE relevant window observed | 27 | 16 | 43 |
| FUTURE unique TRAIN location observable | 21 | 10 | 31 |
| Same TRAIN anchor reappeared | 17 | 8 | 25 |
| No same-anchor recurrence, other TRAIN location seen | 4 | 2 | 6 |
| Time-observed but spatially unresolved | 6 | 6 | 12 |

**Interpretation:** Of the 18 temporally assessable
non-reappearances in Stage10f, 12/18 (=66.7%) are NOT uniquely
spatially assessable, and six can be spatially mapped to an
alternate TRAIN anchor. Under *conditioning on unique spatial
assessability*, same-anchor reappearance is 25/31 (=80.6%);
HOME 17/21 (=81.0%) and OFFICE 8/10 (=80.0%).
This denominator is **selected by future GPS**, so these
numbers are not population recurrence, prediction accuracy,
semantic HOME/OFFICE correctness, or evidence score calibration.
Even the six alternate-TRAIN-anchor cases may reflect incomplete
HOME/OFFICE-specific future sampling, relocation, changed routine,
or geometric alignment constraints rather than a wrong semantic label.

**Conclusion:** Keep separate FUTURE observability types:
(1) relevant-hour time-observed, (2) unique TRAIN-location
spatially observed, and (3) same TRAIN location observed.
Do not feed future-derived observability into a prediction-time
confidence; it is an **evaluation outcome/censoring diagnostic**.
Production CP2 and research candidate tiers remain frozen.
Stage10h median v1 comparisons on time-only assessable anchors
are confounded by the 12 spatially unresolved cases.

## Next: Stage 10j — Predeclared multi-cutoff sensitivity

Compare frozen TRAIN-only CP2 anchor reappearance under
**60%, 70%, and 80% early observed-UTC-date splits**, with
later local behavior-window and uniquely matched TRAIN-anchor
observability **reported separately**. Do not tune any 200m
matching threshold or Evidence v1/v2 formula on FUTURE
outcomes. Keep the same complete-link training policy and
mark cutoff-crossing stays excluded. These nested splits
re-use the **same users**; they are correlated sensitivity
checks, **not independent replications** or confidence intervals.
A stricter validation would also require disjoint later
participants, temporal cutoffs fixed without future-activity
timeline knowledge, and labeled semantics if accuracy is
the scientific question.


### Stage 10j script and Modal invocation

Implemented `analysis/10j_cutoff_sensitivity.py`, with synthetic
tests in `tests/test_evidence_v2_cutoff_sensitivity.py`. It reuses
the existing frozen CP1 stays and independently refits CP2 using
TRAIN-only histories for 60%, 70% and 80% of observed UTC arrival
dates. It reuses the Stage10i future-window spatial opportunity
definitions and checks Stage10f time/recurrence parity at each
cutoff. Full evaluation is only **retrospective**, uses correlated
repeated participants, and has no label correctness ground truth.

In the trusted Modal notebook environment, fetch the latest
`feature/evidence-v2-offline-audit` checkout, then run:

```bash
PYTHONPATH=/tmp/geolife-evidence-v2-stage10a/src \
python /tmp/geolife-evidence-v2-stage10a/analysis/10j_cutoff_sensitivity.py \
  --stays-cache /mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl \
  --cache-root /mnt/geolife-data/cache/cp2_v2
```

The output is **aggregate-only** and saved privately to
`10_evidence_v2_offline/cutoff_sensitivity_aggregate.json`.
Only share the printed JSON, not any underlying GPS/identities.
No AWS EC2, new Stay Point Detection or full EDA rerun is needed.

**Acceptance:** The 70% row should match earlier Stage10f/10i
aggregates (44 TRAIN emitted, 43 FUTURE-time-observable,
31 FUTURE-unique-spatial-observable, 25 exact-anchor recurrences,
12 spatially unresolved); if these numbers diverge, halt and
investigate version/cache/protocol differences before interpreting
other cutoffs. The 60% and 80% rows are *new* and must not
be predicted, invented or treated as independent trials.


## Stage 10j — Measured multi-cutoff observability sensitivity (2026-10-15)

Operator-reported real Modal execution PASSED with exact Stage10i parity at 70%.
The shared 114 TRAIN-stay users across splits do **not** constitute independent replicates.

| TRAIN/FUTURE | emitted | future time | unique spatial | same TRAIN anchor | unresolved |
| --- | ---: | ---: | ---: | ---: | ---: |
| 60/40 | 40 | 40 | 34 | 27 | 6 |
| 70/30 | 44 | 43 | 31 | 25 | 12 |
| 80/20 | 43 | 40 | 29 | 21 | 11 |

HOME recurrence among spatially assessable: 19/22, 17/21, 16/20;
OFFICE: 8/12, 8/10, 5/9. Denominators and candidate identities change.
These are retrospective strict anchor-recurrence diagnostics, **not** HOME/OFFICE
semantic accuracy, independently validated probabilities or evidence v2 gains.
Do not modify deployed CP2 (full-period 27 HOME/16 OFFICE), v1 scoring or AWS.

## Stage 10k — Paired anchor identity & common FUTURE sensitivity (implementation)

`analysis/10k_paired_anchor_common_future_audit.py` refits the **unchanged**
complete-link 200m CP2 on per-user 60/70/80 TRAIN folds. It hard-fails unless
all three results exactly reproduce the existing private Stage10j aggregate.
For 60→70, 70→80, and 60→80:
- Compare candidate emission transitions on the same `(user_id, label)` keys.
  Do not equate `location_id` integers across independently clustered folds.
- For candidates emitted at both cutoffs, compute all pairwise distances between
  TRAIN cluster members: all <=200m = strictly compatible; all >200m = fully
  separated; partial overlap = uncertain. This is operational geometry, not
  an independently verified semantic location identity.
- Project exactly the later cutoff's FUTURE stays into **both** frozen TRAIN
  location models (same per-user future dates, time-window definition and
  GPS observations). Verify UTC-stay multiset nesting, no future refit, and
  identical time-window opportunity counts per user-label.
- Report common-FUTURE time observability, unique spatial opportunity in each
  model, one/both/neither spatial support, conditional recurrence discordance
  for strictly compatible clusters, and unmatched/ambiguous relevant-window
  overlap categories for spatially unresolved candidates. Do not interpret
  unmatched alone as proof of new travel or spatial error; it is unresolved.
- Keep private user-label paired diagnostics inside the trusted Modal Volume
  at `10_evidence_v2_offline/paired_anchor_common_future_private.pkl`.
  The only shareable artifact is
  `10_evidence_v2_offline/paired_anchor_common_future_aggregate.json`.
  Some label-level cells may be small: do not publish user-row results.

**Running on existing Modal Jupyter checkout** (after updating branch):
```bash
PYTHONPATH=/tmp/geolife-evidence-v2-stage10a/src \
python /tmp/geolife-evidence-v2-stage10a/analysis/10k_paired_anchor_common_future_audit.py \
  --stays-cache /mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl \
  --cache-root /mnt/geolife-data/cache/cp2_v2
```

Requires Stage10j aggregate JSON in trusted Modal Volume, same pinned
dependencies including `timezonefinder==9.0.0`. Synthetic-only test:
`pytest -q tests/test_evidence_v2_paired_anchor_common_future.py`.
No CP1 rerun, future GPS fit, evidence score redesign, semantic accuracy
assertion, production/AWS changes, or promotion of v2 tiers. Results pending
actual private Modal execution.
