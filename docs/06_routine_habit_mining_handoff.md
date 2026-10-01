# Stage 06 — Routine / Habit Mining handoff

## Status

Scaffold ready for Modal execution.

## Inputs

Private frozen Stage-03a caches:

- `stays_baseline_v1.pkl`;
- `cleaned_point_daily_metrics.pkl`.

No raw GeoLife rescan is required when those caches exist.

## Parity checks

The notebook stops if:

- CP1 stays != 5,821;
- stay-bearing users != 136;
- recurring-location users under the broader complete-link 200 m behavior representation != 104.

These checks protect scope comparability.

## Primary outputs

Private:

- `day_sequences_private.pkl`;
- `transitions_private.pkl`;
- `edge_summary_private.pkl`;
- `user_summary_private.pkl`;
- `split_half_private.pkl`.

Aggregate:

- routine coverage;
- departure-time mode summary;
- split-half stability;
- recurrence/concentration sensitivity.

## Questions to answer after execution

1. How many users have repeated directed OD edges?
2. How much coverage is gained over exact full-day motif repeatability?
3. How regular are repeated-edge departure times?
4. How often is more than one departure-time mode selected?
5. Does the dominant directed edge repeat across first/second halves?
6. Are these conclusions robust to 2/3/5 repeat-day definitions?

## Interpretation boundary

Stage 06 can support claims about recurring mobility structure and temporal habits.

It cannot support:

- workplace semantics;
- occupation inference;
- semantic accuracy.

If coverage and split-half stability are adequate, Stage 07 may build sliding-window behavioral representations for change detection.
