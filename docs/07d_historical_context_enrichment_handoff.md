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

