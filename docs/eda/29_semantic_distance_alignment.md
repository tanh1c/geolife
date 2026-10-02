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
- `profile_axis_context_summary.csv`.

## Interpretation boundary

Historical OSM mapping is incomplete in early China.

Therefore:

- no mapped feature within 100 m != real-world absence;
- work-compatible mapped context != WORK/OFFICE;
- residential mapped context != HOME;
- no occupation or employment-status inference is allowed.

Stage 07e can strengthen or weaken consistency between mobility geometry and historical mapping evidence. It cannot independently establish semantic workplace ground truth.
