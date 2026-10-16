# S1b frontend–backend integration audit — 2026-10-16

**Scope:** PR #76, synthetic-only local mobility demo. No real rides, fare, map routing, GeoLife participant access, public ingress, production OAuth or new AWS infrastructure. This page documents which parts were operator-verified locally and which remain technical/release follow-ups.

## 1. Latest FE–BE milestone

At PR head `0cc667e9c3029e0ac769f09ed486b47e2833992d`, operator reported a local demo (FE typecheck/build, 11 recommendation/API tests and local browser flow):

`login → choose simulated hour → GET /v2/me/destination-suggestions → account-bound Top-3 → select destination → booking UI simulation`.

Observed limitations: map/routing/ETA/price are not calculated from Top-3; no real ride order is created. Frontend `placeName(place_ref)` converts **fictional** recommendation refs to generic UI labels and should **not** be represented as a geocoded POI. The backend ranks synthetic visit fixtures, not the user's or a GeoLife participant's real trip history. User login uses restricted demo SQLite sessions, not Cognito/OIDC.

**Source review:** `frontend/src/GeoLife.tsx` authenticates and queries suggestions, `App.tsx` keeps session in React memory and drives navigation, `RideBooking.tsx` contains hardcoded example fares/ETAs. `frontend/vite.config.ts` proxies `/v2` to local FastAPI. Playwright test `tests/test_frontend_auth_flow.py` needs a configured private local account/password plus both servers and is **skipped in CI** absent `FRONTEND_DEMO_PASSWORD`. Python CI/Docker smoke **PASS on 0cc667e** but did not initially build or typecheck the React bundle.

## 2. Changes in response to code review

- Added a dedicated frontend job in `.github/workflows/ci.yml`: Node 24 `npm ci`, TypeScript typecheck and production Vite build. No use of real GPS or cloud secrets.
- Corrected a **Windows-produced incomplete npm optional platform package-lock**: Linux CI clean `npm ci` failed, so regenerated lock data on a GitHub Linux runner and committed the expanded lockfile. Removed the temporary export diagnostic; CI again uses strict `npm ci`.
- Added the missing `frontend/index.html` entry point required by Vite (it was absent from PR at initial review).
- Changed Vite dev binding from `0.0.0.0` to **`127.0.0.1`**, both `dev` npm script and `vite.config.ts`. Keep FastAPI on `127.0.0.1:8000`. Vite is a dev server, not public TLS ingress.
- Added a visible **demo-only** explanation atop the booking page: hardcoded car prices/ETAs and map do not come from recommendation or real booking APIs; no taxi service affiliation is claimed in the disclaimer.
- Updated `frontend/README.md` with two-terminal PowerShell commands and the limitations.
- **Acceptance pending at doc creation:** final head `ci`/frontend job and Docker smoke must pass. A local operator can optionally rerun browser smoke after updating branch; no Modal/AWS checks are required.

## 3. What to do next according to the unified roadmap

| Area | Status | Next gate |
| --- | --- | --- |
| S1a backend contextual Top-3 / synthetic holdout | Implemented + Python regression tests | Broader non-synthetic legally authorized recommendation evaluation remains future research |
| S1b FE–BE synthetic login/Top-3/booking shell | Operator-reported local PASS; new CI build required | Review UX caveat after pulling fixes; keep PR Draft until approved |
| S1b user-confirmed saved places/ownership lifecycle | **Not implemented** | Design source-of-truth place storage, ownership and consent; no linking Cognito account to original GeoLife user ID |
| S1b geospatial place catalog/map/routing/fare | **Not implemented** | If pursuing true geospatial demo, add synthetic catalog + clearly demo map/routing; don't invent ETA or charge |
| S2 **original Track B1 mandatory** async serving | **Not implemented** | Contract `POST /v2/jobs` → encrypted short-TTL job payload → SQS pointer-only queue → idempotent worker + DLQ → owned `GET /v2/jobs/{job_id}`; compare complete-result times sync vs async |
| S3 **original Track B1 mandatory** monitoring/drift | **Not implemented** | CloudWatch dashboard, model/route p50/p95/p99 and errors, SQS queue metrics, labeled offline simulated drift replay |
| Identity/security parallel | Design in PR #75 | Cognito User Pool synthetic principals / OIDC Code+PKCE and object-level auth proof only after budget/privacy approval |
| Brand/licensing before public demo | **Not reviewed/cleared** | Confirm provenance and permission for Xanh SM/VinFast-inspired screenshots/logos/illustrations/brand names; rename/rebrand for public usage. Copying a look-and-feel does not confer asset license. |

**Release decision:** The existing functionality qualifies as an **internal synthetic interaction demo**, not a real ride-sharing app, a production destination recommendation service or completed full Track B1. Keep frozen CP1/CP2 and Evidence v1 unchanged; no private GeoLife caches on AWS.

**Operator handoff:** From `feature/destination-s1-synthetic-recommender`, run backend localhost 8000 + `cd frontend; npm ci; npm run typecheck; npm run build; npm run dev`, open `http://127.0.0.1:3000/`. Avoid re-provisioning an existing `demo_000` account. See `frontend/README.md`. Only sanitized logs or screenshots without private account tokens/coordinates should be shared.
