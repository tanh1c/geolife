# Stage 08a — HOME coverage expansion / confidence tiers

## Purpose

Stage 08a begins a new coverage-expansion track after Stage 07p closed the
validated CP2-v2 production policy.

The frozen production core remains:

~~~text
HOME = 27
OFFICE = 16
~~~

Stage 08a does not lower the HOME gate and does not search the entire non-HOME
population indiscriminately.

Stage 05b already reduced the candidate space to exactly two non-production
HOME locations that were unique consensus winners at HIGH/MEDIUM internal
evidence tier.

Therefore Stage 08a is a targeted audit of those two candidates using later
independent evidence.

## Candidate provenance

Stage 05b measured:

- 67 unique HOME vote winners;
- HIGH: 21;
- MEDIUM: 4;
- UNCERTAIN: 42.

Production relationship:

- HIGH: 20 baseline-emitted + 1 fixed candidate not emitted;
- MEDIUM: 3 baseline-emitted + 1 fixed candidate not emitted.

The historical measured Stage-05b snapshot recorded two non-production HIGH/MEDIUM HOME candidates. The current cache is treated as authoritative for Stage 08a execution; any difference from the historical count is reported as lineage drift rather than causing a hard failure.

## Evidence added in Stage 08a

### Internal evidence — Stage 05b

The candidate must already be:

- a unique HOME vote winner;
- HIGH or MEDIUM;
- selected by at least two internal HOME methods;
- supported by at least two of:
  - split-half confirmation;
  - held-out top-1;
  - 30% dropout robustness.

### Exact same-namespace external evidence

Three external semantic families are used for the primary expansion tier:

1. Trackintel OSNA from Stage 07m;
2. scikit-mobility-style nighttime HOME from Stage 07o;
3. SCITEPRESS-style work/rest HOME from Stage 07o.

All three operate on the frozen production location namespace in their
semantic-only comparator form, so exact location-id identity is meaningful.

Trackintel FREQ is reported separately as auxiliary evidence rather than counted
toward the main exact-family threshold.

### Different-namespace spatial evidence

Two sources are auxiliary:

- Stage-07o geohash HOME;
- Stage-07n Trackintel end-to-end OSNA HOME under DBSCAN-100 / DBSCAN-200.

Because these methods define different spatial representations, Stage 08a uses
distance to the candidate center and reports support within 200 m.

Spatial support alone cannot create a HOME_PROBABLE tier.

## Tier contract

### HOME_PROBABLE

All conditions must hold:

~~~text
Stage-05b tier in {HIGH, MEDIUM}
unique vote winner
method_votes >= 2
reliability_axes >= 2

external_exact_family_count >= 2
from:
    Trackintel OSNA
    scikit HOME
    SCITEPRESS HOME

candidate does not equal production OFFICE location
~~~

### HOME_PLAUSIBLE

The same internal evidence floor and no OFFICE collision, but fewer than two
primary exact external confirmations.

At least one external support signal is still required:

- >=1 primary exact family;
- Trackintel FREQ exact;
- geohash within 200 m;
- Trackintel end-to-end HOME within 200 m.

### ABSTAIN

Anything weaker or semantically conflicting.

## Why no weighted score

The expansion set is intentionally small and already prefiltered by Stage 05b.

A weighted score would introduce arbitrary calibration without ground truth and
would obscure which independent evidence families actually support a candidate.

Stage 08a therefore keeps the evidence columns explicit.

## OFFICE collision gate

If a candidate HOME location is exactly the user's frozen production OFFICE
location, Stage 08a forces ABSTAIN regardless of external HOME agreement.

This is a conservative semantic-conflict rule, not a claim that co-located
HOME/OFFICE is impossible.

## Outputs

Private:

- \`home_expansion_audit_map_private.pkl\`;
- \`home_expansion_evidence_private.pkl\`.

Aggregate:

- \`frozen_and_candidate_gate.csv\`;
- \`external_cache_inventory.csv\`;
- \`home_expansion_support_summary.csv\`;
- \`home_tiered_coverage_summary.csv\`;
- \`home_expansion_policy.csv\`.

Cache root:

~~~text
/mnt/geolife-data/cache/cp2_v2/08a_home_coverage_expansion/
~~~

## Policy boundary

Stage 08a may increase downstream semantic coverage through separate tiers:

~~~text
HOME_HIGH_CONFIDENCE_CORE = 27
HOME_PROBABLE_NEW         = measured
HOME_PLAUSIBLE_NEW        = measured
~~~

It does not silently change production HOME.

The validated production contract remains HOME 27 / OFFICE 16 unless a later
explicit policy stage decides otherwise.


## Measured result

Stage 08a executed successfully on `main` at `c1da357`.

No traceback occurred and all Stage-08a outputs were saved.

### Candidate-lineage gate

Frozen production reproduced:

- CP1 stays: 5,821;
- HOME: 27;
- OFFICE: 16.

The Stage-05b candidate count differs from the historical snapshot:

| metric | count |
| --- | ---: |
| historical HIGH/MEDIUM non-production candidates | 2 |
| current cache HIGH/MEDIUM non-production candidates | 5 |

This drift is recorded explicitly. Stage 08a audits the five candidates present
in the current cache.

### Tier result

All five candidates satisfy the predeclared HOME_PROBABLE contract:

| tier | count |
| --- | ---: |
| HOME_HIGH_CONFIDENCE_CORE | 27 |
| HOME_PROBABLE_NEW | 5 |
| HOME_PLAUSIBLE_NEW | 0 |
| HOME_EXPANSION_ABSTAIN | 0 |
| high + probable coverage | 32 |

Production remains unchanged at HOME 27 / OFFICE 16.

### Aggregate external support

Across the five HOME_PROBABLE candidates:

| signal | supported |
| --- | ---: |
| Trackintel OSNA exact | 4/5 |
| Trackintel FREQ exact | 4/5 |
| scikit-style HOME exact | 4/5 |
| SCITEPRESS-style HOME exact | 5/5 |
| geohash within 200 m | 3/5 |
| Trackintel e2e DBSCAN-100 within 200 m | 4/5 |
| Trackintel e2e DBSCAN-200 within 200 m | 4/5 |
| production-OFFICE collision | 0/5 |

Three candidates receive all three primary exact external confirmations.
Two receive exactly two, which is the minimum required by the locked
HOME_PROBABLE rule.

The weakest HOME_PROBABLE candidate receives scikit-style and SCITEPRESS-style
exact support but no Trackintel OSNA/FREQ, geohash, or end-to-end Trackintel
spatial support. It is retained because the rule was specified before seeing the
candidate-level results.

### Internal support

Candidate-level descriptive support:

- internal tiers: 2 HIGH, 3 MEDIUM;
- method votes: median 2;
- reliability axes: median 2;
- dropout retention is high across the set;
- no candidate collides with production OFFICE.

Observed location support spans:

- stay count: 9 to 85;
- total dwell: about 11.6 to 55.1 hours;
- active local dates: 6 to 21.

These descriptive features are not used as an additional post-hoc promotion
score.

### Interpretation

Stage 08a provides the first validated coverage expansion beyond the frozen
HOME-27 core.

The appropriate downstream representation is:

```text
HOME_HIGH_CONFIDENCE = 27
HOME_PROBABLE        = 5
usable tiered HOME   = 32
```

This is not equivalent to changing production HOME from 27 to 32.

The 27-case core retains its validated production semantics; the five additions
carry a distinct HOME_PROBABLE tier.

### Decision

Stage 08a supports exposing the five candidates downstream as HOME_PROBABLE.

Do not silently merge them into the HOME_HIGH_CONFIDENCE core.

A future export/policy layer should preserve the tier field so analyses can
choose either:

- strict HOME coverage = 27;
- tiered HOME coverage = 32.
