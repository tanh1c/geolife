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
