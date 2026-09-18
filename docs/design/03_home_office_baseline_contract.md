# CP2 Home / Office / POI baseline contract

Date: 2026-09-18  
Status: DRAFT — full-release CP2 stay materialization reproduced CP1 exactly; recurring-location and timezone gates are under review. No Home/Office heuristic is frozen yet.

## Goal

Define a conservative user-level baseline for inferring recurring **Home**, **Office**, and **Other/POI** locations from the frozen CP1 stay-point pipeline.

This stage begins only after CP1 because semantic location inference must consume stable stay events rather than raw GPS points.

The baseline is intentionally heuristic and interpretable. GeoLife does not provide direct Home/Office ground truth, so evaluation is based on coverage, recurrence, temporal plausibility, and sensitivity rather than supervised accuracy.

## Frozen upstream input

CP2 consumes stays produced with the merged CP1 engineering baseline:

- same-second safe-collapse radius: `10 m`;
- temporal continuity gap: `300 s`;
- hard-speed guard: `1200 km/h`;
- stay distance threshold: `200 m`;
- minimum dwell: `1200 s`.

Same-second groups above 10 m remain continuity boundaries under the diagnostic reason `same_second_spatial_ambiguity`. The 10 m value is a safe-to-collapse threshold, not a valid-vs-corrupt threshold.

CP2 must not bypass or reimplement CP1 cleaning/stay detection logic in notebook code. The notebook imports production APIs from `src/`.

## Required stay-event schema

The first CP2 materialization should persist at least:

- `user_id`;
- `source_file`;
- `arrival_time_utc`;
- `departure_time_utc`;
- `duration_s`;
- `latitude`;
- `longitude`.

Derived semantic-time columns must be added only after an explicit timezone policy is selected.

## Stage A — materialize the frozen stay baseline

Run the frozen CP1 pipeline over the full release and persist user-level stay events in a reusable cache.

The materialization must:

- be deterministic;
- print progress and elapsed time;
- reuse the cache on reruns;
- preserve source-file lineage;
- never infer Home/Office during cleaning.

The CP1 full-release summary reported 5,821 stays. The CP2 materialized stay table should reconcile to that total before semantic inference begins.

## First full-release CP2 materialization

The first CP2 run reproduced the frozen CP1 total exactly:

- stays: `5,821`;
- users with at least one stay: `136`.

History sufficiency from the measured stay table:

- users with >=2 stays: `120`;
- users with >=5 stays: `99`;
- users with >=10 stays: `81`;
- users with stays on >=2 distinct UTC dates: `114`;
- users with stays on >=5 distinct UTC dates: `83`;
- users with stays on >=10 distinct UTC dates: `62`.

This confirms that Home/Office inference must support abstention: 46/182 release users have no detected stay at all under the frozen CP1 baseline, and many users with stays still have limited repeated-history support.

## Stage B — user-level coverage audit

Before scoring Home/Office, measure:

- users with at least one stay;
- stays per user;
- distinct active dates per user;
- observation span per user;
- stay-duration distribution;
- recurring-location evidence.

Users with insufficient history must be allowed to produce no Home/Office label rather than forcing a guess.

## Stage C — recurring-location representation

The first notebook compares two representations:

1. individual stay representatives;
2. user-scoped spatial clustering of stay representatives.

A candidate spatial clustering baseline may use Haversine DBSCAN with an interpretable radius near the already reviewed 200 m recurrence scale, but the clustering configuration is **not frozen by this document**.

Any clustering review should inspect:

- number of locations per user;
- stays per location;
- active dates per location;
- within-cluster spatial spread/diameter;
- sensitivity to the clustering radius;
- chaining/pathological clusters.

The semantic label must be assigned to a recurring location, not to a raw GPS point.

## First recurring-location audit

A candidate per-user Haversine DBSCAN run with `eps=200 m` and `min_samples=1` produced:

- candidate locations: `1,885`;
- recurring locations with >=2 stays: `635`;
- users with at least one recurring location: `104`.

The largest observed distance from a cluster's median representative to a member stay was about `526.7 m`, which is substantially larger than the 200 m DBSCAN epsilon. This is expected under density-connectivity chaining and demonstrates why `eps=200 m` must not be interpreted as a hard cluster-radius guarantee.

Therefore the recurring-location representation remains a review gate. CP2 should compare alternatives or add a compactness constraint before freezing production clustering semantics.

## Stage D — timezone policy gate

Home/Office heuristics depend on local behavioral time. GeoLife PLT timestamps are UTC/GMT, while the release contains trajectories outside Beijing. The first CP2 stay materialization confirms that the 5,821 stays are strongly Beijing-centered but include substantial geographic outliers (stay longitude spans approximately -149.88 to 135.77 degrees).

Therefore:

> Do not blindly apply UTC+8 to every stay.

Before computing night/daytime features, the notebook must audit spatial coverage of the materialized stays and document the local-time policy.

Candidate v1 policy under review:

- define a Beijing-focused cohort using sensitivity over distance-to-Beijing and per-user stay/dwell share;
- current audit values are 50/100/200 km radii and a candidate 100 km / 80% stay-share / 80% dwell-share rule;
- for accepted users, only stays inside the selected Beijing radius enter `Asia/Shanghai` semantic-time processing;
- out-of-radius travel stays remain excluded rather than being silently converted to Beijing time;
- a broader cohort is deferred unless a reliable per-location timezone mapping is added.

No production heuristic may silently infer a timezone from longitude alone without a reviewed contract.

See `docs/eda/16_cp2_timezone_geography_audit.md`.

## Stage E — candidate semantic features

After the timezone gate is resolved, candidate location-level features include:

### Home-oriented evidence

- overnight dwell;
- late-evening / early-morning recurrence;
- number of distinct nights;
- total night dwell;
- fraction of a user's night dwell captured by the location.

### Office-oriented evidence

- weekday daytime dwell;
- recurrence across distinct weekdays;
- total weekday work-hour dwell;
- fraction of a user's weekday daytime dwell captured by the location.

Candidate time windows such as night and 09:00–17:00 are **parameters for sensitivity review**, not universal truths.

## Stage F — candidate labeling semantics

A first interpretable baseline should allow:

- zero or one `HOME` candidate per user;
- zero or one `OFFICE` candidate per user;
- remaining recurring locations as `OTHER` / `POI`;
- abstention when evidence is weak.

Home and Office may not be forced to different locations without evidence. If the same location dominates both score families, the system must expose the ambiguity rather than inventing a second location.

## Confidence

Confidence is heuristic evidence strength, not a calibrated probability.

Candidate components include:

- recurrence count;
- distinct active days/nights;
- share of relevant dwell captured by the selected location;
- margin over the second-ranked candidate;
- observation-span sufficiency.

The first contract must define the exact confidence formula before implementation is promoted to production.

## Validation without Home/Office ground truth

Because direct semantic ground truth is unavailable, CP2 validation should report:

- user coverage and abstention rate;
- number of users with Home / Office / both;
- recurrence and distinct-day support;
- distance between Home and Office candidates;
- score margins;
- sensitivity to time windows and spatial clustering;
- examples of ambiguous users;
- stability under reasonable parameter perturbations.

These metrics assess plausibility and robustness. They must not be reported as accuracy.

## Privacy

Home and Office are highly sensitive derived locations.

Repository outputs must avoid committing user-level precise coordinates or raw inferred Home/Office tables. Only aggregate summaries and carefully selected non-identifying diagnostics may be committed.

## Notebook / production separation

`notebooks/03_home_office_baseline.ipynb` is the CP2 exploration/validation surface.

Production logic will live under `src/geolife/model/` only after:

1. timezone policy is reviewed;
2. recurring-location representation is reviewed;
3. Home/Office scoring semantics are written as acceptance tests.

## Initial review gates

Before writing production Home/Office inference:

1. full-release stay materialization reconciles to the CP1 total;
2. user-level history sufficiency is quantified;
3. timezone policy is explicit;
4. recurring-location representation is reviewed;
5. candidate time windows and abstention behavior are documented;
6. no precise user-level inferred-location artifact is committed.
