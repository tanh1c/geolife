# Stage 08a handoff — HOME coverage expansion

## Run only

~~~text
notebooks/08a_home_coverage_expansion.ipynb
~~~

No raw GeoLife scan is required.

The notebook uses the existing Modal Volume:

~~~text
/mnt/geolife-data
~~~

## Required caches

Stage 05b:

~~~text
cache/cp2_v2/05b_home_consensus_adaptive_work/home_consensus_private.pkl
~~~

Stage 07m:

~~~text
cache/cp2_v2/07m_trackintel_semantic_parity/trackintel_candidates_private.pkl
~~~

Stage 07n:

~~~text
cache/cp2_v2/07n_trackintel_end_to_end/trackintel_osna_candidates_private.pkl
~~~

Stage 07o:

~~~text
cache/cp2_v2/07o_literature_comparator_suite/scikit_home_candidates_private.pkl
cache/cp2_v2/07o_literature_comparator_suite/scitepress_candidates_private.pkl
cache/cp2_v2/07o_literature_comparator_suite/geohash_user_home_private.pkl
~~~

## Expected first gate

The notebook must reproduce:

~~~text
CP1 stays = 5821
production HOME = 27
production OFFICE = 16
historical Stage-05b HIGH/MEDIUM non-production HOME candidates = 2\ncurrent cache candidate count = reported at runtime

production + Stage-05b expansion gate: PASS
~~~

## Main output tables

Send the executed notebook with:

~~~text
TARGETED HOME EXPANSION EVIDENCE

HOME EXPANSION SUPPORT SUMMARY

HOME TIERED COVERAGE

candidate descriptive location context

policy
~~~

The candidate table uses stable audit ids H01, H02, ... rather than user ids.

## Expected interpretation

Possible outcome:

~~~text
HOME_HIGH_CONFIDENCE_CORE = 27
HOME_PROBABLE_NEW         = measured current-cache count\nHOME_PLAUSIBLE_NEW        = measured current-cache count\nHOME_EXPANSION_ABSTAIN    = measured current-cache count
~~~

The three expansion counts must sum to the current Stage-05b HIGH/MEDIUM non-production candidate count.

Production must remain:

~~~text
HOME = 27
OFFICE = 16
~~~

## Output cache

~~~text
/mnt/geolife-data/cache/cp2_v2/08a_home_coverage_expansion/
~~~

## Important boundary

A HOME_PROBABLE result is intended as a separate downstream confidence tier.

Do not silently merge it into the frozen production HOME set.

After the executed notebook is reviewed, a separate policy decision can decide
whether HOME_PROBABLE should be exported to downstream analysis.
