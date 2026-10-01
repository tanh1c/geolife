# Stage 05b handoff

## Run this notebook

- notebooks/05b_home_consensus_adaptive_work.ipynb

Analysis helper:

- analysis/05b_home_consensus_adaptive_work.py

## Prerequisite

Run Stage 05 first so the private cache contains:

- assignments_private.pkl;
- split_half_details_private.pkl;
- holdout_details_private.pkl;
- dropout_details_private.pkl.

Stage 05b reuses those tables rather than rerunning the whole reliability suite.

## HOME outputs

Private:

- home_consensus_private.pkl.

Aggregate:

- home_tier_summary.csv;
- home_production_summary.csv;
- home_vote_summary.csv;
- home_expansion_summary.csv;
- home_consensus_overview.csv.

Interpret HIGH/MEDIUM as multi-axis reliability tiers only.

Do not call them ground-truth HOME labels.

## Adaptive secondary-anchor outputs

Primary 42-day audit:

- adaptive_work_windows_42_private.pkl;
- adaptive_work_patterns_42_private.pkl;
- adaptive_work_pattern_summary_42.csv;
- adaptive_static_agreement_42.csv.

Sensitivity:

- adaptive_work_sensitivity.csv;
- adaptive_work_all_windows_private.pkl.

Decision snapshot:

- decision_snapshot.csv.

## Primary questions after execution

HOME:

- How many HIGH and MEDIUM winners exist?
- How many are already baseline-emitted?
- How many HIGH/MEDIUM cases would be new HOME expansion candidates?
- Are expansion candidates supported by split + held-out + dropout evidence, or mostly by method voting?

WORK-like:

- How many eligible users have a stable secondary anchor across 42-day windows?
- How many show multiple recurring secondary anchors?
- How many remain unstable or insufficient?
- Does the dominant adaptive secondary anchor agree with fixed-window OFFICE?
- Are stable counts robust across 28/42/56-day windows and 0.60/0.70/0.80 persistence thresholds?

## Important interpretation boundary

A stable secondary anchor means only that the same non-HOME recurring location repeatedly dominates sliding windows.

It does not establish:

- workplace semantics;
- occupation;
- employment status;
- semantic accuracy.

Do not change production HOME/OFFICE until the measured 05b outputs are reviewed.
