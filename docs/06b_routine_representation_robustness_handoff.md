# Stage 06b handoff — Routine Representation Robustness

## Inputs

Reuse Stage-06 private Modal Volume artifacts:

- day_sequences_private.pkl
- transitions_private.pkl
- edge_summary_private.pkl
- user_summary_private.pkl

No raw GeoLife rescan is required.

## Primary settings

- minimum usable days for fair motif/OD comparison: 6;
- repeated OD support: >=3 active days;
- collapsed-sequence motif: >=3 active days and >=50% usable-day share;
- split-half minimum support: 3 usable days per half;
- random balanced partitions: 200/user;
- departure bootstrap: 1000 active-day resamples;
- strong routine tier: >=5 active days;
- strict GMM: >=5 active days, >=8 transitions, ΔBIC>=10, component weight>=0.20, separation>=2h.

## Outputs to inspect after execution

1. motif_primary
2. motif_sensitivity
3. support_tiers
4. split_aggregate
5. random_partition_summary
6. departure_bootstrap_summary
7. strict multimodal summary + sensitivity
8. readiness

## Interpretation

- low exact top-1 agreement with low JSD means rank swapping rather than major distributional change;
- chronological JSD comparable to random partitions suggests sparse-support instability;
- chronological JSD above random p95 is drift-like evidence worth carrying into Stage 07;
- high departure concentration is stronger when its bootstrap lower bound remains high at larger active-day support;
- multimodality should not be reported from BIC alone when support is tiny.

No production or semantic inference changes are made by Stage 06b.

## Measured result — 2026-10-01

Stage-06 parity:

- 107 supported users;
- 984 supported days;
- 1,086 transitions;
- 869 user-edge rows.

Primary support-aware comparison (>=6 usable days, >=3 active-day recurrence):

- 51 eligible users;
- 8 repeated-OD users;
- 9 supported collapsed-motif users;
- 0 overlap under the current comparator.

Caveat: the current motif comparator permits single-location motifs with no transition, so zero overlap is not an apples-to-apples mobility-routine comparison.

Support tiers:

- >=2 days: 66 edges / 23 users;
- >=3 days: 25 edges / 9 users;
- >=5 days: 12 edges / 2 users.

Split-half distribution:

- 45 comparable users;
- same top edge 13.3%;
- median JSD 1.0;
- median weighted Jaccard 0.0;
- median total variation 1.0;
- median top-3 Jaccard 0.0.

Random-partition calibration:

- median chronological JSD 1.0;
- median random JSD 1.0;
- only 2/45 users (4.4%) exceed random p95.

This means broad exact-OD instability is sampling-driven rather than clear temporal drift.

Departure bootstrap:

- supported tier: 13 edges / 8 users, median observed concentration 0.888, median CI low 0.823;
- strong tier: 12 edges / 2 users, median observed concentration 0.964, median CI low 0.944;
- 9/12 strong edges have CI low >=0.7.

Strict GMM:

- 6 primary modeled edges / 1 user;
- 1 strict multimodal edge / 1 user.

Decision: Stage 07 is not yet justified on exact OD identity. A follow-up should evaluate coarser or support-normalized temporal representations and window feasibility before detector implementation.