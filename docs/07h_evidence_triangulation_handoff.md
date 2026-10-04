# Stage 07h handoff — Multi-source evidence triangulation

## Run

Use:

`notebooks/07h_evidence_triangulation.ipynb`

from current `main`.

No API, web, Modal, source download, OSM query, or BCL extraction is performed.

## Required private inputs

```text
/mnt/geolife-data/cache/cp2_v2/05b_home_consensus_adaptive_work/
  adaptive_work_patterns_42_private.pkl

/mnt/geolife-data/cache/cp2_v2/05c_stable_secondary_evidence/
  candidate_comparison_private.pkl

/mnt/geolife-data/cache/cp2_v2/07e_semantic_distance_alignment/
  stable_secondary_user_comparisons_private.pkl

/mnt/geolife-data/cache/cp2_v2/07g_bcl_poi_2008_alignment/
  stable_secondary_bcl_comparisons_private.pkl
```

Do not rerun 05c, 07e, or 07g before 07h.

## Expected frozen input counts

The notebook should print:

```text
05b stable-secondary rows: 9
05c fair-comparator users: 7
07e OSM comparison users: 9
07g BCL comparison users: 9
```

It then validates that candidate location ids match across every available source.

Expected:

`candidate identity validation: PASS`

Any mismatch is a hard stop.

## Important outputs

Send the executed notebook.

The main tables are:

1. `SOURCE COVERAGE`
2. `EXTERNAL SOURCE DIRECTION AGREEMENT BY RADIUS`
3. `CANDIDATE CONTEXT OVERLAP AT 100m`
4. `TRIANGULATION SIGNATURES AT 100m`
5. `BEHAVIOR BAND × NUMBER OF POSITIVE EXTERNAL SOURCES AT 100m`
6. `DECISION SNAPSHOT`

The most important decision fields are:

- `behavior_strict_support_users`;
- `behavior_directional_majority_users`;
- `external_both_positive_100m_users`;
- `strict_three_way_convergence_100m_users`;
- `directional_three_way_convergence_100m_users`;
- `candidate_context_both_sources_100m_users`.

## Interpretation

Primary behavioral support is still the Stage-05c rule:

`top1_evidence_axes >= 3`.

The weaker `behavior_directional_majority` only means the candidate beats the peer median on at least 3/4 behavior axes.

OSM/BCL signs remain same-user candidate-minus-peer context differences.

Do not convert a triangulation signature into WORK/OFFICE.

Do not retune any mobility or semantic threshold after seeing the result.


## Final measured handoff — 2026-10-04

Stage 07h completed successfully on commit `ff79fdd`.

Measured decision snapshot:

```text
stable_secondary_users                       9
behavior_available_users                     7
behavior_strict_support_users                0
behavior_directional_majority_users          3
both_external_sources_users                  9
all_three_sources_users                      7
external_both_positive_100m_users            1
strict_three_way_convergence_100m_users      0
directional_three_way_convergence_100m_users 0
candidate_context_both_sources_100m_users    1
```

At 100 m:

- OSM and BCL are both positive for only 1 / 9 users;
- both negative for 3 / 9;
- directly opposite in sign for 3 / 9;
- exact-candidate context occurs in both sources for only 1 / 9.

The single user positive in both external sources has weak Stage-05c behavioral evidence.

Final decision:

- no strict or directional three-way convergence;
- no WORK/OFFICE semantic promotion;
- no threshold retuning;
- the semantic-source track is closed.

The saved Stage-07h private panel can support future audit/review, but no further source-mining stage is recommended on this cohort without stronger ground truth.
