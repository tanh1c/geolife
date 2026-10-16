# GeoLife frontend (local synthetic demo)

Requires Node.js and a local GeoLife FastAPI server on `127.0.0.1:8000` with `GEOLIFE_DEMO_AUTH_DB`, `GEOLIFE_PRIVATE_DEMO=1`, and `GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER=1`. Provision a demo account outside the repository using `scripts/provision_demo_users.py`; never commit credentials.

From `frontend/` run `npm ci` and `npm run dev`, then open `http://localhost:3000/`. The GeoLife panel proxies `/v2` to local FastAPI; recommendations use synthetic fixtures only. Other booking screens are UI previews, not real rides.

Run `npm run typecheck` and `npm run build` to check the frontend.
