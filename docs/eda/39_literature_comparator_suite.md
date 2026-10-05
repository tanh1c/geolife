# Stage 07o — Literature comparator suite

## Purpose

Stage 07o adds a literature-grounded comparator layer on top of the frozen
CP1 + CP2-v2 representation.

The goal is not to find a new production threshold. It is to ask whether
different published/open heuristics and feature representations converge with
the current HOME/OFFICE candidate identities when stay detection and spatial
location identity are held fixed.

\`\`\`text
frozen 5,821 CP1 stays
        |
per-stay IANA local time
        |
production complete-link locations
        |
literature comparator suite
\`\`\`

## Frozen reproduction gates

The notebook must reproduce:

- 5,821 CP1 stays;
- 136 users with stays;
- 2,015 semantic locations;
- 716 recurring locations;
- 104 users with recurring locations;
- HOME = 27;
- OFFICE = 16.

A failure invalidates the suite.

## Comparator A — scikit-mobility HOME

scikit-mobility 1.3.1 documents \`home_location()\` as the exact location with
the largest number of observations during 22:00–07:00. If no nighttime
observation exists, the implementation falls back to the most frequently
observed location overall.

References:

- API:
  https://scikit-mobility.github.io/scikit-mobility/reference/individual_measures.html
- v1.3.1 source:
  https://github.com/scikit-mobility/scikit-mobility/blob/1.3.1/skmob/measures/individual.py

Stage 07o uses a source-equivalent replica instead of installing the old
scikit-mobility runtime package. The input is one observation per frozen stay,
located at its stable production location center and timestamped by local stay
arrival.

This is a HOME-only comparator.

## Comparator B — arXiv:2302.14742 hierarchical geohash HOME

Kabiri et al. identify monthly HOME through a level-6 -> level-7 geohash
procedure.

The source method keeps level-6 cells that are:

- observed on at least three days;
- observed on more than half of all observed days;
- observed at at least two distinct hours per observed day on average.

Eligible cells are ranked by observed days / distinct hours / sightings; the
top three are then reranked by nighttime evidence. Night is 21:00–06:00. The
winning level-6 cell is refined to level 7 by repeating the logic.

Reference:

- https://arxiv.org/pdf/2302.14742

Dataset mismatch is explicit. The paper uses raw mobile-device sightings over a
month. CP2 does not persist a raw-point cache, so Stage 07o converts frozen stays
into stay-hour occupancy observations: each local hour touched by a stay counts
as one timestamped observation at the production location center.

The paper is monthly. GeoLife spans multiple years, so a project-specific
aggregation is required to compare against one frozen HOME per user:

1. run the paper-style rule separately per user-month;
2. collect qualifying monthly level-7 HOME cells;
3. choose the modal level-7 cell across qualifying months;
4. break ties by accumulated nighttime hours, then lexical geohash.

Monthly coverage and modal share are reported so this added aggregation remains
visible rather than being presented as part of the paper.

## Comparator C — Pavan feature space

Pavan et al. (MDM 2015) propose mapping candidate important locations into a
feature space with three dimensions:

- area;
- intensity: time spent at a location;
- frequency: number of visits.

They evaluate on GeoLife.

Reference:

- DOI: 10.1109/MDM.2015.11
- public abstract:
  https://www.researchgate.net/publication/274565711_Finding_Important_Locations_A_Feature-Based_Approach

The accessible abstract does not provide enough information to reproduce one
unique classifier or ranking formula. Stage 07o therefore does not invent one.

Production locations provide:

- intensity = \`total_dwell_h\`;
- frequency = \`stay_count\`.

For area, Stage 07o uses an explicitly named descriptive proxy:

\`\`\`text
area_proxy_m2 = pi * (diameter_m / 2)^2
\`\`\`

The notebook reports feature distributions and within-user intensity/frequency
ranks for production HOME/OFFICE versus other recurring locations.

## Comparator D — SCITEPRESS/MATEC work-rest ranker

The 2018 paper demonstrates a GeoLife example on user 159 over seven days. It
takes the two largest regions and uses time-of-day proportions:

- 00:00–06:00 to infer Home;
- 08:00–18:00 to infer workplace;
- 18:00–24:00 for leisure interpretation.

It then applies Google reverse geocoding and keyword analysis.

Reference:

- https://www.matec-conferences.org/articles/matecconf/pdf/2018/32/matecconf_smima2018_03086.pdf

Stage 07o generalizes only the work-rest ranking component:

1. select the two largest production locations by \`stay_count\`;
2. choose the location with the most 00:00–06:00 dwell as HOME;
3. choose the location with the most 08:00–18:00 dwell as OFFICE.

No weekday filter is introduced because the cited passage does not specify one.

This is labeled \`SCITEPRESS_WORK_REST_STYLE\`: it is not an exact reproduction
of the paper's ADPC clustering or reverse-geocoding/NLP stages.

## Observation adapters

Two input adapters are materialized from the frozen semantic stays.

### Stay-arrival observations

One row per stay:

- user;
- production location;
- local arrival timestamp;
- production location center.

Used by the scikit-mobility source-equivalent rule.

### Stay-hour observations

One row per local hour touched by each stay:

- user;
- production location;
- local hour;
- production location center.

Used by the geohash comparator to provide a repeat-observation representation
closer to the paper's sightings than a single stay arrival.

## Comparison contracts

scikit-mobility and SCITEPRESS-style candidates use the same production
location namespace, so exact \`location_id\` agreement is valid.

The geohash method has a different spatial namespace. It is compared to
production HOME by distance at:

- 50 m;
- 100 m;
- 200 m.

Pavan is not assigned an agreement/accuracy score because the stage does not
construct a classifier.

## Stage-07j near-miss view

When the existing private Stage-07j audit panel is present, the
SCITEPRESS-style WORK candidate is compared against the fixed nine near-miss
candidates.

This diagnostic does not reopen Stage 07l.

## Outputs

Private:

- \`stay_arrival_observations_private.pkl\`;
- \`stay_hour_observations_private.pkl\`;
- \`scikit_home_candidates_private.pkl\`;
- \`scikit_home_comparison_private.pkl\`;
- \`geohash_monthly_home_private.pkl\`;
- \`geohash_monthly_audit_private.pkl\`;
- \`geohash_user_home_private.pkl\`;
- \`geohash_home_comparison_private.pkl\`;
- \`pavan_feature_space_private.pkl\`;
- \`scitepress_candidates_private.pkl\`;
- \`scitepress_comparison_private.pkl\`;
- optional \`scitepress_near_miss_private.pkl\`.

Aggregate:

- \`production_parity.csv\`;
- \`adapter_summary.csv\`;
- \`scikit_home_summary.csv\`;
- \`geohash_coverage_summary.csv\`;
- \`geohash_home_summary.csv\`;
- \`pavan_feature_summary.csv\`;
- \`pavan_rank_summary.csv\`;
- \`scitepress_summary.csv\`;
- \`literature_suite_summary.csv\`;
- optional \`scitepress_near_miss_summary.csv\`.

Cache root:

\`\`\`text
/mnt/geolife-data/cache/cp2_v2/07o_literature_comparator_suite/
\`\`\`

## Decision boundary

Stage 07o is evidence about methodological convergence and feature structure.

It does not:

- claim HOME/OFFICE accuracy;
- treat any paper/library as ground truth;
- replace CP1 or CP2;
- tune production thresholds;
- promote Stage-07j near-miss candidates.

The frozen production result remains HOME 27 / OFFICE 16 unless a separate
policy decision is justified.
