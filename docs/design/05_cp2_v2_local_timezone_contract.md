# CP2 v2 production contract — per-stay local timezone

## Status

Migration candidate. The final Notebook-03 timezone contract has already been audited on the frozen CP1 stay inventory. This document defines the production refreeze target.

Do not merge the production migration until the full 5,821-stay migration notebook passes independent reference parity and HTTP parity.

## Frozen CP1 input

CP2 v2 reuses CP1 unchanged:

- 5,821 stay events;
- 136 users with at least one stay;
- UTC-aware arrival/departure timestamps;
- WGS84 latitude/longitude.

No raw trajectory rescan is required for the migration audit.

## Semantic-time contract

For each stay independently:

```text
(latitude, longitude)
→ timezonefinder
→ IANA timezone_id
→ ZoneInfo(timezone_id)
→ local wall-clock arrival/departure
```

Rules:

- timezone is resolved from the stay coordinate, not from user identity;
- no Beijing radius is used for eligibility;
- no China-only or Asia/Shanghai user filter is used;
- travel stays remain in semantic analysis if their timezone resolves;
- unresolved stays are excluded from semantic scoring but remain auditable;
- the API abstention for a fully unresolved request is `unresolved_timezone`.

The production local behavioral timestamps are timezone-naive wall-clock values after conversion. The IANA timezone identifier is retained separately in `timezone_id`. This matches the final Notebook-03 candidate.

## Spatial recurrence contract

The recurring-location representation remains:

- per-user clustering;
- complete linkage;
- maximum cluster diameter 200 m;
- Haversine distance.

DBSCAN remains a benchmark option only.

The production namespace after successful migration is:

```text
production_complete_link_200m_local_timezone_v2
```

Downstream artifacts must not join this namespace to legacy v1 `location_id` values without an explicit mapping/rebuild.

## Behavioral evidence contract

HOME:

- local-time window 21:00–06:00;
- minimum 3 relevant dates;
- minimum dwell share 0.50;
- minimum top-two margin 0.20.

OFFICE:

- local weekday window 09:00–17:00;
- minimum 3 relevant dates;
- minimum dwell share 0.30;
- minimum top-two margin 0.10.

Relevant-date overlap threshold remains 600 s.

Evidence strength remains:

```text
(dwell_share + top_two_margin + min(relevant_dates / 5, 1)) / 3
```

It is a heuristic evidence index, not a calibrated probability.

## Migration parity

The migration runner compares production v2 to an independent reconstruction of the audited Notebook-03 candidate.

Required technical gates:

1. frozen CP1 input is exactly 5,821 stays / 136 stay-bearing users;
2. all 5,821 stays resolve to an IANA timezone, as measured in the prior notebook audit;
3. production timezone IDs match the independent reference exactly;
4. production local arrival/departure wall-clock values match exactly;
5. complete-link cluster signatures match;
6. emitted HOME/OFFICE evidence signatures match;
7. the internal stay-event API matches direct production inference for all 136 users;
8. API responses report `model_contract = cp2-v2`.

The old 27 HOME / 16 OFFICE result is not a parity target. It is a historical v1 comparator. Any v2 count delta is measured and reviewed rather than forced away.

## Geography

CP2 v2 does not define a geographic product scope.

If a future product requires Beijing-only, China-only, or another regional cohort, that must be a separate explicit geography contract. Timezone assignment must not be reused as a geography proxy.

## Downstream consequence

After successful refreeze:

- old CP2-v1 semantic-location IDs are stale;
- stages that depend on production HOME/secondary location IDs must be rebuilt in the v2 namespace;
- CP1 stays remain valid;
- exploratory all-timezone analyses that already use per-stay local timezone can be reused where their schema does not depend on legacy production IDs;
- external-source acquisition audits such as BCL source provenance remain valid independently of the semantic namespace.
