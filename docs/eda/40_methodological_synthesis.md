# Stage 07p — Final methodological synthesis

## Purpose

Stage 07p closes the CP2-v2 HOME/OFFICE validation track.

It does not add a new semantic model, threshold, external data source, or user-level
adjudication layer.

Instead, it reads the aggregate outputs already produced by:

- Stage 05 — internal HOME/OFFICE reliability;
- Stage 07i — threshold sensitivity;
- Stage 07j — targeted OFFICE near-miss robustness;
- Stage 07l — imagery / behavior / BCL unblinding synthesis;
- Stage 07m — Trackintel semantic-only parity;
- Stage 07n — Trackintel end-to-end decomposition;
- Stage 07o — literature comparator suite.

The output is a reproducible evidence hierarchy and final policy boundary.

## Why a synthesis stage is necessary

The project now has multiple kinds of evidence that answer different questions.

Examples:

- cross-method agreement asks whether different semantic rankers choose the same
  location;
- held-out / split / dropout tests ask whether candidate identity persists under
  perturbation;
- historical POI / imagery asks whether the physical context is compatible with
  a semantic interpretation;
- Trackintel semantic parity asks whether an independent implementation chooses
  the same candidate on the same representation;
- Trackintel end-to-end asks how much upstream implementation changes the result;
- literature comparators ask whether other published heuristic families converge
  with the frozen candidate identity.

These quantities must not be averaged into one pseudo-accuracy score.

Stage 07p keeps them separate and organizes them into an evidence ladder.

## Input contract

Stage 07p requires aggregate CSVs only.

Cache root:

\`\`\`text
/mnt/geolife-data/cache/cp2_v2/
\`\`\`

Required stage folders:

\`\`\`text
05_home_office_reliability_validation/
07i_threshold_sensitivity/
07j_near_miss_office_audit/
07l_imagery_unblinding_synthesis/
07m_trackintel_semantic_parity/
07n_trackintel_end_to_end/
07o_literature_comparator_suite/
\`\`\`

No raw GPS data are required.

No private user-level pickle is required.

## Measured-lineage validation

Before synthesis, the notebook hard-validates a representative set of accepted
measurements.

Examples include:

### Stage 05

- HOME fixed-window vs recurrence: 35/42 same location;
- OFFICE fixed-window vs recurrence: 6/25 same location;
- fixed-window held-out top-1:
  - HOME 50.0%;
  - OFFICE 42.1%;
- 30% dropout retention:
  - HOME 81.7%;
  - OFFICE 78.9%.

### Stage 07i

- frozen OFFICE gate: 16 users;
- margin .10 -> .05: 18 users;
- share .30 -> .20: 23 users.

### Stage 07j / 07l

- nine one-step OFFICE near-miss users;
- only 1/9 recovers the exact candidate in both split tests;
- only 2/9 remain held-out top-1;
- no near-miss user has BCL work-compatible context within 150 m;
- imagery remains heterogeneous.

### Stage 07m

- Trackintel OSNA HOME exact: 27/27;
- Trackintel OSNA OFFICE exact: 11/16.

### Stage 07n

- CP1 -> Trackintel strong stay match: 2,125/5,821;
- Trackintel -> CP1 strong stay match: 2,088/2,157;
- end-to-end DBSCAN-200 + OSNA:
  - HOME within 200 m: 21/27;
  - OFFICE within 200 m: 9/16.

### Stage 07o

- scikit-mobility-style HOME exact: 26/27;
- SCITEPRESS-style HOME exact: 25/27;
- SCITEPRESS-style OFFICE exact: 15/16;
- geohash HOME adaptation within 200 m: 20/27.

If these measurements no longer reproduce from the caches, Stage 07p stops
instead of silently synthesizing inconsistent lineage.

## HOME evidence ladder

HOME evidence is organized into:

1. internal cross-method convergence;
2. held-out / dropout persistence;
3. independent semantic implementation;
4. end-to-end pipeline sensitivity;
5. literature-style temporal/spatial comparators.

The expected overall interpretation is not that HOME is known to be correct.

It is that HOME candidate identity is comparatively stable and convergent across
multiple independent formulations.

## OFFICE evidence ladder

OFFICE uses the same hierarchy but has a different pattern.

Important distinctions:

- fixed-window and HoWDe-style schedule-aware methods can agree strongly;
- recurrence-style alternate-location ranking agrees poorly;
- held-out persistence is weaker;
- independent comparators often select many more WORK candidates than
  production;
- end-to-end representation changes affect OFFICE more strongly than HOME.

Therefore comparator agreement is evidence of plausibility, not a replacement
for abstention.

## Near-miss policy synthesis

Stage 07p carries forward the nine one-step OFFICE near-miss users.

The key policy distinction is:

\`\`\`text
candidate plausibility
!=
candidate persistence
!=
production emission
\`\`\`

The near-miss cohort contains several temporally plausible WORK candidates, but
the accumulated robustness/context evidence does not justify a global OFFICE
gate relaxation.

## Pipeline-sensitivity synthesis

Stage 07n is summarized in three layers:

1. stay extraction;
2. location geometry;
3. semantic candidate.

The largest observed divergence is the stay inventory itself.

Therefore end-to-end disagreement must not be attributed to OSNA or semantic
ranking alone.

## Literature synthesis

Stage 07o contributes three different comparator contracts:

- exact candidate identity on the frozen production namespace;
- spatial correspondence for geohash;
- descriptive important-location feature structure for Pavan.

These remain separate in Stage 07p.

No unified "literature score" is created.

## Claim boundary

Stage 07p explicitly distinguishes supported from unsupported project claims.

Supported examples:

- HOME candidate identity is strongly convergent across multiple heuristic
  families;
- OFFICE is more method- and representation-sensitive;
- the OFFICE gate is conservative in coverage;
- Trackintel end-to-end differences arise substantially upstream;
- several share-near candidates are temporally plausible but not robust enough
  for production.

Unsupported examples:

- HOME/OFFICE semantic accuracy is known from GeoLife ground truth;
- a POI or imagery match proves employment;
- Trackintel or literature comparators are ground truth;
- external heuristic agreement alone justifies near-miss promotion.

## Final policy boundary

Stage 07p is expected to reproduce the frozen production decision:

\`\`\`text
HOME   = 27
OFFICE = 16
\`\`\`

and:

- no HOME gate change;
- no OFFICE gate change;
- no global margin relaxation;
- no global share relaxation;
- no automatic promotion of the nine near-miss candidates.

## Outputs

Aggregate-only Stage-07p outputs:

- \`lineage_validation.csv\`;
- \`home_evidence_ladder.csv\`;
- \`office_evidence_ladder.csv\`;
- \`near_miss_policy_summary.csv\`;
- \`pipeline_sensitivity_summary.csv\`;
- \`final_policy_snapshot.csv\`;
- \`claim_boundary.csv\`.

Cache root:

\`\`\`text
/mnt/geolife-data/cache/cp2_v2/07p_methodological_synthesis/
\`\`\`

## Exit criterion

The CP2-v2 validation track can close when:

1. all measured-lineage checks pass;
2. the final policy snapshot reproduces HOME 27 / OFFICE 16;
3. the claim boundary is explicit;
4. no new threshold is selected from comparator agreement;
5. the synthesis is documented in the worklog and learning journals.
