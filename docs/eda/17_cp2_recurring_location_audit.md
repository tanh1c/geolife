# CP2 recurring-location representation audit

Date: 2026-09-18  
Status: COMPLETE — CP2 v1 recurring-location representation frozen at 200 m complete linkage after measured sensitivity review.

## Why this audit exists

The first per-user DBSCAN experiment used a 200 m epsilon and produced useful recurrence structure, but its largest cluster radius from the median representative reached about 526.7 m.

This is expected DBSCAN chaining: epsilon constrains local neighbor links, not the final cluster diameter.

For Home/Office inference, a recurring "location" should have an interpretable spatial compactness contract.

## Candidate representation

Audit per-user complete-linkage agglomerative clustering on the frozen Beijing semantic cohort.

Thresholds:

- 100 m;
- 200 m;
- 300 m.

Complete linkage uses maximum pairwise distance when deciding whether clusters may merge. Therefore, with a threshold T, the final cluster diameter should not exceed T (up to numerical tolerance).

## Metrics

For each threshold report:

- candidate locations;
- recurring locations with >=2 stays;
- users with at least one recurring location;
- median locations per user;
- p95 cluster diameter;
- maximum cluster diameter.

The notebook verifies the candidate 200 m result with an explicit diameter assertion.

## Decision rule

The 200 m threshold is already meaningful in CP1 as the stay radius and recurrence proxy, but it is not automatically promoted to CP2 clustering.

Freeze 200 m complete linkage only if:

- the resulting coverage is not pathologically sensitive relative to 100/300 m;
- exact cluster diameters satisfy the intended bound;
- user-level recurring-location coverage remains adequate for Home/Office inference.

## Measured sensitivity

| threshold | locations | recurring locations | users with recurring location | median locations/user | p95 diameter m | max diameter m |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 100 m | 1,320 | 499 | 67 | 9 | 83.26 | 99.95 |
| 200 m | 1,111 | 486 | 73 | 7 | 159.69 | 199.23 |
| 300 m | 1,007 | 473 | 73 | 6 | 247.46 | 297.42 |

The 200 m setting is a middle sensitivity point. Moving from 100 to 200 m increases recurring-location user coverage from 67 to 73; moving from 200 to 300 m does not add users with recurring locations, while continuing to merge locations.

The exact diameter assertion passed for the 200 m candidate: maximum observed cluster diameter was 199.23 m.

## CP2 v1 decision

Freeze per-user complete-linkage clustering at **200 m maximum cluster diameter** as the recurring-location engineering baseline.

This is not claimed to be an accuracy-optimal spatial threshold. It is selected because:

- it has a direct compactness contract;
- it avoids DBSCAN chaining;
- it preserves recurring-location user coverage relative to 300 m;
- it sits between the 100 and 300 m sensitivity settings;
- it aligns with the already reviewed 200 m CP1 stay/recurrence scale without assuming those semantics are identical.

## Downstream consequence

The recurring-location gate is resolved. CP2 can proceed to Home/Office scoring audit, with scoring semantics still considered exploratory until reviewed.

Notebook: `notebooks/03_home_office_baseline.ipynb`.
