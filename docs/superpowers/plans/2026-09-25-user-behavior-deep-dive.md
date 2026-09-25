# User Behavior Deep-Dive EDA Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reproducible, privacy-safe behavior-first GeoLife EDA that explains schedule/mobility heterogeneity and frozen CP2 v1 abstention modes before any model redesign.

**Architecture:** One runner module materializes frozen CP1 stay and cleaned-point daily caches privately, then derives three separate views: frozen CP2 v1 comparator, all-resolved stay recurrence/dwell, and cleaned-point movement/observation quality. Pure aggregation helpers are unit-tested with synthetic data; the runner validates full-release reconciliation, emits private artifacts, aggregate summary, figures, and a committed aggregate report without touching CP1, production Home/Office code, or notebook 03.

**Tech Stack:** Python 3.11+, pandas, NumPy, scikit-learn, matplotlib, existing GeoLife CP1/CP2 production APIs, stdlib `zipfile`/`hashlib`/`zoneinfo`; existing notebook-only `timezonefinder==9.0.0` only if already available, otherwise fail with an explicit installation instruction.

## Global Constraints

- Reuse frozen CP1 exactly: same-second 10 m, gap 300 s, speed guard 1,200 km/h, stay 200 m, dwell 1,200 s.
- Do not modify `src/geolife/staypoints/`, `src/geolife/model/home_office.py`, API code, or `notebooks/03_home_office_baseline.ipynb`.
- Begin comparator reporting from all 182 release users; assert 5,821 stays across 136 users with stays and frozen parity of 27 HOME / 16 OFFICE emissions.
- Main behavior view uses per-stay IANA local time; label it exploratory, distinct from frozen CP2 v1.
- Stays support recurrence/dwell/anchors; cleaned points support movement/travel/observation-quality only.
- User-level artifacts are private under `artifacts/03a/`, ignored by Git, and must contain no latitude or longitude in exported CSVs.
- Reports/figures use `Case A…` aliases and deterministic `L0…` location IDs, never raw user IDs or coordinates.
- No accuracy, occupation, true Home/Work, favorite/hobby, or frozen-new-rule claims.

---

## File Structure

| File | Responsibility |
| --- | --- |
| `analysis/03a_user_behavior_deep_dive.py` | Main runnable EDA and pure aggregation functions; materializes private caches, computes features, writes figures/CSV/JSON/report inputs. |
| `tests/test_user_behavior_deep_dive.py` | Synthetic tests for comparator rejection ordering, daily observation quality, deterministic locations/motifs, stability eligibility, privacy, and provenance. |
| `reports/03a_user_behavior_deep_dive.md` | Committed aggregate report answering Q1–Q10. Generated deterministically from summary values after a full run; no user IDs/coordinates. |
| `.gitignore` | Ignore `artifacts/03a/` private materialization, figures, user-level tables, and case alias mapping. |

## Common data contracts

```python
from pathlib import Path
from typing import TypedDict
import pandas as pd

class FrozenConfig(TypedDict):
    same_second_radius_m: float
    max_gap_s: float
    hard_speed_guard_kmh: float
    stay_distance_threshold_m: float
    stay_min_dwell_s: float

FROZEN_CP1: FrozenConfig = {
    "same_second_radius_m": 10.0,
    "max_gap_s": 300.0,
    "hard_speed_guard_kmh": 1200.0,
    "stay_distance_threshold_m": 200.0,
    "stay_min_dwell_s": 1200.0,
}

STAY_COLUMNS = [
    "user_id", "source_file", "sequence_id", "arrival_time_utc",
    "departure_time_utc", "duration_s", "latitude", "longitude", "n_points",
]

POINT_DAY_COLUMNS = [
    "user_id", "local_date", "point_count", "observed_span_h", "largest_gap_h",
    "has_large_gap", "cleaned_distance_km", "movement_duration_h",
    "boundary_count", "first_local_hour", "last_local_hour",
    "usable_for_temporal_profile",
]
```

---

### Task 1: Add private artifact exclusion and runner scaffold

**Files:**
- Create: `analysis/03a_user_behavior_deep_dive.py`
- Create: `tests/test_user_behavior_deep_dive.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces `FROZEN_CP1`, `ARTIFACT_DIR`, `STAY_CACHE`, `POINT_DAY_CACHE`, and `ensure_private_artifact_path(path: Path) -> None`.
- Later tasks import these constants and write only beneath `artifacts/03a/`.

- [ ] **Step 1: Write the failing privacy-path test**

```python
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

spec = spec_from_file_location(
    "user_behavior_deep_dive", Path("analysis/03a_user_behavior_deep_dive.py")
)
assert spec and spec.loader
behavior = module_from_spec(spec)
spec.loader.exec_module(behavior)


def test_private_artifact_path_rejects_paths_outside_03a() -> None:
    with pytest.raises(ValueError, match="artifacts/03a"):
        behavior.ensure_private_artifact_path(Path("reports/leak.csv"))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py::test_private_artifact_path_rejects_paths_outside_03a -v`

Expected: FAIL because the analysis module does not exist.

- [ ] **Step 3: Create minimal module and ignore rule**

```python
# analysis/03a_user_behavior_deep_dive.py
from pathlib import Path

ARTIFACT_DIR = Path("artifacts/03a")
STAY_CACHE = ARTIFACT_DIR / "stays_baseline_v1.pkl"
POINT_DAY_CACHE = ARTIFACT_DIR / "cleaned_point_daily_metrics.pkl"


def ensure_private_artifact_path(path: Path) -> None:
    if ARTIFACT_DIR not in (path, *path.parents):
        raise ValueError("private artifacts must be written beneath artifacts/03a")
```

Append to `.gitignore`:

```gitignore
# Private behavior-first EDA materialization and user-level profiles
/artifacts/03a/
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py::test_private_artifact_path_rejects_paths_outside_03a -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py .gitignore
git commit -m "chore(eda): scaffold private behavior audit"
```

### Task 2: Materialize and validate frozen CP1 inputs

**Files:**
- Modify: `analysis/03a_user_behavior_deep_dive.py`
- Modify: `tests/test_user_behavior_deep_dive.py`

**Interfaces:**
- Consumes ZIP member streams and `FROZEN_CP1`.
- Produces `materialize_frozen_cp1(zip_path: Path, stay_cache: Path, point_day_cache: Path) -> tuple[pd.DataFrame, pd.DataFrame]`.
- Produces `validate_materialization(stays: pd.DataFrame, point_days: pd.DataFrame, release_users: set[str]) -> None`.
- Stay cache follows `STAY_COLUMNS`; point-day cache follows `POINT_DAY_COLUMNS` plus local-time fields needed later.

- [ ] **Step 1: Write failing reconciliation tests with a synthetic ZIP fixture**

```python
def test_validate_materialization_rejects_wrong_frozen_stay_reconciliation() -> None:
    stays = pd.DataFrame({"user_id": ["001"]})
    point_days = pd.DataFrame({"user_id": ["001"]})

    with pytest.raises(AssertionError, match="5,821 stays"):
        validate_materialization(stays, point_days, {"000", "001"})


def test_validate_materialization_requires_182_release_users() -> None:
    stays = make_stays(5821, users=136)
    point_days = make_point_days(users=136)

    with pytest.raises(AssertionError, match="182 release users"):
        validate_materialization(stays, point_days, {"001"})
```

`make_stays` and `make_point_days` are test-local helpers that provide all required columns with harmless literal values.

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k materialization -v`

Expected: FAIL because `validate_materialization` is undefined.

- [ ] **Step 3: Implement one-file CP1 materialization**

```python
def process_trajectory(user_id: str, source_file: str, raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    cleaned, audit = clean_trajectory_with_audit(raw, **FROZEN_CLEANING_KWARGS)
    stays = detect_staypoints(cleaned, **FROZEN_STAY_KWARGS)
    # Add user_id/source_file only; do not alter detector fields.
    # Build point-day rows from cleaned points and audit, not from stays.
    return stay_rows, point_day_rows
```

The implementation must:

1. enumerate numeric `Data/<user>/Trajectory/*.plt` members from the ZIP in sorted order;
2. parse each PLT with existing `read_plt` semantics or an equivalent 6-header-line reader that produces UTC timestamps;
3. call production cleaning/detection functions using exact frozen kwargs;
4. checkpoint both private caches atomically every 500 trajectory files;
5. cache-hit only after `validate_materialization` passes;
6. preserve `source_file` only in private stay cache;
7. assert 5,821 stays, 136 stay users, and 182 release users before accepting the final caches.

- [ ] **Step 4: Run unit tests and a cache-only smoke check**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k materialization -v`

Expected: PASS.

Run after a full materialization: `python analysis/03a_user_behavior_deep_dive.py --stage materialize --zip "data/Geolife Trajectories 1.3.zip"`

Expected final console line: `validated 5821 stays across 136 users; release universe 182 users`.

- [ ] **Step 5: Commit**

```bash
git add analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py
git commit -m "feat(eda): materialize frozen behavior inputs"
```

### Task 3: Build observation-quality and cleaned-point mobility metrics

**Files:**
- Modify: `analysis/03a_user_behavior_deep_dive.py`
- Modify: `tests/test_user_behavior_deep_dive.py`

**Interfaces:**
- Consumes cleaned trajectory points with `timestamp`, `latitude`, `longitude`, `sequence_id`, and `boundary_before_reason`.
- Produces `summarize_cleaned_point_days(cleaned: pd.DataFrame, timezone_id: str) -> pd.DataFrame` with `POINT_DAY_COLUMNS`.
- Produces `classify_day_quality(point_day: pd.DataFrame) -> pd.DataFrame`.

- [ ] **Step 1: Write failing tests for point-level distance and quality gates**

```python
def test_cleaned_point_day_distance_uses_adjacent_cleaned_points_not_stays() -> None:
    cleaned = cleaned_points([
        ("2026-01-01T00:00:00Z", 39.9000, 116.4000, 0),
        ("2026-01-01T01:00:00Z", 39.9100, 116.4000, 0),
        ("2026-01-01T02:00:00Z", 39.9200, 116.4000, 0),
    ])

    row = summarize_cleaned_point_days(cleaned, "Asia/Shanghai").iloc[0]
    assert row["cleaned_distance_km"] > 2.0
    assert row["point_count"] == 3


def test_day_quality_marks_sparse_or_gappy_day_not_usable() -> None:
    day = pd.DataFrame([{
        "point_count": 2, "observed_span_h": 1.0, "largest_gap_h": 7.0,
    }])

    result = classify_day_quality(day).iloc[0]
    assert not result["usable_for_temporal_profile"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "point_day or day_quality" -v`

Expected: FAIL because helpers are undefined.

- [ ] **Step 3: Implement cleaned-point aggregation**

Use `haversine_m` for positive-time adjacent points only within the same `sequence_id`; do not bridge a CP1 boundary. Compute local date/hour through the already resolved per-point IANA timezone. For each user/date populate:

```python
usable_temporal = point_count >= 3 and observed_span_h >= 2.0 and largest_gap_h <= 6.0
usable_motif = stay_count >= 1 and stay_observed_span_h >= 2.0
```

Record `movement_duration_h` as the sum of positive segment durations, capped to the observed daily span; name it `movement_duration_proxy_h` if it is not exact moving time. Record `boundary_count` from CP1 boundaries and never label it as behavioral error.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "point_day or day_quality" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py
git commit -m "feat(eda): measure point-level observation quality"
```

### Task 4: Resolve local time and construct deterministic recurrence views

**Files:**
- Modify: `analysis/03a_user_behavior_deep_dive.py`
- Modify: `tests/test_user_behavior_deep_dive.py`

**Interfaces:**
- Consumes private CP1 stays.
- Produces `resolve_stay_timezones(stays: pd.DataFrame) -> pd.DataFrame` with `timezone_id`, `arrival_time_local`, `departure_time_local`, `local_date`, `local_weekday`.
- Produces `cluster_behavior_locations(stays: pd.DataFrame, threshold_m: float) -> tuple[pd.DataFrame, pd.DataFrame]`.
- Produces `relabel_locations_deterministically(clustered: pd.DataFrame) -> pd.DataFrame` where per-user `location_id` is rank-by-dwell/stay-count/first-arrival/internal-key.

- [ ] **Step 1: Write failing deterministic-label and timezone tests**

```python
def test_location_ids_rank_dwell_before_first_seen() -> None:
    stays = local_stays([
        ("A", "2026-01-01T01:00:00Z", 39.90, 116.40, 3600),
        ("A", "2026-01-02T01:00:00Z", 39.90, 116.40, 3600),
        ("A", "2026-01-01T02:00:00Z", 39.91, 116.40, 1200),
    ])

    clustered, _ = cluster_behavior_locations(stays, 200.0)
    top_id = clustered.groupby("location_id")["duration_s"].sum().idxmax()
    assert top_id == 0


def test_resolved_local_time_retains_non_beijing_stay_when_timezone_resolves() -> None:
    stays = local_stays([("A", "2026-01-01T01:00:00Z", 35.6762, 139.6503, 1200)])

    result = resolve_stay_timezones(stays)
    assert result.loc[0, "timezone_id"] == "Asia/Tokyo"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "location_ids or resolved_local" -v`

Expected: FAIL because helpers are undefined.

- [ ] **Step 3: Implement per-stay timezone and clustering adapters**

Use `TimezoneFinder(in_memory=True).timezone_at(lng=..., lat=...)` and `ZoneInfo` for all resolved stays. If `timezonefinder` cannot import, raise exactly:

```python
RuntimeError("timezonefinder==9.0.0 is required for all-resolved behavior EDA; install it before running --stage behavior")
```

For 100/200/300 m, call `AgglomerativeClustering(metric="precomputed", linkage="complete", distance_threshold=threshold_m, n_clusters=None)` per user on Haversine distance matrices. Sort/relabel each cluster as specified; output location IDs and summaries without coordinates in artifacts.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "location_ids or resolved_local" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py
git commit -m "feat(eda): build all-timezone recurrence view"
```

### Task 5: Derive coverage, temporal, schedule, and motif features

**Files:**
- Modify: `analysis/03a_user_behavior_deep_dive.py`
- Modify: `tests/test_user_behavior_deep_dive.py`

**Interfaces:**
- Consumes resolved stays, deterministic 200 m locations, and point-day rows.
- Produces `build_user_behavior_features(...) -> pd.DataFrame`, `build_user_day_features(...) -> pd.DataFrame`, `compute_schedule_stability(...) -> pd.DataFrame`, and `build_daily_motifs(...) -> pd.DataFrame`.

- [ ] **Step 1: Write failing eligibility and motif tests**

```python
def test_schedule_stability_requires_weeks_days_and_dwell_in_each_half() -> None:
    daily = usable_days([
        ("A", "2026-01-01", 2.0), ("A", "2026-01-08", 2.0),
        ("A", "2026-01-15", 2.0),
    ])

    stability = compute_schedule_stability(daily)
    assert stability.loc[0, "schedule_status"] == "insufficient"


def test_daily_motif_uses_deterministic_location_ids_only() -> None:
    stays = motif_stays([
        ("A", "2026-01-01", 0), ("A", "2026-01-01", 1), ("A", "2026-01-01", 0),
    ])

    motifs = build_daily_motifs(stays)
    assert motifs.loc[0, "motif"] == "L0→L1→L0"
    assert "latitude" not in motifs.columns
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "schedule_stability or daily_motif" -v`

Expected: FAIL because helpers are undefined.

- [ ] **Step 3: Implement feature derivation**

Implement dwell-weighted 24-hour, weekday-hour, and weekend-hour arrays as private serializable structures; public CSV uses scalar entropy/concentration/peak summaries only. Compute:

- coverage and usable-day totals;
- semantic/recurring location counts; top 1/2/3 shares and normalized entropy;
- radius/spread and distance-to-top-anchor quantiles;
- weekday/weekend local dwell proportions;
- JSD early-vs-late and weekly JSD, plus `schedule_status` only after the global minimum support controls;
- user-day stays/recurring locations/dwell joined to point-level distance/proxies;
- motif frequency, entropy, and weekday/weekend stability.

Use empirical quantiles for descriptive low/high JSD wrappers only after computing continuous JSD. Store the quantile cutpoints and counts in `summary.json`; do not create production constants.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "schedule_stability or daily_motif" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py
git commit -m "feat(eda): profile behavior and daily motifs"
```

### Task 6: Reproduce frozen comparator funnel and sensitivity conclusions

**Files:**
- Modify: `analysis/03a_user_behavior_deep_dive.py`
- Modify: `tests/test_user_behavior_deep_dive.py`

**Interfaces:**
- Consumes all 182 user IDs, frozen stays, and unchanged `HomeOfficeConfig`.
- Produces `build_baseline_user_audit(release_users: set[str], stays: pd.DataFrame) -> pd.DataFrame` with exactly one HOME and one OFFICE reason per user.
- Produces `run_location_sensitivity(...) -> pd.DataFrame` for 100/200/300 m primary conclusions.

- [ ] **Step 1: Write failing ordering and full-universe tests**

```python
def test_baseline_audit_keeps_user_without_stay_in_full_release_universe() -> None:
    audit = build_baseline_user_audit({"000", "001"}, stays_for_user("001"))

    missing = audit.query("user_id == '000' and label == 'HOME'").iloc[0]
    assert missing["reject_reason"] == "no_cp1_stay"


def test_baseline_audit_prefers_no_overlap_before_insufficient_dates() -> None:
    audit = build_baseline_user_audit({"001"}, recurring_daytime_only_stays("001"))

    home = audit.query("label == 'HOME'").iloc[0]
    assert home["reject_reason"] == "no_behavioral_window_overlap"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "baseline_audit" -v`

Expected: FAIL because `build_baseline_user_audit` is undefined.

- [ ] **Step 3: Implement explicit frozen-v1 funnel without changing model code**

Reconstruct intermediate location/window values in analysis code using frozen config and the same public CP2 primitives. Apply reason order exactly:

```python
REASON_ORDER = (
    "no_cp1_stay",
    "outside_frozen_v1_geographic_scope",
    "no_recurring_location",
    "no_behavioral_window_overlap",
    "insufficient_relevant_dates",
    "share_below_frozen_gate",
    "margin_below_frozen_gate",
    "emitted",
)
```

Assert per-label reason uniqueness, all 182×2 rows present, and emitted labels reconcile directly with `infer_home_office()` to 27 HOME and 16 OFFICE. Keep only IDs/metrics in private audit; no coordinates.

For 100/200/300 m, calculate anchor count class, top-anchor stability relative to 200 m, recurring count, motif membership stability, and regime membership stability. Use a three-row aggregate sensitivity table in summary/report.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "baseline_audit" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py
git commit -m "feat(eda): audit baseline abstention funnel"
```

### Task 7: Build regime, outlier, and private case-study selection

**Files:**
- Modify: `analysis/03a_user_behavior_deep_dive.py`
- Modify: `tests/test_user_behavior_deep_dive.py`

**Interfaces:**
- Consumes feature table, user-day table, baseline audit, and sensitivity table.
- Produces `assign_behavioral_candidates(...) -> pd.DataFrame`, `build_outlier_audit(...) -> pd.DataFrame`, and `select_case_studies(...) -> pd.DataFrame`.

- [ ] **Step 1: Write failing tests for coherent rarity and alias privacy**

```python
def test_repeated_high_mobility_is_rare_but_coherent_not_data_quality_noise() -> None:
    features = candidate_features(
        weekday_usable_days=6, weekday_distance_km=42.0,
        weekday_mobility_repeatability=0.9, recurring_daytime_locations=3,
        office_dominant=False,
    )

    result = assign_behavioral_candidates(features).iloc[0]
    assert result["mobile_work_like_candidate"]
    assert result["outlier_interpretation"] == "rare_but_coherent"


def test_case_studies_export_aliases_without_user_ids_or_coordinates() -> None:
    cases = select_case_studies(candidate_case_features(), seed=42)

    assert cases["case_alias"].iloc[0] == "Case A"
    assert "user_id" not in cases.columns
    assert not {"latitude", "longitude"}.intersection(cases.columns)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "coherent or case_studies" -v`

Expected: FAIL because functions are undefined.

- [ ] **Step 3: Implement descriptive candidate and case selection rules**

Require usable-day/stability support for shifted/mobile candidates. Use empirical cohort quantiles for high mobility/spread thresholds and write the selected values to summary provenance. Do not assign every user a regime; retain `unknown_or_insufficient`.

Outlier audit includes `outlier_type`, `user_count`, `repeatable_user_count`, `likely_data_quality_issue`, `likely_behavioral_pattern`, and `needs_manual_review`. CP1 boundary reasons remain data-quality events; large mobility/late activity/many anchors are behavioral rarity until evidence says otherwise.

Select 12–20 deterministic cases across required groups. Store private mapping `case_alias,user_id,selection_reason`; generated figure/report inputs expose only alias and `L*` IDs.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "coherent or case_studies" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py
git commit -m "feat(eda): identify coherent behavior candidates"
```

### Task 8: Write private artifacts, aggregate report, figures, and provenance

**Files:**
- Modify: `analysis/03a_user_behavior_deep_dive.py`
- Create: `reports/03a_user_behavior_deep_dive.md`
- Modify: `tests/test_user_behavior_deep_dive.py`

**Interfaces:**
- Consumes all task outputs.
- Produces the private artifact set and committed report.
- Produces `write_outputs(results: AnalysisResults, root: Path) -> None` and `render_report(summary: dict[str, object]) -> str`.

- [ ] **Step 1: Write failing report/privacy/provenance tests**

```python
def test_exported_user_csvs_exclude_precise_coordinates(tmp_path: Path) -> None:
    results = minimal_analysis_results_with_coordinates()
    write_outputs(results, tmp_path)

    exported = pd.read_csv(tmp_path / "artifacts/03a/user_behavior_features.csv")
    assert "latitude" not in exported.columns
    assert "longitude" not in exported.columns


def test_report_answers_all_required_questions_without_raw_user_ids() -> None:
    report = render_report(minimal_summary())

    for heading in ("Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10"):
        assert heading in report
    assert "user_id" not in report
    assert "accuracy" not in report.lower()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "exported_user_csvs or report_answers" -v`

Expected: FAIL because output functions are undefined.

- [ ] **Step 3: Implement output generation**

Write private files only below `artifacts/03a/`:

```text
stays_baseline_v1.pkl
cleaned_point_daily_metrics.pkl
user_behavior_features.csv
baseline_user_audit.csv
outlier_audit.csv
archetype_candidates.csv
case_studies.csv
summary.json
figures/
```

Before every CSV write, drop `latitude`, `longitude`, `source_file`, raw timestamps, and raw `user_id` from case/report-facing exports. Keep user IDs in private audit/features only as needed for reproducibility. The committed report contains aggregate tables/figure references and aliases only.

Generate private case figures: hour dwell histogram, weekday-hour heatmap, top `L*` dwell shares, daily cleaned-point distance/proxy, and daily motif sequence. Do not render maps.

`summary.json` contains reconciliation, comparator counts, quality coverage, continuous/sensitivity metrics, regime counts, outlier counts, POI feasibility, exact configuration, SHA-256 of `data/Geolife Trajectories 1.3.zip`, git SHA, package versions, timezonefinder/tzdata versions if resolvable, and seed.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest tests/test_user_behavior_deep_dive.py -k "exported_user_csvs or report_answers" -v`

Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py reports/03a_user_behavior_deep_dive.md
git commit -m "docs(eda): report user behavior deep dive"
```

### Task 9: Run full release EDA and verify reproducibility

**Files:**
- Modify: `reports/03a_user_behavior_deep_dive.md` only if rendered aggregate values change from placeholder-free template output
- Modify: `tests/test_user_behavior_deep_dive.py` only if a concrete full-release invariant reveals an untested condition

**Interfaces:**
- Consumes local ZIP and all previous runner functions.
- Produces validated private artifacts and a complete aggregate report.

- [ ] **Step 1: Run full materialization and behavior pipeline**

Run:

```bash
python analysis/03a_user_behavior_deep_dive.py \
  --zip "data/Geolife Trajectories 1.3.zip" \
  --stage all \
  --seed 42
```

Expected: validated 5,821 stays / 136 users with stays / 182 release users; 27 HOME and 16 OFFICE frozen-v1 emissions; all private artifact paths printed.

- [ ] **Step 2: Run the full test suite**

Run: `python -m pytest -q`

Expected: PASS with no failures.

- [ ] **Step 3: Verify private artifacts and report boundaries**

Run:

```bash
python - <<'PY'
from pathlib import Path
import pandas as pd
root = Path("artifacts/03a")
for name in [
    "user_behavior_features.csv", "baseline_user_audit.csv", "outlier_audit.csv",
    "archetype_candidates.csv", "case_studies.csv",
]:
    frame = pd.read_csv(root / name)
    assert not {"latitude", "longitude"}.intersection(frame.columns), name
print("private CSV coordinate check passed")
PY
git check-ignore artifacts/03a/user_behavior_features.csv
git diff --check
```

Expected: all coordinate checks pass; artifact path is ignored; no whitespace errors.

- [ ] **Step 4: Inspect report completeness manually**

Check `reports/03a_user_behavior_deep_dive.md` has all 14 required sections plus explicit Q1–Q10 answers, cites table/figure paths for every numerical claim, uses aliases only, and ends with the user-requested final-response headings.

- [ ] **Step 5: Commit report/source only**

```bash
git add analysis/03a_user_behavior_deep_dive.py tests/test_user_behavior_deep_dive.py reports/03a_user_behavior_deep_dive.md .gitignore
git commit -m "chore(eda): complete behavior-first audit"
```

Do not stage anything under `artifacts/03a/`, the raw ZIP, extracted data, caches, maps, or coordinate-bearing files.

## Plan Self-Review

### Spec coverage

- Frozen CP1 reuse/reconciliation: Tasks 2 and 9.
- Full 182-user baseline comparator with corrected ordering and 27/16 parity: Task 6.
- Cleaned-point movement separate from stay recurrence: Tasks 2–3 and 5.
- Observation-quality/day completeness and dual all/usable reporting: Tasks 3 and 5.
- All-resolved local-time behavioral view: Task 4.
- 100/200/300 m targeted sensitivity: Task 6.
- Continuous JSD with minimum support before wrappers: Task 5.
- Regimes, mobile/shifted/outlier/POI feasibility: Task 7.
- Case aliases, deterministic `L*`, privacy and provenance: Tasks 4, 7, 8, and 9.
- Q1–Q10 report and requested final headings: Tasks 8–9.
- No production/notebook 03 change: Global Constraints and file list.

### Placeholder scan

No unresolved placeholders, TODOs, or unspecified signatures remain. Commands, paths, expected outputs, contract columns, reason ordering, and support thresholds are explicit.

### Type consistency

All later tasks consume outputs declared in the preceding task interfaces. Stays feed recurrence/dwell, cleaned points feed movement/quality, and joins use `user_id` plus local date. The report consumes aggregate summary and aliases rather than coordinates or raw users.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-25-user-behavior-deep-dive.md`. Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — Execute tasks in this session using `superpowers:executing-plans`, batch execution with checkpoints.

Which approach?