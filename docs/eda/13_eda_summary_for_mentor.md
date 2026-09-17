# CP1 EDA summary for mentor

Date: 2026-09-17
Status: EDA CLOSED for the CP1 cleaning decision. Transportation-label interval semantics and the speed benchmark have been re-audited under half-open `[start, end)` semantics.

## 1. Objective

The EDA was designed to support concrete CP1 decisions for GeoLife preprocessing, stay-point detection, Home/Office inference, evaluation, and privacy. The process followed:

`observe distributions -> form hypotheses -> inspect anomalies -> test hypotheses -> quantify impact -> derive candidate rules`

rather than copying thresholds from tutorials.

## 2. Dataset verification

Measured from the mounted GeoLife 1.3 release:

- 182 users;
- 18,670 trajectory files;
- 24,876,978 GPS points;
- 69 user folders with `labels.txt`.

The actual file counts match the v1.3 comparison table. The guide text mentions 73 labeled users, but the mounted release contains 69 folders with `labels.txt`; the reason for that discrepancy is not established.

User history is strongly long-tailed: median 27.5 trajectories/user, maximum 2,153, and the top 10 users contribute about 47.4% of all trajectories. Later evaluation should therefore include user-aware views rather than relying only on global point/trajectory-weighted metrics.

## 3. Raw quality findings

A full scan over all 18,670 trajectories found:

- 0 null timestamps;
- 0 non-monotonic trajectories under the current parser;
- 698,900 duplicate-timestamp rows (2.81% of all points), affecting 441 trajectories;
- one invalid latitude (`400.166667`) surrounded by plausible `40.166...` values;
- severe movement corruption, including repeated roughly 850-862 km jumps in one second in user 062 trajectory `20080926000623`.

These were treated as different failure modes rather than collapsed into one generic speed rule.

## 4. Timestamp precision hypothesis

Hypothesis: PLT `serial_date` might preserve hidden sub-second timing and duplicate-second rows might be a parser artifact.

Result: rejected.

For a trajectory with 45,215 duplicate text timestamps, reconstructing timestamps from `serial_date` produced the same 45,215 duplicates. Same-second rows shared the same serial-date value; microsecond differences versus text timestamps were floating-point conversion noise.

Decision: within-second order and velocity are not recoverable from this release. Same-second rows must be handled as simultaneous observations.

## 5. Same-second spatial structure

Across 212,409 same-second groups:

- median max-radius from the coordinate-wise median: 0.47 m;
- p95: 4.85 m;
- p99: 7.06 m;
- 95.32% are within 5 m;
- 99.61% are within 10 m;
- 99.84% are within 20 m.

A tiny corrupted tail reaches roughly 430 km radius.

This supports a 10 m same-second consolidation rule for the first implementation: compact groups collapse to one median coordinate, while spatial conflicts create continuity boundaries rather than fake averaged locations.

## 6. Exact duplicate content and leakage risk

SHA-256 over all 18,670 trajectory files found:

- 821 exact-duplicate hash groups;
- 1,677 participating files (8.98% of trajectories);
- all observed duplicate groups span multiple user IDs;
- participating files contain 2,965,977 points, or 11.92% of all points;
- extra copies beyond one representative account for 1,495,115 points, or 6.01% of the dataset.

Shared-content links involve 52 users across 18 connected components; the largest component contains 15 user IDs.

Decision: content hashes are required for leakage control. A user-only split does not guarantee content independence. This is an evaluation concern, not an inference-time deduplication rule.

## 7. Same-second consolidation experiment

Representative cases separated two failure modes clearly.

User 141 trajectory `20111022031803`:

- 56,780 raw points -> 11,565 timestamp rows;
- only 3 spatial conflicts;
- dominant duplicate bursts collapsed cleanly.

User 062 trajectory `20080926000623`:

- 8,117 raw points -> 8,091 timestamp rows;
- 26 same-second conflicts;
- repeated cross-region jumps between different timestamps remained, still producing multi-million-km/h speeds.

Conclusion: same-second ambiguity and impossible inter-timestamp movement are independent preprocessing problems.

## 8. Full-release consolidation result

Applying the exploratory 10 m rule across the release produced:

- 24,876,978 raw points -> 24,178,077 timestamp rows;
- 698,901 rows reduced (2.81%);
- 835 spatial-conflict timestamps (0.0035% of consolidated rows);
- 1 invalid coordinate point;
- 24,157,908 valid inter-timestamp movement segments.

## 9. Segment-speed distribution

After same-second consolidation:

- >100 km/h: 5.4029% of valid segments;
- >150 km/h: 0.9983%;
- >200 km/h: 0.3661%;
- >500 km/h: 0.2030%;
- >1,000 km/h: 0.0070%.

Trajectory-level max-speed prevalence is much larger because one extreme segment marks an entire trajectory; for example, 46.96% of trajectories have max speed >100 km/h while only 5.40% of valid segments exceed 100 km/h.

Decision: movement-noise reasoning should be performed primarily at segment level.

## 10. Temporal-gap sensitivity

Trajectory-level max-gap sensitivity after consolidation:

- >2 min: 65.92% of trajectories;
- >5 min: 50.95%;
- >10 min: 41.74%;
- >30 min: 29.66%;
- >1 h: 22.89%.

Decision: stay duration must not bridge arbitrary observation outages. `max_gap_s` is a sensitivity parameter; first benchmark values are 120 / 300 / 600 seconds.

## 11. Transportation-label audit and final V3 speed benchmark

The release contains 14,718 transportation-label intervals over 69 labeled users. These are auxiliary movement labels, not Home/Office ground truth.

An independent audit exposed an interval-semantics issue in the earlier analysis: treating label ends as inclusive converted many endpoint touches into one-second ambiguities. The project therefore adopted standard half-open `[start, end)` semantics.

Final audited accounting:

- 1,742 different-mode endpoint-touching pairs;
- 146 different-mode true-overlap pairs;
- 14,583 unambiguous canonical windows;
- 149 atomic ambiguous sweep slices;
- 138 report-level ambiguous windows with a stable active-mode set;
- 12,720.833 unambiguous labeled hours;
- 76.345 ambiguous labeled hours;
- ambiguous share: 0.597%.

The corrected V3 strict-containment join matched 4,807,087 of 11,878,198 valid segments from labeled users, for 40.47% coverage.

Key V3 speed values:

- airplane: 9,169 segments, median 625.91 km/h, p99 937.99, max 1,048.11; 52.92% exceed 500 km/h;
- train: median 93.14, p99 210.34;
- car: median 30.05, p99 119.63;
- taxi: median 31.64, p99 104.75;
- subway: median 49.63, p99 94.32;
- bus: median 16.91, p99 90.59;
- bike: median 11.19, p99 40.63;
- walk: median 4.08, p99 40.39.

The corrected V3 distribution is effectively unchanged in shape from the earlier benchmark. Therefore generic `speed > 100`, `>200`, or `>500 km/h => noise` rules are rejected: they would remove legitimate fast transportation. Rare multi-thousand-km/h maxima inside ordinary modes also show that label membership does not guarantee clean GPS.

## 12. EDA-backed cleaning proposal

The EDA supports this proposed preprocessing sequence, pending explicit contract approval before production code:

1. coordinate-domain validation;
2. same-second consolidation using a 10 m compact-group rule;
3. same-second spatial conflicts become continuity boundaries;
4. temporal gaps above configurable `max_gap_s` become continuity boundaries;
5. a release-specific hard speed guard of 1,200 km/h becomes a continuity boundary only, not endpoint deletion;
6. stay-point detection runs independently inside each resulting sequence.

The 1,200 km/h proposal sits above the audited airplane maximum of 1,048.11 km/h while catching clearly extreme corruption. It is a release-specific engineering guard, not a universal physical limit.

## 13. What is finished versus what remains

EDA and its transportation-label audit are closed for CP1. Remaining work is implementation-oriented:

- review/approve the cleaning + stay-point contract;
- write RED tests;
- implement preprocessing and stay-point detection;
- run a bounded stay-point sensitivity grid for continuity gap 120/300/600 s, stay radius 100/200/300 m, and dwell 10/20/30 min;
- then build the Home/Office heuristic.

## 14. Traceability / supporting documents

Detailed chronological evidence is retained in `docs/eda/00..14_*.md`. The mentor-facing reproducible notebook is `notebooks/02_geolife_eda_mentor_vi.ipynb`. Project chronology is in `docs/worklog.md`; reasoning and lessons are recorded in the EN/VI learning journals.

Raw trajectory data, user-level generated artifacts, and runtime caches are intentionally not committed because of dataset license/privacy constraints. Reportable aggregate evidence and the decision history are committed instead.