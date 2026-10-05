"""Stage 07o: literature comparator suite on frozen CP1/CP2-v2.

Comparators:
- scikit-mobility 1.3.1 home_location source-equivalent HOME replica;
- Kabiri et al. (arXiv:2302.14742) hierarchical geohash HOME, adapted from raw
  sightings to frozen stay-hour occupancy observations;
- Pavan et al. (MDM 2015) area/intensity/frequency feature-space audit;
- SCITEPRESS/MATEC 2018 work-rest HOME/WORK ranker, adapted to frozen locations.

Diagnostic only: no comparator is ground truth and no output retunes production.
"""

from __future__ import annotations

from math import pi

import numpy as np
import pandas as pd

from geolife.geo.distance import haversine_m


_GEOHASH_BASE32 = "0123456789bcdefghjkmnpqrstuvwxyz"


def _local_naive(value: object) -> pd.Timestamp:
    ts = pd.Timestamp(value)
    return ts if ts.tzinfo is None else ts.tz_localize(None)


def build_location_centered_stays(
    semantic_stays: pd.DataFrame,
    locations: pd.DataFrame,
) -> pd.DataFrame:
    required_stay = {
        "user_id", "location_id", "arrival_time_local",
        "departure_time_local", "duration_s",
    }
    required_loc = {"user_id", "location_id", "latitude", "longitude"}
    missing = required_stay.difference(semantic_stays.columns)
    if missing:
        raise ValueError(f"missing semantic stay columns: {sorted(missing)}")
    missing = required_loc.difference(locations.columns)
    if missing:
        raise ValueError(f"missing location columns: {sorted(missing)}")

    loc = locations[list(required_loc)].copy()
    loc["user_id"] = loc["user_id"].astype(str)
    loc["location_id"] = pd.to_numeric(loc["location_id"], errors="raise").astype(int)

    out = semantic_stays[
        ["user_id", "location_id", "arrival_time_local",
         "departure_time_local", "duration_s"]
    ].copy()
    out["user_id"] = out["user_id"].astype(str)
    out["location_id"] = pd.to_numeric(out["location_id"], errors="raise").astype(int)
    out = out.merge(loc, on=["user_id", "location_id"], how="left", validate="many_to_one")
    if out[["latitude", "longitude"]].isna().any().any():
        raise RuntimeError("location-centered stays failed to join coordinates")
    return out


def build_stay_arrival_observations(
    semantic_stays: pd.DataFrame,
    locations: pd.DataFrame,
) -> pd.DataFrame:
    base = build_location_centered_stays(semantic_stays, locations)
    return pd.DataFrame({
        "user_id": base["user_id"].astype(str),
        "location_id": base["location_id"].astype(int),
        "datetime": base["arrival_time_local"].map(_local_naive),
        "latitude": pd.to_numeric(base["latitude"], errors="raise"),
        "longitude": pd.to_numeric(base["longitude"], errors="raise"),
    }).sort_values(["user_id", "datetime"], kind="stable").reset_index(drop=True)


def build_stay_hour_observations(
    semantic_stays: pd.DataFrame,
    locations: pd.DataFrame,
) -> pd.DataFrame:
    """Each stay contributes one observation per touched local hour."""
    base = build_location_centered_stays(semantic_stays, locations)
    rows: list[dict[str, object]] = []
    for row in base.itertuples(index=False):
        start = pd.Timestamp(row.arrival_time_local)
        end = pd.Timestamp(row.departure_time_local)
        if end < start:
            raise ValueError("departure precedes arrival")
        start_floor = start.floor("h")
        stamps = [start_floor] if end == start else list(
            pd.date_range(start_floor, end.floor("h"), freq="h")
        )
        for stamp in stamps:
            naive = _local_naive(stamp)
            rows.append({
                "user_id": str(row.user_id),
                "location_id": int(row.location_id),
                "datetime": naive,
                "local_date": naive.date(),
                "year_month": naive.strftime("%Y-%m"),
                "hour": int(naive.hour),
                "latitude": float(row.latitude),
                "longitude": float(row.longitude),
            })
    return pd.DataFrame(rows).sort_values(
        ["user_id", "datetime", "location_id"], kind="stable"
    ).reset_index(drop=True)


def scikit_mobility_home_replica(
    arrival_observations: pd.DataFrame,
    *,
    start_night: str = "22:00",
    end_night: str = "07:00",
) -> pd.DataFrame:
    """Source-equivalent scikit-mobility 1.3.1 home_location rule."""
    required = {"user_id", "location_id", "datetime", "latitude", "longitude"}
    missing = required.difference(arrival_observations.columns)
    if missing:
        raise ValueError(f"missing arrival observation columns: {sorted(missing)}")

    start = pd.Timestamp(f"2000-01-01 {start_night}").time()
    end = pd.Timestamp(f"2000-01-01 {end_night}").time()

    def is_night(ts: pd.Timestamp) -> bool:
        t = pd.Timestamp(ts).time()
        if start <= end:
            return start <= t <= end
        return t >= start or t <= end

    rows = []
    for user_id, group in arrival_observations.groupby("user_id", sort=True):
        night = group.loc[group["datetime"].map(is_night)]
        selected = night if len(night) else group
        counts = (
            selected.groupby(["latitude", "longitude"], sort=True)
            .size()
            .sort_values(ascending=False, kind="stable")
        )
        lat, lon = counts.index[0]
        loc_ids = group.loc[
            group["latitude"].eq(lat) & group["longitude"].eq(lon), "location_id"
        ]
        rows.append({
            "method": "SCIKIT_MOBILITY_1_3_1_HOME",
            "user_id": str(user_id),
            "label": "HOME",
            "location_id": int(loc_ids.min()),
            "latitude": float(lat),
            "longitude": float(lon),
            "night_observations": int(len(night)),
            "used_fallback_all_visits": bool(len(night) == 0),
        })
    return pd.DataFrame(rows)


def geohash_encode(latitude: float, longitude: float, precision: int = 7) -> str:
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    bits = [16, 8, 4, 2, 1]
    chars: list[str] = []
    bit = 0
    ch = 0
    even = True
    while len(chars) < precision:
        interval = lon_interval if even else lat_interval
        value = longitude if even else latitude
        mid = (interval[0] + interval[1]) / 2.0
        if value >= mid:
            ch |= bits[bit]
            interval[0] = mid
        else:
            interval[1] = mid
        even = not even
        if bit < 4:
            bit += 1
        else:
            chars.append(_GEOHASH_BASE32[ch])
            bit = 0
            ch = 0
    return "".join(chars)


def geohash_center(code: str) -> tuple[float, float]:
    lat_interval = [-90.0, 90.0]
    lon_interval = [-180.0, 180.0]
    even = True
    for char in str(code):
        value = _GEOHASH_BASE32.index(char)
        for mask in [16, 8, 4, 2, 1]:
            interval = lon_interval if even else lat_interval
            mid = (interval[0] + interval[1]) / 2.0
            if value & mask:
                interval[0] = mid
            else:
                interval[1] = mid
            even = not even
    return (
        (lat_interval[0] + lat_interval[1]) / 2.0,
        (lon_interval[0] + lon_interval[1]) / 2.0,
    )


def _add_geohashes(observations: pd.DataFrame) -> pd.DataFrame:
    out = observations.copy()
    out["geohash6"] = [
        geohash_encode(float(lat), float(lon), 6)
        for lat, lon in zip(out["latitude"], out["longitude"], strict=True)
    ]
    out["geohash7"] = [
        geohash_encode(float(lat), float(lon), 7)
        for lat, lon in zip(out["latitude"], out["longitude"], strict=True)
    ]
    return out


def _geohash_stats(
    frame: pd.DataFrame,
    *,
    hash_col: str,
    denominator_days: int,
) -> pd.DataFrame:
    rows = []
    for code, group in frame.groupby(hash_col, sort=True):
        observed_days = int(group["local_date"].nunique())
        hour_keys = group[["local_date", "hour"]].drop_duplicates()
        distinct_hours = int(len(hour_keys))
        avg_daily_distinct_hours = distinct_hours / observed_days if observed_days else 0.0
        avg_hourly_sightings = len(group) / distinct_hours if distinct_hours else 0.0

        night = group.loc[group["hour"].ge(21) | group["hour"].lt(6)].copy()
        if len(night):
            night["night_date"] = [
                (pd.Timestamp(d) - pd.Timedelta(days=1)).date() if h < 6 else d
                for d, h in zip(night["local_date"], night["hour"], strict=True)
            ]
            nights = int(night["night_date"].nunique())
            night_hours = int(night["datetime"].nunique())
            avg_daily_night_hours = night_hours / nights if nights else 0.0
            avg_hourly_night_sightings = len(night) / night_hours if night_hours else 0.0
        else:
            nights = night_hours = 0
            avg_daily_night_hours = avg_hourly_night_sightings = 0.0

        rows.append({
            hash_col: str(code),
            "observed_days": observed_days,
            "denominator_days": int(denominator_days),
            "avg_daily_distinct_hours": float(avg_daily_distinct_hours),
            "avg_hourly_sightings": float(avg_hourly_sightings),
            "nights": nights,
            "night_hours": night_hours,
            "avg_daily_night_hours": float(avg_daily_night_hours),
            "avg_hourly_night_sightings": float(avg_hourly_night_sightings),
        })
    return pd.DataFrame(rows)


def _select_geohash_candidate(
    frame: pd.DataFrame,
    *,
    hash_col: str,
    denominator_days: int,
) -> tuple[str | None, pd.DataFrame]:
    stats = _geohash_stats(frame, hash_col=hash_col, denominator_days=denominator_days)
    if stats.empty:
        return None, stats
    eligible = stats.loc[
        stats["observed_days"].ge(3)
        & stats["observed_days"].gt(denominator_days / 2.0)
        & stats["avg_daily_distinct_hours"].ge(2.0)
    ].copy()
    if eligible.empty:
        return None, stats
    top3 = eligible.sort_values(
        ["observed_days", "avg_daily_distinct_hours", "avg_hourly_sightings", hash_col],
        ascending=[False, False, False, True],
        kind="stable",
    ).head(3)
    selected = top3.sort_values(
        ["nights", "avg_daily_night_hours", "avg_hourly_night_sightings", hash_col],
        ascending=[False, False, False, True],
        kind="stable",
    ).iloc[0]
    return str(selected[hash_col]), stats


def geohash2302_monthly_home(
    stay_hour_observations: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Kabiri et al. monthly level-6 -> level-7 HOME adapted to stay-hours."""
    obs = _add_geohashes(stay_hour_observations)
    monthly_rows = []
    audit_rows = []
    for (user_id, year_month), month in obs.groupby(["user_id", "year_month"], sort=True):
        observed_days = int(month["local_date"].nunique())
        level6, stats6 = _select_geohash_candidate(
            month, hash_col="geohash6", denominator_days=observed_days
        )
        audit_rows.append({
            "user_id": str(user_id),
            "year_month": str(year_month),
            "observed_days": observed_days,
            "level6_candidates": int(len(stats6)),
            "selected_geohash6": level6,
        })
        if level6 is None:
            continue
        inside = month.loc[month["geohash6"].eq(level6)].copy()
        inside_days = int(inside["local_date"].nunique())
        level7, stats7 = _select_geohash_candidate(
            inside, hash_col="geohash7", denominator_days=inside_days
        )
        if level7 is None:
            continue
        selected_stats = stats7.loc[stats7["geohash7"].eq(level7)].iloc[0]
        lat, lon = geohash_center(level7)
        monthly_rows.append({
            "user_id": str(user_id),
            "year_month": str(year_month),
            "geohash6": level6,
            "geohash7": level7,
            "latitude": float(lat),
            "longitude": float(lon),
            "observed_days": observed_days,
            "home_nights": int(selected_stats["nights"]),
            "home_night_hours": int(selected_stats["night_hours"]),
        })
    return pd.DataFrame(monthly_rows), pd.DataFrame(audit_rows)


def aggregate_geohash2302_home(monthly_candidates: pd.DataFrame) -> pd.DataFrame:
    if monthly_candidates.empty:
        return pd.DataFrame(columns=[
            "method", "user_id", "label", "geohash7", "latitude", "longitude",
            "qualifying_months", "modal_month_share",
        ])
    rows = []
    for user_id, group in monthly_candidates.groupby("user_id", sort=True):
        by_hash = (
            group.groupby("geohash7", as_index=False)
            .agg(months=("year_month", "nunique"), night_hours=("home_night_hours", "sum"))
            .sort_values(
                ["months", "night_hours", "geohash7"],
                ascending=[False, False, True],
                kind="stable",
            )
        )
        chosen = by_hash.iloc[0]
        lat, lon = geohash_center(str(chosen["geohash7"]))
        qualifying_months = int(group["year_month"].nunique())
        rows.append({
            "method": "ARXIV2302_GEOHASH_STAY_HOUR",
            "user_id": str(user_id),
            "label": "HOME",
            "geohash7": str(chosen["geohash7"]),
            "latitude": float(lat),
            "longitude": float(lon),
            "qualifying_months": qualifying_months,
            "modal_month_share": float(chosen["months"] / qualifying_months),
        })
    return pd.DataFrame(rows)


def _window_overlap_s(
    start: object,
    end: object,
    *,
    start_hour: int,
    end_hour: int,
) -> float:
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)
    if end_ts <= start_ts:
        return 0.0
    total = 0.0
    day = start_ts.date() - pd.Timedelta(days=1)
    last_day = end_ts.date()
    while day <= last_day:
        if start_hour < end_hour:
            wstart = pd.Timestamp(
                year=day.year, month=day.month, day=day.day,
                hour=start_hour, tz=start_ts.tz,
            )
            wend = pd.Timestamp(
                year=day.year, month=day.month, day=day.day,
                hour=end_hour, tz=start_ts.tz,
            )
        else:
            next_day = day + pd.Timedelta(days=1)
            wstart = pd.Timestamp(
                year=day.year, month=day.month, day=day.day,
                hour=start_hour, tz=start_ts.tz,
            )
            wend = pd.Timestamp(
                year=next_day.year, month=next_day.month, day=next_day.day,
                hour=end_hour, tz=start_ts.tz,
            )
        overlap_start = max(start_ts.tz_convert("UTC"), wstart.tz_convert("UTC"))
        overlap_end = min(end_ts.tz_convert("UTC"), wend.tz_convert("UTC"))
        if overlap_end > overlap_start:
            total += float((overlap_end - overlap_start).total_seconds())
        day += pd.Timedelta(days=1)
    return total


def scitepress_style_candidates(
    semantic_stays: pd.DataFrame,
    locations: pd.DataFrame,
) -> pd.DataFrame:
    """Top-two production regions + 00-06 HOME / 08-18 WORK dwell ranker."""
    base = build_location_centered_stays(semantic_stays, locations)
    top2 = (
        locations.sort_values(
            ["user_id", "stay_count", "location_id"],
            ascending=[True, False, True],
            kind="stable",
        )
        .groupby("user_id", as_index=False, sort=True)
        .head(2)[["user_id", "location_id", "latitude", "longitude", "stay_count"]]
        .copy()
    )
    eligible = top2.groupby("user_id")["location_id"].nunique()
    top2 = top2.loc[top2["user_id"].isin(eligible.loc[eligible.ge(2)].index)].copy()

    rows = []
    for row in base.itertuples(index=False):
        rows.append({
            "user_id": str(row.user_id),
            "location_id": int(row.location_id),
            "home_00_06_s": _window_overlap_s(
                row.arrival_time_local, row.departure_time_local,
                start_hour=0, end_hour=6,
            ),
            "work_08_18_s": _window_overlap_s(
                row.arrival_time_local, row.departure_time_local,
                start_hour=8, end_hour=18,
            ),
        })
    dwell = (
        pd.DataFrame(rows)
        .groupby(["user_id", "location_id"], as_index=False)[
            ["home_00_06_s", "work_08_18_s"]
        ]
        .sum()
    )
    candidates = top2.merge(
        dwell, on=["user_id", "location_id"], how="left", validate="one_to_one"
    ).fillna({"home_00_06_s": 0.0, "work_08_18_s": 0.0})

    output = []
    for user_id, group in candidates.groupby("user_id", sort=True):
        home = group.sort_values(
            ["home_00_06_s", "stay_count", "location_id"],
            ascending=[False, False, True], kind="stable",
        ).iloc[0]
        work = group.sort_values(
            ["work_08_18_s", "stay_count", "location_id"],
            ascending=[False, False, True], kind="stable",
        ).iloc[0]
        same = int(home["location_id"]) == int(work["location_id"])
        for label, selected, score_col in [
            ("HOME", home, "home_00_06_s"),
            ("OFFICE", work, "work_08_18_s"),
        ]:
            output.append({
                "method": "SCITEPRESS_WORK_REST_STYLE",
                "user_id": str(user_id),
                "label": label,
                "location_id": int(selected["location_id"]),
                "latitude": float(selected["latitude"]),
                "longitude": float(selected["longitude"]),
                "window_dwell_h": float(selected[score_col] / 3600.0),
                "same_home_work_candidate": bool(same),
            })
    return pd.DataFrame(output)


def pavan_feature_space(
    locations: pd.DataFrame,
    production_output: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Area/intensity/frequency feature audit; no invented composite classifier."""
    required = {
        "user_id", "location_id", "diameter_m", "total_dwell_h",
        "stay_count", "active_local_dates",
    }
    missing = required.difference(locations.columns)
    if missing:
        raise ValueError(f"missing production location columns: {sorted(missing)}")

    frame = locations.loc[locations["stay_count"].ge(2)].copy()
    frame["area_proxy_m2"] = pi * np.square(frame["diameter_m"].astype(float) / 2.0)
    frame["intensity_dwell_h"] = frame["total_dwell_h"].astype(float)
    frame["frequency_visits"] = frame["stay_count"].astype(int)

    emitted = production_output[["user_id", "label", "location_id"]].copy()
    label_map = (
        emitted.groupby(["user_id", "location_id"])["label"]
        .agg(lambda values: "+".join(sorted(set(map(str, values)))))
        .rename("production_role").reset_index()
    )
    frame = frame.merge(label_map, on=["user_id", "location_id"], how="left")
    frame["production_role"] = frame["production_role"].fillna("OTHER_RECURRING")
    frame["intensity_rank"] = frame.groupby("user_id")["intensity_dwell_h"].rank(
        method="min", ascending=False
    )
    frame["frequency_rank"] = frame.groupby("user_id")["frequency_visits"].rank(
        method="min", ascending=False
    )
    frame["area_percentile"] = frame.groupby("user_id")["area_proxy_m2"].rank(
        method="average", pct=True
    )

    summary = (
        frame.groupby("production_role", as_index=False)
        .agg(
            locations=("location_id", "size"),
            users=("user_id", "nunique"),
            median_area_proxy_m2=("area_proxy_m2", "median"),
            median_intensity_dwell_h=("intensity_dwell_h", "median"),
            median_frequency_visits=("frequency_visits", "median"),
            median_active_local_dates=("active_local_dates", "median"),
        )
        .sort_values("production_role", kind="stable")
    )
    labeled = frame.loc[frame["production_role"].ne("OTHER_RECURRING")].copy()
    rank_summary = (
        labeled.groupby("production_role", as_index=False)
        .agg(
            emitted_locations=("location_id", "size"),
            top1_intensity=("intensity_rank", lambda s: int(pd.Series(s).eq(1).sum())),
            top1_frequency=("frequency_rank", lambda s: int(pd.Series(s).eq(1).sum())),
            median_intensity_rank=("intensity_rank", "median"),
            median_frequency_rank=("frequency_rank", "median"),
            median_area_percentile=("area_percentile", "median"),
        )
    )
    return frame, summary, rank_summary


def exact_namespace_comparison(
    universe_users: list[str] | pd.Series,
    production_output: pd.DataFrame,
    comparator_candidates: pd.DataFrame,
    *,
    method: str,
    labels: tuple[str, ...] = ("HOME", "OFFICE"),
) -> pd.DataFrame:
    users = sorted({str(v) for v in universe_users})
    base = pd.MultiIndex.from_product(
        [users, list(labels)], names=["user_id", "label"]
    ).to_frame(index=False)
    prod = production_output[["user_id", "label", "location_id"]].copy()
    prod["user_id"] = prod["user_id"].astype(str)
    prod["label"] = prod["label"].astype(str).str.upper()
    prod = prod.rename(columns={"location_id": "production_location_id"})
    comp = comparator_candidates.loc[
        comparator_candidates["method"].eq(method),
        ["user_id", "label", "location_id"],
    ].copy()
    comp["user_id"] = comp["user_id"].astype(str)
    comp["label"] = comp["label"].astype(str).str.upper()
    comp = comp.rename(columns={"location_id": "comparator_location_id"})
    out = base.merge(prod, on=["user_id", "label"], how="left").merge(
        comp, on=["user_id", "label"], how="left"
    )
    out["method"] = method
    out["production_emitted"] = out["production_location_id"].notna()
    out["comparator_selected"] = out["comparator_location_id"].notna()
    out["exact_match"] = (
        out["production_emitted"] & out["comparator_selected"]
        & out["production_location_id"].eq(out["comparator_location_id"])
    )
    out["status"] = "neither"
    out.loc[out["exact_match"], "status"] = "both_same"
    out.loc[
        out["production_emitted"] & out["comparator_selected"] & ~out["exact_match"],
        "status",
    ] = "both_different"
    out.loc[out["production_emitted"] & ~out["comparator_selected"], "status"] = "production_only"
    out.loc[~out["production_emitted"] & out["comparator_selected"], "status"] = "comparator_only"
    return out


def spatial_home_comparison(
    universe_users: list[str] | pd.Series,
    production_output: pd.DataFrame,
    comparator_home: pd.DataFrame,
) -> pd.DataFrame:
    users = pd.DataFrame({"user_id": sorted({str(v) for v in universe_users})})
    prod = production_output.loc[
        production_output["label"].astype(str).str.upper().eq("HOME"),
        ["user_id", "latitude", "longitude"],
    ].copy()
    prod["user_id"] = prod["user_id"].astype(str)
    prod = prod.rename(columns={
        "latitude": "production_latitude", "longitude": "production_longitude"
    })
    comp = comparator_home[["user_id", "latitude", "longitude", "method"]].copy()
    comp["user_id"] = comp["user_id"].astype(str)
    comp = comp.rename(columns={
        "latitude": "comparator_latitude", "longitude": "comparator_longitude"
    })
    out = users.merge(prod, on="user_id", how="left").merge(comp, on="user_id", how="left")
    out["production_emitted"] = out["production_latitude"].notna()
    out["comparator_selected"] = out["comparator_latitude"].notna()
    out["distance_m"] = np.nan
    mask = out["production_emitted"] & out["comparator_selected"]
    if mask.any():
        out.loc[mask, "distance_m"] = haversine_m(
            out.loc[mask, "production_latitude"].to_numpy(dtype=float),
            out.loc[mask, "production_longitude"].to_numpy(dtype=float),
            out.loc[mask, "comparator_latitude"].to_numpy(dtype=float),
            out.loc[mask, "comparator_longitude"].to_numpy(dtype=float),
        )
    return out


def summarize_exact_comparison(comparison: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (method, label), group in comparison.groupby(["method", "label"], sort=True):
        prod = int(group["production_emitted"].sum())
        comp = int(group["comparator_selected"].sum())
        joint = int((group["production_emitted"] & group["comparator_selected"]).sum())
        exact = int(group["exact_match"].sum())
        rows.append({
            "method": method,
            "label": label,
            "production_emitted": prod,
            "comparator_selected": comp,
            "joint_selected": joint,
            "exact_matches": exact,
            "exact_rate_production": exact / prod if prod else np.nan,
            "exact_rate_joint": exact / joint if joint else np.nan,
        })
    return pd.DataFrame(rows)


def summarize_spatial_home(comparison: pd.DataFrame) -> pd.DataFrame:
    dist = pd.to_numeric(comparison["distance_m"], errors="coerce")
    prod = int(comparison["production_emitted"].sum())
    joint = int((comparison["production_emitted"] & comparison["comparator_selected"]).sum())
    return pd.DataFrame([{
        "method": (
            comparison["method"].dropna().iloc[0]
            if comparison["method"].notna().any()
            else "ARXIV2302_GEOHASH_STAY_HOUR"
        ),
        "production_HOME": prod,
        "comparator_selected": int(comparison["comparator_selected"].sum()),
        "joint_selected": joint,
        "within_50m": int(dist.le(50).sum()),
        "within_100m": int(dist.le(100).sum()),
        "within_200m": int(dist.le(200).sum()),
        "median_distance_m_joint": float(dist.median()) if dist.notna().any() else np.nan,
    }])


def near_miss_work_summary(
    near_miss_panel: pd.DataFrame,
    work_candidates: pd.DataFrame,
    *,
    method: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    near = near_miss_panel.loc[
        near_miss_panel["audit_group"].astype(str).ne("baseline"),
        ["user_id", "audit_group", "candidate_location_id"],
    ].copy()
    near["user_id"] = near["user_id"].astype(str)
    near["candidate_location_id"] = pd.to_numeric(
        near["candidate_location_id"], errors="raise"
    ).astype(int)
    comp = work_candidates.loc[
        work_candidates["method"].eq(method)
        & work_candidates["label"].astype(str).str.upper().eq("OFFICE"),
        ["user_id", "location_id"],
    ].copy()
    comp["user_id"] = comp["user_id"].astype(str)
    comp = comp.rename(columns={"location_id": "comparator_location_id"})
    out = near.merge(comp, on="user_id", how="left")
    out["selected"] = out["comparator_location_id"].notna()
    out["exact_match"] = out["selected"] & out["comparator_location_id"].eq(
        out["candidate_location_id"]
    )
    summary = out.groupby("audit_group", as_index=False).agg(
        users=("user_id", "size"),
        selected=("selected", "sum"),
        exact_matches=("exact_match", "sum"),
    )
    summary["method"] = method
    return out, summary


def synthetic_self_check() -> dict[str, object]:
    code = geohash_encode(38.9, -77.0, 7)
    lat, lon = geohash_center(code)
    assert abs(lat - 38.9) < 0.01
    assert abs(lon + 77.0) < 0.01
    arrivals = pd.DataFrame({
        "user_id": ["u", "u", "u"],
        "location_id": [1, 1, 2],
        "datetime": [
            pd.Timestamp("2026-01-01 23:00"),
            pd.Timestamp("2026-01-02 23:00"),
            pd.Timestamp("2026-01-02 12:00"),
        ],
        "latitude": [1.0, 1.0, 2.0],
        "longitude": [1.0, 1.0, 2.0],
    })
    home = scikit_mobility_home_replica(arrivals)
    assert int(home.iloc[0]["location_id"]) == 1
    return {"status": "ok", "home_rows": int(len(home))}
