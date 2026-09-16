# Transportation-label overlap canonicalization

Date: 2026-09-16

This note records the final label-quality correction before freezing the EDA-backed cleaning contract.

## Why canonicalization was needed

The first transportation-mode benchmark found overlapping/touching label intervals, including true overlaps across different modes. A simple `merge_asof` assignment can therefore choose one label even when another mode is simultaneously active.

The labels were canonicalized into windows where exactly one distinct mode is active. Windows with multiple active modes were marked ambiguous and excluded from the benchmark. Same-mode overlaps were merged.

## Measured result

Canonicalization produced:

- 14,537 unambiguous canonical windows;
- 1,886 ambiguous windows;
- 12,723.9 hours of unambiguous labeled time;
- 76.9 hours of ambiguous labeled time;
- ambiguous time share: 0.60% of all labeled time represented by canonical + ambiguous windows.

The most common ambiguous mode combinations are `(bus, walk)`, `(bike, walk)`, `(taxi, walk)`, `(subway, walk)`, `(car, walk)` and `(train, walk)`. Many ambiguity windows are only one second long, while some user-020 examples span much longer periods.

Interpretation: overlap is common when counted as windows but small by duration. Therefore the broad transportation-speed conclusions from the provisional benchmark are unlikely to be driven solely by overlap ambiguity, but the exact per-mode percentiles should still be recomputed on canonical unambiguous windows.

## V2 strict-containment join status

All 69 labeled users were reprocessed using canonical windows. Summing the per-user outputs yields 4,812,641 matched movement segments. Against 11,878,198 valid movement segments from labeled users, this is about 40.52% coverage.

Relative to the provisional join (4,849,858 matched segments), canonicalization removes 37,217 segments, about 0.77% of the previously matched benchmark. This is consistent with the small 0.60% ambiguous-time share.

The remaining step is to recompute the per-mode speed summary from the V2 cache and compare it with the provisional table. After that comparison, no further label EDA is planned for CP1 unless a specific anomaly requires it.
