# Stage 05c — Stable secondary-anchor independent evidence audit

## Status

Stage 05c follows the measured Stage-05b result.

Stage 05b reduced the adaptive WORK-like question to a small subset:

- 25 users with HIGH/MEDIUM HOME consensus;
- 9 users with a stable secondary anchor under the primary 42-day / 14-day-step audit;
- static OFFICE agreement remained weak enough that stable secondary anchors must not be relabeled as OFFICE.

Stage 05c therefore does not tune another global threshold and does not change production inference.

## Question

For the nine stable-secondary users:

> Does the persistent non-HOME anchor also stand out relative to other recurring non-HOME anchors from the same user on evidence that was not used as the primary Stage-05b selection rule?

## Evidence axes

The primary within-user comparison uses four axes:

1. weekday-vs-weekend visit contrast;
2. direct HOME ↔ secondary transition-day share;
3. arrival-time concentration;
4. dwell-duration regularity.

The Stage-05b selection rule used sliding-window persistence / recurrence. Therefore the new axes are more independent than simply re-measuring persistence.

Important caveat: weekday contrast still uses the same visit history, so it is not fully independent of recurrence. Transition structure and arrival/dwell regularity are more independent of the selection rule.

## Within-user comparator

For each stable-secondary user:

- exclude the accepted HIGH/MEDIUM HOME anchor;
- retain recurring non-HOME anchors with at least three active days and at least two stays;
- compare the stable secondary anchor with those same-user peers.

The primary outputs are:

- within-user percentile;
- whether the stable candidate ranks top-1 on each axis;
- candidate minus same-user peer median.

This avoids inventing another global population threshold.

A stable candidate is only compared when at least one eligible peer anchor exists. Otherwise top-1 would be vacuous.

## Aggregate interpretation

Stage 05c reports:

- top-1 share by evidence axis;
- fraction beating the same-user peer median;
- number of users with 0/1/2/3/4 top evidence axes;
- paired bootstrap intervals for candidate-minus-peer-median differences;
- stratification by whether the adaptive anchor matches static OFFICE candidates;
- peer-support sensitivity at 2 / 3 / 5 minimum active days.

The 3+ top-axis bucket is descriptive convergence only. It is not a calibrated WORK confidence score.

## Decision boundary

Stage 05c may support:

- stronger or weaker WORK-like behavioral convergence among persistent secondary anchors.

It cannot establish:

- workplace ground truth;
- occupation;
- employment status;
- semantic accuracy.

If evidence remains mixed, retain stable_secondary_anchor as a descriptive behavioral state and close semantic WORK expansion.
