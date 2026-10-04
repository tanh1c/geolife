# Stage 07d handoff — Historical Context Enrichment

## Required input

Run Stage 07c first.

Required private artifact:

- anchor_observation_dates_private.pkl

This table already contains support-qualified recurring non-HOME anchors, exact coordinates, and anchor observation dates.

## CLCD runtime

The notebook installs rasterio and remote-samples annual CLCD Cloud Optimized GeoTIFFs.

No manual CLCD download is required for the default path.

The runner only opens the years actually present in the measured anchor set.

For the current result those are 2008, 2009, 2010, 2011, and 2012.

If remote COG access is unavailable in the runtime, do not silently substitute another land-cover product. Record the runtime/access failure and use a local CLCD file path only after the same source/version is obtained.

## ohsome runtime

Optional.

Use the existing Modal secret `ohsome-api` with required key `OHSOME_API_KEY`. The notebook attaches this secret to a small remote Modal function, so the notebook process never reads or prints the key.

## BCL POI 2008

Do not download a random mirror.

The official BCL page currently documents the dataset and Figshare DOI but lists no downloadable attachment.

Keep the semantic source blocked until the exact source file and its license/CRS are verified.

## Interpretation

CLCD = exact-year physical context.

ohsome = historical mapping cross-check.

Neither source creates occupation or OFFICE labels.

## Free-tier ohsome / 429 handling

The current key is free-tier and measured execution hit HTTP 429.

The runner is now resumable:

- every successful anchor response is cached under the Stage-07d cache;
- default fresh-request budget is 20 per run;
- default inter-request pause is 6 seconds;
- first 429 ends fresh requests for that run;
- partial context and request logs are still saved;
- rerunning later reuses cached anchors and continues with uncached ones.

Optional environment overrides:

- OHSOME_MAX_NEW_REQUESTS_PER_RUN
- OHSOME_REQUEST_PAUSE_S

A partial ohsome run is valid cross-check evidence only for the completed anchors. Do not report partial coverage as 225-anchor OSM coverage.

## Measured handoff — 2026-10-02

Stage 07d completed its primary objective.

CLCD:

- 225 anchors / 25 users processed;
- 224 known land-cover classes;
- 216 impervious anchors (96.0%);
- 223/225 point-vs-3x3 agreement;
- 222/225 point-vs-5x5 agreement.

This supports a strong built-up physical-context result while providing no fine functional semantics.

ohsome:

- 35 / 225 anchors completed;
- 15 cached + 20 newly fetched in the latest run;
- no 429 in the latest run;
- 190 deferred by the per-run free-tier request budget;
- 11/35 have semantic OSM context;
- 10/35 have broad work-compatible context;
- completed anchors cover only 3 users.

Do not interpret the partial ohsome proportions as population estimates. The completed set is sequential/quota-driven and user-concentrated.

Stage 07d can close without full ohsome completion because ohsome is explicitly secondary/cross-check-only.

Next semantic-source priority remains BCL POI 2008 access/license/CRS resolution.

## Final measured handoff — full ohsome completion

The historical OSM cross-check has now reached full coverage:

- 225 / 225 anchors completed;
- 25 / 25 users covered;
- 217 cached + 8 newly fetched in the final run;
- no rate-limit hit, deferral, request error, or parse error in the final run.

Full-universe historical OSM summary:

- 65 / 225 anchors (28.89%), 16 users: semantic context found;
- 48 / 225 anchors (21.33%), 14 users: broad work-compatible context;
- 8 / 225 anchors (3.56%), 2 users: residential context.

These are now candidate-universe descriptive proportions, but still not semantic ground truth because historical OSM coverage in early China is incomplete and subject to mapping lag.

Stage 07d is closed.

Next recommended stage: resolve BCL POI 2008 exact file access, reuse rights, and CRS, then evaluate whether a high-precision historical semantic join is feasible for the 208 anchors temporally covered by that source.

## Corrected location namespace requirement

Do not run Stage 07d from an old Stage-07c artifact lacking:

```text
location_namespace = production_complete_link_200m_beijing_policy_v1
```

HOME consensus and Stage-05b dominant secondary ids live in the production semantic-location namespace. Stage 07d now reconstructs coordinates from the same production location table.

If the namespace marker is absent or different, rerun corrected Stage 07c first.



## CP2-v2 measured handoff — 2026-10-04

Current production-aligned universe:

- 298 recurring non-HOME anchors / 29 users;
- namespace `production_complete_link_200m_all_resolved_timezone_v2`.

CLCD:

- 298 / 298 processed;
- 275 known point classes;
- 256 impervious;
- 294 point-vs-3x3 agreements;
- 290 point-vs-5x5 agreements.

Historical OSM:

- 296 anchors are temporally eligible;
- 2 anchors predate 2007-10-08 and are ineligible, not failed;
- 296 / 296 eligible anchors completed;
- 89 have semantic mapped context;
- 61 have broad work-compatible mapped context;
- 13 have residential mapped context.

BCL POI 2008 is no longer blocked on access/licence/CRS: Stage 07f verified the official Figshare file, CC BY 4.0, FileGDB container and EPSG:4326. Its current status is ready for normalization.

Stage 07e must use OSM eligibility-aware denominators. It must retain the two pre-ohsome anchors in the full anchor artifact while excluding them from OSM-distance absence/comparison denominators.
