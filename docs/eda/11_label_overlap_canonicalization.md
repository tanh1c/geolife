# Transportation-label overlap canonicalization

Date: 2026-09-16
Status: corrected after an independent interval-semantics audit.

## Why canonicalization was needed

The first transportation-mode benchmark found label intervals that either overlapped or touched at endpoints. A simple `merge_asof` assignment is unsafe when multiple different modes are truly active at the same time, so ambiguous periods must be excluded from the speed benchmark.

## Interval-semantics correction

The original canonicalization treated label end times as inclusive by internally converting each label to `[start, end + 1 second)`. Under that convention, two different-mode labels that only meet at the same endpoint are counted as ambiguous for one second.

An independent re-audit of the original GeoLife 1.3 ZIP used the standard half-open convention `[start, end)`, where endpoint touching is not temporal overlap. Under this convention the corrected accounting is:

- 14,583 unambiguous canonical windows;
- 138 ambiguous windows;
- 12,720.83 hours of unambiguous labeled time;
- 76.345 hours of ambiguous labeled time;
- ambiguous share of represented labeled time: approximately 0.597%.

The audit reported 1,742 different-mode pairs that only touch at an endpoint and 146 different-mode pairs with true temporal overlap. These pair counts should not be conflated with the earlier `1,903 overlapping/touching intervals` integrity statistic because that earlier metric mixed touching and overlap and was based on adjacency to the immediately previous interval.

Interpretation: true temporal ambiguity is uncommon by both duration and canonical-window count. The previous wording that overlap was "common when counted as windows" was misleading because the large ambiguous-window count was inflated by endpoint-touch handling.

## Historical inclusive-end result

For traceability, the earlier inclusive-end canonicalization produced:

- 14,537 unambiguous windows;
- 1,886 ambiguous windows;
- 12,723.9 hours of unambiguous labeled time;
- 76.9 hours of ambiguous labeled time.

Those numbers are retained only as historical evidence of the earlier convention; they are superseded for mentor-facing reporting by the half-open figures above.

## Status of the V2 strict-containment benchmark

The previously recorded V2 benchmark was computed from the inclusive-end canonical windows:

- 4,812,641 matched movement segments;
- 40.52% coverage of 11,878,198 valid segments from labeled users;
- 37,217 fewer matched segments than the provisional pre-canonicalization join.

Its broad per-mode speed shape was almost unchanged from the provisional benchmark, which supports the qualitative conclusion that label ambiguity is not driving the speed distributions.

However, the exact V2 matched-segment count and per-mode percentiles have not yet been recomputed under the corrected `[start, end)` convention. A single bounded rerun is required before those exact V2 values are treated as the final audited benchmark.

See `docs/eda/14_label_interval_semantics_audit.md` for the correction record.
