# GeoLife MLE — Home / Office / POI Inference

A 6-week MLE learning project built around the Microsoft GeoLife GPS trajectory dataset.

Current focus: **Checkpoint 2/3 MLE delivery (Docker → model-version routing → AWS → async → monitoring).** Further EDA is deferred to a separate TODO backlog.

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
│   ├── 02a_trajectory_config_deep_dive.ipynb
│   ├── 02b_staypoint_sensitivity_validation.ipynb
│   ├── 02c_same_second_transport_audit.ipynb
│   ├── 03_home_office_baseline.ipynb
│   └── eda_core.py           # exploratory helpers, not production code
├── reports/
│   └── eda/                  # generated outputs ignored by default
├── infra/
│   └── terraform/            # AWS Terraform foundation; no paid resources yet
├── src/geolife/
│   ├── data/
│   ├── geo/
│   ├── staypoints/
│   ├── model/
│   └── api/
├── scripts/
│   └── export_openapi.py      # export FastAPI schema to standalone YAML
├── tests/
├── openapi.yaml               # mentor-reviewable standalone OpenAPI spec
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

- CP2-v2 all-resolved-IANA-timezone semantic scope, with explicit abstention;
- per-user complete-link recurring locations with 200 m maximum diameter;
- interval-overlap Home / Office evidence;
- separate Home and Office emission gates;
- heuristic evidence strength, not a calibrated probability;
- full-release parity: 27 HOME / 16 OFFICE emissions.

See `docs/design/03_home_office_baseline_contract.md`.

## API scope

The **implemented compatibility contract** is:

```text
POST /v1/classify/{user_id}
```

A new stateless **v2 serving API is proposed but NOT yet implemented**:

```text
POST /v2/inferences
```

It avoids user IDs in URLs, distinguishes HOME/OFFICE from generic OTHER_RECURRING places and names heuristic evidence without claiming probability. See `docs/design/05_serving_api_v2_proposal.md`.

It accepts one user's raw GPS sequence with UTC timestamps and lat/lng observations,
runs the frozen CP1 cleaning + stay-point detector, then returns HOME / OFFICE /
generic POI locations with heuristic confidence.

The older `POST /v1/home-office/infer` stay-event route remains only as a deprecated
compatibility endpoint for the existing HTTP ↔ direct-model parity checks.

See `docs/design/02_checkpoint1_api_spec.md` for the mentor-facing contract and
`docs/design/04_api_contract.md` for the internal stay-event adapter history.


## Run the CP3 API

Install the project and start the local server:

```bash
python -m pip install -e '.[dev]'
uvicorn geolife.api.app:app --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/health
```

FastAPI provides the API contract in three reviewable forms:

- Swagger UI: `http://127.0.0.1:8000/docs`;
- runtime OpenAPI JSON: `http://127.0.0.1:8000/openapi.json`;
- committed standalone spec: `openapi.yaml`.

Regenerate the committed YAML from the FastAPI app with:

```bash
python scripts/export_openapi.py
```

This keeps the mentor-facing `.yaml` deliverable derived from the same FastAPI application that serves Swagger/OpenAPI at runtime.

The primary Track B1 v1 endpoint is:

```text
POST /v1/classify/{user_id}
```

It accepts one user's raw GPS sequence with UTC timestamps and lat/lng observations.
The pipeline performs cleaning, stay-point detection, and semantic inference before
returning HOME/OFFICE/generic-POI locations with heuristic `confidence`.

Valid but weak/out-of-scope evidence returns HTTP 200 with explicit abstention.
Malformed input returns HTTP 422.

The older `POST /v1/home-office/infer` endpoint remains available as a deprecated
internal compatibility route.

Precise inferred Home/Office coordinates are intentionally omitted from the response contract.

Full-release HTTP parity is validated in `notebooks/04_api_contract_validation.ipynb`.

## Checkpoint 1 deliverable mapping

- Repository/environment/Terraform foundation: implemented under `infra/terraform/` and validated in CI.
- Stay-point detection + baseline Home/Office heuristic: implemented and validated.
- FastAPI API package: `src/geolife/api/`.
- Swagger UI: automatically generated by FastAPI at `/docs`.
- Primary API contract: `POST /v1/classify/{user_id}` with raw GPS sequence input.
- Runtime OpenAPI schema: automatically generated at `/openapi.json`.
- Standalone review artifact: `openapi.yaml`.
- Production structure: `src/geolife/model/`, `src/geolife/api/`, and `tests/`.
- GeoLife has no authoritative Home/Office ground truth; evaluation therefore uses sensitivity, abstention/parity checks, plus a completed privacy-safe manual plausibility review on sampled users (`002`, `009`, `022`) rather than absolute supervised accuracy. See `docs/evaluation/01_home_office_manual_plausibility.md`.


## Terraform foundation

Checkpoint 1 includes a Terraform foundation under `infra/terraform/`.

It intentionally creates **no AWS resources yet**. The purpose is to lock tooling,
AWS-provider configuration, region/environment variables, default tags, state hygiene,
and CI validation before Checkpoint 2 introduces deployable infrastructure.

Validate locally with:

```bash
terraform -chdir=infra/terraform fmt -check
terraform -chdir=infra/terraform init -backend=false
terraform -chdir=infra/terraform validate
```

See `infra/terraform/README.md`.


## Track B1 delivery pivot (October 2026)

The research track is closed for now: Stage 08c is experimental and Stage 09 cross-file stitching had no new HOME/OFFICE emissions. **Research TODOs do not block serving.**

- [Prioritized Track B1 delivery roadmap](docs/roadmap/track_b1_delivery_roadmap.md)
- [Proposed privacy-aware API v2 contract](docs/design/05_serving_api_v2_proposal.md) — design only, not deployed
- [Docker sync-serving runbook](docs/deployment/01_docker_sync_serving.md) — runnable v1 image, CI smoke gate

Current production CP2-v2 clusters recurring locations with **complete-link 200 m**, not DBSCAN. Two distinct model variants, actual AWS endpoint, canary, async job execution and CloudWatch dashboards remain implementation milestones; do not treat project planning or Docker configuration as completed AWS deployment.
