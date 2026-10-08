# GeoLife Notebook Measured Results Log

> Canonical notebook-output index for important measured results.
>
> This file is intentionally **measurement-first**. It does not replace the research narrative in `docs/worklog.md`, the lessons in `docs/learning-journal-vi.md`, or the detailed protocols in `docs/eda/*.md`.
>
> Initial scope: experiments executed after the 2026-09-29 mentor report, from Notebook 04 through Stage 08c.

## How to update this log

After a notebook is executed and accepted:

1. record the exact scope / denominator;
2. copy only measured outputs that were actually produced;
3. separate measurements from interpretation;
4. state whether the result is current, historical, or superseded;
5. record the policy/research decision;
6. never convert agreement into semantic accuracy when no ground truth exists.

Use this file as the quick source for weekly reports and milestone summaries. Use the linked stage docs/worklog for full methodology.

---

# Current production snapshot — CP2-v2

Status: **CURRENT**

```text
CP1 stays                    5,821
stay-bearing users             136
timezone-resolved stays      5,821 / 5,821

semantic locations           2,015
recurring locations            716
recurring-location users       104

production HOME                 27
production OFFICE               16
unique emitted users            37
```

Location namespace:

```text
production_complete_link_200m_all_resolved_timezone_v2
```

Semantic gates:

```text
HOME
relevant_dates >= 3
share >= .50
margin >= .20

OFFICE
relevant_dates >= 3
share >= .30
margin >= .10
```

Interpretation boundary:

- reliability/agreement is not accuracy;
- external context is not HOME/OFFICE ground truth;
- experimental coverage is not production migration.

---

# Notebook 04 — Clustering robustness

Status: **HISTORICAL SCOPE, DECISION STILL ACTIVE**

Scope:

- historical 97-user semantic cohort;
- complete-link 200 m engineering reference;
- DBSCAN sweep: `eps=20/50/100/200m` × `min_samples=1/2/3/5`.

Complete-link 200 m:

```text
locations                    1,111
recurring locations            486
recurring-location users        73
p95 recurring diameter       180.95 m
max recurring diameter       199.23 m
clusters >200m                    0
```

DBSCAN at `eps=200m`:

| min_samples | recurring users | recurring locations | max diameter | clusters >200m |
|---:|---:|---:|---:|---:|
| 1 | 73 | 418 | 836.66 m | 68 |
| 2 | 73 | 418 | 836.66 m | 68 |
| 3 | 64 | — | 836.66 m | persists |
| 5 | 56 | — | 836.66 m | persists |

Additional measured fact:

```text
min_samples=1: 585 singleton locations
min_samples=2: same 585 singleton stays become noise
```

Decision:

> Increasing DBSCAN MinPts does not fix chaining. Keep complete-link 200 m for semantic locations because it enforces the intended hard diameter contract.

Repo references:

- `docs/worklog.md` — 2026-10-01 clustering robustness follow-up;
- `docs/learning-journal-vi.md` — “Tăng DBSCAN MinPts không sửa được chaining”.

---

# Initial historical POI/OSM follow-up

Status: **HISTORICAL NEGATIVE RESULT**

Scope:

- 27 frozen HOME anchors;
- 16 frozen OFFICE anchors;
- historical OSM context audit.

At 150 m:

```text
HOME unknown      22 / 27
OFFICE unknown    14 / 16
```

Decision:

> Historical OSM absence cannot be treated as semantic contradiction. The high unknown rate triggered the pivot from POI-as-validator to behavioral reliability without ground truth.

---

# Stage 05 — HOME/OFFICE reliability, CP2-v2

Status: **CURRENT**

Scope:

```text
stays                    5,821
semantic users             136
semantic locations       2,015
recurring locations        716
recurring users            104
production HOME             27
production OFFICE           16
```

Candidate coverage:

| method | HOME | OFFICE |
|---|---:|---:|
| fixed-window | 42 | 30 |
| HoWDe-style | 26 | 27 |
| recurrence | 104 | 38 |

Cross-method exact candidate agreement:

```text
HOME
fixed <-> HoWDe        19 / 23 = 82.6%
fixed <-> recurrence   35 / 42 = 83.3%
HoWDe <-> recurrence   20 / 26 = 76.9%

OFFICE
fixed <-> HoWDe        16 / 19 = 84.2%
fixed <-> recurrence    6 / 25 = 24.0%
HoWDe <-> recurrence    3 / 24 = 12.5%
```

Held-out top-1, fixed-window:

```text
HOME    50.0%
OFFICE  42.1%
```

30% stay-dropout retention:

```text
fixed HOME        81.7%
fixed OFFICE      78.9%
HoWDe HOME        69.2%
HoWDe OFFICE      56.8%
recurrence HOME   81.7%
recurrence OFFICE 65.8%
```

+12 h local-time stress retention:

```text
fixed HOME         31.0%
fixed OFFICE       13.3%
HoWDe HOME         19.2%
HoWDe OFFICE       11.1%
recurrence HOME   100.0%
recurrence OFFICE  68.4%
```

Decision:

> HOME remains substantially more convergent than OFFICE. Broader recurring-place coverage does not justify broader semantic emission. Keep production gates conservative.

Repo reference:

- `docs/eda/18_home_office_reliability_validation.md`.

---

# Stage 05b — HOME consensus + adaptive secondary anchors

Status: **CURRENT**

HOME vote winners:

```text
unique HOME winners   97
HIGH                  23
MEDIUM                 6
UNCERTAIN             68
```

HIGH/MEDIUM breakdown:

```text
HIGH:    21 production + 2 non-production
MEDIUM:   3 production + 3 non-production

HIGH/MEDIUM total             29
already production HOME       24
non-production review set      5
```

Adaptive secondary-anchor primary setting:

```text
window                42 days
step                  14 days
stability threshold       .70

stable_secondary_anchor       9
multi_anchor                  3
unstable                      1
insufficient                 16
```

Sensitivity:

```text
stable count by window at threshold .70
28d -> 6
42d -> 9
56d -> 10

42d threshold sensitivity
.60 -> 10 stable
.70 ->  9 stable
.80 ->  9 stable
```

Decision:

> Keep the five non-production HIGH/MEDIUM HOME candidates as targeted review cases only. Keep the nine-user stable-secondary cohort as a descriptive mobility state, not OFFICE.

Repo reference:

- `docs/eda/19_home_consensus_adaptive_work.md`.

---

# Stage 05c — Stable-secondary independent evidence

Status: **CURRENT**

Scope:

```text
stable-secondary users      9
fair same-user comparators  7
```

Candidate top-1 evidence:

| evidence axis | candidate top-1 |
|---|---:|
| weekday/weekend visit contrast | 5/7 |
| HOME-pair transition-day share | 3/7 |
| arrival-hour concentration | 0/7 |
| dwell regularity | 0/7 |

Combined:

```text
>=3 of 4 top-1 axes   0 users
exactly 2 axes        1 user
0-1 axes              6 users
```

Candidate identity agreement:

```text
recurrence      6 / 7
fixed OFFICE    3 / 7
HoWDe OFFICE    2 / 7
prod OFFICE     3 / 7
```

Decision:

> Secondary-anchor persistence is behaviorally real, but independent evidence does not support promotion to WORK/OFFICE semantics.

Repo reference:

- `docs/eda/20_stable_secondary_independent_evidence.md`.

---

# Stage 06 — Routine / habit mining

Status: **CURRENT AS PREPARATORY RESULT**

Measured scale:

```text
supported users         107
usable days             984
directed transitions  1,086
distinct user-edge rows 869
```

Repeated OD coverage:

```text
>=2 active days   23 users
>=3 active days    9 users
>=5 active days    2 users
```

Initial exact dominant-edge split-half stability:

```text
6 / 45 users
```

Important caveat discovered:

> The collapsed whole-day motif comparator can include stationary single-location days, so the initial OD-vs-motif comparison was not support/representation-equivalent.

Decision:

> Move to support-aware robustness and random-partition calibration before any change-detection claim.

---

# Stage 06b — Routine representation robustness

Status: **CURRENT**

Primary common-support universe:

```text
users with >=6 usable days                 51
users with comparable edge distributions  45
repeated directed OD >=3 active days        8
supported collapsed motif                   9
```

Chronological split-half:

```text
same top edge             13.3%
median JSD                 1.0
median weighted Jaccard    0.0
median total variation     1.0
median top-3 Jaccard       0.0
```

Support-matched random null:

```text
median random JSD                         1.0
chronological - random median JSD         0.0
chronological JSD > random p95        2 / 45 = 4.4%
```

Decision:

> Exact-OD instability is mostly sampling-driven. High chronological divergence is not sufficient evidence of temporal behavior change.

Repo reference:

- `docs/eda/22_routine_representation_robustness.md`.

---

# Stage 06c — Fixed-window change-detection feasibility

Status: **CURRENT NEGATIVE FEASIBILITY RESULT**

Calendar windows:

| window | adjacent pairs | users with adjacent pair | median usable days |
|---|---:|---:|---:|
| 28d | 16 | 11 | 8 |
| 42d | 15 | 9 | 8 |
| 56d | 11 | 7 | 9 |

Exact OD:

| window | median chronological JSD | median random JSD | chronological > random p95 |
|---|---:|---:|---:|
| 28d | .942 | .876 | 0.0% |
| 42d | 1.000 | .857 | 0.0% |
| 56d | 1.000 | .894 | 9.1% |

Best practically interpretable coarse feature:

```text
42d cleaned distance / usable day
Spearman                         .729
chronological > random p95       6.7%
bootstrap width / observed IQR   .814
```

Predeclared coverage gate:

```text
required adjacent pairs >=20
observed maximum = 16
```

Final:

```text
45 feature x window combinations
candidate_for_stage07 = False for all
```

Decision:

> Do not lower the readiness threshold post hoc. Test support-indexed windows next.

Repo reference:

- `docs/eda/23_change_detection_representation_feasibility.md`.

---

# Stage 06d — Support-indexed change-detection feasibility

Status: **CURRENT STOP RESULT**

Coverage:

| usable days | max span | adjacent pairs | users |
|---:|---:|---:|---:|
| 6 | 56d | 49 | 18 |
| 6 | 84d | 58 | 21 |
| 8 | 56d | 26 | 11 |
| 8 | 84d | 29 | 11 |
| 10 | 56d | 15 | 8 |
| 10 | 84d | 18 | 8 |

Nearest primary-feature pass:

```text
6d / 56d cleaned distance
Spearman                         .712
chronological > random p95      6.12%
bootstrap width / observed IQR  1.030
gate                            <=1.0
```

Second near-pass:

```text
6d / 84d cleaned distance
Spearman                         .697
chronological > random p95      10.34%
gate                            <=10%
```

Final across all configurations:

```text
candidate_features          = 0
candidate_primary_features  = 0
stage07_ready               = False
```

Decision:

> Support-indexing repairs the coverage bottleneck but does not create jointly stable, null-calibrated, low-uncertainty change signal. Stop broad population-level change detection.

Repo reference:

- `docs/eda/24_support_indexed_window_feasibility.md`.

---

# Stage 07b — Factorized work-profile representation

Status: **CURRENT**

Representation-level counts:

| representation signature | users |
|---|---:|
| abstain | 110 |
| anchor_set | 48 |
| anchor_set + route_region | 13 |
| single_anchor + anchor_set + route_region | 7 |
| single_anchor + anchor_set | 2 |
| anchor_set + route_region + schedule_agnostic | 2 |

Evidence-axis counts:

```text
multiple recurring            72
HOME context supported        29
mobile complexity             23
repeated route                23
stable secondary               9
independent secondary evidence 7
adaptive multi-anchor          3
schedule shifted               2
```

Important overlap:

```text
stable secondary AND multiple recurring = 9 / 9
stable secondary AND repeated route     = 7 / 9
multiple recurring AND repeated route   = 22
```

Decision:

> Site structure, route structure and schedule evidence are overlapping dimensions. Do not force them into a mutually-exclusive WORK class.

Repo reference:

- `docs/eda/26_factorized_work_profiles.md`.

---

# Stage 07c — Historical source alignment

Status: **CURRENT**

Current universe:

```text
recurring non-HOME anchors  298
users                        29
OSM-eligible anchors        296
pre-ohsome anchors            2
```

Anchor-year distribution:

```text
2007    2
2008   93
2009  164
2010    6
2011   23
2012   10
```

Key temporal concentration:

```text
2008-2009 anchors = 257 / 298 = 86.2%
```

Final source hierarchy:

```text
BCL POI 2008   -> primary historical functional context
Historical OSM -> positive-support-only cross-check
CLCD           -> physical land-cover context
```

Decision:

> Source priority follows anchor-year support, not convenience of a modern source.

Repo reference:

- `docs/eda/27_historical_source_alignment.md`.

---

# Stage 07d — Historical context enrichment

Status: **CURRENT**

CLCD:

```text
known point class       275 / 298 = 92.28%
impervious              256 / 298 = 85.91%
point = 3x3 mode        294 / 298 = 98.66%
point = 5x5 mode        290 / 298 = 97.32%
```

Historical OSM execution:

```text
eligible anchors  296
completed         296 / 296
request errors      0
parse errors        0
```

BBox/query-level OSM context:

```text
semantic context      89 / 296
work-compatible       61 / 296
residential           13 / 296
```

Decision:

> CLCD is physical built-up context only. OSM must be spatially rechecked using exact geometry distance before semantic interpretation.

Repo reference:

- `docs/eda/28_historical_context_enrichment.md`.

---

# Stage 07e — Exact semantic-distance alignment

Status: **CURRENT AFTER NAMESPACE CORRECTION**

Important correctness fix:

> Earlier results used incompatible location-id namespaces. 07c -> 07e were rerun using the production complete-link namespace. Older incompatible measurements are superseded.

Exact <=100 m OSM context:

```text
semantic context      86 / 296 = 29.05%
work-compatible       59 / 296 = 19.93%
```

Stable-secondary candidate work-compatible context:

```text
25m    2 / 9
50m    2 / 9
100m   2 / 9
```

Candidate-minus-same-user-peer:

| radius | mean difference | bootstrap 95% interval |
|---:|---:|---:|
| 25m | +.123 | [-.108, +.399] |
| 50m | +.088 | [-.147, +.349] |
| 100m | +.036 | [-.201, +.303] |

Category note:

```text
office/commercial among stable-secondary candidates <=100m = 0 / 9
positive candidate cases are education
```

Decision:

> Historical OSM does not show stable candidate-specific WORK/OFFICE advantage.

Repo reference:

- `docs/eda/29_semantic_distance_alignment.md`.

---

# Stage 07f — BCL POI 2008 source audit

Status: **CURRENT SOURCE ARTIFACT**

Source identity:

```text
Figshare article 28667492
DOI 10.6084/m9.figshare.28667492.v1
license CC BY 4.0
file "Points of interest of China in 2008.rar"
```

Actual inspected container:

```text
POI2008All.gdb
ArcGIS File Geodatabase

layer        POI2008CN
geometry     Point
features     6,039,158
CRS          EPSG:4326
fields       PNAME, X, Y
```

Decision:

> Documentation described an older Personal Geodatabase/MDB form, but runtime truth is the inspected FileGDB. Use inspected archive/container/schema/CRS as the data contract.

Repo reference:

- `docs/eda/30_bcl_poi_2008_acquisition.md`.

---

# Stage 07g — BCL POI 2008 alignment

Status: **CURRENT**

Scope:

```text
candidate anchors             298
BCL-temporally eligible      259
eligible users                23
deduplicated BCL POIs       4,884
anchor-POI pairs <=100m       966
```

Coverage:

```text
any BCL POI           140 / 259
any lexical signal     97 / 259
work-compatible        87 / 259
```

Lexical limitation:

```text
unknown/unclassified names  3,769 / 4,884 = 77.2%
```

Stable-secondary candidate context:

```text
25m    2 / 9
50m    3 / 9
100m   4 / 9
```

Candidate-minus-peer:

| radius | mean difference | bootstrap 95% interval |
|---:|---:|---:|
| 25m | +.199 | [-.041, +.537] |
| 50m | +.171 | [-.099, +.494] |
| 100m | +.021 | [-.360, +.395] |

Business-name candidate signal:

```text
25m = 0/9
50m = 0/9
100m = 0/9
```

Decision:

> BCL has broader historical functional context than OSM but does not produce a reliable stable-secondary candidate advantage.

Repo reference:

- `docs/eda/31_bcl_poi_2008_alignment.md`.

---

# Stage 07h — Evidence triangulation

Status: **CURRENT DIAGNOSTIC; OSM NEGATIVE-WEIGHT INTERPRETATION CORRECTED BY 07i**

Lineage:

```text
stable-secondary users       9
behavior-comparable users    7
OSM candidate identities     9
BCL candidate identities     9
candidate identity checks    PASS
```

At 100 m:

```text
OSM + BCL both positive        1 / 9
both negative                  3 / 9
opposite directions            3 / 9
same direction incl neutral    4 / 9

strict three-way convergence      0
directional three-way convergence 0
```

Decision:

> No multi-source convergence supports stable-secondary -> OFFICE promotion. Later evidence weighting must treat historical OSM absence as non-negative because early mapping is sparse.

Repo reference:

- `docs/eda/32_evidence_triangulation.md`.

---

# Stage 07i — Threshold / radius sensitivity

Status: **CURRENT**

Frozen OFFICE gate:

```text
dates >=3
share >=.30
margin >=.10
OFFICE = 16
```

One-step relaxations:

```text
margin .10 -> .05
OFFICE 16 -> 18
+2 margin-near

share .30 -> .20
OFFICE 16 -> 23
+7 share-near
```

BCL radius candidate context:

```text
25m   2/9
50m   3/9
75m   3/9
100m  4/9
125m  5/9
150m  6/9
```

Candidate-minus-peer mean advantage:

```text
25m   +.199
50m   +.171
75m   +.102
100m  +.021
125m  +.057
150m  +.039
```

All relevant bootstrap intervals cross zero.

Decision:

> The frozen OFFICE policy is conservative in coverage, but neither one-step gate relaxation nor a larger POI radius provides independent validation for a global production change.

Repo reference:

- `docs/eda/33_threshold_sensitivity.md`.

---

# Stage 07j — OFFICE near-miss robustness

Status: **CURRENT**

Cohort:

```text
margin-near   2
share-near    7
total         9
```

Margin-near:

```text
median support days   17.5
HoWDe match            2 / 2
recurrence match       0 / 2
both split tests       0 / 2
held-out top-1         0 / 2
```

Share-near:

```text
median support days    3
recurrence match       1 / 7
both split tests       1 / 7
held-out top-1         2 / 7
```

Across all nine:

```text
perfect dropout retention    5 / 9
BCL evaluable                2 / 9
BCL work-compatible <=150m   0 / 9
business-name support        0 / 9
```

Decision:

> Near-threshold candidates are not automatically robust. Do not globally relax OFFICE.

Repo reference:

- `docs/eda/34_near_miss_office_audit.md`.

---

# Stage 07k / 07l — Blinded historical imagery review + unblinding

Status: **CURRENT CONTEXTUAL RESULT**

07k freezes visual review before behavioral unblinding.

07l measured visual buckets:

```text
office-like                         1
institutional/daytime-compatible   3
OFFICE-contradictory               2
indeterminate                      3
```

Across nine near-misses:

```text
both split tests    1 / 9
held-out top-1      2 / 9
perfect dropout     5 / 9
BCL work <=150m     0 / 9
```

The one office-like visual case:

```text
HoWDe match        yes
recurrence         fail
both split tests   fail
held-out top-1     fail
dropout retention  .778
BCL work context   no
```

Decision:

> Historical imagery is contextual plausibility only. Visual office-likeness cannot override weak candidate persistence.

Repo references:

- `docs/eda/35_historical_imagery_review.md`;
- `docs/eda/36_imagery_unblinding_synthesis.md`.

---

# Stage 07m — Trackintel semantic-only comparator

Status: **CURRENT**

Same frozen stays / production locations; semantic selector only is changed.

Trackintel exact agreement:

```text
OSNA HOME      27 / 27
OSNA OFFICE    11 / 16

FREQ HOME      24 / 27
FREQ OFFICE     3 / 16
```

Trackintel internal method agreement:

```text
FREQ vs OSNA HOME   68 / 104 = 65.4%
FREQ vs OSNA WORK   31 / 93  = 33.3%
```

Near-miss OSNA exact candidate support:

```text
6 / 9
```

Decision:

> HOME has strong semantic-family convergence. OFFICE is substantially more method-sensitive. Trackintel agreement is not ground truth.

Repo reference:

- `docs/eda/37_trackintel_semantic_parity.md`.

---

# Stage 07n — Trackintel end-to-end comparator

Status: **CURRENT**

Raw input:

```text
users              182
trajectory files 18,670
raw positions   24,876,978
```

Stay inventories:

```text
frozen CP1        5,821 / 136 users
Trackintel        2,157 / 125 users
```

Strong stay matching:

```text
CP1 -> Trackintel       2,125 / 5,821 = 36.5%
Trackintel -> CP1       2,088 / 2,157 = 96.8%
```

Recurring production-location correspondence <=200 m:

```text
Trackintel DBSCAN-100   559 / 716 = 78.1%
Trackintel DBSCAN-200   530 / 716 = 74.0%
```

End-to-end DBSCAN-200 + OSNA:

```text
HOME    21 / 27 within 200m = 77.8%
OFFICE   9 / 16 within 200m = 56.3%
```

Decision:

> The largest observed end-to-end divergence begins upstream at stay inventory construction. Do not attribute all disagreement to semantic selection.

Repo reference:

- `docs/eda/38_trackintel_end_to_end.md`.

---

# Stage 07o — Literature comparator suite

Status: **CURRENT**

scikit-mobility-style HOME:

```text
26 / 27 exact = 96.3%
comparator selects HOME for 136 users
```

Geohash HOME adaptation:

```text
comparator-selected users  40
joint production users     21
within 200m               20 / 21
```

Pavan-style recurring-location medians:

| role | dwell h | visits | active dates |
|---|---:|---:|---:|
| HOME | 21.74 | 34.5 | 11 |
| OFFICE | 7.62 | 15 | 6 |
| OTHER_RECURRING | 1.38 | 2 | 2 |

SCITEPRESS-style exact agreement:

```text
HOME    25 / 27 = 92.6%
OFFICE  15 / 16 = 93.8%
```

Important failure mode:

```text
same location selected for HOME and WORK:
71 / 117 comparator users
```

Decision:

> Comparator match rate must be interpreted together with coverage and semantic failure modes.

Repo reference:

- `docs/eda/39_literature_comparator_suite.md`.

---

# Stage 07p — Methodological synthesis

Status: **CURRENT VALIDATION CLOSURE**

Lineage validation:

```text
33 / 33 hard checks PASS
```

HOME evidence ladder:

```text
fixed <-> HoWDe          19 / 23
fixed <-> recurrence     35 / 42
held-out top-1            .500
30% dropout               .81746
Trackintel OSNA          27 / 27
Trackintel E2E           21 / 27 within 200m
scikit-style             26 / 27
geohash                  20 / 27 within 200m
SCITEPRESS               25 / 27
```

OFFICE evidence ladder:

```text
fixed <-> HoWDe          16 / 19
fixed <-> recurrence      6 / 25
held-out top-1            .421
30% dropout               .78889
Trackintel OSNA          11 / 16
Trackintel E2E            9 / 16 within 200m
SCITEPRESS               15 / 16
```

Final policy snapshot:

```text
production_HOME   = 27
production_OFFICE = 16

change_home_gate   = False
change_office_gate = False
promote_near_miss  = False

final_policy = freeze_HOME_27_OFFICE_16
```

Decision:

> CP2-v2 methodological validation track is closed with explicit claim boundaries.

Repo reference:

- `docs/eda/40_methodological_synthesis.md`.

---

# Stage 08a — HOME coverage expansion tier

Status: **CURRENT RESEARCH/CONFIDENCE TIER**

Candidate lineage:

```text
production HOME              27
current non-production HIGH/MEDIUM candidates 5
```

External corroboration among five:

| signal | supported |
|---|---:|
| Trackintel OSNA exact | 4/5 |
| Trackintel FREQ exact | 4/5 |
| scikit-style HOME exact | 4/5 |
| SCITEPRESS HOME exact | 5/5 |
| geohash <=200m | 3/5 |
| Trackintel E2E <=200m | 4/5 |
| production OFFICE collision | 0/5 |

Tier result:

```text
HOME_HIGH_CONFIDENCE_CORE  27
HOME_PROBABLE_NEW           5
tiered usable HOME         32
```

Decision:

> Expose the five cases only as HOME_PROBABLE. Do not merge them silently into the production core.

Repo reference:

- `docs/eda/41_home_coverage_expansion.md`.

---

# Stage 08b — Exposure-bias audit

Status: **CURRENT**

Observation exposure across 136 users:

| metric | min | median | max |
|---|---:|---:|---:|
| total stays | 1 | 16 | 470 |
| active local dates | 1 | 8 | 138 |
| observation span days | 1 | 68 | 1885 |
| recurring locations | 0 | 3 | 34 |
| HOME opportunity dates | 0 | 2.5 | 34 |
| OFFICE opportunity dates | 0 | 2 | 52 |

HOME gate outcomes:

```text
min_dates_blocked          45
no_observed_opportunity    34
emitted                    27
no_recurring_candidate     15
share_and_margin_blocked    8
share_blocked               7
```

OFFICE gate outcomes:

```text
min_dates_blocked          50
no_observed_opportunity    39
no_recurring_candidate     17
emitted                    16
share_blocked               8
margin_blocked              3
share_and_margin_blocked    3
```

Emission rate:

| label | SPARSE | MEDIUM | DENSE |
|---|---:|---:|---:|
| HOME | 0.0% | 32.4% | 47.1% |
| OFFICE | 0.0% | 20.0% | 32.4% |

Exposure-limited cases:

```text
HOME min-date blocked     45
raw top covers 100% observed opportunities 13

OFFICE min-date blocked   50
raw top covers 100% observed opportunities 14
```

Continuous associations:

```text
HOME opportunity dates vs emission          +.484
HOME opportunity dates vs raw top share     -.356
HOME opportunity dates vs eligible share    -.535
HOME opportunity dates vs eligible margin   -.597

OFFICE opportunity dates vs emission        +.406
OFFICE opportunity dates vs raw top share   -.631
OFFICE opportunity dates vs eligible share  -.303
OFFICE opportunity dates vs eligible margin -.224
```

Concentration of known expansion cases:

```text
5 / 5 HOME_PROBABLE are DENSE
9 / 9 OFFICE near-misses are DENSE
```

Decision:

> Exposure failure is bimodal: SPARSE users can be absolute-support limited, while DENSE users can be concentration-diluted. Do not use one generic adaptive rule.

Repo reference:

- `docs/eda/42_exposure_bias_audit.md`.

---

# Stage 08c — Exposure-aware policy experiment

Status: **CURRENT EXPERIMENTAL TIER; PRODUCTION UNCHANGED**

Input reproduction:

```text
production HOME        27
production OFFICE      16
HOME_PROBABLE           5
OFFICE near-miss        9
diagnostic rows       272
```

## SPARSE HOME

Rule:

```text
exactly 2 observed HOME opportunities
same candidate on 2 / 2
raw date coverage = 1.0
original HOME share >= .50
original HOME margin >= .20
recurrence exact match
no production-OFFICE collision
```

Measured:

```text
new candidates = 4

raw shares:
1.000
.833
.872
1.000
```

Interpretation:

> This only relaxes absolute support count from 3 to 2 for a very narrow 2-of-2 cohort. It does not relax the original share/margin gates.

## DENSE HOME

Search universe: only the five already-corroborated HOME_PROBABLE cases.

Relative dominance:

```text
top / (top + runner-up) >= .625
```

Measured:

```text
5 / 5 pass

.721
.650
.763
.755
1.000
```

## DENSE OFFICE

Funnel:

```text
9 near-misses
-> 7 pass relative dominance >= .60
-> 3 pass final robustness rule
```

Within 7-user relative pool:

```text
static comparator >=1   4
split support >=1       1
held-out top-1          2
dropout retention >=.80 4
final robust            3
```

All three final OFFICE candidates:

```text
dropout retention = 1.0
+ at least one additional method selects the same candidate
```

Coverage:

| policy view | HOME | OFFICE | production changed |
|---|---:|---:|---|
| frozen baseline | 27 | 16 | no |
| tiered HOME | 36 | 16 | no |
| all experimental branches | 36 | 19 | no |

Decision:

```text
production HOME   = 27
production OFFICE = 16

experimental HOME   = 36
experimental OFFICE = 19
```

Next validation target:

```text
4 new sparse HOME
3 robust OFFICE
```

Repo reference:

- `docs/eda/43_exposure_aware_policy.md`.

---

# Superseded-result registry

The following classes of measurements must not be reused as current production evidence.

## Historical Beijing-v1 semantic scope

Examples:

```text
97 semantic users
1,111 locations
486 recurring locations
73 recurring-location users
```

These are valid historical measurements for chronology and Notebook 04, but CP2-v2 current scope is:

```text
136 semantic users
2,015 locations
716 recurring locations
104 recurring-location users
```

## Pre-correction 07c / 07d / 07e location namespace

Any measurement produced before the production-location namespace correction is superseded for semantic interpretation.

Current namespace:

```text
production_complete_link_200m_all_resolved_timezone_v2
```

## Historical OSM negative evidence

OSM absence from 2008-2009 must not be used as negative semantic evidence.

Current interpretation:

```text
BCL 2008       = primary functional context
Historical OSM = positive-support-only
CLCD           = physical context
```

---

# Quick current-result index

```text
Spatial representation
complete-link 200m hard diameter preserved
DBSCAN 200m max recurring diameter ~836.66m

Current CP2-v2
5,821 stays
2,015 semantic locations
716 recurring locations
104 recurring users
27 HOME / 16 OFFICE

Reliability
HOME fixed<->recurrence     35/42
OFFICE fixed<->recurrence    6/25
Trackintel OSNA HOME        27/27
Trackintel OSNA OFFICE      11/16

Change detection
06d stage07_ready = False

External context
BCL feature count       6,039,158
OSM work-compatible <=100m 59/296
stable-secondary OSM work context 2/9
stable-secondary BCL context <=100m 4/9
no stable BCL candidate-specific advantage

Validation closure
33/33 hard checks PASS
production frozen 27/16

Coverage research
HOME_PROBABLE        +5
SPARSE HOME          +4
robust OFFICE        +3
experimental total   36 HOME / 19 OFFICE
production unchanged 27 HOME / 16 OFFICE
```
