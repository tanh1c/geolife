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
