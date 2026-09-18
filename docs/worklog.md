# Worklog

## 2026-09-16 — CP1 foundation + EDA scaffold

Completed:

- initialized the new GeoLife repository and CP1 package structure;
- separated exploratory notebook code from future production code;
- added raw-data/license/privacy guardrails;
- documented EDA questions and preliminary source-profile observations;
- added a Modal-oriented EDA notebook and memory-bounded trajectory summarization helpers.

Evidence/status:

- files are present on branch `cp1-eda-foundation`;
- GitHub Actions CI passed for the EDA foundation;
- raw GeoLife 1.3 data is mounted in Modal and EDA is being executed against the official release.

## 2026-09-16 — Measured EDA Phase 1

Observed from the mounted release:

- 182 users;
- 18,670 trajectory files;
- 69 user folders containing `labels.txt`;
- strong long-tail imbalance: median 27.5 trajectories/user vs max 2,153;
- top 10 users account for 47.4% of all trajectories and top 50 for 84.0%;
- labeled users are heavier on average: 69 users account for 58.4% of trajectories;
- raw PLT parsing spot-check produced UTC-aware timestamps with no null timestamps in the inspected user-000 trajectory.

Interpretation and caveats are recorded in `docs/eda/02_initial_findings.md`.

## 2026-09-16 — Measured EDA Phase 2

Full trajectory-level scan completed over all 18,670 files.

Observed:

- 24,876,978 total GPS points, matching the v1.3 guide table;
- 0 null timestamps and 0 non-monotonic trajectories under the current parser;
- 698,900 duplicate-timestamp rows (2.81% of points) across 441 trajectories;
- only one invalid latitude, an isolated `400.166667` value among surrounding `40.166...` points;
- physically impossible raw speed/distance tails, including repeated ~850–862 km jumps in one-second intervals in user 062 trajectory `20080926000623`;
- at least one byte-identical trajectory duplicated across three users (`057`, `094`, `150`), confirmed by identical SHA-256.

## 2026-09-16 — Timestamp precision check

The earlier hypothesis that PLT `serial_date` might recover hidden sub-second timing was tested and rejected.

For a trajectory with 45,215 duplicate text timestamps:

- the same 45,215 duplicates remain when using `serial_date`;
- five distinct positions recorded at `2011-10-22 03:18:34` share exactly the same serial date;
- serial-date conversion differs from text timestamps only by a few microseconds of floating-point conversion noise, not meaningful extra timing precision.

Conclusion: duplicate-second observations are a property of the released timestamp precision, not a parser artifact. Speed must not be computed for zero-time pairs, and a downstream policy for same-second groups must be justified from their spatial spread.

Detailed evidence is recorded in `docs/eda/03_phase2_quality_findings.md` and `docs/eda/04_timestamp_precision_and_duplicates.md`.

## 2026-09-16 — Measured EDA Phase 3

Same-second spatial spread and exact raw-file duplication were quantified.

Observed:

- 212,409 same-second groups;
- group size is dominated by 5-point groups (160,534) and 2-point groups (48,838);
- median max-radius from the coordinate-wise median is 0.47 m, p95 is 4.85 m, and p99 is 7.06 m;
- 95.32% of same-second groups are within 5 m, 99.61% within 10 m, and 99.84% within 20 m;
- a tiny corrupted tail reaches about 430 km radius and is concentrated in trajectories such as user 062 / `20080926000623`;
- SHA-256 over all 18,670 raw trajectory files found 821 exact-duplicate hash groups and 1,677 participating files;
- about 8.98% of trajectory files participate in an exact-duplicate group, with 856 extra copies beyond one representative per group (~4.58% of all trajectory files);
- several exact duplicates span multiple user IDs.

Interpretation:

- most same-second groups are spatially compact and support a robust consolidation experiment, but spatially conflicting groups must be flagged rather than averaged blindly;
- exact content identity must be considered in train/test splitting and evaluation weighting to avoid leakage/overcounting.

Detailed evidence is recorded in `docs/eda/04_same_second_and_exact_duplicate_findings.md`.

## 2026-09-16 — Measured EDA Phase 4

Cross-user exact duplication was measured separately.

Observed:

- all 821 exact-duplicate hash groups span more than one user ID;
- 1,677 trajectory files are in cross-user duplicate groups, or 8.98% of all files;
- those files contain 2,965,977 GPS points;
- point-weighted exposure is 11.92% of all 24,876,978 GPS points.

Interpretation:

- the duplicate phenomenon is entirely cross-user in this release;
- duplicated trajectories are longer than average because their point-weighted share (11.92%) exceeds their file-count share (8.98%);
- evaluation must group by content hash to prevent byte-identical traces crossing folds, and point/trajectory-weighted metrics need duplicate-aware interpretation.

Detailed evidence is recorded in `docs/eda/05_cross_user_duplication.md`.

## 2026-09-16 — Measured EDA Phase 5

Redundant point mass and the user graph induced by shared exact content were quantified.

Observed:

- 1,495,115 GPS points are redundant beyond one representative per exact-content hash group, equal to 6.01% of all points;
- 52 users are involved in cross-user duplication;
- shared-content links form 18 connected components;
- the largest component contains 15 user IDs;
- several smaller 3-user components recur, while most remaining components are pairs.

Interpretation:

- 11.92% is exposure to duplicated groups, while 6.01% is the truly redundant point mass after keeping one representative per content hash;
- user-only splitting is not sufficient to guarantee content independence because distinct user IDs can be connected through identical trajectories;
- content-hash grouping is required for leakage control, and component-aware grouping is a candidate for stricter user-level evaluation;
- duplicate analysis is now sufficiently characterized for CP1 and should not expand further unless later evaluation exposes a specific need.

Detailed evidence is recorded in `docs/eda/06_duplicate_redundancy_and_user_components.md`.

## 2026-09-16 — Same-second consolidation prototype

An exploratory one-row-per-timestamp transform was tested with a 10 m compact-group candidate threshold.

Duplicate-heavy trajectory user `141` / `20111022031803`:

- 56,780 raw points -> 11,565 consolidated timestamp rows;
- 11,562 compact rows and only 3 spatial-conflict rows;
- after consolidation, the largest inspected segment speeds were about 225, 220 and 209 km/h.

Structurally corrupted trajectory user `062` / `20080926000623`:

- 8,117 raw points -> 8,091 consolidated rows;
- 26 same-second >10 m groups (then described as spatial conflicts) were flagged for non-consolidation;
- the repeated ~850 km jumps between singleton timestamps remain, with speeds around 3.1 million km/h.

Interpretation:

- same-second consolidation clearly removes one timestamp-resolution/order failure mode;
- it does not solve interleaved/mixed-trace corruption between distinct timestamps;
- movement anomaly handling therefore remains a separate preprocessing stage;
- the 10 m radius is still an experimental candidate, not a production threshold.

Detailed evidence is recorded in `docs/eda/07_same_second_consolidation_prototype.md`.

## 2026-09-16 — Full-release consolidation scan

The 10 m exploratory same-second transform was applied across all 18,670 trajectories.

Observed:

- 24,876,978 raw points -> 24,178,077 consolidated timestamp rows;
- 698,901 rows removed (2.81%);
- only 835 consolidated timestamps are spatial conflicts (0.0035%);
- the single invalid coordinate is still isolated cleanly;
- 24,157,908 valid inter-timestamp movement segments remain;
- segment-level prevalence after consolidation is 5.4029% >100 km/h, 0.9983% >150 km/h, 0.3661% >200 km/h, 0.2030% >500 km/h, and 0.0070% >1,000 km/h;
- trajectory-level exceedance remains much larger because one bad segment marks a whole trajectory (46.96% of trajectories have max speed >100 km/h);
- residual extreme trajectories remain essentially intact, including user 062 / `20080926000623` at ~3.10 million km/h;
- temporal gaps remain highly heterogeneous, with trajectory max-gap median 325 s, p90 ~11,010 s, p99 ~20,690 s and max 93,298 s.

Interpretation:

- same-second consolidation is useful and low-loss, but it is not the main driver of the residual high-speed tail;
- movement-noise decisions should use segment-level prevalence rather than trajectory-max prevalence;
- temporal continuity must be handled before stay duration is trusted;
- transportation-mode labels should be used next as auxiliary evidence to separate plausible fast travel from corrupted motion before choosing a global speed rule.

Detailed evidence is recorded in `docs/eda/08_full_consolidation_findings.md`.

## 2026-09-16 — Temporal-gap sensitivity + transportation-label inventory

Observed after consolidation:

- 81.85% of trajectories contain at least one gap >30 s;
- 75.83% contain at least one gap >60 s;
- 65.92% contain at least one gap >120 s;
- 50.95% contain at least one gap >5 min;
- 41.74% contain at least one gap >10 min;
- 29.66% contain at least one gap >30 min;
- 22.89% contain at least one gap >1 h;
- 15.87% contain at least one gap >2 h;
- 6.28% contain at least one gap >4 h.

Transportation label parsing produced 14,718 intervals across the 69 user folders that contain `labels.txt`. The largest interval counts are walk 6,460, bus 2,853, bike 2,089, taxi 1,179, car 993, subway 813, train 299 and airplane 17; rarer modes include boat, run and motorcycle.

Interpretation:

- temporal outages are common enough that a continuity threshold will materially affect stay-point detection and must be treated as a sensitivity parameter;
- transportation labels provide auxiliary evidence for plausible movement-speed distributions but are not Home/Office ground truth;
- the next and final movement-speed diagnostic is to join valid post-consolidation segments to same-user transportation intervals and compare speed percentiles by mode.

Detailed evidence is recorded in `docs/eda/09_gap_and_label_inventory.md`.

## 2026-09-16 — Provisional transportation-mode speed diagnostic

The strict-containment segment/label join matched 4,849,858 of 11,878,198 valid movement segments from labeled users (40.83%). The broad per-mode speed shape is informative: airplane median/p99 are about 624/938 km/h, train about 93/210, car about 30/120, taxi about 31/105, subway about 50/94, bus about 17/90, walk about 4/41 and bike about 11/41.

A critical label-quality issue was found before freezing the benchmark: 1,903 intervals are overlapping or touching the immediately previous interval under the current integrity check, including genuine overlaps across different modes. Therefore the current `merge_asof` assignment is not guaranteed to be unambiguous and exact per-mode statistics remain provisional.

Despite that caveat, one conclusion is already robust enough for design: a global 500 km/h filter would remove about 52.9% of currently matched airplane segments and is not acceptable as a generic speed-cleaning threshold. Extremely large maxima also appear inside non-airplane labels, so label membership alone does not make a segment clean.

Detailed evidence is recorded in `docs/eda/10_transport_speed_provisional.md`.

## 2026-09-16 — Transportation-label canonicalization (historical inclusive-end run)

The first canonicalization run treated label ends as inclusive. It produced 14,537 unambiguous windows and 1,886 ambiguous windows, with 12,723.9 / 76.9 hours of unambiguous / ambiguous time. These counts are retained only as historical evidence because a later audit found that endpoint touching was being converted into one-second ambiguity.

The historical V2 strict-containment run produced 4,812,641 matched segments (40.52% coverage) and a stable broad speed shape.

## 2026-09-17 — Half-open label semantics audit + final V3 benchmark

The transportation-label analysis was rerun under standard half-open `[start, end)` semantics, where endpoint touching is not overlap.

Final audited label accounting:

- 1,742 different-mode endpoint-touching pairs;
- 146 different-mode true-overlap pairs;
- 14,583 unambiguous canonical windows;
- 149 atomic ambiguous sweep slices;
- 138 report-level ambiguous windows with a stable active-mode set;
- 12,720.833 unambiguous labeled hours;
- 76.345 ambiguous labeled hours;
- ambiguous share 0.597%.

The final V3 strict-containment benchmark matched 4,807,087 of 11,878,198 valid labeled-user segments (40.47%). Key p99 values remain essentially unchanged: airplane 937.99 km/h, train 210.34, car 119.63, bus 90.59, bike 40.63 and walk 40.39. Airplane max is 1,048.11 km/h and 52.92% of canonical airplane segments exceed 500 km/h.

Conclusion: the interval-semantics correction changes the overlap-count narrative but does not change the broad movement-speed decision. Generic 100/200/500 km/h filters remain rejected, and the proposed release-specific 1,200 km/h continuity guard remains a conservative candidate.

EDA and the transportation-label audit are now closed for CP1. Next step: review/approve the cleaning + stay-point contract, then begin RED tests before production implementation.

## 2026-09-18 — Same-second transportation audit resolved Stage 2 semantics

Mentor review challenged the interpretation of the 10 m same-second threshold: with whole-second timestamps, fast movement can create non-trivial spread while within-second ordering remains unobservable.

The follow-up audit evaluated all 835 same-second groups with max radius >10 m, reconstructed exact within-group diameter, and joined available transportation labels using half-open `[start, end)` semantics.

Key evidence:
- 403 groups had one unambiguous mode;
- train 3/3, subway 20/25, and taxi 7/10 were within their audited one-second reference scales;
- walk 4/194 and bike 2/145 were within their diagnostic one-second scales;
- no unambiguous airplane case occurred in this subset;
- 68 groups exceeded 1 km diameter.

Decision:
- 10 m is a safe-to-collapse threshold, not a valid-vs-corrupt threshold;
- >10 m groups remain continuity boundaries because within-second order is unidentifiable;
- the diagnostic reason is `same_second_spatial_ambiguity`;
- transportation mode remains audit evidence only and is not used by production cleaning;
- boundary behavior is unchanged, so the full baseline and sensitivity grid do not need to be rerun.

Detailed evidence: `docs/eda/15_same_second_transport_audit.md`.

## 2026-09-18 — CP2 Home/Office baseline kickoff

PR #3 merged the CP1 cleaning + stay-point baseline into `main`. CP2 now starts from frozen production stay-point semantics instead of raw GPS.

New branch: `cp2-home-office-baseline`.

Scaffolded:

- `docs/design/03_home_office_baseline_contract.md`;
- `notebooks/03_home_office_baseline.ipynb`;
- full-release stay-event materialization with resumable cache;
- user-level history sufficiency audit;
- candidate per-user Haversine DBSCAN recurring-location representation;
- explicit timezone/geography review gate before any Home/Office time-of-day scoring.

Important design constraints:

- reconcile CP2 materialized stays to the CP1 total of 5,821;
- do not reimplement cleaning/stay detection in notebook code;
- do not blindly apply UTC+8 to the full release;
- do not force Home/Office labels for users with weak history;
- do not commit precise user-level inferred Home/Office locations;
- treat heuristic confidence as evidence strength, not calibrated probability.

Production Home/Office logic under `src/geolife/model/` remains intentionally unimplemented until timezone policy, recurring-location representation, scoring semantics and RED acceptance tests are reviewed.

## 2026-09-18 — CP2 stay-cache portability fix

The first full-release CP2 stay materialization completed the expensive cleaning/stay computation but failed while writing the final Parquet cache because the active Modal notebook image did not expose a Parquet engine (`pyarrow` / `fastparquet`) to pandas.

The materialization itself was unaffected. The notebook cache format was changed from Parquet to pandas pickle for this private intermediate artifact:

- no extra runtime dependency is required;
- the existing 500-file partial checkpoint/resume path is unchanged;
- precise user-level stays remain in the mounted private cache rather than the repository.

This is an execution-environment/cache-format fix only; it does not change CP1 or CP2 modeling semantics.
