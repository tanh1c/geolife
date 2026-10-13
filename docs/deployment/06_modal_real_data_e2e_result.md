# Modal real-data E2E acceptance result — 2026-10-13

**Status: PASS (user-reported executed Modal output)**  
Scope: `scripts/modal_real_data_e2e.py` using the existing, private GeoLife CP1 stays cache.  
Source of evidence: sanitized JSON output supplied by the operator on 2026-10-13. The assistant has not independently accessed the private Modal Volume.  
PR: https://github.com/tanh1c/geolife/pull/72

## Measured frozen parity

| Check | Actual reported | Frozen expected | Result |
|---|---:|---:|---|
| CP1 stay events | 5,821 | 5,821 | PASS |
| Users with stays | 136 | 136 | PASS |
| Semantic locations | 2,015 | 2,015 | PASS |
| Recurring locations | 716 | 716 | PASS |
| Recurring users | 104 | 104 | PASS |
| HOME emissions | 27 | 27 | PASS |
| OFFICE emissions | 16 | 16 | PASS |

## HTTP/authenticated integration gates

The reported `case_count` is **4**, with these abstract case types only:

- `HOME`
- `OFFICE`
- `RECURRING_ABSTAIN`
- `NO_STAY`

The executed script returned overall **`status: PASS`** and listed all of the following passed gates:

1. `frozen_full_release_parity`
2. `authenticated_real_cache_inference`
3. `per_user_map_label_coordinate_parity`
4. `real_cache_home_office_recurring_abstain_no_stay`
5. `request_body_user_override_blocked`
6. `unauthorized_access_and_token_revocation`
7. `synthetic_new_gps_mode`

The report also indicated `cache_exported: false`, `private_identifiers_exported: false` and `credentials_persisted: false`. These flags summarize the script's behavior and do not constitute a forensic inspection of the host or network.

## Interpretation and release decision

**The previously outstanding private-cache real-data E2E gate is satisfied according to the operator's output.** This supports:

- Frozen CP2 aggregate parity on the 5,821-event real cache;
- authenticated dataset-mode API responses matching the direct baseline model on selected real-data subjects, including 3-decimal map-marker coordinates;
- session isolation, forged user selection being ineffective, and token revocation;
- new-GPS inference integration on a **synthetic** request.

It **does not** prove: ground-truth correctness of HOME/OFFICE, actual web-map rendering against real data (browser check used synthetic data), all 182 accounts individually tested, public authentication security, authorization security under hostile workloads, AWS deployment, or SQS serving.

**Merge readiness:** local browser/synthetic E2E PASS (reported previously); GitHub CI and Docker smoke PASS; private cache real-data E2E PASS (operator-reported). The technical test gate is complete. PR #72 should be reviewed for restricted/internal deployment scope and its unauthenticated compatibility routes before changing Draft status or merging. Never expose GeoLife individual HOME/OFFICE locations publicly just because these tests pass.

## Privacy/provenance

Only aggregate counts, gate identifiers and case types are recorded here. No GeoLife user IDs, GPS coordinates, individual candidate scores, credentials, tokens, SQLite DB or CP1 cache are stored in this repository.

See `docs/deployment/05_modal_real_data_e2e.md` for the command and detailed assertions.
