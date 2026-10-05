# Stage 07i — Threshold sensitivity + BCL-primary interpretation

## Motivation

Stage 07h originally triangulated Stage-05c behavior, Stage-07e historical OSM, and Stage-07g BCL lexical context as three independent evidence families.

A methodological review identified two concerns.

First, historical OSM is not equally informative for this cohort:

- 257 / 296 OSM-eligible anchors (86.8%) have median observation year 2008 or 2009;
- ohsome returns the OSM state at each anchor's median observation date;
- early OSM absence means "not mapped in OSM at that date", not "not present in the real world".

Therefore historical OSM should not be treated as a negative vote against BCL.

Second, current production/adaptive heuristics are intentionally conservative. Low OFFICE/stable-secondary semantic support could partly reflect strict gates rather than absence of real structure.

Stage 07i audits both issues without changing production.

## Revised evidence hierarchy

For historical functional POI context:

1. **BCL POI 2008** — primary historical POI evidence for the GeoLife-heavy 2007–2009 period.
2. **Historical OSM / ohsome** — weak positive support-only cross-check.
3. **CLCD** — physical land-cover evidence only.

OSM can strengthen a positive BCL interpretation when a relevant historical mapped feature exists.

OSM absence or a negative OSM candidate-minus-peer contrast is not treated as contradiction because historical mapping completeness is not known.

## No post-hoc threshold selection

Stage 07i uses predeclared sensitivity grids.

It must not select a new threshold because that threshold makes OFFICE or BCL agreement look better.

A production change would require a separate decision rule based on:

- broad stability across neighboring configurations;
- behavioral/engineering rationale;
- no material identity instability;
- preferably stronger external supervision.

## Production OFFICE gate sensitivity

Frozen production OFFICE gate:

```text
office_min_dates  = 3
office_min_share  = 0.30
office_min_margin = 0.10
```

Predeclared full grid:

- min dates: 2 / 3 / 5;
- share: 0.20 / 0.30 / 0.40;
- margin: 0.05 / 0.10 / 0.20.

Total: 27 configurations.

For every configuration Stage 07i records:

- fixed-window candidate users;
- emitted users;
- frozen-baseline emitted users retained;
- newly emitted users;
- frozen-baseline users lost;
- same-location retention among common emitted users.

Where an emitted OFFICE candidate also lies in the BCL-temporally-eligible recurring non-HOME universe, Stage 07i reports BCL context descriptively. This is an evaluable subset only, not validation of all OFFICE emissions.

## Adaptive stable-secondary sensitivity

Frozen Stage-05b baseline:

```text
window_days         = 42
step_days           = 14
min_observed_days   = 6
min_candidate_days  = 3
min_candidate_stays = 2
stability_threshold = 0.70
```

### One-at-a-time grid

Hold all other values fixed and vary:

- window days: 28 / 42 / 56;
- min observed days: 4 / 6 / 8;
- min candidate days: 2 / 3 / 4;
- min candidate stays: 1 / 2 / 3;
- stability threshold: 0.60 / 0.70 / 0.80.

The baseline appears once, giving 11 OAT configurations.

For each configuration:

- stable-secondary user count;
- multi-anchor / unstable / insufficient counts;
- baseline-stable users retained;
- newly stable users;
- baseline-stable users lost;
- exact candidate-location retention;
- median dominant-window share.

### Joint profiles

Four predeclared profiles:

**relaxed**

```text
min observed days   = 4
min candidate days  = 2
min candidate stays = 1
stability            = 0.60
```

**mildly relaxed**

```text
min observed days   = 5
min candidate days  = 2
min candidate stays = 2
stability            = 0.60
```

**baseline**

Frozen values.

**strict**

```text
min observed days   = 8
min candidate days  = 4
min candidate stays = 3
stability            = 0.80
```

All keep 42-day windows and 14-day step so the joint comparison isolates support/stability gates.

## BCL radius sensitivity

Stage 07g extracted POIs using 150 m spatial retrieval padding.

Therefore Stage 07i can safely recompute exact Haversine evidence at:

- 25 m;
- 50 m;
- 75 m;
- 100 m;
- 125 m;
- 150 m.

150 m is the maximum reusable radius.

Testing 200 m would require a new BCL spatial extraction and is intentionally excluded from this stage.

For every mobility configuration Stage 07i reports candidate-vs-peer BCL evidence across those radii.

Primary descriptive category checks include:

- business-name;
- education;
- retail/service.

## BCL-primary / OSM-support-only view

For the frozen 9-user Stage-07h panel, at 100 m Stage 07i reports:

- BCL candidate-context users;
- BCL candidate-favoring / neutral / peer-favoring users;
- among BCL-favoring users, how many have OSM mapped candidate context;
- among BCL-favoring users, how many are also OSM candidate-favoring;
- BCL-favoring users without mapped OSM candidate context;
- behavior-strict + BCL-favoring overlap;
- behavior-directional-majority + BCL-favoring overlap.

No field counts OSM absence as contradiction.

## Reproduction gates

Before interpreting sensitivity:

- frozen production OFFICE must reproduce 16 emitted users;
- frozen Stage-05b baseline must reproduce 9 stable-secondary users;
- exact baseline stable candidate location IDs must match the saved Stage-05b artifact.

Any reproduction failure is a hard stop.

## Outputs

Private:

- `office_gate_emitted_details_private.pkl`;
- `mobility_patterns_sensitivity_private.pkl`;
- `bcl_anchor_poi_matches_150m_private.pkl`;
- `bcl_anchor_metrics_150m_private.pkl`.

Aggregate:

- `office_gate_sensitivity.csv`;
- `mobility_gate_sensitivity.csv`;
- `bcl_radius_and_mobility_sensitivity.csv`;
- `bcl_candidate_category_sensitivity.csv`;
- `bcl_primary_osm_support_snapshot.csv`.

Cache root:

`/mnt/geolife-data/cache/cp2_v2/07i_threshold_sensitivity/`

## Decision boundary

Stage 07i can establish whether the current conclusion is robust to reasonable nearby heuristic thresholds.

It cannot establish ground-truth OFFICE.

A relaxed configuration is not preferred merely because:

- it emits more users;
- it increases BCL context;
- it gives a larger positive candidate-minus-peer difference.

The useful signal is a broad, stable plateau across neighboring configurations with consistent candidate identities and independent rationale.


## Measured result — 2026-10-05

Stage 07i executed successfully on repository commit `a8d8308`.

There was no traceback. All outputs were saved under:

`/mnt/geolife-data/cache/cp2_v2/07i_threshold_sensitivity/`.

Hard reproduction gates passed:

- CP2-v2 semantic users: 136;
- semantic locations: 2,015;
- saved Stage-05b stable-secondary users: 9;
- recomputed Stage-05b baseline: exactly the same 9 users and exact candidate IDs;
- frozen production OFFICE: 16 emitted users.

### 1. Production OFFICE gate sensitivity

The frozen gate is:

```text
dates  = 3
share  = 0.30
margin = 0.10
emitted users = 16
```

Nearby relaxations show that this gate is conservative in **coverage**.

| dates | share | margin | emitted | baseline retained | new vs baseline | baseline lost |
|---:|---:|---:|---:|---:|---:|---:|
| 3 | 0.30 | 0.10 | 16 | 16 | 0 | 0 |
| 3 | 0.30 | 0.05 | 18 | 16 | 2 | 0 |
| 3 | 0.20 | 0.10 | 23 | 16 | 7 | 0 |
| 3 | 0.20 | 0.05 | 26 | 16 | 10 | 0 |
| 2 | 0.30 | 0.10 | 26 | 15 | 11 | 1 |
| 2 | 0.30 | 0.05 | 29 | 16 | 13 | 0 |
| 2 | 0.20 | 0.05 | 41 | 16 | 25 | 0 |

Interpretation:

- lowering share/margin at fixed `min_dates=3` expands coverage while preserving all 16 frozen users;
- lowering `min_dates` changes the candidate universe from 30 to 52 users and can change candidate identity for some frozen users;
- therefore the date-support gate is structurally more consequential than a small margin relaxation.

The BCL-evaluable emitted subset remains small.

At the frozen gate:

- BCL-evaluable emitted users: 4;
- broad BCL lexical-context users: 2;
- business-name users: 0.

At nearby relaxed gates:

- `3 / 0.30 / 0.05`: 5 evaluable, 2 broad-context, 0 business-name;
- `3 / 0.20 / 0.10`: 5 evaluable, 2 broad-context, 0 business-name;
- `3 / 0.20 / 0.05`: 6 evaluable, 2 broad-context, 0 business-name.

Thus the extra OFFICE emissions do not come with a corresponding increase in BCL evidence inside the evaluable subset.

This does **not** prove the new emissions are false; it means the current external historical evidence does not validate the expanded coverage.

### 2. One-at-a-time stable-secondary sensitivity

Frozen baseline:

- 29 analyzed users;
- 9 stable-secondary;
- 3 multi-anchor;
- 1 unstable;
- 16 insufficient;
- all 9 baseline candidates reproduce exactly;
- median dominant-window share = 1.00.

One-at-a-time results:

| change | stable users | baseline retained | new stable | baseline lost | same candidate among common |
|---|---:|---:|---:|---:|---:|
| baseline | 9 | 9 | 0 | 0 | 9 |
| window 28d | 6 | 5 | 1 | 4 | 5 |
| window 56d | 10 | 9 | 1 | 0 | 9 |
| observed days 4 | 10 | 9 | 1 | 0 | 9 |
| observed days 8 | 8 | 8 | 0 | 1 | 8 |
| candidate days 2 | 10 | 7 | 3 | 2 | 7 |
| candidate days 4 | 5 | 5 | 0 | 4 | 5 |
| candidate stays 1 | 9 | 9 | 0 | 0 | 9 |
| candidate stays 3 | 9 | 9 | 0 | 0 | 9 |
| stability 0.60 | 10 | 9 | 1 | 0 | 9 |
| stability 0.80 | 9 | 9 | 0 | 0 | 9 |

Main robustness result:

- `min_candidate_stays` in 1–3 has no effect;
- stability 0.60–0.80 leaves the nine-user core almost unchanged;
- longer 56-day windows, lower observed-day support, or stability 0.60 add only one marginal user while preserving all nine;
- `min_candidate_days` is the most sensitive gate because changing it alters both membership and candidate identity;
- shortening to 28-day windows also materially destabilizes the cohort.

Therefore the nine-user stable-secondary core is **not sitting on a generic threshold cliff**.

### 3. Joint relaxed / strict profiles

| profile | stable | multi-anchor | insufficient | baseline retained | new stable | baseline lost | median dominant share |
|---|---:|---:|---:|---:|---:|---:|---:|
| relaxed | 10 | 9 | 9 | 7 | 3 | 2 | 0.764 |
| mildly relaxed | 10 | 8 | 9 | 7 | 3 | 2 | 0.853 |
| baseline | 9 | 3 | 16 | 9 | 0 | 0 | 1.000 |
| strict | 5 | 3 | 18 | 5 | 0 | 4 | 1.000 |

Joint relaxation increases nominal coverage only from 9 to 10, but:

- loses two frozen stable users;
- adds three different stable users;
- increases multi-anchor users from 3 to 8–9;
- lowers dominant-window stability.

So broad relaxation does not reveal a larger stable version of the same cohort. It changes the composition and increases ambiguity.

### 4. BCL radius sensitivity for the frozen baseline

Candidate-vs-peer broad lexical context:

| radius | candidate context | mean peer share | mean candidate-peer | bootstrap 95% CI |
|---:|---:|---:|---:|---:|
| 25 m | 2 / 9 | 0.023 | +0.199 | [-0.041, +0.537] |
| 50 m | 3 / 9 | 0.162 | +0.171 | [-0.099, +0.494] |
| 75 m | 3 / 9 | 0.232 | +0.102 | [-0.186, +0.438] |
| 100 m | 4 / 9 | 0.423 | +0.021 | [-0.360, +0.395] |
| 125 m | 5 / 9 | 0.499 | +0.057 | [-0.280, +0.395] |
| 150 m | 6 / 9 | 0.628 | +0.039 | [-0.328, +0.384] |

Increasing radius clearly increases candidate context coverage, but peer context rises at the same time.

The candidate-specific contrast remains close to zero beyond 75 m, and every bootstrap interval crosses zero.

Therefore the previous null/mixed conclusion is not an artifact of choosing 100 m too strictly.

Category counts at the exact candidate:

- business-name: 0 / 9 through 100 m, 1 / 9 at 125 m, 2 / 9 at 150 m;
- education: 3 / 9 at 100 m, 5 / 9 at 150 m;
- retail/service: 2 / 9 at 100 m, 3 / 9 at 150 m.

Larger radii recover more named context but do not produce a specifically OFFICE-like pattern.

### 5. BCL evidence under relaxed mobility profiles

At 100 m:

- relaxed: 9 evaluable candidates, 3 with context, mean candidate-peer = -0.105, CI [-0.450, +0.255];
- mildly relaxed: identical -0.105, CI [-0.450, +0.255];
- baseline: 4 / 9, +0.021, CI [-0.360, +0.395];
- strict: 3 / 5, +0.261, CI [-0.233, +0.737].

At 150 m:

- relaxed: 5 / 9, -0.095, CI [-0.509, +0.319];
- mildly relaxed: same;
- baseline: 6 / 9, +0.039, CI [-0.328, +0.384];
- strict: 3 / 5, +0.033, CI [-0.464, +0.523].

There is no monotonic semantic improvement as the mobility gates are relaxed.

In fact, the relaxed profiles have slightly negative average candidate-minus-peer differences.

The apparently larger strict-profile 100 m effect occurs in only five selected users and has very wide uncertainty; it must not be used to tune toward stricter thresholds.

### 6. BCL-primary / historical-OSM-support-only result

At 100 m in the frozen nine-user panel:

- BCL candidate context: 4 / 9;
- BCL candidate-favoring vs same-user peers: 4 / 9;
- BCL peer-favoring: 5 / 9;
- BCL-favoring with mapped OSM candidate context support: 1 / 4;
- BCL-favoring with OSM candidate-favoring support: 1 / 4;
- BCL-favoring without mapped OSM candidate context: 3 / 4;
- strict Stage-05c behavior + BCL-favoring: 0;
- weaker behavior-directional-majority + BCL-favoring: 2.

This supports the revised OSM interpretation:

- three of four BCL-positive candidates simply lack mapped historical OSM candidate context;
- that absence should not be treated as contradiction.

However, dropping OSM's negative weight does not validate OFFICE:

- BCL itself is split 4 candidate-favoring versus 5 peer-favoring users;
- no user combines the primary Stage-05c behavioral criterion with BCL candidate-favoring evidence.

## Stage 07i decision

The original concern separates into two different conclusions.

### Production OFFICE

The frozen OFFICE gate is indeed **conservative in coverage**.

Small share/margin relaxations can emit additional users while retaining all 16 frozen OFFICE users.

But Stage 07i does not find independent semantic evidence that validates those additional emissions.

Therefore:

- it is reasonable to describe current OFFICE as an abstention-heavy conservative policy;
- it is not justified to relax production OFFICE gates from this audit alone.

### Stable-secondary / WORK-like structure

The frozen nine-user stable-secondary core is relatively robust to nearby support/stability gates.

Broad joint relaxation changes cohort identity and increases multi-anchor ambiguity rather than revealing a larger version of the same stable cohort.

BCL evidence does not improve under relaxed mobility profiles.

Therefore the null/mixed WORK/OFFICE semantic conclusion is not primarily caused by the stable-secondary thresholds being too strict.

### POI radius

100 m is not the reason the BCL result is weak.

Expanding to 125–150 m increases raw context but not candidate-specific advantage.

### Current recommendation

Keep production thresholds frozen.

If OFFICE coverage is a product requirement, the next useful audit is not another global threshold relaxation. It is a targeted **near-miss OFFICE audit** of users added by small one-step relaxations such as:

- same dates/share with margin 0.05;
- same dates/margin with share 0.20.

Those candidates should be evaluated for behavioral persistence and identity stability before any production policy change.
