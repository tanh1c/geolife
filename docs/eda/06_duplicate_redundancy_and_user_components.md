# Duplicate redundancy and user connected-components

Date: 2026-09-16

These findings are measured from the official GeoLife 1.3 release mounted in Modal.

## Redundant point mass

Exact duplicate content was grouped by SHA-256. After retaining one representative trajectory per hash group, the remaining extra copies account for:

- 1,495,115 redundant GPS points;
- 6.01% of all 24,876,978 GPS points.

This is different from the 11.92% point exposure of all files participating in cross-user duplicate groups. The 11.92% number includes one legitimate representative copy per hash group, while 6.01% measures only the point mass beyond one representative.

Implication: exact duplication is large enough to bias point-weighted statistics and evaluation if all copies are treated as independent observations.

## User graph induced by shared content

Users were connected when at least one byte-identical trajectory hash appeared under both user IDs.

Observed:

- 52 users participate in cross-user duplication;
- 18 connected components are formed;
- the largest component contains 15 user IDs: `056, 078, 082, 101, 109, 110, 112, 115, 126, 128, 140, 153, 156, 163, 167`;
- several 3-user components appear, including `057/094/150`, `058/059/141`, and `081/125/136`;
- the remaining observed components are mostly pairs.

The release itself does not establish why these user IDs share exact trajectory content. No identity inference is made from this structure.

## Evaluation implication

A naive user-only split is not sufficient to guarantee content independence because multiple distinct user IDs can be linked by identical trajectories. Future benchmark splitting should therefore preserve content-hash grouping, and for strict user-level generalization it may also be useful to keep users connected by shared-content components in the same fold.

This does not yet imply that all duplicated files should be removed from the production inference pipeline. The immediate use of SHA-256 is leakage control, dataset diagnostics, and duplicate-aware weighting.

## Decision boundary for EDA

Duplicate analysis is now sufficiently characterized for CP1. The next step is to return to preprocessing relevant to stay-point detection: prototype spatially robust consolidation of compact same-second groups, flag conflicting same-second groups, and recompute movement speed and temporal-gap distributions before selecting noise thresholds.