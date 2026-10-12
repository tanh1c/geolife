# Checkpoint 2 — local Docker sync serving

Status: **IMPLEMENTED CONFIGURATION; container build/smoke must run in CI or a Docker-capable machine. AWS has not been deployed.**

This image packages the existing **v1** HTTP API around frozen CP1+CP2-v2. It does not bundle GeoLife raw files, Modal caches or user location histories.

## Build and run

```bash
docker build -t geolife-api:cp2v2 .
docker run --rm --name geolife-api -p 127.0.0.1:8000:8000 \
  --memory=2g --cpus=2 geolife-api:cp2v2
```

In a separate terminal:

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/openapi.json
```

For local Swagger: `http://127.0.0.1:8000/docs`.

Example abstention request (one raw GPS point is accepted as valid input, but insufficient for a stay):

```bash
curl -sS -X POST http://127.0.0.1:8000/v1/classify/demo \
  -H 'Content-Type: application/json' \
  -d '{"points":[{"timestamp_utc":"2009-01-05T13:00:00Z","latitude":39.9042,"longitude":116.4074}]}'
```

Expected HTTP 200 with empty `locations` and HOME/OFFICE `insufficient_stay_history` abstentions. No exact inferred coordinates are returned.

## Build expectations and CI

- Python 3.11 slim, install production dependencies from `pyproject.toml`.
- Only `src`, `README.md`, `pyproject.toml` are copied into image.
- Non-root UID 10001; `/health` health check; port 8000.
- GitHub CI workflow `docker-smoke.yml` builds image and exercises health, OpenAPI, abstention response on localhost.
- It does **not** push an image to a registry or start AWS resources. CI success must be observed in GitHub Actions; this document is not a passing-run claim.

## Security/deploy notes

Do **not** use `-p 8000:8000` on an internet-facing server without protection: loopback publishing above is intentional. For AWS, put authenticated/HTTPS ingress in front or restrict network access to a private demo network. Configure cost alerts, IAM, deployment/rollback and teardown before creating infrastructure. Python scientific libraries may exceed a very small 1 GiB instance's available RAM; measure container RSS before choosing EC2 size.

## Model/version distinction

The current production semantic model is CP2-v2 **complete-link 200 m**, not DBSCAN. The Docker tag names the packaged implementation; an image digest or immutable Git SHA is needed for reproducible deployment. A second genuinely different candidate model and v2 public API remain separate tasks in the delivery roadmap.


## v2 and metrics follow-up

The image now includes `POST /v2/inferences`, `GET /v2/model-info` and `GET /health/ready`. In canary demo mode, supply `GEOLIFE_ROLLOUT_MODE=canary`, `GEOLIFE_CANARY_PERCENT=10`, a private `GEOLIFE_CANARY_SALT` and immutable `GEOLIFE_RELEASE_ID` via ignored `.env` with `docker run --env-file .env ...`. Rollback: change mode to `baseline` and restart.

Optional protected Prometheus endpoint: set `GEOLIFE_METRICS_BEARER_TOKEN`, scrape `GET /internal/metrics` from a restricted network. Run `python scripts/benchmark_sync.py --requests 50 --warmup 5` for a synthetic client-side latency check. See `docs/deployment/03_monitoring_foundation.md`. Cloud deployment, rate limiting, async SQS and alert/dashboard configuration remain separate work.
