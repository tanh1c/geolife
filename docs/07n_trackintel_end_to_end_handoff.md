# Stage 07n handoff — Trackintel end-to-end pipeline comparator

## Run only

```text
notebooks/07n_trackintel_end_to_end.ipynb
```

The notebook uses the existing Modal Volume:

```text
/mnt/geolife-data
```

It needs both:

1. the raw extracted GeoLife `Data/` directory;
2. the existing frozen `stays_baseline_v1.pkl` cache.

No previous notebook needs to be rerun when those artifacts already exist.

## Raw directory discovery

The notebook checks:

```text
$GEOLIFE_RAW_ROOT
/mnt/geolife-data/extracted/Geolife Trajectories 1.3/Data
/mnt/geolife-data/Data
/mnt/geolife-data/Geolife Trajectories 1.3/Data
```

If your raw release is elsewhere, set `GEOLIFE_RAW_ROOT` to the directory that
directly contains `000/`, `001/`, ..., `181/`.

## Expected early gates

Before Trackintel processing:

```text
raw users           182
trajectory files  18670
CP1 stays          5821
CP1 stay users      136
production HOME      27
production OFFICE    16

raw release + production parity: PASS
```

Trackintel then processes one user at a time and writes resumable per-user
caches. The first run can take materially longer than Stage 07m because it reads
and processes all 24,876,978 raw GPS points.

At the end of raw processing the notebook must print:

```text
Trackintel raw point reconciliation: PASS 24876978
```

A rerun should be much faster because completed users are loaded from the
Volume cache.

## Parameters frozen for this stage

Trackintel 1.4.2 staypoints:

```text
dist_threshold = 200 m
time_threshold = 20 min
gap_threshold  = 5 min
include_last   = False
```

Locations:

```text
DBSCAN epsilon = 100 m, num_samples = 1
DBSCAN epsilon = 200 m, num_samples = 1
```

Semantics:

```text
OSNA
pre_filter = False
```

Do not edit these parameters during the measured run.

## Main tables to send back

After Run All, send the executed notebook containing:

```text
TRACKINTEL PIPELINE SUMMARY

STAY EXTRACTION MATCH

LOCATION GEOMETRY MATCH

timezone adapter summary

SEMANTIC CANDIDATE SPATIAL AGREEMENT

SEMANTIC STATUS DISTRIBUTION

decomposition snapshot
```

## Output cache

```text
/mnt/geolife-data/cache/cp2_v2/07n_trackintel_end_to_end/
```

Raw GPS points are not cached by this stage. User-level derived
stay/location/candidate data and matching details are private.

## Interpretation rule

Do not compare Trackintel and production integer `location_id`.

Do not report Stage 07n as accuracy.

Do not change HOME/OFFICE thresholds based on this notebook.

The goal is to answer where pipeline differences arise:

```text
stay detection?
location clustering?
semantic selection?
```

The frozen production policy remains HOME 27 / OFFICE 16 until a separate
policy decision is justified.
