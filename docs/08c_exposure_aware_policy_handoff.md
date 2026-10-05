# Stage 08c handoff — Exposure-aware policy experiment

## Run only

```text
notebooks/08c_exposure_aware_policy.ipynb
```

No raw trajectory scan is required.

## Required measured caches

```text
08b_exposure_bias_audit/
    user_exposure_profiles_private.pkl
    gate_diagnostics_private.pkl

08a_home_coverage_expansion/
    home_expansion_evidence_private.pkl

07j_near_miss_office_audit/
    near_miss_office_audit_private.pkl

05_home_office_reliability_validation/
    assignments_private.pkl
```

The notebook also loads the frozen 5,821-stay cache to reproduce production
HOME 27 / OFFICE 16.

## Expected input gate

```text
production HOME = 27
production OFFICE = 16
HOME_PROBABLE_08a = 5
OFFICE_near_miss_07j = 9

Stage-08c input gate: PASS
```

## Main outputs to send back

```text
SPARSE HOME support-aware candidates
DENSE HOME concentration-aware candidates
DENSE OFFICE near-miss concentration-aware candidates

EXPOSURE-AWARE CANDIDATE FUNNEL
DENSE OFFICE ROBUSTNESS
POLICY COVERAGE COMPARISON
overlap diagnostics
```

## Key questions

1. Does the strict 2-of-2 SPARSE HOME rule recover any candidates?
2. How many of the five HOME_PROBABLE cases also pass relative dominance >= .625?
3. How many of the nine OFFICE near misses pass relative dominance >= .60?
4. How many OFFICE cases remain after dropout + corroboration filtering?
5. What tiered HOME/OFFICE coverage results without changing production?

## Output cache

```text
/mnt/geolife-data/cache/cp2_v2/08c_exposure_aware_policy/
```

## Important boundary

Do not update production thresholds from the candidate count alone.

Stage 08c is designed to compare candidate policies. A positive branch should
remain tiered until measured robustness is reviewed.
