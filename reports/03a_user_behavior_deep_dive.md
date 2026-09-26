# User behavior deep dive

## Status
Run status: complete. This exploratory EDA uses aliases and aggregate outputs only.

## Evidence boundaries
No occupation labels, semantic POI labels, precise coordinates, raw identifiers, raw timestamps, or validation-label claims are reported.

## Executive summary
The release reconciliation retained 5,821 stays from 136 users in a 182-user universe; frozen-v1 emitted 27 HOME and 16 OFFICE comparator outputs (`artifacts/03a/summary.json`).

## Coverage
Release users: 182; no CP1 stay: 46; users with CP1 stays: 136; schedule-supported users: 46; stay-users failing schedule support: 90. Median coverage was 23.0 active days and 13.5 usable temporal days (`artifacts/03a/summary.json`; `artifacts/03a/figures/coverage.png`).

## Schedule calibration
Supported within-user weekly JSD had median 1.000 (IQR 0.652–1.000), versus between-user 0.904 and shuffled-week null 1.000. These distributions calibrate personal structure; they do not set a universal stability threshold (`artifacts/03a/summary.json`).

## Heterogeneity
Among 136 users with CP1 stays, 200 m anchor classes were 19 dominant, 13 two-anchor, 72 multiple-anchor, and 32 without a stable anchor; 46 release users had no detected CP1 stay (`artifacts/03a/summary.json`).

## Schedules
The calibrated supported within-user weekly JSD median was 1.000, versus between-user 0.904 and shuffled-week null 1.000; 23 supported users had repeatable peaks outside frozen comparison windows. The current JSD check does not establish personalized schedule structure (`artifacts/03a/summary.json`).

## Mobility
Across usable temporal-profile days, median cleaned-point distance was 28.5 km/day (IQR 17.6–54.0), movement-duration proxy was 2.3 h/day, and boundary count was 4.7/day. Lifetime totals remain 529.2 km and 34.9 h; all are cleaned-point proxies, not stay-to-stay travel (`artifacts/03a/summary.json`).

## Candidate overlap
Of 23 mobile-work-like candidates, 23 also had multiple anchors, 2 had repeatable usable-day motifs, 0 emitted frozen OFFICE, and 23 abstained. This is a behavioral overlap audit, not a new semantic rule (`artifacts/03a/summary.json`; `artifacts/03a/candidate_overlap.csv`).

## Extreme-pattern challenge
The independent top-decile challenge identified 26 behavioral extremes, of which 0 were coherent across independent repeatability evidence, 26 had quality-boundary evidence, and 26 remained for review. It challenges rather than replaces the existing outlier wrapper (`artifacts/03a/summary.json`; `artifacts/03a/behavioral_extreme_audit.csv`).

## Abstentions
Comparator gates were HOME [emitted=27, insufficient_relevant_dates=25, no_behavioral_window_overlap=13, no_cp1_stay=46, no_recurring_location=24, outside_frozen_v1_geographic_scope=39, share_below_frozen_gate=8] and OFFICE [emitted=16, insufficient_relevant_dates=31, margin_below_frozen_gate=2, no_behavioral_window_overlap=15, no_cp1_stay=46, no_recurring_location=24, outside_frozen_v1_geographic_scope=39, share_below_frozen_gate=9], with one ordered reason per label and release user (`artifacts/03a/summary.json`; `artifacts/03a/baseline_user_audit.csv`).

## Shifted candidates
2 users met the supported descriptive shifted-candidate wrapper; 122 had a shifted peak before support filtering. Neither count is an occupation or semantic label (`artifacts/03a/summary.json`).

## Mobile-work-like candidates
23 users met the supported mobile-work-like wrapper; it is exploratory supporting evidence only (`artifacts/03a/summary.json`).

## Outlier reinterpretation
The aggregate separates 170 data-quality boundary cases from 0 rare-but-coherent patterns; 1 aggregate audit rows retain a manual-review condition (`artifacts/03a/summary.json`; `artifacts/03a/outlier_audit.csv`).

## POI feasibility
104 users had at least one recurring anchor and 35 had a motif occurring on at least half of usable motif days. This supports recurrence feasibility only, not category, favorite, or recommender claims (`artifacts/03a/summary.json`).

## Cases
The private case set contains deterministic aliases only. Each alias figure combines temporal histogram, weekday-hour dwell heatmap, top `L*` dwell shares, daily distance/proxy, and daily motifs; it is private and non-map-based (`artifacts/03a/figures/case_a.png`; `artifacts/03a/case_studies.csv`).

## Baseline gaps
Location sensitivity was: 100 m: 715 recurring locations; 200 m: 716 recurring locations; 300 m: 710 recurring locations; all values are exploratory threshold sensitivity, not new production rules (`artifacts/03a/summary.json`).

## Open questions
52 users were sparse or insufficient while 0 showed rare coherent patterns, so non-emission cannot be reduced to one behavioral explanation (`artifacts/03a/summary.json`).

## Q1
How heterogeneous are anchors? Among 136 users with CP1 stays, the 200 m distribution is 19/13/72/32 across dominant/two/multiple/no-stable classes; 46 release users had no detected CP1 stay (`artifacts/03a/summary.json`).

## Q2
Is schedule evidence well supported? 46 users met all support gates; the calibrated within-user weekly JSD median was 1.000, versus between-user 0.904 and shuffled-week null 1.000. Current JSD evidence does not establish personalized schedule structure (`artifacts/03a/summary.json`; `artifacts/03a/figures/coverage.png`).

## Q3
Do repeated non-window patterns exist? 23 supported users had repeatable non-window peaks; this is descriptive schedule evidence, not a replacement label (`artifacts/03a/summary.json`).

## Q4
Are abstentions sparse or coherent? 52 are sparse/insufficient and 0 are rare-but-coherent, preserving both explanations (`artifacts/03a/summary.json`).

## Q5
Are shifted or mobile candidates present? 2 stable shifted and 23 mobile-work-like candidates meet their separate descriptive wrappers (`artifacts/03a/summary.json`).

## Q6
What anchor evidence is available for feasibility? 104 users have recurring anchors; 32 stay-bearing users lack one and 46 release users have no CP1 stay. Only recurrence, dwell, and temporal regularity are measured (`artifacts/03a/summary.json`).

## Q7
Which comparator gates dominate? HOME [emitted=27, insufficient_relevant_dates=25, no_behavioral_window_overlap=13, no_cp1_stay=46, no_recurring_location=24, outside_frozen_v1_geographic_scope=39, share_below_frozen_gate=8] and OFFICE [emitted=16, insufficient_relevant_dates=31, margin_below_frozen_gate=2, no_behavioral_window_overlap=15, no_cp1_stay=46, no_recurring_location=24, outside_frozen_v1_geographic_scope=39, share_below_frozen_gate=9] retain every observed gate count in the ordered audit (`artifacts/03a/summary.json`; `artifacts/03a/baseline_user_audit.csv`).

## Q8
Can rare patterns be separated from quality events? 0 repeatable rare patterns are separated from 170 boundary-quality cases (`artifacts/03a/summary.json`; `artifacts/03a/outlier_audit.csv`).

## Q9
What do private cases add? The deterministic case set provides 20 alias-only visual audits with the required five compact evidence views, without raw identifiers or coordinates (`artifacts/03a/summary.json`; `artifacts/03a/figures/case_a.png`).

## Q10
What limits POI conclusions? 35 users have repeatable motifs on usable motif days, but no enrichment, categories, favorites, or recommendations were queried or inferred (`artifacts/03a/summary.json`).

## Next experiments
Preserve frozen CP1 and CP2 v1. First evaluate the ordered comparator reason counts against separately approved validation; then test schedule-window and recurrence sensitivity only among adequately supported users; finally, consider POI enrichment only after an approved privacy and evaluation design (`artifacts/03a/summary.json`).

## Final response
### Status
Complete exploratory release audit.

### Concerns
Private artifacts remain ignored and should not be published.
