# Task 6 Comparator Funnel Report

## Scope

Implemented the frozen CP2 v1 comparator audit in the private EDA runner only. Production model code remains unchanged.

## Implementation

`analysis/03a_user_behavior_deep_dive.py` now provides:

- `REASON_ORDER` with the required mutually exclusive ordering:
  1. `no_cp1_stay`
  2. `outside_frozen_v1_geographic_scope`
  3. `no_recurring_location`
  4. `no_behavioral_window_overlap`
  5. `insufficient_relevant_dates`
  6. `share_below_frozen_gate`
  7. `margin_below_frozen_gate`
  8. `emitted`
- `build_baseline_user_audit(release_users, stays)`, which produces exactly one HOME and one OFFICE row per release user, excludes coordinates from audit rows, reconstructs frozen window evidence without modifying the model, and reconciles emitted `(user_id, label)` pairs directly with `infer_home_office()`.
- `run_location_sensitivity(stays)`, which returns exactly three aggregate rows for complete-link thresholds 100, 200, and 300 m. Each row contains anchor-count-class totals, top-anchor membership stability relative to 200 m, recurring-location count, and motif-membership stability relative to 200 m. Regime stability is deliberately omitted until Task 7 supplies the classifier.
- A `--stage comparator` runner mode. When intentionally run against the full frozen cache/ZIP, it asserts the 182-user × 2 audit universe and frozen parity of 27 HOME and 16 OFFICE labels.

The comparator uses the frozen `HomeOfficeConfig`, `build_semantic_locations`, and `infer_home_office` as the model interfaces. Its intermediate window aggregation is local to the EDA analysis so the production model remains untouched.

## Test coverage

Added synthetic tests that do not require the release ZIP or cache:

- all users remain present in the audit, including a user with no CP1 stay;
- zero behavioral-window overlap is selected before insufficient date support;
- nonzero overlap with only two relevant dates is classified as `insufficient_relevant_dates`;
- sensitivity always includes 100/200/300 m and all five specified primary-conclusion columns;
- top-anchor stability detects membership changes between 100 m and the 200 m baseline.

## Verification

Passed:

- `python -m pytest tests/test_user_behavior_deep_dive.py -v` — 29 passed.
- `python -m pytest -q` — exit status 0.
- `python -m ruff check analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py` — all checks passed.
- Production-model diff check for `src/geolife/model/home_office.py` — no changes.

## Full-run status

The requested no-full-ZIP-run constraint was honored. Therefore the full-cache assertions for 182×2 rows and 27 HOME/16 OFFICE are implemented but have not been executed in this milestone. They will execute when `--stage comparator` is run locally with the release ZIP and valid frozen CP1 cache.

## Deliberate scope boundary

Regime classification is Task 7 work. Regime-membership stability is deliberately omitted until the Task 7 classifier exists. No production behavior, location threshold, semantic decision, or model configuration was changed.

## Re-review fix round 2

- Local-hour dwell allocation now considers both timezone-aware resolutions of the next local hour and selects only a boundary later than the current absolute timestamp. A stay spanning `America/New_York`'s repeated fall-back hour terminates and assigns 5,400 seconds to local hour 1 and 1,800 seconds to local hour 2.

```text
RED: timeout 15s python -c "import os, pytest; os.chdir('C:/Users/LG/Desktop/Study Material/VSF/geolife/.claude/worktrees/eda-user-behavior-deep-dive'); raise SystemExit(pytest.main(['tests/test_user_behavior_deep_dive.py', '-q']))"
(exit 124 after 33 passed; the new fall-back regression reproduced the non-advancing allocation loop)

GREEN: python -m pytest tests/test_user_behavior_deep_dive.py -q
35 passed

python -m pytest -q
82 passed

python -m ruff check analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py
All checks passed!

git -c core.whitespace=cr-at-eol diff --check
(exit 0)
```
