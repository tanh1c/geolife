# Full-release same-second consolidation findings

Date: 2026-09-16

The exploratory 10 m same-second consolidation transform was applied across all 18,670 trajectories.

## Consolidation impact

Observed from 24,876,978 raw GPS points:

- consolidated rows: 24,178,077;
- rows reduced: 698,901 (2.81%);
- spatial-conflict timestamps: 835 (0.0035% of consolidated rows);
- invalid coordinate points: 1.

This confirms that nearly all duplicate-second redundancy can be represented as one timestamp-level observation, while only a very small fraction of timestamps are spatially inconsistent under the 10 m experimental radius.

## Sampling and temporal gaps

After consolidation, trajectory-level sampling summaries remain strongly heterogeneous:

- median of per-trajectory median gap: 2 s;
- p75: 5 s;
- p95: 15 s;
- p99: 53.5 s;
- trajectory max-gap median: 325 s;
- p90 max-gap: 11,010.4 s;
- p99 max-gap: 20,689.86 s;
- maximum observed gap: 93,298 s.

Implication: stay duration cannot be inferred safely across arbitrary observation gaps. A continuity/split policy is required before stay-point detection.

## Speed distribution after consolidation

Across 24,157,908 valid inter-timestamp movement segments:

- >50 km/h: 5,259,160 segments (21.7699%);
- >100 km/h: 1,305,237 (5.4029%);
- >150 km/h: 241,167 (0.9983%);
- >200 km/h: 88,450 (0.3661%);
- >300 km/h: 53,379 (0.2210%);
- >500 km/h: 49,035 (0.2030%);
- >1,000 km/h: 1,691 (0.0070%).

Trajectory-level exceedance remains much larger because one extreme segment marks the whole trajectory; for example, 46.96% of trajectories have max speed >100 km/h while only 5.40% of valid segments exceed 100 km/h.

This confirms that segment-level prevalence is the more informative statistic for movement-noise analysis.

## Comparison with raw summaries

Same-second consolidation materially fixes zero-time ambiguity, but it changes the high-speed trajectory tail only slightly. The previously observed structurally corrupted trajectories remain extreme after consolidation.

Examples include:

- user 062 / `20080926000623`: max speed ~3.10 million km/h and distance ~510,032 km after same-second conflicts are masked;
- user 144 / `20090324004422`: max speed ~1.17 million km/h;
- several other trajectories retain multi-thousand-km/h segments despite having no same-second conflicts.

Therefore same-second ambiguity is not the dominant source of the residual speed tail.

## Cleaning implications

The evidence supports the following staged preprocessing design candidates:

1. validate coordinate domain;
2. collapse spatially compact same-second groups to a robust representative point;
3. retain/flag spatial-conflict timestamps without bridging across them;
4. split or otherwise guard against large temporal gaps before stay-duration calculations;
5. analyze legitimate versus corrupted high-speed movement using segment-level evidence and, where available, transportation-mode labels;
6. only then choose a movement-speed cleaning rule.

No production speed threshold is selected yet. Speeds in the 500–1,000 km/h range may include legitimate airplane travel, so a single global cutoff should not be chosen solely from the raw tail.