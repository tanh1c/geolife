# Stage 07g handoff — BCL POI 2008 lexical-context alignment

## Prerequisites

Do not rerun Stage 07f.

Required existing artifacts:

```text
/mnt/geolife-data/cache/07f_bcl_poi_2008_acquisition/
  acquisition_manifest.json

/mnt/geolife-data/external/bcl_poi_2008/
  raw/
  extracted/
    .../POI2008All.gdb

/mnt/geolife-data/cache/cp2_v2/07c_historical_source_alignment/
  anchor_observation_dates_private.pkl

/mnt/geolife-data/cache/cp2_v2/05b_home_consensus_adaptive_work/
  adaptive_work_patterns_42_private.pkl

/mnt/geolife-data/cache/cp2_v2/07b_factorized_work_profiles/
  factorized_work_profiles_private.pkl
```

## Notebook

Run:

`notebooks/07g_bcl_poi_2008_alignment.ipynb`

from current `main`.

The notebook fetches/resets the repo and installs the checked-out package before importing Stage-07g helpers.

## Expected initial gate

The source-manifest table must show:

`ready = True`

with:

- source `bcl_poi_2008`;
- runner status `ready_for_normalization`;
- container kind `gdb`;
- EPSG containing 4326.

If this gate fails, stop. Do not bypass it.

## Expected CP2-v2 eligibility

The frozen current universe should report:

```text
candidate anchors       298
candidate users          29
BCL eligible anchors    259
BCL eligible users       23
exact 2008 anchors       93
proxy 2007 anchors        2
proxy 2009 anchors      164
```

A mismatch means an upstream artifact changed and must be reviewed before semantic interpretation.

## Modal worker

The worker:

1. checks the cached original Stage-07f source SHA-256;
2. validates the FileGDB layer;
3. runs GDAL spatial filters over deterministic padded tiles;
4. selects `PNAME/X/Y` only;
5. deduplicates overlapping tile output;
6. writes private neighborhood POIs to the CP2-v2 Stage-07g cache.

No source download or external API call occurs.

Default Modal Volume object:

`geolife-data`

Override only if necessary:

```python
os.environ["GEOLIFE_MODAL_VOLUME_NAME"] = "<actual-volume-name>"
```

## Important outputs to send back

Send the executed notebook.

Key tables/counts:

- source manifest gate;
- BCL eligibility summary;
- spatial extraction summary;
- lexical status summary;
- anchors with any POI <=100 m;
- anchors with any lexical signal <=100 m;
- anchors with broad work-compatible lexical signal <=100 m;
- lexical category × distance threshold;
- stable-secondary paired composite summary;
- stable-secondary category-specific summary;
- Stage-07b axes × BCL lexical context.

Also send any GDAL/Modal traceback.

## Semantic boundary

The BCL source has names but no trusted categories.

Therefore:

- raw names stay private;
- lexical rules remain explicit and deterministic;
- unknown is not auto-filled;
- multi-signal names remain ambiguous;
- no WORK/OFFICE/HOME or occupation label is emitted.

The decision hinges on same-user candidate-vs-peer evidence, not on the raw percentage of anchors near named POIs.
