# Stage 07e — Offline Semantic Distance + Mobility Alignment

## Purpose

Stage 07d established full historical-context coverage for 225 recurring non-HOME anchors across 25 users:

- CLCD exact-year physical context: complete;
- historical OSM / ohsome: 225 / 225 anchors cached.

Stage 07e does **not** call external APIs. It reuses the complete historical OSM cache to ask a narrower question:

> Are the mobility-derived anchor roles aligned with independently mapped historical context more strongly than same-user peer anchors?

This is still an evidence audit, not semantic label production.

## Inputs

Required private artifacts:

- Stage 07d `historical_context_private.pkl`;
- Stage 07d `ohsome_request_log_private.pkl`;
- Stage 07d `ohsome_raw/*.parquet` full cache;
- Stage 05b `adaptive_work_patterns_42_private.pkl`;
- Stage 07b `factorized_work_profiles_private.pkl`.

No API key is required.

## Full-cache gate

07e rejects partial ohsome coverage.

Every target anchor must have exactly one successful `cached` / `fetched` request-log row and a corresponding raw Parquet file.

This makes 07e deterministic and prevents quota-driven sampling from entering the semantic-distance audit.

## Feature geometry

ohsome feature extracts contain WGS84 geometry as WKB.

For each anchor, 07e:

1. decodes historical feature WKB;
2. transforms the small local neighborhood to an anchor-centred metre coordinate frame;
3. computes anchor-to-geometry distance;
4. falls back to the OSM feature bounding box only if WKB cannot be decoded.

Stage 07d queried an axis-aligned approximately ±100 m bounding box. Corners can exceed 100 m radial distance, so 07e explicitly thresholds by true geometry distance:

- <=25 m;
- <=50 m;
- <=100 m;
- no mapped matching feature within 100 m.

A feature returned in the bbox corner at >100 m is not counted as <=100 m evidence.

## Semantic categories

07e preserves the Stage-07d multi-label categories:

- residential;
- office/commercial;
- education;
- healthcare;
- industrial;
- retail/service;
- transport;
- civic/institutional;
- recreation/tourism.

Broad `work-compatible` context remains the union of:

- office/commercial;
- education;
- healthcare;
- industrial;
- retail/service;
- transport;
- civic/institutional.

This means only that mapped context is compatible with locations where work activity could occur. It is not a WORK/OFFICE label.

## Exact stable-secondary anchor

Stage 05b already records the dominant sliding-window non-HOME location as `dominant_location_id`.

07e marks an anchor as the stable-secondary candidate only when:

- `window_pattern == stable_secondary_anchor`; and
- anchor `location_id == dominant_location_id`.

No new anchor-ranking rule is introduced.

## Within-user comparison

For each stable-secondary user with at least one peer recurring non-HOME anchor, compare the candidate anchor against that user's other anchors.

Primary thresholds:

- mapped work-compatible context within 25 m;
- within 50 m;
- within 100 m.

For each user:

- candidate context indicator;
- peer-anchor context share;
- candidate minus peer share;
- candidate censored work-context distance;
- peer median censored distance;
- candidate unique/tied closest mapped work-compatible context.

The 100 m censored distance maps both no-detection and detections beyond 100 m to 100 m. It is a comparison device under the extraction boundary, not a claim that the true nearest feature is exactly 100 m away.

Aggregate paired differences use a deterministic user bootstrap. The stable-secondary cohort is small, so these intervals are descriptive uncertainty summaries, not calibrated semantic-accuracy intervals.

## Stage-07b alignment

07e also provides user-level descriptive mapped-context coverage for the existing factorized axes:

- site stable secondary;
- site multiple recurring;
- site adaptive multi-anchor;
- repeated route;
- shifted schedule evidence;
- mobility complexity;
- independent secondary evidence availability.

This section does not rank axes or create a composite work-regime score.

## Outputs

Private:

- `feature_semantic_distances_private.pkl`;
- `anchor_semantic_distances_private.pkl`;
- `mobility_aligned_semantic_context_private.pkl`;
- `stable_secondary_user_comparisons_private.pkl`.

Aggregate:

- `work_context_distance_buckets.csv`;
- `category_threshold_summary.csv`;
- `stable_secondary_within_user_summary.csv`;
- `stable_secondary_category_summary.csv`;
- `profile_axis_context_summary.csv`;
- `profile_axis_category_summary.csv`.

## Interpretation boundary

Historical OSM mapping is incomplete in early China.

Therefore:

- no mapped feature within 100 m != real-world absence;
- work-compatible mapped context != WORK/OFFICE;
- residential mapped context != HOME;
- no occupation or employment-status inference is allowed.

Stage 07e can strengthen or weaken consistency between mobility geometry and historical mapping evidence. It cannot independently establish semantic workplace ground truth.

Category-specific paired summaries are included so a composite work-compatible result can be decomposed into office/commercial, education, healthcare, industrial, retail/service, transport, civic/institutional, residential, and recreation/tourism context rather than being interpreted as one opaque score.

### Raw cache vs request-log provenance

Stage 07d can be completed by rerunning only the OSM fetch cell. In that workflow the raw `ohsome_raw/*.parquet` cache may reach full 225/225 coverage while the persisted `ohsome_request_log_private.pkl` remains from an earlier partial run.

Stage 07e therefore recomputes each deterministic Stage-07d request body and cache key from the anchor table and validates the corresponding raw Parquet file directly. The request log is audit metadata only and is never used as the coverage source of truth.

## Correctness correction: Stage-05b and Stage-07c location ids must share one namespace

The first 07e run exposed a namespace mismatch:

- Stage 05b dominant secondary ids came from production semantic locations;
- old Stage 07c anchors came from behavior-cluster locations.

The two pipelines both used complete-link 200 m but assign ids differently and do not share the same preprocessing universe. Integer `location_id` equality was therefore invalid.

Stage 07e now requires the explicit production namespace marker and rejects old artifacts. The first measured 07e tables are superseded pending corrected 07c -> 07d -> 07e rerun.

## Final measured result — corrected production-aligned universe

Stage 07e completed cleanly on the corrected 198-anchor / 25-user universe with:

- location namespace: `production_complete_link_200m_beijing_policy_v1`;
- raw cache validated: 198 / 198 anchors;
- exact stable-secondary users represented: 9;
- exact stable-secondary anchors: 9;
- within-user comparison rows: 9.

### Exact radial historical-OSM context

The Stage-07d OSM existence summary used the extraction bbox. Stage 07e applies true anchor-to-geometry radial distance, so features returned in bbox corners at >100 m are not counted.

Measured within <=100 m:

- semantic context: 61 / 198 anchors (30.81%);
- broad work-compatible context: 46 / 198 anchors (23.23%).

Work-compatible distance buckets:

| bucket | anchors | users | anchor share |
|---|---:|---:|---:|
| 0–25 m | 31 | 9 | 15.66% |
| 25–50 m | 5 | 5 | 2.53% |
| 50–100 m | 10 | 7 | 5.05% |
| none within 100 m | 152 | 25 | 76.77% |

Category coverage within 100 m:

- education: 33 anchors;
- recreation/tourism: 14;
- retail/service: 14;
- residential: 6;
- office/commercial: 2;
- transport: 2;
- healthcare: 1;
- civic/institutional: 0;
- industrial: 0.

### Stable-secondary within-user comparison

For all 9 stable-secondary users, the exact Stage-05b dominant secondary anchor was found in the corrected anchor universe.

Composite work-compatible context:

| threshold | candidate-context users | mean peer context share | mean candidate - peer share | bootstrap 95% interval |
|---|---:|---:|---:|---:|
| 25 m | 2 / 9 | 0.107 | +0.115 | [-0.109, +0.387] |
| 50 m | 2 / 9 | 0.141 | +0.081 | [-0.147, +0.337] |
| 100 m | 2 / 9 | 0.203 | +0.019 | [-0.210, +0.284] |

All three uncertainty intervals cross zero. Only 2 of 9 users have a candidate anchor with mapped work-compatible context at any tested threshold.

Category decomposition shows that those two candidate-context cases are both driven by the `education` category. None of the 9 stable-secondary candidate anchors has mapped `office_commercial`, `industrial`, `healthcare`, `retail_service`, `transport`, `civic_institutional`, `residential`, or `recreation_tourism` context within 100 m.

At 100 m, retail/service is actually more common among peer anchors than stable-secondary candidates:

- mean candidate - peer share = -0.081;
- bootstrap interval = [-0.135, -0.028].

This is a descriptive contrast in a tiny cohort, not evidence that stable-secondary anchors avoid retail locations.

### Decision

Historical OSM does not provide a strong independent semantic validation of stable-secondary anchors as WORK/OFFICE-like places.

The evidence is:

- sparse at the exact candidate anchors;
- dominated by education rather than office/commercial categories;
- not consistently stronger than same-user recurring peers;
- uncertainty crosses zero for the composite work-compatible comparison.

Therefore Stage 07e should close as a null/mixed independent-evidence result. Do not tune mobility thresholds to improve semantic agreement and do not promote stable-secondary geometry to WORK/OFFICE semantics.

The next semantic-source priority remains BCL POI 2008, now relevant to 185 / 198 corrected anchors across 19 users, after access/license/CRS resolution.



## CP2-v2 final Stage 07e result — 2026-10-04

Stage 07e was rerun after the CP2-v2 production-location refresh, the ohsome temporal-eligibility correction, the notebook-bootstrap fix, and the Stage-07b profile-axis merge correction.

The earlier 198-anchor Beijing-v1 result remains the corrected historical baseline. The measurements below are the final CP2-v2 result.

### Execution and coverage

The final notebook executed on repository commit `6804925` without traceback and saved all Stage-07e artifacts successfully.

Universe:

- full recurring non-HOME anchors: 298;
- users: 29;
- location namespace: `production_complete_link_200m_all_resolved_timezone_v2`;
- ohsome-eligible anchors: 296;
- pre-ohsome anchors retained as not eligible: 2;
- raw historical-OSM cache validated: 296 / 296 eligible anchors.

The two anchors before 2007-10-08 remain in the full anchor artifact but are excluded from historical-OSM absence/distance denominators.

### Exact radial historical-OSM context

Among the 296 OSM-eligible anchors:

- any semantic feature within 100 m: 86 / 296 = 29.05%;
- broad work-compatible feature within 100 m: 59 / 296 = 19.93%.

Corrected Beijing-v1 comparison:

| metric | corrected Beijing-v1 | CP2-v2 |
|---|---:|---:|
| OSM-eligible anchors | 198 | 296 |
| semantic <=100 m | 61 / 198 = 30.81% | 86 / 296 = 29.05% |
| work-compatible <=100 m | 46 / 198 = 23.23% | 59 / 296 = 19.93% |

The broader CP2-v2 universe therefore preserves a similar overall historical-semantic-context rate while slightly reducing the broad work-compatible share.

Work-compatible distance buckets among eligible anchors:

| bucket | anchors | users | share |
|---|---:|---:|---:|
| 0–25 m | 36 | 11 | 12.16% |
| 25–50 m | 8 | 8 | 2.70% |
| 50–100 m | 15 | 10 | 5.07% |
| none within 100 m | 237 | 29 | 80.07% |

Category coverage within 100 m:

- education: 33 anchors;
- recreation/tourism: 25;
- retail/service: 17;
- residential: 13;
- transport: 13;
- office/commercial: 4;
- healthcare: 1;
- industrial: 1;
- civic/institutional: 0.

Relative to the corrected Beijing-v1 result, the larger universe adds mapped recreation/tourism, residential, transport and retail/service context, while education remains exactly 33 anchors. Fine functional categories remain sparse.

### Stable-secondary within-user comparison

The exact Stage-05b stable-secondary candidate is represented for all 9 stable-secondary users:

- stable-secondary users represented: 9;
- exact stable-secondary anchors: 9;
- within-user comparison rows: 9.

Composite work-compatible context:

| threshold | candidate-context users | mean peer context share | mean candidate - peer share | bootstrap 95% interval |
|---|---:|---:|---:|---:|
| 25 m | 2 / 9 | 0.100 | +0.123 | [-0.108, +0.399] |
| 50 m | 2 / 9 | 0.134 | +0.088 | [-0.147, +0.349] |
| 100 m | 2 / 9 | 0.187 | +0.036 | [-0.201, +0.303] |

These values remain extremely close to the corrected Beijing-v1 comparison (+0.115 / +0.081 / +0.019), and all composite intervals still cross zero.

Category decomposition:

- both candidate-context cases are education;
- 0 / 9 stable-secondary candidates have office/commercial within 100 m;
- 0 / 9 have healthcare, industrial, retail/service, transport, civic/institutional, residential or recreation/tourism within 100 m.

At 100 m, retail/service remains more common among same-user peer anchors than stable-secondary candidates:

- mean candidate - peer share: -0.074;
- bootstrap 95% interval: [-0.125, -0.026].

This is a descriptive tiny-cohort contrast, not evidence that stable-secondary anchors avoid retail/service locations.

### Factorized mobility axes x mapped work-compatible context

After fixing the Stage-07c/Stage-07b profile-column merge collision, Stage-07b profile axes are read authoritatively.

Within the 29-user HOME-supported / recurring-non-HOME analysis universe:

| axis | users | users with any work-compatible context <=100m | share |
|---|---:|---:|---:|
| site_stable_secondary | 9 | 7 | 77.8% |
| site_multiple_recurring | 28 | 18 | 64.3% |
| site_adaptive_multi_anchor | 3 | 3 | 100% |
| route_repeated | 12 | 9 | 75.0% |
| schedule_shifted_evidence | 0 | 0 | n/a |
| mobile_complexity_evidence | 7 | 7 | 100% |
| independent_secondary_evidence_available | 7 | 5 | 71.4% |

These are descriptive user-level overlaps inside the Stage-07e analysis subset. They do not imply semantic WORK validity for any axis and must not be compared directly to whole-population Stage-07b axis prevalence without conditioning on the same 29-user subset.

### Final Stage 07e decision

The CP2-v2 expansion does not change the Stage-07e semantic conclusion.

1. Historical OSM remains incomplete mapping evidence, not ground truth.
2. Stable-secondary candidates are not consistently closer to work-compatible mapped context than same-user recurring peers.
3. All composite candidate-minus-peer bootstrap intervals cross zero.
4. Candidate-side mapped context remains driven entirely by education; no stable-secondary candidate has office/commercial context within 100 m.
5. Do not tune mobility thresholds against the external semantic source.
6. Do not promote stable-secondary geometry to WORK/OFFICE semantics.
7. Close the CP2-v2 production-dependent downstream refresh through Stage 07e.

The main robustness result is that the null/mixed independent semantic conclusion survives the expansion from the corrected 198-anchor Beijing-v1 universe to the 298-anchor CP2-v2 universe.


## Methodological reinterpretation — historical OSM as support-only

The measured Stage-07e tables remain valid as descriptions of what was mapped in historical OSM at each anchor's median observation date.

However, their semantic weight is revised.

The CP2-v2 OSM-eligible year distribution is:

- 2008: 93 anchors;
- 2009: 164;
- 2010: 6;
- 2011: 23;
- 2012: 10.

Thus 257 / 296 eligible anchors (86.8%) are queried at 2008–2009 OSM snapshots.

For this cohort, a missing historical OSM feature must be interpreted primarily as **historically unmapped / unavailable mapped evidence**, not as evidence that the real-world feature did not exist.

Consequences:

- positive mapped OSM context remains useful supporting evidence;
- OSM absence is not semantic negative evidence;
- an OSM candidate-minus-peer value below zero must not be read as a contradiction of contemporaneous BCL evidence;
- BCL POI 2008 is the primary historical functional-POI source for the GeoLife-heavy 2007–2009 period;
- CLCD remains physical-context evidence only.

No Stage-07e numeric result is deleted. The correction changes evidential interpretation, not the cached geometry/distance measurement.
