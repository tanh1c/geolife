# GeoLife EDA plan — Checkpoint 1

## Purpose

The EDA is not just a descriptive report. It should produce evidence for later cleaning, stay-point detection, Home/Office inference, evaluation, and privacy decisions.

## Source expectations to verify from the actual files

The GeoLife v1.3 user guide reports 182 users and 73 users with transportation-mode labels. It also contains a useful inconsistency: the page-1 narrative states 17,621 trajectories, while the v1.3 comparison table states 18,670 trajectories and 24,876,978 points. The notebook must count the files/points directly rather than copying either number into measured results.

The guide documents:

- GPS points contain latitude, longitude, altitude, and time;
- PLT files have six header lines;
- timestamps are GMT/UTC;
- altitude `-777` means invalid;
- sampling rates vary across devices and users;
- most trajectories are densely sampled;
- data is concentrated in Beijing but includes other locations.

## EDA questions

1. **Inventory / imbalance** — How many trajectories and points does each user have? How long is each user's observation history?
2. **Schema quality** — Invalid coordinates, bad timestamps, duplicates, ordering problems, missing altitude.
3. **Sampling behavior** — Distribution of inter-point time gaps and whether sampling differs strongly by user/trajectory.
4. **Trajectory geometry** — Duration, traveled distance, spatial extent, and heavy-tail behavior.
5. **Movement/noise** — Segment distance and speed distributions, impossible jumps, duplicated timestamps, long gaps.
6. **Spatial coverage** — Global bounds, Beijing concentration, geographic outliers, and privacy-safe aggregate density.
7. **Temporal coverage** — Hour/day/week patterns and whether users have enough recurring history for Home/Office inference.
8. **Transport labels** — Which users/modes are labeled and whether labels can help diagnose movement without confusing them with Home/Office targets.
9. **Stay-point readiness** — What evidence should drive candidate distance/time thresholds?
10. **Privacy** — Which exploratory outputs are safe to retain or share?

## Method

Use a two-level analysis:

- **metadata/full scan:** iterate over every trajectory but reduce each file to one summary row, keeping memory bounded;
- **raw-point sample:** use a reproducible stratified sample for visual diagnostics rather than concatenating roughly 25M points into a single in-memory table.

The first notebook intentionally does not filter noise. We should inspect raw distributions before choosing thresholds.

## Outputs

Local-only generated artifacts:

- dataset inventory;
- trajectory-level summary;
- user-level summary;
- transport-mode summary;
- plots and observations.

Generated outputs are ignored by Git by default. Publish only reviewed aggregate findings, with dataset license and mobility-privacy concerns considered.

## Decisions that should follow EDA, not precede it

- coordinate validity policy;
- duplicate timestamp policy;
- speed threshold or movement-specific filtering policy;
- long-gap handling;
- timezone policy for behavioral time features;
- candidate stay-point distance/time thresholds;
- minimum user history required for Home/Office inference.
