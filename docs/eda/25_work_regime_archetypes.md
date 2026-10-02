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
