# Mobile / distributed-work hypothesis audit

## Status
Research-only audit over frozen 03a evidence; no production classifier or individual semantic label is created.

## EXECUTIVE RESULT
Hypothesis decision: mixed evidence. The frozen set has 23 mobile-work-like candidates, with 23 multiple-anchor, 23 OFFICE-abstained, and 0 OFFICE-emitted outcomes (`artifacts/03b/summary.json`).

## GROUP SIZES
Group A has 23 candidates; Group B has 23 matched OFFICE-abstained controls; Group C has 16 fixed-location-like frozen OFFICE comparators (`artifacts/03b/summary.json`).

## INDEPENDENT EVIDENCE
Construction features are separated from independent validation: mode composition, mode transitions, recurrent L* edges, edge entropy, sensitivity stability (`artifacts/03b/summary.json`).

## TRANSPORT MODE RESULT
Mode results are reported only for transportation-labeled coverage and remain auxiliary movement evidence, never a role assignment (`artifacts/03b/mode_evidence.csv`).

## ROUTE / TRANSITION RESULT
Route evidence uses recurrent abstract `L*→L*` transitions, not coordinates or semantic anchors (`artifacts/03b/route_structure.csv`).

## WEEKDAY VS WEEKEND RESULT
Weekday/weekend contrasts are descriptive because weekday mobility contributes to the frozen wrapper (`artifacts/03b/weekday_weekend.csv`).

## SENSITIVITY RESULT
The frozen Group A remains primary; perturbations report count and Jaccard overlap rather than selecting a favorable variant (`artifacts/03b/sensitivity.csv`).

## NEGATIVE CONTROLS
Sparse, boundary-heavy, travel-heavy, weekend-heavy, and same-stratum controls remain falsification checks (`artifacts/03b/summary.json`).

## WHAT SUPPORTS THE HYPOTHESIS
Only independent evidence that separates Group A from matched controls without recurring in negative controls can support further study.

## WHAT WEAKENS THE HYPOTHESIS
Insufficient label coverage, non-recurrent transitions, sensitivity, or matching imbalance weakens the hypothesis.

## WHAT CANNOT BE CONCLUDED
No individual receives a job-role classification; no true workplace, HOME, accuracy, or semantic POI conclusion is made.

## RECOMMENDED NEXT STEP
Use the aggregate result only to decide whether a distributed-mobility regime warrants further research.

## Q1
Are candidates robust? See `artifacts/03b/sensitivity.csv`.

## Q2
Do candidates differ after matching? See `artifacts/03b/matched_controls.csv`.

## Q3
Do modes differ? See `artifacts/03b/mode_evidence.csv`.

## Q4
Do transitions recur? See `artifacts/03b/route_structure.csv`.

## Q5
Is weekday mobility stronger? See `artifacts/03b/weekday_weekend.csv`.

## Q6
Could controls explain it? See `artifacts/03b/summary.json`.

## Q7
How many have independent support? See `artifacts/03b/summary.json`.

## Q8
How many remain ambiguous? See `artifacts/03b/summary.json`.

## Q9
Does evidence justify further study? See the research-only decision above.

## Q10
What is still needed before a semantic label? External validation and an approved semantic evaluation design.
