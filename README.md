# GeoLife MLE — Home / Office / POI Inference

A 6-week MLE learning project built around the Microsoft GeoLife GPS trajectory dataset.

Current focus: **Checkpoint 1 — data exploration, trajectory cleaning, stay-point detection, baseline Home/Office inference, and API contract design**.

## CP1 workflow

```text
GeoLife raw PLT
    ↓
EDA + data-quality study
    ↓
clean / speed-based filtering
    ↓
stay-point detection
    ↓
Home / Office heuristic
    ↓
OpenAPI contract review
    ↓
FastAPI implementation
```

Production implementation starts only after the relevant design/contract is reviewed. Exploratory EDA code is kept under `notebooks/` and will not be silently promoted into `src/`.

## Repository structure

```text
geolife/
├── data/                     # setup docs only; raw data is gitignored
├── docs/
│   └── eda/                  # EDA questions and decision records
├── notebooks/
│   ├── 01_geolife_eda.ipynb
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
