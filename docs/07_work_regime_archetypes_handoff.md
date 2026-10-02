# Stage 07 handoff — Work-Regime / Occupational-Mobility Archetypes

## Purpose

Compose already-audited GeoLife evidence into descriptive work-regime hypotheses.

Do not infer occupation or job title.

## Required inputs

Primary private artifacts:

- Stage 03a: user_behavior_features.csv
- Stage 05b: home_consensus_private.pkl
- Stage 05b: adaptive_work_patterns_42_private.pkl
- Stage 06: user_summary_private.pkl

Optional:

- Stage 05c: candidate_comparison_private.pkl

No raw trajectory rescan is required.

## Outputs

Private:

- evidence_matrix_private.pkl
- work_regime_archetypes_private.pkl

Aggregate:

- archetype_summary.csv
- representation_summary.csv
- upstream_overlap.csv
- evidence_summary.csv

## Regimes

- shifted_fixed_site_like
- fixed_site_like
- route_centric_mobile_like
- multi_site_recurring
- irregular
- insufficient

## Representation recommendations

- shifted fixed-site -> single_work_anchor_schedule_agnostic
- fixed-site -> single_work_anchor_candidate
- route-centric -> route_or_activity_region
- multi-site -> work_anchor_set
- irregular -> abstain_fixed_workplace
- insufficient -> abstain_insufficient_evidence

These recommendations are representation choices, not workplace truth.

## Interpretation rules

Do not rename fixed_site_like to OFFICE.
Do not rename route_centric_mobile_like to driver, salesperson, courier, or another occupation.
Do not rename multi_site_recurring to multi-office employee.

The data do not support those semantic claims.

## Next step after measured run

If the taxonomy has useful coverage and coherent upstream evidence, add external POI / land-use context as an independent semantic axis.

That external step should ask whether a mobility-defined anchor or activity region is compatible with work-related place categories; it should not use POI context to retroactively redefine the mobility archetype.

## Measured result — 2026-10-02

Executed population:

- behavior users: 182;
- adaptive work-pattern users: 25;
- routine users: 107;
- independent Stage-05c evidence users: 7.

V1 output:

- insufficient: 110;
- irregular: 48;
- multi_site_recurring: 9;
- route_centric_mobile_like: 8;
- fixed_site_like: 7;
- shifted_fixed_site_like: 0.

Only 24 users receive a non-abstaining WORK representation.

Important overlap finding:

- all 7 fixed_site_like users also have multi_anchor_state;
- 2 route_centric_mobile_like users also have stable_single_secondary;
- shifted evidence appears inside route/multi-site users rather than forming an independent shifted-fixed class.

This means the v1 mutually-exclusive archetypes combine several non-orthogonal evidence dimensions.

## Handoff decision

Do not merge the v1 categories into a semantic WORK taxonomy or infer occupation from them.

Keep the v1 result as an integration diagnostic and proceed to Stage 07b factorized work-regime profiles.

Stage 07b should preserve separate axes for:

- dominant/stable secondary-anchor evidence;
- multiple recurring-anchor evidence;
- repeated-route evidence;
- route complexity;
- shifted-schedule evidence;
- mobile-complexity evidence;
- HOME context;
- optional Stage-05c independent evidence.

External POI / land-use enrichment should follow the factorized profile, not the current mutually-exclusive label.

