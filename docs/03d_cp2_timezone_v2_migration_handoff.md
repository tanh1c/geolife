# CP2 v2 migration handoff

## Run this next

Notebook:

```text
notebooks/03d_cp2_timezone_v2_migration.ipynb
```

Use the existing Modal Volume.

No raw GeoLife rescan is required.

The notebook searches for:

```text
stays_baseline_v1.pkl
```

and requires exactly:

```text
5,821 stays
136 stay-bearing users
```

## What it runs

### Reference parity

Production-v2 is compared against the independent notebook-03 reference for:

- per-stay timezone;
- local wall-clock timestamps;
- per-stay location ID;
- location membership;
- emitted HOME/OFFICE keys;
- evidence fields.

### API parity

All 136 users are replayed through the stay-event FastAPI endpoint.

Expected:

```text
model_contract = cp2-v2
http_direct_exact = True
```

## Required final status

```text
runner_status = ready_to_refreeze_cp2_v2
```

Do not merge/refreeze if any exact parity field is false.

## Important outputs to send back

```text
cp1_stays
cp1_users

production_semantic_stays
production_semantic_users
distinct_timezones

production_locations
production_recurring_locations
production_recurring_users

production_home_emitted
production_office_emitted
unique_emitted_users

timezone_distribution_exact
location_membership_exact
emission_keys_exact
evidence_exact

users_replayed
http_mismatch_users
model_contract_mismatch_users
http_direct_exact

runner_status
```

## Private artifacts

Written under:

```text
/mnt/geolife-data/cache/03d_cp2_timezone_v2_migration/
```

No precise coordinates or raw timestamps are committed.

## After pass

Only after the migration pass:

1. update notebook-03 narrative from candidate to production-refrozen;
2. rerun the legacy-production-dependent semantic chain beginning at Stage 05;
3. mint and propagate namespace `complete_link_200m_local_timezone_v2`;
4. realign 07c→07e;
5. reuse Stage 07f BCL source audit;
6. design BCL extraction around the new actual anchor universe rather than a Beijing-radius population cut.
