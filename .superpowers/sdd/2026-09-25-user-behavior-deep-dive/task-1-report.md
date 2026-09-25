# Tasks 1–2 Implementation Report

## Status

Implemented both approved tasks in the current isolated worktree. The runner is limited to private `artifacts/03a/` outputs and does not modify CP1 implementation, production HomeOffice code, API behavior, or `notebooks/03_home_office_baseline.ipynb`.

## Files changed

- `.gitignore`: ignores `/artifacts/03a/`.
- `analysis/03a_user_behavior_deep_dive.py`: adds the private runner scaffold, frozen CP1 constants, private-path protection, ZIP member enumeration/parsing, per-trajectory frozen CP1 processing, point-day aggregate calculation, atomic cache checkpoints, cache reconciliation, and materialization CLI.
- `tests/test_user_behavior_deep_dive.py`: covers private-path rejection, expected frozen reconciliation, release-universe validation, frozen processing on a synthetic trajectory, and rebuilding invalid cache checkpoints.

## Behavior

- Uses the exact frozen CP1 values: 10 m same-second radius, 300 s maximum gap, 1,200 km/h speed guard, 200 m stay distance, and 1,200 s stay dwell.
- Enumerates sorted numeric `Data/<user>/Trajectory/*.plt` ZIP members.
- Materializes only private stay rows (with source lineage) and private user-day cleaned-point aggregates. No raw point cache is written.
- Checkpoints both caches atomically every 500 trajectory files.
- Accepts a cache hit only when reconciliation passes: 5,821 stays, 136 stay users, and 182 release users. Invalid caches are rebuilt.
- Local-day fields currently use the UTC timestamps produced by the frozen input stage. Timezone-local behavioral conversion is intentionally deferred to the later timezone-aware task.
- Pandas pickle caches are loaded only from the local `artifacts/03a/` paths written by this runner; the code documents that untrusted pickles must not be used.

## Verification

Focused tests and lint passed:

```text
python -m pytest tests/test_user_behavior_deep_dive.py -v
6 passed in 0.76s

ruff check analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py
All checks passed!
```

Relevant full suite passed:

```text
python -m pytest
53 passed in 6.17s
```

Repository-wide `ruff check .` was attempted after the full suite. It fails on 31 pre-existing violations in unchanged notebooks and existing tests, including `notebooks/01_geolife_eda.ipynb`, `notebooks/03_home_office_baseline.ipynb`, and `tests/test_api.py`; the new runner and test files pass focused Ruff.

The required full materialization command was not run, per task constraint:

```text
python analysis/03a_user_behavior_deep_dive.py --stage materialize --zip "data/Geolife Trajectories 1.3.zip"
```

## Scope/concerns

- No full pass was run on the 313 MB ZIP. Therefore the code path is unit-tested but the required release reconciliation output has not been independently observed in this task.
- Task 2’s stated full-materialization verification and exact 5,821/136 release result remain for the later permitted materialization task.
- No cache or derived user artifact has been created outside ignored `artifacts/03a/`.

## Scoped review fixes

- `ensure_private_artifact_path()` now resolves the candidate and private root before containment validation, rejecting normalized traversal such as `artifacts/03a/../leak.pkl`.
- Final cache materialization aggregates all per-PLT partials to exactly one `(user_id, local_date)` row. It explicitly sums point/transition/movement metrics, takes daily temporal bounds for span and first/last hour, takes the maximum largest gap, unions covered hours, and validates that no duplicate key remains.
- Distance and movement-duration proxy include only positive-time adjacent pairs in the same CP1 `sequence_id`; segment pairs across CP1 boundaries are excluded.
- `transition_count` uses the complete `clean_trajectory_with_audit()` event stream rather than retained-row `boundary_before_reason`. Each audit event is allocated to the UTC-local calendar day of the event timestamp, so discarded terminal events are counted.
- The execution branch still tracks `.superpowers/sdd/2026-09-25-user-behavior-deep-dive/task-1-report.md`, `docs/superpowers/plans/2026-09-25-user-behavior-deep-dive.md`, and `docs/superpowers/specs/2026-09-25-user-behavior-deep-dive-design.md`; none was deleted or modified.

### Fix verification

```text
python -m pytest tests/test_user_behavior_deep_dive.py -v
11 passed in 3.14s

python -m pytest
58 passed in 7.75s

python -m ruff check analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py
All checks passed!

git -c core.whitespace=cr-at-eol diff --check
(exit 0; required because the existing test file uses CRLF)
```
