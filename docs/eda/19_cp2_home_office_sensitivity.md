# CP2 Home / Office scoring sensitivity

Date: 2026-09-18  
Status: COMPLETE — CP2 v1 behavioral windows and separate Home/Office emission gates frozen as engineering baselines.

## Motivation

The first scoring audit found materially different evidence distributions for Home and Office.

Measured on the frozen 97-user semantic cohort:

- Home candidates: 47 users; median dwell share 0.635; median top-two margin 0.513;
- Office candidates: 40 users; median dwell share 0.357; median top-two margin 0.243.

Therefore one shared emission threshold is not justified by the observed evidence.

## Sensitivity family A — behavioral windows

Home windows:

- 20:00–06:00;
- 21:00–06:00;
- 22:00–06:00.

Office windows:

- weekdays 08:00–17:00;
- weekdays 09:00–17:00;
- weekdays 09:00–18:00.

For each variant report:

- supported users;
- users shared with the baseline variant;
- fraction of shared users whose top location is unchanged;
- median top share;
- median top-two share margin;
- median relevant support dates.

The main robustness signal is not only coverage but top-location stability.

## Sensitivity family B — emission / abstention thresholds

Home grid:

- minimum relevant dates: 2 / 3 / 5;
- minimum night-dwell share: 0.4 / 0.5 / 0.6;
- minimum top-two share margin: 0.1 / 0.2 / 0.3.

Office grid:

- minimum relevant dates: 2 / 3 / 5;
- minimum office-dwell share: 0.2 / 0.3 / 0.4;
- minimum top-two share margin: 0.05 / 0.10 / 0.20.

For every configuration report:

- emitted users;
- coverage among all 97 semantic-cohort users;
- coverage among the 73 users with a recurring semantic location.

## Why the grids differ

The grids are anchored to the measured evidence distributions, not to a claim that Home and Office should use the same confidence scale.

Home evidence is more concentrated and has larger top-two margins in the first run. Office evidence is weaker and more diffuse. Using the Home thresholds for Office would make Office abstention much more aggressive without ground-truth justification.

## Decision principle

The final engineering emission rules should favor:

- stability across neighboring time windows;
- a clear reduction of weak low-share / low-margin candidates;
- non-pathological coverage;
- explicit abstention rather than forced labels.

No configuration is selected by supervised accuracy because GeoLife provides no direct Home/Office ground truth.

## Confidence semantics

Any final confidence output remains heuristic evidence strength, not a calibrated probability.

Candidate ingredients:

- relevant-dwell share;
- top-two share margin;
- distinct relevant dates;
- relevant dwell duration;
- observation-history support.

The exact combination should be frozen only after sensitivity review.

Notebook: `notebooks/03_home_office_baseline.ipynb`.


## Measured behavioral-window stability

Home:

| window | supported users | shared with 21–06 baseline | same top location |
| --- | ---: | ---: | ---: |
| 20–06 | 51 | 47 | 93.6% |
| 21–06 | 47 | 47 | 100% |
| 22–06 | 42 | 42 | 90.5% |

Office:

| window | supported users | shared with 09–17 baseline | same top location |
| --- | ---: | ---: | ---: |
| 08–17 | 44 | 40 | 95.0% |
| 09–17 | 40 | 40 | 100% |
| 09–18 | 40 | 40 | 92.5% |

The baseline windows remain reasonably stable under the bounded neighboring choices, so CP2 v1 keeps the original interpretable windows rather than expanding or narrowing them.

## Measured emission sensitivity and decision

The grid shows monotonic coverage reduction as support/share/margin requirements tighten.

CP2 v1 freezes the **middle sensitivity setting** for each semantic label:

### Home

- local window: 21:00–06:00;
- minimum relevant dates: 3;
- minimum night-dwell share: 0.50;
- minimum top-two share margin: 0.20.

Measured emission: **27 / 97 semantic-cohort users** (27.84%), or 27 / 73 users with recurring locations (36.99%).

### Office

- local weekday window: 09:00–17:00;
- minimum relevant dates: 3;
- minimum office-dwell share: 0.30;
- minimum top-two share margin: 0.10.

Measured emission: **16 / 97 semantic-cohort users** (16.49%), or 16 / 73 users with recurring locations (21.92%).

The thresholds are deliberately different because the measured Office evidence distribution is weaker and more diffuse than Home. They are engineering abstention gates, not supervised-optimal cutoffs.

## Heuristic evidence strength

For an emitted label, expose a non-probabilistic evidence-strength score:

```text
support_factor = min(relevant_dates / 5, 1)
evidence_strength = (relevant_dwell_share + top_two_share_margin + support_factor) / 3
```

Properties:

- bounded to [0, 1];
- monotonic in each included evidence component;
- support saturates at 5 relevant dates, matching the strongest support point reviewed in sensitivity;
- not calibrated to semantic correctness probability.

The raw components must remain available alongside the aggregate score.

## CP2 v1 scoring decision

The scoring gate is resolved. The next step is RED acceptance tests followed by production implementation under `src/geolife/model/`.
