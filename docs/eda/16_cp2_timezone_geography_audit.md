# CP2 timezone / geography audit

Date: 2026-09-18  
Status: OPEN — audit methodology added to notebook; measured sensitivity output still needs review.

## Why this audit exists

GeoLife PLT timestamps are UTC/GMT, while Home/Office rules depend on local behavioral time. The full release contains trajectories outside Beijing, so applying UTC+8 to every stay would silently assign the wrong local time to some observations.

The first CP2 materialization already showed that stays are strongly Beijing-centered but geographically broad. Therefore CP2 must define an explicit semantic cohort before any night/daytime scoring.

## Candidate v1 policy under review

The first interpretable policy is a **Beijing-focused cohort** rather than full-release timezone inference.

Use an approximate Beijing reference point:

`39.9042° N, 116.4074° E`

This coordinate is only a distance anchor, not an administrative boundary.

Audit radii:

- 50 km;
- 100 km;
- 200 km.

For each user and radius, measure:

- fraction of stays inside the radius;
- fraction of total dwell time inside the radius.

Candidate rule to review:

- at least 80% of stays within 100 km;
- at least 80% of dwell time within 100 km.

The 100 km / 80% values are deliberately marked as **candidate parameters**, not frozen contract values.

## Travel-stay handling

A user can be Beijing-focused and still travel.

Therefore, even if a user satisfies the candidate cohort rule, CP2 does **not** convert all of that user's stays to `Asia/Shanghai`.

Only stays that are themselves inside the selected Beijing radius enter the first semantic-time cohort. Out-of-radius travel stays are excluded from Home/Office scoring for v1.

This prevents a user-level cohort assignment from silently applying Beijing time to observations from another timezone.

## Local-time conversion

For in-region stays from accepted Beijing-focused users:

- source timestamps remain UTC-aware;
- local timestamps are produced with timezone-aware conversion to `Asia/Shanghai`;
- manual `UTC + 8h` arithmetic is not used.

## Abstention

Users who do not meet the geography rule remain out-of-scope for the first Home/Office baseline.

CP2 does not infer timezone from longitude alone and does not force semantic labels for those users.

This is a deliberate abstention policy, not missing implementation.

## Review outputs required

Before freezing the timezone policy, inspect:

1. stay-distance distribution to the Beijing reference point;
2. user counts under 50/100/200 km sensitivity;
3. user counts under 50/80/90/95% inside-share thresholds;
4. number of stays retained in the candidate semantic cohort;
5. number of travel/out-of-region stays excluded from otherwise eligible users;
6. interaction with user-history sufficiency;
7. whether reasonable neighboring thresholds materially change the eligible population.

## Downstream consequence

Home/Office time-window features remain blocked until this audit is reviewed.

Notebook: `notebooks/03_home_office_baseline.ipynb`.
