# CP2 timezone-v2 production migration

Date: 2026-10-03  
Status: CANDIDATE — implementation and migration audit prepared; full 5,821-stay refreeze run pending.

## Why this migration exists

Notebook 03 already established the final semantic-time contract:

```text
(latitude, longitude)
→ timezonefinder
→ IANA timezone_id
→ ZoneInfo(timezone_id)
→ local arrival/departure wall clock
```

The final notebook retains every stay whose timezone resolves. Asia/Shanghai concentration is descriptive only. It is not an eligibility rule.

Production `src/geolife/model/home_office.py` remained on the older CP2 v1 Beijing-radius contract, so the repository had two semantic contracts.

## Production-v2 contract

The candidate production implementation now:

- resolves every valid stay independently from WGS84 coordinate to IANA timezone;
- converts UTC arrival/departure to the same tz-naive local wall-clock representation used by notebook 03;
- drops only stays whose timezone lookup itself is unresolved;
- does not apply Beijing radius, China-only, or Asia/Shanghai concentration eligibility;
- keeps complete-link 200 m as the production recurring-location representation;
- keeps the reviewed HOME/OFFICE windows and emission gates unchanged;
- carries an explicit semantic-location namespace.

Default namespace:

```text
complete_link_200m_local_timezone_v2
```

The namespace must travel with semantic-location and emitted-label artifacts so integer `location_id` values cannot be silently joined across CP2 contracts.

## Frozen scoring controls retained

HOME:

```text
21:00–06:00 local
>=3 supported dates
share >=0.50
margin >=0.20
```

OFFICE:

```text
Mon–Fri 09:00–17:00 local
>=3 supported dates
share >=0.30
margin >=0.10
```

Evidence strength remains:

```text
support_factor = min(relevant_dates / 5, 1)
evidence_strength =
  (relevant_dwell_share + share_margin + support_factor) / 3
```

It is not a calibrated probability.

## Independent migration reference

`analysis/03d_cp2_timezone_v2_migration.py` contains a deliberately independent reference implementation transcribed from the finalized notebook-03 cells.

It does not call private production helpers.

The migration notebook compares:

1. exact per-stay timezone ID;
2. exact per-stay local arrival/departure wall time;
3. exact per-stay complete-link `location_id`;
4. aggregate semantic-location membership;
5. exact emitted `(user_id, label, location_id)`;
6. exact relevant dwell share, margin, dates, and evidence strength.

This is a one-time migration comparator, not a second production implementation.

## Full-release refreeze gate

Required input:

```text
stays_baseline_v1.pkl
5,821 stays
136 users with stays
```

Hard gate:

```text
cp1_stay_count_status
  = pass_5821_frozen_cp1

timezone_resolution_status
  = pass_reference_timezone_parity

semantic_location_status
  = pass_reference_location_parity

emission_key_status
  = pass_reference_emission_key_parity

evidence_status
  = pass_reference_evidence_parity

runner_status
  = ready_to_refreeze_cp2_v2
```

## HTTP parity

The same migration notebook replays all 136 stay-bearing users through:

```text
POST /v1/home-office/infer
```

and compares the emitted response to direct production inference.

The API model contract is versioned as:

```text
cp2-v2
```

The old `out_of_scope_geography` abstention is removed from the v2 serving semantics. A fully unresolved semantic stay table is represented as `unresolved_timezone`.

## Downstream invalidation

Once CP2 v2 is refrozen, any artifact whose semantic-location IDs were created with legacy production `build_semantic_locations()` is stale.

Expected rebuild chain:

```text
05
→ 05b
→ 05c
→ 07b
→ 07c
→ 07d
→ 07e
```

03a/06 all-resolved behavior analyses are already timezone-aware and are not automatically invalidated, but any comparator fields that call production CP2 must be recomputed if reused.

## Reusable stages

Do not rerun:

- CP1 cleaning/stay detection;
- frozen 5,821-stay materialization;
- Stage 07f BCL source acquisition / licence / FileGDB / CRS audit.

## Semantic boundary

This migration changes time/geography eligibility semantics only.

It does not claim:

- semantic accuracy;
- occupation;
- workplace truth;
- POI category truth.

HOME/OFFICE remain heuristic behavioral labels with abstention.
