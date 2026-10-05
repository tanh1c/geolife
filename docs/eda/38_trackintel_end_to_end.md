# Stage 07n — Trackintel end-to-end pipeline comparator

## Purpose

Stage 07m held CP1 stays and the CP2-v2 location namespace fixed and compared
only semantic selection. Stage 07n intentionally removes that control and lets
Trackintel build its own upstream representation from the raw GeoLife release.

```text
raw GeoLife
    |
Trackintel read_geolife
    |
Trackintel sliding staypoints
    |
Trackintel DBSCAN locations
    |
per-stay IANA local wall clock
    |
Trackintel OSNA
    |
spatial / temporal decomposition
    |
frozen CP1 + CP2-v2 reference
```

This is an implementation/pipeline comparator, not an accuracy evaluation and
not a production migration.

## Runtime design

The raw release contains 24,876,978 GPS points. Loading the full release into a
single GeoDataFrame is unnecessary and memory-heavy.

The Modal notebook therefore processes one user at a time:

1. create a temporary GeoLife root with a symlink to one user directory;
2. call Trackintel `read_geolife` on that root;
3. generate Trackintel staypoints;
4. generate DBSCAN locations at 100 m and 200 m;
5. cache the derived user result on the Modal Volume;
6. release the raw positionfixes before moving to the next user.

Cache root:

```text
/mnt/geolife-data/cache/cp2_v2/07n_trackintel_end_to_end/
```

Raw GPS points are not persisted by Stage 07n.

## Frozen release gates

The mounted release must reconcile to:

- 182 user directories;
- 18,670 trajectory files;
- 24,876,978 position fixes accumulated through Trackintel's raw reader.

The production reference must still reproduce:

- 5,821 CP1 stays / 136 users;
- 2,015 CP2-v2 semantic locations;
- 716 recurring production locations / 104 users;
- HOME = 27;
- OFFICE = 16.

## Trackintel staypoint parameters

Primary Trackintel staypoint parameters are threshold-aligned to CP1:

```text
dist_threshold = 200 m
time_threshold = 20 min
gap_threshold  = 5 min
include_last   = False
```

The purpose is not to imitate the CP1 implementation line by line. It is to
avoid deliberately changing the broad stay definition at the same time as the
algorithm implementation.

Trackintel 1.4.2 documents the sliding staypoint API with distance, time, and
gap thresholds in meters/minutes. The implementation follows the Li et al.
sliding-window family.

Reference:

- https://trackintel.readthedocs.io/en/latest/modules/preprocessing.html

## Trackintel location parameters

The same Trackintel staypoint inventory is clustered twice:

```text
DBSCAN epsilon = 100 m, num_samples = 1
DBSCAN epsilon = 200 m, num_samples = 1
```

100 m is the Trackintel default and 200 m provides a radius sensitivity view
against the production complete-link 200 m maximum-diameter representation.

These are not equivalent cluster contracts:

- DBSCAN constrains density connectivity and can chain;
- complete-link constrains maximum pairwise diameter.

Stage 07n does not claim `num_samples=1` is optimal. MinPts sensitivity remains
a separate methodological question.

## Local-time handling before OSNA

Trackintel reads the GeoLife raw timestamps into timezone-aware UTC timestamps.

Before OSNA, each Trackintel staypoint center is independently resolved to an
IANA timezone using the same project dependency `timezonefinder==9.0.0`.
Physical UTC start time is converted to local wall clock and then encoded as a
dummy UTC timestamp while true elapsed duration is preserved.

This gives OSNA local weekday/time-of-day semantics without assuming every
Trackintel stay is in Asia/Shanghai.

Timezone-unresolved Trackintel staypoints remain part of the upstream
stay/location comparison but are excluded from OSNA.

## Decomposition A — staypoint extraction

The CP1 and Trackintel stay inventories are matched reciprocally.

For each source stay, the best target stay for the same user is the interval
with maximum positive temporal overlap.

Diagnostics include:

- any temporal overlap;
- temporal overlap + centers within 200 m;
- strong match: overlap is at least 50% of the shorter stay and centers are
  within 200 m.

This is reported both CP1 -> Trackintel and Trackintel -> CP1 because the two
inventories can differ in size.

## Decomposition B — location geometry

For each production location, find the nearest Trackintel DBSCAN location for
the same user.

Report separately for:

- all production locations;
- recurring production locations.

Spatial correspondence is summarized at 50 / 100 / 200 m and by median
nearest-center distance.

Integer location ids are never compared between the two pipelines.

## Decomposition C — semantic candidates

Trackintel OSNA runs separately on DBSCAN-100 and DBSCAN-200 staypoint
assignments with:

```text
method = OSNA
pre_filter = False
```

HOME/WORK candidates are joined to Trackintel location centers and compared
against production HOME/OFFICE by center distance.

Reported candidate correspondence:

- within 50 m;
- within 100 m;
- within 200 m;
- both selected but >200 m;
- production only;
- Trackintel only;
- neither.

These are spatial correspondence categories, not correctness classes.

## Why pre_filter remains disabled

The purpose of Stage 07n is decomposition.

Trackintel's own pre-filter would add another eligibility contract involving
minimum staypoints, locations, visits, dwell, and observation span. That is
valid as a library workflow, but it would make it harder to separate:

- upstream event extraction;
- location clustering;
- semantic selection;
- eligibility/abstention.

Production abstention remains evaluated by the existing CP2 and Stage-05/07
reliability work.

## Interpretation

Stage 07n should be read in order:

```text
stay extraction correspondence
        ↓
location geometry correspondence
        ↓
semantic candidate correspondence
```

If semantic candidates differ while upstream stay/location correspondence is
high, the semantic rule is the likely source.

If stay correspondence is already low, later semantic disagreement cannot be
attributed to OSNA.

If stays correspond but location geometry does not, clustering is the main
representation difference.

No Stage-07n result changes HOME 27 / OFFICE 16.

## Outputs

Private:

- `stay_inventory_matches_private.pkl`;
- `location_geometry_matches_private.pkl`;
- `trackintel_osna_candidates_private.pkl`;
- `semantic_candidate_comparison_private.pkl`;
- per-user Trackintel derived caches under `users/`.

Aggregate:

- `raw_and_production_gate.csv`;
- `trackintel_pipeline_summary.csv`;
- `stay_match_summary.csv`;
- `location_geometry_summary.csv`;
- `timezone_adapter_summary.csv`;
- `semantic_candidate_summary.csv`;
- `semantic_status_distribution.csv`;
- `decomposition_snapshot.csv`.


## Measured result

Stage 07n executed successfully on `main` at `5bd2920` with
`trackintel==1.4.2`.

No traceback remained in the executed notebook and all aggregate/private output
tables were written to the Stage-07n cache.

### Raw and frozen-reference gates

All gates passed:

- raw users: 182;
- trajectory files: 18,670;
- Trackintel raw-reader positionfix reconciliation: 24,876,978;
- frozen CP1 stays: 5,821 / 136 users;
- production semantic locations: 2,015;
- production HOME: 27;
- production OFFICE: 16.

### Trackintel pipeline scale

The threshold-aligned Trackintel sliding detector produced:

- 2,157 staypoints;
- 125 users with staypoints.

Location generation:

| variant | locations | recurring locations | recurring-location users |
| --- | ---: | ---: | ---: |
| DBSCAN 100 m | 1,237 | 247 | 75 |
| DBSCAN 200 m | 1,113 | 264 | 81 |

All 2,157 Trackintel staypoints resolved to an IANA timezone across 18 distinct
timezones.

The Trackintel staypoint generator emitted warnings that duplicate positionfixes
were dropped during preprocessing. This is a real implementation difference
from the frozen CP1 pipeline and remains part of the end-to-end comparator.

### Decomposition A — staypoint extraction

Strong match requires:

- >=50% temporal overlap relative to the shorter stay;
- center distance <=200 m.

| source inventory | stays | strong matches | strong-match rate |
| --- | ---: | ---: | ---: |
| CP1 | 5,821 | 2,125 | 36.5% |
| Trackintel | 2,157 | 2,088 | 96.8% |

Any temporal-overlap rates show the same asymmetry:

- CP1 -> Trackintel: 37.1%;
- Trackintel -> CP1: 97.1%.

This is the dominant observed representation difference. Trackintel detects far
fewer stays, but nearly all Trackintel stays have a corresponding CP1 stay.

The correct interpretation is not that one detector is more accurate; GeoLife
has no staypoint ground truth here. The result says the two implementations
partition the raw trajectory differently even with broadly aligned thresholds.

### Decomposition B — location geometry

Nearest Trackintel location to each production location:

| variant | scope | within 50 m | within 100 m | within 200 m | median distance |
| --- | --- | ---: | ---: | ---: | ---: |
| DBSCAN 100 m | all 2,015 production locations | 1,025 | 1,170 | 1,238 | 44.9 m |
| DBSCAN 100 m | 716 recurring locations | 412 | 518 | 559 | 36.4 m |
| DBSCAN 200 m | all 2,015 production locations | 927 | 1,062 | 1,187 | 65.2 m |
| DBSCAN 200 m | 716 recurring locations | 357 | 453 | 530 | 49.3 m |

For recurring production anchors, within-200-m correspondence is therefore:

- DBSCAN-100: 559/716 = 78.1%;
- DBSCAN-200: 530/716 = 74.0%.

DBSCAN-100 is slightly closer by these diagnostics. A 200 m DBSCAN epsilon does
not reproduce a 200 m complete-link maximum-diameter location contract.

### Decomposition C — OSNA semantic candidates

Trackintel end-to-end OSNA selected:

- HOME: 92 users;
- WORK: 85 users.

Production-emitted users jointly selected by Trackintel:

- HOME: 26/27;
- OFFICE: 15/16.

Spatial correspondence:

| variant | label | production emitted | both selected | within 50 m | within 100 m | within 200 m |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| DBSCAN 100 m | HOME | 27 | 26 | 19 | 19 | 19 |
| DBSCAN 100 m | OFFICE | 16 | 15 | 9 | 9 | 9 |
| DBSCAN 200 m | HOME | 27 | 26 | 17 | 18 | 21 |
| DBSCAN 200 m | OFFICE | 16 | 15 | 9 | 9 | 9 |

Relative to the frozen production emissions:

- HOME within 200 m: 70.4% with DBSCAN-100; 77.8% with DBSCAN-200;
- OFFICE within 200 m: 56.3% for both variants.

Among jointly selected users:

- DBSCAN-200 HOME within 200 m: 21/26 = 80.8%;
- OFFICE within 200 m: 9/15 = 60.0%.

### 07m -> 07n decomposition

Stage 07m held stays and locations fixed:

- OSNA HOME exact candidate: 27/27;
- OSNA OFFICE exact candidate: 11/16.

Stage 07n replaces stay extraction and clustering:

- best HOME spatial correspondence: 21/27 within 200 m;
- OFFICE spatial correspondence: 9/16 within 200 m.

Therefore the end-to-end drop cannot be attributed to semantic selection alone.
A substantial difference is already introduced by upstream event extraction,
with a secondary effect from location representation.

### Final interpretation

The measured ordering of differences is:

```text
largest observed divergence:
stay inventory construction
        ↓
secondary:
location clustering / anchor geometry
        ↓
semantic OSNA remains more stable for HOME than OFFICE
```

HOME remains comparatively robust across implementations.

OFFICE remains more sensitive to both semantic rule and upstream representation,
consistent with the Stage-07m and Stage-07j/07l findings.

### Decision

Keep the frozen production policy unchanged:

- HOME = 27;
- OFFICE = 16.

Do not tune CP1 stay thresholds, DBSCAN/complete-link parameters, or
HOME/OFFICE gates from Stage 07n.

Stage 07n validates that the two pipelines share substantial significant-place
structure while also showing that apparently identical stay thresholds do not
create equivalent event inventories across implementations.
