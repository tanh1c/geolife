# Same-second transportation audit

Date: 2026-09-18  
Status: COMPLETE — mentor follow-up audit resolved the interpretation of the 10 m same-second rule.

## Question

The original CP1 contract treated a same-second group with `max_radius_m > 10 m` as a spatial conflict. Mentor review raised a valid concern: GeoLife exposes timestamps only to whole-second precision, so fast transportation can move materially inside one recorded second while the release does not preserve within-second ordering.

The audit therefore asked:

> Is 10 m a validity/corruption threshold, or only a threshold below which consolidation is safe?

Transportation labels were used only as auxiliary evidence. They are not introduced as a runtime cleaning dependency.

## Data and method

Prior EDA identified:

- 212,409 same-second groups;
- 835 groups with `max_radius_m > 10 m`.

For each of the 835 groups the audit:

1. reconstructed the raw same-second observations;
2. computed exact maximum pairwise Haversine diameter;
3. joined the group timestamp to same-user transportation labels using half-open `[start, end)` semantics;
4. assigned a mode only when exactly one distinct mode was active;
5. compared observed diameter with a one-second distance reference from the audited V3 transportation-speed benchmark.

The one-second reference is diagnostic only. It does not prove that the true elapsed time was one second and is not a validity rule.

## Label coverage

All 835 groups were accounted for:

- unambiguous mode: 403;
- labeled user but timestamp outside all label intervals: 349;
- unlabeled user: 83.

No unambiguous airplane group occurred in this subset, so airplane remains a motivating theoretical example rather than observed evidence from these 835 groups.

Unambiguous groups by mode:

- walk: 194;
- bike: 145;
- subway: 25;
- bus: 19;
- taxi: 10;
- car: 7;
- train: 3.

## Spatial spread by mode

| mode | groups | median diameter m | p90 diameter m | max diameter m |
| --- | ---: | ---: | ---: | ---: |
| walk | 194 | 19.89 | 42.55 | 314.18 |
| bike | 145 | 22.51 | 54.28 | 266.28 |
| subway | 25 | 19.07 | 38.59 | 89.80 |
| bus | 19 | 22.95 | 54.16 | 499.71 |
| taxi | 10 | 17.78 | 106.36 | 117.18 |
| car | 7 | 35.82 | 65.19 | 71.40 |
| train | 3 | 30.08 | 31.34 | 31.66 |

This already shows that the >10 m tail is heterogeneous. Train/subway examples can sit at a few tens of metres, while other groups have much stronger inconsistency.

## Compatibility with one-second movement scale

Using the audited V3 reference values:

| mode | groups | one-second reference m | within reference | rate |
| --- | ---: | ---: | ---: | ---: |
| train | 3 | 58.43 | 3 | 100.0% |
| subway | 25 | 26.20 | 20 | 80.0% |
| taxi | 10 | 29.10 | 7 | 70.0% |
| bus | 19 | 25.16 | 10 | 52.6% |
| car | 7 | 33.23 | 3 | 42.9% |
| bike | 145 | 11.29 | 2 | 1.4% |
| walk | 194 | 11.22 | 4 | 2.1% |

Interpretation:

- train and many subway/taxi cases are compatible with legitimate movement plus whole-second timestamp quantization as one plausible explanation;
- ordinary movement does not explain most walk/bike >10 m groups;
- therefore the >10 m population cannot be assigned one cause.

## Broad tail diagnostic

Across all 835 groups:

- 747 (89.46%) had diameter <=333.3 m;
- 20 were in 333.3 m–1 km;
- 68 exceeded 1 km.

The 333.3 m value is the distance traveled in one second at the CP1 hard guard of 1200 km/h. It is a deliberately broad diagnostic envelope, **not** a consolidation threshold.

The >1 km groups are strong spatial-inconsistency candidates, but the audit still does not infer a unique failure mechanism.

## Decision

The mentor concern changes the scientific interpretation but not the conservative production behavior.

Final Stage 2 semantics:

- `max_radius_m <= 10 m`: compact enough to consolidate safely using the median representative;
- `max_radius_m > 10 m`: unsafe to collapse because within-second order is not identifiable; discard the unresolved timestamp from the retained sequence and create a continuity boundary.

The 10 m value is therefore a **safe-consolidation threshold**, not a valid-versus-corrupt threshold.

The production diagnostic reason is:

`same_second_spatial_ambiguity`

This means unresolved spatial spread at the released timestamp precision. It does not assert corruption.

Transportation labels remain audit evidence only. Production cleaning does not infer mode, use mode-specific thresholds, or invent sub-second ordering.

## Impact on CP1 baseline

Boundary placement is unchanged relative to the previously validated implementation. Therefore:

- the 18,670-file full-release baseline does not need to be rerun;
- the 27-config stay-point sensitivity analysis does not need to be rerun;
- frozen stay-point parameters remain 300 s gap / 200 m radius / 1200 s dwell.

Notebook: `notebooks/02c_same_second_transport_audit.ipynb`.
