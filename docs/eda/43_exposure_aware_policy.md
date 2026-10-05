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
