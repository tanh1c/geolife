# Stage 07d — Historical Context Enrichment

## Motivation

Measured Stage 07c found 225 recurring non-HOME anchors across 25 users.

Median observation-year distribution:

- 2008: 72 anchors;
- 2009: 136;
- 2010: 1;
- 2011: 10;
- 2012: 6.

Therefore 208 / 225 anchors (92.4%) are in 2008–2009.

This makes exact-year physical context plus early historical cross-checks higher priority than Gaode/Baidu ingestion.

## Primary source — CLCD

Stage 07d uses the pinned CLCD v1.0.2 Zenodo record as the primary runnable source.

The record states that the files are Cloud Optimized GeoTIFFs.

For each anchor:

1. use the anchor median observation year;
2. remote-open the corresponding annual COG;
3. sample the point pixel;
4. sample 3×3 and 5×5 local windows;
5. record local modal classes and point/window agreement.

CLCD classes remain physical land-cover classes only:

- cropland;
- forest;
- shrub;
- grassland;
- water;
- snow/ice;
- barren;
- impervious;
- wetland.

Impervious must never be converted directly into office, residential, education, healthcare, or WORK semantics.

### Why local windows?

GeoLife recurring locations are represented at a much coarser spatial tolerance than one 30 m land-cover pixel.

A point-only lookup could therefore overreact to raster registration, boundary placement, or anchor-center uncertainty.

Point vs 3×3 / 5×5 agreement is an explicit spatial-sensitivity audit.

## Historical OSM cross-check — ohsome

ohsome is optional and cross-check-only.

For each anchor:

- snapshot date = median anchor observation date;
- AOI = a small WGS84 bounding box around the anchor;
- extract only semantically relevant historical OSM features;
- preserve multi-label context categories.

The ohsome cross-check uses the existing Modal secret named `ohsome-api`, which must contain `OHSOME_API_KEY`. The key is injected only into a remote Modal function that performs the HTTP request; it is not exposed to or printed by the notebook process.

Historical OSM absence remains missing mapping evidence, not proof that a real-world feature did not exist.

## BCL POI 2008

BCL POI 2008 remains the highest-leverage blocked semantic source:

- 72 exact-year 2008 anchors;
- 136 one-year-proxy 2009 anchors;
- 208 / 225 anchors in total.

The current BCL page documents a Figshare DOI but lists no downloadable file attachment. Stage 07d therefore does not pretend the dataset is programmatically available.

BCL ingestion remains blocked until the exact file, reuse rights, and CRS are verified.

## Outputs

Private:

- clcd_anchor_context_private.pkl
- ohsome_anchor_context_private.pkl when available;
- ohsome_request_log_private.pkl;
- historical_context_private.pkl.

Aggregate:

- clcd_sampling_plan.csv;
- clcd_population_summary.csv;
- clcd_class_summary.csv;
- ohsome_summary.csv when available.

## Semantic boundary

Stage 07d adds external physical/context evidence only.

It does not infer occupation, employment status, true WORK, OFFICE identity, or functional semantic ground truth from CLCD.

## Free-tier ohsome execution policy

Measured execution returned HTTP 429 Too Many Requests on the free-tier API key.

Stage 07d therefore treats ohsome as resumable partial evidence rather than an all-or-nothing dependency.

Default notebook policy:

- sequential requests only;
- 6 s pause between newly fetched anchor requests;
- maximum 20 new requests per notebook run;
- successful Parquet responses cached by deterministic request hash;
- first 429 stops additional fresh requests for that run;
- cached anchors continue to be parsed;
- remaining anchors are marked deferred rather than failed;
- CLCD results and partial ohsome outputs are saved even when the quota is exhausted.

The defaults can be tuned with:

- OHSOME_MAX_NEW_REQUESTS_PER_RUN
- OHSOME_REQUEST_PAUSE_S

Do not increase these merely to maximize throughput. ohsome is a secondary historical cross-check and should respect API quota.

