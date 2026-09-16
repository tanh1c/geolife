# Timestamp precision and duplicate-second diagnostics

Date: 2026-09-16

## Serial-date validation

The PLT `serial_date` field was tested against the text `date + time` timestamp for a trajectory with many apparent duplicate timestamps.

Observed for timestamp `2011-10-22 03:18:34+00:00`:

- five rows have five distinct coordinates;
- all five rows have the same `serial_date` value (`40838.137894`);
- conversion from serial date gives the same timestamp for all five rows (`2011-10-22 03:18:33.999998270+00:00`);
- `serial_delta_s` within the group is therefore 0.0;
- text-timestamp duplicate count: 45,215;
- serial-timestamp duplicate count: 45,215.

Across the inspected trajectory, serial-date timestamps differ from the text timestamps only by floating-point conversion noise on the order of microseconds (roughly within +/- 5 microseconds). This is not evidence of hidden sub-second sampling.

## Interpretation

The previous hypothesis that `serial_date` might recover sub-second timing is rejected by the measured evidence. The duplicate-second observations are present at the source timestamp precision, not created by the parser.

This means that when multiple coordinates share the same recorded second, their within-second ordering and velocity are not identifiable from this release. Segment speed must not be computed across `dt = 0` pairs.

A safe downstream policy should be based on measured spatial spread of same-second groups before deciding whether to collapse them (for example by median coordinate) or preserve them as simultaneous observations.

## Related measured quality findings

- Full release: 24,876,978 points.
- Apparent duplicate-timestamp rows: 698,900 (2.81%) across 441 trajectories.
- One malformed latitude was identified: `400.166667` between surrounding `40.166...` points.
- A separate trajectory shows repeated impossible ~850-862 km jumps in one-second intervals, indicating a different corruption pattern from the isolated invalid coordinate.
- At least one trajectory is byte-identical across users `057`, `094`, and `150` (same SHA-256), so exact cross-user duplicate prevalence should be measured before evaluation splits.

## Next diagnostics

Before choosing cleaning thresholds:

1. quantify same-second group size and spatial spread across all affected trajectories;
2. quantify exact duplicate trajectories across all 18,670 files;
3. inspect impossible-jump patterns to distinguish isolated spikes from interleaved/mixed traces;
4. define a preprocessing policy that handles coordinate validity, zero-time groups, temporal gaps, and impossible movement as separate failure modes.
