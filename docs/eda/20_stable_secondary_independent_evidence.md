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


## CP2-v2 Stage 05c refresh — 2026-10-04

Stage 05c was rerun after the CP2-v2 Stage-05b refresh.

The 2026-10-01 section above remains historical Beijing-v1 evidence. The current CP2-v2 production-dependent measurements are below.

### Cohort and comparator support

The stable-secondary cohort is unchanged:

- stable-secondary users: 9;
- historical Beijing-v1 stable-secondary users: 9;
- CP2-v2 delta: 0.

Under the primary peer rule (>=3 active days, >=2 stays):

- 7 / 9 stable-secondary users have at least one fair recurring non-HOME peer;
- median comparator anchors: 4.

This exactly preserves the primary comparator-support size from the historical run.

### Independent evidence axes

| metric | top-1 users | top-1 share | beats peer median | median candidate - peer median |
|---|---:|---:|---:|---:|
| weekday-weekend visit contrast | 5/7 | 71.4% | 5/7 | +0.188 |
| HOME-pair transition-day share | 3/7 | 42.9% | 5/7 | +0.102 |
| arrival-hour concentration | 0/7 | 0% | 3/7 | -0.168 |
| dwell-duration regularity | 0/7 | 0% | 3/7 | -0.057 |

Relative to the historical Beijing-v1 run, the directional pattern is unchanged:

- weekday/transition evidence is modestly positive;
- arrival-time and dwell-regularity evidence do not support stable-secondary anchors as uniquely regular WORK-like places.

The median differences shift slightly because the CP2-v2 semantic location universe changes the same-user peer set for some users, but no evidence axis changes qualitative direction.

### Multi-axis convergence

Primary >=3-active-day comparator:

- 0 / 7 users are top-1 on >=3 evidence axes;
- 1 / 7 is top-1 on exactly 2 axes;
- 6 / 7 are top-1 on only 0-1 axes.

The absence of strong top-rank multi-axis convergence is identical to the historical result.

### Paired bootstrap

All candidate-minus-peer-median 95% bootstrap intervals still cross zero:

- weekday contrast: median +0.188, CI [-0.083, +0.261];
- HOME-pair transition share: +0.102, CI [-0.083, +0.333];
- arrival concentration: -0.168, CI [-0.341, +0.178];
- dwell regularity: -0.057, CI [-0.231, +0.059].

The strongest directional signals remain weekday contrast and HOME-pair transition share, but the seven-user sample does not support a strong semantic conclusion.

### Peer-support sensitivity

The support-sensitivity pattern is unchanged:

- >=2 active days: 9 comparable users, median 5 peers, 0 with >=3 top axes;
- >=3 active days: 7 comparable users, median 4 peers, 0 with >=3 top axes;
- >=5 active days: 3 comparable users, median 1 peer, 1 with >=3 top axes.

The >=5-day result remains too small to overturn the primary result.

### Relationship to static OFFICE candidates

Among the 7 users with fair comparators:

- adaptive dominant secondary matches fixed-window OFFICE for 3 users and differs for 4;
- matches HoWDe-style OFFICE for 2 and differs for 5;
- matches recurrence OFFICE for 6 and differs for 1;
- matches baseline-emitted OFFICE for 3 and differs for 4.

For every static-match stratum, the median top-1 evidence-axis count remains 1 and no stratum contains a user with >=3 top axes.

Thus agreement with a static OFFICE candidate does not rescue the weak independent multi-axis evidence.

## CP2-v2 Stage 05c decision

The Stage-05c decision is unchanged:

1. Independent evidence remains mixed.
2. Persistent secondary anchors do not show strong enough multi-axis convergence to justify WORK/OFFICE semantics.
3. Close semantic WORK/OFFICE expansion.
4. Keep stable_secondary_anchor as a descriptive mobility state.
5. Preserve the 9-user cohort and private comparison artifacts for downstream factorized profiling.
6. Proceed to Stage 07b factorized work-regime profiles, reusing Stage-03a behavior features, Stage-06 routine summaries, CP2-v2 Stage-05b artifacts, and the refreshed Stage-05c comparison artifact.

The CP2-v2 refresh therefore strengthens the robustness of the negative semantic conclusion: despite a broader all-resolved location universe upstream, the stable-secondary cohort and its lack of strong independent WORK-like convergence remain essentially unchanged.
