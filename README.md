# GeoLife MLE — Home / Office / POI Inference

A 6-week MLE learning project built around the Microsoft GeoLife GPS trajectory dataset.

Current focus: **Checkpoint 3 — OpenAPI contract and FastAPI serving for the merged CP2 Home / Office inference baseline**.

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
    ↓
HTTP ↔ production-model parity
```

Production implementation follows contract-first TDD. CP1 cleaning/stay-point and CP2 Home/Office inference are merged and validated, including full-release production parity. CP3 now adds a thin HTTP/OpenAPI layer without changing frozen CP2 model semantics. Exploratory code under `notebooks/` is not silently promoted into `src/`.

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


## CP2 baseline status

The merged CP2 v1 production baseline is intentionally conservative:

- Beijing-focused semantic cohort with explicit abstention;
- per-user complete-link recurring locations with 200 m maximum diameter;
- interval-overlap Home / Office evidence;
- separate Home and Office emission gates;
- heuristic evidence strength, not a calibrated probability;
- full-release parity: 27 HOME / 16 OFFICE emissions.

See `docs/design/03_home_office_baseline_contract.md`.

## CP3 API scope

The first API accepts **CP1 stay events for one user per request** and calls the frozen CP2 production model.

It does not accept raw GPS in v1 and does not return precise inferred Home/Office coordinates.

See `docs/design/04_api_contract.md`.
