# CP1 EDA summary for mentor

Date: 2026-09-16
Status: broad EDA is closed for the CP1 cleaning decision. One bounded transportation-label audit rerun remains before the exact V2 speed table is treated as final.

## 1. Objective

The EDA was designed to support concrete CP1 decisions for GeoLife preprocessing, stay-point detection, Home/Office inference, evaluation, and privacy. The process deliberately followed:

`observe distributions -> form hypotheses -> inspect anomalies -> test hypotheses -> quantify impact -> derive candidate rules`

rather than copying cleaning or stay-point thresholds from tutorials.

## 2. Dataset verification

Measured from the mounted GeoLife 1.3 release:

- 182 users;
- 18,670 trajectory files;
- 24,876,978 GPS points;
- 69 user folders with `labels.txt`.

The actual file counts resolve documentation ambiguity: the v1.3 table's 18,670 trajectories and 24,876,978 points match the release, while the guide text that mentions 73 labeled users does not match the 69 label folders present in the mounted release.

User history is strongly long-tailed. The median user has 27.5 trajectories, the maximum is 2,153, and the top 10 users contribute 47.4% of all trajectories. Therefore later evaluation should not rely only on point- or trajectory-weighted global metrics.

## 3. Raw quality findings

A full scan over all 18,670 trajectories found:

- 0 null timestamps;
- 0 non-monotonic trajectories under the current parser;
- 698,900 duplicate-timestamp rows (2.81% of all points), affecting 441 trajectories;
- one invalid latitude (`400.166667`), surrounded by plausible `40.166...` values;
- severe movement outliers, including repeated roughly 850-862 km jumps in one second in user 062 trajectory `20080926000623`.

The invalid coordinate and the repeated impossible-jump pattern were treated as different failure modes rather than collapsed into one generic speed rule.

## 4. Rejected timestamp hypothesis

Hypothesis: PLT `serial_date` might preserve hidden sub-second timing and the duplicate-second rows might be a parser artifact.

Test result: rejected.

For a trajectory with 45,215 duplicate text timestamps, reconstructing timestamps from `serial_date` produced the same 45,215 duplicates. Same-second rows had identical serial-date values; microsecond differences versus text timestamps were floating-point conversion noise.

Decision: within-second order and speed are not recoverable from this release. Same-second rows must be handled as simultaneous observations.

## 5. Same-second spatial structure

Across 212,409 same-second groups:

- median max-radius from the coordinate-wise median: 0.47 m;
- p95: 4.85 m;
- p99: 7.06 m;
- 95.32% are within 5 m;
- 99.61% are within 10 m;
- 99.84% are within 20 m.

A tiny corrupted tail reaches roughly 430 km radius.

This supported a 10 m same-second consolidation experiment: compact groups are replaced by one median coordinate, while spatially conflicting groups are treated as continuity boundaries rather than averaged into fake locations.

## 6. Exact duplicate content and evaluation leakage

SHA-256 over all 18,670 trajectory files found:

- 821 exact-duplicate hash groups;
- 1,677 participating files (8.98% of trajectories);
- all observed duplicate groups span multiple user IDs;
- those files contain 2,965,977 points, or 11.92% of all points;
- after keeping one representative per hash group, extra copies still account for 1,495,115 points, or 6.01% of the dataset.

Shared-content links involve 52 users in 18 connected components; the largest component contains 15 user IDs.

Decision: content hashes are required for leakage control. A user-only split does not guarantee content independence. This is an evaluation concern, not an inference-time deduplication rule.

## 7. Same-second consolidation experiment

Prototype tests separated two failure modes clearly.

Duplicate-heavy user 141 trajectory `20111022031803`:

- 56,780 raw points -> 11,565 timestamp rows;
- only 3 spatial conflicts;
- dominant duplicate bursts collapsed cleanly.

Corrupted user 062 trajectory `20080926000623`:

- 8,117 raw points -> 8,091 timestamp rows;
- 26 same-second conflicts;
- repeated cross-region jumps between different timestamps remained, still producing multi-million-km/h speeds.

Conclusion: same-second ambiguity and inter-timestamp movement corruption are separate preprocessing stages.

## 8. Full-release consolidation result

Applying the exploratory 10 m rule to the full release produced:

- 24,876,978 raw points -> 24,178,077 timestamp rows;
- 698,901 rows reduced (2.81%);
- 835 spatial-conflict timestamps (0.0035% of consolidated rows);
- 1 invalid coordinate point;
- 24,157,908 valid inter-timestamp movement segments.

The row accounting is consistent with the known 698,900 duplicate-timestamp rows plus the single invalid coordinate.

## 9. Segment speed distribution

After same-second consolidation:

- >100 km/h: 5.4029% of valid segments;
- >150 km/h: 0.9983%;
- >200 km/h: 0.3661%;
- >500 km/h: 0.2030%;
- >1,000 km/h: 0.0070%.

Trajectory-level max-speed counts are much larger because one bad segment marks an entire trajectory. For example, 46.96% of trajectories have max speed >100 km/h while only 5.40% of segments exceed 100 km/h.

Decision: movement cleaning should reason primarily at segment level, not from trajectory maxima.

## 10. Temporal-gap sensitivity

Trajectory-level max-gap sensitivity after consolidation:

- >2 min: 65.92% of trajectories;
- >5 min: 50.95%;
- >10 min: 41.74%;
- >30 min: 29.66%;
- >1 h: 22.89%.

Decision: stay duration must not bridge arbitrary observation outages. `max_gap_s` is a sensitivity parameter rather than a hidden implementation detail. Candidate values for the first stay-point benchmark are 120 / 300 / 600 seconds.

## 11. Transportation-label validation of plausible speed

The release contains 14,718 transportation-label intervals over 69 labeled users. Labels are auxiliary movement evidence, not Home/Office ground truth.

A first strict-containment segment/label join matched 4,849,858 segments (40.83% coverage among valid segments of labeled users), but label interval ambiguity required a canonicalization step.

An independent re-audit identified an interval-semantics issue in the original canonicalization: it treated end times as inclusive and therefore turned many different-mode endpoint touches into one-second ambiguous windows. The project now uses standard half-open `[start, end)` semantics, where touching endpoints are not overlaps.

Corrected label accounting under `[start, end)`:

- 14,583 unambiguous canonical windows;
- 138 ambiguous windows;
- 12,720.83 unambiguous labeled hours;
- 76.345 ambiguous hours;
- ambiguous share approximately 0.597% of represented labeled time;
- the external audit reported 1,742 different-mode endpoint-touching pairs and 146 different-mode pairs with true temporal overlap.

This correction changes the window-count narrative materially but not the core interpretation: true label ambiguity occupies only about 0.6% of represented labeled time.

The previously reported V2 strict-containment benchmark (4,812,641 matched segments, 40.52% coverage) and its exact per-mode percentiles were computed under the earlier inclusive-end convention. Their broad shape was nearly identical to the provisional benchmark, so the qualitative speed conclusions remain useful, but these exact V2 values should be recomputed once under `[start, end)` before being presented as the final audited benchmark.

Historical V2 values that support the qualitative conclusion include airplane around 625 km/h median and 938 km/h p99, train around 93/210, car around 30/120, bus around 17/91, bike around 11/41 and walk around 4/40. More than half of airplane segments in that historical benchmark exceeded 500 km/h.

Decision retained: generic `speed > 100`, `>200`, or `>500 km/h => noise` rules are not justified because they would remove legitimate fast transport. Rare multi-thousand-km/h values inside ordinary modes also show that speed is best used as a conservative corruption guard rather than a generic motion filter.

## 12. EDA-backed cleaning proposal

The EDA supports this proposed preprocessing sequence, pending review before production implementation:

1. coordinate-domain validation;
2. same-second consolidation with a 10 m compact-group rule;
3. spatial-conflict timestamps become continuity boundaries;
4. temporal gaps above configurable `max_gap_s` become continuity boundaries;
5. a release-specific hard speed guard of 1,200 km/h becomes a continuity boundary only, not endpoint deletion;
6. stay-point detection runs independently inside each resulting sequence.

The 1,200 km/h guard remains a conservative proposal, not a universal physical limit. The broad transport evidence supports avoiding lower global speed cutoffs, while the exact half-open V2 transport table should be rerun before final contract approval cites exact airplane percentages/maxima as fully audited evidence.

## 13. What is finished versus what remains

Broad EDA is complete for the CP1 cleaning decision. Remaining work is bounded and implementation-oriented:

- rerun the transportation-label V2 segment join/table once under `[start, end)` semantics;
- review/approve the cleaning + stay-point contract;
- write RED tests;
- implement preprocessing and stay-point detection;
- run a bounded stay-point sensitivity grid for continuity gap 120/300/600 s, stay radius 100/200/300 m, and dwell 10/20/30 min;
- then build the Home/Office heuristic.

## 14. Traceability / supporting documents

Chronological evidence is retained in:

- `docs/eda/00_source_profile.md` — source-guide expectations and discrepancies;
- `docs/eda/01_eda_plan.md` — questions and method;
- `docs/eda/02_initial_findings.md` — measured inventory and user imbalance;
- `docs/eda/03_phase2_quality_findings.md` — full-scan quality and anomalies;
- `docs/eda/04_timestamp_precision_and_duplicates.md` — rejected serial-date hypothesis;
- `docs/eda/04_same_second_and_exact_duplicate_findings.md` — same-second spread and hash duplication;
- `docs/eda/05_cross_user_duplication.md` — duplicate prevalence and point exposure;
- `docs/eda/06_duplicate_redundancy_and_user_components.md` — redundant point mass and connected components;
- `docs/eda/07_same_second_consolidation_prototype.md` — prototype behavior on representative trajectories;
- `docs/eda/08_full_consolidation_findings.md` — full-release consolidation and segment speed;
- `docs/eda/09_gap_and_label_inventory.md` — temporal-gap sensitivity and transport labels;
- `docs/eda/10_transport_speed_provisional.md` — first speed-by-mode benchmark and initial overlap/touching issue;
- `docs/eda/11_label_overlap_canonicalization.md` — corrected half-open label accounting and historical V2 status;
- `docs/eda/12_transport_speed_final.md` — historical V2 table plus interval-audit caveat;
- `docs/eda/14_label_interval_semantics_audit.md` — independent audit correction and reporting convention;
- `docs/design/01_cleaning_staypoint_contract.md` — proposed implementation contract derived from EDA;
- `docs/worklog.md` — chronological project milestones;
- `docs/learning-journal-en.md` and `docs/learning-journal-vi.md` — learning narrative and decision evolution.

Raw trajectory data, user-level generated artifacts, and runtime caches are intentionally not committed because of the GeoLife license/privacy constraints. The reportable aggregate evidence and decision history are committed instead.
