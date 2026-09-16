# GeoLife source-profile observations (before executing raw-data EDA)

This note records what the supplied **GeoLife User Guide v1.3 (2012-08-01)** says. These are source-reported facts, **not notebook measurements**. The notebook must verify what can be verified from the actual files.

## Scale and an important documentation inconsistency

The guide reports 182 users, collection from April 2007 to August 2012, total distance about 1.29M km, and total duration about 50k hours.

However, the guide is internally inconsistent about trajectory count:

- the narrative on page 1 says 17,621 trajectories;
- the version-comparison table on page 2 says v1.3 contains **18,670 trajectories** and **24,876,978 points**, while 17,621 was the v1.2 count.

Therefore, CP1 should count files and points directly instead of copying the narrative number.

## Sampling behavior

The guide states that 91.5% of trajectories are densely represented, for example every 1–5 seconds or every 5–10 meters per point. Sampling rate still varies across GPS loggers and phones, so stay-point and speed analysis must inspect inter-point gaps rather than assume one fixed cadence.

## Trajectory distance distribution (guide Figure 2)

- 36%: < 5 km
- 36%: 5–20 km
- 23%: 20–100 km
- 5%: >= 100 km

Implication: trajectory distance is strongly heterogeneous. Means alone will hide the tail; report quantiles and clipped/log-aware plots.

## Trajectory duration distribution (guide Figure 3)

- 58%: < 1 hour
- 26%: 1–6 hours
- 11%: 6–12 hours
- 5%: >= 12 hours

Implication: most trajectories are short, but a meaningful long-duration tail exists. Stay-point extraction and gap handling must avoid treating all files as comparable sessions.

## User observation-period imbalance (guide Figure 4)

- 24% of users: < 1 week
- 34%: 1 week–1 month
- 40%: 1 month–1 year
- 2%: >= 1 year

This is central to Home/Office inference. A baseline should not assume every user has enough repeated history. We likely need a minimum-history policy and must report coverage after applying it.

## Trajectory-count imbalance by user (guide Figure 5)

- 28% of users: < 10 trajectories
- 34%: 10–50
- 15%: 50–100
- 23%: >= 100

Implication: evaluation should be user-aware. A point- or trajectory-weighted global metric can be dominated by heavy users.

## Transportation labels

The guide states that 73 users have transportation-mode labels. Modes include walk, bike, bus, car/taxi, train, airplane, and others; the label set is only partial coverage of the full dataset.

These labels are useful for movement analysis, but they are **not Home/Office labels**. They should not be presented as ground truth for the target task.

## Geography and time

The guide states that data is distributed across 30+ cities/countries, with the majority in Beijing. PLT timestamps are documented as GMT/UTC.

This creates an important modeling issue: Home/Office rules based on 'night' or 'office hours' need a timezone policy. Applying Beijing local time to every trajectory would silently mis-handle non-Beijing data.

## Privacy / publication

Raw mobility traces can reveal routines such as home and workplace. The repository therefore keeps raw data and generated user-level artifacts out of Git by default. Any later H3/geohash coarsening should be evaluated as a privacy/utility trade-off, not treated as automatic anonymization.

## Questions the raw-data notebook must answer next

1. Which trajectory count is actually present in the files?
2. What is the actual point count?
3. How severe are duplicate/non-monotonic timestamps and invalid coordinates?
4. What are the empirical sampling-interval quantiles?
5. How much altitude is missing (`-777`)?
6. Which speed extremes are plausible transport versus GPS jumps?
7. How concentrated is usable history among users?
8. What scope/timezone policy is defensible for the first Home/Office heuristic?
9. What candidate stay-point thresholds are supported by the observed data rather than copied from a paper/tutorial?
