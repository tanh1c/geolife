# Stage 07i handoff — Threshold sensitivity + BCL-primary interpretation

## Run

Run:

`notebooks/07i_threshold_sensitivity.ipynb`

from current `main`.

This stage does not call OSM, BCL network endpoints, or Modal.

It reuses existing local/private artifacts.

## Expected reproduction gates

Before sensitivity results, the notebook must print:

```text
baseline 05b reproduction: PASS (9 users, candidate IDs exact)
frozen production OFFICE reproduction: PASS (16 users)
```

If either fails, stop and send the notebook.

## Main outputs to inspect

### 1. OFFICE gate sensitivity

27 configurations:

```text
min dates  = 2 / 3 / 5
min share  = .20 / .30 / .40
min margin = .05 / .10 / .20
```

Important columns:

- `emitted_users`;
- `baseline_emitted_retained`;
- `new_vs_baseline_emitted`;
- `baseline_emitted_lost`;
- `common_emitted_same_location`;
- `bcl_evaluable_emitted_users`;
- `bcl_context_emitted_users`;
- `bcl_business_name_emitted_users`.

BCL columns apply only to the temporally eligible recurring-anchor subset.

### 2. One-at-a-time stable-secondary sensitivity

Inspect:

- `stable_users`;
- `new_stable_vs_baseline`;
- `baseline_stable_lost`;
- `common_stable_same_candidate`.

We want to know whether the frozen count of 9 is sitting on a sharp threshold cliff or on a stable plateau.

### 3. Joint relaxed/baseline/strict profiles

Compare:

- relaxed;
- mildly_relaxed;
- baseline_profile;
- strict.

Then inspect the same profiles in:

`JOINT PROFILE — BCL CANDIDATE VS PEERS @100/150m`.

### 4. BCL radius sensitivity

Frozen baseline stable-secondary candidates are evaluated at:

```text
25 / 50 / 75 / 100 / 125 / 150 m
```

Do not extrapolate beyond 150 m from this run.

### 5. BCL-primary / OSM-support-only snapshot

This replaces the earlier equal-vote interpretation.

OSM may positively support BCL.

OSM absence/negative direction is not contradiction.

## Interpretation rule

Do not choose the "best looking" threshold.

A threshold change is interesting only if neighboring relaxed settings show:

- stable increase in support;
- candidate identity stability;
- BCL evidence that improves consistently rather than at one isolated setting;
- no obvious collapse into many unstable/multi-anchor cases.

Send the executed notebook after Run All.
