# 03b mobile / distributed-work hypothesis audit handoff

## Purpose

Continue the narrow research audit prompted by frozen 03a—not a Home/Office v2 implementation. The question is whether frozen 03a mobile-work-like candidates differ from comparable OFFICE-abstained controls on **independent** evidence. Do not assign occupations, true work locations, semantic WORK labels, or POI labels.

## Frozen baseline

- 03a evidence checkpoint: commit `4341382`.
- Do not edit CP1, `src/geolife/model/home_office.py`, API behavior, `notebooks/03_home_office_baseline.ipynb`, or 03a definitions unless a demonstrated bug requires it.
- Required parity before analyzing 03b:

```text
mobile-work-like candidates: 23
multiple-anchor among candidates: 23
frozen OFFICE abstained: 23
frozen OFFICE emitted: 0
```

- Frozen CP2 comparator remains 27 HOME / 16 OFFICE.

## Current 03b state

Committed WIP files:

```text
analysis/03b_mobile_work_hypothesis_audit.py
tests/test_mobile_work_hypothesis_audit.py
reports/03b_mobile_work_hypothesis_audit.md
.gitignore
```

Private ignored output root:

```text
artifacts/03b/
```

The initial runner reconstructs frozen 03a candidates, creates deterministic A/B/C cohorts, builds abstract `L*→L*` transition metrics, computes weekday/weekend summaries, parses half-open transport mode windows, and has started clean-segment matching.

## What is verified

- `tests/test_mobile_work_hypothesis_audit.py` initially covered deterministic control matching, half-open mode labels, fully-contained mode segments, L*-only transition metrics, sensitivity Jaccard, and public-report wording/privacy.
- The initial 03b run reproduced the required frozen parity exactly.
- The initial run revealed two invalid preliminary evidence paths, which must **not** be used as results:
  1. transport summary initially used label-window duration instead of cleaned segments;
  2. sensitivity initially held the frozen cohort fixed instead of re-evaluating the wrapper.
- The runner has been revised to address both paths, but its latest full run was intentionally stopped because it re-cleans too broadly and has not yet been revalidated end-to-end.

## Required continuation

### 1. Make transport execution bounded and resumable

The current `_cleaned_mode_segments()` iterates all trajectory files for cohort users. This was too slow with no progress output.

Replace it with a private resumable cache under `artifacts/03b/`, keyed by source trajectory file:

- first identify each cohort user’s canonical mode windows;
- skip PLT files whose raw UTC min/max do not overlap any window for that user;
- frozen-clean only overlapping files;
- retain valid same-`sequence_id`, positive-duration segments wholly contained in one unambiguous half-open window;
- checkpoint segment rows after each user or bounded file batch;
- print progress, e.g. `mode segments: user 4/20, file 31/…`;
- on rerun, load completed files and process only missing ones.

Never match segments that cross a mode-window boundary, a CP1 sequence boundary, or have non-positive duration.

Report per A/B/C group:

```text
users with any canonical labels
users with matched segments
median canonical labeled duration/user
median matched duration/user
median matched distance/user
mode shares by matched distance
active-mode and motorized-mode shares
mode-transition count
```

If label coverage is sparse or imbalanced, state that mode evidence is exploratory supporting evidence only.

### 2. Finish actual candidate sensitivity

The frozen 23 stay primary. Each variant must rerun the wrapper expression from scratch and produce:

```text
perturbation
candidate_count
Jaccard with frozen 23
retained
added
dropped
```

Minimum variants:

```text
frozen baseline
anchor 100m
anchor 300m
mobility -10%
mobility +10%
support -1 weekday
support +1 weekday
```

`_perturbed_candidates()` currently reruns mobility/support variation against the frozen 200m feature table. Extend it to recompute the clustering-dependent recurrence/daytime-location inputs for 100m and 300m before rerunning the expression. Do not choose a preferred variant based on output quality.

### 3. Add explicit A/B/C support balance

`match_office_abstained_controls()` now exports candidate/control values for:

```text
active_days
usable_temporal_days
observed_span_h
cp1_stay_count
```

Aggregate and report medians/IQRs plus unmatched Group A candidates. Group B must remain OFFICE-abstained, non-mobile-work-like, multiple-anchor, and comparable observation support. Group C is frozen OFFICE-emitted with the same basic support gate; it is a heuristic-selected fixed-location-like comparator, never ground truth.

### 4. Complete independent route/transition and falsification evidence

- Use usable motif days only and deterministic 200m `L*` identifiers.
- Report transition count, distinct directed edges, recurrent edges on at least two dates, top-edge frequency, and edge entropy.
- Do not use CP1 `boundary_count` as a location-transition count.
- Add negative-control denominators/results for:
  - sparse/low-support;
  - CP1-boundary-heavy;
  - travel-heavy non-candidates;
  - weekend-heavy users;
  - same multiple-anchor OFFICE-abstained controls.
- A difference that recurs in those controls weakens the hypothesis.

### 5. Cases, report, and decision

Produce deterministic private alias-only cases:

```text
5 strong/stable Group A
3 threshold-sensitive Group A
3 matched Group B
3 Group C
```

Figures must be non-map and use only aliases and `L*`. Include weekday/weekend mobility, observation quality, available mode composition, transition graph, and daily movement/transition profile.

Regenerate `reports/03b_mobile_work_hypothesis_audit.md` with measured answers to Q1–Q10 and these exact final headings:

```text
EXECUTIVE RESULT
GROUP SIZES
INDEPENDENT EVIDENCE
TRANSPORT MODE RESULT
ROUTE / TRANSITION RESULT
WEEKDAY VS WEEKEND RESULT
SENSITIVITY RESULT
NEGATIVE CONTROLS
WHAT SUPPORTS THE HYPOTHESIS
WHAT WEAKENS THE HYPOTHESIS
WHAT CANNOT BE CONCLUDED
RECOMMENDED NEXT STEP
```

Research decision only:

```text
supported enough for further study
mixed evidence
not supported
```

Use `supported enough for further study` only if robustness plus at least two independent validation streams distinguish A from matched B without being reproduced by negative controls.

## Verification required before claiming evidence

```bash
python -m pytest -q tests/test_mobile_work_hypothesis_audit.py
ruff check analysis/03b_mobile_work_hypothesis_audit.py tests/test_mobile_work_hypothesis_audit.py
python -m pytest -q
python analysis/03b_mobile_work_hypothesis_audit.py --zip "data/Geolife Trajectories 1.3.zip" --seed 42
```

Then verify:

```text
frozen 03a parity and CP2 27 HOME / 16 OFFICE unchanged
summary/report include no raw IDs, coordinates, timestamps, source paths, or maps
all artifacts/03b paths are ignored
report contains Q1–Q10 and a research-only decision
notebook 03 and production inference files unchanged
```

## Takeover status — 2026-09-27

A dedicated continuation branch, `eda/03b-audit-completion`, now hardens the two evidence paths that the handoff marked invalid:

- transport execution uses a private resumable per-file cache, skips trajectory files whose raw UTC extent cannot overlap canonical mode windows, applies frozen CP1 cleaning only to overlapping files, and keeps only positive-duration same-sequence segments fully contained in one unambiguous half-open label window;
- sensitivity now reruns the frozen wrapper under explicit mobility/support perturbations, and the 100 m / 300 m anchor variants recompute clustering-dependent features before candidate selection.

The continuation also adds:

- edge entropy to usable-day `L*→L*` transition evidence;
- A/B/C observation-support balance with unmatched Group A accounting;
- explicit negative-control aggregate tables;
- a measured public-report renderer for Q1–Q10 rather than placeholder “see artifact” text.

These changes are **implementation hardening only**. No new 03b evidence is accepted until the Modal/full-release run, targeted tests, full repository tests, Ruff, privacy checks, and frozen parity all pass.

