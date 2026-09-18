# CP2 Home / Office scoring audit

Date: 2026-09-18  
Status: OPEN — first scoring implementation added to notebook; measured output pending review.

## Upstream semantics already frozen for CP2 v1

Semantic scoring is scoped to:

- Beijing-focused users: >=80% of stays and >=80% of dwell within 100 km of the Beijing reference point;
- only in-radius stays enter semantic scoring;
- local timezone: `Asia/Shanghai`;
- recurring locations: per-user complete-linkage clusters with maximum diameter <=200 m.

These are engineering baselines, not accuracy-optimal parameters.

## Candidate time windows

Home evidence:

- local night window: 21:00–06:00.

Office evidence:

- local weekday window: Monday–Friday, 09:00–17:00.

These windows are not frozen yet.

## Interval-overlap semantics

A stay contributes only the portion of its interval that overlaps the relevant behavioral window.

For example, a stay from 20:50 to 21:30 contributes 30 minutes of night dwell, not the full 40 minutes.

This avoids arrival-hour classification artifacts and handles stays that cross midnight or behavioral-window boundaries.

## Location-level evidence

For each recurring location:

- `night_dwell_s`;
- `office_dwell_s`;
- `night_dates`: distinct night windows with at least 10 minutes of overlap;
- `office_dates`: distinct weekday office windows with at least 10 minutes of overlap;
- `night_dwell_share`: share of the user's observed night-window dwell;
- `office_dwell_share`: share of the user's observed weekday-office-window dwell.

The user-level denominator includes all semantic locations, not only recurring candidates. This prevents scattered non-recurring dwell from disappearing from the evidence denominator.

## Candidate eligibility

For the first audit, a location must:

- contain at least 2 stays;
- have evidence on at least 2 distinct relevant dates.

No minimum dwell-share or top-1 margin is frozen yet.

## Ranking

Home candidates are ranked lexicographically by:

1. night-dwell share;
2. distinct night dates;
3. night dwell;
4. stay count.

Office candidates use the analogous office features.

The audit reports top-1 vs top-2 share margin.

This is intentionally not presented as a calibrated confidence probability.

## Same-location Home and Office

The first baseline does not force Home and Office to be different locations.

If the same recurring location ranks first for both evidence families, the audit surfaces that condition explicitly. It does not invent a second location.

## Review outputs required

Before freezing emission/abstention semantics, inspect:

1. users with supported Home candidate;
2. users with supported Office candidate;
3. users with both;
4. abstention counts;
5. same-location candidate frequency;
6. top candidate share distribution;
7. top-1 vs top-2 margin distribution;
8. distinct support dates and relevant dwell distribution.

## Next sensitivity

After reviewing the first output, run a bounded sensitivity around:

- Home window: 20–06 / 21–06 / 22–06;
- Office window: 08–17 / 09–17 / 09–18;
- minimum relevant dates;
- minimum share and top-1 margin required for label emission.

Only then freeze Home/Office scoring and heuristic confidence semantics.

Notebook: `notebooks/03_home_office_baseline.ipynb`.
