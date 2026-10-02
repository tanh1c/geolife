# Stage 07c handoff — Historical Source Audit & Temporal Alignment\n\n## Outputs\n\nPrivate:\n- anchor_observation_dates_private.pkl\n- anchor_source_plan_private.pkl\n\nAggregate:\n- source_gate_summary.csv\n- source_plan_summary.csv\n- source_year_coverage.csv\n\n## Runner rule\n\nStage 07c does not fetch historical POI datasets.\n\nIt records which source is temporally appropriate and whether that source is currently allowed into Stage 07d.\n\n## Current gate state\n\nReady/near-ready:\n- ohsome historical OSM: cross-check only;\n- CLCD: exact-year physical context after local-file/license acknowledgement.\n\nBlocked pending additional verification:\n- BCL POI 2008: file access/license/CRS;\n- Gaode 2010 reusable corpus: access/license;\n- Gaode 2011: provenance/license/CRS;\n- BCL 2011 POI research corpus: reusable dataset metadata/access;\n- Baidu 2012: provenance/access/license/CRS;\n- planning permits / transactions / BCL blocks: license/CRS for automated local joins.\n\n## Stage 07d\n\n07d should be source-modular and must refuse to use any blocked source unless the gate metadata is explicitly updated with evidence.\n

## Measured handoff — 2026-10-02

Measured candidate universe:

- 25 users;
- 225 recurring non-HOME anchors.

Anchor median-year distribution:

- 2008: 72 anchors / 12 users;
- 2009: 136 anchors / 11 users;
- 2010: 1 anchor / 1 user;
- 2011: 10 anchors / 4 users;
- 2012: 6 anchors / 2 users.

208 / 225 anchors (92.4%) are in 2008–2009.

## Stage 07d priority

Primary MVP:

- CLCD exact-year join for every anchor;
- ohsome exact historical snapshot cross-check for every anchor.

Highest-value blocked semantic source:

- BCL POI 2008: 208 anchors / 19 users;
  - 72 exact-year anchors;
  - 136 2009 anchors using an explicit one-year proxy.

Lower-priority blocked semantic sources:

- Gaode 2010: 1 anchor / 1 user;
- 2011 candidates: 10 anchors / 4 users;
- Baidu 2012: 6 anchors / 2 users.

The measured distribution therefore justifies resolving BCL-2008 access/license/CRS before investing engineering effort in Gaode/Baidu ingestion.

