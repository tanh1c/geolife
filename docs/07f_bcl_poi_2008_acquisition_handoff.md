# Stage 07f handoff — BCL POI 2008 on Modal

## What is already known

Corrected historical anchor universe:

```text
198 recurring non-HOME anchors
25 users
```

BCL 2008 temporal relevance:

```text
185 / 198 anchors
19 users
```

Official BCL metadata describes a 2008 mainland-China POI snapshot with over six million records, ArcGIS Personal Geodatabase 10.1 format, coordinates and place names, and no category field.

## Before running

Required existing Modal Volume content:

```text
/mnt/geolife-data/**/anchor_observation_dates_private.pkl
```

The anchor artifact must carry:

```text
location_namespace =
production_complete_link_200m_beijing_policy_v1
```

No Figshare API secret is required for public metadata/files.

## Modal Volume name

The notebook's filesystem mount remains:

```text
/mnt/geolife-data
```

The remote worker also needs the Modal object name.

Default:

```text
geolife-data
```

If yours is different, set this before the worker cell:

```python
import os
os.environ["GEOLIFE_MODAL_VOLUME_NAME"] = "<actual-volume-name>"
```

## First run

Run the notebook top-to-bottom.

Expected first diagnostics:

1. BCL eligible-anchor summary;
2. Figshare metadata summary;
3. Figshare files table;
4. INITIAL GATES;
5. selected source mode.

### If public file + explicit reusable licence are available

The notebook automatically:

- starts a dedicated Modal worker;
- streams/resumes the download to the Volume;
- verifies size/MD5;
- computes SHA-256;
- extracts ZIP safely if necessary;
- finds the MDB;
- runs mdbtools/GDAL inspection;
- writes the final gate table and acquisition manifest.

### If no public downloadable file is exposed

The notebook should finish cleanly with:

```text
source_mode: None
BLOCKED ...
Manual fallback inbox:
/mnt/geolife-data/external/bcl_poi_2008/inbox
```

Do not invent a URL.

If you obtain the exact file from a provenance-preserving source, upload the original MDB/ZIP/RAR to that inbox and rerun.

### If the public licence is unclear

The notebook intentionally does not auto-download.

Do not bypass the licence gate merely because a direct file URL is visible.

## Worker environment

The worker image installs:

- mdbtools;
- unixODBC;
- odbc-mdbtools;
- gdal-bin;
- unzip;
- httpx.

No GPU is required.

The worker timeout is 30 minutes and large files are streamed in 8 MiB chunks.

## What output to send back

Send the executed notebook.

The important fields are:

```text
metadata_summary:
  title
  doi
  license_name
  file_count
  downloadable_file_count

INITIAL GATES

source_mode

worker ok / worker error

MDB inspection:
  table_count
  layer_count
  point_like_layer_count
  max_feature_count
  EPSG / CRS availability
  field list

FINAL GATES
  runner_status
```

## Interpretation

Do not proceed to semantic joining unless:

```text
runner_status == ready_for_normalization
```

If the notebook ends blocked, Stage 07f still succeeded as an audit: the blocking reason becomes the result.

If it reaches `ready_for_normalization`, the next patch should be Stage 07g:

- deterministic Beijing-only extraction;
- normalized WGS84 coordinates only after CRS is verified;
- name preservation;
- no category invention;
- high-precision lexical semantic audit against the 185 eligible anchors.


## Measured first-run update

The official Figshare record now exposes a direct public RAR attachment:

```text
Points of interest of China in 2008.rar
120023687 bytes
MD5 e77c3473874a6fb64fd0c52d3c66fc84
licence CC BY 4.0
```

The corrected notebook downloads this automatically and extracts it with `unar`; no manual inbox upload should be needed unless public availability changes.

## After the second runtime

RAR download and extraction have already succeeded on Modal, but no `.mdb` file was found.

The next notebook version reuses the cached RAR and prints the extracted inventory. It automatically detects MDB, FileGDB, GeoPackage, Shapefile, or SQLite.

Important outputs now include:

```text
extracted file_count
extension_counts
container_kind
container_path
container candidates
```

If no supported container is found, send the printed extension counts and representative paths; that is now an explicit source-format audit result rather than a generic runtime error.

