# Worklog

## 2026-09-16 — CP1 foundation + EDA scaffold

Completed:

- initialized the new GeoLife repository and CP1 package structure;
- separated exploratory notebook code from future production code;
- added raw-data/license/privacy guardrails;
- documented EDA questions and preliminary source-profile observations;
- added a Modal-oriented EDA notebook and memory-bounded trajectory summarization helpers.

Evidence/status:

- files are present on branch `cp1-eda-foundation`;
- GitHub Actions CI passed for the EDA foundation;
- raw GeoLife 1.3 data is mounted in Modal and EDA is being executed against the official release.

## 2026-09-16 — Measured EDA Phase 1

Observed from the mounted release:

- 182 users;
- 18,670 trajectory files;
- 69 user folders containing `labels.txt`;
- strong long-tail imbalance: median 27.5 trajectories/user vs max 2,153;
- top 10 users account for 47.4% of all trajectories and top 50 for 84.0%;
- labeled users are heavier on average: 69 users account for 58.4% of trajectories;
- raw PLT parsing spot-check produced UTC-aware timestamps with no null timestamps in the inspected user-000 trajectory.

Interpretation and caveats are recorded in `docs/eda/02_initial_findings.md`.

## 2026-09-16 — Measured EDA Phase 2

Full trajectory-level scan completed over all 18,670 files.

Observed:

- 24,876,978 total GPS points, matching the v1.3 guide table;
- 0 null timestamps and 0 non-monotonic trajectories under the current parser;
- 698,900 duplicate-timestamp rows (2.81% of points) across 441 trajectories;
- only one invalid latitude, an isolated `400.166667` value among surrounding `40.166...` points;
- physically impossible raw speed/distance tails, including repeated ~850–862 km jumps in one-second intervals in user 062 trajectory `20080926000623`;
- at least one byte-identical trajectory duplicated across three users (`057`, `094`, `150`), confirmed by identical SHA-256.

## 2026-09-16 — Timestamp precision check

The earlier hypothesis that PLT `serial_date` might recover hidden sub-second timing was tested and rejected.

For a trajectory with 45,215 duplicate text timestamps:

- the same 45,215 duplicates remain when using `serial_date`;
- five distinct positions recorded at `2011-10-22 03:18:34` share exactly the same serial date;
- serial-date conversion differs from text timestamps only by a few microseconds of floating-point conversion noise, not meaningful extra timing precision.

Conclusion: duplicate-second observations are a property of the released timestamp precision, not a parser artifact. Speed must not be computed for zero-time pairs, and a downstream policy for same-second groups must be justified from their spatial spread.

Detailed evidence is recorded in `docs/eda/03_phase2_quality_findings.md` and `docs/eda/04_timestamp_precision_and_duplicates.md`.

Next evidence step: quantify same-second spatial spread, exact duplicate-file prevalence, and impossible-jump patterns before proposing cleaning/stay-point thresholds.
