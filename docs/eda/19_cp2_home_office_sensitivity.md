# CP2 Home / Office scoring sensitivity

Date: 2026-09-18  
Status: OPEN — bounded sensitivity implemented; measured output pending review.

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
