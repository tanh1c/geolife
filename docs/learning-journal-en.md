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

Next learning target: inspect sampling intervals, trajectory duration/distance, timestamp anomalies, altitude missingness, and segment-speed distributions before proposing noise thresholds.
