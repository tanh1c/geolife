# Temporal-gap sensitivity and transportation-label inventory

Date: 2026-09-16

These findings are measured from the official GeoLife 1.3 release mounted in Modal, after the exploratory 10 m same-second consolidation stage.

## Temporal-gap sensitivity

Using each trajectory's maximum positive inter-observation gap after consolidation:

- max gap > 30 s: 15,281 trajectories (81.85%);
- max gap > 60 s: 14,158 (75.83%);
- max gap > 120 s: 12,308 (65.92%);
- max gap > 300 s: 9,513 (50.95%);
- max gap > 600 s: 7,793 (41.74%);
- max gap > 1,800 s: 5,537 (29.66%);
- max gap > 3,600 s: 4,274 (22.89%);
- max gap > 7,200 s: 2,962 (15.87%);
- max gap > 14,400 s: 1,172 (6.28%).

Interpretation: temporal discontinuity is common. A continuity threshold of only 30-60 seconds would split most trajectories at least once, while a 5-10 minute threshold still affects roughly half to two-fifths of trajectories. Therefore the continuity rule for stay-point detection must be treated as a sensitivity parameter rather than copied blindly from a tutorial.

The current table is trajectory-level sensitivity: it answers whether a trajectory has at least one gap above the threshold. A later segment-level gap distribution may be useful, but this is already sufficient to establish that observation outages are a first-class preprocessing concern.

## Transportation-label inventory

The mounted release contains 69 user folders with `labels.txt`. Parsing those files yielded 14,718 labeled time intervals.

Observed interval counts by mode:

- walk: 6,460;
- bus: 2,853;
- bike: 2,089;
- taxi: 1,179;
- car: 993;
- subway: 813;
- train: 299;
- airplane: 17;
- boat: 7;
- run: 6;
- motorcycle: 2.

The labels parse to UTC-aware start/end timestamps and can be used as auxiliary evidence for plausible movement speed. They are not Home/Office ground truth and their interval count should not be confused with trajectory coverage.

## Next diagnostic

Join post-consolidation valid movement segments to transportation-mode intervals using segment midpoint timestamps for the same user. Then compare per-mode segment speed distributions (median, p95, p99, max) and labeled coverage. This is the final speed diagnostic before freezing the exploratory cleaning contract and moving to stay-point implementation.