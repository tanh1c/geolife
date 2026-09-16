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

Next learning target: quantify same-second spatial spread, exact duplicate-file prevalence, and impossible-jump patterns before proposing cleaning or stay-point thresholds.
