# Stage 07k handoff — Historical imagery review

## Run once

Run:

`notebooks/07k_historical_imagery_review.ipynb`

from current `main`.

You do not need to rerun Stage 07j or any earlier notebook.

Expected gates:

```text
07j audit reproduction: PASS (25 total / 9 near-miss)
blinding + spatial/date validation: PASS
```

## Files to use for manual review

Start with:

```text
/mnt/geolife-data/cache/cp2_v2/07k_historical_imagery_review/
  near_miss_9_blinded_historical_imagery_review_private.kml
  near_miss_9_blinded_review_manifest_private.csv
  historical_imagery_review_rubric.csv
```

Do not open the unblinding key during visual review.

Optional reference:

`baseline16_blinded_historical_imagery_reference_private.kml`

## Google Earth Pro workflow

For each `Ixx candidate`:

1. Open the near-miss KML.
2. Enable Historical Imagery.
3. Read the candidate median observation date from the placemark.
4. Move to the nearest interpretable historical image.
5. Record the actual imagery date used.
6. Inspect 50 / 100 / 150 m rings.
7. Fill the review CSV using the fixed rubric.
8. Do not use Stage-07j behavior/BCL evidence while classifying imagery.

If the closest image is materially earlier/later than the observation period, record that temporal mismatch explicitly.

## Important distinction

Satellite imagery may support:

- structure existed;
- campus / institutional / industrial / residential / transport / mixed morphology;
- candidate lies within a visible complex.

It cannot prove:

- employer;
- occupation;
- OFFICE ground truth;
- historical business name.

Present-day map/geocoder names are naming aids only.

## After review

Upload the completed:

`near_miss_9_blinded_review_manifest_private.csv`

Then Stage 07k can be unblinded and compared against Stage-07j behavior + BCL without changing the original visual classifications.
