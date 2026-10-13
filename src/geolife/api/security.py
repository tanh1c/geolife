"""HTTP hardening for the *restricted research demo* deployment profile.

Legacy inference routes intentionally remain usable in standalone local Python
tests, preserving the frozen v1/OpenAPI contract. The Docker image opts into
GEOLIFE_PRIVATE_DEMO=1 by default; configuring the demo auth DB also enables
restricted mode automatically. In restricted mode legacy/stateless routes do
not accept public requests and cannot bypass per-account dataset authorization.

An application content-length guard is not a substitute for upstream ingress
limits on streaming/chunked bodies, concurrency, timeouts or rate limits.
"""
from __future__ import annotations

import os

from fastapi import Request
from fastapi.responses import JSONResponse

DEFAULT_MAX_BODY_BYTES = 3 * 1024 * 1024

DEMO_CSP = (
    "default-src 'self'; "
    "base-uri 'none'; object-src 'none'; frame-ancestors 'none'; "
    "form-action 'self'; connect-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://unpkg.com; "
    "style-src 'self' 'unsafe-inline' https://unpkg.com; "
    "img-src 'self' data: https://*.tile.openstreetmap.org https://unpkg.com; "
    "font-src 'self' data:"
)


def restricted_demo_mode() -> bool:
    return (
        os.getenv("GEOLIFE_PRIVATE_DEMO", "").strip() == "1"
        or bool(os.getenv("GEOLIFE_DEMO_AUTH_DB", "").strip())
    )


def _legacy_inference(path: str) -> bool:
    return path.startswith("/v1/") or path == "/v2/inferences"


async def secure_http(request: Request, call_next):
    path = request.scope.get("path", "")
    if restricted_demo_mode() and _legacy_inference(path):
        # A scoped demo never exposes a parallel anonymous GPS inference API.
        # The legacy routes remain in OpenAPI for cross-version compatibility;
        # requests in the restricted runtime are deliberately unavailable.
        response = JSONResponse({"detail": "Not found"}, status_code=404)
    elif request.method in ("POST", "PUT", "PATCH") and request.headers.get("content-length"):
        # Check *declared* length before FastAPI/Pydantic allocates input arrays.
        # Streaming bodies without Content-Length must be bounded at ingress.
        try:
            declared = int(request.headers["content-length"])
        except (TypeError, ValueError):
            response = JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
        else:
            if declared < 0:
                response = JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
            elif declared > DEFAULT_MAX_BODY_BYTES:
                response = JSONResponse({"detail": "Request body too large"}, status_code=413)
            else:
                response = await call_next(request)
    else:
        response = await call_next(request)

    # HOME/OFFICE coordinates and login tokens must never be cached by browser
    # shared proxies. No user IDs, GPS input or secrets are reflected in headers.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "geolocation=(), camera=(), microphone=()"
    if path == "/demo":
        response.headers["Content-Security-Policy"] = DEMO_CSP
    return response
