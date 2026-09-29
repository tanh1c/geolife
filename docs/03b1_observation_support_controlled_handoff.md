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
