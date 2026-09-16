# Same-second groups and exact duplicate trajectories

Date: 2026-09-16

These findings are measured from the official GeoLife 1.3 release mounted in Modal.

## Same-second GPS groups

Across trajectories with duplicate timestamps, 212,409 same-second groups were found.

Group-size distribution is dominated by 5-point and 2-point groups:

- 160,534 groups contain 5 rows;
- 48,838 groups contain 2 rows;
- larger groups are rare.

Spatial spread around the coordinate-wise median is usually very small:

- median max-radius: 0.47 m;
- p75: 1.57 m;
- p90: 3.27 m;
- p95: 4.85 m;
- p99: 7.06 m;
- 95.32% of groups are within 5 m;
- 99.61% are within 10 m;
- 99.84% are within 20 m.

However, a tiny tail is extremely corrupted. The maximum radius is about 430 km. The largest examples are concentrated in trajectories such as user 062 / `20080926000623`, where two coordinates recorded in the same second can be hundreds of kilometres apart.

Interpretation: most same-second groups look like dense GPS jitter/burst logging rather than true independent movement observations. Because the release provides no recoverable sub-second order, speed is undefined within a same-second group. A robust consolidation experiment is justified for compact groups, but it should not blindly average spatially conflicting groups.

A useful next representation is one row per timestamp with a robust representative coordinate and provenance such as `raw_point_count`, while flagging spatially inconsistent groups separately. The exact consolidation threshold is still a candidate to be validated rather than a production rule.

## Timestamp precision hypothesis rejected

The PLT `serial_date` field does not recover hidden sub-second timing for the affected trajectories. In the inspected 5-point same-second group, all rows have the same `serial_date`; serial-date reconstruction preserves the same duplicate count as the date/time text parser. Microsecond-scale offsets are floating-point/conversion artifacts, not meaningful timing information.

Therefore, same-second ordering cannot be reconstructed from the supplied release.

## Exact raw-file duplicates

SHA-256 hashing over all 18,670 trajectory files found:

- 821 exact-duplicate hash groups;
- 1,677 files participating in duplicate groups;
- about 8.98% of trajectory files participate in at least one exact-duplicate group;
- 856 files are extra copies beyond one representative per duplicate group, about 4.58% of all trajectory files.

Several duplicate groups span multiple different user IDs, including repeated clusters such as `[057, 094, 150]`, `[058, 059, 141]`, `[081, 125, 136]`, and `[128, 153, 163]`.

Interpretation: raw-file duplication is not an isolated anomaly. The reason for the duplicated assignment is not established from the release itself. Future evaluation must account for content identity so byte-identical trajectories cannot leak across train/test folds or receive accidental extra weight. A content-hash grouping key is a safer split primitive than trajectory path alone.

## Cleaning design implication

The evidence now supports separating preprocessing concerns:

1. validate coordinate domain;
2. consolidate or flag same-second groups based on spatial consistency;
3. handle long temporal gaps explicitly;
4. detect movement anomalies only after the timestamp representation is well-defined;
5. preserve content hashes for deduplication/leakage control.

A single global `speed > X => drop point` rule would collapse several distinct failure modes and is not justified yet.