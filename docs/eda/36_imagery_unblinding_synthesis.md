# Stage 07l — Historical imagery unblinding synthesis

## Purpose

Stage 07k produced a blinded visual review for the nine Stage-07j OFFICE near-miss candidates.

Stage 07l removes the blind only after the visual classifications are fixed, then joins:

- visual historical-imagery context;
- Stage-07j behavioral persistence / identity diagnostics;
- BCL-primary historical context.

The goal is to test whether the visually plausible cases are also the behaviorally persistent cases.

No composite OFFICE score is created.

## Inputs

Completed blinded review CSV:

`near_miss_9_blinded_review_manifest_filled.csv`

Private Stage-07k key:

`historical_imagery_unblinding_key_private.pkl`

Private Stage-07j panel:

`near_miss_office_audit_private.pkl`

The review CSV must contain exactly the nine near-miss audit IDs and all nine must have a visual-context class.

## Visual interpretation buckets

The fixed Stage-07k classes are collapsed only for transparent aggregate comparison.

### OFFICE-like

Only:

- `large_office_commercial_like_complex`.

This is deliberately narrow.

### Institutional / daytime-compatible

- `education_campus`;
- `healthcare_institutional`;
- `industrial_warehouse`.

These contexts can plausibly explain regular weekday/daytime presence but do not establish OFFICE.

### OFFICE-contradictory context

- `residential_compound`;
- `transport_infrastructure`;
- `construction_vacant`;
- `recreation_green_space`.

These are useful contextual counter-signals for a literal OFFICE interpretation.

### Indeterminate

- `mixed_urban_block`;
- `other_visible_structure`;
- `ambiguous`.

No visual semantic conclusion should be drawn from these.

## Evidence join

After unblinding, each case may carry:

- audit family: margin-near or share-near;
- full-period support days and OFFICE share;
- HoWDe exact-candidate agreement;
- recurrence exact-candidate agreement;
- split-half exact-candidate recovery;
- held-out exact-candidate top-1;
- dropout retention;
- BCL evaluability;
- BCL work-compatible context at 100 / 150 m;
- BCL business-name context at 100 / 150 m;
- HOME collision / HOME distance;
- blinded historical-imagery class and confidence.

The output is a transparent case matrix, not a score.

## Aggregate views

Stage 07l produces:

1. visual context by near-miss family;
2. behavior × visual bucket;
3. cross-source signatures;
4. a compact policy snapshot.

These views answer:

- whether margin-near or share-near contains the more plausible visual contexts;
- whether office-like/institutional imagery aligns with held-out/split stability;
- whether visually plausible candidates also receive BCL support;
- whether contradictory visual contexts are concentrated in the weaker behavioral cases.

## Approximate imagery dates

The completed review currently uses same-year imagery proxies rather than exact acquisition dates.

Therefore:

- imagery is useful for broad contemporaneous physical context;
- no exact-day claim is allowed;
- image-derived business/function names remain unsupported unless independently historically verified.

## Outputs

Private:

- `imagery_unblinded_panel_private.pkl`;
- `imagery_behavior_bcl_case_matrix_private.pkl`.

Aggregate:

- `visual_context_by_near_miss_family.csv`;
- `behavior_by_visual_bucket.csv`;
- `cross_source_signature_summary.csv`;
- `policy_snapshot.csv`.

Cache root:

`/mnt/geolife-data/cache/cp2_v2/07l_imagery_unblinding_synthesis/`

## Decision boundary

Stage 07l still does not change production.

A visually office-like case is not promoted automatically.

The strongest possible finding would be that one near-miss family contains a stable concentration of:

- office-like or clearly institutional/daytime-compatible imagery;
- exact-candidate behavioral persistence across existing diagnostics;
- no HOME collision;
- independent BCL support where evaluable.

If the evidence remains heterogeneous or visually plausible cases are behaviorally weak, the frozen OFFICE gate should remain unchanged.
