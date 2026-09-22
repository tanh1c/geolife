# Home / Office manual plausibility review

Status: **Checkpoint 1 sample review completed**.

GeoLife does not provide authoritative Home / Office ground-truth labels. This review
therefore checks whether inferred labels are behaviorally plausible for a small sample;
it does **not** measure accuracy.

The review was performed against the executed private Home/Office notebook/cache. Exact
coordinates and raw trajectories are intentionally not copied into the repository.

## Review rule

For each sampled user, inspect:

1. whether the candidate is a recurring location;
2. whether HOME evidence repeats across local night dates (21:00–06:00);
3. whether OFFICE evidence repeats across weekday office dates (09:00–17:00);
4. the relevant-dwell share;
5. the top-vs-second-location share margin;
6. whether the frozen emission gate emits or abstains.

Frozen gates:

```text
HOME:
relevant_dates >= 3
share          >= 0.50
margin         >= 0.20

OFFICE:
relevant_dates >= 3
share          >= 0.30
margin         >= 0.10
```

## Privacy-safe sample

The sample is purposive rather than random: two users with clear dual-label evidence and
one user illustrating conservative abstention. This is useful for mentor review because
it shows both positive cases and a boundary case.

| User | Candidate | Location | Stays | Active dates | Relevant dates | Relevant dwell | Share | Margin | Frozen result | Manual plausibility |
|---|---|---:|---:|---:|---:|---:|---:|---:|---|---|
| 002 | HOME | 0 | 64 | 32 | 22 night dates | 19.09 h | 0.956 | 0.956 | emit | Plausible — repeated night support is strong and clearly separated from the next location. |
| 002 | OFFICE | 3 | 7 | 6 | 4 office dates | 2.14 h | 0.553 | 0.335 | emit | Plausible — weekday-office evidence clears all gates; HOME and OFFICE resolve to different recurring locations. |
| 009 | HOME | 0 | 50 | 21 | 11 night dates | 8.13 h | 0.948 | 0.948 | emit | Plausible — strong repeated night pattern with a very large top-location margin. |
| 009 | OFFICE | 4 | 6 | 4 | 4 office dates | 3.27 h | 0.606 | 0.356 | emit | Plausible — all observed active dates for this candidate support office-time behavior and the margin is above the frozen gate. |
| 022 | HOME | 1 | 85 | 13 | 10 night dates | 27.81 h | 0.479 | 0.221 | abstain | Ambiguous — there is substantial night evidence, but the location explains less than half of semantic dwell, so the conservative HOME gate correctly refuses to force the label. |
| 022 | OFFICE | 6 | 214 | 49 | 35 office dates | 68.43 h | 0.741 | 0.695 | emit | Strongly plausible — repeated weekday-office evidence is extensive and clearly dominant over the second-ranked location. |

## Case interpretation

### User 002

The HOME candidate is supported on 22 separate night dates and accounts for about 95.6%
of the relevant dwell evidence. The OFFICE candidate appears on four office dates and
has a 0.553 share with a 0.335 margin.

The two labels use different recurring location IDs (`0` and `3`). The temporal pattern
is consistent with the intended HOME/OFFICE heuristic.

Verdict: **plausible**.

### User 009

The HOME candidate has 11 night-support dates with share/margin both about 0.948. The
OFFICE candidate has four office-support dates with share 0.606 and margin 0.356.

Again, HOME and OFFICE resolve to different recurring location IDs (`0` and `4`).

Verdict: **plausible**.

### User 022

The OFFICE pattern is very strong: 35 office-support dates, 68.43 hours of office-window
dwell, share 0.741 and margin 0.695.

The HOME candidate has many night-support dates and substantial night dwell, but its
share is only 0.479. That is just below the frozen 0.50 HOME threshold, so production
abstains instead of forcing a HOME label.

Verdict: **OFFICE plausible; HOME appropriately ambiguous/abstained**.

## What this review does and does not prove

This review supports the statement:

> the inferred labels are behaviorally plausible for the inspected sample under the
> frozen temporal and recurrence rules.

It does **not** support statements such as:

- "HOME accuracy is X%";
- "OFFICE accuracy is X%";
- "location 0 is the user's true residence";
- "location 6 is the user's true workplace".

GeoLife does not provide the authoritative labels needed for those claims.

The manual review complements:

- threshold sensitivity;
- DBSCAN vs complete-link comparison;
- notebook ↔ production parity;
- HTTP ↔ direct-model parity;
- abstention analysis.

## Evidence source

Review values come from the executed private
`notebooks/03_home_office_baseline.ipynb` run used to freeze CP2 v1. The public repo
keeps only privacy-safe evidence and does not publish exact inferred coordinates.
