# Stage 07 — Work-Regime / Occupational-Mobility Archetypes

## Motivation

The project has repeatedly shown that a single fixed-OFFICE assumption is too narrow:

- Stage 03a found a 23-user mobility-complexity cohort where all 23 users had multiple anchors and all 23 abstained under frozen OFFICE;
- Stage 05b found stable secondary, multi-anchor, unstable and insufficient states rather than one universal WORK pattern;
- Stage 05c found that secondary-anchor persistence does not converge strongly enough with independent commute-like evidence to promote those anchors to OFFICE;
- Stage 06 showed that recurring OD / departure habits can exist without workplace semantics;
- Stage 06d closed broad within-user change detection, but it did not invalidate descriptive routine or anchor structure.

The next question is therefore not: What exact occupation does this user have?

The Stage-07 question is: Do different users exhibit different work-related mobility structures that imply different WORK representations?

## Semantic boundary

Stage 07 is research-only. It does not infer job title, occupation, employment status, true workplace, or semantic POI ground truth.

Names such as fixed_site_like or route_centric_mobile_like describe mobility structure only.

## Inputs

Reuse audited private/aggregate artifacts:

- Stage 03a: user behavior features, anchor-count class, stable-shifted candidate flag, mobile-work-like candidate flag;
- Stage 05b: HOME consensus tier and 42-day adaptive secondary-anchor pattern;
- Stage 05c: optional independent evidence for the stable-secondary subset;
- Stage 06: user-level route / OD recurrence summary.

No raw GeoLife rescan is needed.

## Primary taxonomy

### shifted_fixed_site_like

Evidence: stable secondary anchor plus Stage-03a shifted-schedule evidence.

Recommended WORK representation: one recurring work-anchor candidate with schedule-agnostic timing semantics.

### fixed_site_like

Evidence: stable secondary anchor without shifted-schedule evidence.

Recommended representation: one recurring work-anchor candidate. This is not an OFFICE label.

### route_centric_mobile_like

Evidence: mobile-complexity candidate plus multiple-anchor structure plus repeated OD edge.

Recommended representation: recurrent route / activity region rather than one workplace point.

### multi_site_recurring

Evidence: multi-anchor structure plus repeated OD evidence, without satisfying the more specific route-centric condition.

Recommended representation: a set of recurring work-like anchors.

### irregular

Evidence includes unstable adaptive secondary pattern, or multi-anchor/mobile-complexity state without repeated-route support.

Recommended representation: abstain from fixed workplace inference.

### insufficient

No supported regime evidence. Recommended representation: abstain.

## Why this is different from an occupation classifier

The taxonomy answers: How should WORK be represented for this mobility history?

It does not answer: What job does this person have?

A route-centric regime could be compatible with many real occupations. A fixed-site regime could also correspond to many occupations. GeoLife does not contain the ground truth required to distinguish them.

## Validation strategy

Because there is no occupational ground truth, Stage 07 must not report classification accuracy.

Instead report:

1. population coverage by archetype;
2. overlap with upstream anchor states;
3. route-recurrence evidence per archetype;
4. HOME-context availability;
5. independent Stage-05c evidence where available;
6. representation counts: single anchor / anchor set / route-region / abstain.

The goal is to determine whether the taxonomy produces coherent, interpretable mobility regimes without contradicting prior audits.

## Next gate

If measured archetypes have meaningful support and the evidence composition is coherent, the next step is external semantic enrichment:

- map recurring anchors / activity regions to coarse POI or land-use context;
- test whether external context adds evidence for work-like semantics;
- keep mobility archetype and external semantic evidence as separate axes.

External context is required before making stronger WORK/POI semantic claims.

## Measured result — 2026-10-02

The executed Stage-07 notebook joined:

- 182 Stage-03a behavior users;
- 25 Stage-05b work-pattern users;
- 107 Stage-06 routine users;
- 7 Stage-05c independent-evidence users.

### Archetype distribution

| regime | users | share |
|---|---:|---:|
| insufficient | 110 | 60.4% |
| irregular | 48 | 26.4% |
| multi_site_recurring | 9 | 4.9% |
| route_centric_mobile_like | 8 | 4.4% |
| fixed_site_like | 7 | 3.8% |

No user was assigned shifted_fixed_site_like.

Only 24 / 182 users (13.2%) receive a non-abstaining WORK representation. The remaining 158 / 182 (86.8%) map to insufficient-evidence or abstain-fixed-workplace states.

### Evidence coherence

Some distinctions are informative:

- multi_site_recurring: repeated-route evidence for 9/9 users, median 11 distinct edges, median 2 repeated edges;
- route_centric_mobile_like: repeated-route evidence for 8/8, mobile-complexity evidence for 8/8, median 24.5 distinct edges and median edge entropy 4.40;
- fixed_site_like: stable-secondary evidence for 7/7 and HOME context for 7/7.

However, the mutually-exclusive taxonomy also exposes an important structural problem:

- fixed_site_like has multi_anchor_state for 7/7 users;
- route_centric_mobile_like includes stable_single_secondary for 2/8 users;
- one route-centric user and one multi-site user also carry shifted-schedule evidence;
- fixed_site_like has independent Stage-05c evidence for 5/7, but median top-1 independent evidence axes is only 1.0.

Therefore the evidence axes are not mutually exclusive. A user can simultaneously have a stable dominant secondary anchor, multiple recurring anchors, repeated routes, and shifted timing.

### Decision

Do not treat the Stage-07 v1 labels as a final occupational-mobility taxonomy.

The integration audit succeeds as a diagnostic: it shows that different WORK representations are plausible and that route complexity separates some users strongly. But it also shows that site topology, route topology, and schedule timing are overlapping dimensions rather than one categorical variable.

Next step: Stage 07b — factorized work-regime profiles.

Represent each user on separate audited axes:

1. anchor/site structure;
2. route recurrence / route complexity;
3. schedule-shift evidence;
4. mobile-complexity evidence;
5. HOME-context support;
6. independent secondary-anchor evidence.

Only after this factorization should external POI / land-use context be added as a separate semantic axis.

