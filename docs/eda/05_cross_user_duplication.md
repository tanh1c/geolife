# Cross-user exact duplication findings

Date: 2026-09-16

These findings are measured from SHA-256 content hashes over all 18,670 raw GeoLife 1.3 trajectory files and the trajectory-level point counts produced in Modal.

## File-level prevalence

All 821 exact-duplicate hash groups span more than one user ID.

- cross-user duplicate groups: 821
- files participating in those groups: 1,677
- share of all trajectory files: 8.98%

This means the exact-duplicate phenomenon observed earlier is entirely cross-user in the mounted release, not merely repeated files within the same user folder.

## Point-weighted impact

The 1,677 cross-user duplicate files contain 2,965,977 GPS points.

- total dataset points: 24,876,978
- points inside cross-user duplicate files: 2,965,977
- point-weighted share: 11.92%

The point-weighted share (11.92%) is materially larger than the file-count share (8.98%), so duplicated trajectories are, on average, longer than the dataset-wide average trajectory. Consequently, naive point-weighted or trajectory-weighted evaluation can be affected more than file counts alone suggest.

## Interpretation and evaluation risk

The raw release does not establish why identical trajectory content appears under multiple user IDs, so no identity-level conclusion should be made from duplication alone.

For model development, however, content identity must be treated as an explicit grouping variable. A random split by trajectory path or user/trajectory filename can place byte-identical content in both train and test sets, creating leakage and overweighting repeated traces.

Recommended exploratory safeguards:

- keep `content_sha256` in trajectory metadata;
- prevent the same hash group from crossing evaluation folds;
- report duplicate-aware counts in addition to raw file counts;
- measure redundant point mass beyond one representative per hash group before deciding whether to deduplicate training data;
- inspect user-level connected components formed by shared hashes before designing Home/Office evaluation splits.

No production deduplication rule is selected yet because this is a user-centric inference task and duplicated content across user IDs may affect user-history semantics differently from simple repeated samples.
