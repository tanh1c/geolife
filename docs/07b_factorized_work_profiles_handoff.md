# Stage 07b handoff — Factorized Work-Regime Profiles\n\n## Purpose\n\nReplace Stage-07 v1 mutually-exclusive work-regime classes with independent evidence axes.\n\n## Required inputs\n\n- Stage 03a: user_behavior_features.csv\n- Stage 05b: home_consensus_private.pkl\n- Stage 05b: adaptive_work_patterns_42_private.pkl\n- Stage 06: user_summary_private.pkl\n- optional Stage 05c: candidate_comparison_private.pkl\n\nNo raw trajectory rescan is required.\n\n## Private outputs\n\n- factorized_work_profiles_private.pkl\n\n## Aggregate outputs\n\n- support_summary.csv\n- axis_summary.csv\n- pairwise_overlap.csv\n- signature_summary.csv\n- representation_summary.csv\n\n## Interpretation\n\nMultiple representation options may be true for the same user.\n\nA stable secondary anchor and multiple recurring anchors are not contradictory. Repeated routes and shifted timing are separate dimensions.\n\nDo not collapse the result back into one occupation/work class.\n\n## Next step\n\nIf measured overlap/signatures are coherent, proceed to external coarse POI / land-use enrichment as a separate semantic axis.\n

## Measured result — 2026-10-02

Executed support:

- behavior: 182 users;
- adaptive work patterns: 25;
- routine evidence: 107;
- HOME context: 25;
- independent Stage-05c evidence: 7.

Measured axes:

- 72 multiple-recurring-anchor users;
- 23 mobile-complexity users;
- 23 repeated-route users;
- 9 stable-secondary users;
- 7 independent-secondary-evidence users;
- 3 adaptive multi-anchor users;
- 2 shifted-schedule users;
- 1 unstable adaptive user.

Important overlap:

- 9 stable-secondary + multiple-recurring;
- 7 stable-secondary + repeated-route;
- 22 multiple-recurring + repeated-route;
- 2 shifted + repeated-route.

Representation signatures:

- abstain: 110;
- anchor_set: 48;
- anchor_set + route_region: 13;
- single_anchor + anchor_set + route_region: 7;
- single_anchor + anchor_set: 2;
- anchor_set + route_region + schedule_agnostic: 2.

## Handoff decision

Factorization is accepted as the mobility representation.

Do not derive one mutually-exclusive work class from these axes.

Next: Stage 07c external POI / land-use enrichment on a support-qualified subset, starting from the 25 HOME-supported users and their non-HOME recurring candidate geometry.

External context is an independent semantic axis and must not rewrite the Stage-07b mobility profile.

