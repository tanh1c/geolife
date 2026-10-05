# Stage 07j handoff — Targeted near-miss OFFICE audit

## Run

Run:

`notebooks/07j_near_miss_office_audit.ipynb`

from current `main`.

No OSM query, BCL extraction, Modal worker, or threshold grid is rerun.

## Required upstream artifacts

Stage 05 reliability:

```text
/mnt/geolife-data/cache/cp2_v2/05_home_office_reliability_validation/
  assignments_private.pkl
  split_half_details_private.pkl
  holdout_details_private.pkl
  dropout_details_private.pkl
  time_shift_details_private.pkl
```

Stage 07i:

```text
/mnt/geolife-data/cache/cp2_v2/07i_threshold_sensitivity/
  office_gate_emitted_details_private.pkl
  bcl_anchor_metrics_150m_private.pkl
```

Do not rerun Stage 05 or Stage 07i before 07j.

## Expected cohort reproduction

The notebook must show:

```text
baseline      16
margin_near    2
share_near     7
```

and:

`near-miss cohort reproduction: PASS (16 baseline + 2 margin + 7 share = 25 unique)`

It must also show:

`full-period candidate identity validation: PASS`

Any mismatch is a hard stop.

## Main tables

### SUPPORT DISTRIBUTION

Compare full support days and OFFICE share across:

- baseline;
- margin near;
- share near.

### BEHAVIORAL / IDENTITY ROBUSTNESS

Important fields:

- HOME collision users;
- HoWDe exact-candidate match;
- recurrence exact-candidate match;
- both static comparators match;
- first/second both halves match full candidate;
- odd/even both halves match full candidate;
- both split tests match;
- held-out full candidate top-1;
- median / mean dropout candidate retention;
- 12-hour-shift candidate retention.

The 12-hour result is diagnostic only.

### BCL PRIMARY CONTEXT — 100m / 150m

Report evaluable users and:

- broad work-compatible lexical context;
- business-name;
- education;
- retail/service.

Lack of BCL evidence is not a negative OFFICE label.

### NEAR-MISS AGGREGATE DIAGNOSTICS

This table summarizes the 9 near-miss users without exposing user IDs.

### STATIC COMPARATOR MATCH COUNT

Distribution of 0 / 1 / 2 static comparator matches.

### SPLIT FULL-CANDIDATE MATCH COUNT

Distribution of 0 / 1 / 2 split tests where both halves recover the exact full-period candidate.

## Interpretation

The central comparison is near-miss robustness relative to the frozen baseline OFFICE cohort.

Do not promote a user because of one strong metric.

Do not create a new composite score after seeing the results.

Send the executed notebook after Run All.


## Final measured handoff — 2026-10-05

Stage 07j completed successfully on commit `afbfe81`.

Measured groups:

```text
baseline      16
margin_near    2
share_near     7
```

Near-miss result:

```text
users                                  9
HOME collisions                         0
both static comparators exact-match     0
both split tests exact-recovery         1
held-out exact candidate top-1          2
100% dropout retention                  5
BCL evaluable                           2
BCL work context <=150m                 0
BCL business-name <=150m                0
```

No global OFFICE threshold change is supported.

The next step is Stage 07k historical-imagery adjudication for all nine near-miss candidates, with the frozen 16-user OFFICE cohort retained only as visual/reference context.
