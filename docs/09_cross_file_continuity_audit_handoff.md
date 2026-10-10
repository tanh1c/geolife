# Stage 09 — Cross-file continuity audit (Modal)

## Run

Open **notebooks/09_cross_file_continuity_audit.ipynb** in a Modal Notebook with Volume **geolife-data** mounted at `/mnt/geolife-data`.

The notebook clones/pulls branch `experiment/09-cross-file-continuity-audit` automatically (override with `GEOLIFE_REPO_BRANCH`). It requires the extracted release at `/mnt/geolife-data/extracted/Geolife Trajectories 1.3/Data` (or `GEOLIFE_RAW_ROOT`) and a pre-existing frozen `stays_baseline_v1.pkl` on the same Volume.

No downstream notebooks need to be rerun. Cells run top-to-bottom.

**Performance patch (2026-10-10, commit 7778ad5):** Endpoint inventory reads only a file's first GPS row and its last 8 KiB; it no longer loops through all ~24.9 million raw rows. Exact point counts are deferred until the eligible connected components in Section 4. If an older notebook is still running the old inventory cell, interrupt it, reopen the latest notebook from this branch, and rerun; compatible endpoint checkpoints are resumed from the same Volume path. Do not delete prior private cache files. The synthetic split-stay test was also repaired to use <=5-minute intra-file intervals.

## Question and A/B

A: frozen per-file CP1 processing (5,821 stays, 136 users).

B: rerun the same cleaning/detector across neighboring `.plt` files only when the boundary has valid endpoint observations, positive temporal gap <=300 s, implied speed <=1200 km/h, and endpoint distance <=400 m. No CP1 parameters are changed. The 400 m rule is a necessary geometric condition for a common 200 m anchor stay, not a sufficient stay condition.

File overlaps, zero-time boundaries, invalid endpoints, overly long gaps and very distant endpoints are intentionally not joined. `MAX_GROUP_RAW_POINTS = 500_000` is a resource cap; oversized components retain baseline outcomes in the experimental view and are counted as **skipped/unmeasured**.

## Volume artifacts

All outputs are written under:

```
/mnt/geolife-data/cache/cp2_v2/09_cross_file_continuity_audit/
```

Shareable aggregate outputs:
- `boundary_status_summary.csv`
- `stay_impact_summary.csv`
- `semantic_impact_summary.csv`
- `semantic_correspondence_summary.csv`

Private only: raw-file endpoint manifest, per-boundary audit, component plan, per-component caches, stitched stay candidates, user-level delta and component comparisons. These contain location or user-specific information and must not be committed.

## Checks and limitations

- Reproduce frozen CP1=5,821 / stay users=136 and production HOME=27 / OFFICE=16 before proceeding.
- Run synthetic split-stay test proving separate 12-minute files can yield a 25-minute stay when joined.
- Assert release inventory=182 users, 18,670 files and source-file cache lineage.
- Report evaluated and skipped components. The experiment is **not** a universal GPS-trajectory merging algorithm.
- Assess overlap, candidate identity and coverage; do not call more stays "more accurate" without ground truth.
- This is **not** a policy migration. Preserve all source code and frozen production caches.

## After running

Send the 4 aggregate CSVs or the notebook output for interpretation. If stitched spans produce material additional stays, the next stage can audit individual changes privately and predeclare an ingestion contract before threshold relaxation.

## Debug note after first executed Modal notebook (2026-10-10)

The original Stage-09 notebook had two presentation/test-only bugs, both fixed on this branch:

1. The synthetic self-check used intra-file 6-minute gaps even though CP1 splits at 5 minutes. The check now uses 4-minute intervals and can validate a 25-minute boundary-spanning stay.
2. The semantic spatial comparison unnecessarily merged coordinates from the location table a second time. Since `infer_home_office()` already returns `latitude` and `longitude`, pandas added `latitude_x/latitude_y` and `longitude_x/longitude_y` suffixes; attempting `a.latitude` raised `AttributeError`. The fixed code uses production inference output coordinates directly.

The first uploaded executed run finished endpoint inventory (18,670 files), found 647 stitch-eligible boundaries grouped into 517 components (0 skipped), and reran all 517 groups. Stage-09 summary printed 5,821 -> 5,831 stays (+10) but unchanged stay users (136), recurring users (104), HOME (27), OFFICE (16). These results are **preliminary until spatial correspondence cell finishes**. The errors did not cause those counts to be recomputed or invalidate the cached per-component runs.

To resume an existing live Modal kernel with the original notebook, replace only the two buggy lines in `summarize_semantics` with `labeled=outputs.copy()` and execute that last code cell. The already cached 517 groups do not need to be recomputed. If starting a new kernel with the latest notebook, all prior stages reuse the existing Volume manifest and group caches. Avoid deleting any Stage-09 caches.
