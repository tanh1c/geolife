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



### Stage 05c — stable secondary independent evidence

- `05c_stable_secondary_independent_evidence.ipynb`
- Reuses Stage-05b private caches.
- Compares persistent non-HOME secondary anchors with same-user recurring peers on weekday contrast, HOME-pair transitions, arrival-time concentration, and dwell regularity.
- Audit only: does not relabel stable secondary anchors as OFFICE.


### Stage 06 — routine / habit mining

- `06_routine_habit_mining.ipynb`
- Uses the broader Stage-03a all-resolved behavior representation.
- Mines supported daily sequences, directed OD recurrence, cyclic departure-time regularity, multimodal departure habits, and split-half routine stability.
- No HOME/OFFICE relabeling; user-level routine tables remain private on the Modal Volume.


### Stage 06b — routine representation robustness

- `06b_routine_representation_robustness.ipynb`
- Reuses private Stage-06 routine caches; no raw rescan.
- Fixes the one-day motif-repeatability issue with a common support universe.
- Compares chronological OD-distribution shifts against random balanced day partitions.
- Bootstraps departure-time concentration by active day and applies stricter multimodal GMM checks.
- This is the readiness gate before Stage 07 behavioral change detection.


### Stage 06c — change-detection representation feasibility

- `06c_change_detection_representation_feasibility.ipynb`
- Reuses private Stage-06 day/transition caches plus Stage-03a cleaned point-day metrics; no raw rescan.
- Evaluates 28/42/56-day coarse support-normalized features, adjacent-window test-retest stability, support-matched random-partition nulls, and feature bootstrap uncertainty.
- Keeps exact-edge JSD as a baseline comparator; Stage 07 remains blocked until the measured 06c tables are reviewed.

### Stage 06d — support-indexed window feasibility

- `06d_support_indexed_window_feasibility.ipynb`
- Reuses the Stage-06c representation but replaces fixed calendar windows with non-overlapping 6 / 8 / 10 usable-day blocks.
- Applies 56 / 84-day calendar-span caps so equal support does not silently allow arbitrarily long elapsed-time windows.
- Keeps the Stage-06c null calibration and bootstrap gates, and adds a >=10 unique-user coverage guard.
- Stage 07 proceeds only if at least one predeclared primary feature passes every readiness gate.

