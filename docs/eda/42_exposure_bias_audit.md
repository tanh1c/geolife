# Stage 08b — Observation-density / exposure-bias audit

## Purpose

Stage 08b tests whether the frozen global HOME/OFFICE gates interact with
heterogeneous observation exposure across users.

The production contract remains:

~~~text
HOME = 27
OFFICE = 16
~~~

Stage 08b is diagnostic only. It does not introduce adaptive thresholds.

## Motivation

A single global gate currently applies to users with very different observation
histories.

Examples:

- a user may have many stays but very little nighttime coverage;
- another may have only two well-observed HOME nights;
- a dense user may have many recurring locations, making share or margin harder
  to satisfy even when absolute support is strong.

Therefore raw trajectory count is not enough.

The audit focuses on behavior-window exposure:

- HOME opportunity dates: dates with at least 600 seconds observed inside the
  local 21:00–06:00 HOME window;
- OFFICE opportunity dates: weekdays with at least 600 seconds observed inside
  the local 09:00–17:00 OFFICE window.

## User exposure profile

For each of the 136 frozen stay users, Stage 08b computes:

- total stays;
- active local dates;
- observation span;
- total dwell;
- recurring-location count;
- HOME opportunity dates and hours;
- OFFICE opportunity dates and hours;
- production HOME/OFFICE status.

Positive-exposure users are stratified separately for HOME and OFFICE into:

- SPARSE;
- MEDIUM;
- DENSE.

ZERO exposure remains a separate group.

The positive regimes are percentile-based thirds used only for descriptive
comparison. They are not candidate thresholds.

## Gate decomposition

The production gate is decomposed per user and label into:

~~~text
no_observed_opportunity
no_recurring_candidate
min_dates_blocked
share_blocked
margin_blocked
share_and_margin_blocked
emitted
~~~

This makes it possible to distinguish sparse-user support limitations from
share/margin failures.

## Unconstrained top candidate

For diagnostics only, Stage 08b also ranks the top recurring location without
applying the minimum-date requirement.

This allows cases such as:

~~~text
observed HOME opportunity dates = 2
raw top candidate dates = 2
raw candidate coverage = 2/2
production min_dates = 3
=> min_dates_blocked
~~~

Such a case is exposure-limited under the global gate. It is not automatically
a correct HOME label.

## Regime-level audit

For HOME and OFFICE separately, Stage 08b reports by exposure regime:

- users;
- median stays;
- median active dates;
- median opportunity dates;
- raw-candidate coverage;
- eligible-candidate coverage;
- production emission rate;
- min-date failure count;
- share failure count;
- margin failure count.

A material SPARSE-to-DENSE emission gradient is evidence that observation
density affects coverage.

It is not by itself proof of an inappropriate or unfair threshold.

## Exposure-limited summary

Among users blocked by the absolute minimum-date rule, Stage 08b counts:

- how many raw top candidates cover all observed behavior-window opportunity
  dates;
- how many cover at least 80% of observed opportunity dates.

This specifically tests the concern that a user can have internally consistent
but sparse observations that cannot satisfy an absolute global date threshold.

## Continuous associations

Spearman rank correlations are reported for:

- total stays vs emission;
- opportunity dates vs emission;
- opportunity dates vs raw top share;
- opportunity dates vs eligible candidate share;
- opportunity dates vs eligible candidate margin.

Interpretation:

- positive opportunity→emission association is consistent with an
  exposure-sensitive coverage gate;
- negative opportunity→share/margin association would be consistent with
  dilution among denser users.

These are descriptive associations, not causal estimates.

## Independent-method coverage by exposure

Stage-05 candidate assignments are reused:

- fixed-window;
- HoWDe-style;
- recurrence.

For each HOME/OFFICE exposure regime, Stage 08b reports:

- method selection rate;
- exact fixed-vs-alternate candidate agreement where both select.

If alternate semantic methods continue selecting plausible candidates in sparse
regimes while fixed-window selection collapses, the low production coverage
cannot be explained solely by absence of semantic signal.

## Stage-08a HOME expansion concentration

The five measured HOME_PROBABLE candidates from Stage 08a are joined to HOME
exposure regimes.

This tests whether the validated expansion cases concentrate in sparse/medium
users or instead appear among dense users that may experience share/margin
dilution.

## Stage-07j OFFICE near-miss concentration

The nine audited OFFICE near misses are joined to OFFICE exposure regimes.

This helps separate:

- low exposure / support-date limitation;
- dense-user share/margin limitation.

No near-miss promotion occurs in Stage 08b.

## Bias-hypothesis snapshot

Stage 08b creates a compact descriptive table containing:

- SPARSE emission rate;
- DENSE emission rate;
- Spearman(opportunity dates, emission);
- min-date-blocked users;
- min-date-blocked users whose raw top candidate covers all observed
  opportunities.

The stage intentionally does not output a causal binary verdict such as
"biased" or "not biased".

## Outputs

Private:

- \`user_exposure_profiles_private.pkl\`;
- \`gate_diagnostics_private.pkl\`.

Aggregate:

- \`input_gate.csv\`;
- \`exposure_profile_summary.csv\`;
- \`gate_by_exposure_regime.csv\`;
- \`exposure_limited_summary.csv\`;
- \`exposure_association_summary.csv\`;
- \`method_coverage_by_exposure_regime.csv\`;
- \`method_agreement_by_exposure_regime.csv\`;
- \`home_expansion_by_exposure_regime.csv\`;
- \`office_near_miss_by_exposure_regime.csv\`;
- \`bias_hypothesis_snapshot.csv\`.

Cache root:

~~~text
/mnt/geolife-data/cache/cp2_v2/08b_exposure_bias_audit/
~~~

## Decision boundary

Stage 08b does not modify production thresholds.

If measured evidence shows a strong exposure gradient together with corroborated
sparse-user semantic candidates, the next stage can predeclare and test an
exposure-aware policy against the frozen global baseline.

If the gradient is weak, the low HOME/OFFICE emission count should not be
attributed primarily to observation-density bias.


## Measured result

Stage 08b reran successfully on `main` at `0ef6107`.

The executed notebook contains no traceback and all aggregate/private outputs
were saved.

### Exposure profiles

The 136 stay users span a very wide observation range:

| metric | min | median | max |
| --- | ---: | ---: | ---: |
| total stays | 1 | 16 | 470 |
| active local dates | 1 | 8 | 138 |
| observation span days | 1 | 68 | 1885 |
| recurring locations | 0 | 3 | 34 |
| HOME opportunity dates | 0 | 2.5 | 34 |
| OFFICE opportunity dates | 0 | 2 | 52 |

Regime counts:

| label | ZERO | SPARSE | MEDIUM | DENSE |
| --- | ---: | ---: | ---: | ---: |
| HOME | 34 | 34 | 34 | 34 |
| OFFICE | 39 | 38 | 25 | 34 |

### Gate outcomes

HOME:

| gate status | users |
| --- | ---: |
| min_dates_blocked | 45 |
| no_observed_opportunity | 34 |
| emitted | 27 |
| no_recurring_candidate | 15 |
| share_and_margin_blocked | 8 |
| share_blocked | 7 |

OFFICE:

| gate status | users |
| --- | ---: |
| min_dates_blocked | 50 |
| no_observed_opportunity | 39 |
| no_recurring_candidate | 17 |
| emitted | 16 |
| share_blocked | 8 |
| margin_blocked | 3 |
| share_and_margin_blocked | 3 |

### Emission gradient by exposure regime

| label | SPARSE | MEDIUM | DENSE |
| --- | ---: | ---: | ---: |
| HOME | 0.0% | 32.4% | 47.1% |
| OFFICE | 0.0% | 20.0% | 32.4% |

Median opportunity dates move from 1 in SPARSE to 15 in DENSE for both label
families.

### Exposure-limited support

Among users blocked only because no location reaches the absolute minimum-date
eligibility floor:

| label | min-date blocked | raw top covers 100% observed opportunities | raw top coverage >=80% |
| --- | ---: | ---: | ---: |
| HOME | 45 | 13 | 13 |
| OFFICE | 50 | 14 | 14 |

The median opportunity-date count among these blocked users is 3 for both HOME
and OFFICE.

This is evidence of exposure sensitivity, not semantic correctness.

### Continuous associations

Spearman rho:

| label | metric | rho |
| --- | --- | ---: |
| HOME | total stays vs emission | +0.462 |
| HOME | opportunity dates vs emission | +0.484 |
| HOME | opportunity dates vs raw top share | -0.356 |
| HOME | opportunity dates vs eligible share | -0.535 |
| HOME | opportunity dates vs eligible margin | -0.597 |
| OFFICE | total stays vs emission | +0.326 |
| OFFICE | opportunity dates vs emission | +0.406 |
| OFFICE | opportunity dates vs raw top share | -0.631 |
| OFFICE | opportunity dates vs eligible share | -0.303 |
| OFFICE | opportunity dates vs eligible margin | -0.224 |

The positive exposure-emission gradient coexists with negative
exposure-concentration gradients.

### Independent-method coverage

HOME SPARSE:

- fixed-window: 0/34;
- HoWDe-style: 0/34;
- recurrence: 25/34.

HOME MEDIUM:

- fixed-window: 14/34;
- HoWDe-style: 7/34;
- recurrence: 34/34.

HOME DENSE:

- fixed-window: 28/34;
- HoWDe-style: 19/34;
- recurrence: 34/34.

Where both fixed-window and recurrence select, exact HOME agreement remains
high:

- MEDIUM: 13/14;
- DENSE: 22/28.

OFFICE SPARSE:

- fixed-window: 0/38;
- HoWDe-style: 0/38;
- recurrence: 0/38.

OFFICE DENSE:

- fixed-window: 25/34;
- HoWDe-style: 22/34;
- recurrence: 28/34.

Dense OFFICE agreement is method-sensitive:

- fixed vs HoWDe: 14/17 exact;
- fixed vs recurrence: 4/22 exact.

### Stage-08a HOME expansion concentration

All five HOME_PROBABLE cases are DENSE:

| tier | regime | candidates | median HOME opportunity dates | median stays | median active dates | median exact external families |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| HOME_PROBABLE | DENSE | 5 | 32 | 255 | 90 | 3 |

This contradicts a simple theory that the HOME-27 shortfall is mainly caused by
sparse users.

For the strongest corroborated HOME expansion cases, dense-user
share/margin dilution is the more relevant mechanism.

### Stage-07j OFFICE near-miss concentration

All nine OFFICE near misses are DENSE:

| group | regime | users | median OFFICE opportunity dates | median stays | median active dates |
| --- | --- | ---: | ---: | ---: | ---: |
| margin_near | DENSE | 2 | 28.5 | 209 | 44 |
| share_near | DENSE | 7 | 19 | 106 | 54 |

This strongly associates the known OFFICE near-miss set with dense observation,
not sparse support.

### Interpretation

Stage 08b supports an exposure-sensitive global gate, but the failure mechanism
is bimodal:

```text
SPARSE
→ absolute support / min_dates limitation

DENSE / mobile
→ enough support dates
→ lower candidate share and margin
→ concentration dilution
```

The two semantic labels also differ.

Sparse HOME retains schedule-light recurrence signal, whereas sparse OFFICE does
not receive candidates from fixed-window, HoWDe-style, or recurrence.

Therefore one generic adaptive rule for both labels is not justified.

### Decision

Do not change production HOME 27 / OFFICE 16 from Stage 08b alone.

The next policy experiment should compare predeclared, label-specific
exposure-aware rules against the frozen baseline:

- sparse/support-limited HOME: exposure-normalized support should be tested
  conservatively and require independent corroboration;
- dense HOME: test concentration-aware alternatives to absolute share/margin;
- OFFICE: prioritize dense share/margin adaptation first; sparse OFFICE has
  insufficient corroborating evidence for relaxed support rules.

Any additional outputs should remain separate confidence tiers until their
robustness is demonstrated.
