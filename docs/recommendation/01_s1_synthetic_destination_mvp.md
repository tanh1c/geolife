# GeoLife S1 — Private synthetic-first destination recommendation MVP

**Date:** 2026-10-15.  
**Status:** implemented as a guarded development research prototype; CI and local run status must be recorded separately. **Not** a production recommender, HOME/OFFICE truth, public API, user OAuth integration or deployed AWS service.  
**Priority source:** agreed post-AWS roadmap 2026-10-15 and unified Track B1 plan (PR #75, not yet merged when S1 started). The original Track B1 Checkpoint 3 SQS, monitoring and drift requirements remain mandatory for declaring the full track complete.

## 1. Question and boundary

Given a fictional app user with visits to places they previously chose, and *known at request time* origin, local timestamp and weekday, return at most **Top-3 suggested destinations** and descriptive reasons. This is **not** a classifier for whether a place is HOME/OFFICE. The numerical ranking score stays internal and must never be presented as a calibrated probability, Evidence v1 confidence, "percentage of correct HOME", or an inferred real person's data.

S1 intentionally isolates the method from Stage06/07 private GeoLife history, CP1 stays PKL, inferred HOME/OFFICE, Stage08 candidate tiers, and AWS cloud services. The server-owned `fixture_visits()` uses fictional destination IDs and independent fake demo account IDs. This prevents mistaken mapping between an authenticated demo account and a historical GeoLife research participant.

## 2. Pure recommender and baselines

Implementation: `src/geolife/recommendation/destination.py`, fixtures: `fixtures.py`.

Each visit contains only:
`owner_id`, `place_id`, aware `observed_at`, optional `origin_place_id` — **no GPS coordinates**.

For every `owner_id` independently, only events **strictly earlier than query_at** can count toward the rank. A candidate requires at least two earlier visits. The query origin (if given) is excluded from destination suggestions. If nothing qualifies, return **abstain / no suggestion**, never invent HOME/OFFICE.

Three deterministic methods, exact same eligible candidates:

1. **frequency**: order by number of prior visits, tie-break by recent visit and lexical place ID.
2. **recency**: order by time since latest visit, tie-break by visit count and lexical place ID.
3. **contextual**: weighted, uncalibrated heuristic over past frequency share (0.35), seven-day normalized recency (0.20), visits within ±2 local hours (0.20), matching weekday (0.10) and fraction of visits from current origin (0.15). Tie-break by count, recency and place ID. The model reasons use simple descriptions rather than showing any numerical score.

The weights are **prototype engineering defaults**, not fit to GeoLife or validated across people/cities. No arbitrary percent confidence. No place name is semantically guaranteed, and the UI must distinguish **suggested**, **user-confirmed** and **unknown**.

## 3. Offline evaluation protocol (anti-leakage)

Script: `scripts/evaluate_destination_synthetic.py`.

- Per synthetic owner, sort time then place; earliest `max(3, floor(0.70*n))` observations are TRAIN.
- The **first held-out** observation is exactly one future positive target. Its time and origin are assumed known as query context. Its destination and **all later FUTURE visits** are not available to scoring.
- Fail closed if TRAIN/FUTURE boundary has identical timestamps; no random split, no model fitting on FUTURE.
- Evaluate the same candidate set and target for contextual, frequency and recency, including no-suggestion and unknown/cold-start targets in denominator.
- Output **aggregate only**: evaluated query count, novel held-out targets, Hit@1, Hit@3, Recall@3 and no-suggestion rate per method. Because this protocol has **one relevant destination per query**, Hit@3 and Recall@3 are numerically identical. This does **not** establish real-user utility, HOME/OFFICE accuracy, statistical superiority or calibration.
- Four completely synthetic fixture owners are a code/regression smoke, **not** a statistically reliable recommender evaluation. Further work needs a larger consented or appropriately authorized dataset, multiple strict chronological query points per owner, uncertainty intervals and baseline comparisons before ranking weights are claimed better.

## 4. Off-by-default, authenticated API

Route: **GET `/v2/me/destination-suggestions`**.
Requires the *existing private demo bearer session*, `GEOLIFE_DEMO_AUTH_DB` and the explicit `GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER=1` flag. Disabled by default => HTTP 404 after auth; unauthenticated => HTTP 401.

Inputs: `when=2026-09-24T08:00:00+07:00` (offset required) and optional `origin_place_id`. Neither account ID, GeoLife user ID nor history may be selected by the requester; server always derives the owner from the verified demo session's `account_id`, then filters the **fictional fixture**. Another account's fake locations cannot be retrieved by changing query/body parameters. Existing legacy restricted-mode protections remain intact.

Success response includes only `source=synthetic_fixture`, `model=context_ranker_s1_v0`, `status`, Top-3 `rank`+`place_ref`+`explanations`, or `status=abstained` with a reason. No evidence score, numerical probability, GPS coordinate, GeoLife dataset user ID, or private file path. Authenticated synthetic account mapping **does not** prove identity of any real GeoLife contributor.

Do not enable this route for real-user public web app or transfer GeoLife participant data to AWS. Cloud/public access, Cognito/OIDC and per-resource permission design are separate approved workstreams.

## 5. Commands to run **locally** (no Modal, no AWS)

The Python test/CLI is all-synthetic. From a fresh repo clone with Python 3.11 or 3.12 and an isolated virtual environment:

```bash
git fetch origin
git switch feature/destination-s1-synthetic-recommender
python -m pip install -e ".[dev]"
python -m pytest -q tests/test_destination_recommendation.py tests/test_destination_api.py
python scripts/evaluate_destination_synthetic.py
```

Expected CLI: a JSON **aggregate** with `experiment=s1_synthetic_first_next_destination_first_heldout`, `evaluation_queries=4`, `novel_heldout_targets >=1`, non-null `methods.contextual/frequency/recency`, and `production_ready=false`. Do **not** interpret fixture Hit@3 as a measured GeoLife result.

Manual HTTP is **optional** after the automated tests pass. Use **only local synthetic accounts** with the existing private demo provisioning runbook (never hardcode/share passwords). Start a single private local app with `GEOLIFE_DEMO_AUTH_DB` set to a protected absolute SQLite path and `GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER=1`, then:

```text
GET http://127.0.0.1:8000/v2/me/destination-suggestions?when=2026-09-24T08%3A00%3A00%2B07%3A00
Authorization: Bearer <test-only-private-session-token>
```

Never paste an actual bearer token, credentials, auth DB, raw coordinates or Terraform state in chat. Synthetic tests are sufficient to validate API ownership and disabled-by-default policy; no immediate local rerun is necessary if GitHub CI passes.

## 6. Acceptance and next gate

| S1 gate | Current implemented design |
| --- | --- |
| Deterministic Top-3 with user-scoped history, causal timestamp boundary | Implemented; needs verified test run |
| Frequency & recency comparators on identical synthetic holdout | Implemented; needs verified test run |
| Hit@1 / Hit@3 / Recall@3 / no-suggestion aggregate, cold-start accounting | Implemented; needs verified test run |
| 401 unauthorized, flag-disabled 404, no cross-owner place IDs, no numeric score/GPS | Tests included; needs verified test run |
| Immutable CP1/CP2 baselines, Evidence v1 and current AWS | No changes made |
| Actual private Modal data / Stage06 trip transition integration | **NOT DONE / deliberate non-goal of S1** |
| Web UI visual Top-3 / user confirmation | **NOT DONE** |
| Multi-account real Cognito, public API and security review | **NOT DONE; separate approval** |
| Independently validated ranking quality on non-synthetic data | **NOT DONE** |

**Next after CI:** human review of S1 private synthetic MVP; optional local demo; then **S1b** design user-confirmed saved places with ownership/consent + typed source separation, richer origin→destination transitions and a genuinely held-out, legally usable non-synthetic recommendation benchmark (e.g. Gowalla/Brightkite as sparse check-ins for recommendation, **not** HOME/OFFICE truth), but only after explicit dataset/use/privacy approval. Continue separate Track B1 Checkpoint 3 SQS/monitoring acceptance per unified roadmap.

### Method/security sources

- [Microsoft Product Recommendations — chronological / last-event / fixed-date evaluation](https://github.com/microsoft/Product-Recommendations/blob/master/doc/model-evaluation.md)
- [Microsoft Recommenders — Recall@K definitions](https://microsoft-recommenders.readthedocs.io/en/staging/evaluation.html)
- [AWS ML Lens — independent holdout principle](https://docs.aws.amazon.com/wellarchitected/latest/machine-learning-lens/model-evaluation.html)
- [OWASP API1:2023 object-level authorization](https://api-security.owasp.org/editions/2023/en/0xa1-broken-object-level-authorization/)
