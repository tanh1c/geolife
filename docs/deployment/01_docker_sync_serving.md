# Track B1 — Docker sync serving, restricted research demo

Status: **Docker image and HTTP smoke tests implemented; AWS deployment NOT done**. See `docs/deployment/07_security_review_pre_merge.md` for the security review.

The production frozen CP1 + CP2 semantic algorithms remain unchanged. The Docker image now defaults to `GEOLIFE_PRIVATE_DEMO=1` so it is **fail-closed for anonymous legacy inference**. This is intentionally different from a standalone Python process without demo settings, which retains the v1 contract for parity/compatibility tests.

## Build / local smoke

```bash
docker build -t geolife-api:private-demo .
docker run --rm --name geolife-api -p 127.0.0.1:8000:8000 \
    --memory=2g --cpus=2 geolife-api:private-demo
```

```bash
curl --fail http://127.0.0.1:8000/health
curl --fail http://127.0.0.1:8000/openapi.json
curl -i http://127.0.0.1:8000/demo
curl -i -X POST http://127.0.0.1:8000/v1/classify/000 \
    -H 'Content-Type: application/json' -d '{"points":[]}'
# Expected HTTP 404 (legacy route is disabled in Docker private-demo mode).
curl -i -X POST http://127.0.0.1:8000/v2/me/dataset-inferences
# Expected HTTP 401 (account-scoped endpoint requires Bearer token).
```

The image **does not** ship with GeoLife data or demo auth credentials. `POST /v2/auth/login` needs an admin-provisioned private SQLite DB; `POST /v2/me/dataset-inferences` additionally needs the trusted private CP1 cache. Without them, the authenticated demo cannot complete a real inference.

See `docs/deployment/04_authenticated_geolife_map_demo.md` for provisioning accounts and private cache mounts. The auth SQLite directory must be writable by non-root UID 10001 for session creation; the trusted CP1 cache should be read-only. Never put account DB/cache into the container image, public volumes or CI artifacts.

## Running the demo with accounts

Once the private accounts and mounts are provided, login with `POST /v2/auth/login`, then use:

- `POST /v2/me/inferences` for a new GPS sequence.
- `POST /v2/me/dataset-inferences` for the **authenticated account's** allocated research GeoLife user ID.
- `GET /demo` for the consent-gated map frontend.
- `GET /health/ready` for readiness (process/config only, not external AWS dependency health).
- `GET /v2/model-info` for declared model variants/rollout mode.

The `/v1/*` and anonymous `POST /v2/inferences` endpoints remain part of the API schema and Python standalone parity tests but are disabled with HTTP 404 when `GEOLIFE_PRIVATE_DEMO=1` **or** `GEOLIFE_DEMO_AUTH_DB` is set. Avoid using an unsafe override for AWS just to enable legacy inference.

## HTTP security and operational limits

- The app sets `Cache-Control: no-store`, clickjacking/nosniff/referrer headers, and an explicit CSP for `/demo`.
- Declared `Content-Length` over **3 MiB** receives HTTP 413; Pydantic caps each new-GPS request at 20,000 observations.
- **Chunked/streamed bodies must have separate ingress limits**; rate limiting, TLS, authorized ingress, per-IP throttling, timeouts and concurrency limits are **not implemented at application deployment level**.
- Do not expose the app over public plain HTTP; `-p 127.0.0.1:8000:8000` binds only to loopback for local testing.
- The `/internal/metrics` endpoint is disabled unless a server Bearer token is provided. Restrict metric scraping to a private network.
- The current CP2-v2 baseline uses complete-link 200m. DBSCAN 100m is a routed comparator, not a trained model/accuracy upgrade.
- Pin deploy artifact by immutable image digest/Git SHA, review supply-chain security and configure AWS cost alerts/IAM before deployment.

## CI and next steps

The `.github/workflows/docker-smoke.yml` workflow builds the image and verifies health/OpenAPI, anonymous legacy inference **blocked**, demo HTML served, and dataset endpoint requiring authentication. Normal GitHub Python CI still validates the frozen v1 contract outside the restricted runtime. CI tests **do not** provision AWS or validate historical participant identity.

No AWS service, async SQS flow, public identity provider or production monitoring dashboard has been deployed.
