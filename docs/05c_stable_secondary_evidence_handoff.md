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
