# Stage 05b — HOME consensus tiers and adaptive WORK audit

## Status

Stage 05b follows the completed Stage-05 reliability matrix.

Stage 05 established two main findings:

- HOME assignments converge relatively strongly across fixed-window, HoWDe-style, and recurrence rankers;
- OFFICE assignments are much more method-dependent, especially when recurrence is compared with clock-window methods.

Stage 05b therefore does not tune another global OFFICE window and does not modify production inference.

## Frozen foundations

Do not reopen in this stage:

- CP1 cleaning and stay detection;
- refrozen CP2-v2 all-resolved per-stay timezone semantic representation (the 2026-10-01 Beijing-v1 measurement below is retained as historical evidence);
- complete-link 200 m locations;
- Stage-05 method definitions;
- 27 HOME / 16 OFFICE production parity.

## Part A — HOME candidate evidence tiers

Stage 05b consumes private Stage-05 detail tables:

- assignments;
- split-half details;
- held-out details;
- dropout details.

For every HOME candidate, evidence remains separated into independent axes:

1. method convergence;
2. split-half consistency;
3. held-out top-1 persistence;
4. 30% stay-dropout robustness.

Raw scores from different methods are not averaged because their scales and meanings differ.

### Tier definitions

A candidate is HIGH when:

- it is the unique method-vote winner for the user;
- at least two methods select the same location;
- split consistency has at least one confirming method;
- held-out top-1 persistence has at least one confirming method;
- 30% dropout robustness has at least one confirming method.

A candidate is MEDIUM when:

- it is the unique method-vote winner;
- at least two methods select the same location;
- at least two of the three reliability axes above have confirming evidence.

All remaining cases are UNCERTAIN.

These are transparent audit tiers. They are not calibrated probabilities and must not be described as accuracy.

Each winning candidate is also classified as:

- baseline_emitted;
- fixed_candidate_not_emitted;
- outside_fixed_candidate.

The main expansion question is how many HIGH/MEDIUM candidates lie outside baseline-emitted HOME.

## Part B — adaptive secondary-anchor audit

Only users with HIGH/MEDIUM HOME evidence are eligible for the primary WORK-like audit.

The HOME anchor is excluded. Remaining recurring locations are ranked independently inside overlapping calendar windows.

Primary setting:

- window length: 42 days;
- step: 14 days;
- minimum six stay-observed days in a window;
- secondary candidate requires at least three active days and at least two stays.

The secondary-anchor selection does not use a fixed clock range such as 09:00–17:00.

After selecting the top secondary anchor, Stage 05b measures:

- visit-day share;
- non-HOME dwell share;
- arrival-hour circular center;
- arrival-hour concentration;
- window-to-window persistence;
- switch count;
- longest same-anchor run.

The primary descriptive pattern categories are:

- stable_secondary_anchor;
- multi_anchor;
- unstable;
- insufficient.

None is equivalent to OFFICE or occupation.

## Sensitivity

The audit compares:

- 28 / 42 / 56-day windows;
- dominant-window-share thresholds 0.60 / 0.70 / 0.80.

The 42-day setting is an audit operating point, not a frozen production parameter.

## Privacy

User/location-level outputs remain in the private Modal Volume.

Repository-safe outputs are aggregate tables only. Do not commit precise inferred HOME/WORK coordinates.

## Exit criteria

Before any production change:

1. count HIGH/MEDIUM HOME candidates beyond the baseline-emitted set;
2. verify which evidence axes support those expansions;
3. confirm the expansion is not dominated by a single method;
4. inspect adaptive secondary-anchor stability under window sensitivity;
5. compare adaptive dominant anchors with static OFFICE candidates;
6. keep all conclusions as reliability/behavioral evidence because GeoLife has no semantic HOME/OFFICE ground truth.

## Measured result — 2026-10-01

### HOME: consensus expansion is small

Stage 05b found 67 unique HOME vote winners: 21 HIGH, 4 MEDIUM and 42 UNCERTAIN.

Of the 25 HIGH/MEDIUM winners, 23 were already production HOME emissions. The only two non-emitted HIGH/MEDIUM winners were both fixed-window HOME candidates that had failed the final production emission gate.

No HIGH/MEDIUM winner came from the broad outside-fixed-candidate set.

This is the key Stage-05b HOME result: recurrence can rank many more anchors, but independent reliability evidence does not support a broad expansion from 27 HOME toward the full recurring-anchor population.

### WORK-like: persistence exists in a small subset

Among the 25 HIGH/MEDIUM HOME users, the primary 42-day sliding-window audit classified 9 stable secondary anchors, 3 multi-anchor patterns, 1 unstable pattern, and 12 insufficient-support cases.

For the 13 sufficient users, the adaptive dominant anchor has limited agreement with static semantic candidates: 40.0% with fixed-window OFFICE, 28.6% with HoWDe-style OFFICE, and 54.5% with recurrence OFFICE.

This is evidence of recurring secondary-place structure, not validated workplace semantics.

### Window sensitivity

At dominant-window-share threshold 0.70:
- 28d: 10 sufficient, 6 stable, 3 multi-anchor, 1 unstable;
- 42d: 13 sufficient, 9 stable, 3 multi-anchor, 1 unstable;
- 56d: 14 sufficient, 10 stable, 3 multi-anchor, 1 unstable.

For 42d and 56d, stable-secondary counts are unchanged between 0.70 and 0.80 thresholds. Longer windows mainly improve observation sufficiency.

The result is therefore support-limited more than threshold-fragile, but the sample is too small and cross-method agreement too weak to relabel stable secondary anchors as OFFICE.

## Stage 05b decision

1. Keep production HOME/OFFICE unchanged.
2. Retain two non-emitted HIGH/MEDIUM HOME cases for targeted review only.
3. Do not expand HOME using recurrence-only candidates.
4. Do not convert stable_secondary_anchor to OFFICE.
5. If Stage 05 continues, the next narrow experiment should add independent transition and weekday/arrival regularity evidence for the stable-secondary subset, rather than search another global threshold.


## CP2-v2 Stage 05b refresh — 2026-10-04

Stage 05b was rerun after the CP2-v2 Stage-05 reliability refresh.

The 2026-10-01 section above is retained as historical Beijing-v1 evidence. The measurements below are the current CP2-v2 production-dependent result.

### HOME consensus: broader candidate universe, still narrow reliable expansion

The CP2-v2 run produced 97 unique HOME vote winners:

- 23 HIGH;
- 6 MEDIUM;
- 68 UNCERTAIN.

Historical Beijing-v1 had 67 unique winners:

- 21 HIGH;
- 4 MEDIUM;
- 42 UNCERTAIN.

Among the current HIGH/MEDIUM winners:

- HIGH: 21 baseline-emitted + 2 fixed candidates not emitted;
- MEDIUM: 3 baseline-emitted + 3 fixed candidates not emitted.

Therefore:

- 29 users have HIGH/MEDIUM HOME consensus;
- 24 of those are already baseline-emitted HOME;
- 5 HIGH/MEDIUM candidates lie outside production HOME;
- all 5 are already fixed-window candidates that failed the final production emission gate;
- no HIGH/MEDIUM expansion candidate comes from the broad recurrence-only / outside-fixed-candidate population.

Historical Beijing-v1 had only 2 such HIGH/MEDIUM expansion candidates. CP2-v2 therefore increases the targeted-review set from 2 to 5, but it still does not support broad HOME expansion toward the full recurring-anchor universe.

The uncertain tier also expands strongly:

- 7 fixed candidates not emitted;
- 61 outside-fixed-candidate winners.

This is consistent with Stage 05: broader recurring-place coverage creates more candidate structure than semantic certainty.

### Adaptive secondary-anchor audit: stable WORK-like subset does not expand

Primary setting:

- 42-day windows;
- 14-day step;
- stability threshold 0.70.

Among the 29 HIGH/MEDIUM HOME users:

- stable_secondary_anchor: 9;
- multi_anchor: 3;
- unstable: 1;
- insufficient: 16.

Historical Beijing-v1 used 25 HIGH/MEDIUM HOME users and produced:

- stable_secondary_anchor: 9;
- multi_anchor: 3;
- unstable: 1;
- insufficient: 12.

The four additional CP2-v2 HOME-consensus users therefore enter the primary adaptive audit entirely as additional insufficient-support cases. The stable, multi-anchor and unstable counts are unchanged.

This is the central Stage-05b CP2-v2 result:

> broadening the HOME-consensus cohort does not broaden the stable-secondary WORK-like cohort.

The primary sufficient subset remains 13 users.

For the 42-day sensitivity row, fixed-window OFFICE is comparable for 10 users and the adaptive dominant anchor matches it for 40.0%, unchanged from the historical result.

The rerun notebook does not print refreshed aggregate HoWDe-style or recurrence-OFFICE agreement tables, so no new values are claimed for those comparisons here.

### Window sensitivity

At stability threshold 0.70:

- 28d: 10 sufficient, 6 stable, 3 multi-anchor, 1 unstable;
- 42d: 13 sufficient, 9 stable, 3 multi-anchor, 1 unstable;
- 56d: 14 sufficient, 10 stable, 4 multi-anchor, 0 unstable.

The stable-secondary counts at 28d / 42d / 56d remain exactly 6 / 9 / 10, matching the historical run.

At 42d:

- threshold 0.60 -> 10 stable, 2 multi-anchor, 1 unstable;
- threshold 0.70 -> 9 stable, 3 multi-anchor, 1 unstable;
- threshold 0.80 -> 9 stable, 3 multi-anchor, 1 unstable.

Thus the primary stable count remains insensitive to moving the threshold from 0.70 to 0.80.

At 56d, the sufficient-user count remains 14 and the stable count remains 10. The non-stable remainder shifts from the historical 3 multi-anchor / 1 unstable split to 4 multi-anchor / 0 unstable, without changing the main stable-secondary conclusion.

### CP2-v2 Stage 05b decision

1. Keep production HOME/OFFICE unchanged.
2. Retain the 5 non-emitted HIGH/MEDIUM HOME candidates as a small targeted-review set only; do not promote them automatically.
3. Do not expand HOME from recurrence-only candidates.
4. Do not convert stable_secondary_anchor to OFFICE.
5. The stable-secondary subset remains 9 users despite the broader CP2-v2 HOME-consensus cohort.
6. Proceed to Stage 05c independent evidence for those stable-secondary users rather than tuning another global WORK threshold.
7. Continue treating all tiers and adaptive states as behavioral evidence, not semantic ground truth.
