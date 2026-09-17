# Label-interval semantics audit correction

Date: 2026-09-17
Status: CLOSED.

## Why this correction exists

An independent re-audit of the original GeoLife 1.3 ZIP reproduced the repository's core dataset and quality findings but identified one reporting issue in transportation-label canonicalization. The earlier analysis treated label ends as inclusive by internally converting intervals to `[start, end + 1 second)`, which turned different-mode endpoint touches into one-second ambiguities.

The project now uses standard half-open `[start, end)` semantics. Under this convention, endpoint touching is not temporal overlap.

## Corrected overlap accounting

The final rerun reproduced the independent audit:

- 1,742 different-mode pairs touch only at an endpoint;
- 146 different-mode pairs have true positive-duration overlap;
- 14,583 unambiguous canonical windows;
- 149 atomic ambiguous sweep slices;
- 138 report-level ambiguous windows after merging adjacent slices only when the distinct active-mode set is unchanged;
- 12,720.833 hours of unambiguous labeled time;
- 76.345 hours of ambiguous labeled time;
- ambiguous share: 0.597%.

The distinction between the 149 atomic slices and 138 report-level windows is intentional. Sweep-line event boundaries may split one stable ambiguity combination into several adjacent atomic slices. Reporting merges only adjacent slices with the same active mode set; it does not merge different ambiguity combinations merely because they are temporally contiguous.

The earlier 14,537 unambiguous / 1,886 ambiguous counts are superseded for reporting.

## Final V3 speed rerun

Using corrected half-open canonical windows, the strict-containment segment-label join matched 4,807,087 of 11,878,198 valid post-consolidation segments from labeled users, for 40.47% coverage.

The corrected speed distribution is effectively unchanged in shape from the earlier benchmark:

- airplane: median 625.91 km/h, p99 937.99, max 1,048.11; 52.92% of segments exceed 500 km/h;
- train: median 93.14, p99 210.34;
- car: median 30.05, p99 119.63;
- bus: median 16.91, p99 90.59;
- bike: median 11.19, p99 40.63;
- walk: median 4.08, p99 40.39.

Coverage moves from 40.52% in the earlier inclusive-end V2 run to 40.47% in V3, about 0.05 percentage point.

## What changes and what does not

The previous wording that overlap was 'common when counted as windows' was misleading because most inflation came from endpoint-touch handling. True ambiguous time is small, at about 0.6% of represented labeled time.

The main CP1 conclusions remain unchanged and are now supported by the corrected V3 rerun:

- same-second GPS ambiguity is separate from inter-timestamp corruption;
- movement-noise reasoning should use segment-level evidence rather than trajectory maxima;
- generic 100/200/500 km/h global filters are not justified;
- exact-content hashes are required for evaluation leakage control;
- temporal continuity must be explicit for stay-point detection;
- the proposed 1,200 km/h release-specific hard guard remains a conservative continuity boundary rather than endpoint deletion.

## Reporting rule going forward

Mentor-facing reports use half-open `[start, end)` semantics, distinguish endpoint touching from true overlap, and use the V3 speed benchmark as the final audited transportation-mode diagnostic for CP1.