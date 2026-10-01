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
