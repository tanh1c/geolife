# Tasks 7–8 final-preparation report

## Scope
Implemented descriptive, non-exclusive behavioral candidate flags, outlier interpretation, deterministic case aliases, private artifact wiring, report rendering, and reproducibility provenance. No full ZIP execution was performed.

## Implemented
- Candidate outputs retain `unknown_or_insufficient` unless observation support is adequate.
- High-mobility thresholds are empirical cohort quantiles and are retained in the candidate-table attributes for summary provenance.
- `rare_but_coherent` requires repeatable mobile or shifted evidence; CP1 boundary counts remain data-quality events.
- Case-facing data uses only `Case A`-style aliases and omits coordinates and raw user IDs; the alias mapping is retained only in the private case artifact.
- Private CSV writers remove coordinates, source files, and raw timestamp fields. `summary.json` records ZIP hash when present, git SHA, frozen configuration, package versions, and seed.
- The committed report explicitly answers Q1–Q10 with pending full-release sections for Task 9.

## Verification
- Focused Task 7–8 pytest selection passed: 6 tests.
- Full pytest suite passed; focused Ruff check passed.

## Deferred
- Full release ZIP materialization, figures, and measured aggregate answers are intentionally deferred to Task 9.
