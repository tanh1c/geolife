# Stage 07g handoff — BCL Beijing normalization on Modal

## Prerequisite

Stage 07f must already be complete on the same Modal Volume.

Required:

```text
/mnt/geolife-data/cache/07f_bcl_poi_2008_acquisition/acquisition_manifest.json
/mnt/geolife-data/cache/07f_bcl_poi_2008_acquisition/worker_report.json
```

Expected 07f result:

```text
runner_status = ready_for_normalization
container_kind = gdb
container = POI2008All.gdb
layer = POI2008CN
CRS = EPSG:4326
```

The 120 MB RAR does not need to be downloaded again.

## Modal Volume

Filesystem mount:

```text
/mnt/geolife-data
```

Default Modal Volume object:

```text
geolife-data
```

If the object name is different:

```python
import os
os.environ["GEOLIFE_MODAL_VOLUME_NAME"] = "<actual-volume-name>"
```

## Run

Run the 07g notebook top-to-bottom.

No external API key is needed.

No GPU is needed.

The remote worker may take longer on the first run because it scans the FileGDB with a spatial bbox filter and writes the normalized Parquet. Reruns with the same fingerprint/hash should return the cached result.

## Expected early output

```text
stage07f_runner_status = ready_for_normalization
container_kind = gdb
source_md5 = e77c3473874a6fb64fd0c52d3c66fc84

study region:
39.9042, 116.4074, 100 km
```

## Expected worker output

```text
worker ok: True
worker error: None
cached: False   # or True on rerun
bbox rows: ...
exact 100km rows: ...
```

## Final decision

Required:

```text
source_handoff_status  = pass_stage07f_handoff
schema_status          = pass_normalized_schema
spatial_filter_status  = pass_exact_100km_filter
output_integrity_status = pass_parquet_hash
runner_status          = ready_for_anchor_context_audit
```

## What to send back

Send the executed notebook.

Important measured values:

```text
bbox_filter_rows
row_count
blank_name_count
unique_name_count

raw_xy_valid_count
raw_xy_within_1m_count
raw_xy_within_1m_share
raw_geom_delta_m_median
raw_geom_delta_m_p95
raw_geom_delta_m_max

duplicate_point_rows
duplicate_name_point_rows

min/max geom lon/lat
max_distance_to_beijing_km

parquet_size_bytes
parquet_sha256
gdal_version

NORMALIZATION DECISION
runner_status
```

## If it fails

Useful failures are explicit:

- validated GDB missing;
- layer/Point/EPSG contract changed;
- `ogr2ogr` bbox extraction failed;
- staged CSV schema differs from `WKT/PNAME/X/Y`;
- exact 100 km result is empty;
- Parquet/schema/hash QC fails.

Do not bypass a failed gate by manually editing the output.

## Next stage

If 07g passes, the next stage can compare BCL place names around the 185 temporally eligible anchors.

That later stage must keep `unknown/ambiguous` as a first-class result and must not treat BCL names as direct WORK/OFFICE ground truth.
