# Notebooks

## Modal setup

The EDA notebooks are designed to run in a CPU-backed Modal Notebook. A GPU is unnecessary for Checkpoint 1 EDA.

Recommended workflow:

1. Create a Modal Notebook.
2. Attach a persistent Modal Volume for the dataset (for example `geolife-data`). Modal Notebooks support attaching Volumes from the UI.
3. Upload/extract the official GeoLife dataset into that Volume. Keep the raw data out of Git.
4. Mount the Volume so the dataset is available at a stable path such as `/data/Geolife Trajectories 1.3/Data`.
5. Clone this repository/branch in the notebook environment.
6. Install the project dependencies:

```bash
pip install -e '.[dev]'
```

7. If the dataset is mounted elsewhere, set:

```bash
export GEOLIFE_DATA_ROOT="/your/mount/Geolife Trajectories 1.3/Data"
```

8. Run `01_geolife_eda.ipynb` top to bottom.

## Why a Volume?

The extracted GeoLife dataset is much larger than the Git repository and should persist independently of notebook kernels. Modal Volumes are persistent filesystem storage and are a better fit than repeatedly uploading the dataset into ephemeral notebook state.

## Notebook sequence

- `01_geolife_eda.ipynb` — raw dataset inventory, quality, sampling, movement/noise, spatial/temporal coverage, label coverage, privacy notes.
- `02_staypoint_threshold_study.ipynb` — planned after the first EDA is executed and reviewed.

Do not commit executed notebooks containing user-level maps or raw GPS excerpts.

## Mentor demo notebook

`03c_behavior_eda_mentor_demo.ipynb` is the consolidated mentor-facing notebook for the post-Home/Office exploratory work.

It reuses the validated Modal Volume caches from:

- `03a_user_behavior_deep_dive`;
- `03b_mobile_work_hypothesis`;
- `03b1_observation_support_controlled`.

The notebook is intentionally presentation-oriented:

- no raw GeoLife rescan;
- aggregate tables/charts plus deterministic user-level case diagnostics;
- internal demo maps intentionally show public GeoLife user IDs and coordinates;
- each section follows question → rationale → measurement → result → caveat → decision;
- it ends with mentor-ready talking points and the open DBSCAN MinPts follow-up.

Recommended demo path:

```text
03_home_office_baseline.ipynb
        ↓
03c_behavior_eda_mentor_demo.ipynb
```

The detailed 03a/03b/03b.1 runners remain the reproducibility/audit source; 03c is the compact narrative view.

The mentor-demo notebook now also includes a visual v2 layer: deterministic raw GeoLife user IDs, interactive Folium stay/location maps, a representative matched A/B pair, daily mobility timelines, and L* transition heatmaps. Case selection is deterministic and illustrative; aggregate/sensitivity/bootstrap evidence remains the basis for research conclusions. visual v2 adds deterministic raw-ID case maps.

