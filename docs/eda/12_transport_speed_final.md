# Final transportation-speed diagnostic

Date: 2026-09-17
Status: AUDIT CLOSED for CP1 transportation-speed evidence.

## Corrected label semantics

Transportation labels are interpreted as half-open intervals `[start, end)`. Endpoint touching is not temporal overlap.

The final audit measured:

- 1,742 different-mode endpoint-touching pairs;
- 146 different-mode pairs with true positive-duration overlap;
- 14,583 unambiguous canonical windows;
- 149 atomic ambiguous sweep slices;
- 138 report-level ambiguous windows after merging adjacent slices with the same active mode set;
- 12,720.833 hours of unambiguous labeled time;
- 76.345 hours of ambiguous labeled time;
- ambiguous share: 0.597%.

The earlier inclusive-end 14,537 / 1,886 counts are superseded for reporting. See `docs/eda/14_label_interval_semantics_audit.md`.

## Final V3 strict-containment benchmark

Using corrected half-open canonical windows, the strict segment-label join matched 4,807,087 of 11,878,198 valid post-consolidation segments from labeled users, for 40.47% coverage.

| mode | canonical windows | label users | segments | median km/h | p95 km/h | p99 km/h | max km/h | >100 | >200 | >500 | >1000 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| airplane | 17 | 6 | 9,169 | 625.91 | 881.29 | 937.99 | 1,048.11 | 57.13% | 56.63% | 52.92% | 0.0327% |
| train | 296 | 19 | 556,136 | 93.14 | 165.32 | 210.34 | 4,678.32 | 38.65% | 2.64% | 0.0025% | 0.0013% |
| car | 995 | 40 | 499,945 | 30.05 | 93.69 | 119.63 | 2,515.25 | 3.55% | 0.10% | 0.0026% | 0.0010% |
| taxi | 1,171 | 35 | 209,078 | 31.64 | 72.11 | 104.75 | 1,469.41 | 1.16% | 0.0081% | 0.0010% | 0.0005% |
| subway | 813 | 27 | 249,389 | 49.63 | 74.22 | 94.32 | 3,776.07 | 0.72% | 0.0557% | 0.0056% | 0.0024% |
| bus | 2,823 | 51 | 1,189,927 | 16.91 | 57.05 | 90.59 | 2,765.76 | 0.43% | 0.0234% | 0.0029% | 0.0008% |
| boat | 7 | 4 | 3,552 | 3.69 | 74.52 | 75.34 | 336.30 | 0.17% | 0.0282% | 0% | 0% |
| bike | 2,053 | 40 | 773,004 | 11.19 | 22.74 | 40.63 | 2,556.51 | 0.11% | 0.0124% | 0.0014% | 0.0006% |
| walk | 6,400 | 63 | 1,314,584 | 4.08 | 14.35 | 40.39 | 9,415.67 | 0.14% | 0.0242% | 0.0034% | 0.0014% |
| motorcycle | 2 | 2 | 336 | 23.06 | 37.38 | 39.07 | 48.20 | 0% | 0% | 0% | 0% |
| run | 6 | 6 | 1,967 | 4.74 | 14.65 | 25.92 | 55.11 | 0% | 0% | 0% | 0% |

## Stability versus the earlier benchmark

The corrected half-open V3 table is effectively unchanged in shape. Key p99 values remain about 938 km/h for airplane, 210 for train, 120 for car, 91 for bus, and 40 for bike/walk. Coverage changes from 40.52% in the earlier inclusive-end V2 run to 40.47% in V3, only about 0.05 percentage point.

Therefore the broad speed conclusions are robust to the interval-semantics correction.

## Decisions supported by the evidence

A generic `speed > 100`, `>200`, or `>500 km/h => noise` rule is rejected. The corrected V3 benchmark still places 52.92% of canonical airplane segments above 500 km/h, while train movement also legitimately occupies the 100-200+ km/h range.

At the same time, rare multi-thousand-km/h maxima remain inside ordinary transport labels, so label membership does not guarantee a clean GPS segment. Speed is useful as a conservative corruption guard, not as a mode-agnostic ordinary-motion filter.

For CP1, the proposed release-specific hard guard remains `1,200 km/h`, used only to break continuity and never to guess which endpoint is wrong. The corrected V3 airplane maximum is 1,048.11 km/h, while clearly corrupted segments extend into thousands or millions of km/h. This is an engineering guard for this release, not a universal physical limit.

## EDA stop condition

Transportation-speed EDA and its interval-semantics audit are now closed for CP1. Remaining work is contract review, RED tests, implementation, and bounded stay-point threshold sensitivity.