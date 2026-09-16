# Measured EDA Phase 2 — trajectory quality diagnostics

Date: 2026-09-16

These findings come from the full 18,670-trajectory scan of the mounted official GeoLife 1.3 release.

## Dataset cardinality confirmed

- Total points: 24,876,978
- This exactly matches the v1.3 table in the supplied GeoLife user guide.

## Timestamp observations

Using the current exploratory parser, which constructs `timestamp` from the date/time text fields at one-second precision:

- null timestamps: 0
- non-monotonic trajectories: 0
- duplicate-timestamp rows: 698,900 (2.81% of points)
- trajectories affected by duplicate timestamps: 441

The duplicate pattern is not yet treated as a data defect. In the most affected trajectory, many seconds contain five rows with five different coordinates. This strongly suggests that the one-second text timestamp may be losing sub-second sampling information. The PLT serial-date field must be tested as a higher-precision timestamp source before any deduplication or speed threshold is chosen.

## Coordinate validity

Only one latitude value is outside [-90, 90]:

- user: `020`
- trajectory: `20110911000506`
- row: 6775
- value: latitude `400.166667`
- surrounding rows are near latitude `40.166...`

This is consistent with an isolated malformed coordinate and should be handled by explicit coordinate validation rather than by a generic speed threshold.

## Extreme movement diagnostics

The current summary contains physically impossible distances/speeds, so raw means and max-based threshold counts are contaminated by outliers.

The most extreme trajectory is user `062`, trajectory `20080926000623`. Its raw sequence contains repeated one-second jumps of roughly 850–862 km between two distant coordinate regions, producing speeds around 3.1 million km/h. The pattern is repeated, not a single isolated spike, so a simple single-point deletion rule would not fully describe this failure mode.

Implication: movement cleaning needs to distinguish at least:

1. isolated malformed coordinates;
2. repeated/interleaved impossible jumps;
3. legitimate high-speed travel such as train/airplane;
4. long sampling gaps that make inferred continuity unsafe.

No speed threshold has been selected yet.

## Exact duplicated raw trajectories across users

The file named `20070803084029.plt` appears under users `057`, `094`, and `150`. SHA-256 for all three files is identical:

`3f7638131e957853db976a1b2409286440ee820e201cd467163b06d8147d33ef`

This proves that at least one trajectory is duplicated byte-for-byte across different user folders. The prevalence of such duplicates still needs to be measured. This matters for distribution weighting and train/test leakage risk if future evaluation is split naively by trajectory.

## Next evidence step

Before rerunning speed/sampling statistics or choosing cleaning thresholds:

1. verify whether PLT `serial_date` preserves sub-second timing and whether it resolves the 698,900 apparent duplicate timestamps;
2. inspect the repeated impossible-jump trajectory as a contiguous sequence to characterize the corruption pattern;
3. measure the prevalence of byte-identical trajectories across users;
4. only then revise the exploratory parser and rerun trajectory-level summaries.
