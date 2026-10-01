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
- frozen Beijing semantic cohort;
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
