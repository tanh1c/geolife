# Stage 07l handoff — Imagery unblinding synthesis

## Before running

You need the completed file:

`near_miss_9_blinded_review_manifest_filled.csv`

Upload/copy it into the notebook runtime.

The notebook automatically checks, in order:

1. path from environment variable `GEOLIFE_07K_REVIEW_CSV`;
2. `/mnt/data/near_miss_9_blinded_review_manifest_filled.csv`;
3. Stage-07k cache;
4. recursive search under `/mnt/geolife-data`.

## Run

Run only:

`notebooks/07l_imagery_unblinding_synthesis.ipynb`

No upstream notebook needs to be rerun.

Expected gate:

`unblinding validation: PASS (9/9 near-miss candidates matched exactly)`

## Main tables

### VISUAL CONTEXT BY NEAR-MISS FAMILY

Reveals which blinded imagery IDs belong to:

- margin-near;
- share-near.

### BEHAVIOR × VISUAL BUCKET

For each family/context bucket, reports:

- HoWDe matches;
- recurrence matches;
- both split tests;
- held-out top-1;
- median dropout retention;
- BCL coverage.

### CROSS-SOURCE SIGNATURES

Transparent combinations of:

- imagery bucket;
- behavioral persistence flags;
- BCL flags.

No total score.

### POLICY SNAPSHOT

Aggregate counts only.

## Important

The private case matrix contains user IDs after unblinding.

Do not publish:

`imagery_behavior_bcl_case_matrix_private.pkl`

After running 07l, send the executed notebook. The result will determine whether:

- one near-miss family deserves a separate policy review;
- a small manually-supported candidate subset should remain research-only;
- or the global OFFICE gate should remain fully frozen.
