# Stage 07g — BCL POI 2008 production-Beijing normalization

## Purpose

Stage 07f verified the official BCL POI 2008 source and reached:

```text
runner_status = ready_for_normalization
```

Measured source/container:

- public Figshare record under CC BY 4.0;
- `Points of interest of China in 2008.rar`;
- extracted FileGDB `POI2008All.gdb`;
- layer `POI2008CN`;
- Point geometry;
- 6,039,158 features;
- EPSG:4326;
- fields `PNAME`, `X`, `Y`.

Stage 07g converts that validated national layer into a compact Parquet artifact aligned with the **same geographic policy used by production Home/Office inference**.

This is a normalization/QC stage, not a semantic label stage.

## Geographic definition

"Beijing" in this stage means the frozen CP2 production study region:

```text
center: 39.9042, 116.4074
radius: 100 km
```

It is not a Beijing administrative-boundary claim.

The values are read from `HomeOfficeConfig`; Stage 07g does not introduce a new geographic threshold.

## Two-stage spatial filter

### 1. Coarse GDAL bbox pushdown

The notebook computes the spherical bounding box enclosing the 100 km circle and runs `ogr2ogr -spat` against the FileGDB.

Only:

- `PNAME`;
- source `X`;
- source `Y`;
- point geometry as WKT

are staged.

This prevents all 6,039,158 national features from entering Python.

### 2. Exact Haversine filter

The worker streams the staged CSV in chunks and keeps only points satisfying:

```text
distance(point, production Beijing center) <= 100 km
```

The exact radial test is the population definition. The bbox is only query pushdown.

## Preserved output fields

The normalized Parquet contains:

```text
poi_id
pname_raw
geom_lon
geom_lat
raw_x
raw_y
distance_to_beijing_km
raw_geom_delta_m
source_year
source_layer
source_crs
```

Rules:

- `pname_raw` preserves BCL source text;
- `geom_lon/geom_lat` come from validated FileGDB geometry;
- `raw_x/raw_y` preserve source attribute values;
- `raw_geom_delta_m` measures consistency between the two representations;
- no lexical cleanup/category inference is introduced.

## Geometry and CRS authority

Stage 07f verified FileGDB geometry as EPSG:4326.

Therefore:

- FileGDB geometry is the spatial authority;
- raw `X/Y` are retained for source-QC comparison;
- a disagreement between geometry and raw X/Y must be reported, not silently resolved by replacing geometry.

## Memory / Modal design

No GPU is required.

The Modal worker installs:

- `gdal-bin`;
- numpy;
- pandas;
- pyarrow;
- duckdb.

The worker:

1. validates the existing GDB/layer/Point/EPSG contract;
2. writes a bbox-filtered CSV to container-local `/tmp`;
3. reads that staging CSV in 200k-row chunks;
4. exact-filters to 100 km;
5. writes ZSTD Parquet row groups directly to the persistent Volume;
6. runs duplicate/QC queries on the Parquet;
7. removes the staging CSV.

The national source is never materialized as a pandas DataFrame.

## Persistent paths

Input handoff:

```text
/mnt/geolife-data/cache/07f_bcl_poi_2008_acquisition/
  acquisition_manifest.json
  worker_report.json
```

Normalized output:

```text
/mnt/geolife-data/external/bcl_poi_2008/normalized/
  bcl_poi_2008_beijing_100km_v1.parquet
```

07g cache:

```text
/mnt/geolife-data/cache/07g_bcl_beijing_normalization/
  normalization_worker_result.json
  normalization_manifest.json
  normalization_qc_summary.csv
  normalization_decision.csv
  study_region.csv
```

## Idempotency

The normalization fingerprint includes:

- verified source RAR MD5;
- FileGDB container name;
- source layer;
- EPSG:4326;
- production study-region parameters;
- normalized schema version.

If the fingerprint and existing Parquet hash match, a rerun returns the cached result.

## QC

Required hard gates:

- valid Stage-07f handoff;
- exact expected normalized schema;
- non-empty subset;
- no invalid output geometry;
- maximum stored radial distance <= 100 km;
- output Parquet exists with SHA-256.

Descriptive QC:

- bbox-filter rows vs exact-filter rows;
- blank-name count;
- unique-name count;
- source X/Y valid count;
- share source X/Y matching geometry within 1 m;
- median/p95/max geometry-vs-X/Y distance;
- exact duplicate-point rows;
- duplicate name+point rows;
- normalized bbox;
- output file size;
- GDAL version.

Raw X/Y agreement is descriptive and is not allowed to override the verified FileGDB geometry.

## Terminal status

Successful Stage 07g:

```text
runner_status = ready_for_anchor_context_audit
```

Failure:

```text
runner_status = blocked
```

A later anchor/name-context stage may start only after the successful status.

## Semantic boundary

Stage 07g does not:

- infer WORK/OFFICE/HOME;
- infer occupation;
- create POI categories from `PNAME`;
- tune mobility thresholds against BCL data.

It produces only a normalized historical external-context dataset.
