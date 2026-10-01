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


## Measured result — 2026-10-01

The run completed all planned axes and reproduced frozen parity.

Cohort:

- 5,821 CP1 stays / 136 stay users;
- 97 frozen semantic users;
- 1,111 semantic locations;
- 486 recurring locations;
- 73 recurring-anchor users.

Candidate coverage:

| method | HOME | OFFICE |
|---|---:|---:|
| fixed_window | 35 | 27 |
| howde_style | 20 | 21 |
| recurrence | 73 | 31 |

Production emissions remain 27 HOME / 16 OFFICE.

Cross-method same-location agreement:

| label | comparison | overlap | agreement |
|---|---|---:|---:|
| HOME | fixed ↔ howde | 19 | 94.7% |
| HOME | fixed ↔ recurrence | 35 | 82.9% |
| HOME | howde ↔ recurrence | 20 | 85.0% |
| OFFICE | fixed ↔ howde | 16 | 81.3% |
| OFFICE | fixed ↔ recurrence | 22 | 31.8% |
| OFFICE | howde ↔ recurrence | 20 | 15.0% |

Primary interpretation:

- HOME evidence converges across methods much more strongly than OFFICE;
- recurrence-only WORK/OFFICE expansion is rejected;
- fixed-window HOME appears conservative but reasonably stable under split and dropout stress;
- candidate expansion is not frozen yet because the current aggregate notebook does not quantify how many non-emitted HOME candidates pass a multi-axis consensus tier;
- +12 h sensitivity is reported as schedule dependence, not as semantic error.

Next run should create candidate-level consensus tiers without exposing precise coordinates:

1. at least two methods select the same HOME anchor;
2. sufficient split-half support where available;
3. candidate seen in held-out data and preferably top-1;
4. dropout retention under a selected perturbation level;
5. sliding-window status for temporally unstable cases.

For OFFICE/WORK, prioritize a sliding-window/adaptive behavior audit before any coverage expansion.
