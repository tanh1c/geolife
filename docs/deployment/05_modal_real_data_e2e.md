# Modal private-cache real-data E2E — Stage serving acceptance gate

Status: **script and synthetic CI checks implemented; private Modal Volume execution NOT YET VERIFIED**.

Entry point: `scripts/modal_real_data_e2e.py`. This is the final acceptance check for PR #72 before considering a controlled demo merge, **not** another EDA study. It does not clone, recompute or read any raw `.plt` files. It does not create/deploy an HTTP server, does not contact external map providers, and does not write a report or credentials to the shared Volume.

## Why run on Modal?

The 5,821-event frozen CP1 cache is private and already lives on the mounted Volume. GitHub Actions uses synthetic data, so it cannot prove actual cached-user + login + inference + map-marker parity. Run the script as a **separate Python process on Modal** where `/mnt/geolife-data` is already mounted. The app is exercised directly via FastAPI `TestClient`, not a public URL.

The script deliberately outputs only aggregate reference counts, fixed test-case names and PASS/FAIL gate identifiers. Do **not** screenshot or share private selected IDs, returned coordinates, raw GPS, password/token/session data, or cache rows.

## Execute from an existing Modal Jupyter instance

In a terminal inside the running Modal Jupyter server (with Volume mounted), use a fresh worktree to avoid overwriting in-progress notebooks:

```bash
cd /tmp
git clone --single-branch --branch feature/track-b1-serving-delivery \
    https://github.com/tanh1c/geolife.git geolife-serving-audit
cd /tmp/geolife-serving-audit
python -m pip install -e ".[dev]"

# Confirm path exists without printing its contents:
test -f /mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl

# Does not read or parse raw GPS; does recompute frozen CP2 once.
python scripts/modal_real_data_e2e.py
```

Or run this as the only notebook cell on Modal (a subprocess avoids stale imports from older kernels):

```python
import subprocess, sys
subprocess.run(
    [sys.executable, "scripts/modal_real_data_e2e.py"],
    cwd="/tmp/geolife-serving-audit",
    check=True,
)
```

If the existing frozen baseline is located at another *trusted private path*:

```bash
python scripts/modal_real_data_e2e.py --cache /mnt/geolife-data/path/to/stays_baseline_v1.pkl
```

The script does not search for alternate pickle paths or read arbitrary uploads. Only supply a cache file whose provenance is known from your CP1/Stage 09 work.

## What PASS actually verifies

**Frozen aggregate gate** (actual cache and existing `HomeOfficeConfig`; strict):

| Metric | Expected |
|---|---:|
| CP1 stay events | 5,821 |
| Users with stays | 136 |
| Semantic stays | 5,821 |
| Semantic locations | 2,015 |
| Recurring locations | 716 |
| Users with recurring locations | 104 |
| HOME emissions | 27 |
| OFFICE emissions | 16 |

These values are the frozen baseline reported by Stage 09. A disagreement is a failed gate, **not** an opportunity to silently change thresholds or adopt Stage 08c experimental results.

**Automatically selected anonymous test cases** (identities never printed):

1. A user with HOME emission.
2. A user with OFFICE emission.
3. A user with recurring places but neither HOME nor OFFICE.
4. A dataset ID absent from CP1 stay users (valid abstention).

The script provisions one temporary 30-minute test session account per case; runs authenticated `POST /v2/me/dataset-inferences` on the real private cache; compares each returned stay count, recurring count, HOME/OFFICE emission/abstention, evidence score, marker membership and **rounded 3-decimal coordinates** with the same frozen model's direct output on that user.

Additional authorization/privacy checks:

- Anonymous dataset/new-GPS requests and `/v2/auth/me` return 401.
- Each account's `/v2/auth/me` returns only its provisioned dataset ID.
- Sending a forged `dataset_user_id` in the dataset inference request body does **not** change which user's cache is processed.
- Bogus/revoked session token returns 401, and logging out one account does not revoke the other account's session.
- A 15-point **synthetic-only** uploaded GPS fixture yields three 20-minute nighttime stays and HOME for the no-stay dataset account; it does not alter the private cached input.
- `/demo` HTTP HTML shell responds; **the map is not rendered** by TestClient (actual Leaflet rendering has already passed the separate local-browser synthetic test).

A valid completion output looks like this:

```json
{
  "audit": "real_geolife_cp1_cache_api_e2e",
  "status": "PASS",
  "frozen": {
    "stays": 5821,
    "stay_users": 136,
    "semantic_locations": 2015,
    "recurring_locations": 716,
    "recurring_users": 104,
    "home": 27,
    "office": 16
  },
  "case_types_tested": ["HOME", "NO_STAY", "OFFICE", "RECURRING_ABSTAIN"],
  "case_count": 4,
  "checks": ["..."],
  "cache_exported": false,
  "private_identifiers_exported": false,
  "credentials_persisted": false
}
```

The shown values are **expected test criteria**, not a claim that the run occurred.

## Privacy and operational details

- The script reads one **trusted** pandas pickle (unsafe if attacker-controlled; never load a user-uploaded pickle).
- Accounts are created only under `/tmp/geolife-e2e-*/audit_auth.sqlite3`, with cryptographically generated passwords and sessions. The directory is removed when the script completes, including after normal exceptions.
- The API app gets `GEOLIFE_STAYS_CACHE` and `GEOLIFE_DEMO_AUTH_DB` **only inside the child process**. No manual credentials or account exports are required.
- API marker coordinates and raw user IDs stay in memory; logs expose only aggregate counts and safe gate names. Any unexpected exception's detail is suppressed to avoid leaking private file paths/coordinates.
- The script uses direct frozen inference on the whole stay cache, then the authenticated API on four selected users. This is **not a CP1 rescan**. Expect model runtime and memory overhead from the complete-link and timezone evaluation.
- No third-party map tiles are contacted. Real-map browser rendering/consent on Modal or a separately configured internal app is not covered by this script; do not label it as verified on real data.

## Outcomes and next steps

- **PASS**: record the small sanitized JSON report in worklog (no users/coordinates), review PR #72 for appropriate internal-demo security scope, then consider merge. Cloud deployment is still a separate release/security decision.
- **FAIL with gate name**: share only the non-sensitive gate identifier. Do not relax thresholds, merge, or publish user-level results until investigated.
- **FAIL with UNEXPECTED_...**: a schema/library/implementation issue occurred. Keep the trace private and diagnose without posting raw cache contents.

CI unit tests: `tests/test_modal_real_data_e2e.py` use *synthetic fixtures only*, never the private Volume. Neither a green GitHub CI nor a successful synthetic local-browser test replaces this actual Modal execution.
