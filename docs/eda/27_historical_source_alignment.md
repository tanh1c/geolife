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

