# GeoLife MLE — Home / Office / POI Inference

A 6-week MLE learning project built around the Microsoft GeoLife GPS trajectory dataset.

Current focus: **Checkpoint 2 — user-level recurring locations, timezone policy, and interpretable Home / Office / POI baseline inference on top of the merged CP1 cleaning + stay-point pipeline**.

## Workflow

```text
GeoLife raw PLT
    ↓
EDA + data-quality study
    ↓
clean / speed-based filtering
    ↓
stay-point detection
    ↓
user-level recurring locations
    ↓
timezone / geography policy
    ↓
Home / Office / POI heuristic
    ↓
OpenAPI contract review
    ↓
FastAPI implementation
```

Production implementation starts only after the relevant design/contract is reviewed. CP1 cleaning/stay-point code is now merged; CP2 Home/Office logic remains notebook/design work until timezone, recurring-location and scoring semantics are reviewed and covered by RED tests. Exploratory code under `notebooks/` is not silently promoted into `src/`.

## Repository structure

```text
geolife/
├── data/                     # setup docs only; raw data is gitignored
├── docs/
│   └── eda/                  # EDA questions and decision records
├── notebooks/
│   ├── 01_geolife_eda.ipynb
│   ├── 02_cleaning_staypoint_validation.ipynb
│   ├── 02b_staypoint_sensitivity_validation.ipynb
│   ├── 02c_same_second_transport_audit.ipynb
│   ├── 03_home_office_baseline.ipynb
│   └── eda_core.py           # exploratory helpers, not production code
├── reports/
│   └── eda/                  # generated outputs ignored by default
├── src/geolife/
│   ├── data/
│   ├── geo/
│   ├── staypoints/
│   ├── model/
│   └── api/
├── tests/
└── pyproject.toml
```

## EDA

The first notebook is deliberately broader than the previous MovieLens baseline. It investigates dataset inventory and imbalance, schema quality, sampling behavior, trajectory duration/distance, temporal history per user, spatial coverage, raw movement/noise, altitude quality, transportation-label coverage, timezone semantics, and mobility privacy.

See:

- `docs/eda/01_eda_plan.md`
- `notebooks/01_geolife_eda.ipynb`
- `notebooks/README.md` for Modal setup

## Data policy

Raw GeoLife data is intentionally **not** stored in this repository. The Microsoft Research license supplied with the dataset is non-commercial and includes redistribution restrictions. GPS trajectories also carry significant privacy risk.

See `data/README.md` before downloading or publishing any derived artifact.

## Install

```bash
python -m pip install -e '.[dev]'
```

Python 3.11–3.13 is supported by the project configuration.
