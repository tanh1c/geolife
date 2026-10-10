# Stage 09 — Cross-file trajectory continuity audit

Date: 2026-10-10  
Status: **MEASURED COMPLETE — experimental ingestion comparator; production unchanged**

## Question

Does frozen CP1's per-`.plt` detection miss enough boundary-spanning stays to explain the low HOME/OFFICE emission coverage? Does safely stitching adjacent files from the same user improve stay-user or semantic-label coverage without changing any CP1/CP2 thresholds?

This is a **targeted, conservative file-boundary test**, not a universal user-level GPS-trajectory merge or accuracy evaluation.

## Evidence source and provenance

- Executed user-provided notebook: `09-cross-file-continuity-audit-1.ipynb` (19 cells; all 9 code cells have outputs; no traceback).
- Run printed Git short commit `5b76e25` on branch `experiment/09-cross-file-continuity-audit`.
- Existing private frozen baseline cache: `/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl`.
- Stage output cache: `/mnt/geolife-data/cache/cp2_v2/09_cross_file_continuity_audit/`.
- Existing **517/517 per-component caches were loaded** on the reported rerun; the notebook reproduced the comparison and semantic reports rather than rescanning every connected component.
- Validation shown: frozen parity PASS (5,821 CP1 stays / 136 stay users / HOME 27 / OFFICE 16); endpoint manifest PASS (18,670 files); synthetic cross-file stay self-check PASS.

The source notebook's reported tables, not an independent Modal rerun, are the measured basis of the figures below. The notebook does not contain user-level case records; they remain on the private Volume.

## Frozen A/B design

**A:** Existing per-`.plt` cleaning + anchor-based stay detection, followed by per-user accumulation of stay events.

**B:** Only eligible adjacent files from the same user are jointly cleaned and detected with exactly the same production implementations. All other files retain the original baseline stays. A candidate boundary requires:

- strictly positive time gap, at most 300 seconds;
- valid endpoints, implied speed at most 1,200 km/h;
- first/last endpoint separation at most 400 m, a *necessary* but not sufficient geometric condition for a cross-boundary stay with a 200 m anchor radius.

Frozen CP1 values: same-second consolidation radius **10 m**, max gap **300 s**, hard-speed guard **1,200 km/h**, anchor spatial threshold **200 m**, minimum dwell **1,200 s (20 min)**. CP2-v2 HomeOfficeConfig unchanged, including complete-link 200 m and IANA local time.

Resource safeguard: connected components with more than 500,000 GPS points would be skipped and reported; none were skipped in the measured run.

## Measured boundary inventory

Raw release inventory: **182 users, 18,670 trajectory files**. There are **18,488 adjacent within-user file boundaries** (18,670 minus 182).

| Status | Boundaries |
|---|---:|
| Time gap greater than 300 s | 17,475 |
| Stitch candidate passing safety filters | 647 |
| Endpoint separation too large for a shared 200 m anchor | 305 |
| Implied speed above 1,200 km/h | 61 |
| **Total** | **18,488** |

Only **647/18,488 (about 3.5%)** were stitch candidates. Candidate boundaries formed **517 connected components** (average 2.3 files/component, maximum 16); the largest component had **104,170 raw points**, below the 500,000-point cap. **517/517** components evaluated, **0** skipped.

This inventory is descriptive, not a proof that the remaining boundaries can never affect behavior under a different ingestion contract or different CP1 thresholds.

## Measured stay impact

| Metric | Frozen per-file A | Stitched experiment B | Delta |
|---|---:|---:|---:|
| Stay events | 5,821 | 5,831 | +10 |
| Users with at least one stay | 136 | 136 | 0 |
| Users gaining stay events | — | 3 | — |
| Users losing stay events | — | 0 | — |

- The **+10 net stays** are about **+0.17%** versus frozen CP1.
- Within successfully evaluated components, baseline had **256 stays**, jointly processed groups emitted **266** (net +10).
- **19 stitched stays spanned at least one file boundary**. This is **not** the count of newly recovered stays: a spanning stay can represent a modified/extended existing event.
- No user without baseline stay was newly recovered by conservative stitching.

## Measured semantic impact

| Metric | Frozen A | Stitched B | Delta |
|---|---:|---:|---:|
| Semantic stays | 5,821 | 5,831 | +10 |
| Semantic locations | 2,015 | 2,022 | +7 |
| Recurring locations | 716 | 716 | 0 |
| Users with recurring locations | 104 | 104 | 0 |
| HOME emitted | 27 | 27 | 0 |
| OFFICE emitted | 16 | 16 | 0 |

Spatial candidate correspondence (within **200 m**, **not exact ID/geometry**):

| Label | Both selected | Both within 200 m | Frozen-only | Experimental-only |
|---|---:|---:|---:|---:|
| HOME | 27 | 27 | 0 | 0 |
| OFFICE | 16 | 16 | 0 | 0 |

The 27/27 HOME and 16/16 OFFICE correspondences preserve *candidate-level spatial identity within tolerance*. They **do not prove coordinates are exactly equal** or semantic correctness.

## Interpretation: what this supports

1. **File-level isolation causes some lost/altered stay segmentation**: boundary-spanning stays exist and a conservative joint rerun changes the total stay inventory (+10).
2. **It does not explain low current user coverage at material scale under frozen CP1**: there are **zero new stay users**, **zero new recurring-location users**, and unchanged 27 HOME / 16 OFFICE counts.
3. **Production HOME/OFFICE labels are robust to this narrow upstream perturbation**: all jointly selected frozen labels have a candidate within 200 m after stitching.
4. **No evidence for blanket threshold relaxation follows from Stage 09**: CP1 threshold sensitivity, observation exposure and direct semantic validity require separate studies.

## Limits and confounders

- This is an **endpoint-gated** audit, not full chronological union of all files per user. It does not stitch overlaps, zero-time endpoints, invalid coordinate cases, gap>300 s, speed-guard failures, or endpoints separated by >400 m.
- If a true cross-file stay is missed due to the restrictive join criteria, this experiment cannot quantify that missed effect.
- The same CP1 cleaning and stay detector are rerun on selected components. Some net stay differences may come from duplicate-timestamp handling or episode boundaries as well as genuine continuity; a private per-component audit would be needed for causal attribution.
- The 19 boundary-spanning events are not equivalent to 19 true positive stays; no staypoint or HOME/OFFICE ground truth is provided.
- Matching is within 200 m, not exact point equality; support scores and detailed evidence margins have not been compared.
- The measured run reused 517 previously produced private per-component caches. Cache lineage is associated with the notebook's fixed settings, and the reported results are those of this run; independent raw recomputation was not performed in this review.

## Decision and next experiment

**Decision:** Keep frozen per-file CP1 and HOME 27 / OFFICE 16 unchanged. Do not migrate stitching into production on these aggregate results alone. A broader file-union implementation has no measured coverage justification from this narrow study.

**Next:** Predeclare a **CP1 stay-detection threshold/observation-support sensitivity** experiment with the frozen source-file handling as control. Test the contribution of gap, dwell and spatial radius separately, report stay/user coverage, recurring-location stability, and HOME/OFFICE label persistence (not accuracy). If a new ingestion strategy is revisited, first perform a private matched-event audit of the three users gaining stays and the 19 spanning events.

## Files

- Notebook: `notebooks/09_cross_file_continuity_audit.ipynb`.
- Modal runbook: `docs/09_cross_file_continuity_audit_handoff.md`.
- Canonical measurement index: `docs/eda/notebook_measured_results_log.md`.
- Private output root: `/mnt/geolife-data/cache/cp2_v2/09_cross_file_continuity_audit/`; do not commit private candidate coordinates, user IDs or traces.
