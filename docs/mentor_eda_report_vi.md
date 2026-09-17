# GeoLife CP1 — EDA Report for Mentor

## Executive summary

EDA được thực hiện trên GeoLife v1.3 với mục tiêu thiết kế preprocessing đáng tin cậy trước stay-point và Home/Office inference.

### Dataset verified
- Users: **182**
- Trajectory files: **18,670**
- GPS points: **24,876,978**
- User folders with labels: **69**

### Raw quality
- Duplicate-timestamp rows: **698,900** (2.81%)
- Trajectories affected: **441**
- Invalid latitude points: **1**
- Non-monotonic trajectories: **0**

### Same-second structure
- Same-second groups: **212,409**
- Share within 10 m: **99.61%**
- Interpretation: phần lớn là compact burst/jitter; tiny tail là spatial conflict.

### Exact duplicate content
- Exact duplicate groups: **821**
- Files in cross-user duplicate groups: **1,677**
- Redundant points beyond one representative/hash: **1,495,115** (6.01%)
- Users involved: **52**
- Connected components: **18**
- Largest component: **15 users**

### Same-second consolidation
- Raw points: **24,876,978**
- Consolidated rows: **24,178,077**
- Rows reduced: **698,901** (2.81%)
- Spatial-conflict timestamps: **835**
- Valid movement segments: **24,157,908**

### Segment-level speed prevalence
- >100 km/h: **5.40%**
- >200 km/h: **0.37%**
- >500 km/h: **0.20%**
- >1000 km/h: **0.01%**

### Temporal continuity
- Trajectories có gap >2 min: **65.92%**
- >5 min: **50.95%**
- >10 min: **41.74%**

### Transportation-label interval audit — half-open [start,end)
- Different-mode endpoint-touching pairs: **1,742**
- Different-mode true-overlap pairs: **146**
- Unambiguous canonical windows: **14,583**
- Ambiguous atomic sweep slices: **149**
- Ambiguous maximal windows: **138**
- Unambiguous labeled hours: **12,720.833**
- Ambiguous labeled hours: **76.345**
- Ambiguous share: **0.597%**

### Half-open V3 labeled-speed coverage
- Valid movement segments from labeled users: **11,878,198**
- Strictly matched segments: **4,807,087**
- Coverage: **40.47%**

- **airplane**: 9,169 segments; median 625.91 km/h; p95 881.29; p99 937.99; max 1048.11
- **train**: 556,136 segments; median 93.14 km/h; p95 165.32; p99 210.34; max 4678.32
- **car**: 499,945 segments; median 30.05 km/h; p95 93.69; p99 119.63; max 2515.25
- **bus**: 1,189,927 segments; median 16.91 km/h; p95 57.05; p99 90.59; max 2765.76
- **bike**: 773,004 segments; median 11.19 km/h; p95 22.74; p99 40.63; max 2556.51
- **walk**: 1,314,584 segments; median 4.08 km/h; p95 14.35; p99 40.39; max 9415.67

## Decisions supported by the EDA

1. Coordinate-domain validation is a separate preprocessing stage.
2. Same-second observations do not have recoverable sub-second order.
3. Compact same-second groups can be represented by a median coordinate; 10 m is the current evidence-backed candidate.
4. Same-second spatial conflict must break continuity instead of being averaged.
5. Movement quality should be reasoned at segment level, not trajectory max-speed.
6. Temporal gaps are common; `max_gap_s` must be an explicit sensitivity parameter.
7. Generic 100/200/500 km/h global cutoffs are not justified because legitimate high-speed transport exists.
8. Exact content hashes must be used for leakage control in evaluation.
9. Transportation labels are auxiliary movement evidence only, not Home/Office ground truth.

## Proposed next step

Review/freeze cleaning contract, then write RED tests before implementing preprocessing and stay-point detection. After GREEN, run the bounded stay-point sensitivity grid rather than reopening open-ended EDA.

## Important caveat

The 1,200 km/h hard guard remains a **release-specific engineering proposal**. It should be frozen only after reviewing this half-open V3 speed table. It is intended as a continuity boundary, not a universal physical law or automatic endpoint-deletion rule.