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
