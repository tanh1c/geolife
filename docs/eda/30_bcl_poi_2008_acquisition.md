# Stage 07f — BCL POI 2008 acquisition / provenance / CRS audit

## Why this stage exists

Corrected Stage 07c shows that Beijing City Lab POI 2008 is temporally relevant to:

- 185 / 198 recurring non-HOME anchors;
- 19 / 25 candidate users.

That makes BCL POI 2008 the highest-value unresolved historical semantic source after Stage 07e.

Stage 07f is deliberately an **acquisition and provenance gate**, not a semantic join.

## Current source facts

Official Beijing City Lab DATA 011 states:

- source: over six million POI records scraped in 2008;
- spatial coverage: mainland China;
- temporal coverage: 2008 snapshot;
- format: ArcGIS Personal Geodatabase 10.1;
- content: coordinates + place names, no category field;
- current access/documentation DOI: `10.6084/m9.figshare.28667492`.

Official page:

- https://www.beijingcitylab.org/data/data-011/index.html

Figshare public API documentation states that public metadata and public files can be retrieved without authentication:

- https://api.figshare.com/v2/articles/28667492
- https://docs.figshare.com/v2/
- https://info.figshare.com/user-guide/how-to-use-the-figshare-api/

The BCL page itself currently lists no direct attachment. Therefore Stage 07f probes the Figshare API at runtime rather than inventing a download URL.

## Gates

A downstream normalization stage is allowed only if all required gates pass.

### Metadata access

Required:

- public Figshare API response is available;
- record metadata can be parsed.

Failure is blocking.

### File access

Passes when either:

- Figshare metadata exposes a downloadable `.mdb`, `.zip`, or `.rar`; or
- a manually acquired/cached `.mdb`, `.zip`, or `.rar` exists in the declared Modal Volume inbox.

The notebook never assumes that DOI metadata implies a downloadable file.

### Licence / reuse rights

Public auto-download is allowed only when the runtime metadata exposes an explicit broadly reusable licence token recognised by the audit.

Missing or ambiguous licence metadata stays blocked.

This is a technical reproducibility gate, not legal advice.

### Format

Accepted acquisition containers:

- direct `.mdb`;
- `.zip` containing at least one `.mdb`;
- `.rar` containing at least one `.mdb`.

Other formats are blocked until explicitly reviewed.

### Integrity

For Figshare downloads:

- stream to `.part`;
- resume with HTTP Range when supported;
- restart cleanly if the server ignores Range;
- verify metadata file size when present;
- verify Figshare MD5 when present;
- compute SHA-256 for the local manifest.

### Personal Geodatabase inspection

The Modal worker uses:

- `mdbtools`;
- `unixodbc`;
- `odbc-mdbtools`;
- `gdal-bin`.

Primary commands:

- `mdb-tables -1`;
- `mdb-schema`;
- `ogrinfo --formats`;
- `ogrinfo -ro -so -al`.

GDAL's PGeo driver is preferred for spatial metadata because Personal Geodatabase geometries are stored in ESRI-specific BLOBs and PGeo can expose feature layers and spatial reference metadata.

Reference:

- https://gdal.org/en/stable/drivers/vector/pgeo.html

### CRS

CRS is not inferred from coordinate ranges alone.

Pass requires the inspected geodatabase/layer to expose usable spatial-reference metadata through GDAL/PGeo.

If CRS metadata is absent, Stage 07f remains blocked even if longitude/latitude-looking values are observed.

## Modal execution design

### Notebook layer

The notebook performs:

- repo checkout;
- corrected-anchor provenance check;
- public Figshare metadata probe;
- gate evaluation;
- small aggregate outputs.

### Worker layer

Large-file and system-library work runs in a Modal Function.

Default Volume name:

```text
geolife-data
```

Override when needed:

```bash
export GEOLIFE_MODAL_VOLUME_NAME="<actual-volume-name>"
```

The worker mounts the named Volume at:

```text
/mnt/geolife-data
```

Its image installs system dependencies via `apt_install` instead of changing the notebook kernel.

This keeps execution reproducible and restart-safe.

## Persistent paths

Cache:

```text
/mnt/geolife-data/cache/07f_bcl_poi_2008_acquisition/
```

External source area:

```text
/mnt/geolife-data/external/bcl_poi_2008/
  inbox/
  raw/
  extracted/
```

Manual fallback files belong in `inbox/`.

## Expected outputs

Aggregate/reproducibility outputs:

- `figshare_metadata_summary.csv`;
- `figshare_files.csv`;
- `acquisition_gates.csv`;
- optional `mdb_inspection_summary.csv`;
- `acquisition_manifest.json`;
- worker raw report in the private Modal cache.

The manifest explicitly keeps:

- `semantic_claim_allowed = false`;
- `occupation_inference_allowed = false`.

## Stage decision

Possible terminal states:

### `blocked`

Do not proceed to semantic normalization.

Typical blockers:

- no public/manual file;
- no explicit reusable licence;
- unsupported file format;
- MDB inspection failure;
- missing CRS metadata.

### `ready_for_mdb_inspection`

File and licence gates pass but CRS is not yet resolved.

Inspect only; no spatial join.

### `ready_for_normalization`

Access, licence, format and CRS gates all pass.

Only then create a Stage 07g normalization / Beijing extraction patch.

## Semantic boundary

The official BCL description says this source has place names but no category field.

Therefore even a fully usable file does not provide direct WORK/OFFICE labels.

Any later semantic evidence must use a predeclared, high-precision lexical mapping with explicit unknown/ambiguous output. Free-form occupation or workplace inference is not allowed.


### Measured official Figshare attachment

The first Modal run resolved one direct public attachment:

- `Points of interest of China in 2008.rar`;
- 120,023,687 bytes;
- MD5 `e77c3473874a6fb64fd0c52d3c66fc84`;
- CC BY 4.0;
- not link-only.

RAR is therefore a first-class supported acquisition container. The worker installs Debian `unar`, which supports RAR extraction on Linux, then continues with the same MDB/GDAL inspection gates.

### Archive-container inspection after the second runtime

The official RAR may not expose an `.mdb` file directly even though the BCL documentation describes ArcGIS Personal Geodatabase 10.1.

Stage 07f therefore treats the documentation format as a claim to verify, not as a filename assumption.

After extraction the worker now inventories the real tree and checks, in order:

1. `.mdb`;
2. FileGDB `.gdb` directory;
3. GeoPackage `.gpkg`;
4. Shapefile `.shp`;
5. SQLite `.sqlite`.

If none exists, the audit stores extension counts and representative paths and remains blocked.

GDAL PGeo is required only for an actual MDB. Other supported spatial containers are inspected with their native GDAL driver.

## Final measured result — ready for normalization

The third Modal run completed the acquisition/provenance/CRS audit successfully.

### Public source identity

- Figshare article id: 28667492;
- DOI: `10.6084/m9.figshare.28667492.v1`;
- licence: CC BY 4.0;
- direct public file: `Points of interest of China in 2008.rar`;
- file size: 120,023,687 bytes;
- MD5: `e77c3473874a6fb64fd0c52d3c66fc84`.

### Extracted archive structure

The RAR does not contain an MDB. It contains an ArcGIS File Geodatabase:

```text
POI2008All.gdb
```

Extracted inventory:

- 45 files;
- FileGDB components include `.gdbtable`, `.gdbtablx`, `.gdbindexes`, `.atx`, `.spx`.

This resolves the discrepancy with the older BCL page wording that described an ArcGIS Personal Geodatabase. The actual current Figshare attachment is a File Geodatabase.

### GDAL inspection

Selected container:

```text
container_kind = gdb
container_path = .../POI2008All.gdb
```

Measured layer metadata:

- layer: `POI2008CN`;
- geometry: Point;
- feature count: 6,039,158;
- CRS: EPSG:4326;
- fields: `PNAME`, `X`, `Y`.

### Final gates

```text
metadata_access   = pass_public_metadata_identity
file_access       = pass_public_file
license_status    = pass_explicit:CC BY 4.0
format_status     = pass_inspected_gdb
structure_status  = pass_spatial_point_structure
crs_status        = pass_inspected_crs
runner_status     = ready_for_normalization
```

Stage 07f therefore closes successfully.

The next stage may normalize/extract the FileGDB deterministically, but must preserve the semantic boundary: the source provides POI names and coordinates, not trusted WORK/OFFICE categories.

