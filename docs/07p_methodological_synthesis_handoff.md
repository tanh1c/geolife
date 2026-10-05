# Stage 07p handoff — Final methodological synthesis

## Run only

\`\`\`text
notebooks/07p_methodological_synthesis.ipynb
\`\`\`

The notebook uses aggregate outputs already stored under:

\`\`\`text
/mnt/geolife-data/cache/cp2_v2/
\`\`\`

It does not require raw GeoLife data and does not require private user-level
pickles.

## Required previous measured stages

The following cache folders must exist:

\`\`\`text
05_home_office_reliability_validation
07i_threshold_sensitivity
07j_near_miss_office_audit
07l_imagery_unblinding_synthesis
07m_trackintel_semantic_parity
07n_trackintel_end_to_end
07o_literature_comparator_suite
\`\`\`

If a required aggregate CSV is missing, Stage 07p will stop and identify the
missing path.

## Expected first hard gate

You should see:

\`\`\`text
measured lineage validation: PASS
\`\`\`

The notebook intentionally verifies previously accepted measurements before
building the synthesis.

## Main tables to send back

After Run All, send the executed notebook containing:

\`\`\`text
measured lineage validation

HOME evidence ladder

OFFICE evidence ladder

OFFICE near-miss policy synthesis

pipeline sensitivity summary

LITERATURE SUITE
PAVAN FEATURE MEDIANS
PAVAN WITHIN-USER RANK AUDIT

final production-policy snapshot

claim boundary
\`\`\`

## Expected final policy

The notebook must end with:

\`\`\`text
HOME = 27
OFFICE = 16

change_home_gate   = False
change_office_gate = False
promote_near_miss  = False

final_policy = freeze_HOME_27_OFFICE_16
\`\`\`

## Output cache

\`\`\`text
/mnt/geolife-data/cache/cp2_v2/07p_methodological_synthesis/
\`\`\`

All Stage-07p outputs are aggregate.

## Interpretation

Stage 07p is the final synthesis layer, not another tuning stage.

Do not convert evidence ladders into an accuracy score.

Do not use literature/Trackintel agreement to reopen the nine near-miss OFFICE
cases without new independent supervision.

If lineage validation passes and the final policy snapshot reproduces the frozen
decision, the current CP2-v2 methodological validation track can be closed.
