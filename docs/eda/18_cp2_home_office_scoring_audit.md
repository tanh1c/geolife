# CP2 Home / Office scoring audit

Date: 2026-09-18  
Status: COMPLETE — CP2 v1 Home/Office scoring, abstention, evidence-strength, and production parity are resolved.

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

## First measured scoring output

On the frozen 97-user Beijing semantic cohort:

- users with a recurring semantic location: **73**;
- users with a supported Home candidate: **47** (48.5% of cohort; 64.4% of recurring-location users);
- users with a supported Office candidate: **40** (41.2% of cohort; 54.8% of recurring-location users);
- users with both candidates: **27** (27.8% of cohort; 37.0% of recurring-location users);
- among those 27 users, **7** (25.9%) had the same leading location for Home and Office.

Top Home-candidate evidence:

- median night-dwell share: **0.635**;
- median top-1 vs top-2 share margin: **0.513**;
- median supported night dates: **4**;
- median night dwell: **7.04 h**.

Top Office-candidate evidence:

- median office-dwell share: **0.357**;
- median top-1 vs top-2 share margin: **0.243**;
- median supported office dates: **3**;
- median office dwell: **2.94 h**.

The Office distribution is materially weaker than the Home distribution. Therefore CP2 should not assume that Home and Office need identical emission thresholds.

The first audit also confirms that minimum support of only two dates admits weak candidates: Home share can be as low as 0.095 with margin 0.002, and Office share as low as 0.091 with margin 0.015. Ranking alone is therefore insufficient; an explicit abstention gate is required.

## Next sensitivity

Run a bounded sensitivity around:

- Home window: 20–06 / 21–06 / 22–06;
- Office window: 08–17 / 09–17 / 09–18;
- Home minimum relevant dates: 2 / 3 / 5;
- Home minimum share: 0.4 / 0.5 / 0.6;
- Home minimum top-1 margin: 0.1 / 0.2 / 0.3;
- Office minimum relevant dates: 2 / 3 / 5;
- Office minimum share: 0.2 / 0.3 / 0.4;
- Office minimum top-1 margin: 0.05 / 0.10 / 0.20.

The Home and Office grids are intentionally different because their measured evidence distributions differ substantially.

Only then freeze Home/Office scoring and heuristic confidence semantics.

Notebook: `notebooks/03_home_office_baseline.ipynb`.


## Final production parity

The frozen production implementation was run over the cached full-release stay table.

Observed:

- HOME: 27;
- OFFICE: 16;
- total emitted labels: 43;
- unique emitted users: 36.

The 27/16 label counts match the frozen notebook sensitivity decision exactly. This closes the scoring audit for CP2 v1.
