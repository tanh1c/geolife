# Same-second consolidation prototype

Date: 2026-09-16

This note records an exploratory preprocessing experiment. It is not yet production code or a final threshold decision.

## Prototype rule

For each trajectory:

1. validate latitude/longitude domain;
2. group raw GPS rows by exact timestamp;
3. compute the coordinate-wise median and each raw point's distance to that median;
4. if a same-second group has max radius <= 10 m, replace it with one representative median coordinate and preserve `raw_point_count`;
5. if max radius > 10 m, keep the timestamp but mark it as `spatial_conflict` and set representative coordinates to missing so movement calculations cannot bridge through it.

The 10 m value is an experimental candidate motivated by prior EDA: 99.61% of same-second groups are within 10 m. It is not yet a production cleaning threshold.

## Duplicate-heavy trajectory test

Test trajectory: user `141`, trajectory `20111022031803`.

Observed:

- raw points: 56,780;
- consolidated rows: 11,565;
- compact rows: 11,562;
- spatial-conflict rows: 3;
- invalid-coordinate points: 0.

Most 5-point same-second bursts collapse into one representative point with sub-metre to low-metre spatial spread. Example compact groups around `2011-10-22 03:18:34` have max radius well below 1 m.

After consolidation, the largest inspected segment speeds were approximately 225, 220 and 209 km/h. This is a large reduction from the multi-million-km/h corruption seen elsewhere and shows that same-second consolidation can remove one source of timing/order ambiguity without any global speed threshold.

However, speeds above 200 km/h still occur and cannot automatically be labeled as noise because GeoLife includes high-speed transport modes. Further dataset-wide comparison is required.

## Structurally corrupted trajectory test

Test trajectory: user `062`, trajectory `20080926000623`.

Observed:

- raw points: 8,117;
- consolidated rows: 8,091;
- compact rows: 8,065;
- spatial-conflict rows: 26;
- invalid-coordinate points: 0.

The consolidation correctly flags same-second pairs whose two locations are hundreds of kilometres apart, with max radii around 390–430 km.

Crucially, the trajectory still contains many ~850–862 km one-second jumps between singleton timestamps, producing speeds around 3.1 million km/h. Therefore same-second consolidation solves only the simultaneous-observation ambiguity; it does not solve the separate interleaved/mixed-trace corruption pattern.

## Interpretation

The experiment separates two failure modes:

- compact same-second bursts: mostly timestamp-resolution/jitter ambiguity and suitable for robust consolidation;
- impossible movement between distinct timestamps: a separate movement-integrity problem requiring additional anomaly logic.

This supports a staged preprocessing pipeline rather than a single `speed > X => drop point` rule.

## Next experiment

Run the consolidation transform across all 18,670 trajectories and recompute:

- total rows retained after consolidation;
- number/share of spatial-conflict timestamps;
- sampling-gap distribution;
- max and p99 segment-speed distributions;
- counts of trajectories exceeding several speed sensitivity levels.

Compare those results with the raw summaries before deciding whether a movement-speed threshold is necessary and, if so, how it should interact with high-speed transport and temporal gaps.