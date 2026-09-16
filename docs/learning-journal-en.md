# Learning Journal — EN

## 2026-09-16 — Why GeoLife needs deeper EDA

GeoLife is not a small i.i.d. tabular dataset. It is hierarchical and spatiotemporal: points belong to trajectories, trajectories belong to users, users have very different observation periods, sampling rates vary, and geography/timezone affect interpretation.

Key lessons:

- verify dataset counts from files instead of trusting documentation blindly;
- inspect raw distributions before choosing cleaning thresholds;
- avoid loading every GPS point into one giant DataFrame when trajectory-level reduction is enough;
- evaluate user-history imbalance because Home/Office inference needs repeated behavior;
- treat transportation labels as auxiliary movement labels, not Home/Office ground truth;
- make timezone semantics explicit before using 'night' or 'office hours';
- treat mobility privacy as a system-design concern, not just a reporting concern.

## 2026-09-16 — What the first measured distributions changed

The mounted release contains 182 users and 18,670 trajectory files. The user distribution is highly long-tailed: the median user has 27.5 trajectories, while the largest has 2,153. The top 10 users alone contribute 47.4% of all trajectories.

This changes how I should think about evaluation. A single trajectory-weighted score can mostly reflect heavy users, so later model evaluation should include a per-user/macro view where appropriate. I also observed that users with transportation-label files represent 69/182 users but 58.4% of all trajectories, so the labeled subset is not representative by trajectory volume.

The first raw trajectory also showed why spot checks are useful but insufficient: timestamps parsed cleanly as UTC, while altitude values had a very wide range. I should not convert one unusual value into a cleaning rule; I need the dataset-wide distribution first.

## 2026-09-16 — Data-quality diagnostics changed the cleaning plan

The full scan confirmed 24,876,978 points. It also showed why a simple `speed > threshold => noise` rule would be premature.

I found one malformed latitude (`400.166667`) that is clearly different from a repeated corruption pattern in another trajectory, where coordinates jump roughly 850–862 km in one second over and over. These are different failure modes and may need different handling.

I also confirmed that one raw trajectory is byte-identical across three different user folders. This introduces a potential leakage/weighting concern for future evaluation and shows that file-level duplication should be measured explicitly.

## 2026-09-16 — A hypothesis was tested and rejected

I initially suspected that the PLT `serial_date` field might preserve hidden sub-second timing and that the apparent duplicate timestamps were created by parsing only the text date/time fields. The data did not support that hypothesis.

In a trajectory with 45,215 duplicate text timestamps, the duplicate count stays exactly 45,215 when timestamps are reconstructed from `serial_date`. Several different coordinates inside the same recorded second also have the same serial-date value. The few-microsecond difference between serial and text timestamps is just floating-point conversion noise, not useful extra timing precision.

This changes the preprocessing problem: same-second observations are genuinely ambiguous at the released timestamp resolution. I cannot estimate within-second velocity or impose an arbitrary order. I should first measure the spatial spread of these groups, then decide whether to collapse them or preserve them as simultaneous observations.

## 2026-09-16 — Same-second groups are mostly jitter, but exact duplicates are structural

The same-second analysis found 212,409 groups. Most are spatially compact: the median maximum radius from the coordinate-wise median is about 0.47 m, p95 is 4.85 m, p99 is 7.06 m, and 99.61% are within 10 m. This supports testing a robust one-row-per-timestamp representation for compact groups. The tiny long-distance tail must be flagged separately rather than averaged across incompatible locations.

The raw-file hash scan changed the evaluation plan more substantially. There are 821 exact duplicate hash groups containing 1,677 files. About 8.98% of trajectory files participate in an exact duplicate group, and several groups span different user IDs. Therefore content identity is not a rare edge case. Future train/test splitting should keep byte-identical content in the same fold, and benchmark weighting should avoid giving duplicated content accidental extra influence.

## 2026-09-16 — Cross-user duplication is large enough to affect evaluation

All 821 exact-duplicate hash groups were found to span multiple user IDs. The 1,677 affected files make up 8.98% of trajectories but contain 2,965,977 points, or 11.92% of the full dataset.

This is important because the point-weighted exposure is larger than the file-count exposure. Duplicate traces are therefore longer than average and can have disproportionate influence on point-level metrics. The raw release does not explain why the same content is assigned to multiple users, so I should not infer that these user IDs represent the same person. For evaluation, however, content hashes need to act as grouping keys so identical traces cannot leak across folds.

## 2026-09-16 — Redundancy and connected components changed the split strategy

After retaining one representative per exact-content hash group, the extra copies still account for 1,495,115 points, or 6.01% of the full dataset. This clarifies the difference between duplicate exposure and true redundancy: 11.92% of points belong to duplicate groups, but 6.01% are extra copies beyond one representative.

The shared-content user graph includes 52 users across 18 connected components. The largest component contains 15 user IDs. Therefore even a user-level split is not enough to guarantee content independence: different user IDs can still be linked by identical trajectories. For strict evaluation, content-hash grouping is required, and connected-component grouping is a reasonable candidate when measuring user-level generalization.

A useful stopping lesson is also emerging: EDA must support decisions rather than becoming the entire project. Duplicate structure is now sufficiently characterized for CP1. The next focus should return to preprocessing that directly affects stay-point detection: same-second consolidation, temporal gaps, and movement anomalies.

## 2026-09-16 — Same-second consolidation solves one failure mode, not all of them

The consolidation prototype made the separation between failure modes concrete. On a duplicate-heavy trajectory, 56,780 raw points collapsed to 11,565 timestamp rows with only three spatial conflicts, and the largest inspected speeds dropped to roughly 225 km/h. That is evidence that timestamp-resolution ambiguity was materially affecting segment construction.

The same transform did not fix the structurally corrupted user-062 trajectory. It flagged 26 same-second conflicts, but the multi-million-km/h jumps remained because they occur between singleton timestamps at different seconds. This means same-second ambiguity and impossible inter-timestamp movement are independent cleaning problems.

The main lesson is to make preprocessing staged and interpretable: first validate coordinates, then consolidate compact same-second groups, then deal with temporal gaps and movement anomalies. A global speed filter should come only after those earlier failure modes are removed or flagged.

## 2026-09-16 — Full consolidation changed how I interpret the speed tail

Applying same-second consolidation to the whole release reduced 24,876,978 raw points to 24,178,077 timestamp-level rows, a 2.81% reduction, while only 835 timestamps (0.0035%) were spatial conflicts. This is strong evidence that the transform is low-loss for the dominant duplicate-second pattern.

The more important result is that the residual speed tail barely disappears. At the trajectory level, 46.96% of trajectories still have a maximum speed above 100 km/h, but at the segment level only 5.40% of valid movement segments exceed 100 km/h. Above 150 km/h the segment share falls to about 1.00%, above 200 km/h to 0.37%, and above 1,000 km/h to 0.007%.

This taught me that a trajectory-max statistic answers a different question from segment prevalence. One bad segment can make an otherwise normal trajectory look extreme, so cleaning thresholds should be reasoned about at the segment level and then traced back to trajectories/users.

Temporal gaps are another independent issue: the median trajectory's largest gap is 325 seconds, while p90 is about 11,010 seconds and the maximum is 93,298 seconds. For stay-point detection, nearby points separated by a long observation outage cannot automatically be interpreted as continuous dwelling.

Next learning target: use available transportation-mode labels to characterize legitimate speed distributions, analyze gap sensitivity, then freeze an evidence-backed cleaning contract before implementing stay-point detection.