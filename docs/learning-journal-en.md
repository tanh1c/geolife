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

## 2026-09-24 — Change one semantic layer at a time during timezone migration

Notebook 03 now assigns an IANA timezone to each stay from its coordinate instead of using a 100 km circle around a Beijing reference point.

A key migration lesson is to **avoid retuning every threshold at once**. The 80% stay-share / 80% dwell-share threshold is retained as a control:

```text
v1:
Beijing-distance proxy + 80/80

candidate:
coordinate timezone lookup + 80/80
```

This makes downstream differences easier to attribute to the timezone-assignment change rather than threshold tuning.

Travel stays for eligible users are also retained and converted with their own timezone instead of being discarded solely because they fall outside the old Beijing radius.

The old 97-user / 4,197-stay cohort and 27 HOME / 16 OFFICE emissions are now historical references only. They must not be copied into the candidate notebook as if parity were expected.

General lesson: when an upstream semantic contract changes, downstream measured outputs become stale and must be rerun before they are treated as evidence.

## 2026-09-24 — If geography is not a product requirement, timezone should not become a cohort filter

The first timezone-v2 run showed that coordinate-based lookup works cleanly: all 5,821 frozen CP1 stays resolved to an IANA timezone, with Asia/Shanghai dominating the release. I initially kept an 80/80 Asia/Shanghai concentration rule as a migration cohort.

A follow-up review showed that this is still an unnecessary restriction when the task only asks for Home/Office inference and does not require a Beijing-only or China-only scope.

The final notebook therefore uses:

```text
each stay
→ coordinate → timezone
→ UTC → that stay's local time
→ recurring location
→ HOME/OFFICE evidence
```

Asia/Shanghai concentration remains a useful dataset-profile diagnostic, but it no longer decides whether a user enters semantic inference.

General lesson: **metadata needed to interpret an observation does not automatically belong in the eligibility policy**. Timezone answers which local clock to use; abstention should come from task-relevant evidence such as history, recurrence, share, margin and repeated dates.

## 2026-09-24 — DBSCAN eps improves coverage without controlling cluster diameter

The final rerun over all 5,821 timezone-resolved stays makes the DBSCAN trade-off explicit.

As eps increases from 10 m to 200 m, users with a recurring location increase from 78 to 104, but spatial compactness degrades quickly:

```text
eps 30m  → 90 recurring users, 0 clusters >200m, max diameter ~181m
eps 50m  → 94 recurring users, 6 clusters >200m, max ~249m
eps 100m → 97 recurring users, 24 clusters >200m, max ~441m
eps 200m → 104 recurring users, 86 clusters >200m, max ~837m
```

The key lesson is that `eps=200m` constrains local neighbor connectivity, not total cluster diameter. Chaining can join many short links into a very wide recurring location.

DBSCAN therefore remains useful as a coverage benchmark, while complete-link clustering is better suited to a contract that needs a directly interpretable maximum-diameter threshold.

## 2026-09-26 — 03a: heterogeneous structure matters more than a simple Home/Office assumption

Behavior-first EDA 03a is closed as an evidence checkpoint, not a production redesign. Among 136 users with CP1 stays, the anchor distribution is 19 dominant, 13 two-anchor, 72 multiple-anchor, and 32 no-stable-anchor. Most stay-bearing users therefore do not directly fit a simple `HOME anchor → OFFICE anchor` worldview.

The schedule result is a useful negative finding. Although 46 users meet support requirements, within-user weekly JSD has median 1.000 (IQR 0.652–1.000), which is not lower than the 0.904 between-user comparator or the 1.000 shuffled-week null. The current metric does not establish personalized schedule structure, so 09–17 should not be replaced with per-user hours on JSD evidence alone.

The next hypothesis is the 23 mobile-work-like candidates: all 23 have multiple anchors, all 23 abstain under frozen OFFICE, and none emits frozen OFFICE. This does not confirm an occupation or semantic WORK label, but it supports testing whether the fixed-office baseline misses a distributed-mobility regime. A 03b audit must use independent evidence—mode labels, route/transition recurrence, weekday-weekend contrast, sensitivity, and negative controls—rather than reusing construction features to validate the wrapper.

## 2026-09-27 — Runnable audit code is not automatically evidence-grade

The 03b handoff exposed a useful distinction: a script can run successfully while its outputs are still not evidence-grade.

Two early paths were invalid for scientific interpretation:

1. transportation summaries used label-window duration rather than frozen-cleaned movement segments;
2. sensitivity reused the frozen candidate cohort instead of rerunning the candidate wrapper.

The continuation fixes both before any result is interpreted. The general lesson is that an audit must verify **evidence provenance** and **the dependency actually being perturbed**, not merely that code executes.

These are engineering hardening changes only; no new behavioral conclusion is accepted until the full-release run and verification gates pass.

## 2026-09-28 — Symlinks can invalidate resolved-path privacy guards

The first Modal runner symlinked `artifacts/03a` into the persistent Volume. That was convenient operationally, but 03a intentionally validates private paths using `Path.resolve()`; after resolution the path no longer contained the approved `artifacts/03a` root and materialization correctly stopped.

The fix keeps the guard intact and removes the symlink. The runner supplies explicit persistent cache roots through environment configuration, repoints the module's approved private root, and passes explicit cache paths into materialization to avoid default-argument binding surprises.

General lesson: persistence plumbing must not silently change privacy invariants. A symlink is part of the path-security model when guards validate resolved paths.

## 2026-09-29 — DBSCAN has a second modeling assumption: MinPts

Notebook 03 studied `eps` in detail while keeping `min_samples=1` fixed. That is still an unvalidated modeling choice.

In scikit-learn DBSCAN, `min_samples` is the number of samples in an epsilon neighborhood required for a point to be a core point, including the point itself. Therefore:

```text
min_samples = 1
→ every point is core
→ no density-based noise
→ isolated stays become singleton clusters
→ connectivity is maximally permissive

higher min_samples
→ stronger local-density requirement
→ more transient/sparse stays may become noise
→ but valid sparse recurring places may also be lost
```

The downstream `stay_count >= 2` recurring-location rule is not equivalent to `min_samples=2`: the former is a post-cluster visit-count condition, while MinPts is a local epsilon-neighborhood density condition.

A later sensitivity experiment should test at least `1/2/3/5` across representative epsilon values and compare coverage, noise, compactness, chaining, and downstream recurring-user support before giving the DBSCAN benchmark a fully justified configuration.

## 2026-09-29 — Support matching must use the frozen upstream schema

03b referenced `observed_span_h` for support matching because that field exists at the point-day layer in the design, but the frozen 03a user-level feature table does not export it. The full audit therefore failed even though synthetic unit fixtures had passed.

Lessons:

- downstream audits must validate the actual upstream artifact schema rather than infer fields from a design document;
- fixtures should mirror the frozen upstream schema instead of introducing convenient fields absent from production tables;
- support balance now uses `active_days`, `usable_temporal_days`, `usable_active_days`, and `cp1_stay_count`.

Verification should also separate current-change quality from unrelated repository lint debt. Full pytest remains a regression gate, while Ruff is targeted to the 03b runner and tests.

## 2026-09-29 — A robust candidate set is not the same as a validated semantic regime

03b provides a clean example of the difference between **robustness** and **semantic validation**.

The 23-user candidate set is highly stable: anchor thresholds 100/200/300 m retain the exact same cohort; ±10% mobility thresholds change only one user; ±1 weekday support leaves membership unchanged.

Independent evidence is weaker:

- aggregate observation support remains materially different between matched A/B groups;
- transportation labels cover only 6/23 A users, 12/23 B users, and 3/16 C users;
- motorized distance share is similar across A/B/C;
- median recurrent route-edge count is zero in both A and B;
- A has more transitions and higher edge entropy, but those describe mobility complexity rather than work semantics.

Lesson: high membership stability shows that a descriptive wrapper is robust around the tested thresholds. It does not manufacture external or independent semantic evidence. The appropriate decision remains `mixed evidence`, not a validated distributed-work class.

## 2026-09-29 — When matched users still differ in exposure, control at the user-day level

03b matched all 23 A/B pairs, but aggregate observation support remained materially different. User-level matching therefore did not fully remove observation confounding.

03b.1 controls exposure at the user-day level:

```text
for each A/B pair
→ stratify weekday/weekend
→ take the smaller usable-day count in each stratum
→ downsample the better-observed side
→ recompute metrics
→ repeat by bootstrap
```

Route analysis independently uses controlled `usable_for_motif` days. The transportation subset controls matched labeled hours. This asks a narrower question: do A/B differences persist when both sides contribute comparable observed exposure?

Lesson: per-day normalization is useful but can still leave support imbalance. Pairwise exposure control directly tests that confounding mechanism.

## 2026-09-29 — Narrow eligibility joins avoid hidden schema collisions

03b.1 failed because both the clustered stay table and the daily eligibility table carried `local_weekday`. A merge on `user_id + local_date` therefore produced suffixed weekday columns, while downstream code still requested the unsuffixed field.

The better fix is not to pick one suffix. The daily table is only an eligibility gate for `usable_for_motif`, so the join now carries only `user_id + local_date`; weekday is derived deterministically from `local_date`.

Lesson: when a merge exists only to filter eligibility, keep the join payload minimal. Narrow joins reduce collision risk and make data provenance easier to reason about.

## 2026-09-29 — Statistically valid bootstrap code can still be operationally unusable

The first 03b.1 bootstrap design was conceptually valid but operationally slow because every repetition refiltered/copied pandas frames, while the transport path also rebuilt DataFrames and iterated segments with `iloc`.

The optimized implementation preserves the same experiment while:

- prefiltering each A/B pair once;
- sampling only pair-local frames;
- precomputing compact NumPy transport arrays once per user;
- using vectorized permutation/cumulative-duration sampling for matched labeled hours;
- emitting stage/pair progress.

Lesson: reproducible research code also needs observable progress and sufficiently efficient execution to support actual reruns.

## 2026-09-29 — Exposure-controlled 03b.1 result

After equalizing usable-day exposure within each A/B pair, Group A still shows higher movement magnitude: about +22.9 km/day cleaned distance and +0.74 h/day movement proxy.

Route evidence is narrower: edge entropy is higher by about 0.232 with a 95% bootstrap interval above zero, while recurrent-edge difference is zero and transition/day plus distinct-edge/day intervals touch zero.

Appropriate interpretation: observation imbalance does not fully explain the behavioral difference, but current evidence supports only a descriptive mobility-complexity cohort. Home/Office semantics remain unchanged.

## 2026-09-29 — A mentor demo should preserve the reasoning chain, not just charts

After 03a → 03b → 03b.1, the audit trail had become too fragmented for a clean review conversation. A separate narrative notebook now reuses validated caches instead of rerunning raw data.

The mentor-facing structure is:

```text
question
→ why it matters
→ measurement
→ result
→ what cannot be concluded
→ decision
```

This keeps research findings separate from semantic claims. The 23-user set is shown as a robust mobility-complexity cohort while explicitly showing why recurrent-route evidence and transport coverage are insufficient for a mobile-work label.

Lesson: reproducibility notebooks and communication notebooks serve different purposes. The former optimize for auditability; the latter should preserve provenance while making the reasoning and decision trace easy to follow.

## 2026-09-29 — Case maps should illustrate aggregate findings, not replace them

The mentor demo is easier to understand with real spatial cases, but visual case selection can easily become cherry-picking.

03c visual v2 therefore uses deterministic selection: archetype users nearest the class median active-day support, and an A/B pair whose Group A edge entropy is nearest the Group A median plus its actual matched control.

The notebook shows raw public GeoLife IDs, cached CP1 stays, recurring L* locations, chronological stay paths, daily mobility timelines, and L* transition heatmaps.

Lesson: a case visualization answers what a measured pattern looks like; whether the pattern exists at population level still comes from sensitivity, matched controls, and exposure-controlled bootstrap evidence.

## 2026-09-29 — Demo notebooks should not assume derived caches already exist

03c initially assumed the full 03a `summary.json` existed on the Modal Volume. In practice, 03b can reuse the frozen stay and point-day caches without ever persisting the complete 03a derived bundle.

The corrected design separates two cache layers:

```text
expensive frozen inputs
= stays + point-day metrics

cheap derived demo artifacts
= summary + user features + audit tables
```

If the derived layer is missing, the demo rebuilds it from frozen inputs instead of rescanning raw trajectories. This makes the mentor notebook more self-contained while keeping reruns practical.

## 2026-09-29 — Cloning a repository does not make its src package importable

03c cloned the repository successfully on a fresh Modal runtime but failed when importing `analysis/03a...` because that module imports `geolife`, while the project had not yet been installed and `src/` was not on Python's import path.

Lesson: notebook setup must follow `checkout -> install project -> add import paths -> import analysis helpers`. A source tree existing under `/tmp/geolife` does not by itself make `src/geolife` importable.



## 2026-10-01 — Increasing DBSCAN MinPts does not fix chaining

Notebook 04 directly tested the remaining DBSCAN assumption: `min_samples = 1/2/3/5` on the same 97-user semantic cohort.

The clearest result is at `eps=200 m`:

```text
min_samples=1
→ 73 recurring users
→ 418 recurring locations
→ 585 singleton locations
→ max diameter ~836.66 m

min_samples=2
→ still 73 recurring users
→ still 418 recurring locations
→ 585 singleton stays become noise
→ max diameter still ~836.66 m

min_samples=3/5
→ recurring-user coverage falls to 64/56
→ max diameter still ~836.66 m
```

The frozen complete-link 200 m comparator keeps the same 73 recurring users with 486 recurring locations, p95 recurring diameter ~180.95 m, maximum ~199.23 m, and zero recurring clusters above 200 m.

Lessons:

- `min_samples=2` is not equivalent to the downstream `stay_count >= 2` recurrence rule; in this run it mainly converts singleton stays into noise;
- increasing MinPts can lose coverage before it solves the representation problem;
- DBSCAN epsilon + MinPts still cannot provide a hard maximum-diameter contract because chaining follows from density connectivity;
- equal user coverage does not imply an equivalent spatial representation.

The engineering decision therefore remains complete-link 200 m for semantic Home/Office work. This is robustness evidence, not an accuracy claim, because GeoLife has no Home/Office ground truth.

Scope remains important: this follow-up runs on the 97-user semantic cohort. It does not replace the full-stay DBSCAN audit and does not directly revalidate behavior-EDA anchor counts across all 136 stay-bearing users.


## 2026-10-01 — Related-work lesson: HOME/OFFICE can be evaluated without making POI the primary validator

### Andrade, Cancela & Gama (2019) — meaningful places and DBSCAN chaining

Mining Human Mobility Data to Discover Locations and Habits builds meaningful places from stay points and recurrence without requiring an external semantic source. In its GeoLife experiment it uses 200 m / 20 min stay-point parameters; for user 004, 2,437 stay points are reduced to 50 meaningful places and the two most frequent places are interpreted as Home/Work. The paper also highlights a failure mode that matches our own audit: density-connected DBSCAN points can chain into location clusters that are too extended.

Project lesson:

- external map/POI semantics are not required to discover recurrent structure;
- spatial compactness and recurrence of visits/movements are independent evidence axes;
- paper user 004 is a sanity reference, not GeoLife-wide ground truth;
- the Stage 04 complete-link 200 m decision is methodologically consistent with the paper's chaining warning.

### Dong et al. (2022) — the spatial threshold is not the semantic classifier

The universality in urban commuting across and within cities uses 200 m / 10 min stay detection and DBSCAN MinPoint=1 for stay locations, but final HOME/WORK classification uses XGBoost with 28 features and self-reported ground truth. The feature set includes user support, weekday/weekend and day/night ratios, within-user location shares, transfer-matrix counts, and residential/work POI counts.

Project lesson:

- 200 m + recurrence is not sufficient to establish HOME/OFFICE;
- transition structure, recurrence, and observation support provide separate evidence;
- POI is auxiliary rather than the complete validation strategy;
- the paper's reported supervised HOME/WORK accuracy must not be transferred to GeoLife because we do not have its self-reported labels.

### HoWDe (2025) — separate coverage from semantic selection

HoWDe converts stop sequences into hourly bins, filters days by temporal coverage, uses proportions over observed hours rather than absolute observed time, supports sliding windows, and explicitly allows not detected. It evaluates both detected accuracy and fraction not detected, making the accuracy/retention trade-off explicit.

Project lesson:

- support gates and semantic scores should be separate concepts;
- abstention is a valid output;
- proportions over observed data are preferable to raw counts under uneven sampling;
- sliding-window inference is a strong follow-up when static assignments are unstable;
- HoWDe also states relevant limits: temporal behavior does not infer detailed semantic purpose, and a single run does not directly resolve rotating night-shift lifestyles.

### Applied decision

Stage 05 pivots from POI lookup to reliability validation:

recurring locations -> multiple semantic rankers -> split-half -> held-out -> dropout -> cross-method agreement -> schedule-sensitivity

The frozen 27 HOME / 16 OFFICE result is now only a parity comparator. New candidate coverage may be larger, but no method is treated as truth until the reliability axes are measured.


## 2026-10-01 — HOME is more stable than OFFICE; more coverage is not better semantics

Stage 05 reproduced the frozen 27 HOME / 16 OFFICE parity, but before the final production emission gate the fixed-window ranker already yields 35 HOME and 27 OFFICE candidates. The recurrence ranker can rank 73 HOME and 31 OFFICE candidates. Thus 27/16 is a conservative emission-policy outcome, not the natural ceiling of the data.

More importantly, agreement differs sharply between HOME and OFFICE.

HOME:

- fixed vs HoWDe-style: 18/19 same location = 94.7%;
- fixed vs recurrence: 29/35 = 82.9%;
- HoWDe-style vs recurrence: 17/20 = 85.0%.

OFFICE:

- fixed vs HoWDe-style remains reasonably high at 13/16 = 81.3%;
- fixed vs recurrence falls to 7/22 = 31.8%;
- HoWDe-style vs recurrence is only 3/20 = 15.0%.

Lessons:

- HOME has a strong dominant recurrent-anchor signal, so materially different assumptions often converge on the same location;
- OFFICE depends much more strongly on temporal semantics — recurrence at an alternate anchor is not sufficient evidence of a workplace;
- larger coverage is not stronger evidence: recurrence HOME covers 73 users but held-out top-1 persistence is only about 43.3%;
- reliability must be interpreted jointly with coverage.

Missing-data stress also shows relatively strong fixed-HOME robustness: after dropping 30% of stays, candidate retention is about 84.8%; recurrence HOME retains about 87.2%. HoWDe-style HOME drops to about 68.3%, indicating that the current hourly proportional implementation is more sensitive to sparse stop support in GeoLife.

## 2026-10-01 — A time shift tests assumptions, not accuracy

Shifting every local timestamp by +12 h while preserving physical locations provides a useful metamorphic stress test:

- recurrence HOME retains 100% of candidates;
- recurrence OFFICE retains about 77.4%;
- fixed HOME retains about 37.1% and fixed OFFICE 14.8%;
- HoWDe-style HOME/OFFICE retain about 25.0% / 14.3%.

This does not mean recurrence is semantically more accurate. Fixed-window and HoWDe-style methods intentionally encode clock windows, so sensitivity is part of their design.

The appropriate lessons are:

- the +12 h test measures schedule dependence;
- HOME can separate physical-anchor recurrence from circadian interpretation;
- OFFICE needs adaptive/sliding-window reasoning if atypical schedules are in scope;
- a single global time window should not be loosened merely to increase coverage.

Next decision: quantify HOME consensus/support tiers and run sliding-window/adaptive audits for unstable OFFICE/WORK assignments before changing production inference.

## 2026-10-01 — Consensus tiers should combine evidence axes, not raw scores

The three HOME rankers expose scores with different semantics:

- fixed-window uses dwell share in frozen time windows;
- HoWDe-style uses observed-hour / visited-day proportions;
- recurrence uses dwell/recurrence ranking.

Normalizing and summing those values would create a pseudo-confidence with no shared measurement scale.

Stage 05b therefore keeps separate:

```text
method convergence
split consistency
held-out top-1
30% dropout robustness
```

and uses only transparent rules to form HIGH / MEDIUM / UNCERTAIN audit tiers.

Lesson: when weak labelers are not on a common scale, consensus should be built from agreement plus independent validation axes rather than arithmetic score fusion. The resulting tier is evidence, not a calibrated probability.

## 2026-10-01 — Adaptive WORK should select the anchor before measuring clock behavior

Stage 05 showed that OFFICE assignments depend strongly on temporal assumptions. Stage 05b therefore does not construct candidates with a replacement fixed clock window.

New flow:

```text
reliable HOME
→ exclude HOME
→ sliding windows
→ recurring secondary anchor
→ persistence / switches
→ arrival-hour center & concentration
```

Clock behavior is measured after the secondary anchor is selected. This allows a physically stable anchor with shifted or changing schedules to remain visible instead of being filtered out by 09–17 at construction time.

Lesson: when the time window itself is the hypothesis under test, do not use the same window to construct the candidate and then treat that candidate as validation of the window.

## 2026-10-01 — Timezone-aware data require timezone-aware audit windows

The Stage-05b executable synthetic test caught a runtime bug that syntax checks could not: `arrival_time_local` is timezone-aware, while the first sliding-window boundaries were created from Python dates and were timezone-naive.

The fix derives normalized boundaries directly from timezone-aware semantic timestamps:

```text
min/max arrival_time_local
→ normalize()
→ pd.date_range()
```

Lesson: research notebooks need at least one executable synthetic path. Syntactically valid datetime code can still violate timezone semantics.

## 2026-10-01 — Strong consensus sharply contracts expansion: 73 recurring HOME candidates become only 2 new review cases

Stage 05 showed that recurrence can rank HOME for 73 users. Stage 05b then required convergence across methods plus independent reliability axes.

Unique winner results: HIGH 21, MEDIUM 4, UNCERTAIN 42.

Among the 25 HIGH/MEDIUM winners:
- 23 are already production HOME emissions;
- only 2 are not emitted;
- both are still fixed-window HOME candidates that failed only the final share/margin emission gate;
- no HIGH/MEDIUM winner comes from the much broader outside-fixed-candidate set.

Lesson: broad candidate coverage is useful for testing the ceiling, but multi-axis reliability can sharply contract the credible expansion set. High recurrence coverage does not justify moving production HOME from 27 toward 73.

Also, 23/27 production HOME emissions appear as HIGH/MEDIUM unique consensus winners. The remaining four emissions should not be called wrong; they simply have weaker convergent evidence under this audit.

## 2026-10-01 — Sliding-window secondary-anchor persistence is not WORK semantics

Among 25 users with HIGH/MEDIUM HOME evidence, the primary 42-day audit gives 9 stable secondary anchors, 3 multi-anchor, 1 unstable and 12 insufficient.

The first limitation is support: nearly half of the cohort is insufficient at the primary operating point.

The second limitation is semantic convergence. The dominant adaptive anchor matches fixed OFFICE for 40.0% of comparable users, HoWDe-style OFFICE for 28.6%, and recurrence OFFICE for 54.5%.

Thus persistent non-HOME recurrence is real behavioral evidence, but it is not enough to establish workplace semantics.

At a 0.70 stability threshold: 28d -> 10 sufficient / 6 stable; 42d -> 13 / 9; 56d -> 14 / 10.

Longer windows mainly increase usable observation support. They do not create a semantic breakthrough; fixed-OFFICE agreement remains around 40%.

Lesson: window-size sensitivity must separate more observation support from better semantic identification. An increase in stable-count alone is not an accuracy gain.

Decision: if WORK research continues, restrict it to the stable-secondary subset and add independent transition/weekday/arrival evidence. Do not tune another persistence threshold and rename it OFFICE.


## 2026-10-01 — When recurrence selects the candidate, the next validation step should use different evidence

Stage 05b selected stable secondary anchors mainly through persistence / recurrence across sliding windows. Reusing active-day share or dominant-window share as Stage-05c validation would mostly self-validate the construction rule.

Stage 05c therefore moves to four different axes:

- weekday-versus-weekend contrast;
- direct HOME ↔ secondary transition regularity;
- arrival-time concentration;
- dwell-duration regularity.

Lesson: candidate construction and validation should be feature-separated as much as possible. Without ground truth, reusing the same signal to generate and validate a candidate can manufacture false confidence.

## 2026-10-01 — Same-user peers are preferable to another global threshold for a small audit

Stage 05c contains only nine stable-secondary users. With small N and strong user heterogeneity, introducing new cutoffs such as arrival concentration > X or weekday share > Y would be arbitrary.

The audit instead asks whether the selected anchor stands out relative to the user's other recurring non-HOME anchors.

Outputs are within-user percentile, top-1 evidence axes, and candidate-minus-peer-median differences.

Lesson: for strongly personalized mobility behavior, relative within-user evidence is often more defensible than another global cutoff. At least one supported peer is required; otherwise top-1 would be a vacuous result.

## 2026-10-01 — Secondary-anchor persistence does not imply convergent commute-like regularity

Stage 05c tested the nine stable-secondary users from Stage 05b with evidence different from the primary candidate-selection rule. Only seven users had at least one sufficiently supported recurring non-HOME peer for a fair within-user comparison.

Primary result:

- weekday-weekend contrast: 5/7 candidate anchors ranked top-1;
- direct HOME<->secondary transition-day share: 3/7 top-1;
- arrival-time concentration: 0/7 top-1;
- dwell-duration regularity: 0/7 top-1.

Most importantly, no user ranked top-1 on >=3/4 axes. One user reached two axes; six reached only zero or one.

Paired bootstrap intervals for all four candidate-minus-peer-median metrics crossed zero. Weekday contrast and HOME-pair transitions had a positive direction, but N=7 was too small and the evidence did not converge.

Lesson: persistence across sliding windows is a separate property. It does not automatically imply arrival regularity, dwell regularity, or transition dominance. Keep stable_secondary_anchor as a behavioral state rather than promote it to OFFICE.

## 2026-10-01 — Apply related work to the project's current state, not as a greenfield architecture

The deep-research report recommends Trackintel as a backbone, HoWDe for robust HOME/WORK inference, then habit/change detection downstream. That architecture is sensible from scratch, but this project already has deeply audited CP1 cleaning/stays and complete-link locations.

The appropriate integration now is:

- do not replace the frozen CP1/CP2 backbone with Trackintel;
- use Trackintel as an external comparator and tracking-quality reference where useful;
- formalize coverage-before-change-detection;
- pivot toward meaningful routines, OD habits, and behavior change because those questions do not require forcing a secondary anchor into WORK semantics;
- use commute distance, OD entropy, transition and mode changes as supporting signals;
- treat the change-detection repository as research code to refactor/test rather than importing its defaults as truth.

General lesson: literature integration must respect accumulated validation debt. A mature external library is not automatically worth replacing an already-audited pipeline if the replacement destroys comparability with prior experiments.


## 2026-10-01 — Routines can be represented by OD + time without WORK semantics

After Stage 05c, forcing a persistent secondary anchor into OFFICE semantics no longer produced strong convergent evidence. Stage 06 changes the unit of analysis from semantic place to behavioral routine:

```text
supported daily sequence
→ directed OD edge
→ recurrence
→ local departure-time habit
```

Lessons:

- a directed OD pair can repeat even when the exact whole-day motif changes because of an extra or missing stop;
- exact motifs are a strict comparator, not the only useful representation;
- recurrence and clock regularity should remain separate evidence axes rather than be fused into a pseudo-confidence;
- clock time is cyclic: 23:30 and 00:30 must be treated as close, so ordinary linear averages are inappropriate;
- sequence order should use UTC timestamps, while departure habits should use the origin's local clock;
- support gates must run before routine mining so missing observation is not converted into behavioral absence.

For edges with sufficient transitions, Stage 06 fits 1–3 departure-time modes after circular unwrapping and uses BIC only as a descriptive multimodality tool. The number of modes is a temporal pattern, not an occupation or trip-purpose label.

Only if routine coverage and split-half stability are adequate should Stage 07 perform behavioral change detection on this representation.

## 2026-10-01 — An importable source tree does not imply complete runtime dependencies

The first Stage-06 Modal run hit a case where `geolife` was importable from `/tmp/geolife/src`, but `timezonefinder` was not installed.

The old setup only ran `pip install -e .` when the main package import failed. Because the source tree was already on `sys.path`, that branch was skipped and `resolve_stay_timezones()` failed later.

Lessons:

- notebook setup must check runtime dependencies actually required by imported helpers, not only whether the main package imports;
- adding a source tree to `sys.path` can make the package import successfully while leaving its environment partially installed;
- dependency checks should be idempotent: install when missing and skip when present.

Stage 06 now checks for `timezonefinder==9.0.0` explicitly before importing the Stage-03a behavior helper.


## 2026-10-01 — Top-1 instability is not distribution instability

Stage 06 found that only 6/45 users kept the same dominant OD across chronological halves. But top-1 identity is brittle: a 40%/38% edge mix can become 38%/40% with almost no meaningful distribution shift.

Stage 06b therefore moves primary stability evidence to:

- Jensen-Shannon divergence;
- weighted Jaccard;
- total variation;
- top-3 overlap.

Lesson: before calling a rank swap behavioral change, inspect the full distribution.

## 2026-10-01 — Change detection needs a sampling-variability null

Sparse observation can make first and second halves look different even when there is no real temporal change.

Stage 06b builds a within-user null:

```text
chronological split
vs
200 random balanced day partitions
```

If chronological JSD is not larger than random partitions, instability may be explained by support/sampling. If it exceeds the random p95, the temporal ordering contains stronger drift-like evidence worth carrying into Stage 07.

This is still not a labeled real-world event.

## 2026-10-01 — High circular concentration with N=2 is weak routine evidence

Stage 06 showed high median departure concentration, but many repeated edges occurred on only two days. Two similar departure times can yield concentration near one while uncertainty remains large.

Stage 06b bootstraps at the active-day level:

```text
one circular mean / edge-day
→ resample days
→ concentration interval
```

Support count and lower confidence bound must therefore be interpreted together with the point estimate.

## 2026-10-01 — GMM multimodality needs evidence beyond BIC

The permissive Stage-06 GMM modeled only 11 edges from 2 users, yet 8 selected three components. That is easy to over-interpret under small N.

Stage 06b calls a result strict multimodal only when all are satisfied:

- >=5 active days;
- >=8 transitions;
- ΔBIC >=10 versus one mode;
- every component weight >=0.20;
- centers separated by >=2 hours.

Lesson: model-selection criteria do not replace minimum support and component-interpretability checks.
