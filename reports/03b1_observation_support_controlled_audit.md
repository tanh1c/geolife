# 03b.1 Observation-support-controlled audit

## Status

Research-only follow-up to 03b. Frozen Home/Office production semantics remain unchanged.

## Question

03b found a robust 23-user Group A cohort, but Group A had denser observation support than matched Group B.

03b.1 asks whether A/B differences persist after forcing each matched pair to contribute comparable observation exposure.

## Verification

The Modal run completed successfully:

- targeted 03b.1 tests passed;
- full repository tests passed;
- targeted Ruff passed;
- frozen parity reproduced as `23 / 23 / 23 / 0`;
- public-report privacy checks passed;
- runtime after optimization was about 3.1 minutes.

## Exposure-control design

- 23 matched A/B pairs;
- 500 bootstrap repetitions;
- temporal days downsampled within each pair and within weekday/weekend strata;
- route evidence independently downsampled on `usable_for_motif` days;
- transportation subset controlled to matched labeled hours when both sides had enough coverage.

## Mobility results

These metrics overlap with candidate construction, so they are descriptive confounding checks rather than independent semantic validation.

| metric | eligible pairs | median controlled days | median A-B difference | 95% interval | P(A-B>0) |
|---|---:|---:|---:|---:|---:|
| boundary count | 23 | 45 | 0.883 | [0.466, 1.279] | 1.000 |
| cleaned distance, km/day | 23 | 45 | 22.878 | [16.046, 27.608] | 1.000 |
| movement-duration proxy, h/day | 23 | 45 | 0.743 | [0.638, 0.826] | 1.000 |
| recurring-location count/day | 23 | 45 | 0.000 | [-0.060, 0.065] | 0.334 |
| stay count/day | 23 | 45 | -0.063 | [-0.152, 0.061] | 0.112 |

Observation support therefore does not fully explain the larger movement magnitude in Group A. However, these movement metrics partly define the candidate cohort and cannot be treated as independent validation.

## Route / transition results

These are the main support-controlled independent checks.

| metric | eligible pairs | median controlled days | median A-B difference | 95% interval | P(A-B>0) |
|---|---:|---:|---:|---:|---:|
| distinct edges/day | 22 | 8 | 0.127 | [0.000, 0.283] | 0.924 |
| edge entropy | 22 | 8 | 0.232 | [0.006, 0.455] | 0.978 |
| recurrent edges/day | 22 | 8 | 0.000 | [0.000, 0.000] | 0.000 |
| top-edge frequency | 22 | 8 | -0.010 | [-0.039, 0.003] | 0.042 |
| transitions/day | 22 | 8 | 0.136 | [0.000, 0.310] | 0.890 |

Only edge entropy has a bootstrap interval strictly above zero. The evidence therefore supports greater route diversity/complexity in Group A after exposure control, but not stronger recurrent-route structure.

## Transportation subset

Only one matched pair met the minimum labeled-exposure requirement, so transportation evidence is not population-level evidence.

For that one pair, Group A had higher distance/hour and motorized-distance share and lower active-distance share. These values are retained only as an auxiliary case-level aggregate and should not influence the cohort-level conclusion.

## Interpretation

The support-controlled result is **mixed**.

What survives exposure control:

- substantially more movement distance/day;
- longer movement-duration proxy/day;
- more quality boundaries/day;
- higher route edge entropy.

What does not show robust independent support:

- recurrent route edges;
- stay count/day;
- recurring-location count/day;
- a clearly higher transition/day interval;
- a population-level transportation-mode difference.

## Research decision

The 23-user set remains useful as a **robust descriptive mobility-complexity cohort**.

Current evidence does **not** justify calling it a distributed/mobile-work class or using it to change Home/Office semantics.

The working interpretation is therefore:

```text
robust high-mobility / route-diversity cohort
!=
validated mobile-work semantic regime
```

## Recommended next step

Close the current mobile-work hypothesis audit unless new independent semantic evidence becomes available.

The next engineering/research follow-up can proceed separately, including the mentor-requested DBSCAN MinPts sensitivity study.