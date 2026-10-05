# Stage 08c — Exposure-aware policy experiment

## Purpose

Stage 08c tests predeclared, label-specific exposure-aware candidate rules
against the frozen production baseline:

```text
HOME = 27
OFFICE = 16
```

It is an experiment only. Production code and thresholds remain unchanged.

Stage 08b showed two exposure-related failure modes:

1. SPARSE users can be blocked by the absolute `min_dates=3` requirement;
2. DENSE/mobile users can have enough support but lower absolute share/margin
   because semantic mass is distributed across more locations.

The measured evidence also showed that HOME and OFFICE should not share one
adaptive rule.

## Branch A — SPARSE HOME support-aware rule

Sparse HOME still had substantial recurrence coverage in Stage 08b, unlike
sparse OFFICE.

The conservative rule changes only one production condition:

```text
absolute HOME support dates: 3 -> 2
```

and requires all of:

- HOME exposure regime = SPARSE;
- production failure mode = `min_dates_blocked`;
- exactly two observed HOME opportunity dates;
- raw top HOME candidate supported on both 2/2 dates;
- raw top HOME share >= 0.50;
- raw top HOME margin >= 0.20;
- recurrence selects the same location;
- candidate does not equal production OFFICE;
- user is not already production HOME.

Therefore sparse HOME does not receive relaxed share/margin.

Single-opportunity users are not eligible.

## Branch B — DENSE HOME concentration-aware rule

Stage 08a already produced five independently corroborated HOME_PROBABLE
candidates, and Stage 08b showed all five are DENSE.

Stage 08c does not search all dense users. It tests only the existing
HOME_PROBABLE set.

For dense users, absolute share/margin are replaced by relative top-vs-runner-up
concentration.

The threshold is derived from the frozen HOME boundary rather than selected
post-hoc:

```text
top share = 0.50
margin    = 0.20
runner-up = 0.30

relative dominance
= 0.50 / (0.50 + 0.30)
= 0.625
```

Candidate requirements:

- existing HOME_PROBABLE from Stage 08a;
- DENSE HOME exposure;
- fixed-window eligible top candidate matches the probable candidate;
- failure mode is share/margin concentration;
- relative top-2 dominance >= 0.625;
- no production-OFFICE collision.

This tests whether a concentration-normalized rule explains the validated
HOME expansion without broadly relaxing dense users.

## Branch C — DENSE OFFICE conservative rule

Sparse OFFICE is not relaxed because Stage 08b measured 0/38 candidate selection
under fixed-window, HoWDe-style, and recurrence.

Dense OFFICE testing is restricted to the nine Stage-07j one-step near misses.

The relative dominance threshold is derived from the frozen OFFICE boundary:

```text
top share = 0.30
margin    = 0.10
runner-up = 0.20

relative dominance
= 0.30 / (0.30 + 0.20)
= 0.60
```

The candidate pool requires:

- DENSE OFFICE exposure;
- near-miss candidate equals eligible fixed-window top candidate;
- relative top-2 dominance >= 0.60;
- no production-HOME collision;
- user is not already production OFFICE.

The stricter experimental OFFICE candidate additionally requires:

- dropout candidate retention >= 0.80; and
- at least one identity corroborator:
  - static comparator match; or
  - split-half candidate match; or
  - held-out top-1 candidate match.

This deliberately keeps OFFICE more conservative than HOME.

## Outputs

Private:

- `sparse_home_support_candidates_private.pkl`;
- `dense_home_concentration_candidates_private.pkl`;
- `dense_office_near_miss_candidates_private.pkl`.

Aggregate:

- `input_gate.csv`;
- `candidate_funnel.csv`;
- `office_robustness_summary.csv`;
- `policy_coverage_comparison.csv`;
- `policy_overlap_summary.csv`.

Cache root:

```text
/mnt/geolife-data/cache/cp2_v2/08c_exposure_aware_policy/
```

## Decision boundary

Stage 08c does not migrate production.

A candidate branch is useful only if it increases tiered coverage while
remaining tightly corroborated.

Any positive result remains a separate confidence/policy tier until additional
robustness review is complete.


## Measured result

The executed notebook ran successfully on `main` at `37cb1e8` with no
traceback.

### Input reproduction

| item | count |
| --- | ---: |
| production HOME | 27 |
| production OFFICE | 16 |
| HOME_PROBABLE from 08a | 5 |
| OFFICE near miss from 07j | 9 |
| 08b diagnostic rows | 272 |

### SPARSE HOME support-aware branch

The predeclared sparse rule emitted 4 candidates.

All four have:

- HOME exposure regime = SPARSE;
- exactly 2 observed HOME opportunity dates;
- raw top candidate support on 2/2 dates;
- raw top date coverage = 1.0;
- recurrence exact match;
- no production-OFFICE collision;
- original HOME share >= .50;
- original HOME margin >= .20.

Observed raw shares and margins:

| audit | raw share | raw margin |
| --- | ---: | ---: |
| SH01 | 1.000 | 1.000 |
| SH02 | .833 | .833 |
| SH03 | .872 | .872 |
| SH04 | 1.000 | 1.000 |

This is a narrowly exposure-normalized support relaxation, not a general
sparse-user threshold reduction.

### DENSE HOME concentration-aware branch

All 5/5 existing HOME_PROBABLE candidates pass relative dominance >= .625.

| audit | gate failure | share | margin | relative dominance | external exact families |
| --- | --- | ---: | ---: | ---: | ---: |
| DH01 | share+margin | .265 | .162 | .721 | 3 |
| DH02 | share+margin | .407 | .188 | .650 | 2 |
| DH03 | share | .453 | .312 | .763 | 2 |
| DH04 | share+margin | .277 | .187 | .755 | 3 |
| DH05 | share+margin | .187 | .187 | 1.000 | 3 |

Because the branch only searches the already-corroborated probable tier, this
result supports relative concentration as an explanation for dense HOME
dilution without demonstrating that the same rule should be applied to all dense
users.

### DENSE OFFICE branch

Relative-dominance pool:

```text
7 / 9 near misses
```

Robust subset:

```text
3 / 9 near misses
```

Aggregate robustness within the 7-user pool:

| metric | users |
| --- | ---: |
| static comparator >=1 | 4 |
| split match >=1 | 1 |
| held-out top-1 | 2 |
| dropout retention >= .80 | 4 |
| final robust rule | 3 |

The three final robust candidates all have dropout retention = 1.0 and at least
one additional identity corroborator.

### Candidate funnel

| branch | candidate users |
| --- | ---: |
| HOME_SPARSE_2OF2_RECURRENCE | 4 |
| HOME_DENSE_RELATIVE_DOMINANCE | 5 |
| OFFICE_DENSE_RELATIVE_POOL | 7 |
| OFFICE_DENSE_ROBUST_RELATIVE | 3 |

### Coverage comparison

| policy view | HOME | OFFICE | production changed |
| --- | ---: | ---: | --- |
| frozen baseline | 27 | 16 | no |
| tiered HOME: dense probable + sparse support | 36 | 16 | no |
| all experimental Stage-08c branches | 36 | 19 | no |

The +9 HOME are composed of:

- +5 existing Stage-08a HOME_PROBABLE candidates validated by relative
  dominance;
- +4 new sparse 2-of-2 support candidates.

The +3 OFFICE are a strict subset of the previously audited nine near misses.

### Interpretation

Stage 08c supports a label-specific exposure-aware design:

```text
SPARSE HOME
absolute support limitation
→ allow only strict 2-of-2 observed support
→ retain original share/margin
→ require recurrence identity

DENSE HOME
absolute concentration dilution
→ relative top-vs-runner-up dominance
→ restrict to corroborated HOME_PROBABLE tier

DENSE OFFICE
relative concentration can recover candidates
→ but requires dropout + identity corroboration
→ only 3/9 survive
```

### Decision

Do not migrate production from Stage 08c alone.

Keep:

```text
production HOME = 27
production OFFICE = 16
```

and retain exposure-aware additions as separate research/confidence tiers:

```text
tiered HOME coverage = 36
robust experimental OFFICE coverage = 19
```

The next validation should test persistence/robustness of the 4 sparse HOME and
3 robust OFFICE additions before any production policy change.
