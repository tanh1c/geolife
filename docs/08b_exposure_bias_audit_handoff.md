# Stage 08b handoff — Observation-density / exposure-bias audit

## Run only

~~~text
notebooks/08b_exposure_bias_audit.ipynb
~~~

No raw GeoLife scan is required.

The notebook uses:

~~~text
/mnt/geolife-data
~~~

## Required caches

Frozen stays:

~~~text
stays_baseline_v1.pkl
~~~

Stage 05:

~~~text
cache/cp2_v2/05_home_office_reliability_validation/assignments_private.pkl
~~~

Stage 08a:

~~~text
cache/cp2_v2/08a_home_coverage_expansion/home_expansion_evidence_private.pkl
~~~

Stage 07j:

~~~text
cache/cp2_v2/07j_near_miss_office_audit/near_miss_office_audit_private.pkl
~~~

## Expected input gate

~~~text
CP1 stays        = 5821
stay users       = 136
locations        = 2015
production HOME  = 27
production OFFICE = 16
HOME_PROBABLE    = 5
OFFICE near miss = 9

Stage-08b input gate: PASS
~~~

## Main tables to send back

After Run All, send the executed notebook containing:

~~~text
HOME EXPOSURE REGIME COUNTS
OFFICE EXPOSURE REGIME COUNTS

GATE STATUS — HOME
GATE STATUS — OFFICE

gate_by_exposure_regime

exposure_limited_summary

exposure_association_summary

METHOD COVERAGE BY EXPOSURE REGIME

FIXED VS ALTERNATE METHOD AGREEMENT BY EXPOSURE REGIME

home_expansion_by_exposure_regime

office_near_miss_by_exposure_regime

bias_hypothesis_snapshot
~~~

## What to look for

Evidence supporting an exposure-bias hypothesis would include some combination
of:

- much lower SPARSE emission rate than DENSE;
- strong positive opportunity-date vs emission association;
- many min_dates-blocked users whose raw top candidate covers nearly all
  observed opportunity dates;
- HOME_PROBABLE candidates concentrated outside DENSE;
- alternate semantic methods retaining coverage in sparse users when the fixed
  candidate is absent.

Evidence against the hypothesis would include:

- similar emission rates across exposure regimes;
- few exposure-limited min-date failures;
- weak exposure-emission association;
- expanded/near-miss candidates concentrated in dense users for reasons unrelated
  to support exposure.

## Output cache

~~~text
/mnt/geolife-data/cache/cp2_v2/08b_exposure_bias_audit/
~~~

## Important boundary

Do not change HOME/OFFICE thresholds from Stage 08b alone.

Stage 08b is an audit. If an adaptive policy is justified, define and validate it
in a separate next stage against the frozen global baseline.


## Measured completion

The rerun on `main` at `0ef6107` completed successfully with no traceback.

Key measured result:

```text
HOME emission:
SPARSE   0.0%
MEDIUM  32.4%
DENSE   47.1%

OFFICE emission:
SPARSE   0.0%
MEDIUM  20.0%
DENSE   32.4%
```

Min-date blocking:

```text
HOME   45 users; 13 have raw-top coverage = 100% of observed opportunities
OFFICE 50 users; 14 have raw-top coverage = 100%
```

Expansion / near-miss concentration:

```text
HOME_PROBABLE: 5/5 DENSE
OFFICE margin-near: 2/2 DENSE
OFFICE share-near:  7/7 DENSE
```

The measured conclusion is therefore not simply "sparse users are penalized."

Stage 08b indicates two exposure-related failure modes:

- sparse absolute-support blocking;
- dense share/margin dilution.

A future adaptive policy should treat these separately and remain
label-specific.
