# Stage 07h — Multi-source evidence triangulation

## Purpose

Stages 05c, 07e, and 07g independently asked whether the exact Stage-05b stable-secondary anchor is special relative to other recurring non-HOME anchors of the same user.

They used different evidence families:

- Stage 05c: behavioral regularity / temporal relation to HOME;
- Stage 07e: historical OSM mapped context;
- Stage 07g: BCL POI 2008 place-name lexical context.

Each source closed as null/mixed at the aggregate level.

Stage 07h asks a different question:

> Even if no source is persuasive on its own, do the same individual stable-secondary users consistently show candidate-favoring evidence across multiple independent sources?

This is a triangulation audit, not a new semantic classifier.

## Frozen cohort

The base cohort is the Stage-05b `stable_secondary_anchor` group.

Current CP2-v2 count:

- 9 stable-secondary users;
- one exact `dominant_location_id` candidate per user.

Stage 07h must never define its cohort from OSM/BCL availability. External-source missingness remains evidence availability, not cohort membership.

## Upstream evidence contracts

### Stage 05c — behavioral

Private input:

`05c_stable_secondary_evidence/candidate_comparison_private.pkl`

Current support:

- 7 / 9 stable-secondary users have a fair recurring-anchor comparator;
- 4 valid behavioral evidence axes where available.

Primary Stage-05c criterion remains unchanged:

`top1_evidence_axes >= 3`

The existing measured result has 0 users satisfying that primary criterion.

Stage 07h also carries a weaker descriptive flag:

`beats_peer_median_axes >= 3`

This is called `behavior_directional_majority`. It is not primary behavioral validation.

### Stage 07e — historical OSM

Private input:

`07e_semantic_distance_alignment/stable_secondary_user_comparisons_private.pkl`

Current support:

- 9 / 9 stable-secondary users have an eligible exact-candidate vs same-user-peer comparison.

Source-native fields are retained at:

- 25 m;
- 50 m;
- 100 m.

The direction is the candidate work-compatible-context indicator minus the peer-anchor context share.

### Stage 07g — BCL POI 2008 lexical context

Private input:

`07g_bcl_poi_2008_alignment/stable_secondary_bcl_comparisons_private.pkl`

Current support:

- 9 / 9 stable-secondary users have a BCL exact-candidate vs same-user-peer comparison.

Again the source-native comparison is retained at 25 / 50 / 100 m.

BCL lexical context remains heuristic external name-string evidence, not a trusted semantic label.

## Candidate identity gate

The candidate location id must match across every available source:

- Stage 05b `dominant_location_id`;
- Stage 05c `secondary_location_id`;
- Stage 07e `candidate_location_id`;
- Stage 07g `candidate_location_id`.

Any mismatch is a hard error.

This gate prevents false multi-source convergence created by comparing different physical anchors that happen to belong to the same user.

## No composite semantic score

Stage 07h intentionally does not create a weighted score such as:

`behavior + OSM + BCL = WORK probability`.

The evidence families differ in measurement quality, temporal coverage, source completeness, and semantic meaning. A numeric sum would imply comparability that the project has not established.

Instead Stage 07h preserves:

- behavior top-1 axis count;
- behavior beats-peer-median axis count;
- OSM candidate-minus-peer differences at each radius;
- BCL candidate-minus-peer differences at each radius;
- candidate-context presence per external source;
- positive / neutral / negative sign per external source and radius.

## Behavioral bands

For compact aggregate summaries:

- `strict`: primary Stage-05c criterion, top-1 on at least 3/4 axes;
- `partial`: exactly 2 top-1 axes;
- `weak`: 0–1 top-1 axes;
- `unavailable`: no fair Stage-05c comparator.

This is only a behavior-evidence band.

## External-source directional signs

For OSM and BCL separately, at each threshold:

- `positive`: candidate-minus-peer share > 0;
- `neutral`: difference = 0;
- `negative`: candidate-minus-peer share < 0;
- `unavailable`: no source comparison.

The primary shared cross-source radius is 100 m because both upstream stages define complete composite context at that same maximum threshold.

The 25 m and 50 m results remain explicit sensitivity views.

## Triangulation views

Stage 07h produces five complementary aggregate views.

### 1. Source coverage

How many of the 9 frozen users have:

- behavior;
- OSM;
- BCL;
- both external sources;
- all three sources.

### 2. External directional agreement by radius

At 25 / 50 / 100 m:

- both sources positive;
- both sources negative;
- same sign including neutral;
- opposite positive/negative;
- OSM-positive count;
- BCL-positive count.

### 3. Candidate context overlap at 100 m

For exact stable-secondary candidates:

- both OSM and BCL context;
- OSM only;
- BCL only;
- neither.

This asks whether the two external sources identify the same candidate anchors as context-bearing.

### 4. Triangulation signatures

Aggregate combinations of:

- behavioral band;
- OSM/BCL direction at 100 m;
- candidate context overlap at 100 m.

User ids remain in the private panel only.

### 5. Decision snapshot

Counts:

- behavior-primary support;
- weaker behavior directional-majority support;
- both-external-positive users at 100 m;
- strict three-way convergence;
- weaker directional three-way convergence;
- candidate context in both external sources.

## Strict versus directional convergence

`strict_three_way_convergence_100m` requires:

1. Stage-05c primary behavioral support (`top1 >= 3`);
2. OSM candidate-minus-peer > 0 at 100 m;
3. BCL candidate-minus-peer > 0 at 100 m.

This flag is deliberately difficult to satisfy.

`directional_three_way_convergence_100m` replaces the primary behavior criterion with the weaker:

`beats_peer_median_axes >= 3`.

It is secondary/descriptive only.

Neither flag is a semantic WORK/OFFICE class.

## Outputs

Private:

`/mnt/geolife-data/cache/cp2_v2/07h_evidence_triangulation/stable_secondary_triangulation_private.pkl`

Aggregate:

- `source_coverage.csv`;
- `external_direction_by_threshold.csv`;
- `candidate_context_overlap_100m.csv`;
- `triangulation_signature_summary.csv`;
- `behavior_external_relationship.csv`;
- `decision_snapshot.csv`.

## Interpretation boundary

Triangulation can strengthen a statement only about **evidence consistency**.

It cannot establish:

- workplace truth;
- OFFICE;
- occupation;
- employer identity;
- employment status.

If strict convergence is zero, the correct result is that no user satisfies the predeclared multi-source convergence requirement.

If one or more users show directional convergence, that remains descriptive unless the primary behavioral criterion and independent semantic evidence are jointly compelling.

No upstream threshold may be tuned after seeing the 07h result.


## Measured result — 2026-10-04

Stage 07h executed successfully on repository commit `ff79fdd`.

There was no traceback. The candidate-location identity gate passed across all available Stage-05c, Stage-07e, and Stage-07g evidence, and the aggregate/private outputs were saved under:

`/mnt/geolife-data/cache/cp2_v2/07h_evidence_triangulation/`.

### Source coverage

The frozen cohort remains 9 Stage-05b stable-secondary users.

| source | users available | share |
|---|---:|---:|
| Stage 05c behavior | 7 / 9 | 77.8% |
| Stage 07e OSM | 9 / 9 | 100% |
| Stage 07g BCL | 9 / 9 | 100% |
| OSM + BCL | 9 / 9 | 100% |
| behavior + OSM + BCL | 7 / 9 | 77.8% |

The two users without Stage-05c fair comparators remain in the frozen cohort; they are evidence-unavailable, not negative behavioral cases.

### External-source directional agreement

Candidate-minus-peer direction by shared radius:

| threshold | both positive | both negative | same direction incl. neutral | opposite positive/negative | OSM positive | BCL positive |
|---|---:|---:|---:|---:|---:|---:|
| 25 m | 1 | 2 | 6 | 0 | 2 | 2 |
| 50 m | 1 | 3 | 5 | 0 | 2 | 3 |
| 100 m | 1 | 3 | 4 | 3 | 2 | 4 |

At 25–50 m, OSM and BCL often share the same direction, but only one user is positive in both sources.

At the primary 100 m radius, the external sources become more heterogeneous:

- 1 user positive in both;
- 3 users negative in both;
- 3 users have directly opposite positive/negative directions;
- only 4 / 9 have the same sign when neutral is included.

Therefore the external sources do not converge toward a common stable-secondary-favoring pattern.

### Exact-candidate context overlap at 100 m

| pattern | users | share |
|---|---:|---:|
| both OSM and BCL context | 1 | 11.1% |
| OSM only | 1 | 11.1% |
| BCL only | 3 | 33.3% |
| neither | 4 | 44.4% |

Only 1 / 9 exact stable-secondary candidates carries context in both external sources.

This is consistent with the different source coverage/semantics already observed in 07e and 07g; BCL identifies more candidate-side context than historical OSM.

### Behavior bands and external evidence

The measured behavioral bands contain:

- 0 strict users;
- 1 partial user;
- 6 weak users;
- 2 behavior-unavailable users.

This preserves the Stage-05c primary result: no stable-secondary user is top-1 on at least 3 / 4 independent behavioral axes.

There are 3 users with the weaker `behavior_directional_majority` criterion (`beats_peer_median_axes >= 3`).

However:

- the single user with both OSM and BCL positive at 100 m is in the **weak** behavioral band;
- no behavior-directional-majority user is simultaneously positive in both external sources.

The partial behavior user has zero positive external sources at 100 m despite beating the peer median on all 4 behavioral axes.

### Decision snapshot

Final counts:

| field | users |
|---|---:|
| stable-secondary users | 9 |
| behavior available | 7 |
| behavior strict support | 0 |
| behavior directional majority | 3 |
| both external sources available | 9 |
| all three sources available | 7 |
| OSM + BCL both positive at 100 m | 1 |
| strict three-way convergence at 100 m | 0 |
| directional three-way convergence at 100 m | 0 |
| exact candidate has context in both external sources at 100 m | 1 |

The strongest predeclared result is therefore:

`strict_three_way_convergence_100m_users = 0`.

Even after relaxing behavior from the primary `top1 >= 3` rule to the weaker directional-majority criterion, convergence remains:

`directional_three_way_convergence_100m_users = 0`.

## Stage 07h decision

1. No stable-secondary user satisfies the predeclared strict three-source convergence requirement.
2. No user satisfies even the weaker directional three-source convergence requirement.
3. The only user positive in both external sources at 100 m has weak behavioral evidence.
4. OSM and BCL frequently disagree at the user level by 100 m, so combining them into a single semantic score would hide meaningful source disagreement.
5. The evidence does not support promotion of stable-secondary anchors to WORK/OFFICE.
6. Do not tune mobility or semantic thresholds after this result.
7. Close the current semantic-source track.

Further progress on semantic WORK/OFFICE validity should require qualitatively better supervision or ground truth rather than additional post-hoc source hunting on the same nine-user cohort.

The stable-secondary pattern remains a valid descriptive mobility structure. The correct project-level claim is that its behavioral recurrence is real, while the available independent semantic evidence does not establish a general WORK/OFFICE interpretation.
