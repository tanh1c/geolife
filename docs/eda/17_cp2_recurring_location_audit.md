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

## Final timezone-resolved DBSCAN rerun — 2026-09-24

Notebook 03 now keeps every CP1 stay whose timezone resolves. Since all 5,821 frozen stays resolve successfully, the final DBSCAN sensitivity again runs on the complete stay inventory.

| eps_m | locations | recurring_locations | users_with_recurring_location | median_recurring_diameter_m | p95_recurring_diameter_m | max_recurring_diameter_m | recurring_clusters_gt_200 |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 10 | 3698 | 442 | 78 | 8.03 | 43.12 | 110.84 | 0 |
| 20 | 3018 | 466 | 84 | 15.81 | 73.41 | 172.31 | 0 |
| 30 | 2702 | 496 | 90 | 23.24 | 100.13 | 181.32 | 0 |
| 50 | 2420 | 551 | 94 | 34.61 | 118.10 | 248.80 | 6 |
| 100 | 2131 | 602 | 97 | 51.09 | 186.28 | 441.31 | 24 |
| 150 | 1996 | 616 | 102 | 64.38 | 258.85 | 627.11 | 53 |
| 200 | 1885 | 635 | 104 | 73.48 | 307.99 | 836.66 | 86 |

Key interpretation:

- 10–30 m improve recurring-user coverage while keeping every recurring cluster under 200 m;
- 50 m is the first tested setting where DBSCAN chaining creates clusters wider than 200 m;
- beyond 50 m, recurring-user gains are modest relative to the growth in large-diameter clusters;
- at 200 m, 86 / 635 recurring clusters exceed 200 m and the maximum diameter reaches ~837 m.

This does not select 30 m as the production clustering threshold. It demonstrates why DBSCAN eps is not a hard location-size contract and why the complete-link audit remains necessary.



## DBSCAN MinPts follow-up — 2026-10-01

A focused notebook-04 follow-up tested `min_samples = 1/2/3/5` across `eps = 20/50/100/200 m` on the frozen 97-user Home/Office semantic cohort.

This follow-up uses the production semantic cohort and therefore should not be conflated with the separate full-stay DBSCAN rerun above. The complete-link comparator is the same frozen 200 m representation: 1,111 locations, 486 recurring locations, and 73 users with recurrence.

For recurring clusters only, the current notebook-04 comparator reports:

- p95 diameter: 180.95 m;
- maximum diameter: 199.23 m;
- recurring clusters above 200 m: 0.

The older table above reports p95 over its original audit aggregation and is retained as historical evidence; the maximum-diameter contract is unchanged.

At DBSCAN `eps=200 m`:

| min_samples | locations | recurring locations | recurring users | singleton locations | noise stays | p95 recurring diameter m | max recurring diameter m | recurring clusters >200 m |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 1003 | 418 | 73 | 585 | 0 | 365.01 | 836.66 | 68 |
| 2 | 418 | 418 | 73 | 0 | 585 | 365.01 | 836.66 | 68 |
| 3 | 239 | 239 | 64 | 0 | 943 | 407.80 | 836.66 | 68 |
| 5 | 131 | 131 | 56 | 0 | 1317 | 457.27 | 836.66 | 56 |

Interpretation:

- moving from `min_samples=1` to `2` leaves recurring-user and recurring-location counts unchanged; it mainly reclassifies 585 singleton stays as noise;
- raising MinPts to 3 or 5 materially reduces recurring-user coverage;
- the widest chained recurring cluster remains ~837 m for every tested MinPts value;
- therefore MinPts tuning does not solve the compactness problem that motivated complete linkage.

Decision remains unchanged: keep complete-link 200 m as the frozen recurring-location representation for semantic Home/Office work. The next research step is POI / land-use enrichment as auxiliary semantic evidence, not a production relabeling rule.
