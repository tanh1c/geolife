# Cleaning + stay-point contract

Date: 2026-09-18
Status: APPROVED — semantics reviewed and implemented; CP1 engineering baseline frozen after full-release audit, user-stratified sensitivity, and same-second transportation audit.

## Goal

Define the minimum production preprocessing contract needed before implementing the CP1 stay-point detector. The contract is intentionally conservative: it removes or breaks continuity only where EDA found concrete data-quality failure modes, while avoiding broad motion filters that would erase legitimate fast travel.

## Input contract

A trajectory is an ordered collection of observations with at least:

- `timestamp`: timezone-aware UTC timestamp;
- `latitude`: decimal degrees;
- `longitude`: decimal degrees.

Altitude is not required for stay-point detection.

## Output contract

Preprocessing returns timestamp-level observations grouped into independent `sequence_id` runs. A stay-point detector may operate only within one sequence; it must never bridge a sequence boundary.

Each retained timestamp-level observation should expose at least:

- `timestamp`;
- `latitude`;
- `longitude`;
- `raw_point_count`;
- `max_radius_m` for same-second groups;
- `sequence_id`;
- `boundary_before_reason` for diagnostics.

`boundary_before_reason` is attached to the first retained observation of a new sequence. The first sequence uses `None`. Initial reason values are:

- `invalid_coordinate`;
- `same_second_spatial_ambiguity`;
- `temporal_gap`;
- `hard_speed_guard`.

This field is diagnostic metadata; the hard semantic constraint for downstream stay detection is still `sequence_id`.

Because a discarded invalid/ambiguity timestamp may occur at the end of a file or several quality events may occur before the next retained point, `boundary_before_reason` is **not** a complete event counter. Production cleaning therefore also exposes a separate audit-event stream with at least:

- `timestamp`;
- `reason`.

The audit stream records every observed quality/boundary event, including discarded terminal timestamps. This keeps event observability separate from the retained-row schema used by the stay detector.

## Stage 1 — coordinate-domain validation

Valid coordinates require:

- latitude in `[-90, 90]`;
- longitude in `[-180, 180]`.

An invalid coordinate does not get repaired by guessing. It is not retained as a valid timestamp-level observation and it creates a continuity boundary so points before and after it are not connected into an artificial movement segment.

Evidence: the release contains one malformed latitude (`400.166667`) among otherwise plausible surrounding points.

## Stage 2 — same-second consolidation

All rows with the same timestamp are treated as simultaneous observations because the release does not expose recoverable sub-second ordering.

For a timestamp group:

1. compute coordinate-wise median latitude/longitude;
2. compute each raw point's Haversine distance to that median center;
3. let `max_radius_m` be the largest of those distances.

If `max_radius_m <= 10 m`, emit one representative point using median latitude/longitude and preserve `raw_point_count`.

The `10 m` value is a **safe-consolidation threshold**, not a valid-versus-corrupt threshold.

If `max_radius_m > 10 m`, do not collapse the group into a representative point. The release does not preserve recoverable sub-second ordering, so the group is treated as `same_second_spatial_ambiguity` and creates a continuity boundary. This reason means only that the observed spatial spread is unresolved at the released timestamp precision; it does **not** assert that the observations are necessarily corrupt.

Evidence before the mentor audit: 99.61% of measured same-second groups are within 10 m; only 835 groups exceed the threshold.

The follow-up same-second × transportation audit computed exact within-group diameter for all 835 groups and joined available transportation labels using half-open `[start, end)` semantics. Among the 403 groups with one unambiguous mode, the audit found:

- train: 3 groups, median diameter 30.08 m, all 3 within the train p99 one-second distance scale;
- subway: 25 groups, median diameter 19.07 m, 20/25 within the subway p99 one-second distance scale;
- taxi: 10 groups, 7/10 within the taxi p99 one-second distance scale;
- walk and bike: only 4/194 and 2/145 groups respectively within their diagnostic one-second reference scales;
- no unambiguous airplane groups occurred in this 835-group subset;
- 68 groups had diameter >1 km, showing that the >10 m tail also contains much stronger spatial inconsistency.

Therefore the >10 m population is heterogeneous. Transportation evidence shows that legitimate movement plus whole-second timestamp quantization is a plausible explanation for some groups, while other groups require different explanations. Production cleaning does not use transportation mode to repair or reorder observations; the conservative behavior remains to create a boundary whenever the group is not safe to collapse.

## Stage 3 — temporal continuity boundary

A stay duration must not span an unobserved outage. If the positive gap between consecutive valid timestamp-level observations exceeds `max_gap_s`, split the sequence.

`max_gap_s` is a model/configuration parameter, not a universal constant. Sensitivity values evaluated for CP1 were:

- 120 s;
- 300 s;
- 600 s.

The frozen CP1 engineering baseline uses `max_gap_s = 300` (5 minutes). It is deliberately shorter than the 20-minute dwell threshold and prevents a large unobserved interval from being counted as dwell time.

Evidence: 65.92% of trajectories contain a gap >2 min, 50.95% contain a gap >5 min, and 41.74% contain a gap >10 min.

## Stage 4 — conservative hard-speed corruption boundary

Compute Haversine speed only between consecutive valid timestamp-level observations with positive `dt` and within a continuity candidate not already split by an earlier cleaning rule.

Do NOT apply generic `100`, `200`, or `500 km/h` removal rules. The final half-open V3 transportation benchmark shows legitimate train and airplane movement in those ranges.

For CP1, use a release-specific hard guard:

`hard_speed_guard_kmh = 1200`

If a segment exceeds this value, break continuity at that segment. Do not automatically delete either endpoint because the data alone does not identify which endpoint is wrong.

Rationale from the final audited V3 benchmark:

- airplane median: 625.91 km/h;
- airplane p99: 937.99 km/h;
- airplane max: 1,048.11 km/h;
- 52.92% of canonical airplane segments exceed 500 km/h;
- clear corruptions elsewhere extend into thousands or millions of km/h.

The 1,200 km/h guard therefore preserves all observed canonical airplane segments while catching extreme release-specific corruption. It is an engineering guard for GeoLife 1.3, not a universal physical limit.

Transportation-label interval semantics are explicitly `[start, end)`. The final audit found 14,583 unambiguous windows, 138 report-level ambiguous windows, 0.597% ambiguous labeled time, and V3 coverage of 40.47%. See `docs/eda/14_label_interval_semantics_audit.md` and `docs/eda/12_transport_speed_final.md`.

## Explicit non-goals in CP1 cleaning

The cleaning stage will not:

- interpolate across long gaps;
- infer hidden sub-second ordering;
- delete points merely because speed exceeds ordinary road/train speeds;
- deduplicate identical files across users during inference;
- infer transportation mode;
- repair structurally interleaved trajectories by inventing a preferred branch.

Exact-content hashes remain an evaluation/leakage-control concern rather than an inference-time cleaning rule.

## Stay-point detector contract

The detector runs independently per `sequence_id` using Haversine distance.

The algorithm semantics are parameterized by:

- `distance_threshold_m`;
- `min_dwell_s`.

The frozen CP1 engineering baseline is:

- `distance_threshold_m = 200`;
- `min_dwell_s = 1200` (20 minutes).

These values are frozen for the first CP1 Home/Office implementation after sensitivity validation. They are not part of the immutable algorithm semantics and are not claimed to be accuracy-optimal because GeoLife does not provide direct Home/Office ground truth. A later parameter revision may change them without changing the detector definition, but it must be compared against this baseline.

Algorithm semantics:

1. choose the current point `i` as anchor;
2. advance `j` while points remain within `distance_threshold_m` of the anchor;
3. when the first point outside the radius is found, close the current candidate and evaluate dwell time from `i` through `j-1`;
4. if dwell time >= `min_dwell_s`, emit one stay point for `i..j-1`, using median latitude/longitude and recording arrival, departure, duration, and point count;
5. continue after the emitted stay; otherwise advance the anchor;
6. if the sequence ends before an outside-radius point appears, still evaluate the terminal candidate and emit it when its duration satisfies the threshold;
7. a later return inside the original anchor radius must not be merged back across the first outside-radius observation.

A stay point must never include observations from two different sequences.

Changing a parameter value (for example `200 m -> 300 m` or `20 min -> 10 min`) changes detector behavior but does not change these semantics. Changing the distance reference from anchor-based to centroid-based, skipping outside-radius observations, or changing the dwell definition would be semantic changes and require a new contract review.

## Expected stay-point output

Each stay point should contain at least:

- `sequence_id`;
- `arrival_time`;
- `departure_time`;
- `duration_s`;
- representative `latitude`;
- representative `longitude`;
- `n_points`.

## TDD acceptance cases

Implementation is locked by these reviewed semantics:

1. invalid coordinate creates a boundary and is not bridged;
2. compact same-second observations collapse to a median representative;
3. same-second spatial ambiguity creates a boundary;
4. temporal gap above `max_gap_s` prevents one stay from spanning the outage;
5. speed above the hard guard creates a boundary without guessing which endpoint is wrong;
6. a cluster inside the distance threshold but shorter than `min_dwell_s` is not a stay;
7. a cluster inside the threshold for long enough is emitted as a stay;
8. a valid stay at the end of a sequence is not lost;
9. no stay crosses a sequence boundary;
10. the first outside-radius observation closes the current stay candidate; a later return inside the original anchor radius cannot be merged back into that candidate;
11. a discarded quality event at the end of a trajectory remains observable in the audit-event stream even when no retained observation exists to carry `boundary_before_reason`.

## Sensitivity validation — complete

The final grid evaluated:

- continuity gap: 120 / 300 / 600 s;
- stay distance: 100 / 200 / 300 m;
- dwell: 10 / 20 / 30 min.

Sampling used a deterministic user-balanced/capped design rather than a path-ordered prefix:

- 182 users covered;
- 851 trajectory files sampled;
- at most 5 trajectories per user;
- heavy-user samples spread across sorted trajectory history.

The frozen `300 s / 200 m / 1200 s` configuration produced, on this sensitivity sample:

- 478 stays;
- 89 users with at least one stay;
- mean 2.626374 stays per user;
- median 4 stays per active user;
- 69 users with at least two stays;
- 52 users with at least one repeated location under the 200 m recurrence proxy;
- repeat-location user rate 0.753623;
- median stay duration 1621.5 s;
- p90 stay duration 3202.9 s.

Neighboring configurations changed coverage in expected directions without showing an instability that justified replacing the reviewed baseline. In particular, `200 m` had a stronger recurrence proxy than its immediate `100 m` and `300 m` neighbors at `300 s / 20 min`; `300 s` preserved a more conservative continuity rule than `600 s`; and `20 min` remained a middle dwell setting between broad short-stop coverage at 10 minutes and substantial coverage loss at 30 minutes.

This sensitivity analysis is evidence of behavioral stability, not proof of Home/Office classification accuracy. See `docs/design/02_staypoint_baseline_validation.md` for the recorded results and rationale.

## Frozen CP1 configuration

The first Home/Office implementation must use:

```text
same_second_radius_m   = 10
max_gap_s              = 300
hard_speed_guard_kmh   = 1200
distance_threshold_m   = 200
min_dwell_s            = 1200
```

Any future parameter change is a configuration/model revision and should be measured against this baseline. Any semantic change to sequence boundaries, anchor-based membership, outside-radius handling, or dwell definition requires contract review.