# Stage 07o handoff — Literature comparator suite

## Run only

\`\`\`text
notebooks/07o_literature_comparator_suite.ipynb
\`\`\`

The notebook uses:

\`\`\`text
/mnt/geolife-data
\`\`\`

No raw GeoLife rescan is required. It starts from the existing frozen
\`stays_baseline_v1.pkl\` cache and rebuilds the current CP2-v2 semantic-location
namespace.

## Expected frozen gates

Before any comparator:

\`\`\`text
CP1 stays                 5821
stay users                 136
semantic locations        2015
recurring locations        716
recurring-location users   104
HOME                        27
OFFICE                      16

frozen CP2-v2 parity: PASS
\`\`\`

## Comparators

The notebook runs:

\`\`\`text
SCIKIT_MOBILITY_1_3_1_HOME
ARXIV2302_GEOHASH_STAY_HOUR
PAVAN feature-space audit
SCITEPRESS_WORK_REST_STYLE
\`\`\`

No additional raw-data download is needed.

## Main tables to send back

After Run All, send the executed notebook with:

\`\`\`text
SCIKIT-MOBILITY HOME

ARXIV2302 GEOHASH HOME COVERAGE

ARXIV2302 GEOHASH HOME SPATIAL AGREEMENT

PAVAN FEATURE SPACE BY PRODUCTION ROLE

PAVAN LABEL RANK AUDIT

SCITEPRESS-STYLE HOME/WORK

SCITEPRESS WORK × STAGE-07j NEAR-MISS

literature suite summary
\`\`\`

The near-miss table is optional and appears when this artifact is still on the
Volume:

\`\`\`text
/mnt/geolife-data/cache/cp2_v2/07j_near_miss_office_audit/near_miss_office_audit_private.pkl
\`\`\`

## Output cache

\`\`\`text
/mnt/geolife-data/cache/cp2_v2/07o_literature_comparator_suite/
\`\`\`

User-level details remain private on the Volume.

## Interpretation

Do not call agreement accuracy.

Do not compare Pavan feature-space rows as though they were classifier outputs.

The geohash method is a documented stay-hour adaptation of a raw-sightings
paper and includes a project-specific cross-month modal aggregation.

The SCITEPRESS ranker is a generalized work-rest style comparator rather than
an exact reproduction of the one-user ADPC experiment.

No Stage-07o result changes HOME 27 / OFFICE 16 by itself.
