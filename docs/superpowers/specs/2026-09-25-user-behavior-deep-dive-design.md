# User behavior deep-dive EDA design

## Purpose

Run a behavior-first exploratory audit before any future Home/Office/POI redesign. The work measures observed recurrence, schedules, mobility, observation quality, and frozen-baseline abstentions. It does not define a new production heuristic, semantic ground truth, occupation label, or preference claim.

## Scope and invariants

- Reuse frozen CP1 only: same-second radius 10 m, continuity gap 300 s, speed guard 1,200 km/h, stay radius 200 m, dwell 1,200 s.
- Use `clean_trajectory()` / `clean_trajectory_with_audit()` and `detect_staypoints()`; do not alter CP1.
- Do not change `src/geolife/model/home_office.py`, API behavior, or `notebooks/03_home_office_baseline.ipynb`.
- Treat frozen CP2 v1 only as a reproducibility comparator; the all-resolved behavioral view is exploratory and must never be presented as a production migration.
- Do not claim accuracy, true Home/Work, an occupation, a hobby/favorite, or a precise place.

## Inputs, materialization, and provenance

The runner reads `data/Geolife Trajectories 1.3.zip` locally and enumerates all 182 release users. One frozen CP1 pass materializes two private, read-only-on-rerun caches under `artifacts/03a/`:

- `stays_baseline_v1.pkl`: stay rows with source lineage;
- `cleaned_point_daily_metrics.pkl`: user-day point-level movement and observation-quality aggregates only, with no raw points retained in committed output.

The runner validates 5,821 stays across 136 users. A mismatch stops the EDA. It does not use point-level data to reimplement or reinterpret stay detection.

`summary.json` records ZIP SHA-256, current git commit, frozen CP1 config, analysis config, random seed, Python/package versions, timezone lookup package/version, and available timezone-data version. Every generated aggregate links to this provenance snapshot.

## Three analytical layers

### 1. Frozen baseline comparator

Use `HomeOfficeConfig`, `build_semantic_locations()`, and `infer_home_office()` unchanged. Begin the audit universe with all 182 GeoLife users, then left-join CP1 stays and frozen-v1 results so `no_cp1_stay` is measurable.

For HOME and OFFICE independently, assign one mutually exclusive comparator result in this order:

1. `no_cp1_stay`;
2. `outside_frozen_v1_geographic_scope`;
3. `no_recurring_location`;
4. `no_behavioral_window_overlap`;
5. `insufficient_relevant_dates`;
6. `share_below_frozen_gate`;
7. `margin_below_frozen_gate`;
8. `emitted`.

Window overlap precedes date support so a user with zero overlap is not hidden inside `insufficient_relevant_dates`. The audit separately marks identical leading HOME/OFFICE candidates; it never invents a second location.

### 2. All-resolved stay behavioral view

The main recurrence/dwell view uses all CP1 stays with an IANA timezone resolved per stay coordinate and timestamps converted to that stay's local wall-clock time. It measures anchors, dwell, time distributions, motifs, and schedule evidence without excluding valid non-Beijing behavior.

### 3. Cleaned-point movement and observation-quality view

Movement features use cleaned point-level trajectories after exactly the frozen CP1 cleaning rules. They do not use stay-to-stay displacement as actual travel distance.

Per user-day calculate total retained points, observed span, largest inter-point gap, large-gap flag, cleaned point travel distance, movement duration proxy from positive-time adjacent segments, transition/boundary count, first and last local observed hour, and point coverage across hours. Join these day-level rows to stay-derived day features by `user_id` and local date.

If a movement metric cannot be supported from cleaned points, expose it only as `stay_transition_distance_lower_bound` or `movement_proxy`, never as actual mobility.

## Observation-quality and usable-day layer

GeoLife sampling is incomplete. Every user-day has:

- `observed_span_h`;
- `point_count`;
- `stay_count`;
- `largest_gap_h`;
- `has_large_gap`;
- `usable_for_temporal_profile`;
- `usable_for_motif`.

Predefined initial controls, reported as sensitivity rather than frozen decisions:

- temporal-profile usable day: at least 3 cleaned points, observed span >= 2 h, and no gap > 6 h within the observed span;
- motif usable day: at least one stay and at least 2 h between first and last stay observation;
- schedule-stability eligible user: at least 2 active calendar weeks, at least 3 usable temporal-profile days in both early and late halves, and >= 6 h dwell mass in each half.

Temporal, motif, and mobility summaries report all observed days and usable-day-only results. Any candidate flag depending on schedule stability requires the eligible-user condition. Sparse/insufficient is a separate result, not irregular behavior.

## Feature pipeline

### Coverage

For every release user: CP1 stay count, cleaned-point active days, active weeks, observation span, stays per active day, median daily observed dwell, point coverage, and usable-day counts. This separates under-observation from unusual behavior.

### Spatial recurrence and location-ID sensitivity

Main descriptive locations use user-scoped complete-link clustering at 200 m to remain comparable to notebook 03. Run a targeted 100/200/300 m sensitivity only for primary conclusions:

- dominant-anchor, two-anchor, multiple-anchor, and no-stable-anchor counts;
- top-anchor identity stability;
- recurring-location counts;
- motif and regime-candidate membership stability.

The report states when a conclusion is stable around 200 m and labels it threshold-sensitive when it is not. It does not rerun every visualization at all thresholds.

For each threshold, assign deterministic location IDs by sorting clusters per user by total dwell descending, then stay count descending, then first local arrival timestamp ascending, then internal cluster key ascending. Render them only as `L0`, `L1`, etc.; no coordinates appear in CSV/report/figures.

Compute semantic/recurring location counts, top 1/2/3 stay shares, top 1/2 dwell shares, normalized location entropy, radius of gyration/equivalent spread, and median/p90 distance to the most frequent location.

### Temporal behavior and stability

Use dwell-weighted local-time 24-hour histograms, weekday×hour and weekend×hour matrices, dominant stationary hours, night/day distribution, weekday/weekend difference, hour entropy, and temporal concentration.

The primary stability output is continuous Jensen-Shannon distance: early-vs-late eligible-day distributions plus median pairwise weekly JSD where adequate weeks exist. Candidate wrappers are descriptive only:

- stable shifted/night-like: eligible, low within-user JSD, and a repeatable dwell peak materially shifted relative to frozen windows;
- stable conventional-like: eligible, low within-user JSD, with dwell concentrated in the frozen comparison windows;
- unstable/rotating-like: eligible with high JSD or materially changing weekly profiles;
- insufficient: does not meet support.

Thresholds for low/high JSD are selected from the empirical distribution and reported with sensitivity; they are not production thresholds.

### Daily mobility, motifs, and transport support

Use cleaned-point metrics for movement/travel and stays for recurrence/dwell. User-day motifs are ordered deterministic location IDs from usable motif days. Measure most frequent motif, motif frequency, distinct motifs, motif entropy, weekday stability, and weekend stability.

Transportation labels are optional supporting evidence only for labeled users. Report label coverage before comparing stationary, walking/transit-heavy, and high-mobility patterns. Users without labels remain in every primary analysis.

### Baseline abstention audit and descriptive regimes

Compare: both emitted, HOME-only, OFFICE-only, recurring-but-neither, HOME-rejected, OFFICE-rejected, no recurrence, same leading candidate, and no CP1 stay. Compare coverage/quality, anchors, spatial and temporal entropy, night/day dwell, weekday/weekend activity, cleaned-point distance, movement-duration proxy, transitions, and usable-day support.

Non-exclusive behavioral candidate flags require explicit support and never denote occupations:

- one dominant anchor / two strong anchors / multiple meaningful anchors / no stable anchor;
- stable shifted/night-like;
- mobile-work-like;
- multi-site repeated;
- home-centered low-mobility;
- weekday-mixed / weekend-heavy / travel-heavy / rotating-or-irregular / sparse-or-insufficient.

A mobile-work-like candidate requires enough usable weekday days, repeatable cleaned-point weekday mobility, high daytime activity away from the top recurring anchor, multiple recurring daytime locations, and no single dominant frozen-office candidate. It is not evidence of any profession.

### Outlier and POI feasibility

Separate CP1 data-quality boundary events from behavioral rarity. Mark behavioral rarity `rare_but_coherent` only if it repeats across days/weeks with stable locations, temporal structure, or motifs. Otherwise retain `needs_manual_review` or `insufficient_evidence`.

POI remains feasibility only: recurrence, unique visit days, dwell share, weekday/weekend profile, time profile, recency, and regularity. No network/OSM enrichment, semantic category, favorite/hobby, or recommender is built.

## Private outputs and report privacy

Private local files under `artifacts/03a/` include the requested stay cache, feature/audit/outlier/archetype/case CSVs, summary JSON, and figures. User-level outputs are never committed. They exclude latitude/longitude but remain private because behavioral profiles are sensitive.

The report uses deterministic aliases `Case A`, `Case B`, etc., never raw GeoLife `user_id`. The private `case_studies.csv` retains the alias-to-user mapping. All visuals use `L0`, `L1`, etc. and aggregate/non-identifying values only.

`reports/03a_user_behavior_deep_dive.md` contains: executive summary; coverage; heterogeneity; schedules; mobility; abstentions; shifted candidates; mobile-work-like candidates; outlier reinterpretation; POI feasibility; cases; baseline gaps; open questions; and next experiments. It explicitly answers Q1–Q10. Each claim names a measured table/figure and no conclusion is framed as accuracy.

## Verification

The runner asserts:

- 5,821 stays and 136 users with a stay; 182-user release universe;
- frozen comparator parity: 27 HOME and 16 OFFICE emissions;
- mutually exclusive/reproducible reason assignment per label for all 182 users;
- no raw latitude/longitude in private CSV exports intended for analysis summaries;
- deterministic 200 m location labels, motifs, case aliases, and aggregate summary on rerun;
- 100/200/300 m sensitivity completeness for specified primary conclusions;
- all-days versus usable-day coverage in schedule/motif outputs;
- report consistency with Q1–Q10 and no accuracy/ground-truth language.

## Non-goals and next decision

This EDA does not freeze a schedule window, clustering threshold, timezone contract, production threshold, or implementation. It produces ranked evidence and next experiments for mentor review before any Home/Work/POI redesign.
