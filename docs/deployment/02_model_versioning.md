# Model variant registry — naming and release policy

This is an **inventory/plan**, not proof that two versions are deployed.

| Variant ID | Status | Actual implementation | Cluster policy | Role |
|---|---|---|---|---|
| `cp2-v2-complete-link-200m` | implemented in Python; HTTP v1 uses this | `geolife.model.infer_home_office` + `HomeOfficeConfig()` | complete-link diameter <=200 m | frozen reference |
| `cp2-v2-dbscan-100m` | IMPLEMENTED v2 candidate routing and synthetic distinctness test; not deployed on AWS | `HomeOfficeConfig(clustering_method="dbscan", dbscan_eps_m=100.0)` | DBSCAN eps 100 m; may chain | candidate benchmark |
| `per-stay-time-v1` | design only | **not implemented** | no spatial recurrence clustering | if mentor specifically wants direct-per-stay baseline |

Current `cp2-v2` version string describes the **semantic policy generation**, not an artifact trained with MLflow. For deployment, label image releases immutably (Git SHA or image digest) and record:
`api_version`, `model_variant`, `release_sha`, `config_fingerprint`, and `routing_mode`.

**Model-version baseline check:** two truly deployable versions require independent tests that they select different behavior on a predeclared synthetic fixture; pointing both IDs to the same default inference is not a legitimate second version. DBSCAN should not be misrepresented as the current production default. The baseline per-stay variant can be implemented later only if necessary, because the deliverable permits an adapted demonstration.

**Rollout admission:** comparative candidate must pass contract/parity tests, privacy checks, and synthetic known-difference tests. Freeze all CP1 cleaning/stay detector thresholds when comparing clustering variants. Do not use different model outputs to claim supervised accuracy on GeoLife.

Deployment status: no AWS registry/S3 artifact or running weighted route exists yet. See `docs/roadmap/track_b1_delivery_roadmap.md`.


## Implemented routing API (feature branch)

`POST /v2/inferences` uses one of the two genuine model configurations, selected server-side. Runtime metadata is visible via `GET /v2/model-info`. A stable HMAC bucket on `client_request_id` (opaque, non-PII) routes 10% to DBSCAN in `GEOLIFE_ROLLOUT_MODE=canary`, while `baseline` mode selects 100% complete-link. Set `GEOLIFE_RELEASE_ID` to the immutable deployed SHA or digest; its default `local-unversioned` is not a production release label. Model changes remain comparison variants, not evidence of better accuracy.
