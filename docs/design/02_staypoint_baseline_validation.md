# CP1 stay-point baseline validation

Date: 2026-09-18
Status: COMPLETE — CP1 engineering baseline frozen after full-release audit, user-stratified sensitivity, and same-second transportation audit.

## Decision

Freeze the CP1 cleaning + stay-point baseline at:

- same-second compactness radius: `10 m`;
- temporal continuity gap: `300 s`;
- hard-speed corruption guard: `1200 km/h`;
- stay distance threshold: `200 m`;
- minimum dwell: `1200 s` (20 minutes).

This is an engineering baseline for CP1, not a claim of accuracy-optimal thresholds. GeoLife does not provide direct Home/Office ground truth for calibrating these parameters.

## Full-release baseline audit

The production implementation was run over all `18,670` GeoLife trajectory files.

Observed baseline totals:

- total stays: `5,821`;
- files with at least one stay: `2,435`;
- complete cleaning semantics passed the reviewed acceptance tests;
- full-release cleaning counts were consistent with the prior EDA consolidation audit;
- quality-event counting is separated from retained-row `boundary_before_reason` diagnostics through `clean_trajectory_with_audit()`.

The largest hard-speed outlier trajectory contained `593` hard-speed boundaries. The corruption was strongly concentrated rather than broadly distributed, which supports the conservative rule of breaking continuity at extreme segments without applying ordinary transport-speed deletion thresholds globally.

## Same-second transportation audit

A mentor review questioned whether the 10 m same-second rule was being interpreted too strongly. GeoLife exposes only whole-second timestamps, so two observations recorded in the same second can have unknown within-second order. Fast transportation can therefore create non-trivial spatial spread without proving corruption.

The dedicated audit in `notebooks/02c_same_second_transport_audit.ipynb` evaluated all `835` same-second groups with `max_radius_m > 10 m`.

Label accounting:

- unambiguous transportation mode: `403` groups;
- labeled user but timestamp outside label intervals: `349`;
- unlabeled user: `83`;
- no unambiguous airplane cases occurred in this subset.

Observed mode evidence:

| mode | groups | median diameter (m) | within one-second reference |
| --- | ---: | ---: | ---: |
| train | 3 | 30.08 | 3/3 (100%) |
| subway | 25 | 19.07 | 20/25 (80%) |
| taxi | 10 | 17.78 | 7/10 (70%) |
| bus | 19 | 22.95 | 10/19 (52.6%) |
| car | 7 | 35.82 | 3/7 (42.9%) |
| bike | 145 | 22.51 | 2/145 (1.4%) |
| walk | 194 | 19.89 | 4/194 (2.1%) |

Across all 835 groups, `747` (89.46%) had diameter <=333.3 m, while `68` had diameter >1 km. The broad 333.3 m figure is only a diagnostic envelope derived from 1200 km/h in one second; it is **not** a proposed consolidation threshold.

The audit conclusion is semantic rather than behavioral:

- `10 m` is a **safe-to-collapse threshold**;
- a group above 10 m is not automatically corrupt;
- because within-second order is not identifiable, groups above 10 m remain unsafe to collapse and continue to create continuity boundaries;
- the diagnostic reason is renamed to `same_second_spatial_ambiguity`;
- transportation mode remains audit evidence only and is not a runtime cleaning dependency.

Because the retained/boundary behavior is unchanged, the full-release baseline and stay-point sensitivity results do not need to be rerun.

## Sensitivity design

The final sensitivity run used a deterministic user-stratified sample instead of a path-ordered trajectory prefix:

- users covered: `182`;
- trajectory files sampled: `851`;
- at most `5` files per user;
- heavy-user samples were spread across sorted trajectory history rather than taking only the earliest files.

Grid:

- `max_gap_s`: `120`, `300`, `600`;
- `distance_threshold_m`: `100`, `200`, `300`;
- `min_dwell_s`: `600`, `1200`, `1800`.

This produced `27` configurations.

The recurring-location stability proxy was defined as follows: among users with at least two detected stays, count the fraction having at least one pair of stay representatives within `200 m`. This is a stability proxy only, not Home/Office ground-truth accuracy.

## Frozen baseline result

For `300 s / 200 m / 1200 s`:

- stays: `478`;
- files with stays: `174`;
- users with stays: `89`;
- mean stays per user: `2.626374`;
- median stays per active user: `4`;
- users with at least two stays: `69`;
- users with a repeated location: `52`;
- repeated-location user rate: `0.753623`;
- median stay duration: `1621.5 s`;
- p90 stay duration: `3202.9 s`.

## Local sensitivity around the baseline

### Continuity gap

Holding `distance=200 m` and `dwell=1200 s`:

| max gap | stays | users with stays | repeat-location rate |
| ---: | ---: | ---: | ---: |
| 120 s | 205 | 57 | 0.750000 |
| 300 s | 478 | 89 | 0.753623 |
| 600 s | 655 | 113 | 0.770115 |

The recurrence proxy is stable across these values while coverage rises as continuity becomes more permissive. `300 s` remains the CP1 choice because it is the middle sensitivity value and preserves the conservative goal of avoiding dwell across longer unobserved outages. The `600 s` setting increases coverage but there is no ground-truth evidence sufficient to justify weakening that continuity rule for CP1.

### Stay radius

Holding `gap=300 s` and `dwell=1200 s`:

| radius | stays | users with stays | repeat-location rate |
| ---: | ---: | ---: | ---: |
| 100 m | 324 | 77 | 0.698113 |
| 200 m | 478 | 89 | 0.753623 |
| 300 m | 547 | 102 | 0.708861 |

`200 m` is a useful middle point and has the strongest recurring-location proxy among its immediate radius neighbors in this sensitivity sample. This does not prove accuracy, but it gives no reason to move away from the reviewed baseline.

### Minimum dwell

Holding `gap=300 s` and `distance=200 m`:

| minimum dwell | stays | users with stays | repeat-location rate | median duration |
| ---: | ---: | ---: | ---: | ---: |
| 10 min | 1,239 | 139 | 0.791304 | 964.0 s |
| 20 min | 478 | 89 | 0.753623 | 1621.5 s |
| 30 min | 210 | 67 | 0.615385 | 2423.0 s |

The `10 min` configuration substantially expands short-stay coverage, while `30 min` removes many users and lowers the recurrence proxy. The `20 min` baseline remains a conservative middle setting and matches the original semantic goal of identifying sustained stays rather than short pauses.

## Interpretation

The sensitivity surface behaves in the expected directions:

- larger continuity gaps produce more stays and broader user coverage;
- larger spatial thresholds generally produce more stays;
- longer dwell thresholds produce fewer stays and longer duration distributions.

The frozen baseline does not sit at an unstable edge of the grid. Its recurring-location behavior is reasonably stable relative to neighboring configurations, while retaining conservative continuity and dwell assumptions.

No threshold in this grid should be described as empirically optimal for Home/Office classification. The next validation stage is downstream: use these frozen stays to build the Home/Office heuristic, apply local-time semantics there, and evaluate plausibility/stability at the user level.

## Handoff

CP1 stay-point semantics and baseline are now frozen for the first Home/Office implementation:

```text
raw GeoLife trajectories
    -> cleaning (10 m / 300 s / 1200 km/h)
    -> anchor-based stay detection (200 m / 20 min)
    -> user-level stay history
    -> Home / Office / POI heuristic
```

Any future change to the parameter values is a model/config revision and must be compared against this baseline. Any change to anchor-based membership, sequence-boundary semantics, dwell definition, or outside-radius behavior is a semantic change and requires contract review.