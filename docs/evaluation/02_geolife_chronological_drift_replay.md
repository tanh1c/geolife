# Track B1 — P0 chronological GeoLife replay (private/offline)

**Status:** source + synthetic tests implemented; **real Modal run NOT YET VERIFIED**. This is the required stay-derived historical replay step. It does NOT change frozen CP1/CP2, use AWS or imply production drift detection.

## Purpose / data boundary
- Reads only the operator-trusted frozen CP1 pickle, preferably \`/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl\` (fallback \`/mnt/geolife-data/cache/cp2_home_office/stays_baseline_v1.pkl\`).
- Enforces **5,821 stays / 136 stay users** and required columns; refuses missing/invalid timestamps, coordinates, timezone resolution, or insufficient monthly support.
- Uses per-stay **IANA local arrival hour**, dwell-duration buckets, and binned distances between consecutive stays of the same user (only if intervening gap is 0–24 hours). Data are ordered by **UTC arrival timestamp**.
- Uses stable calendar months as windows; the first 3 supported months form the **past-only reference**, with at least 30 stays, 5 distinct users and 7 UTC arrival dates per supported month.
- Fixed 0.5 pseudocount JS divergence in bits; exploratory threshold 0.12; 2 consecutive supported windows to emit \`observed_shift_candidate\`. Low-support windows suppress bins and reset streak. This is *not* an independently calibrated threshold.
- A separate **constructed histogram injection** demonstrates a two-window \`simulated_alert\`. Synthetic injection is never mixed into actual monthly GeoLife observations.
- Report JSON contains only month-level histograms, support-safe stay counts, JS values, config and limitations. No user IDs, rows, locations, raw GPS, filenames, tokens or coordinates. Any monthly output from private data still requires human disclosure review.

**Caveat:** GeoLife spans nonuniform years/users/places. Differences can come from participation/sampling, not changed behavior. These CP1 stays are trajectory-derived summaries; no claim of raw-point chronological streaming, newly trained HOME/OFFICE labels, semantic label accuracy, real-time alarm, or live production drift.

## Run on the existing Modal Notebook (NO raw PLT rescan)

Use the same existing Modal Volume, but install/run from a **separate checkout/worktree** of the replay PR to avoid affecting another active branch. On Modal:

\`\`\`bash
git clone --branch feature/track-b1-geo-chronological-drift --single-branch https://github.com/tanh1c/geolife.git /tmp/geolife-drift-review
cd /tmp/geolife-drift-review
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_geolife_chronological_drift.py
python scripts/replay_geolife_chronological_drift.py
\`\`\`

If the checkout already exists, use a safe \`git fetch\` / \`git pull --ff-only\`, **never** reset active workspaces. Alternatively open \`notebooks/09_geolife_chronological_drift_replay.ipynb\` from the checkout and set \`GEOLIFE_REPO_DIR\` to the checkout path.

Default sanitized aggregate files generated **outside the mounted Volume** under \`/tmp/geolife-chronological-drift/\`:
- \`chronological_drift_aggregate.json\`
- \`chronological_drift_js.png\`
- \`injected_alert_demo.png\`

No files are written to Git or private Modal Volume automatically. Only send a sanitized short summary (reference months, number of eligible windows, whether constructed alert triggered, whether figures were created); share aggregate figures only after checking privacy. Do not upload private pickle, user-level rows, exact dates, coords or private notebook outputs.

## Acceptance gates
1. Synthetic CI tests and plot generation PASS; import/JSON notebook valid.
2. Operator-run **private real cached GeoLife**: FROZEN parity PASS; window support sufficient; output privacy review PASS.
3. Chronological chart and separately labeled constructed alert available; observations not labeled as production drift.
4. Keep initial run evidence as operator-reported, separate from synthetic CI. No AWS trial and no production semantic thresholds are changed.
