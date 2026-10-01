# Stage 05c handoff

## Runnable artifact

Use the self-contained notebook artifact:

- 05c_stable_secondary_independent_evidence.ipynb

It injects the exact 05c analysis helper into the temporary cloned repository at runtime, so execution does not depend on a remote helper commit.

## Prerequisite

Run Stage 05b first. The Modal Volume must contain:

- /mnt/geolife-data/cache/05b_home_consensus_adaptive_work/home_consensus_private.pkl
- /mnt/geolife-data/cache/05b_home_consensus_adaptive_work/adaptive_work_patterns_42_private.pkl

Primary upstream parity:

- stable_secondary_anchor users = 9.

The notebook stops if this count changes.

## Primary evidence

For each stable-secondary user, compare the persistent secondary anchor with same-user recurring non-HOME peers on:

- weekday_weekend_visit_contrast;
- home_pair_transition_day_share;
- arrival_hour_concentration;
- dwell_regularity_score.

Primary peer eligibility:

- at least 3 active days;
- at least 2 stays.

At least one peer is required for a fair within-user comparison.

## Outputs

Private:

- anchor_metrics_private.pkl
- candidate_comparison_private.pkl

Aggregate:

- metric_summary.csv
- convergence_summary.csv
- decision_snapshot.csv
- paired_bootstrap_summary.csv
- static_office_stratified_evidence.csv
- support_sensitivity.csv

Cache root:

- /mnt/geolife-data/cache/05c_stable_secondary_evidence/

## Interpretation

Do not turn a 3+ axis result into an OFFICE label automatically.

A positive result means only that the selected persistent non-HOME anchor also exhibits stronger commute-like / schedule-regular behavior than the user's other recurring non-HOME anchors.

A negative or mixed result means the Stage-05b persistence signal should remain descriptive rather than semantic.

## Measured result — 2026-10-01

Upstream parity remained nine stable-secondary users. Seven had at least one eligible recurring non-HOME peer under the primary >=3-active-day comparator rule; median peer count was four.

Axis summary:

- weekday_weekend_visit_contrast: top-1 for 5/7; median candidate-minus-peer-median +0.198;
- home_pair_transition_day_share: top-1 for 3/7; median difference +0.102;
- arrival_hour_concentration: top-1 for 0/7; median difference -0.181;
- dwell_regularity_score: top-1 for 0/7; median difference -0.092.

Convergence:

- 0 users with >=3 top-1 evidence axes;
- 1 user with exactly 2;
- 6 users with 0-1;
- 3 users beat the peer median on >=3 axes, but that weaker criterion did not produce top-rank convergence.

All four paired-bootstrap 95% intervals crossed zero.

Comparator-support sensitivity:

- >=2 active days: 9 users, 0 with >=3 top axes;
- >=3 active days: 7 users, 0 with >=3 top axes;
- >=5 active days: 3 users, 1 with >=3 top axes.

Decision: close semantic WORK/OFFICE expansion. Keep stable_secondary_anchor descriptive only. If the project continues beyond Stage 05, move to routine/habit or behavior-change questions that do not require workplace ground truth.
