# Transportation-speed diagnostic

Date: 2026-09-16
Status: broad speed conclusions retained; exact V2 benchmark requires one half-open interval rerun after audit correction.

## Audit note

The first V2 transportation-label benchmark used an inclusive-end canonicalization convention. An independent re-audit of the original GeoLife ZIP found that this convention incorrectly turned many different-mode endpoint touches into one-second ambiguities.

The corrected interval convention is standard half-open `[start, end)`. Under that convention the label accounting is:

- 14,583 unambiguous canonical windows;
- 138 ambiguous windows;
- 12,720.83 unambiguous labeled hours;
- 76.345 ambiguous hours;
- ambiguous share approximately 0.597%.

The earlier 14,537 / 1,886 window counts are superseded for reporting. See `docs/eda/14_label_interval_semantics_audit.md`.

## Historical V2 benchmark under the earlier inclusive-end convention

The earlier strict-containment V2 join matched 4,812,641 movement segments, covering 40.52% of 11,878,198 valid post-consolidation segments from labeled users.

Per-mode speed summary from that historical V2 run:

| mode | canonical windows | label users | segments | median km/h | p95 km/h | p99 km/h | max km/h | >100 | >200 | >500 | >1000 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| airplane | 17 | 6 | 9,177 | 624.54 | 881.24 | 937.92 | 1,048.11 | 57.11% | 56.61% | 52.89% | 0.0327% |
| train | 274 | 19 | 556,185 | 93.14 | 165.32 | 210.33 | 4,678.32 | 38.65% | 2.64% | 0.0025% | 0.0013% |
| car | 988 | 40 | 500,584 | 29.99 | 93.67 | 119.62 | 2,515.25 | 3.54% | 0.10% | 0.0026% | 0.0010% |
| taxi | 1,171 | 35 | 209,355 | 31.61 | 72.10 | 104.74 | 1,469.41 | 1.16% | 0.0081% | 0.0010% | 0.0005% |
| subway | 806 | 27 | 249,747 | 49.51 | 74.22 | 94.32 | 3,776.07 | 0.72% | 0.0557% | 0.0056% | 0.0024% |
| bus | 2,823 | 51 | 1,190,855 | 16.89 | 57.05 | 90.60 | 2,765.76 | 0.43% | 0.0238% | 0.0029% | 0.0008% |
| boat | 7 | 4 | 3,558 | 3.69 | 74.52 | 75.35 | 336.30 | 0.17% | 0.0281% | 0% | 0% |
| bike | 2,049 | 40 | 774,111 | 11.19 | 22.73 | 40.63 | 2,556.51 | 0.11% | 0.0125% | 0.0014% | 0.0006% |
| walk | 6,394 | 63 | 1,316,764 | 4.08 | 14.36 | 40.42 | 9,415.67 | 0.14% | 0.0243% | 0.0035% | 0.0014% |
| motorcycle | 2 | 2 | 334 | 23.17 | 37.38 | 39.07 | 48.20 | 0% | 0% | 0% | 0% |
| run | 6 | 6 | 1,971 | 4.74 | 14.64 | 25.88 | 55.11 | 0% | 0% | 0% | 0% |

## Stability versus provisional benchmark

Under the earlier inclusive-end run, canonicalization barely changed central or tail percentiles: absolute p99 deltas versus the provisional benchmark were below 0.5 km/h for every mode.

This remains useful qualitative evidence because the corrected audit shows that truly ambiguous time is still only about 0.6% of represented labeled time. It is therefore unlikely that the broad mode-speed shape is driven by label-overlap ambiguity.

## Decisions supported by the evidence

A generic `speed > 100`, `>200`, or `>500 km/h => noise` rule remains rejected. The first two conflict with legitimate train/airplane movement, and the historical benchmark places more than half of airplane segments above 500 km/h.

Rare multi-thousand-km/h maxima also appear inside non-airplane labels, so label membership does not guarantee clean GPS. Speed is therefore useful as a conservative corruption guard, not as a mode-agnostic ordinary-motion filter.

The proposed CP1 hard-speed guard remains `1,200 km/h` as a release-specific continuity boundary rather than endpoint deletion. This proposal is intentionally conservative and still requires contract review. Before treating the exact airplane maximum/share numbers as fully audited evidence for that threshold, rerun the strict-containment benchmark once under `[start, end)`.

## EDA stop condition

Open-ended speed EDA is closed for CP1. One bounded audit rerun remains: recompute the V2 segment-label join and per-mode speed table under half-open label semantics. This is a correction/verification step, not a reopening of broad exploratory analysis.
