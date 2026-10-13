"""Privacy-safe request metrics for Track B1 local/CloudWatch/Grafana demo.

All label values are bounded route templates, status codes and model versions.
Never tag a metric with user_id, request ID, coordinates or raw path.
"""

from __future__ import annotations

import hmac
import os
import time

from fastapi import HTTPException, Request
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


HTTP_REQUESTS = Counter(
    "geolife_http_requests_total",
    "Geolife HTTP request count (no user identifiers).",
    ["route", "method", "status", "model"],
)
HTTP_LATENCY = Histogram(
    "geolife_http_latency_seconds",
    "Geolife HTTP request duration in seconds.",
    ["route", "method", "model"],
    buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5, 10, 30, 60),
)


def route_template(request: Request) -> str:
    route = request.scope.get("route")
    name = getattr(route, "path", None)
    # If routing failed, never use the raw URL path; it can contain user IDs.
    if isinstance(name, str) and name.startswith("/"):
        return name
    return "__unmatched__"


async def instrument_requests(request: Request, call_next):
    start = time.perf_counter()
    status = "500"
    try:
        response = await call_next(request)
        status = str(response.status_code)
        return response
    finally:
        route = route_template(request)
        if route != "/internal/metrics":
            model = getattr(request.state, "model_variant", "not-applicable")
            if model not in (
                "cp2-v2-complete-link-200m",
                "cp2-v2-dbscan-100m",
                "not-applicable",
            ):
                model = "not-applicable"
            HTTP_REQUESTS.labels(route, request.method, status, model).inc()
            HTTP_LATENCY.labels(route, request.method, model).observe(
                time.perf_counter() - start
            )


def protected_metrics(request: Request) -> Response:
    token = os.getenv("GEOLIFE_METRICS_BEARER_TOKEN", "")
    # Disabled by default, including on public demo deployments.
    if not token:
        raise HTTPException(status_code=404, detail="Not found")
    supplied = request.headers.get("Authorization", "")
    if not hmac.compare_digest(supplied, f"Bearer {token}"):
        raise HTTPException(status_code=403, detail="Forbidden")
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
