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

