# 03b.1 Observation-support-controlled audit

## Purpose

03b found a robust 23-user mobile/distributed-mobility candidate cohort, but Group A had substantially denser observation support than matched Group B.

03b.1 asks one narrow question:

> After forcing each matched A/B pair to contribute the same amount of usable observation exposure, do the descriptive mobility and independent route differences persist?

This is a research-only confounding audit. It does not create a semantic work-role classifier.

## Frozen inputs

The audit must reproduce the 03b frozen parity before continuing:

```text
23 candidates
23 multiple-anchor
23 OFFICE-abstained
0 OFFICE-emitted
```

Frozen candidate membership and A/B matching logic are imported from 03a/03b and are not retuned.

## Exposure control

For each matched A/B pair:

- temporal analysis downsamples to equal usable-day counts;
- weekday and weekend counts are controlled separately;
- route analysis independently downsamples equal `usable_for_motif` days;
- 500 bootstrap repetitions are used by default;
- aggregate evidence is based on paired A-minus-B differences.

Primary route metrics:

```text
transitions per controlled day
distinct edges per controlled day
recurrent edges per controlled day
edge entropy
top edge frequency
```

Mobility metrics such as distance/day and movement-hours/day are retained only as descriptive confounding checks because they overlap with candidate construction.

## Transportation labels

For matched pairs where both users have sufficient transportation-label coverage:

- total matched labeled hours are equalized;
- distance/hour and mode-distance shares are recomputed;
- mode-transition counts are not used after segment resampling because temporal ordering is not preserved.

Transportation evidence remains auxiliary.

## Interpretation rule

03b.1 does not infer a new semantic class.

If at least two predeclared independent route metrics remain higher for Group A with a 95% bootstrap interval above zero, the report may conclude that richer observation alone does not fully explain the route-structure difference.

If all primary route intervals overlap zero, observation density remains a plausible explanation for much of the original difference.

Anything else is reported as mixed support-controlled evidence.

Even a persistent difference does not prove distributed/mobile work.

## Privacy

Private outputs remain ignored under `artifacts/03b1/` or the configured Modal Volume cache.

Public report:

```text
reports/03b1_observation_support_controlled_audit.md
```

must contain aggregate evidence only and no raw identifiers or coordinates.

## Stop rule

After the full run:

1. targeted tests;
2. full repository pytest;
3. targeted Ruff for 03b.1 files;
4. frozen parity;
5. public-report privacy checks;
6. evidence review.

Do not modify frozen Home/Office semantics or notebook 03 from this audit alone.

## Modal correction — local_weekday collision

The first full Modal attempt stopped before evidence generation with `KeyError: local_weekday` in `_day_edge_table()`.

Root cause: `clustered` and the daily eligibility frame both contained `local_weekday`; the merge produced suffixed columns. The route-day builder now joins only `user_id + local_date` for motif eligibility and derives weekday directly from the date. A regression test covers this exact collision.

No report or summary from the failed run is valid evidence.

## Runtime correction — vectorized bootstrap

The initial 500-repetition Modal attempt was interrupted after more than an hour with no output. The scientific protocol was not changed; execution was optimized.

Day bootstrap now prefilters pair-local frames outside the repetition loop. Transportation bootstrap precomputes NumPy arrays once per user and uses vectorized cumulative-duration sampling rather than rebuilding pandas frames per repetition. Stage and pair-level progress is printed so future stalls are diagnosable.

No evidence from the interrupted run is valid.

## Full-release result — 2026-09-29

The optimized Modal run completed successfully in about 3.1 minutes and passed targeted tests, full repository tests, targeted Ruff, frozen parity, and public-report privacy checks.

Measured result:

- all 23 matched pairs contributed controlled temporal days; median controlled exposure was 45 days;
- 22 pairs contributed controlled motif days; median controlled route exposure was 8 days;
- movement magnitude remained higher in Group A after exposure control: +22.88 km/day cleaned distance and +0.74 h/day movement-duration proxy;
- recurring-location count/day and stay count/day did not separate A/B;
- edge entropy remained higher in Group A (+0.232, 95% bootstrap interval [0.006, 0.455]);
- recurrent-edge count/day remained exactly 0 difference, and transition/day / distinct-edge/day intervals touched zero;
- only one matched pair had enough transportation-label coverage, so transportation evidence is not population-level.

Decision: the cohort remains a robust descriptive **mobility-complexity** cohort, but current independent evidence does not validate a distributed/mobile-work semantic class. The mobile-work hypothesis audit can be closed unless new independent semantic evidence becomes available.

