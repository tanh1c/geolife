# Authenticated GeoLife map demo — Track B1

Status: **implemented code on feature branch, not deployed to AWS**. The UI is at `GET /demo`. This demonstrator is intended for a controlled local/internal teaching environment, **not** identity verification of the original GeoLife participants.

## Threat model and account policy

GeoLife `000` through `181` are research dataset pseudonyms, **not actual login identities**, and their owners cannot be authenticated from the dataset itself. A raw user ID must not grant access to private stay history or inferred HOME/OFFICE locations.

- Admin **explicitly provisions** a synthetic demo account and maps it to exactly one GeoLife dataset ID. Self-registration, listing all 182 IDs, and requesting an arbitrary dataset ID are disabled.
- Credentials are independent high-entropy passwords with salted PBKDF2-HMAC-SHA256 (600k rounds). Each account gets an independently generated salt.
- A successful login creates a cryptographically random 30-minute bearer token; only its SHA-256 digest is stored in SQLite. `POST /v2/auth/logout` revokes it. Browser keeps token **in memory**, not localStorage.
- Five failed logins lock an existing account for 15 minutes (demo control, **not** distributed rate limiting).
- Auth SQLite DB must be provided at an absolute private path via `GEOLIFE_DEMO_AUTH_DB`. No accounts/default passwords are in the repository or image.
- Separate authenticated endpoints never accept `dataset_user_id` in a request body/path as an access selector; they derive it exclusively from the authenticated session.
- Run behind TLS, restricted ingress, a trusted demo population and proper response/cache-log controls. The restricted Docker service defaults to `GEOLIFE_PRIVATE_DEMO=1`, which blocks anonymous `/v1/*` and `POST /v2/inferences` (404). Setting `GEOLIFE_DEMO_AUTH_DB` also activates the gate. These compatibility routes remain available only in standalone non-demo Python parity tests. **Do not expose the app to the internet without TLS/network/auth/privacy controls.**

## Local setup: private credential database

Run from project root after `pip install -e '.[dev]'`:

```bash
mkdir -p /mnt/geolife-private
chmod 700 /mnt/geolife-private
python scripts/provision_demo_users.py \
  --db /mnt/geolife-private/demo_auth.sqlite3 \
  --user-id 000 --account-id demo_000
```

The CLI prompts for a password (min 12 chars), avoiding shell-history leaks. Provision the other demo accounts one-by-one if needed.

Optional **controlled all-182 training accounts**:

```bash
python scripts/provision_demo_users.py \
  --db /mnt/geolife-private/demo_auth.sqlite3 \
  --all --credentials /mnt/geolife-private/one-time-credentials.csv
```

The CSV contains **plaintext randomly generated passwords** and is only intended as a temporary administrator handoff. File permissions are 0600; handle offline with strict access and delete securely when no longer necessary. This is **not** an enrollment of the historical people who contributed GeoLife data.

The SQLite DB itself also contains hashed passwords and private session data; keep it out of public repos, Docker images, notebooks, logs and screenshots.

## Connect the existing private CP1 stay cache

The dataset mode is purposefully fast: it uses the **existing frozen 5,821-stay CP1 cache**, not expensive raw .plt parsing on every request. That is the same observed stay table used to produce HOME 27 / OFFICE 16 under CP2-v2. It only reads the current account's `user_id` after auth.

Example **Modal Volume mount**:

```text
/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl
```

Do not copy the user-level stay cache into GitHub, the Docker image, or an unprotected public AWS image. The `.pkl` file uses `pickle`: it must be produced by a trusted source and kept writable by admin only. Never load a client-submitted pickle.

Configure environment before starting the service:

```bash
export GEOLIFE_DEMO_AUTH_DB=/mnt/geolife-private/demo_auth.sqlite3
export GEOLIFE_STAYS_CACHE="/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl"
uvicorn geolife.api.app:app --host 127.0.0.1 --port 8000
```

Then open `http://127.0.0.1:8000/demo`, log in using the explicit account credential and select a mode. To run Docker, bind-mount `/mnt/geolife-private` and `/mnt/geolife-data` **read-only** inside the container (the auth DB needs write access for sessions, so make only auth DB directory writable for the container UID; do not mount the whole raw-data Volume writable). This is an internal/demo setup, not an AWS deployment instruction.

If the cache is not mounted, **new-GPS mode still works**, but dataset mode returns HTTP 503 with a safe explanation. A dataset user with no CP1 stays receives a valid empty/abstained result, not a fake HOME/POI.

## Two user experiences

### Option A — new GPS trajectory

Authenticated `POST /v2/me/inferences` accepts `{"points": [...]}` with timezone-aware `timestamp_utc`, valid lat/lon and up to 20,000 points. The UI accepts pasted JSON or client-side parsed `.plt`/`.json` files; the service applies frozen CP1 cleaning + stay detector, then frozen CP2-v2 complete-link inference. This mode does not modify the private cache.

### Option B — historical GeoLife dataset user

Authenticated `POST /v2/me/dataset-inferences`, no user ID parameter. Account -> authorized dataset ID from private SQLite -> select its stays from trusted CP1 cache -> CP2-v2 inference -> map markers. **A different account can't ask for someone else's GeoLife ID via request parameters.** Records without stays cannot produce semantic locations under this mode.

Both return `dataset_user_id`, `source`, `detected_stays`, `recurring_locations`, typed HOME/OFFICE emitted-or-abstained details with heuristic evidence, and `map_locations`:

```json
{
  "location_ref": "L0",
  "label": "HOME",
  "latitude": 39.904,
  "longitude": 116.407,
  "evidence_score": 0.82,
  "visit_count": 3,
  "note": "Heuristic time-window inference"
}
```

Example **shape only**, not measured from a real GeoLife participant. HOME and OFFICE labels are **not ground truth**. `OTHER_RECURRING` markers are generic recurring places; external restaurant/school/store POI categories were never verified. `location_ref` is **request-scoped**, not a persistent database primary key.

### Map / third-party disclosure

Markers round lat/lon to 3 decimals (typically ~100 m, depending on latitude). This is **coarsening**, not anonymization. A user must actively check a consent box and click **Hiển thị bản đồ** before the browser loads Leaflet from CDN and fetches OpenStreetMap raster tiles. The tile/CDN providers can receive approximate geographic/tile information and IP/network metadata. Do not enable external maps for sensitive real-world users without reviewing provider terms/consent, or replace with self-hosted tiles and local JS.

No map coordinates enter unauthenticated v1/v2 response contracts. Coordinates are exposed only through the authenticated demo endpoints.

## Endpoint inventory

| Method | Path | Authentication | Description |
|---|---|---|---|
| GET | `/demo` | HTML shell public; contains no data | Login / input / map UI |
| POST | `/v2/auth/login` | account/password | 30-minute token; configured DB required |
| POST | `/v2/auth/logout` | Bearer | Revokes session |
| GET | `/v2/auth/me` | Bearer | Account and assigned GeoLife ID |
| POST | `/v2/me/inferences` | Bearer | New trajectory inference, map markers |
| POST | `/v2/me/dataset-inferences` | Bearer | Authorized cached GeoLife stays inference |

Original stateless `POST /v2/inferences` and v1 endpoints exist for standalone Python regression parity, but are **disabled** inside the restricted Docker/demo runtime; they do not provide dataset lookup or authenticated map coordinates.

## CI and acceptance

`tests/test_demo_auth_map.py` exercises provisioned accounts, bad password, missing auth, login/logout revocation, disjoint synthetic locations for 2 different dataset IDs, attempted cross-user selection, new-GPS workflow, missing cache 503, UI availability and OpenAPI. No historical raw trajectories or user-level real GPS data are included in tests.

For a real privacy-reviewed public deployment, further work is mandatory: HTTPS and authentication enforcement across all routes, CSRF/XSS/CSP hardening for UI, login rate limiting at ingress, account-management audit, secure secret rotation, cookie/token policies, tile-host privacy, backup/retention, monitoring, an independent security review, and AWS IAM/network policy. **This is a research demo, not a secure multi-tenant production identity platform.**


## Deployment-facing acceptance gates

- A logged-in demo account can open only its server-bound dataset ID; a forged JSON user ID does not switch account context.
- Unauthenticated or expired bearer sessions receive HTTP 401 for both map-producing endpoints.
- Without `GEOLIFE_STAYS_CACHE`, historical dataset mode returns 503 instead of silently guessing predictions; fresh GPS mode remains usable.
- Swagger/OpenAPI describes auth and map endpoints, while `/demo` is just the HTML shell.
- Frozen CP1/CP2 inference semantics remain unchanged. In restricted demo mode the anonymous v1/v2 inference routes are **unavailable** (HTTP 404); compatibility/parity tests still run outside this mode.
- A human operator must still mount and grant access to the private GeoLife cache and separately provision demo accounts. No historical participant consent/identity can be inferred from an ID.


## Real-cache model/API parity gate

Local/browser tests already exercised synthetic trajectories and mock cache. To validate the **frozen private GeoLife** dataset without exporting stays, run `scripts/modal_real_data_e2e.py` inside an existing Modal Jupyter server with Volume mounted. It checks full CP2 frozen counts, then privately selects HOME/OFFICE/recurring-abstain/no-stay cases and verifies authenticated API responses and map marker rounding. Only aggregate PASS/FAIL is displayed. The script is described in `docs/deployment/05_modal_real_data_e2e.md`. This step is a merge gate; it has **not** been run against the real private Volume by CI.


## Pre-merge security hardening (2026-10-13)

The final review found an anonymous compatibility API bypass and added a fail-closed restricted-demo gate. Docker now sets `GEOLIFE_PRIVATE_DEMO=1` by default, and configuring a demo auth database activates the same restriction even for Python-run demos. Authenticated `/v2/me/*` routes are unchanged. HTTP responses use `Cache-Control: no-store`, browser security headers and a consent-page CSP; requests declaring bodies above 3 MiB receive 413. The upstream proxy **still must** enforce a limit on chunked bodies, HTTPS ingress, login rate limits and other deployment-specific controls. See `docs/deployment/07_security_review_pre_merge.md`. **No public deployment is approved**.
