# Stage 06b — Routine representation robustness

## Why 06b exists

The executed Stage 06 run found useful routine structure but also three reasons not to move directly into behavioral change detection:

- repeated-OD coverage fell from 23 users at >=2 active days to 9 at >=3 days and 2 at >=5 days;
- only 6/45 users with a dominant OD in both chronological halves kept the exact same top edge;
- departure-time GMMs were supported for only 11 edges from 2 users, with 8/11 selecting three components under the permissive Stage-06 rule.

The Stage-06 collapsed-sequence motif comparator also allowed a user with only one usable day to appear 100% repeatable.

## Primary design

06b keeps the frozen CP1 and complete-link 200 m behavior representation unchanged.

### Support-aware motif comparison

Primary common support universe:

- at least 6 usable motif days;
- repeated directed OD: same edge on at least 3 active days;
- supported collapsed-sequence motif: top motif on at least 3 days and at least 50% of usable days.

The name "collapsed-sequence motif" is intentional: this is not identical to the original 03a exact motif representation.

### Distributional split-half stability

Exact top-1 equality is retained only as one diagnostic. Primary distribution metrics are:

- Jensen-Shannon divergence;
- weighted Jaccard similarity;
- total variation distance;
- top-3 edge-set Jaccard.

### Random-partition calibration

For each comparable user, the chronological first/second-half split is compared with 200 random balanced partitions of the same supported dates.

A chronological JSD above the user's random-partition p95 is treated as drift-like evidence beyond sampling-only partition variability. It is not a labeled real-world event.

### Departure-time bootstrap

Departure time is reduced to one circular-mean hour per edge-day. Active days are then bootstrapped, producing a 95% interval for circular concentration.

This prevents two nearly identical observations from being treated as strong routine evidence without uncertainty.

### Stricter multimodality

Primary strict GMM requirements:

- >=5 active days;
- >=8 transitions;
- BIC gain versus one component >=10;
- every component weight >=0.20;
- minimum circular center separation >=2 hours.

Sensitivity varies active-day support, BIC gain, component weight, and separation.

## Decision rule

06b does not create a single readiness score.

Stage 07 should only proceed after inspecting support retention, distributional split stability, random-partition calibration, departure-time bootstrap strength, and strict multimodal stability jointly.
