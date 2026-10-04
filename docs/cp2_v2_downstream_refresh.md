# CP2 v2 downstream refresh

Date: 2026-10-04

CP2 v2 is frozen on `main` after exact full-release parity against the audited Notebook-03 timezone-aware reference.

This refresh is intentionally limited to stages whose artifacts depend on the production Home/Office location namespace.

## Rerun order

```text
05
→ 05b
→ 05c
→ 07b
→ 07c
→ 07d
→ 07e
```

Do **not** rerun 06 / 06b / 06c / 06d for this migration. That lineage already uses the all-resolved per-stay timezone behavior representation.

Do **not** repeat the 07f BCL acquisition/licence/format/CRS audit. Its source provenance is independent of the CP2 location namespace.

## Artifact namespace

New private outputs are written below:

```text
/mnt/geolife-data/cache/cp2_v2/
```

Historical CP2-v1 artifacts remain untouched.

## Stage-specific notes

- 05/05b/05c consume production CP2-v2 semantic locations. Mixed timezone-aware timestamps are normalized to per-stay local wall-clock time inside downstream analysis helpers.
- 05c treats the old 9-user stable-secondary count as historical Beijing-v1 evidence, not an assertion.
- 07b reuses the existing 03a behavior features and Stage-06 routine artifacts, but consumes CP2-v2 05b/05c outputs.
- 07c freezes the new namespace as `production_complete_link_200m_all_resolved_timezone_v2`.
- 07d reads only the CP2-v2 07c anchor artifact and rebuilds coordinates from current production locations when needed.
- 07d reuses the existing content-addressed historical OSM raw cache at `cache/07d_historical_context_enrichment/ohsome_raw`; only unseen anchor request hashes require network fetches.
- 07e consumes CP2-v2 07d/05b/07b outputs while reading the same shared historical OSM raw cache.

## Completion gate

The refresh is complete only after all seven notebooks run successfully in order and their measured aggregate outputs are recorded in the worklog. No old Beijing-v1 count other than the already-proven 27 HOME / 16 OFFICE production parity is an acceptance target.
