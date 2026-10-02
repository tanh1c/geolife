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

Set OHSOME_API_KEY as a Modal secret/environment variable.

Without a key, Stage 07d still completes the CLCD primary analysis.

## BCL POI 2008

Do not download a random mirror.

The official BCL page currently documents the dataset and Figshare DOI but lists no downloadable attachment.

Keep the semantic source blocked until the exact source file and its license/CRS are verified.

## Interpretation

CLCD = exact-year physical context.

ohsome = historical mapping cross-check.

Neither source creates occupation or OFFICE labels.
