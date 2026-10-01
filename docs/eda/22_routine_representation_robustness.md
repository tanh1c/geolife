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

## Measured result — 2026-10-01

### Fair-support routine coverage

On the primary >=6-usable-day universe (51 users):

- directed OD repeated on >=3 active days: 8 users;
- collapsed-sequence motif repeated on >=3 days and >=50% usable-day share: 9 users;
- current overlap: 0 users.

The overlap must not be over-interpreted because the current motif comparator permits single-location motifs with no transition. It is therefore a repeated-day-pattern comparator, not yet a fully matched mobility-routine comparator.

### Exact-OD distribution stability

Among 45 users with comparable first/second-half edge distributions:

- same dominant edge: 13.3%;
- median JSD: 1.0;
- median weighted Jaccard: 0.0;
- median total variation: 1.0;
- median top-3 edge-set Jaccard: 0.0.

### Sampling-null calibration

Balanced random day partitions are equally unstable:

- median chronological JSD: 1.0;
- median random-partition JSD: 1.0;
- median chronological-minus-random JSD: 0.0;
- only 2/45 users exceed the random-partition p95.

Thus the exact-OD space is sparse enough that disjoint halves occur even without preserving chronology. High chronological JSD is therefore not broad evidence of behavior change.

### Departure-time robustness

At 3-4 active days, 13 edges from 8 users have median concentration 0.888 and median bootstrap lower bound 0.823.

At >=5 active days, 12 edges from only 2 users have median concentration 0.964 and median bootstrap lower bound 0.944. Nine of those twelve strong edges retain a lower bound >=0.7.

Clock regularity can therefore be strong conditional on support, but its broad coverage is very small.

### Strict multimodality

Under the primary strict gate, six edges from one user are modeled and one edge is strict multimodal. Relaxed sensitivity reaches at most two users, so population-level multimodal claims are not supported.

## Stage-06b decision

Do not launch broad Stage-07 change detection on exact OD identities.

The representation is currently support-limited: random balanced partitions are nearly as disjoint as chronological halves. A next step should quantify temporal-window feasibility and/or use coarser support-normalized behavioral features before attempting change-point detection.