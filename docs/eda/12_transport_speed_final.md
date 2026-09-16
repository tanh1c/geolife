# Final transportation-speed diagnostic

Date: 2026-09-16

This closes the speed-focused EDA before the stay-point cleaning contract is implemented.

## Canonical V2 benchmark

Transportation labels were first canonicalized into windows with exactly one distinct active mode. Periods with simultaneous different modes were excluded. This left 14,537 unambiguous windows and 1,886 ambiguous windows; ambiguous time was only 76.9 hours, or 0.60% of represented labeled time.

The V2 strict-containment join matched 4,812,641 movement segments, covering 40.52% of 11,878,198 valid post-consolidation segments from labeled users.

Per-mode V2 speed summary:

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

Canonicalization barely changed the central or tail percentiles. The p99 deltas are all below 0.5 km/h in absolute value; airplane changes by +0.03 km/h, train by -0.02, car by +0.05, taxi by +0.13, bus by +0.12, bike by -0.02, and walk by -0.46. Therefore the broad transportation-speed shape is robust to the overlap correction.

## Decisions supported by the evidence

A generic `speed > 100`, `>200`, or `>500 km/h => noise` rule is rejected. The first two would remove substantial legitimate train/airplane movement, and more than half of canonical airplane segments exceed 500 km/h.

At the same time, rare multi-thousand-km/h maxima appear even inside non-airplane labels, which proves that label membership does not guarantee clean GPS. Speed remains useful as a conservative corruption guard, but not as a mode-agnostic ordinary-motion filter.

For the stay-point preprocessing contract, the proposed hard speed guard is 1,200 km/h and is used only as a continuity boundary, not to delete either endpoint. This value sits above the maximum canonical airplane speed observed in the release (1,048.11 km/h) while catching clearly impossible corruption such as the repeated multi-million-km/h jumps in user 062. It is a conservative release-specific engineering guard, not a universal physical law.

## EDA stop condition

Speed-focused EDA is now complete for CP1. The remaining work is implementation and stay-point threshold sensitivity, not additional open-ended data-quality exploration.