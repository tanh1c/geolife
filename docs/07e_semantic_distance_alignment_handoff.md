# Stage 07e handoff — Offline Semantic Distance + Mobility Alignment

## Run prerequisite

Stage 07d must have completed all 225 historical OSM anchor extracts.

Expected Stage-07d cache:

```text
/mnt/geolife-data/cache/07d_historical_context_enrichment/
  historical_context_private.pkl
  ohsome_request_log_private.pkl
  ohsome_raw/
    <cache_key>.parquet
    ...
```

07e validates complete coverage before doing any analysis.

## Runtime

No network source is queried.

The notebook:

1. checks all 225 target anchors have raw historical OSM cache files;
2. decodes cached WKB geometries;
3. calculates anchor-to-feature distances;
4. builds 25/50/100 m category evidence;
5. joins Stage-05b exact stable-secondary location IDs;
6. joins Stage-07b factorized user axes;
7. runs within-user stable-secondary vs recurring-peer comparison;
8. saves private and aggregate outputs.

The dev environment now includes Shapely for WKB geometry distance.

## What to send back after the run

The important aggregate notebook tables are:

- WORK-COMPATIBLE DISTANCE BUCKETS;
- CATEGORY x DISTANCE THRESHOLD;
- STABLE SECONDARY — WITHIN-USER COMPOSITE WORK-COMPATIBLE COMPARISON;
- STABLE SECONDARY — CATEGORY-SPECIFIC WITHIN-USER COMPARISON;
- STAGE-07b AXES x MAPPED WORK-COMPATIBLE CONTEXT <=100m;
- STAGE-07b AXES x CATEGORY CONTEXT <=100m.

Also send any traceback if the full-cache gate or WKB parser fails.

## Decision rule

The key result is not whether many anchors have work-compatible context.

The stronger independent-evidence question is:

> Across stable-secondary users, is the exact Stage-05b dominant secondary anchor more often / more closely aligned with mapped historical work-compatible context than the user's other recurring non-HOME anchors?

A useful positive signal would require consistency across thresholds and users, not one favorable percentage.

A null or mixed result should remain a negative result and should not trigger semantic threshold tuning.

## No production change

07e does not alter:

- CP1 cleaning/stay detection;
- frozen Home/Office production;
- Stage-05b anchor definitions;
- Stage-07b factorized profiles.

It is an external-context audit only.

## Important: stale Stage-07d request logs

A full raw cache can coexist with an older partial `ohsome_request_log_private.pkl` if Stage 07d was resumed by rerunning only the fetch cell without rerunning the save cell.

07e handles this correctly: it recomputes the exact Stage-07d request/cache key per anchor and checks `ohsome_raw/<cache_key>.parquet` directly. The log is audit-only.

If 07e reports `ohsome raw cache is incomplete`, that means Parquet files are genuinely missing. A low count of successful request-log rows alone is not a failure.

## Rerun prerequisite after namespace correction

The first 07e measured run must not be interpreted because its anchor universe came from the old behavior-location namespace.

Run in this order:

1. corrected 07c — production semantic locations;
2. corrected 07d — production-aligned coordinates, reuse existing ohsome raw cache by request hash;
3. corrected 07e — namespace assertion must pass.

Expected marker:

```text
production_complete_link_200m_beijing_policy_v1
```

Only the corrected rerun can be frozen as measured Stage-07e evidence.

## Final corrected measured handoff

Stage 07e completed on the production-aligned universe:

- 198 / 198 raw OSM caches validated;
- 25 users;
- 9 stable-secondary users;
- 9 exact stable-secondary anchors;
- 9 within-user comparisons.

Exact radial <=100 m historical-OSM context:

- 61 / 198 anchors have any semantic context;
- 46 / 198 have broad work-compatible context.

Stable-secondary candidates:

- 2 / 9 have mapped work-compatible context within 25 m;
- 2 / 9 within 50 m;
- 2 / 9 within 100 m.

Candidate-minus-peer mean differences are +0.115, +0.081, and +0.019 respectively, but all bootstrap 95% intervals cross zero.

Both candidate-context cases are `education`. No exact stable-secondary candidate has mapped office/commercial context within 100 m.

Decision: close Stage 07e as null/mixed independent semantic evidence. Do not create WORK/OFFICE labels from this result.

Next source priority: BCL POI 2008 acquisition / reuse-rights / CRS audit for the 185 / 198 corrected anchors that are temporally eligible.

