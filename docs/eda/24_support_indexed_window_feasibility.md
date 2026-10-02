# Stage 06d — Support-indexed window feasibility

## Why 06d exists

Measured Stage 06c showed that fixed calendar windows are a poor support unit for GeoLife:

- 28d / 42d / 56d eligible windows contain only median 8 / 8 / 9 usable days;
- users with adjacent eligible windows fall 11 / 9 / 7 as calendar span increases;
- coarse features can be more stable than exact OD, but coverage remains below the predeclared Stage-07 gate.

06d changes the window construction, not the statistical acceptance rules.

## Question

> If each window contains the same number of usable observations, can GeoLife provide enough independent longitudinal coverage and stable coarse features to justify Stage 07?

## Support-indexed windows

Primary usable-day block sizes:

- 6 days;
- 8 days;
- 10 days.

Blocks are non-overlapping and chronological within each user.

Calendar-span sensitivity:

- maximum 56 elapsed calendar days;
- maximum 84 elapsed calendar days.

A complete k-day block whose first-to-last usable day exceeds the cap is rejected.

Adjacent comparisons require consecutive block indices. The audit never bridges over a rejected block.

## Representation

Reuse the Stage-06c feature family unchanged so the window experiment does not also become a feature-retuning experiment.

Primary features, declared from the measured 06c result:

- cleaned distance per usable day;
- active-location count per usable day.

Secondary features remain in the audit:

- transition count per usable day;
- edge entropy and normalized entropy;
- top-edge share;
- repeated-edge count;
- departure-time concentration;
- movement-duration proxy;
- coarse departure-time bins.

Exact-edge JSD remains a baseline comparator, not a candidate backbone.

## Null and uncertainty protocol

For every adjacent eligible k-day block pair:

1. compute chronological feature difference;
2. pool the 2k usable days;
3. repeatedly draw balanced random k-vs-k partitions;
4. compare chronological difference with the random p95;
5. bootstrap days inside each block for feature uncertainty.

This preserves the Stage-06c logic while equalizing observation count by construction.

## Predeclared readiness gates

A feature/configuration is a Stage-07 candidate only if all hold:

- comparable adjacent pairs >=20;
- unique users >=10;
- test-retest Spearman >=0.50;
- chronological difference above random p95 for <=10% of pairs;
- median bootstrap CI95 width / observed IQR <=1.0.

The unique-user guard prevents a few long-history users from creating many pairs and masquerading as population coverage.

A configuration is Stage-07 ready only if at least one **primary** feature passes all gates.

Do not lower these gates after seeing 06d output.

## Stop rule

If at least one support/cap configuration passes the primary-feature readiness rule:

- freeze the support-window representation;
- proceed to Stage 07 change detection.

If no configuration passes:

- stop broad within-user change detection on GeoLife;
- record the limitation as longitudinal data density rather than detector failure;
- do not continue tuning window sizes until a setting passes.

No HOME/OFFICE semantics or production inference are changed by 06d.

## Measured result — 2026-10-02

### Coverage

| support days | max span | eligible blocks | adjacent pairs | users with adjacent pair |
|---|---:|---:|---:|---:|
| 6 | 56d | 84 | 49 | 18 |
| 6 | 84d | 98 | 58 | 21 |
| 8 | 56d | 49 | 26 | 11 |
| 8 | 84d | 55 | 29 | 11 |
| 10 | 56d | 29 | 15 | 8 |
| 10 | 84d | 36 | 18 | 8 |

Support-indexing resolves the Stage-06c pair-coverage limitation for the 6-day and 8-day settings. The 10-day settings remain below both the >=20-pair and >=10-user population gates.

### Exact OD baseline

| support days | max span | chronological JSD | random JSD | chronological > random p95 |
|---|---:|---:|---:|---:|
| 6 | 56d | 1.000 | 0.846 | 2.0% |
| 6 | 84d | 1.000 | 0.899 | 1.7% |
| 8 | 56d | 0.842 | 0.812 | 0.0% |
| 8 | 84d | 1.000 | 0.846 | 3.4% |
| 10 | 56d | 0.725 | 0.728 | 6.7% |
| 10 | 84d | 0.949 | 0.778 | 5.6% |

Exact OD remains strongly identity-sensitive, but temporal ordering rarely exceeds the support-matched random null.

### Primary features

Active-location count / usable day does not reach the 0.50 rank-stability gate in any configuration. Spearman ranges from -0.026 to 0.434.

Cleaned distance / usable day is more stable:

| support days | max span | pairs / users | Spearman | chronological > random p95 |
|---|---:|---:|---:|---:|
| 6 | 56d | 49 / 18 | 0.712 | 6.12% |
| 6 | 84d | 58 / 21 | 0.697 | 10.34% |
| 8 | 56d | 26 / 11 | 0.696 | 11.54% |
| 8 | 84d | 29 / 11 | 0.737 | 10.34% |
| 10 | 56d | 15 / 8 | 0.575 | 20.00% |
| 10 | 84d | 18 / 8 | 0.692 | 11.11% |

The nearest pass is 6d / 56d cleaned distance: it passes coverage, rank stability, and null calibration, but bootstrap-width / observed-IQR is 1.030, slightly above the predeclared <=1.0 gate.

The 6d / 84d cleaned-distance setting passes coverage, rank stability and bootstrap precision, but its 10.34% random-p95 exceedance is just above the <=10% null-calibration gate.

The 8-day cleaned-distance settings also exceed the null-calibration boundary.

### Final readiness

Every support/cap configuration reports:

```text
candidate_features = 0
candidate_primary_features = 0
stage07_ready = False
```

No feature in the full Stage-06c representation family passes every predeclared gate.

## Final decision

Stage 06d is the stop gate.

Do not implement a broad population-level Stage 07 behavioral change detector on GeoLife.

The evidence now distinguishes two issues:

1. fixed calendar windows were indeed causing a coverage problem;
2. support-indexed windows repair that problem, but the available longitudinal behavior features still do not jointly satisfy stability, null-calibration and uncertainty requirements.

Therefore the limiting factor is no longer merely window construction. Under the current audited representation, GeoLife does not support a general within-user change-detection claim.

Do not add more support sizes or relax thresholds post hoc.

