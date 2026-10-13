# Checkpoint 3 — metrics foundation (sync serving)

Status: **IMPLEMENTED IN CODE AND TESTS** on \`feature/track-b1-serving-delivery\`; Docker/CI final gate must pass. No CloudWatch/Grafana or AWS production dashboard has yet been deployed.

## What's measured

- \`geolife_http_requests_total{route,method,status,model}\`: request count.
- \`geolife_http_latency_seconds_bucket{route,method,model,le}\`: latency histogram, seconds.
- Default buckets: 5ms–60s. Metrics are **per-process**, not aggregated automatically across independent service replicas.
- Route uses **FastAPI route template**, not raw URL. For instance \`/v1/classify/{user_id}\`; the unrecognized-path label is \`__unmatched__\`. No raw request URL, user ID, GPS, response body, client-request token or exact coordinates are exported.
- \`model\` label permits only the two known model versions or \`not-applicable\`.

## Protected scrape endpoint

\`GET /internal/metrics\` is disabled (HTTP 404) if \`GEOLIFE_METRICS_BEARER_TOKEN\` is unset. It is otherwise available only with a valid \`Authorization: Bearer <token>\` header. Without it, HTTP 403. The endpoint is excluded from public OpenAPI.

For local Docker testing, put a strong random token in the ignored \`.env\` file:

\`\`\`bash
GEOLIFE_METRICS_BEARER_TOKEN=<local-secret>
GEOLIFE_ROLLOUT_MODE=baseline
GEOLIFE_RELEASE_ID=<git-commit-sha-or-image-digest>
\`\`\`

Then:

\`\`\`bash
docker run --rm --env-file .env -p 127.0.0.1:8000:8000 geolife-api:cp2v2
curl -H "Authorization: Bearer <local-secret>" http://127.0.0.1:8000/internal/metrics
\`\`\`

This is not meant to be an internet-exposed dashboard: keep the endpoint behind restricted networking/authenticated scraping. Mask the metrics token in CI and shell histories; never commit it.

## Example PromQL for Prometheus / Grafana

\`\`\`promql
# Per-route and per-model p50 (seconds)
histogram_quantile(0.50,
  sum by (le, route, model) (rate(geolife_http_latency_seconds_bucket[5m])))

# p95
histogram_quantile(0.95,
  sum by (le, route, model) (rate(geolife_http_latency_seconds_bucket[5m])))

# p99
histogram_quantile(0.99,
  sum by (le, route, model) (rate(geolife_http_latency_seconds_bucket[5m])))

# HTTP 5xx rate across the service
sum(rate(geolife_http_requests_total{status=~"5.."}[5m]))
/
clamp_min(sum(rate(geolife_http_requests_total[5m])), 1e-9)
\`\`\`

Because histograms estimate quantiles from buckets, these are not exact latency quantiles. For report-quality p50/p95/p99, also collect client-side request latency in a benchmark run, report load settings, warm-up, machine, and confidence limitations.

## Not yet built

- AWS CloudWatch alarm/dashboards; secure service-to-metrics forwarding.
- Per-label HOME/OFFICE abstention counters, drift signals, simulated chronological GeoLife replay.
- SQS-backed async flow, queue timings, per-job TTL and durable result store.
- Multi-process aggregation; cost alarms; production ingress rate/body limits.

Do not claim production monitoring or drift detection until those pieces are deployed and tested. In particular GeoLife is historical static data, so chronological replay is **offline simulated drift**, not real production drift.
