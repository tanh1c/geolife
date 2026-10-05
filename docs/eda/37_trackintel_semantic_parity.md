# Stage 07m — Trackintel semantic-only parity

## Purpose

Stage 07m evaluates the frozen CP2-v2 HOME/OFFICE heuristic against an
independent open-source implementation without changing stay detection or
spatial location identity.

Primary comparison:

```text
frozen 5,821 CP1 stays
        |
CP2-v2 per-stay IANA timezone
        |
complete-link 200 m production locations
        |
same location_id namespace
        |
Trackintel 1.4.2 location_identifier
  - FREQ
  - OSNA
  - pre_filter=False
        |
candidate-identity comparison
```

This is a methodological comparator, not a replacement model and not a
threshold-selection stage.

## Why semantic-only first

An end-to-end Trackintel pipeline would change at least three components at
once:

1. staypoint extraction;
2. spatial location clustering;
3. HOME/WORK semantic selection.

That is useful later, but it cannot isolate the source of disagreement.

Stage 07m holds the first two components fixed. Therefore an exact
location-identity disagreement is attributable primarily to the semantic
selection rule rather than a different stay inventory or location namespace.

## Trackintel version and methods

The notebook pins:

```text
trackintel==1.4.2
```

Trackintel documents:

- `FREQ`: select the most visited location as home and the second as work;
- `OSNA`: use weekday rest/work/leisure timeframes, combining rest/leisure
  for home and using the work timeframe for work.

The production comparison calls:

```python
ti.analysis.location_identifier(..., method="FREQ", pre_filter=False)
ti.analysis.location_identifier(..., method="OSNA", pre_filter=False)
```

The native Trackintel pre-filter is disabled deliberately. Its default support
thresholds would add an eligibility experiment on top of the semantic-rule
comparison.

References:

- Trackintel documentation:
  https://trackintel.readthedocs.io/en/latest/modules/analysis.html
- Martin et al. (2023), Trackintel:
  https://doi.org/10.1016/j.compenvurbsys.2023.101938

## Frozen reproduction gates

Before calling Trackintel, the notebook must reproduce:

- 5,821 CP1 stays;
- 136 users with stays;
- 2,015 CP2-v2 semantic locations;
- 716 recurring locations;
- 104 users with recurring locations;
- 27 production HOME emissions;
- 16 production OFFICE emissions.

A failure here invalidates the comparator.

## Per-stay timezone adapter

CP2-v2 allows every stay to carry its own IANA timezone. Trackintel expects
timezone-aware pandas datetimes in a common dtype.

The adapter therefore encodes each stay's local arrival wall clock as a
timezone-aware dummy UTC timestamp and preserves true elapsed `duration_s`
when constructing the endpoint.

Example conceptually:

```text
2009-01-05 09:00 Asia/Shanghai
        |
local wall clock
        v
2009-01-05 09:00 UTC   # semantic-clock carrier only
```

The encoded value must not be interpreted as physical UTC time.

`finish_wall_delta_s` audits any difference between exact local departure
wall time and start + true elapsed duration, most notably possible DST
transitions.

This adapter preserves the production question relevant to OSNA: local
weekday/time-of-day behavior.

## Primary outputs

Aggregate:

- `production_parity.csv`;
- `adapter_diagnostics.csv`;
- `agreement_summary.csv`;
- `status_distribution.csv`;
- `office_reference_summary.csv`;
- `home_reference_summary.csv`;
- `trackintel_cross_method_summary.csv`;
- `near_miss_work_summary.csv` when Stage-07j artifacts are available.

Private:

- `trackintel_candidates_private.pkl`;
- `production_trackintel_comparison_private.pkl`;
- `trackintel_cross_method_private.pkl`;
- `near_miss_trackintel_work_private.pkl` when available.

Cache root:

```text
/mnt/geolife-data/cache/cp2_v2/07m_trackintel_semantic_parity/
```

## Comparison states

For each method, user and label:

- `both_same`: production and Trackintel select the same location;
- `both_different`: both select a candidate but identities differ;
- `production_only`: production emits and Trackintel does not;
- `comparator_only`: Trackintel selects while production abstains;
- `neither`: neither emits/selects.

These are agreement and coverage diagnostics, not accuracy classes.

## Stage-07j near-miss view

When the Stage-07j private audit panel is available, the notebook tests whether
Trackintel selects the exact one-step near-miss candidate as WORK.

This view is diagnostic only.

A Trackintel WORK match does not promote a near-miss candidate and does not
reopen the Stage-07l decision. The frozen robustness evidence remains primary:

- recurrence;
- split-half;
- held-out persistence;
- dropout;
- BCL;
- historical imagery.

## Decision boundary

Stage 07m does not tune production thresholds.

Useful findings include:

- high HOME agreement but lower OFFICE agreement;
- many Trackintel WORK selections where production abstains;
- candidate-identity disagreement even under the same location namespace;
- strong or weak FREQ/OSNA internal agreement.

The interpretation is methodological convergence / disagreement, never
semantic accuracy, because GeoLife has no direct HOME/OFFICE ground truth.

The next independent stage may run Trackintel end to end with its own staypoint
generation and DBSCAN location generation, but that experiment must be called a
pipeline comparator rather than semantic parity.
