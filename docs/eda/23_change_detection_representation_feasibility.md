# Stage 06c — Change-detection representation feasibility

## Question

Stage 06b established that exact OD identities are sparse enough that chronological instability is mostly indistinguishable from random support instability. Before implementing Stage 07, 06c tests whether a coarser representation is measurable at useful calendar-window support.

## Representation principle

The target is not to preserve exact place identity. The target is to preserve behaviorally meaningful structure while reducing sensitivity to whether a particular exact OD edge happened to be observed in a sparse window.

The feature family combines support/coverage, mobility magnitude, route complexity, recurrence strength, and temporal regularity. Movement metrics remain cleaned-point proxies.

## Windows

Primary window sizes are 28 / 42 / 56 calendar days. A window is eligible for stability analysis with at least 6 Stage-06 usable days.

## Null calibration

A chronological difference alone is not evidence of behavior change.

For each adjacent pair, pool the usable days from both windows, randomize their assignment while preserving left/right usable-day counts, and recompute feature differences.

Interpretation:

- chronological difference similar to random null: sparse support can explain it;
- chronological difference above random p95: drift-like signal worth further investigation;
- strong test-retest rank correlation plus low null exceedance: better candidate backbone for Stage 07.

## Bootstrap uncertainty

Each eligible window is bootstrapped by usable day. Feature CI width is compared with observed spread. Wide intervals warn that an apparently smooth coarse feature is still under-supported.

## Exact OD baseline

Exact-edge JSD remains as a baseline comparator. 06c succeeds only if at least some coarse features have materially better support/stability characteristics.

## Decision boundary

Do not build Stage 07 merely because a coarse feature looks intuitive. Proceed only after measured 06c output shows a subset with adequate coverage, useful test-retest stability, null-calibrated behavior, and tolerable bootstrap uncertainty.

## Measured result — 2026-10-01

### Calendar-window coverage

| window | eligible windows | users with eligible window | users with adjacent pair | adjacent pairs | median usable days |
|---|---:|---:|---:|---:|---:|
| 28d | 43 | 24 | 11 | 16 | 8 |
| 42d | 48 | 31 | 9 | 15 | 8 |
| 56d | 48 | 35 | 7 | 11 | 9 |

Longer calendar windows increase the number of users with at least one eligible window, but they reduce adjacent comparable users and add almost no median usable-day support.

### Exact OD baseline

| window | median chronological JSD | median random JSD | chronological > random p95 |
|---|---:|---:|---:|
| 28d | 0.942 | 0.876 | 0.0% |
| 42d | 1.000 | 0.857 | 0.0% |
| 56d | 1.000 | 0.894 | 9.1% |

Exact-edge identity therefore remains dominated by sparse support rather than clean temporal structure.

### Best coarse candidates

The strongest practically interpretable candidate is cleaned movement distance per usable day:

| window | Spearman | chronological > random p95 | bootstrap width / observed IQR |
|---|---:|---:|---:|
| 28d | 0.812 | 12.5% | 0.841 |
| 42d | 0.729 | 6.7% | 0.814 |
| 56d | 0.782 | 18.2% | 0.888 |

Active-location count per usable day is also promising at 42d:

- Spearman = 0.540;
- chronological > random p95 = 0%;
- bootstrap width / observed IQR = 0.866.

Three combinations pass every provisional non-coverage gate:

- 28d time_00_06_share;
- 42d active_location_count_per_usable_day;
- 42d cleaned_distance_km_per_usable_day.

The 28d 00–06 share is treated cautiously because zero median difference and zero bootstrap-width indicate a sparse / degenerate feature can satisfy stability gates trivially.

### Readiness decision

All 45 feature × window combinations have `candidate_for_stage07 = False`.

The decisive common failure is coverage: the predeclared gate requires at least 20 comparable adjacent pairs, while the maximum observed count is 16.

Do not lower that threshold after observing the output.

Stage 07 remains blocked.

### Next experiment

Fixed calendar windows appear to be the wrong support unit for GeoLife. The next feasibility stage should hold usable observation count approximately fixed:

- 6 / 8 / 10 usable-day windows;
- sensitivity calendar-span caps of 56 / 84 days;
- same coarse feature set;
- same adjacent-window test–retest;
- same support-matched random-partition null;
- same bootstrap uncertainty audit.

If support-indexed windows still cannot provide adequate coverage and stability, the project should treat broad within-user behavioral change detection as unsupported by GeoLife's longitudinal density rather than continue tuning the detector.

