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

## Measured result — 2026-10-01

### HOME consensus

The executed audit produced 67 unique HOME vote winners: 21 HIGH, 4 MEDIUM and 42 UNCERTAIN.

Production relationship:
- HIGH: 20 baseline-emitted + 1 fixed candidate not emitted;
- MEDIUM: 3 baseline-emitted + 1 fixed candidate not emitted;
- UNCERTAIN unique winners: 1 baseline-emitted + 4 fixed candidates not emitted + 37 outside-fixed candidates.

Therefore only 2 HIGH/MEDIUM expansion candidates lie outside production HOME. Both are already fixed-window candidates; neither comes from the broad recurrence-only/outside-fixed set.

Interpretation:
- the 27-HOME production baseline is conservative but already captures most of the strongest consensus evidence;
- 23 of 27 production emissions are HIGH/MEDIUM unique winners;
- do not automatically add the two expansion candidates; keep them as targeted review candidates.

### Adaptive secondary-anchor audit

Primary 42-day / 14-day-step / 0.70 stability setting among 25 HIGH/MEDIUM HOME users:
- stable_secondary_anchor: 9;
- multi_anchor: 3;
- unstable: 1;
- insufficient: 12.

Static-method agreement for users with sufficient evidence:
- fixed-window OFFICE: 4/10 = 40.0%;
- HoWDe-style OFFICE: 2/7 = 28.6%;
- recurrence OFFICE: 6/11 = 54.5%.

Sensitivity at stability threshold 0.70:
- 28d: 10 sufficient / 6 stable;
- 42d: 13 sufficient / 9 stable;
- 56d: 14 sufficient / 10 stable.

At 42d and 56d, moving the persistence threshold from 0.70 to 0.80 leaves stable counts unchanged (9 and 10 respectively). This suggests the primary conclusion is not driven by a knife-edge 0.70 threshold, but the usable sample remains small.

### Handoff decision

Do not change production HOME/OFFICE from Stage 05b alone.

For HOME: baseline already captures nearly all HIGH/MEDIUM consensus cases; only two non-emitted cases merit focused review.

For WORK-like behavior: retain stable_secondary_anchor as a descriptive state only; do not equate it with OFFICE. If a follow-up is needed, test independent weekday/transition/arrival regularity inside the small stable-secondary subset.
