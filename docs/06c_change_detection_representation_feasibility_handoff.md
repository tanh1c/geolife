# Stage 06c handoff — Change-Detection Representation Feasibility

## Why 06c exists

Stage 06b showed that exact OD identity is too sparse to use directly as the Stage-07 change-detection backbone. Chronological exact-edge instability was extreme, but support-matched random partitions were similarly unstable.

06c therefore asks:

> Can coarser, support-normalized features produce enough calendar-window coverage and materially better test-retest behavior than exact OD identity?

## Inputs

Reuse private derived artifacts only; do not rescan raw GeoLife:

- Stage 06: day_sequences_private.pkl
- Stage 06: transitions_private.pkl
- Stage 03a: cleaned_point_daily_metrics.pkl

The Stage-06 usable-day universe remains the primary support universe. Point-day metrics are joined only to those dates.

## Window protocol

Evaluate non-overlapping calendar windows of 28, 42, and 56 days.

Primary minimum support is 6 Stage-06 usable days per window. Report coverage rather than hiding low-support windows.

For every adjacent eligible window pair, compare chronological differences with support-matched random partitions drawn from the same two-window day pool.

## Candidate representation

Window-level features include usable-day coverage, active locations, transition rate, edge entropy, normalized edge entropy, top-edge share, repeated-edge count, departure-time concentration, cleaned-point distance/day, movement-duration proxy/day, and four coarse departure-time bins.

Exact-edge JSD is retained only as a baseline comparator.

## Stability evidence

Inspect coverage, chronological test-retest Spearman correlation, median adjacent-window difference, support-matched random-partition difference, random-p95 exceedance share, and bootstrap 95% feature uncertainty.

The code emits a convenience candidate_for_stage07 flag using provisional gates. It is a screening aid, not a scientific conclusion.

## Privacy

User/window-level tables remain on the private Modal Volume. Public documentation should report aggregate coverage/stability only and must not expose raw user IDs or coordinates.

## Run artifact

Use notebooks/06c_change_detection_representation_feasibility.ipynb.

No production semantics, HOME/OFFICE inference, or change detector are modified by Stage 06c.

## Measured result — 2026-10-01

Calendar-window support:

- 28d: 16 adjacent eligible pairs from 11 users; median 8 usable days/window;
- 42d: 15 pairs from 9 users; median 8 usable days/window;
- 56d: 11 pairs from 7 users; median 9 usable days/window.

Exact OD remains sparse/noisy:

- chronological JSD medians = 0.942 / 1.000 / 1.000;
- random-partition JSD medians = 0.876 / 0.857 / 0.894;
- chronological above random p95 = 0% / 0% / 9.1%.

Best interpretable coarse evidence:

- 42d cleaned distance / usable day: Spearman 0.729, random-p95 exceedance 6.7%, bootstrap-width / observed-IQR 0.814;
- 42d active-location count / usable day: Spearman 0.540, random-p95 exceedance 0%, bootstrap ratio 0.866.

All 45 feature × window combinations remain below the Stage-07 readiness gate because no setting reaches the predeclared 20 comparable adjacent pairs. The threshold must not be lowered post hoc.

## Handoff decision

Do not implement Stage 07 yet.

Next evaluate support-indexed windows:

- 6 / 8 / 10 usable days;
- 56 / 84-day calendar-span cap sensitivity;
- same feature, null-calibration, test–retest and bootstrap protocol.

If that still fails coverage/stability, close broad GeoLife within-user change detection as data-limited rather than detector-limited.

