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
