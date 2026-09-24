# Learning Journal — EN

## 2026-09-16 — Why GeoLife needs deeper EDA

GeoLife is not a small i.i.d. tabular dataset. It is hierarchical and spatiotemporal: points belong to trajectories, trajectories belong to users, users have very different observation periods, sampling rates vary, and geography/timezone affect interpretation.

Key lessons:

- verify dataset counts from files instead of trusting documentation blindly;
- inspect raw distributions before choosing cleaning thresholds;
- avoid loading every GPS point into one giant DataFrame when trajectory-level reduction is enough;
- evaluate user-history imbalance because Home/Office inference needs repeated behavior;
- treat transportation labels as auxiliary movement labels, not Home/Office ground truth;
- make timezone semantics explicit before using 'night' or 'office hours';
- treat mobility privacy as a system-design concern, not just a reporting concern.

## 2026-09-16 — What the first measured distributions changed

The mounted release contains 182 users and 18,670 trajectory files. The user distribution is highly long-tailed: the median user has 27.5 trajectories, while the largest has 2,153. The top 10 users alone contribute 47.4% of all trajectories.

This changes how I should think about evaluation. A single trajectory-weighted score can mostly reflect heavy users, so later model evaluation should include a per-user/macro view where appropriate. I also observed that users with transportation-label files represent 69/182 users but 58.4% of all trajectories, so the labeled subset is not representative by trajectory volume.

The first raw trajectory also showed why spot checks are useful but insufficient: timestamps parsed cleanly as UTC, while altitude values had a very wide range. I should not convert one unusual value into a cleaning rule; I need the dataset-wide distribution first.

## 2026-09-16 — Data-quality diagnostics changed the cleaning plan

The full scan confirmed 24,876,978 points. It also showed why a simple `speed > threshold => noise` rule would be premature.

I found one malformed latitude (`400.166667`) that is clearly different from a repeated corruption pattern in another trajectory, where coordinates jump roughly 850–862 km in one second over and over. These are different failure modes and may need different handling.

I also confirmed that one raw trajectory is byte-identical across three different user folders. This introduces a potential leakage/weighting concern for future evaluation and shows that file-level duplication should be measured explicitly.

## 2026-09-16 — A hypothesis was tested and rejected

I initially suspected that the PLT `serial_date` field might preserve hidden sub-second timing and that the apparent duplicate timestamps were created by parsing only the text date/time fields. The data did not support that hypothesis.

In a trajectory with 45,215 duplicate text timestamps, the duplicate count stays exactly 45,215 when timestamps are reconstructed from `serial_date`. Several different coordinates inside the same recorded second also have the same serial-date value. The few-microsecond difference between serial and text timestamps is just floating-point conversion noise, not useful extra timing precision.

This changes the preprocessing problem: same-second observations are genuinely ambiguous at the released timestamp resolution. I cannot estimate within-second velocity or impose an arbitrary order. I should first measure the spatial spread of these groups, then decide whether to collapse them or preserve them as simultaneous observations.

## 2026-09-16 — Same-second groups are mostly jitter, but exact duplicates are structural

The same-second analysis found 212,409 groups. Most are spatially compact: the median maximum radius from the coordinate-wise median is about 0.47 m, p95 is 4.85 m, p99 is 7.06 m, and 99.61% are within 10 m. This supports testing a robust one-row-per-timestamp representation for compact groups. The tiny long-distance tail must be flagged separately rather than averaged across incompatible locations.

The raw-file hash scan changed the evaluation plan more substantially. There are 821 exact duplicate hash groups containing 1,677 files. About 8.98% of trajectory files participate in an exact duplicate group, and several groups span different user IDs. Therefore content identity is not a rare edge case. Future train/test splitting should keep byte-identical content in the same fold, and benchmark weighting should avoid giving duplicated content accidental extra influence.

## 2026-09-16 — Cross-user duplication is large enough to affect evaluation

All 821 exact-duplicate hash groups were found to span multiple user IDs. The 1,677 affected files make up 8.98% of trajectories but contain 2,965,977 points, or 11.92% of the full dataset.

This is important because the point-weighted exposure is larger than the file-count exposure. Duplicate traces are therefore longer than average and can have disproportionate influence on point-level metrics. The raw release does not explain why the same content is assigned to multiple users, so I should not infer that these user IDs represent the same person. For evaluation, however, content hashes need to act as grouping keys so identical traces cannot leak across folds.

## 2026-09-16 — Redundancy and connected components changed the split strategy

After retaining one representative per exact-content hash group, the extra copies still account for 1,495,115 points, or 6.01% of the full dataset. This clarifies the difference between duplicate exposure and true redundancy: 11.92% of points belong to duplicate groups, but 6.01% are extra copies beyond one representative.

The shared-content user graph includes 52 users across 18 connected components. The largest component contains 15 user IDs. Therefore even a user-level split is not enough to guarantee content independence: different user IDs can still be linked by identical trajectories. For strict evaluation, content-hash grouping is required, and connected-component grouping is a reasonable candidate when measuring user-level generalization.

A useful stopping lesson is also emerging: EDA must support decisions rather than becoming the entire project. Duplicate structure is now sufficiently characterized for CP1. The next focus should return to preprocessing that directly affects stay-point detection: same-second consolidation, temporal gaps, and movement anomalies.

## 2026-09-16 — Same-second consolidation solves one failure mode, not all of them

The consolidation prototype made the separation between failure modes concrete. On a duplicate-heavy trajectory, 56,780 raw points collapsed to 11,565 timestamp rows with only three spatial conflicts, and the largest inspected speeds dropped to roughly 225 km/h. That is evidence that timestamp-resolution ambiguity was materially affecting segment construction.

The same transform did not fix the structurally corrupted user-062 trajectory. It flagged 26 same-second conflicts, but the multi-million-km/h jumps remained because they occur between singleton timestamps at different seconds. This means same-second ambiguity and impossible inter-timestamp movement are independent cleaning problems.

The main lesson is to make preprocessing staged and interpretable: first validate coordinates, then consolidate compact same-second groups, then deal with temporal gaps and movement anomalies. A global speed filter should come only after those earlier failure modes are removed or flagged.

## 2026-09-16 — Full consolidation changed how I interpret the speed tail

Applying same-second consolidation to the whole release reduced 24,876,978 raw points to 24,178,077 timestamp-level rows, a 2.81% reduction, while only 835 timestamps (0.0035%) were spatial conflicts. This is strong evidence that the transform is low-loss for the dominant duplicate-second pattern.

The more important result is that the residual speed tail barely disappears. At the trajectory level, 46.96% of trajectories still have a maximum speed above 100 km/h, but at the segment level only 5.40% of valid movement segments exceed 100 km/h. Above 150 km/h the segment share falls to about 1.00%, above 200 km/h to 0.37%, and above 1,000 km/h to 0.007%.

This taught me that a trajectory-max statistic answers a different question from segment prevalence. One bad segment can make an otherwise normal trajectory look extreme, so cleaning thresholds should be reasoned about at the segment level and then traced back to trajectories/users.

Temporal gaps are another independent issue: the median trajectory's largest gap is 325 seconds, while p90 is about 11,010 seconds and the maximum is 93,298 seconds. For stay-point detection, nearby points separated by a long observation outage cannot automatically be interpreted as continuous dwelling.

## 2026-09-16 — Gap sensitivity shows why continuity must be explicit

The gap sensitivity table made the continuity problem concrete. More than half of trajectories contain at least one gap longer than five minutes, 41.74% contain a gap longer than ten minutes, and 29.66% contain a gap longer than thirty minutes. A very strict 30-60 second continuity threshold would split most trajectories at least once.

This means the gap threshold is not a harmless implementation detail. It changes which observations can contribute to a dwell interval, so it should be exposed as a sensitivity parameter and justified from downstream stay-point behavior rather than chosen only for convenience.

The transportation-label parser also yielded 14,718 intervals across 69 user folders. Walk dominates the interval count, followed by bus, bike, taxi, car, subway and train, while airplane has only 17 intervals. These labels are useful for validating plausible movement-speed tails, but they are auxiliary evidence only and not Home/Office ground truth.

## 2026-09-16 — Transportation labels validate the broad speed shape but reveal label ambiguity

The first strict-containment join matched about 4.85 million segments, covering 40.83% of valid segments from labeled users. The broad distributions make sense as auxiliary evidence: airplane has median/p99 speeds around 624/938 km/h, train around 93/210, car around 30/120, bus around 17/90, walk around 4/41, and bike around 11/41.

This immediately rules out a naive global 500 km/h filter: more than half of the currently matched airplane segments exceed 500 km/h. At the same time, non-airplane modes still contain rare multi-thousand-km/h maxima, so being inside a transportation label does not automatically make a GPS segment trustworthy.

The important quality finding is that 1,903 label intervals overlap or touch the previous interval under the current check, and examples include genuine overlap between different modes. That means the current `merge_asof` join can choose one active label when several are valid. The exact per-mode percentiles are therefore provisional. Before using them to freeze a speed rule, overlapping labels should be canonicalized so only periods with one distinct active mode are benchmarked.

## 2026-09-16 — Historical inclusive-end canonicalization

The first canonicalization run produced 14,537 unambiguous windows and 1,886 ambiguous windows and a V2 strict-containment join of 4,812,641 segments (40.52% coverage). That run used inclusive-end semantics and is retained as historical evidence only.

Its broad per-mode speed shape was already stable enough to reject naive 100/200/500 km/h filters, but the exact interval accounting was later re-audited.

## 2026-09-17 — Interval semantics can change counts without changing the scientific conclusion

An independent audit exposed a subtle but important contract issue: treating transportation labels as inclusive-end intervals turns many endpoint touches into one-second overlaps. The corrected convention is half-open `[start, end)`.

The final rerun measured 1,742 different-mode endpoint touches, 146 true-overlap pairs, 14,583 unambiguous windows, 149 atomic ambiguous sweep slices, and 138 report-level ambiguous windows. Unambiguous time is 12,720.833 hours, ambiguous time is 76.345 hours, or 0.597% of represented labeled time.

The corrected V3 strict-containment join matched 4,807,087 of 11,878,198 valid labeled-user segments (40.47%). The speed distribution stayed effectively unchanged: airplane p99 is 937.99 km/h, train 210.34, car 119.63, bus 90.59, bike 40.63 and walk 40.39. Airplane max is 1,048.11 km/h and 52.92% of canonical airplane segments exceed 500 km/h.

The lesson is broader than this dataset: interval boundary semantics are part of the data contract. A small definition error can substantially distort event/window counts even when duration-weighted conclusions stay stable. I should specify `[start, end)` or another convention explicitly before joining temporal labels.

This audit also demonstrates a useful stopping rule for EDA. The correction was bounded, reproduced independently, and did not change the design decision. EDA is therefore closed for CP1. The next step is contract review and RED tests before production preprocessing/stay-point code.

## 2026-09-18 — A threshold can mean “safe to transform” without meaning “valid versus corrupt”

The mentor same-second question exposed an important modeling distinction. The 10 m rule was originally easy to describe as a conflict/corruption threshold, but the transportation audit showed that this interpretation was too strong.

Train and many subway cases above 10 m were compatible with movement at the scale already observed in the audited transportation-speed benchmark, while most walk/bike cases were not. The same >10 m population therefore mixes several possible causes.

The robust conclusion is narrower: 10 m is the radius below which a same-second group is compact enough to collapse safely. Above 10 m, within-second ordering is unidentifiable, so the conservative action is still to break continuity, but the diagnostic should describe spatial ambiguity rather than claim corruption.

This is a general data-engineering lesson: a threshold can define when a transformation is safe without classifying the underlying data as good or bad.

## 2026-09-18 — CP2 starts with abstention and timezone semantics, not with a Home/Office formula

The next tempting shortcut would be to take stays, add eight hours, and call nighttime locations Home and weekday daytime locations Office. The earlier EDA already showed why that is unsafe: GeoLife contains trajectories outside Beijing, while the timestamps are UTC/GMT.

The CP2 scaffold therefore puts a timezone/geography gate before semantic scoring. It also treats insufficient user history as a valid abstention case instead of forcing a Home or Office label.

Another lesson is that Home/Office is a user-level recurring-location problem, not a trajectory-file problem. The first CP2 notebook materializes the frozen 5,821 stays, audits history sufficiency, then explores per-user spatial clustering before defining semantic scores.

Because Home and Office are sensitive inferred locations, privacy now becomes part of the artifact contract: precise user-level inferred coordinates should remain in private caches, while the repository keeps aggregate diagnostics and decision records.

## 2026-09-18 — First CP2 materialization shows why abstention and cluster diagnostics matter

The first full-release CP2 stay materialization reproduced the frozen CP1 total exactly: 5,821 stays across 136 users. This is a useful contract check because the semantic stage is now demonstrably consuming the same behavior that CP1 validated.

History sufficiency is uneven. Although 120 users have at least two stays, only 62 have stays on at least ten distinct UTC dates. A Home/Office system therefore needs abstention and evidence thresholds; producing a label for every release user would confuse pipeline coverage with semantic certainty.

The first per-user DBSCAN experiment also surfaced a subtle spatial-clustering issue. With epsilon set to 200 m, the largest distance from a cluster's median representative to a member stay reached about 527 m. DBSCAN epsilon limits density-neighbor links, not total cluster diameter, so chaining can create a location much wider than the intuitive 200 m interpretation.

This means the recurring-location contract needs an explicit compactness diagnostic or a different clustering rule before production semantics are frozen.

The spatial stay distribution remains strongly Beijing-centered but includes large geographic outliers. That empirical result confirms the earlier design warning: local behavioral time cannot be created by blindly adding eight hours to every UTC timestamp.

## 2026-09-18 — Timezone scope should be attached to observations, not only users

The CP2 timezone audit exposed another subtle semantic issue. A user can be predominantly Beijing-based and still have travel stays elsewhere. If I classify the user as “Beijing” and then convert every stay for that user to `Asia/Shanghai`, I can still assign the wrong local time to travel observations.

The safer v1 design is two-stage:

1. decide whether a user is sufficiently Beijing-focused using stay-share and dwell-share sensitivity;
2. even for accepted users, only in-region stays enter Beijing local-time semantic scoring.

Out-of-region travel stays are excluded rather than silently converted.

This is a useful general lesson for spatiotemporal systems: metadata such as timezone may need observation-level scope even when eligibility is decided at the user level.

## 2026-09-18 — Recurring-location clustering needs a diameter contract, not only a neighbor radius

The first DBSCAN representation exposed a useful mismatch between parameter intuition and actual geometry. With epsilon 200 m, one cluster still had a member about 527 m from its median representative.

That is not a DBSCAN bug; density connectivity can chain many local links into a much wider component.

For Home/Office inference, I want the spatial threshold to have a direct semantic meaning: a recurring location should not contain points whose pairwise separation exceeds the threshold. Complete-linkage clustering provides that property more directly because each merge is governed by the maximum pairwise distance between groups.

The next audit therefore compares complete linkage at 100/200/300 m and verifies the resulting cluster diameter explicitly before freezing the recurring-location contract.

## 2026-09-18 — Behavioral-time features should use interval overlap, not arrival-hour labels

The first Home/Office scoring audit uses the full stay interval when measuring behavioral evidence. A stay from 20:50 to 21:30 should contribute only 21:00–21:30 to the night window. Labeling the whole stay from its arrival hour would create a boundary artifact.

The same principle matters for office evidence and for stays crossing midnight. Behavioral-time features are interval-overlap problems, not point-in-time classification problems.

I also avoid turning the first score into a probability. Without Home/Office ground truth, relevant-dwell share, support dates, and top-1 versus top-2 margin are interpretable evidence components, but they are not calibrated confidence probabilities. The next step is to inspect their distributions and define abstention rules before productionizing the heuristic.

## 2026-09-18 — Home and Office evidence should not share a threshold by default

The first interval-overlap scoring run produced noticeably different evidence distributions for Home and Office. Home candidates had a median relevant-dwell share around 0.635 and median top-two margin around 0.513, while Office candidates were around 0.357 and 0.243.

That difference matters. A single threshold such as “share >= 0.5” would be moderately selective for Home but much more aggressive for Office. Without semantic ground truth, there is no justification for pretending both evidence families are calibrated to the same scale.

The next step is therefore separate, bounded sensitivity for Home and Office. I also want to track whether the selected top location itself stays stable when time windows move slightly; coverage alone can hide an unstable heuristic.

## 2026-09-18 — Final CP2 abstention gates come from stability plus middle sensitivity, not pseudo-accuracy

The bounded scoring sensitivity made the stopping rule concrete. The baseline Home window (21–06) kept the same top location for 93.6% of shared users against 20–06 and 90.5% against 22–06. The Office baseline (09–17) was similarly stable at 95.0% versus 08–17 and 92.5% versus 09–18.

Without Home/Office ground truth, I cannot pick a threshold by maximizing accuracy. Instead CP2 v1 freezes the middle support/share/margin settings: Home uses 3 dates / 0.50 share / 0.20 margin, while Office uses 3 dates / 0.30 share / 0.10 margin. These emit 27 and 16 users respectively from the 97-user semantic cohort.

The confidence output is also intentionally framed as evidence strength rather than probability. It averages dwell share, top-two margin, and a date-support factor capped at five dates, while exposing all raw components next to the aggregate.

## 2026-09-18 — RED tests caught a zero-evidence dtype bug that notebook data did not

The first production Home/Office implementation passed compilation but failed RED tests when one semantic evidence family had no overlap at all. After merging an empty feature table, pandas kept an object-typed zero column; the eager division inside `np.where` then raised `ZeroDivisionError`.

The notebook's full-release data had enough mixed Home/Office evidence that this edge case did not appear naturally.

The fix was not to special-case the test. The production feature builder now coerces dwell columns to numeric and uses `np.divide(..., where=denominator > 0)`, making zero-evidence users a first-class abstention case.

This is exactly why the notebook-to-production transition needs acceptance tests even when the exploratory output looks correct.

## 2026-09-18 — Full-release parity is the final notebook-to-production contract check

The production `infer_home_office()` API was run against the same cached 5,821 stays used by the CP2 notebook. It reproduced the frozen emission counts exactly: 27 HOME and 16 OFFICE labels, totaling 43 rows across 36 users.

This final parity check is different from unit tests: tests protect local semantics and edge cases, while parity verifies that the assembled production path reproduces the full-release notebook decision on the actual materialized dataset.

With both checks passing, CP2 v1 has a much stronger handoff from exploratory evidence to production code.

## 2026-09-18 — A notebook should preserve the reasoning contract, not only code and output

After production parity passed, notebooks 02 / 02b / 02c / 03 were expanded to match the mentor-audit narrative style.

A reproducible notebook that contains only executable code is still a weak long-term handoff. A future reader also needs to know:

- which question each section answers;
- why a metric exists;
- what denominator an output uses;
- which conclusions the evidence supports;
- which conclusions it does not support;
- which early decisions were superseded by later audits.

This matters here because several initial assumptions changed through evidence: blanket UTC+8 became an explicit geography/timezone cohort; DBSCAN 200 m was replaced by a complete-link diameter contract; and same-second >10 m was reinterpreted as unresolved spatial ambiguity rather than automatic corruption.

A strong notebook is therefore an executable decision record, not merely a scratchpad with plots.

## 2026-09-18 — Abstention belongs in the model response, not the HTTP error model

The first API-serving contract forced a useful separation between invalid requests and valid uncertainty.

A malformed timestamp, impossible coordinate or reversed interval is a transport/schema problem and should return HTTP 422. A user who is outside the Beijing semantic cohort, has no recurring location, or has weak Home/Office evidence has supplied a perfectly valid request. Those cases should therefore return HTTP 200 with an explicit model abstention reason.

This keeps serving semantics aligned with the conservative CP2 model: uncertainty is a first-class output rather than an operational failure.

The API contract also omits precise inferred Home/Office coordinates even though the internal model computes them. Returning only a request-local `location_id` plus evidence fields gives downstream systems enough traceability for v1 while reducing accidental semantic-location disclosure.

A second lesson is that request-time configuration is part of the model contract. Allowing clients to submit thresholds such as `home_min_share` would silently turn one frozen CP2 model into many per-request variants, so v1 explicitly forbids extra tuning fields.

## 2026-09-18 — Full HTTP replay validates adapter semantics, not only route availability

The CP3 release notebook replayed all 136 users from the private 5,821-stay cache through the FastAPI endpoint and compared the response to direct `infer_home_office()` output.

The aggregate counts matched exactly: 27 HOME and 16 OFFICE labels, 43 emitted rows across 36 users. More importantly, the notebook also checked the exact emitted `(user_id, label)` keys, location ids, relevant dates and numerical evidence fields.

This is stronger than checking only aggregate counts. Two serving layers could both produce 27/16 while disagreeing about which users were labeled.

The replay also produced useful abstention observability. HOME abstained for 39 geography cases, 24 recurring-history cases and 46 semantic-evidence cases; OFFICE had the same first two counts and 57 semantic-evidence abstentions. These are model outcomes, not error rates.

A pandas FutureWarning appeared repeatedly for partial emissions because the model concatenated one non-empty frame with one empty frame. The values were correct, but the warning exposed a future dtype-risk. The production code now concatenates only non-empty frames and has a regression test for that case.

## 2026-09-24 — Timezone lookup is a polygon problem, not a city-radius rule

A review of notebook 03 exposed that I had mixed two different concepts: **timezone assignment** and **Beijing-focused cohort selection**.

The current rule uses an approximate Beijing reference point and a 100 km radius. That can be a useful engineering scope, but it is neither a timezone boundary nor an administrative Beijing boundary.

The more general lesson is that a timezone should not be modeled as a simple `lat_min / lat_max / lon_min / lon_max` rectangle. The IANA tz database provides timezone identifiers and representative locations; mapping a GPS coordinate to a timezone is a point-in-polygon problem. Datasets such as timezone-boundary-builder associate polygons with IANA `tzid` values, and libraries such as `timezonefinder` can perform offline WGS84 `(lat, lon)` lookup.

A cleaner GeoLife design is:

```text
stay coordinate
    ↓
timezone polygon lookup
    ↓
IANA tzid per stay
    ↓
ZoneInfo(tzid)
    ↓
local behavioral time
```

Only after that should the pipeline answer a separate question: whether a user is Beijing-focused.

If CP2 requires a true Beijing geographic cohort, an administrative Beijing polygon is the better contract. If it only needs a central-Beijing engineering cohort, a radius rule can remain, but it should be named and documented as an approximation rather than timezone truth.

General lesson: **geographic scope and timezone scope can be related without being the same contract**.

