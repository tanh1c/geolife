# Home/Office reliability validation

## Status

Stage 05 is pivoted from external POI validation to internal behavioral reliability validation.

The historical-OSM experiment completed technically, but historical coverage was too sparse to act as a useful semantic validator. The new question is:

> Without HOME/OFFICE ground truth, how stable, predictive, and method-independent are the inferred labels?

The frozen 27 HOME / 16 OFFICE output is retained only as a comparator/parity checkpoint. It is not a target count and does not cap candidate coverage.

## Frozen foundations

This stage does not reopen:

- CP1 cleaning;
- stay-point detection;
- the complete-link 200 m spatial representation;
- the Beijing-focused production geography/timezone policy.

The primary reliability cohort is therefore conditional on the frozen semantic representation. Broader behavior-EDA anchor counts from the all-resolved timezone path are not silently mixed into this cohort.

## Methods

Three deliberately different labelers are compared.

### 1. fixed_window

The current production candidate ranking:

- HOME evidence from the frozen night window;
- OFFICE evidence from the frozen weekday daytime window;
- final production share/margin gates are recorded separately as emitted.

For reliability comparisons, the top supported candidate is retained even if the final production emission gate abstains.

### 2. howde_style

A lightweight design inspired by HoWDe, not a reproduction of its PySpark package and not a transfer of its validated accuracy to GeoLife.

- convert stay intervals to a dominant location per observed hourly bin;
- HOME window: 00:00–06:00;
- OFFICE window: weekday 09:00–16:00;
- require at least 40% observed hourly-bin coverage for a day;
- rank HOME by mean within-observed-hour fraction;
- rank OFFICE primarily by fraction of valid workdays visited;
- require at least three valid days and at least two stays at the candidate location.

No HoWDe location-selection threshold is imported as a GeoLife truth gate in this first audit.

### 3. recurrence

A schedule-light control:

- HOME candidate = recurring location with the largest total dwell;
- OFFICE candidate = strongest alternate location by weekday recurrence;
- the OFFICE candidate must have at least three weekday support dates.

This comparator is intentionally less clock-dependent. It is not assumed to be semantically correct.

## Reliability axes

### A. Candidate coverage

Measure how many users each method can rank before treating any method as truth.

Purpose: test whether 27/16 is mostly an emission-policy outcome rather than the natural ceiling of recurring-location evidence.

### B. Cross-method agreement

For users where two methods both produce a label, measure whether they choose the same location_id.

High agreement is convergent behavioral evidence, not ground truth.

### C. Split-half test–retest reliability

Two partitions:

- first half of observed dates vs second half;
- odd ISO weeks vs even ISO weeks.

Clustering remains frozen from the full semantic representation. This isolates semantic-assignment stability rather than re-testing spatial clustering.

### D. Held-out predictive validity

Per user:

- first 60% of observed dates: infer candidate;
- last 40%: freeze the candidate and evaluate persistence.

Metrics:

- HOME: held-out dwell-share rank;
- OFFICE: held-out weekday-visit-day-share rank;
- share of candidates still ranked number 1 in the unseen period.

This is predictive persistence, not semantic accuracy.

### E. Missing-data robustness

Randomly remove 10%, 20%, and 30% of stay events under deterministic seeds and measure candidate retention.

This directly audits sensitivity to GeoLife's uneven observation support.

### F. +12 h time-shift stress

Shift local timestamps while preserving physical locations.

This is reported as schedule dependence:

- recurrence acts as a schedule-light control;
- fixed_window and howde_style are expected to be clock-sensitive by design.

The test is not interpreted as a requirement that every valid HOME/WORK method must be invariant to schedule shifts.

## Interpretation rules

Do not choose a method merely because it emits more users.

- high coverage + low reliability -> over-eager;
- low coverage + high reliability -> conservative but stable;
- high split-half reliability + held-out persistence -> stronger behavioral evidence;
- large cross-method disagreement -> method-dependent semantics;
- dropout sensitivity -> observation-support dependence;
- time-shift sensitivity -> schedule dependence.

None of these axes alone establishes HOME/OFFICE ground truth.

## Source-derived lessons

### Andrade, Cancela & Gama (2019), arXiv:1909.11406

The paper defines meaningful places from repeated mobility observations without requiring external POI semantics, uses 200 m / 20 min stay-point parameters in its experiment, and explicitly highlights DBSCAN chaining as undesirable for location-like clusters. On GeoLife user 004, it reports 2,437 stay points, 50 meaningful places, and interprets the top two frequent places as Home and Work.

Project lesson:

- external map semantics are optional for discovering recurrent structure;
- recurring-place compactness and repeated movement habits are first-class evidence;
- the paper's user-004 interpretation is a sanity reference, not GeoLife-wide ground truth;
- the DBSCAN-chaining warning is consistent with our Stage 04 decision to retain complete-link 200 m.

### Dong et al. (2022), arXiv:2204.12865

The paper detects stays with 200 m / 10 min, clusters with DBSCAN MinPoint=1, then uses 28 individual/cluster/POI features and self-reported HOME/WORK labels to train XGBoost. Its feature table includes weekday/weekend ratios, day/night ratios, within-user location shares, transfer-matrix counts, and only two POI feature families.

Project lesson:

- the spatial threshold alone is not the semantic classifier;
- transition and recurrence features provide independent behavioral evidence;
- POI is auxiliary rather than the entire validation strategy;
- their reported supervised accuracy must not be transferred to GeoLife because we do not have their self-reported labels.

### De Sojo et al. (2025), HoWDe, arXiv:2506.20679

HoWDe separates temporal coverage from location-selection evidence, represents stop sequences in hourly bins, uses proportions rather than absolute observed time, supports abstention, and evaluates an explicit accuracy-versus-non-detection trade-off. The paper also states two limitations relevant here: it does not infer semantic purpose beyond HOME/WORK temporal behavior, and one run assumes a single dominant lifestyle pattern rather than directly resolving rotating night-shift schedules.

Project lesson:

- support quality and semantic score should be separate dimensions;
- abstention is an expected output, not a failure;
- proportional observed-time features are preferable to raw counts when support is uneven;
- dynamic/sliding-window behavior is a strong follow-up if static reliability is weak;
- do not claim occupation, and do not claim HoWDe already solves all shift-work regimes.

## Implementation

Analysis helper:

- analysis/05_home_office_reliability.py

Modal orchestration notebook:

- notebooks/05_home_office_reliability_validation.ipynb

Private Modal outputs should remain under:

- /mnt/geolife-data/cache/05_home_office_reliability_validation/

No precise HOME/OFFICE coordinates or raw user-level reliability details should be committed.

## Exit criteria

Before changing production inference, require:

1. frozen baseline parity still reproduces 27 HOME / 16 OFFICE;
2. candidate coverage is measured independently of final baseline emission gates;
3. split-half, held-out, dropout, and cross-method summaries are complete;
4. results are interpreted as reliability evidence rather than accuracy;
5. a separate decision is made on whether an adaptive/sliding-window model is justified.
