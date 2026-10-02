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

## Measured result — 2026-10-02

Coverage is adequate for 6-day and 8-day blocks:

- 6 / 56: 49 pairs, 18 users;
- 6 / 84: 58 pairs, 21 users;
- 8 / 56: 26 pairs, 11 users;
- 8 / 84: 29 pairs, 11 users.

The 10-day settings remain under coverage at 15–18 pairs from 8 users.

Exact OD still behaves like a sparse sampling representation: chronological JSD is high, but only 0–6.7% of pairs exceed their support-matched random p95.

Primary-feature audit:

- active-location count / usable day fails rank stability in all settings;
- cleaned distance / usable day has strong rank stability for covered 6-day and 8-day settings but misses at least one other predeclared gate in every case;
- closest case: 6 / 56 cleaned distance passes coverage, rank stability and null calibration but has bootstrap-width / observed-IQR = 1.030 (>1.0);
- 6 / 84 and both 8-day cleaned-distance settings exceed the <=10% random-p95 gate by small margins.

Final decision table:

```text
all 6 configurations:
candidate_features = 0
candidate_primary_features = 0
stage07_ready = False
```

## Final handoff decision

Broad Stage 07 change detection is closed for GeoLife under this protocol.

Do not create another support-size sweep and do not relax readiness thresholds after observing these near-misses.

Future work may still use GeoLife for:

- descriptive routine mining;
- conditional analyses on strongly supported users/edges;
- case studies;
- external datasets with denser longitudinal sampling.

But a broad population-level within-user change detector is not supported by the audited GeoLife evidence.

