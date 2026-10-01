# Stage 05 Home/Office reliability handoff

## Why Stage 05 changed

Historical OSM enrichment completed at the network layer but was too sparse for semantic validation. At the primary 150 m radius, most emitted HOME/OFFICE anchors remained unknown, so current/historical map context is no longer the primary validation path.

Stage 05 now tests the behavioral reliability of HOME/OFFICE inference directly.

## What is frozen

Do not reopen unless a specific failure requires it:

- CP1 cleaning and stay detection;
- complete-link 200 m location representation;
- frozen Beijing semantic geography/timezone policy;
- production baseline as the 27 HOME / 16 OFFICE comparator.

## New implementation

Run notebook:

- notebooks/05_home_office_reliability_validation.ipynb

Analysis helper analysis/05_home_office_reliability.py provides:

- full-period candidate ranking for the fixed-window comparator;
- a HoWDe-inspired observed-hour proportional ranker;
- a schedule-light recurrence comparator;
- pairwise cross-method agreement;
- first/second-half and odd/even-week test–retest reliability;
- 60/40 held-out predictive-persistence audit;
- 10/20/30% stay-dropout robustness;
- +12 h schedule-sensitivity stress;
- a small deterministic synthetic self-check.

The analysis intentionally reuses full-data frozen location IDs when splitting time. This means Stage 05 evaluates semantic reliability conditional on the frozen spatial representation, not clustering reliability. Stage 04 already owns the latter question.

## Run order

1. Load the private frozen CP1 stay cache.
2. Run build_semantic_locations() with complete-link 200 m.
3. Reproduce production baseline parity.
4. Run the synthetic self-check.
5. Measure candidate coverage by method.
6. Run cross-method agreement.
7. Run both split-half tests.
8. Run held-out predictive validity.
9. Run dropout robustness.
10. Run +12 h stress.
11. Save aggregate tables separately from private user-level details.

## Expected parity gate

The analysis should stop if production baseline no longer gives:

- HOME: 27;
- OFFICE: 16.

These counts are a reproducibility checkpoint only. New candidate counts are allowed to be larger.

## What not to claim

Do not describe:

- split-half agreement as accuracy;
- held-out persistence as semantic ground truth;
- recurrence candidates as occupations;
- HoWDe's published accuracy as expected GeoLife accuracy;
- +12 h invariance as mandatory for every HOME/WORK detector.

## Next decision

After the run, compare methods on:

- candidate coverage;
- split-half agreement;
- held-out top-1 persistence;
- dropout retention;
- cross-method convergence;
- schedule sensitivity.

Only then decide whether the next semantic model should be:

- the existing conservative fixed baseline;
- a proportional/coverage-aware static rule;
- a sliding-window adaptive rule;
- or an explicit uncertainty/abstention ensemble.
