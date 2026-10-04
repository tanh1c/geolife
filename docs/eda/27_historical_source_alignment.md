# Stage 07c — Historical External Context Source Audit & Alignment\n\n## Why this stage exists\n\nGeoLife observations were collected during 2007–2012. Current POI context cannot be used as historical semantic truth without temporal leakage.\n\nStage 07c therefore does not enrich POIs yet. It audits candidate historical sources and assigns each recurring anchor a temporally explicit evidence plan.\n\n## Source policy\n\n### BCL POI 2008\n\nVerified by Beijing City Lab as over six million POIs scraped in 2008, mainland-China coverage, snapshot 2008, coordinates + place names, no category field.\n\nPolicy:\n- 2008 anchors: exact-year historical semantic candidate;\n- 2007/2009 anchors: explicit ±1-year proxy only;\n- automatic runner remains blocked until the exact downloadable file's access/license/CRS are verified;\n- name-based semantics must use high-precision lexical rules only.\n\n### Gaode 2010\n\nPeer-reviewed evidence reports a self-built crawler obtaining 1,610,384 Gaode POIs for 2010, with name/category/coordinates; the paper describes raw 'Mars coordinates' followed by WGS84 conversion.\n\nPolicy:\n- strong exact-year 2010 candidate;\n- automatic runner blocked until a reusable corpus matching that provenance is obtained and its license is verified;\n- do not assume any third-party 2010 archive is the same corpus.\n\n### Gaode 2011\n\nJunxi Qu's catalog lists Gaode 2010–11, but the catalog does not establish collection provenance, license, or CRS for the exact files.\n\nPolicy: blocked.\n\n### BCL 2011 POI research corpus\n\nBCL research output reports 5,281,382 POIs for 2011.\n\nPolicy: useful provenance lead, but public reusable dataset access/license/CRS remain unverified, so blocked.\n\n### Baidu 2012\n\nThe existence of Baidu place search in 2012 does not prove that a reusable historical 2012 snapshot is available.\n\nPolicy: candidate only; blocked until provenance/access/license/CRS are verified.\n\n### CLCD annual land cover\n\nCLCD provides annual 30 m land-cover rasters including every GeoLife year 2007–2012.\n\nPolicy:\n- exact observation-year physical context;\n- never map built-up/impervious directly to office, residential, school, hospital, or occupation;\n- raster metadata/record license must be acknowledged before Stage 07d local use.\n\n### Beijing planning permits / land transactions\n\nVerified historical administrative datasets covering the GeoLife period.\n\nPolicy: corroboration only. Permit/transaction/planned use does not prove facility operation or actual occupancy at the visit date.\n\n### BCL blocks 2011\n\nVerified 2011 block/morphology dataset based on POIs + road network.\n\nPolicy: neighborhood/morphology prior only; no fine functional semantics are assumed.\n\n### ohsome historical OSM\n\nOfficial ohsome docs allow historical snapshots from 2007-10-08 onward.\n\nPolicy:\n- exact database-snapshot cross-check;\n- early mapping incompleteness/mapping lag means missing OSM is missing mapping evidence, not real-world absence;\n- OSM/ohsome does not replace primary historical semantic evidence.\n\n## Per-anchor temporal plan\n\nFor each recurring non-HOME anchor, Stage 07c computes first / median / last observation dates from the frozen 200 m clustered stays.\n\nThe median observation date determines the initial source plan.\n\nOutputs preserve:\n- source id;\n- evidence role;\n- source year or date range;\n- temporal offset;\n- exact vs proxy alignment;\n- use status / blocking issue.\n\n## No silent proxy promotion\n\nNearest-year evidence is stored as a proxy with temporal_offset_years.\n\nIt must never be silently converted into exact historical semantic ground truth.\n\n## Gate to Stage 07d\n\nStage 07d may only load a source when its source-specific gate is satisfied.\n\nBlocked semantic sources remain visible in the audit but are not queried or joined automatically.\n

## Measured result — 2026-10-02

Stage 07c executed successfully on the support-qualified recurring non-HOME subset.

Population:

- 25 users;
- 225 recurring non-HOME anchors.

Median anchor observation year:

| year | anchors | users |
|---|---:|---:|
| 2008 | 72 | 12 |
| 2009 | 136 | 11 |
| 2010 | 1 | 1 |
| 2011 | 10 | 4 |
| 2012 | 6 | 2 |

Therefore 208 / 225 anchors (92.4%) fall in 2008–2009.

### Source leverage

- CLCD exact-year physical context covers 225 / 225 anchors.
- ohsome historical OSM is temporally eligible for 225 / 225 anchors because this measured subset has no median anchor date before 2008.
- BCL POI 2008 is relevant to 208 / 225 anchors:
  - 72 exact-year 2008 anchors;
  - 136 explicit +/−1-year proxy anchors from 2009.
- Gaode 2010 is relevant to only 1 anchor / 1 user.
- 2011 source candidates are relevant to 10 anchors / 4 users.
- Baidu 2012 candidate is relevant to 6 anchors / 2 users.

### Decision

The measured date distribution changes source priority.

Do not prioritize Gaode 2010 as the first Stage-07d semantic source merely because it has stronger paper-level category metadata. It has negligible leverage on the measured anchor population.

Stage-07d priority should be:

1. CLCD exact-year physical context for all 225 anchors;
2. historical OSM via ohsome as an all-anchor cross-check;
3. resolve access / license / CRS for BCL POI 2008 because it has by far the highest semantic leverage (208 anchors / 19 users);
4. defer Gaode 2010 / 2011 and Baidu 2012 integrations until the primary 2008–2009 path is exhausted or until later-period anchors are specifically audited.

BCL POI 2008 must still distinguish exact 2008 evidence from 2009 proxy evidence. The 2009 proxy is not historical ground truth.



## CP2-v2 Stage 07c refresh — 2026-10-04

Stage 07c was rerun after the CP2-v2 HOME/context expansion and factorized-profile refresh.

The earlier 2026-10-02 measurements remain historical Beijing-v1 evidence. The current production namespace is:

`production_complete_link_200m_all_resolved_timezone_v2`.

### Namespace validation

The CP2-v2 production location universe validated cleanly:

- production semantic-location users: 136;
- production semantic locations: 2,015;
- supported HOME ids checked: 29;
- supported HOME ids missing: 0;
- Stage-05b dominant secondary ids checked: 15;
- dominant secondary ids missing: 0.

### Recurring non-HOME candidate universe

The support-qualified candidate universe expands materially:

| metric | corrected Beijing-v1 | CP2-v2 |
|---|---:|---:|
| users | 25 | 29 |
| recurring non-HOME anchors | 198 | 298 |

The expansion is therefore +4 users and +100 anchors.

### Median observation year

| year | anchors | users |
|---|---:|---:|
| 2007 | 2 | 2 |
| 2008 | 93 | 16 |
| 2009 | 164 | 15 |
| 2010 | 6 | 3 |
| 2011 | 23 | 6 |
| 2012 | 10 | 3 |

The historical corrected Beijing-v1 universe had no median-year 2007 or 2010 anchors and was concentrated in 2008–2009 (65 / 120 anchors respectively).

Under CP2-v2:

- 257 / 298 anchors (86.2%) are in 2008–2009;
- 259 / 298 anchors (86.9%) are temporally relevant to BCL POI 2008 if explicit ±1-year proxies are allowed:
  - 93 exact-year 2008 anchors;
  - 164 2009 one-year proxies;
  - 2 2007 one-year proxies.

### Source leverage

Current temporal coverage:

- CLCD exact-year physical context: 298 / 298 anchors, 29 users;
- historical OSM / ohsome: 296 / 298 anchors, 29 users;
- BCL POI 2008 exact/+1-year candidate: 259 / 298 anchors, 23 users;
- Gaode 2010 candidate: 6 anchors / 3 users;
- 2011 source candidates: 23 anchors / 6 users;
- Baidu 2012 candidate: 10 anchors / 3 users.

The two OSM-ineligible anchors have median observation dates before the ohsome history boundary of 2007-10-08. They remain valid members of the full 298-anchor historical-context universe and are still eligible for CLCD, but must not be treated as missing OSM-cache failures.

### Source-gate metadata correction

The executed notebook still displayed the historical pre-07f BCL-2008 gate as `blocked_pending_access_license_crs`.

That gate is superseded by the completed Stage-07f audit, which established:

- public Figshare article 28667492;
- DOI `10.6084/m9.figshare.28667492.v1`;
- CC BY 4.0;
- official `Points of interest of China in 2008.rar`;
- FileGDB container `POI2008All.gdb`;
- layer `POI2008CN`;
- EPSG:4326.

The Stage-07c source registry is therefore updated to `ready_for_normalization` for BCL-2008. This metadata correction does not change the 07c anchor universe and does not require another 07c measurement rerun.

## CP2-v2 Stage 07c decision

1. Accept the 29-user / 298-anchor CP2-v2 recurring non-HOME universe.
2. Preserve the production namespace `production_complete_link_200m_all_resolved_timezone_v2`.
3. Keep CLCD as all-anchor physical context only.
4. Query historical OSM only for the 296 temporally eligible anchors; do not classify the two pre-2007-10-08 anchors as failed/missing OSM observations.
5. BCL-2008 remains the highest-leverage historical semantic source, now with access/licence/CRS already cleared by Stage 07f.
6. Proceed to Stage 07d only after its OSM fetch path is eligibility-aware.
