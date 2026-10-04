# Stage 07g — BCL POI 2008 normalization + lexical-context alignment

## Purpose

Stage 07f closed the BCL POI 2008 acquisition/provenance/CRS gate with:

- Figshare article 28667492;
- DOI `10.6084/m9.figshare.28667492.v1`;
- CC BY 4.0;
- official public RAR attachment;
- ArcGIS File Geodatabase `POI2008All.gdb`;
- point layer `POI2008CN`;
- 6,039,158 features;
- EPSG:4326;
- fields `PNAME`, `X`, `Y`;
- `runner_status = ready_for_normalization`.

Stage 07g therefore does not repeat source discovery or download work.

Its question is narrower:

> Do BCL-2008 place names provide independent historical lexical context near CP2-v2 recurring non-HOME anchors, and is that context stronger at the exact Stage-05b stable-secondary anchor than at same-user peers?

This remains an external-evidence audit. It does not create semantic WORK/OFFICE labels.

## CP2-v2 scope

The current Stage-07c production-aligned universe contains:

- 298 recurring non-HOME anchors;
- 29 users;
- location namespace `production_complete_link_200m_all_resolved_timezone_v2`.

BCL 2008 is temporally relevant to the explicit exact/+1-year window:

- 2007 proxy anchors: 2;
- 2008 exact-year anchors: 93;
- 2009 proxy anchors: 164;
- total BCL-eligible anchors: 259 / 298;
- BCL-eligible users: 23 / 29.

The earlier 07f handoff used the historical Beijing-v1 figure 185 / 198. Stage 07g must use the current CP2-v2 259 / 298 universe.

## Why Stage 07g is not Beijing-only

CP2-v2 removed the historical Beijing geofence and resolves timezone per stay.

Therefore Stage 07g must not reintroduce a Beijing-only spatial crop.

Instead it performs deterministic **anchor-neighborhood extraction** around the 259 temporally eligible anchors. Anchors outside the actual BCL source coverage naturally receive no nearby POI evidence; they are not removed by a new production geography rule.

## Source-integrity gate

07g reads the Stage-07f `acquisition_manifest.json` and requires:

- `source_id = bcl_poi_2008`;
- expected Figshare article/DOI identity;
- `runner_status = ready_for_normalization`;
- inspected container kind `gdb`;
- FileGDB path;
- EPSG:4326;
- `semantic_claim_allowed = false`;
- `occupation_inference_allowed = false`.

The Modal extraction worker also re-hashes the cached original RAR and checks it against Stage-07f SHA-256 before using the extracted FileGDB.

No network request is required.

## Spatial extraction design

Loading all 6,039,158 POIs into pandas is intentionally avoided.

07g:

1. groups eligible anchors into deterministic geographic tiles;
2. pads every tile by 150 m, larger than the final 100 m evidence threshold;
3. uses GDAL/OGR spatial filtering against `POI2008CN`;
4. selects only `PNAME`, `X`, `Y`;
5. deduplicates POIs returned by overlapping padded tiles;
6. stores the resulting neighborhood POIs privately on the Modal Volume;
7. applies an exact Haversine <=100 m radial gate per anchor.

The 150 m extraction padding is a retrieval guard only. Final evidence thresholds remain 25 / 50 / 100 m.

## Name preservation and lexical signals

The source has no trusted category field.

07g therefore preserves raw `PNAME` privately and derives only predeclared name-string signals.

Lexical signal families:

- business-name;
- education;
- healthcare;
- industrial;
- retail/service;
- transport;
- civic/institutional;
- residential;
- recreation/tourism.

Examples of the rule style include explicit terms such as `大学`, `医院`, `有限公司`, `工业园`, `商场`, `火车站`, `人民政府`, and `小区`.

These rules are heuristic lexical cues authored for the audit; they are not source-provided BCL categories.

Every extracted POI is explicitly assigned one of:

- `unknown`: no declared lexical signal;
- `single_signal`: exactly one declared signal family;
- `ambiguous_multi_signal`: more than one family.

No free-form classifier fills unknown names.

## Work-compatible lexical composite

For descriptive comparison only, the following lexical families form a broad work-compatible-name composite:

- business-name;
- education;
- healthcare;
- industrial;
- retail/service;
- transport;
- civic/institutional.

Residential and recreation/tourism are excluded from that composite.

This composite means only that the **name string contains a declared cue compatible with places where work activity can occur**. It is not a WORK/OFFICE label.

## Stable-secondary comparison

Stage 07g reuses the audited Stage-07e mobility-role alignment:

- exact stable-secondary candidate = Stage-05b `dominant_location_id`;
- same-user recurring non-HOME anchors = peers;
- Stage-07b factorized axes are authoritative.

Only users whose exact candidate is temporally eligible for BCL 2008 and who have at least one BCL-eligible peer enter the paired comparison.

Primary thresholds:

- 25 m;
- 50 m;
- 100 m.

For each user:

- candidate broad lexical-context indicator;
- peer-anchor context share;
- candidate minus peer share.

Aggregate means use a deterministic user bootstrap.

Category-specific candidate-vs-peer summaries are also produced so a positive composite cannot hide whether the signal is driven by education, retail/service, business-name, or another name family.

## Outputs

Private:

- `bcl_neighborhood_pois_private.pkl`;
- `bcl_neighborhood_pois_classified_private.pkl`;
- `anchor_poi_matches_private.pkl`;
- `anchor_bcl_lexical_metrics_private.pkl`;
- `mobility_aligned_bcl_context_private.pkl`;
- `stable_secondary_bcl_comparisons_private.pkl`.

Aggregate:

- `source_manifest_gate.csv`;
- `bcl_eligibility_summary.csv`;
- `spatial_extraction_summary.csv`;
- `lexical_status_summary.csv`;
- `lexical_category_threshold_summary.csv`;
- `stable_secondary_bcl_summary.csv`;
- `stable_secondary_bcl_category_summary.csv`;
- `profile_axis_bcl_context_summary.csv`.

Cache root:

`/mnt/geolife-data/cache/cp2_v2/07g_bcl_poi_2008_alignment/`

## Interpretation boundary

Stage 07g may report lexical-name evidence only.

It must not infer:

- true workplace;
- OFFICE;
- HOME;
- occupation;
- employment status;
- employer identity.

A nearby BCL name cue is external historical context. Absence of a cue is not real-world absence, and presence of a cue is not semantic ground truth.

## Decision rule

A useful positive signal for stable-secondary geometry would require:

- enough paired users;
- consistent candidate > peer differences across 25 / 50 / 100 m;
- category decomposition that is not driven by one incidental lexical family;
- uncertainty that supports the directional claim.

A null/mixed result remains a valid negative result and must not trigger mobility-threshold tuning.
