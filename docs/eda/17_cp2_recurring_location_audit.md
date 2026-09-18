# CP2 recurring-location representation audit

Date: 2026-09-18  
Status: OPEN — complete-link sensitivity added to notebook; measured results pending review.

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

## Downstream consequence

Home/Office scoring remains blocked until this representation is reviewed.

Notebook: `notebooks/03_home_office_baseline.ipynb`.
