# Stage 07j — Targeted near-miss OFFICE audit

## Motivation

Stage 07i showed that the frozen OFFICE gate is conservative in coverage:

- baseline `3 dates / .30 share / .10 margin` emits 16 users;
- one-step margin relaxation to `.05` emits 18 users;
- one-step share relaxation to `.20` emits 23 users.

The key question is not whether relaxed gates emit more users. They do.

The useful question is:

> Are the users added by a one-step relaxation behaviorally persistent and candidate-stable enough to justify a separate production policy review?

Stage 07j therefore audits only the newly emitted users from those two one-step relaxations and compares them with the frozen 16-user OFFICE cohort.

No production threshold is changed in this stage.

## Frozen audit groups

### Baseline

```text
min_dates  = 3
min_share  = .30
min_margin = .10
```

Expected emitted users: 16.

### Margin near-miss

```text
min_dates  = 3
min_share  = .30
min_margin = .05
```

Only users emitted by this relaxed gate but absent from baseline are retained.

Expected new users from Stage 07i: 2.

### Share near-miss

```text
min_dates  = 3
min_share  = .20
min_margin = .10
```

Only users emitted by this relaxed gate but absent from baseline are retained.

Expected new users from Stage 07i: 7.

Because all three configurations keep `min_dates=3`, share/margin relaxation must not alter candidate ranking. Stage 07j hard-validates that every audit candidate matches the frozen full-period fixed-window candidate.

The two near-miss groups are expected to be disjoint.

## Evidence layers

Stage 07j does not invent a new total score.

It carries source-native diagnostics.

### 1. Full-period support

For each candidate:

- relevant support days;
- full-period OFFICE dwell share.

These describe why the user sits near the gate.

### 2. HOME collision

The audit checks whether the candidate location equals an emitted production HOME location for the same user.

A collision is an ambiguity flag.

### 3. Static comparator identity

Using Stage-05 assignments:

- fixed-window candidate identity;
- HoWDe-style OFFICE candidate identity;
- recurrence OFFICE candidate identity.

For each user Stage 07j records whether HoWDe and recurrence select the exact same location as the near-miss candidate.

This is candidate identity evidence, not semantic ground truth.

### 4. Split-half identity stability

Stage-05 reliability already includes:

- first-half vs second-half split;
- odd-week vs even-week split.

Stage 07j does not merely ask whether the two halves agree with each other.

It asks whether **both halves select the exact full-period near-miss candidate**.

This is stricter and directly relevant to safe candidate expansion.

### 5. Held-out persistence

Stage-05 held-out validation trains on the first 60% of observed dates and evaluates on the final 40%.

For a near-miss candidate Stage 07j records:

- whether the train-period fixed candidate equals the full-period candidate;
- whether the candidate is observed in holdout;
- held-out weekday-day-share;
- held-out OFFICE rank;
- whether that exact candidate remains top-1 in holdout.

### 6. Dropout robustness

Stage-05 dropout tests remove 10%, 20%, and 30% of stays under three deterministic seeds each.

Stage 07j records:

- exact-candidate retention over all dropout trials;
- retention separately at 10%, 20%, and 30%.

No new arbitrary cutoff is introduced.

### 7. 12-hour time-shift diagnostic

The Stage-05 12-hour shift result is carried as a falsification diagnostic.

Candidate retention after a 12-hour schedule shift is **not** treated as positive OFFICE support.

### 8. BCL-primary historical context

Stage 07j reuses Stage-07i exact BCL metrics at:

- 100 m;
- 150 m.

For evaluable candidate locations it records:

- broad work-compatible lexical context;
- business-name context;
- education;
- retail/service.

BCL remains supporting historical context, not OFFICE ground truth.

Historical OSM is not used as a negative vote in this near-miss audit.

## Reference design

The frozen 16-user production OFFICE cohort is retained as a reference group.

This is important because an absolute number such as "50% split stability" is hard to interpret without knowing how the already-emitted OFFICE cohort behaves under the same diagnostics.

Therefore aggregate tables report:

- baseline;
- margin near-miss;
- share near-miss.

The baseline is a production policy reference, not verified ground truth.

## Outputs

Private:

- `near_miss_office_audit_private.pkl`;
- `near_miss_office_signatures_private.pkl`.

Aggregate:

- `cohort_counts.csv`;
- `support_distribution.csv`;
- `behavioral_robustness.csv`;
- `bcl_context_summary.csv`;
- `near_miss_diagnostics.csv`;
- `static_comparator_match_distribution.csv`;
- `split_match_distribution.csv`.

Cache root:

`/mnt/geolife-data/cache/cp2_v2/07j_near_miss_office_audit/`

## Decision boundary

Stage 07j is intended to identify whether one-step near-miss users resemble the frozen OFFICE cohort on candidate persistence and identity stability.

It does not automatically promote any user.

A potentially safe expansion would require the near-miss group to show behavior broadly comparable to baseline OFFICE across multiple existing diagnostics, without HOME collision or obvious identity instability.

BCL can strengthen a candidate case when positive, but lack of BCL evidence is not sufficient to reject a candidate.

If near-miss reliability is materially weaker than baseline OFFICE, retain the frozen gate.

If one near-miss family is broadly comparable to baseline across existing reliability diagnostics, that finding can justify a separate production-policy decision stage.
