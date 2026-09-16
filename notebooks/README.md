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
