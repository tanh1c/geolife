# Label-interval semantics audit correction

Date: 2026-09-16

## Why this correction exists

An independent re-audit of the original GeoLife 1.3 ZIP reproduced the repository's core dataset and quality findings, including user/trajectory/point counts, duplicate timestamps, the malformed latitude, cross-user SHA-256 duplication structure, and the two representative trajectory case studies.

The audit identified one reporting issue in the transportation-label canonicalization step: the previous analysis treated label end times as inclusive by internally converting each interval to `[start, end + 1 second)`. That convention makes two different-mode labels that only meet at the same endpoint appear ambiguous for one second.

For interval algebra and segment-label matching, this project will use the standard half-open convention `[start, end)` unless a source contract explicitly requires otherwise. Under this convention, endpoint touching is not temporal overlap.

## Corrected overlap accounting

Re-auditing the raw ZIP under `[start, end)` produced:

- 14,583 unambiguous canonical windows;
- 138 ambiguous windows;
- 12,720.83 hours of unambiguous labeled time;
- 76.345 hours of ambiguous labeled time;
- ambiguous share of represented labeled time: approximately 0.597%.

The external audit also reported:

- 1,742 different-mode pairs that only touch at an endpoint and therefore should not be counted as overlapping under `[start, end)`;
- 146 different-mode pairs with true temporal overlap.

These pair counts are not directly interchangeable with the prior `1,903 overlapping/touching intervals` integrity statistic because that earlier metric was based on adjacency to the immediately previous interval and mixed touching with overlap. The corrected report should therefore distinguish `touching`, `true overlap`, and `canonical ambiguous windows` rather than present them as one quantity.

## What changes and what does not

The previous wording that overlap was "common when counted as windows" was misleading because most of the inflated ambiguous-window count came from endpoint-touch handling, not from true simultaneous labels.

The main methodological conclusion remains: ambiguous transportation-label time is small by duration, at about 0.6%, and overlapping labels should be excluded from speed benchmarking rather than assigned arbitrarily.

The broader CP1 findings remain unaffected by this correction:

- same-second GPS ambiguity is separate from inter-timestamp corruption;
- movement-noise reasoning should use segment-level evidence rather than trajectory maxima;
- generic 100/200/500 km/h global filters are not justified;
- exact-content hashes are required for evaluation leakage control;
- temporal continuity must be explicit for stay-point detection.

## Status of the V2 speed table

The existing V2 per-mode speed table was computed from the earlier inclusive-end canonicalization. Its broad shape was stable against the provisional benchmark, and the audit did not identify evidence that changes the design conclusion about ordinary global speed cutoffs.

However, exact V2 matched-segment counts and per-mode percentiles should be recomputed once using `[start, end)` before those exact values are treated as the final audited benchmark. Until that bounded rerun is completed, the existing V2 table is retained as historical evidence but is marked as based on the earlier inclusive-end convention.

## Reporting rule going forward

Mentor-facing reports should use the corrected half-open overlap counts above, clearly state the interval convention, and avoid describing endpoint touching as true overlap. The remaining rerun is a bounded audit correction, not a reopening of broad EDA.
