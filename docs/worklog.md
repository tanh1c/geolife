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

## 2026-09-18 — First CP2 full-release stay materialization

The first CP2 run completed and reproduced the frozen CP1 stay total exactly:

- 5,821 stays;
- 136 users with at least one stay.

User-history support:

- 120 users with >=2 stays;
- 99 with >=5;
- 81 with >=10;
- 114 users with stays on >=2 distinct UTC dates;
- 83 with >=5 distinct UTC dates;
- 62 with >=10 distinct UTC dates.

The candidate per-user Haversine DBSCAN representation at 200 m produced 1,885 candidate locations, of which 635 had >=2 stays; 104 users had at least one recurring location.

A key diagnostic is DBSCAN chaining: the largest distance from a cluster median representative to a member stay reached ~526.7 m even though epsilon was 200 m. Therefore 200 m cannot be interpreted as a hard location-radius bound and clustering semantics remain unfrozen.

The stay geography is strongly Beijing-centered but includes substantial outliers, confirming that a blanket UTC+8 conversion across the full release is not acceptable without an explicit cohort/timezone policy.

The first notebook execution also exposed a cache-format portability issue: pandas could not write Parquet in the active Modal environment because no Parquet engine was available. The final private cache was successfully saved as pandas pickle and contains all 5,821 stays.

## 2026-09-18 — CP2 timezone/geography audit scaffold

The Home/Office notebook now has an explicit geography sensitivity stage before any time-of-day scoring.

Candidate v1 approach:

- approximate Beijing reference point: 39.9042 N, 116.4074 E;
- audit radii: 50 / 100 / 200 km;
- per-user metrics: share of stays and share of dwell time inside each radius;
- candidate cohort rule for review: >=80% of stays and >=80% of dwell within 100 km;
- only in-radius stays from eligible users are converted to `Asia/Shanghai`;
- travel/out-of-radius stays from otherwise Beijing-focused users remain excluded;
- out-of-cohort users abstain instead of receiving a guessed timezone.

This policy is not frozen yet. The next notebook run should review threshold sensitivity and cohort coverage before Home/Office scoring is implemented.

Detailed plan: `docs/eda/16_cp2_timezone_geography_audit.md`.

## 2026-09-18 — CP2 recurring-location audit moved from DBSCAN to complete linkage

The first 200 m DBSCAN experiment produced useful recurrence structure but exposed chaining: a cluster member could be ~526.7 m from the median representative even though epsilon was 200 m.

The next CP2 gate now compares per-user complete-linkage clustering at 100 / 200 / 300 m on the frozen Beijing semantic cohort.

Complete linkage is preferred for this audit because the threshold has a direct compactness interpretation: the final cluster diameter should not exceed the threshold.

The 200 m value remains a candidate engineering choice until sensitivity and exact diameter outputs are reviewed. Home/Office scoring stays blocked until this gate is resolved.

Detailed plan: `docs/eda/17_cp2_recurring_location_audit.md`.

## 2026-09-18 — CP2 recurring-location gate resolved; Home/Office scoring audit started

Complete-link sensitivity on the frozen Beijing semantic cohort produced:

- 100 m: 1,320 locations, 499 recurring, 67 users with recurrence;
- 200 m: 1,111 locations, 486 recurring, 73 users with recurrence;
- 300 m: 1,007 locations, 473 recurring, 73 users with recurrence.

The 200 m configuration verified a maximum cluster diameter of 199.23 m. It is now frozen as the CP2 v1 recurring-location engineering baseline because it avoids DBSCAN chaining, preserves the same recurring-user coverage as 300 m, and remains a middle sensitivity choice.

The notebook now proceeds to a first Home/Office scoring audit:

- Home candidate window: 21:00–06:00 local;
- Office candidate window: weekdays 09:00–17:00 local;
- stays contribute by exact interval overlap, not arrival hour;
- candidates require recurrence plus at least two relevant dates;
- ranking uses relevant-dwell share with date/dwell support and top-1 vs top-2 margin;
- Home and Office may resolve to the same location and that ambiguity is surfaced explicitly;
- no share/margin emission threshold or confidence formula is frozen yet.

Detailed plan: `docs/eda/18_cp2_home_office_scoring_audit.md`.

## 2026-09-18 — First Home/Office evidence measured; emission sensitivity added

The first interval-overlap scoring run on the frozen 97-user Beijing semantic cohort produced:

- 73 users with recurring semantic locations;
- 47 users with a supported Home candidate;
- 40 users with a supported Office candidate;
- 27 users with both;
- 7/27 both-candidate users with the same leading location for Home and Office.

Home evidence was stronger than Office evidence:

- Home median relevant-dwell share / top-two margin: 0.635 / 0.513;
- Office median relevant-dwell share / top-two margin: 0.357 / 0.243.

The low tail also shows that ranking alone is insufficient: the weakest supported candidates can have shares around 0.09 and near-zero margins under the current two-date support rule.

Therefore no emission threshold is frozen yet. The notebook now runs separate Home and Office sensitivity grids over:

- nearby behavioral-time windows;
- minimum relevant dates;
- minimum relevant-dwell share;
- minimum top-two share margin.

The sensitivity also reports whether the top location remains stable when time windows shift.

Detailed plan: `docs/eda/19_cp2_home_office_sensitivity.md`.

## 2026-09-18 — CP2 Home/Office scoring gate resolved

Bounded time-window sensitivity showed stable top-location selection:

- Home 20–06 vs baseline 21–06: 93.6% same top location;
- Home 22–06 vs baseline: 90.5%;
- Office 08–17 vs baseline 09–17: 95.0%;
- Office 09–18 vs baseline: 92.5%.

CP2 v1 therefore keeps the interpretable baseline windows:

- Home: 21:00–06:00 local;
- Office: weekdays 09:00–17:00 local.

Emission gates are frozen at the middle sensitivity settings:

- Home: >=3 relevant dates, share >=0.50, margin >=0.20 → 27 emitted users;
- Office: >=3 relevant dates, share >=0.30, margin >=0.10 → 16 emitted users.

The separate gates are intentional because measured Office evidence is weaker than Home evidence.

Heuristic evidence strength is defined as the arithmetic mean of relevant-dwell share, top-two share margin, and a support factor capped at five relevant dates. It is explicitly not a calibrated correctness probability.

The CP2 design contract is now approved for RED tests before production model implementation.

## 2026-09-18 — CP2 RED tests implemented; production model CI GREEN

After freezing the scoring contract, eight CP2 acceptance tests were added before production implementation.

The tests cover:

- Beijing-focused user eligibility with observation-level travel exclusion;
- complete-link clustering that prevents >200 m chaining;
- exact night-window interval overlap;
- allowing Home and Office to resolve to the same location;
- Home abstention when top-two margin is weak;
- default Home emission and evidence-strength formula;
- the separate Office emission gate;
- frozen config/evidence-strength semantics.

The first production CI run exposed a zero-evidence edge case: an empty Home or Office feature family could preserve object dtype after merging, and an eager division inside `np.where` raised `ZeroDivisionError`.

The implementation was corrected by coercing dwell columns to numeric and using `np.divide(..., where=denominator > 0)`.

CI #138 then passed all **20 tests**, notebook JSON validation, CP1 imports, and CP2 model API imports.

Production APIs now live under `src/geolife/model/home_office.py`.

One release-level gate remains: run the notebook production parity cell on the cached 5,821 stays and verify the production defaults emit 27 HOME and 16 OFFICE labels.

## 2026-09-18 — CP2 full-release production parity passed

The final CP2 release-level gate was run on the cached 5,821-stay full-release table using the production `infer_home_office()` default config.

Observed:

- HOME: 27;
- OFFICE: 16;
- total emitted rows: 43;
- unique users with at least one emitted label: 36.

The expected 27/16 emission counts exactly match the frozen notebook sensitivity decision.

Production parity check: PASS.

Together with the GREEN CI test suite, this closes the CP2 v1 implementation gate. PR #4 is ready for normal review/merge consideration.

## 2026-09-18 — Notebook narrative pass aligned with mentor-audit style

After CP2 production parity passed, the four implementation/audit notebooks were expanded so that future readers can reconstruct not only what code ran, but why each gate existed and what conclusions are justified.

Updated:

- `notebooks/02_cleaning_staypoint_validation.ipynb`
- `notebooks/02b_staypoint_sensitivity_validation.ipynb`
- `notebooks/02c_same_second_transport_audit.ipynb`
- `notebooks/03_home_office_baseline.ipynb`

The narrative pattern now mirrors the CP1 mentor-audit notebook:

- question / motivation;
- how to read output;
- interpretation;
- what must not be inferred;
- explicit decision / downstream gate.

Stale assumptions were also corrected in the explanatory text:
- no blanket UTC+8 across the release;
- DBSCAN is documented as a historical prototype, not the frozen recurring-location implementation;
- same-second >10 m is documented as unresolved spatial ambiguity, not automatic corruption;
- notebook 02 prefix sensitivity is explicitly separated from the final user-stratified sensitivity in notebook 02b.

No production algorithm or frozen parameter changed in this pass.

## 2026-09-18 — CP3 API serving kickoff and implementation

Checkpoint 3 starts from the merged CP2 v1 Home/Office production baseline.

The API contract was written before implementation in `docs/design/04_api_contract.md`.

Frozen v1 serving boundary:

- one user per request;
- input is CP1 stay events, not raw GPS;
- the HTTP layer uses frozen CP2 defaults only;
- valid weak/out-of-scope evidence returns HTTP 200 with explicit abstention;
- malformed schema/time/coordinates return HTTP 422;
- precise inferred Home/Office coordinates are omitted from the response;
- POI semantics remain out of scope until separately defined.

RED API tests were added first and then the implementation was added under:

- `src/geolife/api/schemas.py`;
- `src/geolife/api/service.py`;
- `src/geolife/api/app.py`.

The service adapter derives `duration_s` from arrival/departure timestamps instead of accepting a second potentially inconsistent duration field.

Stable abstention reasons:

- `out_of_scope_geography`;
- `insufficient_recurring_history`;
- `insufficient_semantic_evidence`.

The FastAPI validation handler strips rejected input values from validation responses so precise stay coordinates are not echoed back by default.

The API tests also lock that clients cannot override frozen CP2 thresholds in v1 and that emitted response/OpenAPI schemas do not expose precise inferred coordinates.

A dedicated release-level notebook, `notebooks/04_api_contract_validation.ipynb`, reuses the private 5,821-stay CP2 cache and is designed to compare all 136 per-user HTTP requests against direct production inference. The remaining CP3 release gate is to run that notebook and verify full-release HTTP ↔ direct-model parity.

## 2026-09-18 — CP3 API CI GREEN

CI #168 passed on the CP3 API implementation head.

Validated:

- **36 tests** passed;
- Python source compilation passed;
- notebook JSON validation includes `notebooks/04_api_contract_validation.ipynb`;
- CP1 production API imports passed;
- CP2 model API imports passed;
- CP3 FastAPI imports passed.

The test suite includes privacy assertions that validation responses do not echo rejected coordinate values, OpenAPI emitted-result schema omits precise coordinates, and request-time model-threshold overrides are rejected.

A Starlette/FastAPI test-client deprecation warning is currently emitted by the installed dependency stack, but it does not affect test correctness. This is dependency/tooling noise rather than a model/API contract failure and can be handled separately from the CP3 semantic gate.

The only remaining CP3 release-level gate is the private-data full-release HTTP parity run in notebook 04.

## 2026-09-18 — CP3 full-release HTTP parity passed

Notebook 04 replayed all **136 users** from the private 5,821-stay cache through the FastAPI endpoint, one user per request.

Direct production output:

- HOME 27;
- OFFICE 16;
- 43 emitted rows;
- 36 unique emitted users.

HTTP output matched exactly:

- HOME 27;
- OFFICE 16;
- 43 emitted rows;
- 36 unique emitted users.

The notebook also passed exact emitted-key parity, location-id parity, evidence-field parity, and validation/privacy smoke checks.

Observed abstention counts:

- HOME: geography 39, recurring-history 24, semantic-evidence 46;
- OFFICE: geography 39, recurring-history 24, semantic-evidence 57.

These counts are valid model outcomes, not failures.

The replay also surfaced repeated pandas `FutureWarning` messages for partial-emission users because the model concatenated an emitted frame with an empty frame. Production output was unchanged, but the implementation was cleaned up to concatenate only non-empty frames. A regression test now locks that partial emission does not produce this FutureWarning.

With that warning fix and final CI, CP3 has no remaining semantic/release-level parity gate.


## 2026-09-22 — Checkpoint 1 standalone OpenAPI deliverable

The FastAPI serving layer already exposed runtime OpenAPI at `/openapi.json` and Swagger UI at `/docs`. To match the mentor's Checkpoint 1 deliverable literally, the repository now also commits a standalone `openapi.yaml`.

Added:

- root-level `openapi.yaml` for direct review;
- `scripts/export_openapi.py` to regenerate YAML from `geolife.api.app:app`;
- PyYAML as a development dependency;
- a regression test that checks the committed YAML against the runtime FastAPI contract shape;
- an explicit manual Home/Office plausibility-review protocol under `docs/evaluation/`.

The model/API semantics are unchanged. This pass makes the existing FastAPI/OpenAPI implementation easier to review against the mentor checklist.


## 2026-09-22 — API contract realigned to the literal Track B1 requirement

A review against the original mentor brief found that the existing API used
`POST /v1/home-office/infer` with already-detected stay events, while Checkpoint 1
explicitly asks for `/v1/classify/{user_id}` with a GPS lat/lng sequence.

The repo now exposes the mentor-facing contract:

- `POST /v1/classify/{user_id}`;
- input: raw GPS observations with `timestamp_utc`, latitude and longitude;
- pipeline: frozen CP1 cleaning → stay detection → semantic inference;
- output: HOME / OFFICE / generic POI plus heuristic `confidence`;
- HOME/OFFICE confidence maps to the existing evidence-strength heuristic;
- generic POI confidence is visit share among semantic stays;
- `openapi.yaml` and Swagger/OpenAPI now document the primary classify route.

The previous stay-event endpoint remains available as a deprecated internal compatibility
route so existing full-release HTTP parity evidence is not discarded.

Generic POI here means "other recurring location"; semantic POI categorization via
reverse geocoding/H3 remains the Checkpoint 2 bonus.


## 2026-09-22 — Checkpoint 1 Terraform foundation added

The original Track B1 Week 1 brief explicitly requires repository/environment/Terraform
setup. A minimal AWS Terraform foundation is now committed under `infra/terraform/`.

The foundation:

- pins Terraform and the AWS provider;
- defines region/project/environment variables;
- defaults development to `ap-southeast-1`;
- applies common AWS tags;
- ignores local state, provider cache and local tfvars;
- is validated in GitHub Actions with `terraform fmt`, `init -backend=false` and
  `terraform validate`.

No AWS resources are created yet. EC2/Lambda/API Gateway/SQS/CloudWatch resources remain
Checkpoint 2/3 work so the repository does not imply a deployment that does not exist.

## 2026-09-22 — Manual Home/Office plausibility sample completed

The Checkpoint 1 evaluation note now includes a privacy-safe manual review of three
GeoLife users from the executed private Home/Office notebook:

- user 002: HOME and OFFICE patterns both plausible;
- user 009: HOME and OFFICE patterns both plausible;
- user 022: OFFICE strongly plausible; HOME remains ambiguous and correctly abstains
  because dwell share 0.479 is below the frozen 0.50 HOME gate.

The review records stay/date/dwell/share/margin evidence but intentionally omits exact
coordinates and raw trajectories.

This is a plausibility review, not an accuracy estimate. GeoLife still has no
authoritative HOME/OFFICE ground truth.

Evidence: `docs/evaluation/01_home_office_manual_plausibility.md`.

## 2026-09-24 — Re-opened CP2 timezone/geography semantics

A review of notebook 03 exposed an important modeling distinction that the frozen CP2 v1 narrative did not make sharply enough.

The current rule uses an approximate Beijing reference point plus a 100 km radius to define a Beijing-focused cohort. That rule is an engineering cohort heuristic; it is **not** a timezone boundary and it does not prove that all retained coordinates are geographically inside Beijing.

External reference review clarified that:

- the IANA time zone database uses representative geographic locations to name zones; those coordinates are not rectangular latitude/longitude bounds;
- practical coordinate-to-timezone lookup is a point-in-polygon problem over timezone boundary data;
- timezone-boundary-builder publishes polygons keyed by IANA `tzid` values, and libraries such as `timezonefinder` can perform offline WGS84 coordinate → IANA timezone lookup;
- Beijing administrative membership is a separate geography problem and should use an explicit Beijing boundary/polygon if that scope is required.

Proposed next audit:

1. assign each stay an IANA timezone from its own latitude/longitude;
2. convert each stay with `zoneinfo.ZoneInfo(tzid)`;
3. evaluate user-level timezone concentration separately from Beijing geographic concentration;
4. if CP2 still needs a Beijing-only semantic cohort, use a Beijing administrative polygon or explicitly label a central-Beijing distance rule as a cohort heuristic;
5. rerun full-release sensitivity and HTTP/direct-model parity before changing the frozen CP2 v1 production behavior.

No production semantics changed in this review.

References:
- IANA tz theory: https://www.iana.org/time-zones/theory
- timezone-boundary-builder: https://github.com/evansiroky/timezone-boundary-builder
- Beijing official administrative-boundary maps: https://ghzrzyw.beijing.gov.cn/zhengwuxinxi/tzgg/sj/202609/t20260911_4859523.html

## 2026-09-24 — Notebook 03 timezone-v2 candidate implemented

Notebook 03 was revised to separate timezone assignment from Beijing geographic scoping.

Implemented in `notebooks/03_home_office_baseline.ipynb`:

- pinned notebook-only dependency `timezonefinder==9.0.0`;
- each CP1 stay now receives an IANA timezone from its own WGS84 `(lat, lon)`;
- user concentration is measured with stay-share and dwell-share in `Asia/Shanghai`;
- the 80/80 threshold is retained only as a migration control so the timezone rule changes in isolation;
- resolved travel stays from eligible users are retained and converted using their own timezone instead of being discarded by a Beijing-radius rule;
- local wall-clock fields are derived per stay with `ZoneInfo(timezone_id)`;
- clustering and scoring outputs from the old 97-user / 4,197-stay cohort are treated as stale and must be rerun;
- production CP2 v1 counts (27 HOME / 16 OFFICE) remain a historical comparison, not a parity assertion for the candidate;
- production end-to-end DBSCAN parity is intentionally gated until the timezone-v2 contract is implemented in `src/`.

The notebook JSON was cleared of stale outputs and syntax-validated before commit.

Commit: `e6005639b6a68050097b83333c9cf522d2c569ef`.

Next step: Run All on the full frozen 5,821 stays, review timezone/cohort sensitivity and downstream emission deltas, then decide whether production migration is justified.

## 2026-09-24 — Final notebook 03 removes timezone-based user filtering

The executed timezone-v2 candidate showed that coordinate-to-IANA lookup works cleanly on the frozen CP1 stay inventory: all 5,821 stays resolved to a timezone, with Asia/Shanghai dominating the release. Review then clarified that the assignment does not require a Beijing-only or China-only cohort.

Notebook 03 was therefore finalized with a simpler semantic scope:

- assign an IANA timezone to every stay from its own WGS84 coordinate;
- convert each stay from UTC into its own local wall-clock time;
- keep every stay whose timezone resolves;
- retain Asia/Shanghai stay/dwell share only as a dataset-profile diagnostic, not an eligibility gate;
- let abstention come from history sufficiency, recurring-location support, and weak HOME/OFFICE behavioral evidence rather than geography;
- keep complete-link 200 m and the v1 HOME/OFFICE gates as audit controls until the full notebook is rerun on the widened semantic scope;
- treat current production CP2 v1 as a historical comparison until src/ is migrated and parity is re-established.

The final notebook also adds a compact final summary table and rewrites the narrative in the explanatory style of the original notebook 03.

Notebook commit: `0a36ad9a8a208b4c6d46299418f389c882660a18`.

The earlier 80/80 Asia/Shanghai-focused candidate is superseded as a filtering rule; its sensitivity table remains useful only for describing how geographically concentrated GeoLife is.

## 2026-09-24 — Final DBSCAN sensitivity rerun on timezone-resolved scope

Notebook 03 reran the DBSCAN recurring-location sensitivity after the semantic scope was finalized as all timezone-resolved stays. All 5,821 stays resolve to a timezone, so this recurring-location audit operates on the full frozen CP1 stay inventory.

Measured results:

- eps 10 m: 78 users with a recurring location, 0 recurring clusters above 200 m, max recurring diameter ~110.84 m;
- eps 20 m: 84 recurring users, 0 clusters above 200 m, max ~172.31 m;
- eps 30 m: 90 recurring users, 0 clusters above 200 m, max ~181.32 m;
- eps 50 m: 94 recurring users, 6 clusters above 200 m, max ~248.80 m;
- eps 100 m: 97 recurring users, 24 clusters above 200 m, max ~441.31 m;
- eps 150 m: 102 recurring users, 53 clusters above 200 m, p95 diameter ~258.85 m, max ~627.11 m;
- eps 200 m: 104 recurring users, 86 clusters above 200 m, p95 diameter ~307.99 m, max ~836.66 m.

Interpretation:

- increasing eps improves recurring-user coverage but progressively weakens spatial compactness;
- 30 m is the largest tested DBSCAN eps with zero recurring clusters above 200 m;
- 50 m is the first tested value where chaining produces >200 m recurring clusters;
- eps=200 m must not be interpreted as a 200 m cluster-diameter contract.

This result strengthens the motivation for keeping DBSCAN as a benchmark while using complete-link clustering for a directly interpretable maximum-diameter contract.

Notebook commit: `147870a9ec2270fecd126df7e9a60a41d01e8d2d`.

## 2026-09-26 — 03a behavior-first EDA checkpoint

03a is frozen as an exploratory evidence checkpoint; it does not alter CP1, the production Home/Office model, or notebook 03.

Measured findings:

- Anchor structure is heterogeneous among 136 stay-bearing users: 19 dominant, 13 two-anchor, 72 multiple-anchor, and 32 with no stable anchor. The 46 remaining release users have no CP1 stay.
- Schedule calibration does not support personalized schedule inference with the current JSD approach: 46 users meet schedule support, but within-user weekly JSD median is 1.000 (IQR 0.652–1.000), versus 0.904 between-user and 1.000 shuffled-week null.
- The next hypothesis is the mobile-work-like × OFFICE-abstention regime: all 23 mobile-work-like candidates are multiple-anchor, all 23 abstain under frozen OFFICE, and none emits frozen OFFICE. This is behavioral evidence only, not an occupation or Work label.

The next phase is a narrow 03b hypothesis audit using independent transportation, route/transition, weekday-weekend, sensitivity, and negative-control evidence before considering any Home/Work v2 design.

## 2026-09-27 — 03b audit takeover prepared

The 03b mobile/distributed-mobility hypothesis audit was taken over from handoff checkpoint `d2a8a5b` on branch `eda/03b-audit-completion`.

Prepared changes:

- bounded/resumable frozen-CP1 transport-segment audit with canonical half-open label containment;
- genuine candidate sensitivity including 100 m / 300 m clustering-dependent reruns;
- A/B/C support-balance summaries;
- recurrent-transition edge entropy and negative-control summaries;
- measured Q1–Q10 report rendering.

No scientific result from these changes is accepted yet. Full GeoLife execution remains pending in Modal; frozen CP1, frozen CP2/HomeOffice, API behavior, and notebook 03 are unchanged.

## 2026-09-28 — Fixed Modal cache-path regression in 03b runner

The first Modal Volume runner exposed two preflight failures before any 03b evidence was accepted:

- the public report renderer still contained the forbidden phrase `semantic WORK`, so the targeted report-wording test correctly failed;
- symlinking `artifacts/03a` to `/mnt/geolife-data` violated 03a's resolved-path privacy guard and stopped materialization before `summary.json` could be produced.

The continuation now removes the forbidden wording and configures persistent caches explicitly via `GEOLIFE_03A_CACHE_DIR` / `GEOLIFE_03B_CACHE_DIR`. The 03a privacy guard is repointed to the approved cache root at runtime while explicit cache paths are passed to avoid Python default-argument binding issues. No scientific 03b result was accepted from the failed run.

## 2026-09-29 — Mentor follow-up: DBSCAN MinPts sensitivity

Mentor raised a follow-up question for the Home/Office recurring-location benchmark: DBSCAN currently fixes `min_samples=1` while only `eps` has received an explicit sensitivity study.

Repository check confirms:

- `notebooks/03_home_office_baseline.ipynb` uses `DBSCAN(..., min_samples=1)`;
- `src/geolife/model/home_office.py` also uses `min_samples=1`.

This setting is not considered optimized. With `min_samples=1`, every stay can become a core point, so DBSCAN behaves close to epsilon-neighborhood connected components: isolated stays become singleton clusters instead of noise, and connectivity/chaining is maximally permissive.

Follow-up after the current 03b audit:

- run a DBSCAN `min_samples` sensitivity study rather than assuming 1;
- test at least `1 / 2 / 3 / 5`;
- cross-check representative `eps` values rather than changing MinPts in isolation;
- measure recurring-user coverage, recurring-location count, noise/singleton behavior, p95/max diameter, clusters above 200 m, and users losing all recurring-location support;
- compare the result with complete-link 200 m under the same frozen stay inventory.

Do not choose a MinPts value merely because it maximizes coverage. The goal is an explainable coverage–density–compactness trade-off.

## 2026-09-29 — Fixed 03b support-schema and verification-gate regression

The next Modal run passed the targeted 03b preflight (`12` tests and targeted Ruff) and reached the full audit, then stopped before evidence generation with:

```text
KeyError: observed_span_h
```

Cause: 03b support matching/balance referenced `observed_span_h`, which is a point-day field but is not exported by the frozen 03a user-level feature table. The audit now uses only support fields that actually exist in 03a:

```text
active_days
usable_temporal_days
usable_active_days
cp1_stay_count
```

The same run also showed that `ruff check .` is not an appropriate 03b verification gate because existing notebooks/tests outside 03b contain unrelated lint debt. Final verification is therefore:

- targeted 03b tests;
- full repository pytest regression suite;
- targeted Ruff on the 03b runner and 03b tests;
- parity/report/privacy checks.

The failed audit produced no accepted `summary.json`; downstream missing-summary errors were consequences of the earlier support-balance failure.

## 2026-09-29 — 03b full-release audit completed

The Modal full-release 03b audit completed successfully after the cache/support fixes.

Verification:

- frozen parity: 23 candidates / 23 multiple-anchor / 23 OFFICE-abstained / 0 OFFICE-emitted;
- targeted 03b tests passed;
- full repository tests passed;
- targeted Ruff passed;
- report/privacy checks passed.

Measured evidence:

- sensitivity is very stable: 100 m and 300 m anchor variants retain the exact same 23 users (Jaccard 1.0); ±10% mobility threshold changes only one user; ±1 weekday support leaves the set unchanged;
- A/B support matching is complete (23 pairs, 0 unmatched), but aggregate support remains imbalanced: Group A has substantially more active/usable days and CP1 stays than Group B, so matching quality is not strong enough to treat A/B differences as causal evidence;
- route structure differs descriptively (A median 13 transitions and edge entropy 3.55 vs B 8 and 2.81), but median recurrent-edge count is 0 in both A and B; Group C has median recurrent-edge count 1;
- transport labels are sparse and imbalanced (A 6 labeled users, B 12, C 3), so mode composition is supporting evidence only;
- motorized distance share is similar across groups (A 0.693, B 0.732, C 0.742), which does not independently distinguish Group A;
- weekday-minus-weekend distance contrast is near zero for A (-0.12 km/day) and is descriptive rather than independent because weekday mobility contributes to candidate construction.

Research decision remains **mixed evidence**. The cohort is robust as a descriptive behavioral regime, but current independent evidence is insufficient to promote it to a semantic distributed/mobile-work rule.

## 2026-09-29 — Started 03b.1 observation-support-controlled audit

03b finished with a robust 23-user cohort but materially imbalanced observation support between matched A/B groups. A narrow follow-up, 03b.1, is now implemented on branch `eda/03b1-support-controlled-audit`.

The experiment equalizes usable observation exposure within each matched pair before recomputing mobility and route metrics. Weekday/weekend day counts are controlled separately; route evidence uses independently controlled `usable_for_motif` days; transportation-label comparisons additionally control matched labeled hours where both sides have enough label coverage.

This phase is explicitly a confounding audit, not a semantic classifier. Construction-overlapping mobility metrics remain descriptive; recurrent route structure is the main independent evidence stream. No 03b.1 result is accepted until the Modal full-release run and verification gates pass.

## 2026-09-29 — Fixed 03b.1 weekday merge collision

The first 03b.1 Modal run passed preflight and reproduced the frozen setup, then stopped in `_day_edge_table()` with `KeyError: local_weekday` before generating evidence.

Cause: the clustered stay table already contained `local_weekday`, while the usable-day eligibility table also carried `local_weekday`. Merging on `user_id + local_date` caused pandas to suffix the duplicate columns (`local_weekday_x` / `local_weekday_y`), while downstream code still requested the unsuffixed name.

Fix:

- use the daily table only as an eligibility gate with `user_id + local_date`;
- derive weekday deterministically from `local_date` inside the route-day table;
- add a regression test where both inputs contain `local_weekday`.

No 03b.1 evidence was accepted from the failed run. Missing report/summary errors later in the notebook were downstream consequences of the route-table failure.

## 2026-09-29 — Optimized 03b.1 bootstrap runtime

A 500-repetition 03b.1 Modal run spent more than an hour inside the audit process without progress output. Inspection showed two avoidable hot loops:

- day bootstrap repeatedly filtered the full `daily` / `edge_days` tables for every pair and repetition;
- transport bootstrap rebuilt pandas DataFrames, recomputed datetimes, permuted rows, and iterated with `iloc` for every pair and repetition.

The audit now:

- prefilters each matched A/B pair once before its bootstrap loop;
- samples only pair-local weekday/weekend frames;
- precomputes compact NumPy transport arrays once per user;
- performs duration-controlled transport sampling with vectorized cumulative sums rather than per-row DataFrame construction;
- prints stage and pair-level progress.

The scientific design and default 500 bootstrap repetitions are unchanged. The interrupted long-running attempt produced no accepted 03b.1 evidence.

## 2026-09-29 — 03b.1 support-controlled audit completed

The optimized 03b.1 Modal run completed successfully and passed all verification gates.

Key findings after pairwise exposure control:

- 23/23 temporal pairs retained; median controlled temporal exposure 45 days;
- 22 route pairs retained; median controlled motif exposure 8 days;
- Group A still shows materially higher movement magnitude (+22.88 km/day cleaned distance; +0.74 h/day movement proxy), so richer observation alone does not explain the descriptive high-mobility pattern;
- route evidence is mixed: edge entropy remains higher (+0.232; 95% interval 0.006–0.455), while recurrent-edge difference is 0 and transition/distinct-edge intervals touch zero;
- only 1 matched pair has enough transport-label exposure, so mode evidence cannot support a cohort-level conclusion.

Research decision: freeze the 23-user set as a robust descriptive mobility-complexity cohort, not a validated mobile-work class. No production Home/Office change is justified. The current mobile-work hypothesis audit is closed pending independent semantic evidence.

## 2026-09-29 — Added consolidated behavior EDA mentor demo notebook

Added `notebooks/03c_behavior_eda_mentor_demo.ipynb` as the mentor-facing narrative notebook for the new behavior EDA.

The notebook reuses the existing Modal Volume caches from 03a, 03b, and 03b.1 rather than rerunning raw GeoLife. It walks through:

- frozen CP1/CP2 baseline and why upstream behavior remains frozen;
- 03a coverage, anchor heterogeneity, schedule/JSD negative result, and the 23-user exploratory cohort;
- 03b sensitivity, matched-control imbalance, route and transport evidence;
- 03b.1 pairwise exposure control with mobility and route bootstrap intervals;
- final research/production decision;
- mentor-ready talking points;
- the separate DBSCAN MinPts follow-up.

The notebook intentionally shows aggregate outputs only and does not expose private case-level identifiers, coordinates, or trajectories.

## 2026-09-29 — Expanded 03c mentor demo with user-level maps

Upgraded `notebooks/03c_behavior_eda_mentor_demo.ipynb` from an aggregate-only narrative to a more visual internal mentor demo.

The notebook now reuses frozen caches to show:

- deterministic representative users for dominant-anchor, two-anchor, and multiple-anchor classes;
- raw GeoLife user IDs and interactive Folium maps of cached CP1 stays, recurring L* locations, and chronological stay paths;
- a deterministic representative Group A candidate (edge entropy nearest the Group A median) and its actual matched Group B control;
- user-level daily cleaned-distance, movement-proxy, and boundary timelines for that A/B pair;
- within-day L* transition heatmaps for the same pair;
- existing aggregate sensitivity and 03b.1 exposure-controlled confidence-interval charts.

This is an internal side-project demo over public GeoLife data, so raw dataset IDs/coordinates are shown intentionally. The notebook still separates illustrative case diagnostics from population evidence and does not infer occupation or Home/Office ground truth from individual maps.

## 2026-09-29 — Fixed 03c mentor-demo cache bootstrap

The visual mentor-demo notebook initially assumed that the full 03a `summary.json` and `user_behavior_features.csv` had already been persisted under `/mnt/geolife-data/cache/03a_user_behavior_deep_dive`. That assumption was false on the current Modal Volume: 03b/03b.1 had reused the frozen stay/point-day caches without necessarily persisting the complete 03a derived artifact bundle.

The corrected mentor-demo notebook now uses a self-healing cache path:

- load full 03a derived artifacts when present;
- discover legacy 03a artifact locations when available;
- otherwise rebuild only derived 03a EDA from `stays_baseline_v1.pkl` + `cleaned_point_daily_metrics.pkl`;
- read the release-user listing from the GeoLife ZIP only for the 182-user reconciliation;
- never rescan raw `.plt` trajectory files during this fallback;
- persist rebuilt `summary.json`, `user_behavior_features.csv`, and `baseline_user_audit.csv` back to the canonical 03a Volume cache for later demos.

The visual layer still uses real public GeoLife user IDs, recurring-location maps, matched A/B examples, daily mobility timelines, and L* transition heatmaps for internal mentor review.

## 2026-09-29 — Fixed 03c fresh-runtime package import

A fresh Modal runtime failed before the 03c demo cache fallback could run with `ModuleNotFoundError: geolife`. The notebook cloned the repository but imported `analysis/03a_user_behavior_deep_dive.py` before installing the project package or adding `src/` to Python's import path.

The mentor-demo runner is corrected to follow the same setup contract as the audit runners: checkout the branch, run `pip install -e .[dev] timezonefinder==9.0.0`, add both the repository root and `src/` to `sys.path`, and only then import 03a analysis helpers. This is a runtime/setup bug only; no EDA evidence or frozen result changes.



## 2026-10-01 — Clustering robustness follow-up completed

Executed notebook 04 re-audited the frozen 97-user Home/Office semantic cohort with DBSCAN `eps = 20/50/100/200 m` × `min_samples = 1/2/3/5`, using frozen complete-link 200 m as the engineering comparator.

Measured complete-link 200 m reference:

- 1,111 locations;
- 486 recurring locations;
- 73 users with at least one recurring location;
- p95 recurring-cluster diameter 180.95 m;
- maximum recurring-cluster diameter 199.23 m;
- 0 recurring clusters above 200 m.

At DBSCAN `eps=200 m`:

- `min_samples=1`: 73 recurring users, 418 recurring locations, 585 singleton locations, 0 noise stays, max recurring diameter 836.66 m, 68 recurring clusters above 200 m;
- `min_samples=2`: the same 73 recurring users and 418 recurring locations, but the 585 singleton stays become noise; max diameter and 68 >200 m clusters are unchanged;
- `min_samples=3`: recurring-user coverage falls to 64 while max diameter remains 836.66 m;
- `min_samples=5`: recurring-user coverage falls to 56 while max diameter remains 836.66 m.

Decision: increasing DBSCAN MinPts does not resolve the chaining problem. `min_samples=2` mostly reclassifies singleton locations as noise, while higher values lose recurring-location support without controlling the widest clusters. Keep frozen complete-link 200 m for semantic work.

Scope caveat: notebook 04 is a follow-up on the 97-user Home/Office semantic cohort. It does not replace the separate full-stay DBSCAN audit or revalidate the 136-user behavior-EDA anchor counts.

Next research step: POI / land-use enrichment as auxiliary semantic evidence for frozen behavioral HOME/OFFICE labels; no production label change is implied.


## 2026-10-01 — Stage 05 pivoted from historical POI to behavioral reliability

The historical-OSM path was completed before this pivot. All 42 emitted-anchor historical requests completed, but the primary 150 m audit remained dominated by missing historical map context: 22/27 HOME and 14/16 OFFICE labels were unknown. Historical OSM therefore remains a documented negative result rather than a semantic ground-truth source.

Stage 05 now evaluates Home/Office inference without external semantic ground truth.

Frozen foundations remain unchanged:

- CP1 cleaning/stay semantics;
- complete-link 200 m spatial representation;
- Beijing-focused semantic geography/timezone policy;
- production baseline as a parity comparator only (27 HOME / 16 OFFICE).

New analysis scaffold:

- analysis/05_home_office_reliability.py;
- notebooks/05_home_office_reliability_validation.ipynb;
- docs/eda/18_home_office_reliability_validation.md;
- docs/05_home_office_reliability_handoff.md.

The new audit compares three independent-ish candidate rankers:

- current fixed-window semantics before final emission gates;
- a lightweight HoWDe-inspired observed-hour proportional ranker;
- a schedule-light recurrence comparator.

Validation axes are:

- candidate coverage;
- cross-method agreement;
- first/second-half and odd/even-week test-retest reliability;
- 60/40 held-out predictive persistence;
- 10/20/30% stay-dropout robustness;
- +12 h schedule-sensitivity stress.

This stage explicitly does not report accuracy because GeoLife has no HOME/OFFICE ground truth. The immediate next step is to run the scaffold on Modal, preserve user-level details privately, and interpret only aggregate reliability tables before changing production inference.


## 2026-10-01 — Stage 05 Home/Office reliability results

The new reliability audit ran successfully on the frozen semantic representation:

- 5,821 CP1 stays from 136 stay-bearing users;
- 97 users in the frozen Beijing semantic cohort;
- 1,111 semantic locations;
- 486 recurring locations across 73 recurring-anchor users;
- production parity reproduced exactly: 27 HOME and 16 OFFICE emissions.

Candidate coverage before treating any method as truth:

- fixed-window ranker: 35 HOME candidates / 27 OFFICE candidates;
- HoWDe-style proportional ranker: 20 HOME / 21 OFFICE;
- schedule-light recurrence ranker: 73 HOME / 31 OFFICE.

The 27/16 production counts are therefore confirmed to be conservative emission-policy outputs rather than the ceiling of recurring-anchor evidence.

Cross-method agreement is much stronger for HOME than OFFICE:

- HOME same-location agreement: fixed vs HoWDe-style 94.7% (18/19), fixed vs recurrence 82.9% (29/35), HoWDe-style vs recurrence 85.0% (17/20);
- OFFICE: fixed vs HoWDe-style 81.3% (13/16), but fixed vs recurrence only 31.8% (7/22) and HoWDe-style vs recurrence 15.0% (3/20).

Reliability/persistence evidence:

- fixed HOME split agreement: 76.5% first-vs-second half and 80.0% odd-vs-even weeks;
- fixed OFFICE: 55.6% first-vs-second and 88.9% odd-vs-even, but only 9 users contributed to each overlap;
- held-out top-1 persistence: HOME 55.6% fixed, 60.0% HoWDe-style, 43.3% recurrence; OFFICE 44.4%, 36.4%, and 37.5% respectively;
- at 30% random stay dropout, candidate retention remained 84.8%/76.5% for fixed HOME/OFFICE, 68.3%/54.0% for HoWDe-style, and 87.2%/64.5% for recurrence HOME/OFFICE;
- under a +12 h clock shift, recurrence HOME remained 100% stable and recurrence OFFICE 77.4%, while fixed-window and HoWDe-style labels changed substantially as expected from their clock-dependent design.

Decision:

- HOME has meaningful convergent behavioral evidence beyond the 27 emitted baseline cases, but expansion is not yet frozen because user-level consensus/support tiers have not been summarized;
- OFFICE remains substantially more method-dependent and should not be broadened from recurrence alone;
- the next semantic follow-up should quantify consensus tiers and use sliding-window/adaptive behavior for unstable users rather than tuning another single global clock threshold;
- no reported metric is semantic accuracy because GeoLife still lacks HOME/OFFICE ground truth.

## 2026-10-01 — Stage 05b scaffolded: HOME consensus tiers + adaptive secondary-anchor audit

Stage 05 showed strong HOME convergence but method-dependent OFFICE behavior. Stage 05b now separates those two follow-ups instead of tuning another global office window.

Added:

- `analysis/05b_home_consensus_adaptive_work.py`;
- `notebooks/05b_home_consensus_adaptive_work.ipynb`;
- `docs/eda/19_home_consensus_adaptive_work.md`;
- `docs/05b_home_consensus_adaptive_work_handoff.md`.

HOME candidate tiers reuse the private Stage-05 assignment/split/holdout/dropout tables.

Tier logic is transparent and non-probabilistic:

- HIGH = unique vote winner, >=2 methods agree, and split + held-out top-1 + 30% dropout axes all have confirming evidence;
- MEDIUM = unique vote winner, >=2 methods agree, and at least 2/3 reliability axes confirm;
- UNCERTAIN = otherwise.

The adaptive secondary-anchor audit runs only for HIGH/MEDIUM HOME users. It excludes HOME and tracks recurring non-HOME anchors in overlapping windows without using a fixed 09–17 selection window. Primary audit uses 42-day windows with 14-day steps, plus 28/42/56-day and 0.60/0.70/0.80 persistence sensitivity.

A synthetic execution test initially exposed a timezone bug: production semantic timestamps are timezone-aware while the first sliding-window implementation created timezone-naive boundaries. The code now derives normalized window boundaries directly from timezone-aware semantic timestamps. Synthetic HOME tiering and a two-secondary-anchor switching case both pass.

No production HOME/OFFICE rule changed. Stage 05b remains an audit layer until measured outputs are reviewed.

## 2026-10-01 — Stage 05b HOME consensus + adaptive secondary-anchor audit completed

Stage 05b reused the private Stage-05 reliability details and measured candidate-level HOME consensus plus sliding-window secondary-anchor persistence.

HOME consensus winners:

- 67 users had a unique method-vote winner;
- 21 HIGH, 4 MEDIUM, 42 UNCERTAIN;
- among HIGH/MEDIUM winners, 23 were already production HOME emissions;
- only 2 additional HIGH/MEDIUM users were outside baseline emission, and both were already fixed-window HOME candidates that had failed the final production emission gate;
- there were no HIGH/MEDIUM winners from the broad outside-fixed-candidate set.

This means the earlier 73-user recurrence HOME coverage does not translate into a large reliable expansion. The frozen 27-HOME baseline already captures most of the strongest multi-axis HOME evidence. Of the 27 production HOME emissions, 23 appear as HIGH/MEDIUM unique consensus winners; the remaining emissions should be interpreted as weaker/more method-dependent evidence, not as demonstrated errors.

Adaptive secondary-anchor audit among the 25 HIGH/MEDIUM HOME users:

Primary 42-day windows, 14-day step, 0.70 dominant-window-share threshold:

- 9 stable secondary-anchor users;
- 3 multi-anchor users;
- 1 unstable user;
- 12 insufficient-support users.

Among the 13 users with sufficient 42-day evidence, the dominant adaptive secondary anchor matched:

- fixed-window OFFICE in 4/10 comparable users (40.0%);
- HoWDe-style OFFICE in 2/7 (28.6%);
- recurrence OFFICE in 6/11 (54.5%).

Window sensitivity at the 0.70 threshold:

- 28 days: 10 sufficient users, 6 stable;
- 42 days: 13 sufficient, 9 stable;
- 56 days: 14 sufficient, 10 stable.

At 42/56 days, stable-secondary counts remain similar across 0.70/0.80 thresholds (9/9 and 10/10 respectively). The main limitation is observation support, not a collapse of persistence under a slightly stricter threshold.

Decision:

- do not broaden HOME production inference wholesale;
- retain the two non-emitted HIGH/MEDIUM HOME cases as targeted review candidates only;
- do not promote stable secondary anchors to OFFICE: static-method agreement remains low and about half of eligible HOME-consensus users are still insufficient at the primary 42-day setting;
- Stage 05b closes the broad expansion question. Any further WORK step should test independent temporal/transition evidence for the small stable-secondary subset rather than tune another global threshold.


## 2026-10-01 — Stage 05c stable-secondary independent-evidence audit scaffolded

Stage 05b left only nine users with a stable secondary anchor under the primary 42-day audit, while static OFFICE agreement remained weak. Stage 05c narrows the question further instead of tuning another global OFFICE threshold.

For each stable-secondary user, the persistent non-HOME anchor is compared with recurring non-HOME peers from the same user on four axes not used as the primary Stage-05b selection rule:

- weekday-versus-weekend visit contrast;
- direct HOME ↔ secondary transition-day share;
- arrival-time concentration;
- dwell-duration regularity.

The primary design is within-user rather than population-threshold based. A candidate must have at least one eligible peer anchor before top-rank evidence is computed, preventing vacuous top-1 results.

The audit also includes paired bootstrap differences versus each user's peer median, peer-support sensitivity at 2/3/5 active days, and descriptive stratification by static OFFICE agreement.

No production HOME/OFFICE change is implied. The notebook is self-contained and reuses private Stage-05b caches.

## 2026-10-01 — Stage 05c independent-evidence audit completed

Stage 05c evaluated the nine Stage-05b stable secondary anchors against same-user recurring non-HOME peers on four evidence axes that were not used as the primary sliding-window persistence rule.

Primary comparator support (>=3 active days, >=2 stays):

- 9 stable-secondary users upstream;
- 7 had at least one fair recurring non-HOME peer;
- median peer-anchor count = 4.

Axis-level result among the seven comparable users:

- weekday-weekend visit contrast: 5/7 candidate anchors ranked top-1; median candidate-minus-peer-median = +0.198;
- direct HOME<->secondary transition-day share: 3/7 top-1; median difference = +0.102;
- arrival-hour concentration: 0/7 top-1; median difference = -0.181;
- dwell-duration regularity: 0/7 top-1; median difference = -0.092.

Multi-axis convergence:

- 0/7 users ranked top-1 on >=3 of 4 axes;
- 1/7 ranked top-1 on exactly 2 axes;
- 6/7 ranked top-1 on only 0-1 axes;
- 3/7 beat the peer median on >=3 axes, but this weaker criterion did not translate into top-rank convergence.

Paired bootstrap intervals for candidate-minus-peer-median differences all crossed zero. The strongest directional signals were weekday contrast and HOME-pair transition share, but small-N uncertainty remained substantial.

Peer-support sensitivity:

- min 2 active days: 9 comparable users, 0 with >=3 top axes;
- min 3 active days: 7 users, 0 with >=3 top axes;
- min 5 active days: sample collapsed to 3 users; 1 reached >=3 top axes.

Decision: close broad semantic WORK/OFFICE expansion. Stable secondary anchors remain a useful behavioral state, but current evidence does not support relabeling them as workplace. Production HOME/OFFICE remains unchanged.

Related-work direction after 05c:

- keep the frozen CP1 stay detector and complete-link 200 m representation; do not replace the current audited backbone with Trackintel mid-project;
- use Trackintel only as an external reference/benchmark and source of tracking-quality ideas if a new behavior-change track needs them;
- adopt the report's coverage-before-change-detection principle;
- prefer Andrade-style routine/habit mining and downstream change detection as the next research direction because they do not require WORK semantics;
- treat HoWDe as a comparator/lesson source rather than a reason to continue tuning WORK labels;
- use Dong-style commute/OD features as sanity/interpretability signals, not as a GeoLife population-law claim.


## 2026-10-01 — Stage 06 routine / habit mining scaffolded

Stage 06 starts the post-semantic behavior track.

Scope:

- frozen CP1 stays and Stage-03a daily support caches;
- broader all-resolved behavior cohort rather than the 97-user Beijing semantic cohort;
- per-stay local-time resolution;
- complete-link 200 m behavior locations;
- parity target: 104 users with at least one recurring location.

The notebook mines supported daily location sequences and directed OD transitions without assigning HOME/WORK meaning.

Primary evidence axes remain separate:

- edge recurrence across supported days;
- circular departure-time concentration;
- 1–3 departure-time modes selected by BIC when an edge has enough transitions;
- exact full-day motif repeatability as a stricter comparator;
- first-half vs second-half dominant-edge stability;
- recurrence/concentration threshold sensitivity.

Important design constraint: observation support is applied before routine construction. Unsupported days are not treated as evidence that a routine did not happen.

Stage 06 is preparatory for Stage 07 behavioral change detection. No production inference changes are proposed.

## 2026-10-01 — Stage 06 Modal runtime dependency fix

The first Modal execution of Stage 06 failed before routine mining because the runtime already had the local `geolife` source importable but did not have `timezonefinder==9.0.0` installed.

Root cause: the notebook only installed the project when `geolife` import failed, so an already-importable source tree caused the dependency install path to be skipped.

Fix:

- Stage 06 now checks `importlib.util.find_spec('timezonefinder')` explicitly;
- when missing, the notebook installs `timezonefinder==9.0.0` before importing the Stage-03a behavior helper;
- when already available, pip is skipped.

This is a notebook-runtime fix only. CP1 stays, complete-link behavior locations, routine definitions and all Stage-06 research thresholds remain unchanged.


## 2026-10-01 — Stage 06b routine representation robustness scaffolded

The executed Stage 06 run showed that routine mining has useful signal but is not yet ready for direct change detection:

- repeated OD coverage: 23 users at >=2 active days, 9 at >=3 days, 2 at >=5 days;
- exact dominant-edge split-half stability: 6/45 users kept the same top edge;
- the permissive Stage-06 GMM modeled only 11 edges from 2 users, with 8/11 selecting three time modes;
- the Stage-06 collapsed-sequence motif comparator could mark a one-day user as 100% repeatable.

Stage 06b therefore adds:

- a support-aware motif comparator on a shared >=6-usable-day user universe;
- routine support tiers at >=2 / >=3 / >=5 active days;
- split-half OD-distribution metrics (JSD, weighted Jaccard, total variation, top-3 overlap);
- 200 random balanced day partitions per comparable user to calibrate chronological JSD against sampling-only variability;
- day-level bootstrap intervals for departure-time concentration;
- stricter multimodal GMM checks using support, BIC gain, component weights, and circular time separation.

The central pre-Stage-07 question is now whether chronological distribution change exceeds random-partition variability after coverage is controlled. No HOME/OFFICE or production inference changes are introduced.

## 2026-10-01 — Stage 06b measured result: exact-OD instability is mostly sampling-driven

Stage 06b completed successfully and preserved Stage-06 parity:

- 107 supported users;
- 984 supported days;
- 1,086 directed transitions;
- 869 distinct user-edge rows.

Support-aware routine comparison on the primary >=6-usable-day universe:

- 51 eligible users;
- 8 users had a directed OD repeated on >=3 active days;
- 9 users had a collapsed-sequence motif repeated on >=3 days and >=50% of usable days;
- the current comparator reported zero overlap between those groups.

The zero-overlap result requires caution: the collapsed-sequence motif comparator currently permits single-location motifs with no transition. It therefore mixes stationary repeated-day patterns with mobile OD routines and should not be interpreted as evidence that OD and motif representations identify disjoint mobility populations.

Routine support tiers:

- candidate >=2 active days: 66 edges / 23 users (22 with >=6 usable days);
- supported >=3 active days: 25 edges / 9 users (8 with >=6 usable days);
- strong >=5 active days: 12 edges / 2 users.

Chronological split-half distribution result:

- 51 users passed support eligibility;
- 45 had comparable edge distributions in both halves;
- exact same top edge: 13.3%;
- median JSD = 1.0;
- median weighted Jaccard = 0.0;
- median total variation = 1.0;
- median top-3 Jaccard = 0.0.

However, the within-user random balanced-partition null is equally sparse:

- median chronological JSD = 1.0;
- median random-partition JSD = 1.0;
- median chronological-minus-random-median JSD = 0.0;
- only 2/45 users (4.4%) had chronological JSD above their random-partition p95.

Interpretation: the very high split-half instability is not evidence of broad temporal behavior change. For most users, exact-OD distributions are so sparse that random balanced partitions are just as disjoint as chronological halves.

Departure-time bootstrap is stronger but concentrated in a tiny subset:

- supported tier (3-4 active days): 13 edges / 8 users, median concentration 0.888, median CI lower bound 0.823;
- strong tier (>=5 active days): 12 edges / 2 users, median concentration 0.964, median CI lower bound 0.944;
- 9/12 strong edges retained CI lower bound >=0.7.

Strict multimodality also remains narrow:

- 6 edges from 1 user met the primary strict modeling gate;
- only 1 edge was strict multimodal;
- sensitivity across relaxed settings still involved at most 2 users.

Decision: do not proceed to broad Stage-07 change detection on exact OD identity. The next step, if pursued, should first test whether a coarser/support-normalized representation yields interpretable temporal continuity and enough eligible windows. Exact OD identity is currently sampling-limited.

## 2026-10-01 — Measured Stage 06c change-detection representation feasibility

The Stage-06c Modal run completed on the private Stage-06 / Stage-03a caches with no raw GeoLife rescan.

Coverage by non-overlapping calendar window:

- 28d: 43 eligible windows, 24 users with at least one eligible window, 11 users with an adjacent eligible pair, 16 adjacent pairs; median 8 usable days/window;
- 42d: 48 eligible windows, 31 users with at least one eligible window, 9 users with an adjacent eligible pair, 15 adjacent pairs; median 8 usable days/window;
- 56d: 48 eligible windows, 35 users with at least one eligible window, 7 users with an adjacent eligible pair, 11 adjacent pairs; median 9 usable days/window.

Increasing the calendar span from 28 to 56 days therefore does not materially increase usable observations, while the number of adjacent comparable users falls.

Exact-OD identity remains unsuitable as a change-detection backbone:

- median chronological JSD: 0.942 / 1.000 / 1.000 for 28d / 42d / 56d;
- median random-partition JSD: 0.876 / 0.857 / 0.894;
- chronological JSD above random p95: 0.0% / 0.0% / 9.1%.

Promising coarse features exist. In particular:

- 42d cleaned distance per usable day: Spearman 0.729, random-p95 exceedance 6.7%, bootstrap-width / observed-IQR 0.814;
- 42d active-location count per usable day: Spearman 0.540, random-p95 exceedance 0%, bootstrap-width / observed-IQR 0.866.

A 28d 00–06 departure share also passes the non-coverage gates, but its zero median difference / zero bootstrap-width pattern makes it a likely sparse or degenerate feature rather than a strong behavioral axis.

All 45 feature × window combinations fail the provisional Stage-07 readiness gate because every window size has fewer than the predeclared 20 comparable adjacent pairs. The gate is not lowered post hoc.

Decision:

- do not implement Stage 07 yet;
- keep 42d movement magnitude and active-location density as promising features;
- stop extending fixed calendar windows because 28→56d adds little usable support;
- next evaluate support-indexed windows (6 / 8 / 10 usable days) with calendar-span caps (56 / 84 days sensitivity), using the same coverage, test–retest, random-null and bootstrap protocol.

## 2026-10-02 — Stage 06d support-indexed window feasibility scaffolded

Measured Stage 06c showed that 28 / 42 / 56-day fixed calendar windows contained only median 8 / 8 / 9 usable days while adjacent comparable users fell as the span increased.

Stage 06d therefore changes only the support unit:

- chronological non-overlapping blocks of 6 / 8 / 10 usable days;
- 56 / 84-day maximum calendar-span sensitivity;
- no bridging across span-rejected blocks;
- same Stage-06c coarse feature family, random balanced-partition null, and day bootstrap;
- predeclared readiness still requires >=20 comparable adjacent pairs, Spearman >=0.50, random-p95 exceedance <=10%, and bootstrap-width / observed-IQR <=1.0;
- adds >=10 unique users so many pairs from a few long-history users cannot masquerade as population coverage.

Primary features are frozen from measured 06c before this run: cleaned distance / usable day and active-location count / usable day.

Stop rule: proceed to Stage 07 only if at least one primary feature passes every gate. If all 6 support/cap configurations fail, close broad within-user change detection on GeoLife as longitudinal-data-limited rather than continue tuning windows.

## 2026-10-02 — Measured Stage 06d support-indexed feasibility closes broad Stage 07

The Stage-06d Modal run completed on the frozen Stage-06 / Stage-03a private caches.

Support-indexed windows solved the Stage-06c coverage bottleneck for smaller block sizes:

- 6 usable days, 56-day cap: 49 adjacent pairs / 18 users;
- 6 usable days, 84-day cap: 58 pairs / 21 users;
- 8 usable days, 56-day cap: 26 pairs / 11 users;
- 8 usable days, 84-day cap: 29 pairs / 11 users;
- 10 usable days, 56-day cap: 15 pairs / 8 users;
- 10 usable days, 84-day cap: 18 pairs / 8 users.

Thus 6-day and 8-day support windows exceed the predeclared >=20-pair and >=10-user coverage gates. The failure is no longer explainable only by insufficient pair count.

Exact OD remains sampling-dominated. Median chronological JSD is 0.724–1.000 across the six settings, while median random-partition JSD is 0.728–0.899. Chronological JSD exceeds the random p95 in only 0–6.7% of pairs.

Primary-feature result:

- active-location count / usable day fails rank stability in every configuration (Spearman from -0.026 to 0.434);
- cleaned distance / usable day has useful rank stability for 6-day and 8-day blocks (Spearman ~0.697–0.737) but misses another predeclared gate in every covered configuration:
  - 6d / 56d: bootstrap-width / observed-IQR = 1.030 (>1.0);
  - 6d / 84d: chronological > random p95 = 10.34% (>10%);
  - 8d / 56d: chronological > random p95 = 11.54%;
  - 8d / 84d: chronological > random p95 = 10.34%.

The 10-day settings also fail population coverage.

Most importantly, the final decision table reports zero passing features of any kind in all six configurations and zero passing primary features. stage07_ready is false everywhere.

Decision: stop broad within-user behavioral change detection on GeoLife. The project has evidence for routines and some stable coarse mobility features, but not enough jointly stable, null-calibrated, low-uncertainty longitudinal signal to justify a general Stage-07 detector under the predeclared protocol. Do not add more support sizes or relax gates post hoc.
## 2026-10-02 — Stage 07 reframed around work-regime representations

After Stage 06d closed broad within-user change detection, the project returns to the mentor's work/job hint without attempting unsupported occupation inference.

Stage 07 composes already-audited evidence into descriptive work-regime hypotheses:

- shifted_fixed_site_like;
- fixed_site_like;
- route_centric_mobile_like;
- multi_site_recurring;
- irregular;
- insufficient.

The new output is not a job title. It recommends how WORK should be represented for that mobility history:

- single recurring anchor;
- schedule-agnostic single anchor;
- recurring anchor set;
- route/activity region;
- abstain.

The taxonomy reuses Stage-03a anchor/mobility states, Stage-05b adaptive secondary-anchor patterns, optional Stage-05c independent evidence, and Stage-06 route recurrence. No raw GeoLife rescan is required.

Semantic boundary: fixed_site_like is not OFFICE, route_centric_mobile_like is not a driver/sales/courier label, and multi_site_recurring is not proof of multiple offices.

If the measured taxonomy has useful coverage and coherent evidence composition, the next independent axis is external coarse POI / land-use context.

## 2026-10-02 — Measured Stage 07 v1 reveals non-orthogonal work-regime evidence

The Stage-07 work-regime notebook executed successfully over 182 behavior users.

Distribution:

- 110 insufficient;
- 48 irregular;
- 9 multi-site recurring;
- 8 route-centric/mobile-like;
- 7 fixed-site-like;
- 0 shifted fixed-site-like.

Only 24 / 182 users (13.2%) receive a non-abstaining WORK representation; 158 / 182 (86.8%) remain abstaining or insufficient.

The integration produced useful route-complexity separation: route-centric users have repeated-route evidence for 8/8 and median 24.5 distinct edges, while multi-site users have repeated-route evidence for 9/9 and median 11 distinct edges.

But the categorical taxonomy is not cleanly separable:

- 7/7 fixed-site-like users are also multi-anchor-state users;
- 2/8 route-centric users also have stable-single-secondary evidence;
- shifted-schedule evidence appears inside route/multi-site groups instead of forming a separate class.

Decision: do not freeze or semantically interpret the v1 mutually-exclusive archetypes. The mentor/job direction remains viable, but it should be expressed as a factorized occupational-mobility profile rather than one class.

Next stage: 07b factorization of site structure, route structure, timing regime, mobility complexity, HOME support and independent secondary-anchor evidence. External POI / land-use context comes after that as an independent semantic layer.
## 2026-10-02 — Stage 07b factorized work-regime profiles scaffolded

Measured Stage 07 v1 showed that stable-secondary, multi-anchor, repeated-route, shifted-schedule and mobile-complexity evidence overlap within the same users.

Stage 07b therefore removes the mutually-exclusive work_regime label and keeps separate axes for:

- site / anchor structure;
- route / OD structure;
- schedule timing;
- mobility complexity;
- HOME context;
- independent Stage-05c evidence.

Representation output is now multi-label rather than categorical:

- candidate_single_anchor_geometry;
- candidate_anchor_set_geometry;
- candidate_route_region_geometry;
- schedule_agnostic_needed.

A user may legitimately receive multiple representation options simultaneously.

Aggregate review focuses on upstream support coverage, axis prevalence, pairwise overlap, common evidence signatures and representation signatures.

No occupation, employment-status, true WORK, OFFICE, or POI semantic claim is created. External POI / land-use enrichment remains a later independent semantic layer.

## 2026-10-02 — Measured Stage 07b validates factorized work profiles

Stage 07b executed successfully on the frozen Stage-03a / 05b / optional 05c / 06 artifacts.

The result confirms that the Stage-07 v1 conflicts were genuine overlaps:

- 9/9 stable-secondary users are also multiple-recurring users;
- 7/9 stable-secondary users have repeated-route evidence;
- 22/23 repeated-route users are multiple-recurring;
- 23/23 mobile-complexity users are multiple-recurring;
- both shifted-schedule users also have repeated-route evidence.

Representation output is correspondingly multi-label:

- 110 abstain;
- 48 anchor-set only;
- 13 anchor-set + route-region;
- 7 single-anchor + anchor-set + route-region;
- 2 single-anchor + anchor-set;
- 2 anchor-set + route-region + schedule-agnostic.

No stable-secondary user is truly single-anchor-only under the broader recurring-location representation.

Decision: accept factorization as the mobility-side representation and stop trying to create one work-regime class.

Next semantic step should be external POI / land-use enrichment, but only on a support-qualified subset. Start with the 25 HIGH/MEDIUM HOME-supported users and candidate non-HOME recurring anchors so HOME exclusion is explicit. Keep the external context separate from the Stage-07b profile.
## 2026-10-02 — Stage 07c reframed as historical-source audit + temporal alignment

Current-OSM PR #19 was closed without merge because GeoLife observations are from 2007–2012 and current POI context would create temporal leakage if treated as historical semantic evidence.

New Stage 07c is gate-first. It does not fetch historical POI data. It:

- rebuilds the support-qualified recurring non-HOME anchor subset;
- computes first/median/last observation dates per anchor;
- assigns temporally appropriate source candidates;
- records exact vs proxy alignment and temporal offsets;
- blocks semantic sources whose provenance/access/license/CRS are unresolved.

Verified source roles:

- BCL POI 2008: scraped in 2008, mainland-China snapshot, names + coordinates, no category field; exact for 2008 and explicit ±1-year proxy only for 2007/2009; file license/CRS still gated;
- Gaode 2010: peer-reviewed paper reports self-built crawler and 1,610,384 2010 POIs, with Mars-coordinate to WGS84 conversion; reusable corpus access/license still gated;
- CLCD: annual 30 m historical land cover available for every GeoLife year 2007–2012; physical context only;
- Beijing planning permits / land transactions: historical administrative cross-checks, not proof of facility operation;
- BCL blocks 2011: morphology prior, not semantic ground truth;
- ohsome: exact OSM database snapshots from 2007-10-08 onward, used only as a cross-check because early mapping can be incomplete;
- Gaode 2011 / Baidu 2012: remain blocked until provenance/access/license/CRS are verified.

Stage 07d will be source-modular and must refuse blocked sources unless their gate metadata is explicitly updated with evidence.

## 2026-10-02 — Measured Stage 07c makes 2008–2009 the dominant historical-context problem

Stage 07c ran successfully after fixing the fresh-runtime src-layout setup.

The support-qualified universe contains 25 users and 225 recurring non-HOME anchors.

Median observation-year distribution:

- 2008: 72 anchors / 12 users;
- 2009: 136 anchors / 11 users;
- 2010: 1 anchor / 1 user;
- 2011: 10 anchors / 4 users;
- 2012: 6 anchors / 2 users.

Thus 208 / 225 anchors (92.4%) are concentrated in 2008–2009.

This materially changes external-source priority:

- CLCD can provide exact-year physical context for all 225 anchors;
- ohsome can provide historical OSM cross-checks for all 225 measured anchors;
- BCL POI 2008 is the highest-leverage semantic source candidate, relevant to 208 anchors / 19 users;
- Gaode 2010 would affect only 1 anchor / 1 user;
- 2011 and 2012 candidates affect only 16 anchors total.

Decision: Stage 07d MVP should implement CLCD + ohsome first, while BCL POI 2008 access/license/CRS is resolved. Do not prioritize Gaode/Baidu ingestion yet.
## 2026-10-02 — Stage 07d historical-context enrichment scaffolded

Measured Stage 07c showed 208 / 225 recurring non-HOME anchors (92.4%) are in 2008–2009.

Stage 07d therefore prioritizes runnable sources with population leverage:

- CLCD exact-year 30 m land cover as the primary physical-context source;
- historical OSM / ohsome as an optional cross-check at the anchor observation date;
- BCL POI 2008 remains the highest-value blocked semantic source while access/license/CRS are unresolved.

CLCD runner behavior:

- pinned CLCD v1.0.2 Zenodo record;
- remote Cloud Optimized GeoTIFF sampling by observation year;
- point pixel plus 3×3 and 5×5 local modal classes;
- explicit point/window agreement audit;
- no conversion from impervious land cover to office/residential/WORK semantics.

ohsome runner behavior:

- v2 extraction API;
- exact anchor median observation date;
- optional `OHSOME_API_KEY`; CLCD analysis remains runnable without the key;
- semantic tags remain multi-label and cross-check-only;
- missing historical OSM is missing mapping evidence, not proof of real-world absence.

Exact coordinates and user-level context outputs remain private.

## 2026-10-02 — Stage 07d runtime contract fix: reconstruct anchor coordinates

The first measured 07d run exposed a contract mismatch:

- Stage 07c correctly produced 225 dated recurring non-HOME anchors but its private dated-anchor artifact did not retain latitude/longitude;
- Stage 07d initially assumed those coordinates were present, causing both CLCD sampling and ohsome request construction to fail.

Fix:

- Stage 07d now detects missing coordinates;
- reloads the frozen Stage-03a stay cache;
- resolves timezones and rebuilds the same deterministic 200 m location clustering;
- attaches per-location median latitude/longitude privately by user_id + location_id;
- validates that all 225 candidate anchors receive coordinates before any external query.

No aggregate result or Stage-07c source-priority conclusion changes.

## 2026-10-02 — Stage 07d free-tier ohsome rate-limit handling

Measured CLCD enrichment completed successfully, but the optional historical-OSM cross-check hit HTTP 429 Too Many Requests on the free-tier ohsome API key.

The previous runner treated this as a fatal remote exception, which also caused a downstream undefined-variable error.

Fix:

- remote Modal function returns structured status instead of serializing httpx exceptions;
- successful anchor responses are cached;
- default fresh-request budget = 20 per run;
- default inter-request pause = 6 s;
- first 429 stops further fresh API calls;
- remaining anchors are logged as deferred;
- partial OSM context and logs are saved;
- later reruns resume from cache.

CLCD measured output from the failed run remains valid:
- 224 / 225 anchors had a known point land-cover class;
- 216 / 225 (96.0%) were impervious;
- point vs 3x3 agreement = 223 / 225;
- point vs 5x5 agreement = 222 / 225.

## 2026-10-02 — Stage 07d measured result: CLCD complete, ohsome partial/resumable

The free-tier-safe Stage-07d notebook completed without errors.

Primary CLCD result on 225 anchors / 25 users:

- 224/225 known point classes;
- 216/225 impervious (96.0%);
- 223/225 point-vs-3x3 local-mode agreement;
- 222/225 point-vs-5x5 local-mode agreement.

By year:

- 2008: 70 impervious, 1 water, 1 unknown;
- 2009: 131 impervious, 4 forest, 1 cropland;
- 2010: 1 cropland;
- 2011: 10 impervious;
- 2012: 5 impervious, 1 water.

Interpretation is deliberately physical only: the recurring non-HOME anchor universe is overwhelmingly on historically built-up/impervious land, with very high local raster stability. No office/residential/WORK/occupation label follows from this.

ohsome free-tier cross-check:

- 35/225 anchors completed;
- 15 cached + 20 newly fetched;
- 0 rate-limit hits in the latest run;
- 190 deferred by request budget;
- 0 request errors;
- 0 parse errors;
- 11 completed anchors had semantic context;
- 10 had broad work-compatible context;
- 0 had residential context.

The 35 anchors come from only 3 users, so their semantic-context proportions are not population-representative and must not be generalized.

Decision: close Stage 07d on the complete CLCD primary result. Keep ohsome as resumable opportunistic cross-check. Next semantic-source priority is BCL POI 2008 because Stage 07c showed relevance to 208/225 anchors.

## 2026-10-02 — Stage 07d closed after full 225-anchor ohsome completion

The resumable free-tier strategy eventually completed historical OSM extraction for all 225 recurring non-HOME anchors across all 25 candidate users.

Final ohsome run state:

- 225/225 anchors completed;
- 25/25 users covered;
- 217 cached;
- 8 newly fetched;
- 0 rate-limit hits;
- 0 deferred;
- 0 request errors;
- 0 parse errors.

Full-universe historical OSM summary:

- semantic context found: 65/225 anchors (28.89%), 16 users;
- broad work-compatible context: 48/225 anchors (21.33%), 14 users;
- residential context: 8/225 anchors (3.56%), 2 users.

This supersedes the earlier partial 35-anchor result.

Combined with CLCD:

- 216/225 anchors (96.0%) are impervious;
- point-vs-3x3 agreement = 223/225;
- point-vs-5x5 agreement = 222/225.

Interpretation remains conservative: CLCD provides physical context; historical OSM provides mapping/context evidence. Neither proves WORK/OFFICE/HOME or occupation.

Decision: close Stage 07d. Next semantic-source priority is BCL POI 2008 access/license/CRS resolution because it is temporally relevant to 208/225 anchors.


## 2026-10-02 — Stage 07e offline semantic-distance alignment patch

A new branch, `eda/07e-semantic-distance-alignment`, starts the first full-cache semantic alignment audit after Stage 07d.

The patch is deliberately offline-only. It consumes the completed 225-anchor historical OSM cache and makes no ohsome requests.

Implemented scope:

- validate full one-to-one anchor/cache coverage;
- decode historical OSM WKB geometry and compute local metric anchor-to-feature distances;
- use bbox only as a geometry-decoding fallback;
- distinguish exact radial <=25 / <=50 / <=100 m evidence from the Stage-07d square extraction AOI;
- preserve Stage-07d multi-label semantic categories;
- identify the exact Stage-05b stable-secondary anchor by `dominant_location_id`;
- compare that candidate against other recurring non-HOME anchors from the same user;
- use 100 m censored distance for bounded within-user comparisons;
- bootstrap user-level candidate-minus-peer context differences;
- summarize mapped work-compatible context against Stage-07b factorized mobility axes.

No measured result is frozen yet. The next step is to run the 07e notebook on the existing Modal Volume and review aggregate outputs before any PR is opened.
\n

## 2026-10-02 — Stage 07e cache-validation contract fix

First Modal execution exposed a persistence mismatch: the raw ohsome cache had been resumed across runs, but the saved Stage-07d request-log pickle was from an earlier partial run. The original 07e gate incorrectly treated the log as coverage truth and reported 170 missing anchors.

Fix:

- recompute the exact Stage-07d request body for every anchor;
- derive the deterministic cache key directly;
- validate the raw Parquet file on disk;
- retain request-log status only as optional audit metadata;
- add regression coverage for complete raw cache + stale partial log.

This preserves the intended requirement: Stage 07e needs complete raw historical OSM cache, not a freshly persisted request log.

## 2026-10-02 — Location-namespace correctness issue invalidates prior 07c/07d/07e measured anchor interpretation

Stage 07e exposed that Stage 05b and Stage 07c were not using the same location-id namespace.

- Stage 05b used production `build_semantic_locations(... complete_link, 200m)`, whose location ids are assigned by first observation after the Beijing region policy.
- Stage 07c/07d used `cluster_behavior_locations(..., 200m)`, whose location ids are relabeled by dwell/support and are built from a different stay universe.

Therefore integer equality of `location_id` across these stages was not a valid join key.

Consequences:

- the old 225-anchor Stage-07c universe may have excluded the wrong location when removing HOME;
- the old Stage-07d CLCD / OSM summaries remain technically valid for those 225 coordinates, but those coordinates are not guaranteed to be the intended production-aligned recurring non-HOME universe;
- the first Stage-07e result (62 semantic <=100m, 46 work-compatible <=100m, 8/9 exact stable-secondary anchors) is superseded and must not be interpreted further.

Corrective patch:

- Stage 07c now rebuilds locations using production `build_semantic_locations` with complete-link 200 m;
- validates that all supported HOME ids and Stage-05b dominant secondary ids exist in that namespace;
- persists `location_namespace=production_complete_link_200m_beijing_policy_v1`;
- Stage 07d attaches coordinates from the production location table;
- Stage 07e rejects any artifact missing the expected namespace.

Required rerun order: corrected 07c -> corrected 07d (resume cache; fetch only missing request hashes) -> corrected 07e.

## 2026-10-02 — Corrected Stage 07c measured result

The production-location namespace rerun completed cleanly.

Namespace validation:

- location namespace: `production_complete_link_200m_beijing_policy_v1`;
- production semantic-location users: 97;
- production semantic locations: 1,111;
- supported HOME ids checked: 25;
- supported HOME ids missing: 0;
- Stage-05b dominant work ids checked: 15;
- Stage-05b dominant work ids missing: 0.

Corrected recurring non-HOME candidate universe:

- 25 users;
- 198 anchors.

Observation-year distribution:

- 2008: 65 anchors / 11 users;
- 2009: 120 anchors / 11 users;
- 2011: 7 anchors / 4 users;
- 2012: 6 anchors / 2 users;
- no corrected candidate anchor has median observation year 2010.

Corrected historical-source coverage:

- CLCD exact-year physical context: 198 anchors / 25 users;
- historical OSM cross-check: 198 anchors / 25 users;
- BCL POI 2008 exact/+1-year candidate: 185 anchors / 19 users;
- 2011 candidates: 7 anchors / 4 users;
- Baidu 2012 candidate: 6 anchors / 2 users.

This supersedes the old behavior-location universe of 225 anchors. The next required run is corrected Stage 07d on these 198 production-aligned anchors.

## 2026-10-03 — Corrected Stage 07d measured result

The production-aligned Stage-07d rerun completed cleanly on the corrected 198-anchor universe.

Universe:

- 198 recurring non-HOME anchors;
- 25 users;
- location namespace: `production_complete_link_200m_beijing_policy_v1`.

CLCD exact-year physical context:

- point class known: 198 / 198 (100%);
- impervious: 191 / 198 (96.46%);
- point = 3x3 local mode: 197 / 198 (99.49%);
- point = 5x5 local mode: 195 / 198 (98.48%).

Class/year counts:

- 2008: 63 impervious, 2 water;
- 2009: 116 impervious, 3 forest, 1 cropland;
- 2011: 7 impervious;
- 2012: 5 impervious, 1 water.

Historical OSM / ohsome:

- target: 198;
- completed: 198 / 198 (100%);
- cached: 189;
- newly fetched in final corrected run: 9;
- rate-limited: 0;
- deferred: 0;
- request errors: 0;
- parse errors: 0.

Full corrected-universe OSM context:

- semantic context found: 63 / 198 anchors (31.82%), 16 users;
- broad work-compatible context: 47 / 198 anchors (23.74%), 15 users;
- residential context: 6 / 198 anchors (3.03%), 2 users.

Interpretation remains source-bounded: CLCD is physical built/impervious context only, and historical OSM is mapping evidence rather than semantic ground truth.

The corrected 07d outputs supersede all old 225-anchor Stage-07d measurements.

Next required run: corrected Stage 07e on this completed 198-anchor cache.

## 2026-10-03 — Corrected Stage 07e completed: null/mixed independent semantic evidence

The corrected production-aligned Stage-07e notebook completed without errors.

Coverage:

- 198 / 198 raw historical-OSM caches validated;
- 25 users;
- 9 stable-secondary users represented;
- 9 exact stable-secondary anchors;
- 9 within-user comparison rows.

Exact radial historical-OSM context:

- semantic <=100 m: 61 / 198 anchors;
- broad work-compatible <=100 m: 46 / 198 anchors.

Work-compatible distance buckets:

- 0–25 m: 31 anchors / 9 users;
- 25–50 m: 5 anchors / 5 users;
- 50–100 m: 10 anchors / 7 users;
- none within 100 m: 152 anchors / 25 users.

Category <=100 m:

- education 33;
- recreation/tourism 14;
- retail/service 14;
- residential 6;
- office/commercial 2;
- transport 2;
- healthcare 1;
- civic/institutional 0;
- industrial 0.

Stable-secondary candidate vs same-user recurring peers:

- 25 m: 2/9 candidate-context users, mean candidate-peer +0.115, bootstrap 95% [-0.109, +0.387];
- 50 m: 2/9, +0.081, [-0.147, +0.337];
- 100 m: 2/9, +0.019, [-0.210, +0.284].

All composite intervals cross zero. Both candidate-context cases are education. No stable-secondary candidate has office/commercial context within 100 m.

Retail/service at 100 m is more common among peers than candidates in this tiny cohort: mean candidate-peer -0.081, bootstrap interval [-0.135, -0.028]. This is descriptive only.

Decision: Stage 07e closes as null/mixed independent semantic evidence. Historical OSM does not justify promoting stable-secondary mobility geometry to WORK/OFFICE semantics. Do not tune mobility thresholds against these external labels.

Next semantic-source priority remains BCL POI 2008, temporally relevant to 185 / 198 corrected anchors across 19 users.

## 2026-10-03 — Stage 07f BCL POI 2008 acquisition / provenance / CRS patch started

After corrected Stage 07e closed as null/mixed historical-OSM semantic evidence, the next source priority is BCL POI 2008:

- temporally relevant to 185 / 198 corrected recurring non-HOME anchors;
- 19 / 25 candidate users.

Current official BCL record states:

- >6 million mainland-China POIs;
- snapshot scraped in 2008;
- ArcGIS Personal Geodatabase 10.1;
- coordinates + place names;
- no category field;
- access/documentation DOI `10.6084/m9.figshare.28667492`.

The official BCL page itself currently exposes no downloadable attachment, so 07f does not hard-code a guessed file URL. Instead the notebook probes the public Figshare API at runtime.

Modal-first implementation:

- public metadata/files probe with no authentication;
- explicit licence gate before public auto-download;
- deterministic MDB/ZIP candidate selection;
- manual/cached inbox fallback;
- resumable `.part` streaming download with Range support;
- metadata size/MD5 verification and local SHA-256;
- safe ZIP extraction;
- isolated Modal worker image with `mdbtools`, unixODBC, `odbc-mdbtools`, GDAL and unzip;
- MDB table/schema inspection plus GDAL PGeo layer/CRS inspection;
- explicit blocked / ready-for-inspection / ready-for-normalization terminal states.

No semantic join is implemented in 07f. A later 07g is allowed only if access, explicit reuse licence, format and CRS gates pass.

## 2026-10-03 — First Stage 07f Modal run: official file resolved; RAR support required

The first executed Stage-07f notebook resolved the official Figshare record successfully.

Measured public metadata:

- HTTP 200;
- article id: 28667492;
- title: `Points of interest of China in 2008`;
- DOI: `10.6084/m9.figshare.28667492.v1`;
- licence: CC BY 4.0;
- one direct public file;
- file: `Points of interest of China in 2008.rar`;
- size: 120,023,687 bytes;
- MD5: `e77c3473874a6fb64fd0c52d3c66fc84`;
- link-only: false.

Corrected anchor relevance was also reproduced:

- 198 candidate anchors / 25 users;
- 185 BCL-eligible anchors / 19 users;
- 65 exact 2008 anchors;
- 120 explicit +1-year 2009 proxy anchors.

The original 07f implementation allowed MDB/ZIP only, so the run ended blocked solely on `.rar` container format. This was an implementation limitation, not a source-access blocker.

Follow-up patch:

- add `.rar` as an accepted acquisition container;
- prefer direct MDB, then ZIP, then RAR;
- install Debian `unar` in the Modal worker;
- extract RAR into the persistent external-data directory;
- retain the same size/MD5/SHA-256, MDB structure, GDAL PGeo, and CRS gates.

No manual upload is required for the official source discovered by this run.

## 2026-10-03 — Second Stage 07f Modal run: RAR extraction succeeds but no MDB is present

The RAR-enabled notebook successfully reached the post-extraction inspection stage:

- official Figshare RAR selected automatically;
- public source mode;
- worker started successfully;
- download/integrity gates had already passed;
- RAR extraction completed without returning an extraction error.

The worker then reported:

```text
worker ok: False
worker error: no .mdb found after acquisition
```

This means the source archive does not expose an `.mdb` file at the location/path pattern expected by the first inspector, despite the BCL documentation describing ArcGIS Personal Geodatabase 10.1.

Do not infer that the archive is unusable yet. The correct next action is to inspect the actual extracted tree and archive inventory.

Follow-up patch:

- persist/print archive listing and extracted extension counts;
- enumerate representative extracted paths;
- detect `.mdb`, FileGDB `.gdb` directories, GeoPackage, Shapefile and SQLite containers;
- inspect the selected container with GDAL;
- require PGeo only when the selected container is truly MDB;
- if no supported spatial container exists, return an explicit blocked result plus inventory rather than the ambiguous `no .mdb` error.

The next 07f rerun reuses the already cached RAR and extracted directory, so it should not require a new 120 MB download.

## 2026-10-03 — Stage 07f complete: BCL POI 2008 ready for normalization

The third Modal run completed the BCL acquisition/provenance/CRS audit successfully.

Source:

- Figshare article 28667492;
- DOI `10.6084/m9.figshare.28667492.v1`;
- CC BY 4.0;
- `Points of interest of China in 2008.rar`;
- 120,023,687 bytes;
- MD5 `e77c3473874a6fb64fd0c52d3c66fc84`.

The extracted archive contains a File Geodatabase:

```text
POI2008All.gdb
```

not an MDB.

Measured GDAL inspection:

- layer `POI2008CN`;
- Point geometry;
- 6,039,158 features;
- EPSG:4326;
- fields `PNAME`, `X`, `Y`.

Final gates:

- metadata identity pass;
- file access pass;
- explicit CC BY 4.0 licence pass;
- FileGDB format pass;
- spatial point structure pass;
- CRS pass;
- `runner_status = ready_for_normalization`.

Decision: close Stage 07f successfully. Stage 07g may perform deterministic Beijing-only extraction and normalization from the validated FileGDB, while preserving raw POI names and avoiding direct WORK/OFFICE semantics.



## 2026-10-03 — CP2 v2 production timezone migration prepared

The previously audited Notebook-03 all-resolved timezone contract has been promoted into a production migration branch.

Implemented on `cp2-v2-timezone-production`:

- removed the Beijing-radius and 80/80 Asia/Shanghai eligibility rules from `HomeOfficeConfig`;
- resolve every stay coordinate to an IANA `timezone_id` with `timezonefinder==9.0.0`;
- convert arrival/departure timestamps per stay with `ZoneInfo(timezone_id)`;
- retain all timezone-resolved stays, including travel stays;
- keep complete-link 200 m as the production recurring-location representation;
- make mixed-timezone clustering deterministic from UTC observation order;
- make local active-date counting robust to mixed timezone-aware timestamp objects;
- construct HOME/OFFICE local windows from local calendar components so DST transitions use real elapsed overlap;
- promote `timezonefinder` to a runtime dependency;
- add regression coverage for all-resolved retention, coordinate-to-timezone mapping, travel-stay local time, no Beijing gate, DST overlap, and complete-link compactness;
- add `analysis/03_cp2_v2_parity.py` for the 5,821-stay production/reference parity and refreeze check.

Refreeze status:

- code migration: complete on branch;
- private full-release 5,821-stay execution: pending;
- exact Notebook-03 semantic/location/HOME/OFFICE parity: pending;
- CP2 v2 namespace refreeze: blocked until those parity checks pass.

Historical CP2 v1 counts (27 HOME / 16 OFFICE) remain a comparison baseline only and are not asserted as CP2 v2 output.


## 2026-10-03 — CP2 v2 migration CI green

PR #27 CI run 384 completed successfully after two migration-specific regressions were corrected:

- API abstention no longer reports `out_of_scope_geography` for valid non-Beijing stays under the all-resolved timezone contract;
- behavioral interval overlap is computed in UTC after local-window construction, preventing DST spring-forward wall-clock subtraction from overcounting elapsed dwell.

Final CI status on head `b0530318`:

- package install: pass;
- Python compile: pass;
- full pytest suite: pass;
- notebook JSON validation: pass;
- EDA / CP1 / CP2 / API imports: pass.

PR #27 remains draft intentionally. The only remaining CP2-v2 refreeze gate is the private full-release 5,821-stay production-vs-Notebook-03 parity run.


## 2026-10-04 — CP2 v2 full-release parity passed

The focused `03d_cp2_v2_production_parity.ipynb` notebook was executed against the frozen private CP1 stay cache.

Measured scope:

- frozen CP1 stays: 5,821;
- CP1 stay-bearing users: 136;
- timezone-resolved stays: 5,821 / 5,821;
- semantic locations: 2,015;
- recurring locations: 716;
- recurring-location users: 104;
- HOME emitted: 27;
- OFFICE emitted: 16;
- unique emitted users: 37.

Production-v2 matched the independently reconstructed Notebook-03 reference exactly on:

- semantic stay inventory;
- per-stay IANA timezone id;
- arrival local wall time;
- departure local wall time;
- complete-link cluster membership;
- HOME/OFFICE selected semantic cluster membership;
- aggregate semantic/recurrence/emission counts.

Mismatch counts were all zero:

- production-only semantic stays: 0;
- reference-only semantic stays: 0;
- production-only clusters: 0;
- reference-only clusters: 0;
- production-only labels: 0;
- reference-only labels: 0.

`all_parity_checks_pass = true`.

Decision:

- CP2 v2 production migration is validated;
- the production model contract is promoted from `cp2-v1` to `cp2-v2`;
- PR #27 can move out of draft once CI passes on the refreeze/version patch;
- downstream reruns should be limited to the production-dependent lineage, not the already timezone-v2 behavior lineage.


## 2026-10-04 — CP2 v2 downstream refresh prepared

After CP2 v2 merged to `main` at `f1bbca4`, the production-dependent downstream lineage was isolated for rerun.

Prepared branch: `cp2-v2-downstream-refresh`.

Changes:

- Stage 05/05b/05c outputs are namespaced under `cache/cp2_v2/`;
- Stage 05/05b/05c analysis helpers now normalize mixed per-stay timezone-aware timestamps to naive local wall-clock series before calendar/hour operations;
- the historical 9-user Stage-05c stable-secondary count is retained as Beijing-v1 reference only, not as a rerun assertion;
- Stage 07b consumes CP2-v2 05b/05c artifacts while reusing unchanged 03a/06 behavior artifacts;
- Stage 07c production namespace is now `production_complete_link_200m_all_resolved_timezone_v2`;
- Stage 07c/07d/07e no longer pin old EDA branches and instead resolve the requested branch, defaulting to `main`;
- Stage 07d consumes only CP2-v2 Stage-07c anchors, but reuses the existing content-addressed historical OSM raw cache so already-fetched requests are not repeated;
- Stage 07e consumes only CP2-v2 downstream artifacts and the shared historical OSM raw cache;
- Stage 06/06b/06c/06d and the Stage-07f BCL source audit remain out of scope for rerun.

Required measured rerun order remains:

`05 -> 05b -> 05c -> 07b -> 07c -> 07d -> 07e`.

No new downstream measured result is frozen yet.


## 2026-10-04 — Stage 05 CP2 v2 reliability refresh

Stage 05 was rerun on the refrozen CP2-v2 all-resolved per-stay timezone production representation.

Measured scope:

- CP1 stays: 5,821;
- CP1 stay users: 136;
- semantic users: 136;
- semantic locations: 2,015;
- recurring locations: 716;
- recurring-anchor users: 104;
- production HOME emitted: 27;
- production OFFICE emitted: 16.

Historical Beijing-v1 Stage-05 scope was 97 semantic users / 1,111 locations / 486 recurring locations / 73 recurring-anchor users. The old section remains historical evidence and is not overwritten.

Candidate coverage under CP2-v2:

- fixed-window: 42 HOME / 30 OFFICE;
- HoWDe-style: 26 HOME / 27 OFFICE;
- recurrence: 104 HOME / 38 OFFICE.

Cross-method same-location agreement:

- HOME fixed vs HoWDe: 19/23 = 82.6%;
- HOME fixed vs recurrence: 35/42 = 83.3%;
- HOME HoWDe vs recurrence: 20/26 = 76.9%;
- OFFICE fixed vs HoWDe: 16/19 = 84.2%;
- OFFICE fixed vs recurrence: 6/25 = 24.0%;
- OFFICE HoWDe vs recurrence: 3/24 = 12.5%.

First-vs-second-half agreement:

- fixed HOME 68.4%, OFFICE 50.0%;
- HoWDe HOME 20.0%, OFFICE 40.0%;
- recurrence HOME 41.0%, OFFICE 21.4%.

Odd-vs-even-week agreement:

- fixed HOME 81.3%, OFFICE 80.0%;
- HoWDe HOME 37.5%, OFFICE 66.7%;
- recurrence HOME 53.5%, OFFICE 35.3%.

Held-out top-1 persistence:

- fixed HOME 50.0%, OFFICE 42.1%;
- HoWDe HOME 45.5%, OFFICE 26.7%;
- recurrence HOME 37.8%, OFFICE 38.5%.

At 30% stay dropout, candidate retention was:

- fixed HOME/OFFICE 81.7% / 78.9%;
- HoWDe HOME/OFFICE 69.2% / 56.8%;
- recurrence HOME/OFFICE 81.7% / 65.8%.

Under +12 h local-time stress:

- fixed HOME/OFFICE 31.0% / 13.3%;
- HoWDe HOME/OFFICE 19.2% / 11.1%;
- recurrence HOME/OFFICE 100.0% / 68.4%.

Interpretation:

- CP2-v2 materially broadens recurring-place coverage without increasing frozen HOME/OFFICE emissions;
- HOME cross-method convergence remains substantially stronger than recurrence-based OFFICE evidence;
- the broader cohort does not improve temporal reliability uniformly and several persistence measures weaken;
- additional recurring structure must not be treated as additional semantic certainty;
- conservative emission/abstention remains justified.

Decision: Stage 05 CP2-v2 refresh is complete. Proceed to Stage 05b HOME consensus tiers + adaptive WORK audit using the new `cache/cp2_v2/05_home_office_reliability_validation` artifacts.


## 2026-10-04 — Stage 05b CP2 v2 refresh

Stage 05b reran successfully on the CP2-v2 Stage-05 artifacts.

HOME consensus:

- 97 unique HOME vote winners;
- 23 HIGH;
- 6 MEDIUM;
- 68 UNCERTAIN;
- 29 HIGH/MEDIUM users total;
- 24 HIGH/MEDIUM users already baseline-emitted HOME;
- 5 HIGH/MEDIUM non-emitted candidates;
- all 5 non-emitted HIGH/MEDIUM cases are fixed-window candidates that failed the final production gate;
- no HIGH/MEDIUM expansion case comes from the broad recurrence-only / outside-fixed-candidate population.

Historical Beijing-v1 Stage 05b had 67 winners / 21 HIGH / 4 MEDIUM / 42 UNCERTAIN and only 2 HIGH/MEDIUM non-emitted candidates.

Primary adaptive secondary-anchor audit (42d windows / 14d step / 0.70 stability):

- eligible HIGH/MEDIUM HOME users: 29;
- stable_secondary_anchor: 9;
- multi_anchor: 3;
- unstable: 1;
- insufficient: 16;
- sufficient users: 13.

Historical Beijing-v1 had 25 eligible users with 9 stable / 3 multi-anchor / 1 unstable / 12 insufficient.

Interpretation: all four additional CP2-v2 HOME-consensus users are added as insufficient-support cases. The stable-secondary WORK-like subset does not expand.

Window sensitivity at threshold 0.70:

- 28d: 10 sufficient / 6 stable / 3 multi-anchor / 1 unstable;
- 42d: 13 sufficient / 9 stable / 3 multi-anchor / 1 unstable;
- 56d: 14 sufficient / 10 stable / 4 multi-anchor / 0 unstable.

Stable counts remain 6 / 9 / 10 across 28d / 42d / 56d, identical to the historical run.

At 42d, increasing stability threshold 0.70 -> 0.80 leaves the stable count unchanged at 9.

Fixed-window OFFICE comparison at 42d remains limited:

- comparable users: 10;
- dominant adaptive anchor matches fixed OFFICE: 40.0%.

Decision:

- keep production HOME/OFFICE unchanged;
- retain 5 HIGH/MEDIUM non-emitted HOME cases for targeted review only;
- do not promote recurrence-only HOME candidates;
- keep stable_secondary_anchor descriptive rather than semantic OFFICE;
- Stage 05b CP2-v2 refresh is complete;
- proceed to Stage 05c independent evidence on the unchanged 9-user stable-secondary subset.


## 2026-10-04 — Stage 05c CP2 v2 refresh

Stage 05c reran successfully on the CP2-v2 semantic representation and Stage-05b artifacts.

Cohort:

- stable-secondary users: 9;
- historical Beijing-v1 stable-secondary users: 9;
- CP2-v2 delta: 0;
- users with a fair >=3-active-day same-user recurring peer comparator: 7.

Primary independent evidence:

- weekday-weekend visit contrast: 5/7 top-1, median candidate-minus-peer-median +0.188;
- HOME-pair transition-day share: 3/7 top-1, median +0.102;
- arrival-hour concentration: 0/7 top-1, median -0.168;
- dwell regularity: 0/7 top-1, median -0.057.

Convergence:

- 0 users with >=3 top-1 evidence axes;
- 1 user with exactly 2;
- 6 users with 0-1.

Paired-bootstrap 95% intervals all crossed zero:

- weekday contrast [-0.083, +0.261];
- HOME-pair transition [-0.083, +0.333];
- arrival concentration [-0.341, +0.178];
- dwell regularity [-0.231, +0.059].

Peer-support sensitivity:

- >=2 active days: 9 users, 0 with >=3 top axes;
- >=3 active days: 7 users, 0 with >=3 top axes;
- >=5 active days: 3 users, 1 with >=3 top axes.

Static semantic comparison among the seven fair-comparator users:

- fixed-window OFFICE match: 3 / 7;
- HoWDe-style OFFICE match: 2 / 7;
- recurrence OFFICE match: 6 / 7;
- baseline-emitted OFFICE match: 3 / 7.

No static-match stratum has >=3-axis top-rank convergence.

Interpretation:

- the CP2-v2 upstream expansion does not change the stable-secondary cohort;
- independent WORK-like evidence remains mixed;
- small numerical shifts in peer-relative medians do not change qualitative direction;
- semantic WORK/OFFICE expansion remains closed.

Decision: retain stable_secondary_anchor as descriptive only. Stage 05c CP2-v2 refresh is complete. Proceed to Stage 07b factorized work-regime profiles using the refreshed CP2-v2 05b/05c artifacts while reusing the already-valid 03a and 06 behavior/routine artifacts.


## 2026-10-04 — Stage 07b CP2 v2 refresh

Stage 07b reran successfully using:

- unchanged Stage-03a behavior features;
- refreshed CP2-v2 Stage-05b HOME/adaptive-work artifacts;
- refreshed CP2-v2 Stage-05c independent-evidence artifact;
- unchanged Stage-06 routine summary.

Support:

- behavior users: 182;
- adaptive work-pattern users: 29 (historical 25);
- routine users: 107;
- HOME-context users: 29 (historical 25);
- independent secondary-evidence users: 7.

Axis prevalence:

- site_multiple_recurring: 72;
- home_context_supported: 29;
- mobile_complexity_evidence: 23;
- route_repeated: 23;
- site_stable_secondary: 9;
- independent_secondary_evidence_available: 7;
- site_adaptive_multi_anchor: 3;
- schedule_shifted_evidence: 2;
- site_unstable: 1.

Key overlaps are unchanged:

- stable-secondary + multiple-recurring: 9;
- stable-secondary + repeated-route: 7;
- multiple-recurring + repeated-route: 22;
- shifted + repeated-route: 2.

Representation signatures are exactly unchanged from the historical run:

- abstain: 110;
- anchor_set: 48;
- anchor_set + route_region: 13;
- single_anchor + anchor_set + route_region: 7;
- single_anchor + anchor_set: 2;
- anchor_set + route_region + schedule_agnostic: 2.

Interpretation:

- CP2-v2 expands HOME-context support by four users but leaves all mobility geometry / route / schedule representation counts unchanged;
- factorization remains the correct abstraction;
- HOME support is contextual rather than geometry-defining;
- the stable-secondary subset remains 9 users and remains embedded in broader recurring-anchor structure.

Decision: Stage 07b CP2-v2 refresh is complete. Proceed to Stage 07c using the new production location namespace `production_complete_link_200m_all_resolved_timezone_v2` and CP2-v2 05b/05c artifacts.


## 2026-10-04 — Stage 07c CP2 v2 refresh

Stage 07c reran successfully in the CP2-v2 production namespace.

Namespace validation:

- location namespace: `production_complete_link_200m_all_resolved_timezone_v2`;
- production semantic-location users: 136;
- production semantic locations: 2,015;
- supported HOME ids checked: 29 / missing 0;
- dominant Stage-05b secondary ids checked: 15 / missing 0.

Candidate recurring non-HOME universe:

- 29 users;
- 298 anchors.

Historical corrected Beijing-v1 universe was 25 users / 198 anchors.

Median observation-year distribution:

- 2007: 2 anchors / 2 users;
- 2008: 93 / 16;
- 2009: 164 / 15;
- 2010: 6 / 3;
- 2011: 23 / 6;
- 2012: 10 / 3.

Source leverage:

- CLCD exact-year physical context: 298 / 298 anchors;
- ohsome historical OSM temporal eligibility: 296 / 298 anchors;
- BCL POI 2008 exact/+1-year relevance: 259 anchors / 23 users;
- Gaode 2010: 6 anchors / 3 users;
- 2011 candidates: 23 anchors / 6 users;
- Baidu 2012: 10 anchors / 3 users.

Two anchors have median observation dates before the ohsome history boundary (2007-10-08). They remain in the full anchor universe but must be excluded from OSM fetch/cache-completeness requirements.

Follow-up correctness patch prepared:

- Stage 07d now filters OSM requests to temporally eligible anchors;
- Stage 07e validates complete raw OSM cache only over the eligible subset while retaining all anchors in final joined metrics;
- regression tests cover pre-ohsome anchors;
- Stage 07c BCL-2008 source-gate metadata is synchronized with the completed Stage-07f audit (public file, CC BY 4.0, FileGDB EPSG:4326, ready for normalization).

Decision: Stage 07c CP2-v2 refresh is complete. Run Stage 07d only with the eligibility-aware patch; expected OSM target is 296 anchors while CLCD target remains 298.


## 2026-10-04 — Stage 07d CP2 v2 refresh

Stage 07d completed successfully on the CP2-v2 production-aligned recurring non-HOME universe.

Universe:

- 298 anchors / 29 users;
- namespace: `production_complete_link_200m_all_resolved_timezone_v2`;
- ohsome eligible: 296;
- pre-ohsome ineligible: 2.

CLCD exact-year physical context:

- known point class: 275 / 298 = 92.28%;
- unknown: 23 / 298 = 7.72%;
- impervious: 256 / 298 = 85.91%;
- point = 3x3 mode: 294 / 298 = 98.66%;
- point = 5x5 mode: 290 / 298 = 97.32%;
- impervious among known classes: 256 / 275 = 93.09%.

Corrected Beijing-v1 comparison was 198 anchors, 100% known class, 96.46% impervious, 99.49% point-vs-3x3 agreement and 98.48% point-vs-5x5 agreement.

Historical OSM / ohsome:

- target: 296 eligible anchors;
- completed: 296 / 296 = 100%;
- cached: 287;
- newly fetched: 9;
- rate-limited: 0;
- deferred: 0;
- request errors: 0;
- parse errors: 0.

OSM context among eligible anchors:

- semantic context found: 89 / 296 = 30.07%, 20 users;
- broad work-compatible context: 61 / 296 = 20.61%, 18 users;
- residential context: 13 / 296 = 4.39%, 5 users.

Corrected Beijing-v1 OSM context was 31.82% semantic, 23.74% work-compatible and 3.03% residential. The expanded CP2-v2 universe therefore preserves a similar ~30% historical semantic-context rate while slightly reducing the work-compatible share.

Interpretation:

- the broader all-resolved cohort is less uniformly impervious than the old Beijing-focused cohort;
- local CLCD spatial agreement remains extremely high;
- historical OSM proportions remain source-bounded mapping evidence, not semantic truth;
- two pre-2007-10-08 anchors are temporally ineligible for ohsome and must not be counted as no-context negatives.

Decision: Stage 07d CP2-v2 refresh is complete. Proceed to Stage 07e only after making OSM-distance metrics and peer comparisons eligibility-aware.


## 2026-10-04 — Stage 07e CP2 v2 final refresh

Stage 07e completed successfully on commit `6804925` after correcting:

- pre-ohsome temporal eligibility;
- notebook pandas/helper bootstrap;
- Stage-07c carried-profile vs Stage-07b authoritative-axis merge collisions.

Execution:

- no traceback;
- outputs saved under `cache/cp2_v2/07e_semantic_distance_alignment`.

Universe:

- 298 recurring non-HOME anchors / 29 users;
- namespace `production_complete_link_200m_all_resolved_timezone_v2`;
- 296 OSM-eligible anchors;
- 2 pre-ohsome anchors retained as not eligible;
- raw cache validated 296 / 296.

Exact radial <=100 m historical OSM context among eligible anchors:

- semantic: 86 / 296 = 29.05%;
- work-compatible: 59 / 296 = 19.93%.

Work-compatible distance buckets:

- 0–25 m: 36;
- 25–50 m: 8;
- 50–100 m: 15;
- none within 100 m: 237.

Category <=100 m:

- education 33;
- recreation/tourism 25;
- retail/service 17;
- residential 13;
- transport 13;
- office/commercial 4;
- healthcare 1;
- industrial 1;
- civic/institutional 0.

Stable-secondary comparison:

- 9 stable-secondary users / 9 exact candidate anchors / 9 within-user rows;
- 25 m: 2/9 candidate-context, mean candidate-peer +0.123, CI [-0.108, +0.399];
- 50 m: 2/9, +0.088, CI [-0.147, +0.349];
- 100 m: 2/9, +0.036, CI [-0.201, +0.303].

All composite intervals cross zero.

Candidate category decomposition:

- both mapped candidate-context cases are education;
- 0/9 candidate anchors have office/commercial within 100 m;
- retail/service at 100 m is more common among peer anchors: mean candidate-peer -0.074, CI [-0.125, -0.026].

Corrected Beijing-v1 comparison was:

- 61/198 semantic <=100 m;
- 46/198 work-compatible <=100 m;
- composite candidate-peer differences +0.115 / +0.081 / +0.019, all with intervals crossing zero.

Therefore the CP2-v2 expansion leaves the semantic decision unchanged.

Factorized-axis context inside the current 29-user analysis subset:

- stable-secondary: 9 users, 7 with any work-compatible context;
- multiple-recurring: 28, 18;
- adaptive multi-anchor: 3, 3;
- repeated-route: 12, 9;
- shifted-schedule: 0;
- mobile-complexity: 7, 7;
- independent-secondary-evidence available: 7, 5.

Decision:

- keep stable_secondary_anchor descriptive only;
- do not promote WORK/OFFICE;
- do not tune mobility thresholds to OSM;
- Stage 07e CP2-v2 refresh is complete;
- the production-dependent rerun lineage `05 -> 05b -> 05c -> 07b -> 07c -> 07d -> 07e` is now fully refreshed.


## 2026-10-04 — Stage 07g BCL POI 2008 alignment started

The CP2-v2 production-dependent rerun through Stage 07e is complete. Historical OSM remained null/mixed independent semantic evidence, so the next external semantic-source track moves to the already-audited BCL POI 2008 source.

Stage 07f source facts already frozen:

- Figshare article 28667492;
- DOI `10.6084/m9.figshare.28667492.v1`;
- CC BY 4.0;
- official RAR size 120,023,687 bytes;
- extracted FileGDB `POI2008All.gdb`;
- layer `POI2008CN`;
- 6,039,158 point features;
- EPSG:4326;
- fields `PNAME`, `X`, `Y`;
- runner status `ready_for_normalization`.

Current CP2-v2 Stage-07c relevance:

- 298 recurring non-HOME anchors / 29 users total;
- 259 BCL-eligible anchors / 23 users under explicit 2007–2009 exact/+1-year policy;
- 2 anchors from 2007;
- 93 exact-year 2008 anchors;
- 164 one-year 2009 proxies.

Stage 07g design:

- do not re-download BCL;
- validate the Stage-07f manifest and cached source SHA-256;
- do not reintroduce a Beijing-only geofence;
- spatially extract FileGDB POIs only around the 259 temporally relevant CP2-v2 anchors;
- use deterministic padded GDAL tiles, then exact Haversine <=100 m matching;
- preserve raw `PNAME` privately;
- derive only predeclared lexical name signals with explicit unknown / multi-signal ambiguity;
- compare exact Stage-05b stable-secondary anchors to same-user BCL-eligible peers at 25 / 50 / 100 m;
- decompose composite lexical evidence by category;
- keep all WORK/OFFICE/HOME and occupation claims disabled.

New files:

- `analysis/07g_bcl_poi_2008_alignment.py`;
- `notebooks/07g_bcl_poi_2008_alignment.ipynb`;
- `tests/test_bcl_poi_2008_alignment.py`;
- `docs/eda/31_bcl_poi_2008_alignment.md`;
- `docs/07g_bcl_poi_2008_alignment_handoff.md`.

Reproducibility cleanup included:

- Stage 07f namespace guard now uses the CP2-v2 production namespace;
- Stage 07f notebook defaults to current `main`;
- Stage 07f notebook reads the explicit CP2-v2 Stage-07c anchor artifact instead of globbing the first historical anchor cache.

No Stage-07f rerun is required for the current 07g run because the source manifest / raw archive / extracted FileGDB are source-level artifacts and already passed acquisition, licence, format and CRS gates.


## 2026-10-04 — Stage 07g runtime handoff fix

The first Stage-07g runtime extracted the BCL neighborhood successfully:

- 118 GDAL query tiles;
- 5,071 raw tile rows;
- 4,884 deduplicated neighborhood POIs;
- worker status `ok = True`.

Two notebook/worker handoff issues were then observed:

1. `modal.Volume.reload()` cannot be called from the notebook process; Modal restricts it to a running function.
2. The worker-written pandas pickle was visible on the next attempt but could not be unpickled by the notebook kernel because the worker and notebook pandas runtimes used incompatible pickle internals.

These were execution-environment issues, not BCL/GDAL extraction failures.

Fix:

- remove notebook-side Volume reload;
- stop using a pandas pickle as the cross-container handoff;
- worker persists the precise neighborhood POIs as private CSV for audit/reuse;
- worker also returns the ~4.9k deduplicated POI rows through Modal result serialization;
- notebook reconstructs the DataFrame directly from the serialized records;
- assert returned row count equals the worker's deduplicated count before lexical analysis;
- regression test forbids `data_volume.reload()` and `pd.read_pickle(POI_PRIVATE)` in this handoff.

No Stage-07g semantic rule or spatial extraction logic changed.


## 2026-10-04 — Stage 07g measured result

Stage 07g completed successfully on commit `9778b66` after the Modal worker-handoff correction.

Source / scope:

- Stage-07f manifest gate: pass;
- 298 candidate anchors / 29 users;
- 259 BCL-eligible anchors / 23 users;
- 93 exact 2008 anchors;
- 2 proxy-2007 anchors;
- 164 proxy-2009 anchors.

Extraction:

- 118 GDAL tiles;
- 5,071 raw tile rows;
- 4,884 deduplicated neighborhood POIs;
- 966 exact anchor-POI pairs <=100 m.

Coverage:

- any POI <=100 m: 140 / 259;
- any declared lexical signal <=100 m: 97 / 259;
- broad work-compatible lexical signal <=100 m: 87 / 259.

Lexical status among extracted POIs:

- unknown 3,769 / 4,884 = 77.17%;
- single-signal 1,081 = 22.13%;
- ambiguous multi-signal 34 = 0.70%.

Stable-secondary paired comparison, n=9:

- 25 m: 2/9 candidate-context, candidate-peer +0.199, CI [-0.041, +0.537];
- 50 m: 3/9, +0.171, CI [-0.099, +0.494];
- 100 m: 4/9, +0.021, CI [-0.360, +0.395].

All broad-composite intervals cross zero.

Category decomposition:

- education candidates: 1/9 at 25 m, 2/9 at 50 m, 3/9 at 100 m; positive contrasts cross zero;
- retail/service candidates: 2/9 at all thresholds; positive contrasts cross zero;
- business-name candidates: 0/9 at all thresholds;
- business-name is peer-favored at 50 m (-0.053, CI [-0.104, -0.009]) and 100 m (-0.162, CI [-0.232, -0.090]);
- recreation/tourism is peer-favored at 25 / 50 / 100 m with intervals below zero;
- civic/institutional is peer-favored at 100 m.

Interpretation:

- BCL provides broader external historical name context than OSM;
- the exact stable-secondary candidate still does not beat same-user recurring peers reliably;
- there is no business-name support at any exact stable-secondary candidate;
- no WORK/OFFICE promotion is justified.

Decision: keep `stable_secondary_anchor` descriptive only; do not tune mobility thresholds to BCL; Stage 07g closes as independent external evidence consistent with the null/mixed Stage-05c/07e semantic conclusion.


## 2026-10-04 — Stage 07h evidence triangulation added

Stage 07g closed as independent historical lexical evidence consistent with the null/mixed Stage-05c and Stage-07e conclusions.

Stage 07h was added to test cross-source convergence at the individual stable-secondary-user level without creating a new semantic score.

Frozen cohort:

- 9 Stage-05b stable-secondary users;
- exact candidate = Stage-05b `dominant_location_id`.

Inputs:

- Stage 05c behavioral candidate-vs-peer comparison: 7 users with fair comparators;
- Stage 07e historical OSM candidate-vs-peer comparison: 9 users;
- Stage 07g BCL lexical candidate-vs-peer comparison: 9 users.

Method:

- candidate location ids must match across every available source;
- preserve Stage-05c primary criterion `top1_evidence_axes >= 3`;
- retain weaker `beats_peer_median_axes >= 3` only as descriptive directional majority;
- preserve OSM/BCL candidate-minus-peer differences at 25 / 50 / 100 m;
- use 100 m as the shared primary cross-source radius;
- summarize external sign agreement, exact-candidate context overlap, behavior/external signatures, and strict/directional three-way convergence;
- user-level evidence panel remains private;
- no weighted WORK/OFFICE probability or semantic classifier is created.

New files:

- `analysis/07h_evidence_triangulation.py`;
- `notebooks/07h_evidence_triangulation.ipynb`;
- `tests/test_evidence_triangulation.py`;
- `docs/eda/32_evidence_triangulation.md`;
- `docs/07h_evidence_triangulation_handoff.md`.

Expected frozen input checks in the notebook:

- 05b stable-secondary rows: 9;
- 05c fair-comparator users: 7;
- 07e OSM comparison users: 9;
- 07g BCL comparison users: 9.

Next action: run Stage 07h and inspect aggregate convergence signatures before deciding whether the external semantic-source track should close.


## 2026-10-04 — Stage 07h measured result and semantic-source closure

Stage 07h ran successfully on commit `ff79fdd` with no traceback.

Input gates:

- Stage-05b stable-secondary cohort: 9 users;
- Stage-05c fair-comparator evidence: 7 users;
- Stage-07e OSM paired evidence: 9 users;
- Stage-07g BCL paired evidence: 9 users;
- candidate location identity: PASS across available sources.

Source coverage:

- behavior 7 / 9;
- OSM 9 / 9;
- BCL 9 / 9;
- all three sources 7 / 9.

External direction:

- 25 m: both-positive 1, both-negative 2, no direct positive/negative disagreement;
- 50 m: both-positive 1, both-negative 3, no direct positive/negative disagreement;
- 100 m: both-positive 1, both-negative 3, directly opposite 3.

Exact-candidate context overlap at 100 m:

- both OSM + BCL: 1 / 9;
- OSM only: 1 / 9;
- BCL only: 3 / 9;
- neither: 4 / 9.

Behavior:

- strict Stage-05c support: 0 users;
- weaker directional-majority support: 3 users.

Final convergence:

- external OSM+BCL both-positive at 100 m: 1 user;
- strict three-way convergence: 0 users;
- weaker directional three-way convergence: 0 users.

The one user positive in both external sources belongs to the weak behavioral band. No directional-majority behavioral user is positive in both external sources.

Decision:

- no multi-source semantic convergence;
- no stable-secondary => WORK/OFFICE promotion;
- no threshold retuning;
- close the current semantic-source track.

Any future attempt to validate WORK/OFFICE semantics should rely on qualitatively better supervision/ground truth, not additional opportunistic external-source mining on the same nine-user cohort.


## 2026-10-05 — Stage 07i threshold sensitivity + OSM weighting correction

Methodological review after Stage 07h identified that historical OSM should not carry equal negative evidential weight with BCL.

OSM timing:

- each Stage-07d query used the anchor's median observation date;
- 93 eligible anchors are from 2008;
- 164 from 2009;
- therefore 257 / 296 (86.8%) historical OSM snapshots are from 2008–2009.

Interpretation correction:

- BCL POI 2008 becomes the primary historical functional-POI source;
- historical OSM becomes positive support-only;
- OSM absence/negative direction is not treated as contradiction;
- CLCD remains physical context only.

The user also raised a plausible second explanation for low OFFICE/stable-secondary semantic support: conservative heuristic thresholds.

Stage 07i was added as a no-retuning robustness audit.

Production OFFICE sensitivity:

- full 27-config grid over dates 2/3/5, share .20/.30/.40, margin .05/.10/.20;
- frozen baseline remains 3 / .30 / .10.

Adaptive stable-secondary sensitivity:

- OAT window 28/42/56;
- OAT observed days 4/6/8;
- OAT candidate days 2/3/4;
- OAT candidate stays 1/2/3;
- OAT stability .60/.70/.80;
- joint relaxed / mildly-relaxed / baseline / strict profiles.

BCL radius sensitivity:

- exact 25/50/75/100/125/150 m using the already-extracted Stage-07g POI neighborhood;
- 150 m is the maximum safe radius without new extraction.

Hard reproduction gates:

- OFFICE baseline must reproduce 16;
- Stage-05b stable-secondary baseline must reproduce 9 with exact candidate IDs.

No threshold will be selected from Stage 07i based on semantic agreement alone.


## 2026-10-05 — Stage 07i measured threshold sensitivity

Stage 07i completed successfully on commit `a8d8308` with no traceback.

Reproduction gates:

- CP2-v2 semantic users 136 / locations 2,015;
- frozen Stage-05b stable-secondary reproduced exactly: 9 users, exact candidate IDs;
- frozen production OFFICE reproduced: 16 users.

OFFICE gate result:

- baseline 3 dates / .30 share / .10 margin = 16;
- margin .10 -> .05 at fixed 3/.30 = 18, retains all 16 and adds 2;
- share .30 -> .20 at fixed 3/.10 = 23, retains all 16 and adds 7;
- 3/.20/.05 = 26, retains all 16 and adds 10;
- lowering dates to 2 greatly expands candidate coverage but can change candidate identity.

Thus OFFICE is conservative in coverage.

BCL evidence in the evaluable emitted subset does not grow with relaxed gates:

- baseline: 4 evaluable / 2 broad-context / 0 business-name;
- 3/.30/.05: 5 / 2 / 0;
- 3/.20/.10: 5 / 2 / 0;
- 3/.20/.05: 6 / 2 / 0.

Stable-secondary OAT:

- baseline 9;
- 56d, observed-days4, stability.60 each produce 10 while retaining all 9;
- candidate-stays1/3 and stability.80 leave the nine-user core unchanged;
- candidate-days2 produces 10 but loses 2 baseline users and adds 3;
- candidate-days4 reduces to 5;
- 28d reduces to 6.

Joint profiles:

- relaxed 10 stable, 9 multi-anchor, retains 7 baseline and adds 3;
- mildly relaxed 10 stable, 8 multi-anchor, retains 7 and adds 3;
- baseline 9 stable, 3 multi-anchor, all 9 retained;
- strict 5 stable.

BCL radius for frozen baseline:

- candidate context increases 2/9 at 25m -> 6/9 at 150m;
- mean candidate-peer = +.199 / +.171 / +.102 / +.021 / +.057 / +.039 for 25/50/75/100/125/150m;
- all bootstrap intervals cross zero;
- business-name exact candidates remain 0/9 through 100m, 1/9 at125m, 2/9 at150m.

Relaxed mobility profiles do not improve BCL alignment:

- relaxed/mildly relaxed mean candidate-peer at100m = -.105;
- at150m = -.095;
- baseline remains near zero positive;
- strict has a larger +.261 at100m but only n=5 with wide CI.

BCL-primary / OSM-support-only snapshot at100m:

- BCL candidate-favoring 4/9;
- BCL peer-favoring 5/9;
- only 1/4 BCL-positive users has OSM mapped-candidate / candidate-favoring support;
- 3/4 BCL-positive users simply lack mapped historical OSM candidate context;
- behavior-strict + BCL-positive = 0;
- behavior-directional-majority + BCL-positive = 2.

Decision:

- historical OSM remains support-only;
- production OFFICE is conservative in coverage, but relaxed emissions are not independently validated;
- stable-secondary null/mixed semantics are robust to nearby threshold changes;
- 100m POI radius is not the limiting factor;
- keep production gates frozen.

Potential next stage: targeted near-miss OFFICE audit for users added by small one-step share/margin relaxations, rather than global retuning.


## 2026-10-05 — Stage 07j targeted near-miss OFFICE audit added

Stage 07i established that the frozen OFFICE policy is conservative in coverage but did not justify global threshold relaxation.

Targeted one-step expansions:

- baseline 3 dates / .30 share / .10 margin: 16 users;
- margin relaxation to .05: +2 users;
- share relaxation to .20: +7 users.

Stage 07j audits only those 9 new users and compares them with the frozen 16-user OFFICE reference cohort.

Evidence reused from existing artifacts:

- full-period fixed OFFICE candidate identity;
- production HOME collision;
- HoWDe-style OFFICE candidate identity;
- recurrence OFFICE candidate identity;
- first/second split candidate recovery;
- odd/even split candidate recovery;
- 60/40 held-out top-1 persistence;
- 10/20/30% dropout candidate retention across deterministic seeds;
- 12-hour time-shift falsification diagnostic;
- BCL-primary context at 100 m and 150 m.

No new total score or promotion threshold is created.

Hard gates:

- expected audit groups = 16 baseline + 2 margin-near + 7 share-near = 25 unique users;
- near-miss groups must be disjoint;
- every audit candidate must match the frozen full-period fixed-window candidate.

New files:

- `analysis/07j_near_miss_office_audit.py`;
- `notebooks/07j_near_miss_office_audit.ipynb`;
- `tests/test_near_miss_office_audit.py`;
- `docs/eda/34_near_miss_office_audit.md`;
- `docs/07j_near_miss_office_audit_handoff.md`.

Decision goal: determine whether either one-step near-miss family is behaviorally comparable to frozen OFFICE on existing reliability diagnostics. No production gate changes occur in Stage 07j.


## 2026-10-05 — Stage 07j measured near-miss OFFICE result

Stage 07j ran successfully on commit `afbfe81` with no traceback.

Hard gates:

- baseline OFFICE 16;
- margin-near 2;
- share-near 7;
- 25 unique audit users;
- full-period candidate identity PASS.

Near-miss aggregate (9 users):

- HOME collision: 0;
- both static comparators match exact candidate: 0;
- both split tests recover exact candidate: 1;
- held-out exact candidate top-1: 2;
- 100% dropout retention: 5;
- BCL-evaluable: 2;
- BCL work-compatible / business-name context at 100 m or 150 m: 0.

Margin-near (2 users):

- HoWDe exact match 2/2;
- recurrence exact match 0/2;
- both split tests 0/2;
- held-out exact-candidate top-1 0/2;
- median dropout retention .889.

Share-near (7 users):

- HoWDe exact match 3/7;
- recurrence exact match 1/7;
- both split tests 1/7;
- held-out exact-candidate top-1 2/7;
- median dropout retention 1.0 but mean .841.

Decision:

- do not relax global OFFICE margin or share gates from this evidence;
- keep the 9 near-miss users as abstained candidates;
- proceed to targeted historical-imagery adjudication rather than more global threshold tuning.

Next stage: 07k KML export + fixed manual historical-imagery review rubric.


## 2026-10-05 — Stage 07k blinded historical imagery review added

Stage 07j left 9 one-step OFFICE near-miss users in abstention and recommended targeted historical-imagery adjudication.

Stage 07k prepares a blinded manual Google Earth Pro review workflow.

Design:

- rebuild exact CP2-v2 semantic candidate coordinates from frozen CP1 stays;
- attach observation start / median distinct local date / end;
- attach HOME reference coordinates;
- generate 50 / 100 / 150 m rings;
- use deterministic blinded audit IDs;
- exclude user id, near-miss family, behavior and BCL evidence from KML/review CSV;
- keep the unblinding key private until review is complete.

Primary review set:

- 9 near-miss candidates.

Optional reference:

- 16 frozen OFFICE candidates.

Private KML outputs:

- `near_miss_9_blinded_historical_imagery_review_private.kml`;
- `baseline16_blinded_historical_imagery_reference_private.kml`;
- `all25_blinded_historical_imagery_review_private.kml`.

Fixed visual context classes cover commercial-like complex, education campus, healthcare/institutional, industrial, residential, transport, mixed urban, construction/vacant, recreation/green, other, and ambiguous.

Historical imagery is contextual evidence only. It does not prove employer, occupation, or OFFICE.

New files:

- `analysis/07k_historical_imagery_review.py`;
- `notebooks/07k_historical_imagery_review.ipynb`;
- `tests/test_historical_imagery_review.py`;
- `docs/eda/35_historical_imagery_review.md`;
- `docs/07k_historical_imagery_review_handoff.md`.


## 2026-10-05 — Stage 07l imagery unblinding synthesis added

The blinded Stage-07k visual review was completed for all 9 OFFICE near-miss candidates using approximate same-year historical imagery proxies.

Imagery-only review classes:

- office-like: 1;
- institutional/daytime-compatible: 3;
- OFFICE-contradictory context: 2;
- indeterminate: 3.

Stage 07l was added to unblind only after those visual labels were fixed.

Inputs:

- completed 9-row blinded review CSV;
- Stage-07k private unblinding key;
- Stage-07j private audit panel.

The stage joins imagery with existing HoWDe, recurrence, split-half, held-out, dropout, HOME and BCL evidence.

No composite score and no automatic OFFICE promotion are introduced.

New files:

- `analysis/07l_imagery_unblinding_synthesis.py`;
- `notebooks/07l_imagery_unblinding_synthesis.ipynb`;
- `tests/test_imagery_unblinding_synthesis.py`;
- `docs/eda/36_imagery_unblinding_synthesis.md`;
- `docs/07l_imagery_unblinding_handoff.md`.

Next action: upload/copy the completed review CSV into the notebook runtime and run Stage 07l only.


## 2026-10-05 — Stage 07l measured imagery-unblinding result

Stage 07l ran successfully against `main` at `7dde88f`.

Execution gates:
- review rows: 9;
- Stage-07k key rows: 25;
- Stage-07j audit rows: 25;
- unblinding validation: PASS (9/9 near-miss candidates matched exactly).

Visual context after unblinding:
- margin-near: 1 indeterminate + 1 office-like;
- share-near: 2 indeterminate + 3 institutional/daytime-compatible + 2 OFFICE-contradictory;
- total: 1 office-like, 3 institutional/daytime-compatible, 2 OFFICE-contradictory, 3 indeterminate.

The single office-like imagery case belongs to margin-near. It matches HoWDe, but fails recurrence, both split tests, and held-out top-1. Dropout retention is 0.778. It is BCL-evaluable, with no BCL work-compatible or business-name support within 100/150 m.

The three share-near institutional/daytime-compatible cases show stronger but heterogeneous behavior:
- HoWDe match: 2/3;
- recurrence match: 0/3;
- both split tests: 1/3;
- held-out top-1: 2/3;
- median dropout retention: 1.0;
- BCL evaluable: 1/3;
- BCL work-compatible or business-name support within 100/150 m: 0/3.

Overall near-miss policy snapshot:
- 9 near-miss users;
- both split tests: 1/9;
- held-out exact-candidate top-1: 2/9;
- perfect dropout retention: 5/9;
- BCL evaluable: 2/9;
- BCL work-compatible context within 150 m: 0/9.

Decision:
- keep the production OFFICE baseline frozen at 16 users;
- do not relax the global margin threshold;
- do not relax the global OFFICE-share threshold;
- keep all nine one-step near-miss candidates in abstention / research-audit status;
- treat historical imagery as contextual evidence only, not as an override of behavioral robustness.

Stage 07l closes the current OFFICE-expansion investigation as a negative policy result.


## 2026-10-05 — Stage 07m Trackintel semantic-only parity added

Stage 07l closed the current OFFICE-expansion investigation with the frozen
production baseline remaining at 16 users.

The next methodological question is different: whether the production
HOME/OFFICE candidate identities agree with an independent open-source
implementation when stay detection and spatial location identity are held
fixed.

Stage 07m was added as a semantic-only Trackintel comparator.

Frozen input / namespace:

- 5,821 CP1 stays / 136 users;
- CP2-v2 per-stay IANA timezone handling;
- complete-link 200 m production location namespace;
- expected 2,015 semantic locations;
- expected 716 recurring locations / 104 users;
- frozen production parity 27 HOME / 16 OFFICE.

Comparator:

- Trackintel pinned at 1.4.2;
- FREQ;
- OSNA;
- native Trackintel pre-filter disabled for the primary comparison so the
  experiment isolates semantic selection rather than an additional eligibility
  gate.

Because CP2-v2 allows different IANA timezones per stay, Stage 07m adapts each
local wall-clock start into a dummy UTC timestamp while preserving true elapsed
duration. These timestamps are semantic-clock carriers only, not physical UTC
times. A finish-wall delta diagnostic audits DST-sensitive cases.

Primary outputs:

- production-vs-Trackintel agreement summary;
- both-same / both-different / production-only / comparator-only status counts;
- frozen HOME-27 and OFFICE-16 reference agreement;
- Trackintel FREQ-vs-OSNA internal agreement;
- optional exact-WORK-candidate comparison for the nine Stage-07j near-miss
  users when the existing private Stage-07j panel is present.

No comparator outcome changes production thresholds. Trackintel agreement is
methodological convergence, not semantic ground truth.

New files:

- `analysis/07m_trackintel_semantic_parity.py`;
- `notebooks/07m_trackintel_semantic_parity.ipynb`;
- `tests/test_trackintel_semantic_parity.py`;
- `docs/eda/37_trackintel_semantic_parity.md`;
- `docs/07m_trackintel_semantic_parity_handoff.md`.

Next action: run Stage 07m on the existing Modal Volume and inspect candidate
agreement before implementing an end-to-end Trackintel pipeline comparator.


## 2026-10-05 — Stage 07m measured Trackintel semantic-parity result

Stage 07m ran successfully on `main` at `5e4b157` with
`trackintel==1.4.2`.

Frozen reproduction and adapter gates passed:

- 5,821 CP1 stays / 136 users;
- 2,015 semantic locations;
- 716 recurring locations / 104 recurring-location users;
- production HOME 27 / OFFICE 16;
- Trackintel adapter rows 5,821;
- local-wall adapter finish delta nonzero: 0.

Trackintel coverage with `pre_filter=False`:

- FREQ: HOME 136, WORK 117;
- OSNA: HOME 104, WORK 99.

HOME candidate identity is strongly convergent:

- FREQ matches 24/27 frozen HOME candidates exactly (88.9%);
- OSNA matches 27/27 exactly (100%);
- OSNA selects HOME for 104 users, so the frozen 27-user production HOME set is
  a strict support-qualified subset rather than a different semantic rule.

OFFICE/WORK is substantially less convergent:

- FREQ selects WORK for all 16 production OFFICE users but matches the exact
  candidate in only 3/16 (18.8%);
- OSNA selects WORK for 15/16 production OFFICE users and matches 11/16 exact
  production candidates (68.8% of the production reference; 11/15 among jointly
  selected users = 73.3%);
- one frozen production OFFICE user is not selected as WORK by OSNA;
- four jointly selected production OFFICE users receive a different OSNA WORK
  location.

Trackintel methods also disagree internally:

- HOME: FREQ and OSNA both select 104 user-label rows and choose the same
  location for 68/104 (65.4%);
- OFFICE: both select 93 user-label rows but choose the same location for only
  31/93 (33.3%).

Stage-07j near-miss diagnostic:

- FREQ selects WORK for all 9 near-miss users but matches the audited candidate
  for only 2/9: 0/2 margin-near and 2/7 share-near;
- OSNA selects WORK for all 9 near-miss users and matches the audited candidate
  for 6/9: 1/2 margin-near and 5/7 share-near.

Interpretation:

- HOME has strong independent semantic-method convergence, especially against
  OSNA;
- OFFICE is intrinsically more ambiguous under established heuristic methods;
- the fact that OSNA selects 99 WORK users and matches 6/9 one-step near-miss
  candidates demonstrates semantic plausibility, not production reliability;
- the frozen OFFICE abstention policy remains justified because Stage 07j/07l
  showed that most near-miss candidates do not jointly satisfy recurrence,
  split, held-out, and independent-context evidence.

Decision:

- keep HOME 27 / OFFICE 16 frozen;
- do not promote any Stage-07j near-miss from Trackintel agreement alone;
- use Stage 07m as independent-method validation of the semantic family, not as
  threshold calibration;
- proceed next to the end-to-end Trackintel pipeline comparator only as a
  separate decomposition experiment.


## 2026-10-05 — Stage 07n Trackintel end-to-end comparator added

Stage 07m showed strong independent semantic convergence for HOME and partial,
method-sensitive convergence for OFFICE while holding CP1 stays and CP2-v2
locations fixed.

Stage 07n now deliberately changes the upstream representation and runs
Trackintel end to end from the raw GeoLife release:

```text
raw GeoLife
→ Trackintel read_geolife
→ Trackintel sliding staypoints
→ Trackintel DBSCAN locations
→ per-stay IANA local wall clock
→ Trackintel OSNA
→ spatial / temporal decomposition against frozen CP1 + CP2-v2
```

Runtime design:

- process one user at a time to avoid loading all 24.9M raw points into memory;
- cache per-user Trackintel-derived outputs under the Modal Volume;
- raw GPS points are never persisted by Stage 07n;
- reruns resume from completed user caches.

Frozen raw / production gates:

- 182 raw users;
- 18,670 trajectory files;
- 24,876,978 raw points reconciled through Trackintel's reader;
- 5,821 frozen CP1 stays / 136 stay users;
- 2,015 production semantic locations;
- HOME 27 / OFFICE 16.

Trackintel staypoint thresholds are aligned to CP1:

- 200 m distance;
- 20 min dwell;
- 5 min gap;
- include_last=False.

The same Trackintel stay inventory is clustered with DBSCAN at 100 m and 200 m,
both with num_samples=1. This is a representation comparator, not a claim that
either DBSCAN setting is optimal.

The stage decomposes differences into three layers:

1. reciprocal CP1-vs-Trackintel staypoint overlap / center agreement;
2. nearest production-vs-Trackintel location geometry at 50/100/200 m;
3. OSNA HOME/WORK candidate center distance against production HOME/OFFICE.

OSNA receives per-stay local wall-clock time resolved from each Trackintel
staypoint center and runs with pre_filter=False so extra Trackintel eligibility
thresholds do not confound decomposition.

New files:

- `analysis/07n_trackintel_end_to_end.py`;
- `notebooks/07n_trackintel_end_to_end.ipynb`;
- `tests/test_trackintel_end_to_end.py`;
- `docs/eda/38_trackintel_end_to_end.md`;
- `docs/07n_trackintel_end_to_end_handoff.md`.

Stage 07n is diagnostic only. Integer location ids are never compared across
pipelines, and no result changes the frozen HOME 27 / OFFICE 16 policy.


## 2026-10-05 — Stage 07n measured Trackintel end-to-end result

Stage 07n executed successfully on `main` at `5bd2920` with
`trackintel==1.4.2`.

All raw / production gates passed:

- 182 raw users;
- 18,670 trajectory files;
- Trackintel raw-reader reconciliation: 24,876,978 points;
- 5,821 frozen CP1 stays / 136 stay users;
- 2,015 production semantic locations;
- production HOME 27 / OFFICE 16.

Trackintel end-to-end pipeline output:

- 2,157 staypoints / 125 users;
- DBSCAN-100: 1,237 locations, 247 recurring locations / 75 users;
- DBSCAN-200: 1,113 locations, 264 recurring locations / 81 users;
- all 2,157 Trackintel stays resolved to IANA timezone;
- 18 distinct timezones.

The main decomposition result begins at stay extraction.

Reciprocal strong-stay matching, defined as >=50% overlap of the shorter stay
and center distance <=200 m:

- CP1 -> Trackintel: 2,125 / 5,821 = 36.5%;
- Trackintel -> CP1: 2,088 / 2,157 = 96.8%.

Trackintel therefore detects a much smaller stay inventory, but almost every
Trackintel stay corresponds to a CP1 stay. The dominant observed end-to-end
difference starts upstream: Trackintel behaves approximately like a strict
subset of the frozen CP1 inventory under the threshold-aligned 200 m / 20 min /
5 min configuration.

The Trackintel staypoint generator also emitted warnings that duplicate
positionfixes were dropped before stay extraction. This is part of the
independent implementation contract and is one possible contributor to the
inventory difference; Stage 07n does not isolate its effect separately.

Location geometry remains substantially aligned once stays exist.

For the 716 recurring production locations, nearest Trackintel location within
200 m:

- DBSCAN-100: 559 / 716 = 78.1%, median nearest distance 36.4 m;
- DBSCAN-200: 530 / 716 = 74.0%, median nearest distance 49.3 m.

DBSCAN-100 is slightly closer to the production complete-link geometry by these
nearest-anchor diagnostics, despite the production 200 m maximum-diameter
contract. This reinforces that DBSCAN epsilon and complete-link diameter are not
interchangeable parameters.

End-to-end OSNA semantic correspondence:

- DBSCAN-100 HOME: 19 / 27 production HOME within 200 m = 70.4%;
- DBSCAN-200 HOME: 21 / 27 within 200 m = 77.8%;
- DBSCAN-100 OFFICE: 9 / 16 production OFFICE within 200 m = 56.3%;
- DBSCAN-200 OFFICE: 9 / 16 within 200 m = 56.3%.

Trackintel selects 92 HOME and 85 WORK users end to end. For production-emitted
users, both pipelines select a candidate for 26/27 HOME and 15/16 OFFICE users.

Comparison with Stage 07m is the important control:

- with stays and location namespace held fixed, OSNA matched production HOME
  27/27 exactly and OFFICE 11/16 exactly;
- after replacing stay extraction + clustering with Trackintel, HOME spatial
  correspondence falls to 21/27 at the better DBSCAN-200 setting and OFFICE to
  9/16.

Interpretation:

- the large end-to-end divergence is already present before OSNA because the
  Trackintel stay inventory is much smaller;
- clustering introduces a secondary representation difference but most
  recurring production anchors still have a nearby Trackintel anchor;
- HOME remains more robust across implementations than OFFICE;
- OFFICE remains method- and representation-sensitive and still requires the
  production abstention / robustness framework.

Decision:

- keep HOME 27 / OFFICE 16 frozen;
- do not reinterpret Stage 07n as accuracy;
- do not retune stay, clustering, HOME, or OFFICE thresholds from this
  comparator;
- treat Stage 07n as evidence that the production method and Trackintel share
  substantial significant-place structure while differing materially in
  upstream stay inventory construction.


## 2026-10-05 — Stage 07o literature comparator suite added

After Stage 07m (semantic-only Trackintel parity) and Stage 07n (end-to-end
Trackintel decomposition), Stage 07o adds a broader literature comparator suite
while holding the frozen CP1 stays and CP2-v2 location namespace fixed.

Comparators:

- scikit-mobility 1.3.1 HOME rule, implemented as a source-equivalent
  `home_location` replica using 22:00-07:00 visit frequency;
- Kabiri et al. (arXiv:2302.14742) monthly hierarchical geohash HOME, preserving
  the level-6 -> level-7 support/ranking logic and 21:00-06:00 night window;
- Pavan et al. (MDM 2015) important-location feature space using area,
  intensity/time-spent, and frequency/visit-count dimensions;
- SCITEPRESS/MATEC 2018 work-rest comparator generalized from the paper's
  top-two-region demonstration with 00:00-06:00 Home and 08:00-18:00 Work.

Adaptation boundaries are explicit.

The geohash paper expects raw sightings. Stage 07o uses one observation per
occupied frozen stay-hour and runs the method separately per user-month. Because
GeoLife spans multiple years, user-level comparison uses a declared
project-specific modal level-7 aggregation across qualifying months.

Pavan's accessible abstract does not expose a unique reproducible classifier.
The stage therefore does not invent an importance score. Production
`total_dwell_h` and `stay_count` implement intensity/frequency; a transparent
circular area proxy is derived from production location diameter.

The SCITEPRESS source reports one GeoLife user over seven days and includes ADPC
clustering + reverse geocoding. Stage 07o only generalizes the work-rest ranking
component on the already-frozen production location namespace and labels it a
style comparator.

The notebook retains the frozen gates:

- 5,821 CP1 stays / 136 users;
- 2,015 semantic locations;
- 716 recurring locations / 104 users;
- HOME 27 / OFFICE 16.

Optional Stage-07j integration compares the SCITEPRESS-style WORK candidate
against the fixed nine OFFICE near-miss candidates.

New files:

- `analysis/07o_literature_comparator_suite.py`;
- `notebooks/07o_literature_comparator_suite.ipynb`;
- `tests/test_literature_comparator_suite.py`;
- `docs/eda/39_literature_comparator_suite.md`;
- `docs/07o_literature_comparator_handoff.md`.

Stage 07o remains diagnostic only. Agreement is methodological convergence, not
accuracy, and no comparator output changes HOME 27 / OFFICE 16.


## 2026-10-05 — Stage 07o measured literature-comparator result

Stage 07o executed successfully on `main` at `f7cbf02` with no traceback.

Frozen gates passed:

- 5,821 CP1 stays / 136 users;
- 2,015 semantic locations;
- 716 recurring locations / 104 users;
- production HOME 27 / OFFICE 16.

Observation adapters:

- 5,821 stay-arrival observations;
- 9,244 stay-hour observations;
- both cover all 136 stay users.

### scikit-mobility 1.3.1 HOME rule

The source-equivalent 22:00-07:00 visit-frequency comparator selected HOME for
all 136 users.

Against the frozen HOME-27 reference:

- jointly selected: 27/27;
- exact production location match: 26/27 = 96.3%;
- 40/136 comparator users had no nighttime stay-arrival observation and used the
  library's fallback to overall most-frequent location.

This is strong HOME-method convergence despite the comparator's intentionally
broad coverage.

### arXiv:2302.14742 geohash HOME adaptation

The stay-hour adaptation observed 591 user-months.

Strict monthly support filters produced:

- 69 qualifying user-month HOME candidates;
- 40 users with at least one qualifying monthly HOME;
- median qualifying months per selected user: 1;
- median modal-month share: 1.0.

Against production HOME:

- comparator selected: 40 users;
- jointly selected production HOME users: 21/27;
- within 50 m: 14;
- within 100 m: 20;
- within 200 m: 20.

Therefore coverage is limited, but conditional agreement is strong:
20/21 jointly selected production HOME users = 95.2% within 200 m.

### Pavan area / intensity / frequency audit

Production roles occupy a substantially stronger important-location feature
region than other recurring locations.

Median feature values:

- HOME (26 standalone locations): 21.74 dwell hours, 34.5 visits, 11 active
  local dates;
- OFFICE (15 standalone locations): 7.62 dwell hours, 15 visits, 6 active local
  dates;
- OTHER_RECURRING (674 locations): 1.38 dwell hours, 2 visits, 2 active local
  dates;
- one production location is jointly labeled HOME+OFFICE and has 49.38 dwell
  hours, 83 visits, and 24 active local dates.

Within-user rank audit:

- standalone HOME: 23/26 are top-1 in both total dwell and visit frequency;
- standalone OFFICE: 11/15 are top-1 in both total dwell and visit frequency;
- the shared HOME+OFFICE location is top-1 in both.

This supports the interpretation that emitted semantic places occupy the high
intensity / high frequency portion of the recurring-location space without
inventing a Pavan classifier.

### SCITEPRESS-style work-rest comparator

The generalized top-two-region comparator selected HOME and WORK for 117 users.

Against production:

- HOME exact match: 25/27 = 92.6%;
- OFFICE exact match: 15/16 = 93.8%.

However, 71/117 comparator users receive the same candidate for both HOME and
WORK. This shows that high agreement on the narrow production reference can
coexist with poor semantic separation under a simple broad-coverage heuristic.

Stage-07j near-miss WORK diagnostic:

- margin-near: 0/2 exact;
- share-near: 5/7 exact.

The 5/7 share-near result independently echoes Trackintel OSNA's Stage-07m
finding that many share-near candidates are temporally plausible WORK
locations. It does not override their weak recurrence/split/held-out/context
robustness from Stage 07j/07l.

Decision:

- keep HOME 27 / OFFICE 16 frozen;
- treat the multi-method HOME convergence as positive methodological support;
- treat SCITEPRESS/OSNA agreement on share-near as semantic plausibility only;
- do not promote near-miss users or widen gates;
- Stage 07o completes the planned literature comparator suite without revealing
  a reason to change production policy.


## 2026-10-05 — Stage 07p final methodological synthesis added

Stage 07p closes the current CP2-v2 HOME/OFFICE validation track by synthesizing
already-measured aggregate evidence from Stage 05 and Stages 07i-07o.

It does not rerun raw GPS processing and does not introduce a new threshold,
semantic classifier, or external evidence source.

Inputs are aggregate CSVs from:

- Stage 05 internal HOME/OFFICE reliability;
- Stage 07i OFFICE threshold sensitivity;
- Stage 07j targeted OFFICE near-miss robustness;
- Stage 07l imagery / behavior / BCL unblinding;
- Stage 07m Trackintel semantic-only parity;
- Stage 07n Trackintel end-to-end decomposition;
- Stage 07o literature comparator suite.

The synthesis notebook first hard-validates representative accepted measurements
from every stage. If the cached lineage no longer matches the measured results,
the notebook stops.

Main outputs:

- HOME evidence ladder;
- OFFICE evidence ladder;
- near-miss policy summary;
- upstream/semantic pipeline-sensitivity summary;
- final production-policy snapshot;
- supported / unsupported claim boundary.

The final policy expected from this synthesis remains:

```text
HOME   = 27
OFFICE = 16

change_home_gate   = False
change_office_gate = False
promote_near_miss  = False
```

No evidence family is collapsed into a composite accuracy score.

New files:

- `analysis/07p_methodological_synthesis.py`;
- `notebooks/07p_methodological_synthesis.ipynb`;
- `tests/test_methodological_synthesis.py`;
- `docs/eda/40_methodological_synthesis.md`;
- `docs/07p_methodological_synthesis_handoff.md`.

Next action: run Stage 07p on the existing Modal Volume. If measured-lineage
validation passes and the final policy snapshot reproduces the frozen decision,
the current CP2-v2 validation track can be closed.


## 2026-10-05 — Stage 07p measured synthesis passed; CP2-v2 validation track closed

Stage 07p was rerun successfully on `main` at `649f805` after correcting the
Stage-05 HOME 30% dropout lineage expectation.

The final execution contains no traceback and completes all aggregate writes to:

```text
/mnt/geolife-data/cache/cp2_v2/07p_methodological_synthesis/
```

Measured-lineage validation passed all 33 checks spanning Stage 05 and
Stages 07i-07o.

Key reproduced values include:

- HOME fixed-vs-recurrence exact: 35/42;
- OFFICE fixed-vs-recurrence exact: 6/25;
- HOME held-out top-1: 50.0%;
- OFFICE held-out top-1: 42.1%;
- HOME 30% dropout retention: 81.746%;
- OFFICE 30% dropout retention: 78.889%;
- frozen OFFICE baseline: 16;
- margin relaxation: 18;
- share relaxation: 23;
- Stage-07l near-miss snapshot: 9 users, 1 both-split exact, 2 held-out top-1,
  0 BCL work-context support within 150 m;
- Stage-07m OSNA exact: HOME 27/27, OFFICE 11/16;
- Stage-07n end-to-end within 200 m: HOME 21/27, OFFICE 9/16;
- Stage-07o literature agreement: scikit HOME 26/27, SCITEPRESS HOME 25/27,
  SCITEPRESS OFFICE 15/16, geohash HOME 20/27 within 200 m.

Final production-policy snapshot reproduced exactly:

```text
HOME = 27
OFFICE = 16

change_home_gate   = False
change_office_gate = False
promote_near_miss  = False

final_policy = freeze_HOME_27_OFFICE_16
```

The final claim boundary also reproduced as intended:

Supported:

- HOME candidate identity converges strongly across multiple heuristic families;
- OFFICE is more method- and representation-sensitive than HOME;
- the OFFICE gate is conservative in coverage;
- Trackintel end-to-end disagreement is driven substantially by upstream stay
  inventory construction;
- several share-near OFFICE candidates are temporally plausible but not robust
  enough for production.

Not supported:

- GeoLife provides known HOME/OFFICE semantic accuracy;
- POI or imagery context proves employment;
- external comparator outputs are ground truth;
- near-miss candidates should be promoted from comparator agreement alone.

Decision: the current CP2-v2 HOME/OFFICE validation track is closed with
HOME 27 / OFFICE 16 frozen.


## 2026-10-05 — Stage 08a HOME coverage expansion added

After Stage 07p closed the validated production core at HOME 27 / OFFICE 16,
Stage 08a starts a separate HOME coverage-expansion track.

The search space is not the full set of non-HOME users.

Stage 05b had already identified only two non-production HOME candidates that
were unique HIGH/MEDIUM consensus winners:

- one HIGH fixed candidate not emitted;
- one MEDIUM fixed candidate not emitted.

Stage 08a therefore audits exactly those two candidates.

Internal evidence is inherited from Stage 05b:

- >=2 HOME method votes;
- HIGH/MEDIUM unique winner;
- >=2/3 reliability axes among split, held-out top-1 and 30% dropout.

Later independent evidence is added from:

- Stage 07m Trackintel OSNA exact candidate;
- Stage 07m Trackintel FREQ exact candidate;
- Stage 07o scikit-mobility-style HOME exact candidate;
- Stage 07o SCITEPRESS-style HOME exact candidate;
- Stage 07o geohash HOME spatial distance;
- Stage 07n Trackintel end-to-end HOME spatial distance under DBSCAN-100/200.

Predeclared expansion tiers:

- HOME_PROBABLE:
  - internal HIGH/MEDIUM floor;
  - no production-OFFICE collision;
  - at least two exact confirmations among Trackintel OSNA, scikit HOME and
    SCITEPRESS HOME;
- HOME_PLAUSIBLE:
  - same internal floor;
  - no production-OFFICE collision;
  - partial exact or auxiliary spatial support;
- ABSTAIN:
  - insufficient or conflicting evidence.

Trackintel FREQ and different-namespace spatial comparators remain auxiliary and
cannot alone create HOME_PROBABLE.

Stage 08a does not change production HOME. It creates an optional downstream
tiered label layer:

```text
HOME_HIGH_CONFIDENCE_CORE = 27
HOME_PROBABLE_NEW         = measured after execution
HOME_PLAUSIBLE_NEW        = measured after execution
```

New files:

- `analysis/08a_home_coverage_expansion.py`;
- `notebooks/08a_home_coverage_expansion.ipynb`;
- `tests/test_home_coverage_expansion.py`;
- `docs/eda/41_home_coverage_expansion.md`;
- `docs/08a_home_coverage_expansion_handoff.md`.
