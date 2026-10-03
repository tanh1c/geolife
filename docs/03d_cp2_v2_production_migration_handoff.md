# CP2 v2 production migration — Modal handoff

## Goal

Validate and refreeze the already-reviewed Notebook-03 all-timezone contract into production `src/geolife/model/home_office.py`.

This is a migration/parity run, not a new timezone experiment.

## Input

The runner searches the existing Modal Volume for:

```text
stays_baseline_v1.pkl
```

Preferred locations include:

```text
/mnt/geolife-data/cache/cp2_home_office/stays_baseline_v1.pkl
/mnt/geolife-data/cache/03a_user_behavior_deep_dive/stays_baseline_v1.pkl
```

Expected frozen input:

```text
5,821 stays
136 users with stays
```

No raw PLT scan is needed.

## Run

Notebook:

```text
notebooks/03d_cp2_v2_production_migration.ipynb
```

Run it top-to-bottom.

No API key is needed.

No GPU is needed.

## What it checks

### Independent semantic parity

The notebook compares production v2 with a separate reference implementation of the final Notebook-03 candidate.

Expected pass statuses:

```text
cp1_input_status             pass_frozen_cp1
timezone_resolution_status   pass_all_stays_resolved
local_time_parity_status     pass_exact_local_time_parity
cluster_parity_status        pass_cluster_signature_parity
emission_parity_status       pass_emission_evidence_parity
runner_status                ready_for_cp2_v2_review
```

### Full-release HTTP parity

Every stay-bearing user is replayed through:

```text
/v1/home-office/infer
```

Expected:

```text
136 responses
all HTTP 200
all model_contract == cp2-v2
0 direct-vs-HTTP evidence mismatches
```

### Measured v1 → v2 delta

The notebook prints a table comparing:

```text
semantic_users
semantic_locations
recurring_locations
recurring_users
HOME
OFFICE
```

The historical v1 values are shown only as reference:

```text
semantic_users       97
semantic_locations   1111
recurring_locations  486
recurring_users      73
HOME                 27
OFFICE               16
```

Do not force v2 back to these values.

## Private outputs

Saved under:

```text
/mnt/geolife-data/cache/03d_cp2_v2_production_migration/
```

including:

- `semantic_stays_cp2_v2_private.pkl`;
- `semantic_locations_cp2_v2_private.pkl`;
- `home_office_emissions_cp2_v2_private.pkl`;
- `http_parity_private.csv`;
- `migration_decision.csv`;
- `cp2_v2_manifest.json`.

The new location namespace is:

```text
production_complete_link_200m_local_timezone_v2
```

## What to send back

Send the executed notebook.

Important outputs:

- migration decision table;
- timezone-resolved stays/users;
- distinct timezone count and top timezone counts;
- local-time parity counts;
- production/reference location counts and mismatch counts;
- production/reference HOME/OFFICE counts and mismatch counts;
- v1 → v2 delta table;
- HTTP parity pass;
- final manifest summary.

## Merge gate

Do not merge the production migration merely because CI is green.

Merge only after the executed full-release notebook shows:

- independent semantic parity;
- HTTP parity;
- measured deltas are reviewed and scientifically acceptable.
