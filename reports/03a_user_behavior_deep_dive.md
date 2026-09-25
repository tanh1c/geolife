# User behavior deep dive

## Status
Run status: complete. This exploratory EDA uses aliases and aggregate outputs only.

## Evidence boundaries
No occupation labels, semantic POI labels, precise coordinates, raw identifiers, raw timestamps, or validation-label claims are reported.

## Executive summary
The release reconciliation retained 5,821 stays from 136 users in a 182-user universe; frozen-v1 emitted 27 HOME and 16 OFFICE comparator outputs (`artifacts/03a/summary.json`).

## Coverage
Observed-day and usable-day coverage are summarized privately, with 182 users represented in the behavior feature table (`artifacts/03a/summary.json`; `artifacts/03a/figures/coverage.png`).

## Heterogeneity
Anchor, dwell-share, entropy, and motif summaries are aggregate-only and are available in `artifacts/03a/summary.json` and `artifacts/03a/user_behavior_features.csv`.

## Schedules
Local-time dwell distributions and continuous schedule support are exploratory; eligible and insufficient counts are recorded in `artifacts/03a/summary.json`.

## Mobility
Cleaned-point distance and movement-duration proxies are reported separately from stay recurrence in `artifacts/03a/user_behavior_features.csv`.

## Abstentions
The frozen comparator funnel retains one ordered reason per label and release user in `artifacts/03a/baseline_user_audit.csv`; emission totals are reported in `artifacts/03a/summary.json`.

## Shifted candidates
2 users met the supported descriptive shifted-candidate wrapper; this is not an occupation or semantic label (`artifacts/03a/summary.json`).

## Mobile-work-like candidates
23 users met the supported mobile-work-like wrapper; it is exploratory supporting evidence only (`artifacts/03a/summary.json`).

## Outlier reinterpretation
Data-quality boundary events and repeatable behavioral rarity are separated in `artifacts/03a/outlier_audit.csv`.

## POI feasibility
Only recurrence, dwell, regularity, and temporal feasibility are measured; no POI enrichment, category, favorite, or recommender is inferred (`artifacts/03a/summary.json`).

## Cases
Private case mappings use deterministic aliases only in `artifacts/03a/case_studies.csv`; no case identities appear in this report.

## Baseline gaps
Location sensitivity was: 100 m: 715 recurring locations; 200 m: 716 recurring locations; 300 m: 710 recurring locations; all values are exploratory threshold sensitivity, not new production rules (`artifacts/03a/summary.json`).

## Open questions
Sparse observation remains distinct from irregular behavior; follow-up needs a separately approved validation design (`artifacts/03a/summary.json`).

## Q1
Exploratory answer: aggregate evidence is reported in `artifacts/03a/summary.json`; it is not a performance or ground-truth claim.

## Q2
Exploratory answer: aggregate evidence is reported in `artifacts/03a/summary.json`; it is not a performance or ground-truth claim.

## Q3
Exploratory answer: aggregate evidence is reported in `artifacts/03a/summary.json`; it is not a performance or ground-truth claim.

## Q4
Exploratory answer: aggregate evidence is reported in `artifacts/03a/summary.json`; it is not a performance or ground-truth claim.

## Q5
Exploratory answer: aggregate evidence is reported in `artifacts/03a/summary.json`; it is not a performance or ground-truth claim.

## Q6
Exploratory answer: aggregate evidence is reported in `artifacts/03a/summary.json`; it is not a performance or ground-truth claim.

## Q7
Exploratory answer: aggregate evidence is reported in `artifacts/03a/summary.json`; it is not a performance or ground-truth claim.

## Q8
Exploratory answer: aggregate evidence is reported in `artifacts/03a/summary.json`; it is not a performance or ground-truth claim.

## Q9
Exploratory answer: aggregate evidence is reported in `artifacts/03a/summary.json`; it is not a performance or ground-truth claim.

## Q10
Exploratory answer: aggregate evidence is reported in `artifacts/03a/summary.json`; it is not a performance or ground-truth claim.

## Next experiments
Review aggregate evidence before proposing any Home/Office/POI redesign; retain frozen CP1 and CP2 v1 unchanged until a separate decision (`artifacts/03a/summary.json`).

## Final response
### Status
Complete exploratory release audit.

### Concerns
Private artifacts remain ignored and should not be published.
