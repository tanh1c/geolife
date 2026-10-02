# Stage 06d handoff — Support-Indexed Window Feasibility

## Inputs

Reuse private derived artifacts only:

- Stage 06: day_sequences_private.pkl
- Stage 06: transitions_private.pkl
- Stage 03a: cleaned_point_daily_metrics.pkl

No raw GeoLife rescan is required.

## Primary grid

Usable-day blocks:

- 6
- 8
- 10

Calendar-span caps:

- 56 days
- 84 days

Blocks are chronological, non-overlapping, and contain exactly k Stage-06 usable days. A block over the span cap is ineligible. Adjacent analysis requires consecutive eligible block indices; rejected blocks are never skipped over.

## Primary features

- cleaned_distance_km_per_usable_day
- active_location_count_per_usable_day

All Stage-06c secondary features remain in the output for diagnostic comparison.

## Readiness gates

Keep the gates fixed before execution:

- >=20 comparable adjacent pairs;
- >=10 unique users;
- Spearman >=0.50;
- chronological > random p95 share <=0.10;
- bootstrap CI95 width / observed IQR <=1.0.

A support/cap configuration is ready for Stage 07 only if at least one primary feature passes every gate.

## Outputs to inspect

1. coverage
2. exact_od_baseline
3. test_retest
4. bootstrap_summary
5. readiness
6. decision

## Decision rule

If decision.stage07_ready is true for any configuration, freeze that representation before implementing Stage 07.

If all configurations are false, stop broad GeoLife within-user behavioral change detection as data-limited.

Do not add more window sizes or relax gates after seeing the result.

## Run artifact

Use:

notebooks/06d_support_indexed_window_feasibility.ipynb
