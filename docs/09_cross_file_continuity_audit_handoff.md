# Stage 09 — Cross-file continuity audit (Modal)

## Run

Open **notebooks/09_cross_file_continuity_audit.ipynb** in a Modal Notebook with Volume **geolife-data** mounted at `/mnt/geolife-data`.

The notebook clones/pulls branch `experiment/09-cross-file-continuity-audit` automatically (override with `GEOLIFE_REPO_BRANCH`). It requires the extracted release at `/mnt/geolife-data/extracted/Geolife Trajectories 1.3/Data` (or `GEOLIFE_RAW_ROOT`) and a pre-existing frozen `stays_baseline_v1.pkl` on the same Volume.

No downstream notebooks need to be rerun. Cells run top-to-bottom.

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
