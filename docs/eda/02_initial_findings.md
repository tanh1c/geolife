# Initial measured EDA findings

Date: 2026-09-16

These findings come from the official GeoLife 1.3 files mounted in Modal, not from documentation counts alone.

## Dataset inventory

- Users: 182
- Trajectory files: 18,670
- User folders containing `labels.txt`: 69

This confirms the v1.3 table count of 18,670 trajectories. It also exposes a discrepancy with the guide text that mentions 73 labeled users; the mounted release contains 69 user folders with `labels.txt`. The reason for that discrepancy is not yet established.

## User-level trajectory imbalance

Trajectory count per user is strongly long-tailed:

- mean: 102.58
- standard deviation: 250.06
- min: 1
- p25: 8
- median: 27.5
- p75: 89.75
- p90: 214.7
- p95: 394.8
- p99: 1,039.85
- max: 2,153

Concentration of all 18,670 trajectories:

- top 1 user: 11.5%
- top 5 users: 34.5%
- top 10 users: 47.4%
- top 20 users: 63.3%
- top 50 users: 84.0%

Implication: trajectory-weighted evaluation can be dominated by a small set of heavy users. Later evaluation should report per-user/macro views in addition to observation-level/micro metrics where appropriate.

## Labeled-user subset

Users without `labels.txt`:
- 113 users
- 7,764 trajectories
- mean trajectories/user: 68.71
- median: 23
- range: 1 to 757

Users with `labels.txt`:
- 69 users
- 10,906 trajectories
- mean trajectories/user: 158.06
- median: 34
- range: 2 to 2,153

The labeled-user subset is not a random-looking cross-section by trajectory volume: 37.9% of users account for 58.4% of trajectories. Presence of `labels.txt` does not imply every trajectory or point is labeled; interval-level coverage still needs to be measured.

## Raw PLT spot-check

First inspected trajectory: user `000`.

- rows: 908
- start: 2008-10-23 02:53:04+00:00
- end: 2008-10-23 11:11:12+00:00
- null timestamps: 0
- `timestamp` parsed as timezone-aware UTC
- altitude sentinel `-777` did not occur in this trajectory
- observed altitude range in this one trajectory: -407 to 7,584 feet

The altitude range is only a spot-check signal; it is not enough to label either extreme as invalid. Dataset-wide altitude and movement diagnostics are still required.

## Next EDA step

Run memory-bounded trajectory-level summarization over all 18,670 files to measure:

- point counts;
- trajectory duration and approximate distance;
- median/p95 sampling intervals;
- duplicate/non-monotonic timestamps;
- coordinate validity;
- max/p99 segment speed;
- altitude missingness.

Do not choose speed-cleaning or stay-point thresholds until these distributions are inspected.