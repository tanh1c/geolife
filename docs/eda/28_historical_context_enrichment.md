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

## Measured result — 2026-10-02

Stage 07d completed successfully on 225 recurring non-HOME anchors from 25 users.

### CLCD primary result

Coverage:

- known point land-cover class: 224 / 225 anchors (99.56%);
- unknown: 1 / 225;
- impervious: 216 / 225 anchors (96.0%);
- point class = 3x3 local modal class: 223 / 225 (99.11%);
- point class = 5x5 local modal class: 222 / 225 (98.67%).

Year/class distribution:

| year | class | anchors | users |
|---|---|---:|---:|
| 2008 | impervious | 70 | 11 |
| 2008 | water | 1 | 1 |
| 2008 | unknown | 1 | 1 |
| 2009 | impervious | 131 | 11 |
| 2009 | forest | 4 | 3 |
| 2009 | cropland | 1 | 1 |
| 2010 | cropland | 1 | 1 |
| 2011 | impervious | 10 | 4 |
| 2012 | impervious | 5 | 2 |
| 2012 | water | 1 | 1 |

Interpretation:

The recurring non-HOME anchor universe is overwhelmingly located on historically built-up / impervious land cover. The near-perfect point-vs-window agreement indicates that this finding is not driven by a fragile single-pixel lookup for almost all anchors.

This does NOT identify office, residential, school, hospital, WORK, or occupation. It only establishes a strong physical constraint: these anchors are overwhelmingly in built-up land rather than agriculture / forest / water / barren contexts.

### ohsome partial cross-check

Free-tier-safe execution completed:

- target anchors: 225;
- completed/cached historical OSM extracts: 35 (15.56%);
- cached before this run: 15;
- newly fetched this run: 20;
- rate-limit hits this run: 0;
- deferred by request budget: 190;
- request errors: 0;
- parse errors: 0.

Among the 35 completed anchors:

- semantic historical OSM context found: 11;
- broad work-compatible context: 10;
- residential context: 0.

Critical limitation:

The 35 completed anchors belong to only 3 users. This is a quota-driven, sequential partial sample, not a population-representative sample. The 31.4% semantic-context and 28.6% work-compatible shares must not be generalized to all 225 anchors or all 25 users.

Decision:

- CLCD is sufficient to close the Stage-07d physical-context objective.
- ohsome remains a cached/resumable cross-check that can accumulate opportunistically in later reruns.
- Full ohsome completion is not a gate for downstream work.
- Semantic enrichment priority remains BCL POI 2008 because it is temporally relevant to 208 / 225 anchors.

## Final measured result — full ohsome completion

A later free-tier-resumable run completed the historical OSM cross-check for the full Stage-07d anchor universe.

Coverage:

- anchor target: 225;
- anchor completed: 225;
- completion share: 100%;
- users covered: 25 / 25;
- cached before final run: 217;
- newly fetched in final run: 8;
- rate-limit hits in final run: 0;
- deferred anchors: 0;
- request errors: 0;
- parse errors: 0.

Full-universe ohsome context:

- semantic historical OSM context found: 65 / 225 anchors (28.89%), 16 users;
- broad work-compatible context: 48 / 225 anchors (21.33%), 14 users;
- residential context: 8 / 225 anchors (3.56%), 2 users.

Because coverage is now complete for the 225-anchor candidate universe, these proportions are descriptive of the Stage-07d candidate set rather than a quota-driven partial sample.

However, they remain historical-OSM mapping evidence, not ground-truth facility semantics. Early-China OSM incompleteness and mapping lag still mean:

- missing semantic context does not imply real-world absence;
- work-compatible tags do not prove that an anchor is WORK/OFFICE;
- residential tags do not prove HOME;
- no occupation or employment label is inferred.

Combined Stage-07d result:

- CLCD establishes that 216 / 225 anchors (96.0%) lie on impervious land with very high local spatial stability;
- historical OSM adds semantic-context evidence for 65 / 225 anchors;
- 48 / 225 anchors have at least one broad work-compatible historical OSM category.

Decision:

Stage 07d is complete. Do not spend more engineering effort on ohsome coverage for this candidate universe. The next highest-value semantic source remains BCL POI 2008 because Stage 07c showed temporal relevance to 208 / 225 anchors.

