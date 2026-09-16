# Transportation-mode speed diagnostic — provisional

Date: 2026-09-16

This analysis joins post-consolidation movement segments to same-user transportation labels. Results are provisional because the raw label intervals themselves contain overlapping/touching intervals, including conflicts between different modes.

## Label integrity

- 14,718 label intervals across 69 users;
- 0 null starts, 0 null ends, 0 intervals with end < start;
- 1,903 intervals are overlapping or touching the immediately previous interval under the current check;
- examples include genuine overlaps in user 020, sometimes across different modes.

This means a simple `merge_asof` to the most recent label start is not sufficient to guarantee an unambiguous mode assignment. Exact per-mode statistics below must therefore be treated as provisional until overlapping label windows are canonicalized.

## Coverage

Among 11,878,198 valid post-consolidation movement segments from labeled users, 4,849,858 segments were matched under the current strict-containment join, for 40.83% coverage.

The transportation labels are auxiliary movement labels, not Home/Office ground truth, and they cover only part of the observed movement history.

## Provisional speed distributions

Key observed segment distributions under the current join:

- airplane: 9,180 segments, median 624.4 km/h, p95 881.2, p99 937.9, max 1,048.1; 52.88% exceed 500 km/h;
- train: 560,826 segments, median 92.9 km/h, p95 165.3, p99 210.3;
- car: 504,235 segments, median 30.2 km/h, p95 93.6, p99 119.6;
- taxi: 210,614 segments, median 31.5 km/h, p95 72.1, p99 104.6;
- subway: 250,413 segments, median 49.5 km/h, p95 74.2, p99 94.3;
- bus: 1,199,439 segments, median 16.9 km/h, p95 56.9, p99 90.5;
- walk: 1,334,467 segments, median 4.1 km/h, p95 14.4, p99 40.9;
- bike: 774,818 segments, median 11.2 km/h, p95 22.7, p99 40.7.

Rare modes such as boat, run, and motorcycle have too few intervals/users for strong distributional conclusions.

## Interpretation

The broad shape is already informative despite overlap contamination:

1. a global 500 km/h filter would clearly remove a large amount of labeled airplane movement and is therefore not acceptable as a generic cleaning rule;
2. the high-speed 500–1,000 km/h band has a plausible transportation-mode explanation in airplane segments;
3. extreme multi-thousand-km/h maxima still appear inside non-airplane labels, so label membership alone does not guarantee a clean segment;
4. exact threshold selection should wait until overlapping labels are converted to unambiguous time windows and the mode summary is recomputed.

## Next step

Canonicalize same-user label intervals into non-overlapping windows. Periods covered by only one distinct active mode remain usable; periods with multiple distinct active modes are marked ambiguous and excluded from the speed benchmark. Recompute coverage and per-mode speed percentiles on those unambiguous windows, then freeze the EDA-backed cleaning contract.