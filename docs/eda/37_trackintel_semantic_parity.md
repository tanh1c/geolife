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


## Measured result

Stage 07m was executed on `main` at `5e4b157` with
`trackintel==1.4.2`.

### Reproduction / adapter validation

All frozen gates passed:

- CP1 stays: 5,821;
- users with stays: 136;
- semantic stays: 5,821;
- semantic locations: 2,015;
- recurring locations: 716;
- recurring-location users: 104;
- production HOME: 27;
- production OFFICE: 16.

The local-wall adapter also passed on all 5,821 rows:

- encoded users: 136;
- encoded locations: 2,015;
- non-zero finish-wall deltas: 0;
- maximum absolute finish-wall delta: 0 s.

Therefore the semantic comparator did not introduce a measured local-time /
elapsed-duration distortion on this frozen dataset.

### Trackintel coverage

With `pre_filter=False`:

| method | HOME selected | WORK selected |
| --- | ---: | ---: |
| FREQ | 136 | 117 |
| OSNA | 104 | 99 |

The broad Trackintel coverage is expected: this stage intentionally disables
Trackintel eligibility filtering so semantic selection can be separated from
production abstention.

### Production candidate identity agreement

| method | label | production emitted | comparator selected | jointly selected | exact matches | exact among joint |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| FREQ | HOME | 27 | 136 | 27 | 24 | 88.9% |
| OSNA | HOME | 27 | 104 | 27 | 27 | 100.0% |
| FREQ | OFFICE | 16 | 117 | 16 | 3 | 18.8% |
| OSNA | OFFICE | 16 | 99 | 15 | 11 | 73.3% |

For the frozen HOME-27 reference:

- FREQ exact: 24/27;
- OSNA exact: 27/27.

For the frozen OFFICE-16 reference:

- FREQ selects all 16 but exact-matches only 3/16;
- OSNA selects 15/16 and exact-matches 11/16;
- among the 15 jointly selected OFFICE users, 11/15 are exact and 4/15 select a
  different location;
- one production OFFICE user is not selected by OSNA.

### Trackintel internal agreement

Among user-label rows jointly selected by FREQ and OSNA:

- HOME: 68/104 same location = 65.4%;
- OFFICE: 31/93 same location = 33.3%.

This internal disagreement is important. Trackintel is useful as an independent
implementation comparator, but its methods do not define a unique semantic
ground truth, especially for WORK.

### Stage-07j near-miss WORK identity

Both Trackintel methods select WORK for all nine near-miss users.

Exact match to the frozen Stage-07j audited candidate:

| method | margin-near | share-near | total |
| --- | ---: | ---: | ---: |
| FREQ | 0/2 | 2/7 | 2/9 |
| OSNA | 1/2 | 5/7 | 6/9 |

OSNA therefore independently supports the semantic plausibility of many
share-near candidates. This does not change the Stage-07l policy result:
candidate plausibility is not the same as robustness. The near-miss cohort still
has weak recurrence/split/held-out convergence and no BCL work-compatible
support within 150 m.

### Interpretation

The semantic-only comparator supports three conclusions.

1. **HOME is strongly convergent.** Exact 27/27 OSNA agreement indicates that
   the frozen HOME ranking is highly consistent with an independent
   time-structured open-source heuristic once stays and locations are held
   fixed.

2. **OFFICE is method-sensitive.** OSNA gives meaningful convergence
   (11/16 exact), but FREQ is weak (3/16 exact), and FREQ-vs-OSNA WORK identity
   agreement is only 31/93.

3. **Production abstention is doing real work.** OSNA selects 99 WORK users and
   matches 6/9 near-miss candidates, whereas production emits only 16 OFFICE
   users. The production gate is therefore not merely reproducing a generic
   daytime heuristic; it is selecting a narrower evidence-supported subset.

### Decision

Keep the frozen production result:

- HOME = 27;
- OFFICE = 16.

Do not promote the nine Stage-07j near-miss candidates based on Trackintel
agreement alone.

Stage 07m is positive validation of the overall semantic-inference family,
especially for HOME, while simultaneously reinforcing the need for abstention
and robustness diagnostics for OFFICE.

The next Trackintel experiment, if run, should be an end-to-end pipeline
comparator that deliberately changes staypoint extraction and spatial
clustering. Its differences must be decomposed rather than interpreted as
semantic accuracy.
