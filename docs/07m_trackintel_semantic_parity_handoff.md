# Stage 07m handoff — Trackintel semantic-only parity

## Run

Run only:

```text
notebooks/07m_trackintel_semantic_parity.ipynb
```

The notebook uses the same Modal Volume convention as the existing project:

```text
/mnt/geolife-data
```

No upstream notebook needs to be rerun if the frozen CP1 cache is already
present.

## Runtime bootstrap

The notebook:

1. clones/pulls `tanh1c/geolife`;
2. installs the repository editable environment;
3. installs/pins `trackintel==1.4.2`;
4. loads the frozen `stays_baseline_v1.pkl` from the Volume;
5. rebuilds the frozen CP2-v2 semantic-location namespace;
6. runs Trackintel FREQ and OSNA with `pre_filter=False`.

## Expected hard gates before Trackintel

You should see production parity equivalent to:

```text
cp1_stays                 5821
stay_users                 136
semantic_stays            5821
semantic_locations        2015
recurring_locations        716
recurring_location_users   104
HOME                        27
OFFICE                      16
```

and:

```text
frozen CP2-v2 parity: PASS
Trackintel staypoint adapter: PASS
Trackintel semantic methods: PASS
```

The FREQ/OSNA candidate counts are intentionally not predeclared; they are the
measured comparator result.

## Main tables to send back

Please send the executed notebook after these tables are visible:

```text
AGREEMENT SUMMARY
STATUS DISTRIBUTION
FROZEN OFFICE-16 REFERENCE
FROZEN HOME-27 REFERENCE
TRACKINTEL WORK × STAGE-07j NEAR-MISS
Trackintel FREQ × OSNA internal agreement
```

The near-miss table appears when this existing file is present:

```text
/mnt/geolife-data/cache/cp2_v2/07j_near_miss_office_audit/near_miss_office_audit_private.pkl
```

If it is missing, the core 07m comparison still runs and that optional view is
skipped.

## Output cache

```text
/mnt/geolife-data/cache/cp2_v2/07m_trackintel_semantic_parity/
```

User-level candidate identity is private and remains on the Volume.

## Important interpretation rule

Do not interpret Trackintel agreement as ground-truth accuracy.

Do not relax HOME/OFFICE thresholds from this stage.

In particular, if Trackintel labels some Stage-07j near-miss candidate as WORK,
that only demonstrates that an independent simpler heuristic chooses the same
location. It does not override Stage-07j/07l robustness evidence.
