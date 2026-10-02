# Stage 07b — Factorized Work-Regime Profiles\n\n## Why 07b exists\n\nMeasured Stage 07 v1 showed that the evidence dimensions are not mutually exclusive:\n\n- 7/7 fixed-site-like users were also multi-anchor-state users;\n- 2/8 route-centric/mobile-like users also had stable-single-secondary evidence;\n- shifted evidence appeared inside route/multi-site users rather than forming a separate class.\n\nTherefore site topology, route topology, schedule timing, and mobility complexity should be represented as separate axes.\n\n## Research question\n\nCan each user be described by a factorized occupational-mobility profile that preserves overlapping evidence without converting it into an occupation label?\n\n## Inputs\n\nReuse exactly the Stage-07 upstream artifacts:\n\n- Stage 03a behavior features;\n- Stage 05b HOME consensus and adaptive work patterns;\n- optional Stage 05c independent secondary-anchor evidence;\n- Stage 06 user-level routine summary.\n\nNo raw GeoLife rescan is required.\n\n## Factorized axes\n\n### 1. Site / anchor structure\n\n- anchor_count_class;\n- stable secondary present;\n- multiple recurring anchors present;\n- adaptive multi-anchor state;\n- unstable adaptive state;\n- dominant-window share;\n- distinct top locations.\n\nThese flags may overlap.\n\n### 2. Route / OD structure\n\n- repeated route present;\n- distinct edge count;\n- repeated edge count;\n- edge entropy;\n- top-edge day share;\n- top-edge transition share;\n- departure-time concentration;\n- descriptive route-complexity percentile.\n\nThe percentile is descriptive only. It is not a semantic threshold.\n\n### 3. Schedule structure\n\n- shifted-schedule evidence;\n- arrival-hour concentration;\n- dominant-hour shift.\n\n### 4. Mobility complexity\n\n- mobile-complexity evidence from Stage 03a;\n- movement distance / usable day;\n- movement-duration proxy / usable day.\n\n### 5. HOME context\n\n- HIGH/MEDIUM HOME consensus available or not.\n\n### 6. Independent secondary-anchor evidence\n\n- evidence available;\n- valid evidence axes;\n- top-1 evidence axes;\n- beats-peer-median axes.\n\nStage-05c negative/mixed evidence is preserved rather than overwritten.\n\n## Representation candidates\n\nRepresentation is now multi-label:\n\n- candidate_single_anchor_geometry: stable secondary exists;\n- candidate_anchor_set_geometry: multiple recurring/adaptive anchors exist;\n- candidate_route_region_geometry: repeated route plus mobile/multi-site context;\n- schedule_agnostic_needed: shifted evidence exists.\n\nA user may receive several options simultaneously.\n\nExample:\n\nsingle_anchor + anchor_set + route_region + schedule_agnostic\n\nis a valid factorized profile, not a conflict.\n\n## Aggregate outputs\n\nStage 07b reports:\n\n1. upstream support coverage;\n2. prevalence of each axis;\n3. pairwise overlap / conditional overlap between axes;\n4. common evidence signatures;\n5. common representation signatures.\n\n## Semantic boundary\n\nStage 07b does not infer occupation, employment status, true WORK, OFFICE, or semantic POI labels.\n\n## Gate to external POI / land-use enrichment\n\nExternal enrichment is justified only after the factorized profile is measured.\n\nThe POI layer must remain independent:\n\n- mobility determines the profile geometry;\n- external POI / land-use adds semantic context;\n- POI must not be used to retroactively redefine mobility axes.\n

## Measured result — 2026-10-02

The Stage-07b notebook executed on the same frozen upstream artifacts:

- 182 behavior users;
- 25 adaptive work-pattern users;
- 107 routine users;
- 25 users with HIGH/MEDIUM HOME context;
- 7 users with Stage-05c independent secondary-anchor evidence.

### Axis prevalence

| axis | users | population share |
|---|---:|---:|
| site_multiple_recurring | 72 | 39.6% |
| home_context_supported | 25 | 13.7% |
| mobile_complexity_evidence | 23 | 12.6% |
| route_repeated | 23 | 12.6% |
| site_stable_secondary | 9 | 4.9% |
| independent_secondary_evidence_available | 7 | 3.8% |
| site_adaptive_multi_anchor | 3 | 1.6% |
| schedule_shifted_evidence | 2 | 1.1% |
| site_unstable | 1 | 0.5% |

### Key overlap

The measured overlaps confirm that factorization is the correct abstraction:

- stable secondary AND multiple recurring: 9 users;
- stable secondary AND repeated route: 7 users;
- multiple recurring AND repeated route: 22 users;
- shifted schedule AND repeated route: 2 users.

Additional conditional structure:

- all 23 mobile-complexity users are multiple-recurring users;
- 22/23 repeated-route users are multiple-recurring;
- all 9 stable-secondary users are multiple-recurring;
- all 9 stable-secondary users have supported HOME context;
- all 7 users with Stage-05c independent evidence are stable-secondary users.

The v1 apparent category conflicts are therefore genuine multi-axis structure, not classification noise.

### Representation signatures

| representation signature | users | share |
|---|---:|---:|
| abstain | 110 | 60.4% |
| anchor_set | 48 | 26.4% |
| anchor_set + route_region | 13 | 7.1% |
| single_anchor + anchor_set + route_region | 7 | 3.8% |
| single_anchor + anchor_set | 2 | 1.1% |
| anchor_set + route_region + schedule_agnostic | 2 | 1.1% |

No user has a standalone single-anchor representation. Every stable-secondary user also has broader recurring-anchor structure.

### Decision

Stage 07b validates the factorized representation.

Do not collapse the axes back into one work-regime class.

The factorized profile should be the mobility-side input to external semantic enrichment.

However, external POI / land-use lookup should not be applied indiscriminately to all 182 users. The first semantic-enrichment audit should use a support-qualified subset where candidate geometry is interpretable and HOME exclusion is available.

Primary Stage-07c scope:

- the 25 users with supported HIGH/MEDIUM HOME context;
- candidate non-HOME recurring anchors derived from the same frozen 200 m behavior representation;
- explicitly retain the 9 stable-secondary users and the route/multi-anchor subsets inside those 25 users;
- attach coarse external POI / land-use context as a new independent evidence axis.

The external layer must not alter the factorized mobility axes.

