# GeoLife Mobility — local synthetic FE–BE demo (PR #76)

**Scope:** local research prototype / visual booking **simulation**, not Xanh SM or any real taxi dispatching, fare estimate, map routing, production identity service or public website. The frontend uses React + Vite + Tailwind and calls only the GeoLife account-authenticated **synthetic** recommender. Existing booking/search screens are demonstration UI; do **not** interpret displayed fare, ETA, map visuals or route as calculated from a suggested destination.

**Current demo journey (operator-reported local browser PASS, 2026-10-16):** Login → select hypothetical clock hour → backend gives account-scoped Top-3 destinations → select suggestion → inspect simulated booking flow. This does not confirm actual trips, charges or geo-routing. The simulated place labels are UI display aliases and the recommender ranks fake IDs, not real GPS coordinates.

## Prerequisites

- Python 3.11/3.12 and Node.js **24** (matching frontend CI; dependencies use Vite 8).
- Existing protected **demo SQLite** account DB outside Git. No real GeoLife cache is required or permitted for this frontend demonstration.
- Clone/fetch PR #76. Separate terminals for FastAPI and Vite; never expose either development server publicly.

## Start backend (PowerShell, from repository root)

```powershell
git fetch origin
git switch feature/destination-s1-synthetic-recommender
python -m pip install -e ".[dev]"

# Create only if you do not already have a test-only account DB:
New-Item -ItemType Directory -Force "$HOME\geolife-private" | Out-Null
$authDb = "$HOME\geolife-private\demo.sqlite3"
python scripts/provision_demo_users.py --db $authDb --user-id 000
# Password is prompted interactively. If demo_000 exists, skip provisioning.

$env:GEOLIFE_DEMO_AUTH_DB = $authDb
$env:GEOLIFE_PRIVATE_DEMO = "1"
$env:GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER = "1"
python -m uvicorn geolife.api.app:app --host 127.0.0.1 --port 8000
```

## Start frontend (a second PowerShell terminal, repo root)

```powershell
cd frontend
npm ci
npm run typecheck
npm run build
npm run dev
```

Open **http://127.0.0.1:3000/**. Vite development server is explicitly bound to **127.0.0.1**; its `/v2` proxy points to **127.0.0.1:8000**. Use `demo_000` and the prompted test password. No need for AWS, Modal, Terraform, ECR or internet-accessible ingress. Shut down both terminals using Ctrl+C.

### Automated checks

The GitHub Actions `frontend` job now performs clean `npm ci`, `npm run typecheck` and `npm run build` independently of Python CI and Docker smoke. **That is not a browser E2E test**. The optional local-only Playwright test is `tests/test_frontend_auth_flow.py`; it is intentionally skipped in GitHub CI without `FRONTEND_DEMO_PASSWORD` and both localhost servers. Operator reported local browser and typecheck/build/test PASS at commit `0cc667e`; remote CI results must be checked at the final head separately.

### Boundaries / review before publishing

- The auth backend is an internal SQLite bearer-session demo; this is **not** Cognito/OIDC or verified ownership of a historical GeoLife research `user_id`. The S1 endpoint restricts fictional visits by authenticated account ID and never reads private GeoLife stay PKL.
- No Evidence Score, calibrated recommendation probability, true HOME/OFFICE confidence or real-world routing/fare is supplied by the S1 recommender API. The frontend is a simulation shell and must label illustrated taxi screens accordingly.
- Branding/styles/assets derived from or visually similar to Xanh SM, VinFast and other businesses require **provenance, trademark, copyright, permission and independent visual differentiation review** before public distribution; this PR does not assert those assets are cleared. Replace with independent GeoLife Mobility identity and verified-licensed/own assets for public release.
- Do not serve `dist` as a public site, expose Vite with `--host 0.0.0.0`, widen EC2 inbound rules, or move GeoLife private cache/credentials to frontend bundle. Third-party map tiles and GPS coordinates require separate consent/privacy consideration.
- Track B1 original **Checkpoint 3** is still pending: SQS async job demo, sync/async result-latency comparison, monitoring dashboard, simulated drift replay.

See [S1 synthetic backend protocol](../docs/recommendation/01_s1_synthetic_destination_mvp.md) and the [Track B1 master roadmap (PR #75)](https://github.com/tanh1c/geolife/pull/75).
