# PR #72 — Security review and pre-merge decision (2026-10-13)

**Scope:** Track B1 **restricted/internal research demo** and compatibility API. This review is code-focused and is **not** a penetration test, independent legal/privacy assessment, AWS deployment review, or approval for an internet-facing service.

## Decision

**GO to human code review for internal research development:** security hardening Python CI + Docker smoke were both PASS at commit `bc4a30ad4814ce522fb7ebcaec90a851b8c41fd4`, and PR #72 was moved from Draft to **Ready for review**. Actual merge still requires human acknowledgment of restricted-only scope. **NO-GO for public AWS exposure, publishing historical GeoLife HOME/OFFICE locations, or claiming that accounts authenticate the original dataset contributors.**

Existing frozen baseline CP1/CP2 data-science behavior remains unchanged. The operator reported real Modal private-cache E2E PASS (5,821 stays; 136 stay users; 27 HOME; 16 OFFICE); see `docs/deployment/06_modal_real_data_e2e_result.md`. This output is not a security audit.

## Threat model and sensitive assets

- Historical Microsoft GeoLife pseudonymous research-user stay cache, inferred HOME/OFFICE points, raw GPS uploaded per request, and the distinction between research IDs 000–181 and real-world identities.
- Privately provisioned demo account IDs/password hashes; 30-minute revocable bearer sessions, authenticated map coordinates (rounded to 3 decimal places but **not anonymous**).
- Trusted GeoLife stay pickle read from an admin-supplied private mount (untrusted pickle would create code execution risk).
- Browser loads Leaflet resources and OpenStreetMap raster tiles **only after a separate consent checkbox**; even coarse tile region and client IP may be visible to third parties.

## Findings and changes

| ID | Severity for exposure | Finding | Mitigation/merge status |
|---|---|---|---|
| SEC-01 | HIGH | The older `/v1/*` and stateless `/v2/inferences` previously accepted arbitrary anonymous requests next to the new account-scoped demo. | **Mitigated for private demo runtime.** Middleware returns 404 on these paths whenever `GEOLIFE_PRIVATE_DEMO=1` or a demo auth DB is configured. Docker image now ships with `GEOLIFE_PRIVATE_DEMO=1` by default. Existing standalone Python v1 parity tests continue in non-restricted mode. Test and Docker smoke assert blocking. These routes remain described by OpenAPI for compatibility, but are unavailable in restricted runtime. |
| SEC-02 | MEDIUM | Login tokens, coordinates, and inferred location IDs could be retained in browser/proxy caches. | **Mitigated in app.** `Cache-Control: no-store` and `Pragma: no-cache` on HTTP responses; `Referrer-Policy: no-referrer`, `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, Permissions-Policy limiting camera/microphone/geolocation, and demo page CSP denying frames. Test asserts headers. Reverse proxies must not override these headers. |
| SEC-03 | MEDIUM | 20,000-point Pydantic limit does not by itself bound large JSON bytes. | **Partially mitigated.** FastAPI middleware rejects POST/PUT/PATCH bodies with declared `Content-Length > 3 MiB` using 413 and no echoed GPS. **Streaming/chunked bodies, per-IP rate limits, request timeouts and concurrency must be bounded at TLS ingress before any public exposure**. |
| SEC-04 | HIGH | GeoLife IDs are only research pseudonyms; nothing proves the bearer account is controlled by the original contributor. | **Known limitation; public deployment blocked.** No self-registration, server-side admin-only per-ID account provisioning, account-bound dataset queries, no arbitrary cross-ID selection. Only controlled internal use may exercise historical trajectories. No real-person login or open public lookup. |
| SEC-05 | HIGH | Historical HOME/OFFICE points are intrinsically sensitive; 3-decimal map rounding is not anonymity. | **Known limitation; public deployment blocked.** Authenticated endpoints only, request-scoped refs, map opt-in for third-party tiles; no precise coordinates emitted through the stateless API. Must review dataset sharing permissions, user access authorization, retention, and whether historical per-user marker maps should be available at all before deployment. |
| SEC-06 | MEDIUM | Demo auth uses a private SQLite session store with password hashing and account lockout but lacks distributed rate limits, audited account lifecycle, MFA, durable central session backend, revocation across replicas. | **Accept only for single-instance internal demo.** Require TLS + restricted network, high-entropy separate credentials, private 0600 SQLite filesystem and single-worker hosting. Cloud multi-replica/public deployment requires stronger identity and session management. |
| SEC-07 | HIGH if cache untrusted | `pd.read_pickle` of a file controlled by an attacker could execute code. | **Trust boundary documented, unchanged.** `GEOLIFE_STAYS_CACHE` must point to a versioned admin-generated, immutable/private file and must never be attacker-writable or request-selected. Convert to verified Parquet in a dedicated trusted conversion process before any multi-tenant cloud service. |
| SEC-08 | MEDIUM | Inline browser JS and third-party Leaflet CDN prevent strict no-inline CSP/SRI enforcement. | **Known residual for internal demo.** Added explicit `/demo` CSP, `frame-ancestors 'none'`, allowed CDN/tile domains. Client-side DOM uses `textContent` for untrusted labels. Prefer self-hosted pinned Leaflet scripts/styles and tiles or audited third-party policy before public deployment. |
| SEC-09 | MEDIUM | Unpinned broad Python dependency ranges and container base image tag can change over time. | **Follow-up** pin dependency lock/image digest, add dependency scanning/SBOM and confirm current CVEs prior to AWS deployment. GitHub CI alone is not a vulnerability scan. |
| SEC-10 | MEDIUM (functional) | The previously implemented canary selection runs on anonymous `/v2/inferences`; that route is correctly blocked in restricted Docker/demo mode. | **Not yet an authenticated-canary demo.** Keep the secure block. Before claiming an AWS canary deployment, move variant selection behind the authenticated `/v2/me/*` endpoints or a protected internal routing layer, and rerun model/version/rollout tests. |

## Positive controls verified by code/tests

- Password hashing uses PBKDF2-HMAC-SHA256 with per-account salt; wrong credentials do not reveal account mappings. Sessions are random, short-lived, store SHA-256 token digests, and can be revoked by logout.
- `/v2/me/dataset-inferences` derives GeoLife ID **only from server-validated token**; the request cannot select a different user's cache.
- `/v2/me/inferences` treats uploaded GPS independently from historical cache. Locations are output only to authenticated demo account.
- FastAPI validation error handler strips user input and Pydantic context, making it less likely to echo precise GPS.
- `/internal/metrics` is off by default unless a server-side bearer token is configured. Metrics labels use template routes and allowlisted model names, not raw URL/GPS.
- Docker COPY allowlist excludes data, credentials, tests and notebook outputs; process runs as non-root.
- Local/browser synthetic E2E, Modal real-data API E2E (operator-reported), Python CI and Docker smoke constitute **functionality/parity evidence**, not exploit testing.

## Merge checklist

- [x] Source inspected for raw GPS/credential exposure and unscoped historical lookup.
- [x] Restricted Docker runtime fail-closed legacy inference protection implemented.
- [x] HTTP no-store, basic anti-clickjacking/CSP and declared-body-size gate implemented.
- [x] Added security regression tests and updated Docker smoke expectations.
- [x] Real Modal private-cache E2E PASS per operator-provided sanitized output.
- [x] Security-hardening Python CI and Docker smoke PASS at `bc4a30ad4814ce522fb7ebcaec90a851b8c41fd4`. Check the final PR head's CI again after documentation-only commits.
- [ ] Human review/acknowledgment: **merge for internal research only**, not permission to expose per-user GeoLife history to the internet.
- [ ] Keep deployment-specific controls (HTTPS ingress, firewall, upstream body limits, login rate limits, secure secrets, privacy/data rights and audit) as blockers for public AWS deployment.

**Merge policy:** Merging implementation into `main` does **not** mean the service may be deployed publicly. PR #72 is **Ready for review, not merged**; an explicit human acknowledgment of internal-only scope is still required before actual merge. The user must approve the actual GitHub merge step separately.

## Operations warning

The Docker image's restricted default means the old `POST /v1/classify/{user_id}` and stateless `POST /v2/inferences` return 404 even though they appear in the same OpenAPI document. For a controlled demo use `POST /v2/auth/login`, then `POST /v2/me/inferences` or `POST /v2/me/dataset-inferences`. To run classic v1 parity tests use a local Python process **without** `GEOLIFE_PRIVATE_DEMO` and **without** `GEOLIFE_DEMO_AUTH_DB`. Never disable restricted mode just to expose a cloud endpoint.
