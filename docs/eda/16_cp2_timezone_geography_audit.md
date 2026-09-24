# CP2 timezone / geography audit

Date: 2026-09-18  
Status: COMPLETE — CP2 v1 Beijing-focused semantic cohort frozen as an engineering baseline after measured sensitivity review.

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

## Measured sensitivity

The full 5,821-stay materialization produced the following user counts when requiring both stay-share and dwell-share to meet the same threshold:

| radius | >=50% | >=80% | >=90% | >=95% |
| ---: | ---: | ---: | ---: | ---: |
| 50 km | 109 | 90 | 78 | 66 |
| 100 km | 113 | 97 | 87 | 78 |
| 200 km | 119 | 103 | 92 | 84 |

The 100 km / 80% candidate lies between the neighboring radius choices rather than at an extreme.

Under the selected rule:

- eligible Beijing-focused users: **97**;
- in-region stays entering semantic-time processing: **4,197**;
- out-of-region travel stays excluded from otherwise eligible users: **245**;
- share of all materialized stays retained for the Beijing semantic cohort: **72.10%**.

The stay-distance distribution is highly skewed: median distance to the Beijing reference point is about 11.76 km, while p90 is about 975.74 km. This confirms a Beijing-centered core plus substantial travel/non-Beijing observations.

## CP2 v1 decision

Freeze the first semantic cohort as an **engineering baseline**:

- reference point: 39.9042 N, 116.4074 E;
- radius: 100 km;
- minimum stay share inside radius: 80%;
- minimum dwell share inside radius: 80%;
- timezone for retained in-region stays: `Asia/Shanghai`;
- out-of-radius stays from eligible users are excluded;
- users failing the cohort rule abstain from the v1 Home/Office baseline.

This is not claimed to be an accuracy-optimal geographic boundary. It is an explicit, conservative scope for the first interpretable semantic baseline.

## Downstream consequence

The timezone/geography gate is now resolved. Home/Office scoring remains blocked only by the recurring-location representation gate.

Notebook: `notebooks/03_home_office_baseline.ipynb`.

## 2026-09-24 post-freeze semantic review

A later review identified a limitation in the v1 framing.

The frozen `39.9042 N, 116.4074 E + 100 km` rule should be interpreted only as a **Beijing-focused engineering cohort heuristic**. It is not a timezone boundary and it is not an administrative Beijing boundary.

### Why the distinction matters

The IANA time zone database does not define a timezone as a simple latitude/longitude rectangle around a city. Its tab files use representative geographic locations for timezone names. Coordinate-to-timezone assignment is more naturally handled with timezone boundary polygons.

A stronger v2 audit candidate is therefore:

```text
each stay coordinate
    -> point-in-timezone-polygon lookup
    -> IANA tzid
    -> ZoneInfo(tzid)
    -> local arrival/departure time
```

This would let a Beijing-based user retain correct local time for travel stays instead of dropping them solely because they fall outside a Beijing radius.

### Keep geography and timezone as separate gates

If the product scope still requires a Beijing-specific cohort, evaluate that independently:

- **timezone gate:** which IANA timezone contains each stay coordinate?
- **Beijing geography gate:** does the stay fall inside the chosen Beijing geographic scope?

For the latter, the strongest geographic contract would use an official Beijing administrative boundary polygon. A central-Beijing radius can remain as a simpler engineering cohort, but it must be described explicitly as an approximation.

### Status

This review does **not** change frozen CP2 v1 production behavior yet. Before replacing the current rule, rerun:

- timezone-id distribution across the 5,821 frozen CP1 stays;
- user-level stay-share and dwell-share by timezone;
- Beijing-geography sensitivity if a Beijing-only cohort is still required;
- downstream Home/Office emission counts;
- direct-model and HTTP parity.

References:

- IANA time zone theory: https://www.iana.org/time-zones/theory
- timezone-boundary-builder: https://github.com/evansiroky/timezone-boundary-builder
- Beijing 2026 administrative-boundary base maps: https://ghzrzyw.beijing.gov.cn/zhengwuxinxi/tzgg/sj/202609/t20260911_4859523.html

