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

## Measured result — 2026-10-01

### Comparator support

Of the nine Stage-05b stable-secondary users, seven had at least one recurring non-HOME peer with >=3 active days and >=2 stays. Median comparator count was four.

### Independent evidence axes

| metric | top-1 users | top-1 share | median candidate - peer median |
|---|---:|---:|---:|
| weekday-weekend visit contrast | 5/7 | 71.4% | +0.198 |
| HOME-pair transition-day share | 3/7 | 42.9% | +0.102 |
| arrival-hour concentration | 0/7 | 0% | -0.181 |
| dwell-duration regularity | 0/7 | 0% | -0.092 |

The candidate anchors therefore show some weekday/transition signal, but not consistent schedule/dwell regularity relative to same-user peers.

### Multi-axis convergence

- 0/7 users were top-1 on >=3 axes;
- 1/7 was top-1 on exactly 2 axes;
- 6/7 were top-1 on only 0-1 axes.

Three users beat their peer median on >=3 axes, but this weaker criterion does not change the lack of top-rank convergence.

### Bootstrap

All candidate-minus-peer-median 95% bootstrap intervals crossed zero:

- weekday contrast: median +0.198, CI [-0.113, +0.292];
- HOME-pair transition share: +0.102, CI [-0.083, +0.333];
- arrival concentration: -0.181, CI [-0.341, +0.178];
- dwell regularity: -0.092, CI [-0.231, +0.059].

### Peer-support sensitivity

The primary conclusion is stable at permissive comparator rules:

- >=2 active days: 9 comparable users, 0 with >=3 top axes;
- >=3 active days: 7 users, 0 with >=3 top axes.

At >=5 days the sample collapses to three users and one reaches >=3 axes; this is too small to overturn the primary result.

## Stage 05c decision

Independent evidence remains mixed and does not converge strongly enough to relabel persistent secondary anchors as OFFICE/WORK.

Close semantic WORK expansion. Keep stable_secondary_anchor as a descriptive mobility state. A future track may study routines or behavioral change without requiring workplace semantics.
