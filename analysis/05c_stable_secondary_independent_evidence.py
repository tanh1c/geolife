"""05c: independent evidence audit for stable secondary anchors."""
import numpy as np
import pandas as pd


def _local_wall_series(values: pd.Series) -> pd.Series:
    """Normalize mixed tz-aware timestamps to naive per-stay local wall clock."""
    normalized = []
    for value in values:
        ts = pd.Timestamp(value)
        if pd.isna(ts):
            normalized.append(pd.NaT)
        elif ts.tzinfo is not None:
            normalized.append(ts.tz_localize(None))
        else:
            normalized.append(ts)
    return pd.Series(normalized, index=values.index, dtype="datetime64[ns]")

EVIDENCE_METRICS = (
    "weekday_weekend_visit_contrast",
    "home_pair_transition_day_share",
    "arrival_hour_concentration",
    "dwell_regularity_score",
)
HISTORICAL_BEIJING_V1_STABLE_USERS = 9


def _circ(hours):
    x = pd.to_numeric(hours, errors="coerce").dropna().to_numpy(float)
    if not len(x):
        return np.nan
    t = 2 * np.pi * (x % 24) / 24
    return float(np.hypot(np.mean(np.sin(t)), np.mean(np.cos(t))))


def _dwell_score(hours):
    x = pd.to_numeric(hours, errors="coerce").dropna().to_numpy(float)
    x = x[x >= 0]
    if not len(x):
        return np.nan
    med = float(np.median(x))
    if med <= 0:
        return 0.0
    q25, q75 = np.quantile(x, [0.25, 0.75])
    return float(1 / (1 + (q75 - q25) / med))


def stable_secondary_cohort(work_patterns_42, home_evidence):
    stable = work_patterns_42.loc[
        work_patterns_42["window_pattern"].eq("stable_secondary_anchor")
        & work_patterns_42["dominant_location_id"].notna(),
        ["user_id", "dominant_location_id"],
    ].copy()
    home = home_evidence.loc[
        home_evidence["unique_vote_winner"].fillna(False).astype(bool)
        & home_evidence["home_tier"].isin(["high", "medium"]),
        ["user_id", "location_id", "home_tier"],
    ].copy()
    for frame in (stable, home):
        frame["user_id"] = frame["user_id"].astype(str)
    stable["dominant_location_id"] = stable["dominant_location_id"].astype(int)
    home["location_id"] = home["location_id"].astype(int)
    return (
        stable.merge(home, on="user_id", validate="one_to_one")
        .rename(columns={
            "dominant_location_id": "secondary_location_id",
            "location_id": "home_location_id",
        })
        .sort_values("user_id")
        .reset_index(drop=True)
    )


def _transition_days(user, home_id):
    direct, any_days = {}, {}
    user = user.sort_values(
        ["local_date", "arrival_time_local", "departure_time_local"]
    )
    for date, day in user.groupby("local_date"):
        seq = []
        for loc in day["location_id"].astype(int):
            if not seq or seq[-1] != loc:
                seq.append(loc)
        for a, b in zip(seq, seq[1:]):
            any_days.setdefault(a, set()).add(date)
            any_days.setdefault(b, set()).add(date)
            if a == home_id and b != home_id:
                direct.setdefault(b, set()).add(date)
            if b == home_id and a != home_id:
                direct.setdefault(a, set()).add(date)
    return direct, any_days


def build_anchor_metrics(semantic_stays, stable_cohort, min_active_days=3, min_recurring_stays=2):
    stays = semantic_stays.copy()
    stays["user_id"] = stays["user_id"].astype(str)
    stays["arrival_time_local"] = _local_wall_series(stays["arrival_time_local"])
    stays["departure_time_local"] = _local_wall_series(stays["departure_time_local"])
    stays["local_date"] = stays["arrival_time_local"].dt.date
    stays["weekday"] = stays["arrival_time_local"].dt.weekday
    stays["arrival_hour"] = stays["arrival_time_local"].dt.hour + stays["arrival_time_local"].dt.minute / 60
    stays["duration_h"] = pd.to_numeric(stays["duration_s"], errors="coerce") / 3600
    rows = []
    for c in stable_cohort.itertuples(index=False):
        user = stays.loc[stays["user_id"].eq(str(c.user_id))].copy()
        if user.empty:
            continue
        home, secondary = int(c.home_location_id), int(c.secondary_location_id)
        obs = user[["local_date", "weekday"]].drop_duplicates()
        wd_obs, we_obs = int(obs["weekday"].lt(5).sum()), int(obs["weekday"].ge(5).sum())
        direct, any_days = _transition_days(user, home)
        for loc, g in user.loc[user["location_id"].astype(int).ne(home)].groupby("location_id"):
            loc = int(loc)
            dates = g[["local_date", "weekday"]].drop_duplicates()
            active, count = len(dates), len(g)
            if active < min_active_days or count < min_recurring_stays:
                continue
            wd, we = int(dates["weekday"].lt(5).sum()), int(dates["weekday"].ge(5).sum())
            wd_share = wd / wd_obs if wd_obs else np.nan
            we_share = we / we_obs if we_obs else np.nan
            pair = direct.get(loc, set())
            rows.append({
                "user_id": str(c.user_id),
                "home_tier": c.home_tier,
                "location_id": loc,
                "is_stable_secondary": loc == secondary,
                "active_days": active,
                "weekday_weekend_visit_contrast": wd_share - we_share if np.isfinite(wd_share) and np.isfinite(we_share) else np.nan,
                "home_pair_transition_day_share": len(pair) / active if active else 0.0,
                "arrival_hour_concentration": _circ(g["arrival_hour"]),
                "dwell_regularity_score": _dwell_score(g["duration_h"]),
            })
    return pd.DataFrame(rows)


def rank_candidate_within_user(anchor_metrics, evidence_metrics=EVIDENCE_METRICS):
    rows = []
    for user_id, group in anchor_metrics.groupby("user_id"):
        cand = group.loc[group["is_stable_secondary"]]
        if len(cand) != 1 or len(group) < 2:
            continue
        c = cand.iloc[0]
        out = {
            "user_id": str(user_id),
            "home_tier": c["home_tier"],
            "secondary_location_id": int(c["location_id"]),
            "comparator_anchor_count": len(group) - 1,
        }
        valid = top = beats = 0
        for metric in evidence_metrics:
            value = float(c[metric])
            peers = pd.to_numeric(group.loc[~group["is_stable_secondary"], metric], errors="coerce").dropna()
            allv = pd.to_numeric(group[metric], errors="coerce").dropna()
            if np.isfinite(value) and len(peers):
                peer_med = float(peers.median())
                is_top = value >= float(allv.max()) - 1e-12
                is_beats = value > peer_med
                pct = float((allv <= value).mean())
                diff = value - peer_med
                valid += 1; top += int(is_top); beats += int(is_beats)
            else:
                peer_med = pct = diff = np.nan
                is_top = is_beats = False
            out.update({
                f"{metric}_value": value,
                f"{metric}_percentile": pct,
                f"{metric}_top1": is_top,
                f"{metric}_peer_median": peer_med,
                f"{metric}_minus_peer_median": diff,
                f"{metric}_beats_peer_median": is_beats,
            })
        out["valid_evidence_axes"] = valid
        out["top1_evidence_axes"] = top
        out["beats_peer_median_axes"] = beats
        rows.append(out)
    return pd.DataFrame(rows)


def summarize_metric_comparison(comp):
    rows = []
    for metric in EVIDENCE_METRICS:
        v = pd.to_numeric(comp[f"{metric}_value"], errors="coerce")
        top = comp[f"{metric}_top1"].fillna(False).astype(bool)
        beats = comp[f"{metric}_beats_peer_median"].fillna(False).astype(bool)
        diff = pd.to_numeric(comp[f"{metric}_minus_peer_median"], errors="coerce")
        rows.append({
            "metric": metric,
            "users_with_metric": int(v.notna().sum()),
            "top1_users": int(top.sum()),
            "top1_share": float(top.mean()),
            "beats_peer_median_users": int(beats.sum()),
            "beats_peer_median_share": float(beats.mean()),
            "median_candidate_minus_peer_median": float(diff.median()),
        })
    return pd.DataFrame(rows)


def summarize_convergence(comp):
    if comp.empty:
        return pd.DataFrame()
    return (
        comp.groupby(["valid_evidence_axes", "top1_evidence_axes", "beats_peer_median_axes"], as_index=False)
        .agg(users=("user_id", "nunique"))
        .sort_values(["top1_evidence_axes", "beats_peer_median_axes"], ascending=False)
    )


def paired_bootstrap_against_peer_median(comp, repetitions=2000, seed=42):
    rng = np.random.default_rng(seed)
    rows = []
    for metric in EVIDENCE_METRICS:
        d = pd.to_numeric(comp[f"{metric}_minus_peer_median"], errors="coerce").dropna().to_numpy(float)
        if not len(d):
            continue
        samples = np.array([np.median(rng.choice(d, len(d), replace=True)) for _ in range(repetitions)])
        rows.append({
            "metric": metric,
            "users": len(d),
            "median_difference": float(np.median(d)),
            "ci95_low": float(np.quantile(samples, .025)),
            "ci95_high": float(np.quantile(samples, .975)),
            "bootstrap_p_gt_zero": float(np.mean(samples > 0)),
        })
    return pd.DataFrame(rows)


def support_sensitivity(semantic_stays, stable_cohort, min_active_days_values=(2, 3, 5)):
    rows = []
    for minimum in min_active_days_values:
        comp = rank_candidate_within_user(build_anchor_metrics(semantic_stays, stable_cohort, minimum))
        if comp.empty:
            continue
        rows.append({
            "min_active_days": minimum,
            "candidate_users": comp["user_id"].nunique(),
            "median_comparator_anchors": float(comp["comparator_anchor_count"].median()),
            "median_top1_axes": float(comp["top1_evidence_axes"].median()),
            "three_plus_top_axes_users": int(comp["top1_evidence_axes"].ge(3).sum()),
            "three_plus_top_axes_share": float(comp["top1_evidence_axes"].ge(3).mean()),
            "median_beats_peer_axes": float(comp["beats_peer_median_axes"].median()),
        })
    return pd.DataFrame(rows)


def compare_to_static_office(comp, work_patterns_42):
    columns = [c for c in [
        "user_id",
        "dominant_matches_fixed_window",
        "dominant_matches_howde_style",
        "dominant_matches_recurrence",
        "dominant_matches_baseline_emitted_office",
    ] if c in work_patterns_42.columns]
    merged = comp.merge(work_patterns_42[columns].drop_duplicates("user_id"), on="user_id", how="left")
    rows = []
    for column in columns[1:]:
        mask = merged[column].fillna(False).astype(bool)
        for state, subset in (("matches", merged.loc[mask]), ("does_not_match", merged.loc[~mask])):
            if len(subset):
                rows.append({
                    "comparison": column,
                    "state": state,
                    "users": subset["user_id"].nunique(),
                    "median_top1_evidence_axes": float(subset["top1_evidence_axes"].median()),
                    "three_plus_top_axes_share": float(subset["top1_evidence_axes"].ge(3).mean()),
                })
    return pd.DataFrame(rows)


def synthetic_self_check():
    tz = "Asia/Shanghai"
    start = pd.Timestamp("2026-01-05", tz=tz)
    rows = []
    for i in range(42):
        day = start + pd.Timedelta(days=i)
        rows.append({"user_id":"u1","location_id":0,"arrival_time_local":day,"departure_time_local":day+pd.Timedelta(hours=6),"duration_s":21600})
        if day.weekday() < 5:
            rows += [
                {"user_id":"u1","location_id":1,"arrival_time_local":day+pd.Timedelta(hours=9),"departure_time_local":day+pd.Timedelta(hours=17),"duration_s":28800},
                {"user_id":"u1","location_id":0,"arrival_time_local":day+pd.Timedelta(hours=19),"departure_time_local":day+pd.Timedelta(hours=23),"duration_s":14400},
            ]
        elif i % 2 == 0:
            h, dur = 11 + i % 7, 1 + i % 4
            rows.append({"user_id":"u1","location_id":2,"arrival_time_local":day+pd.Timedelta(hours=h),"departure_time_local":day+pd.Timedelta(hours=h+dur),"duration_s":dur*3600})
    home = pd.DataFrame([{"user_id":"u1","location_id":0,"home_tier":"high","unique_vote_winner":True}])
    work = pd.DataFrame([{"user_id":"u1","dominant_location_id":1,"window_pattern":"stable_secondary_anchor"}])
    cohort = stable_secondary_cohort(work, home)
    comp = rank_candidate_within_user(build_anchor_metrics(pd.DataFrame(rows), cohort, 2))
    assert len(comp) == 1 and int(comp.iloc[0]["top1_evidence_axes"]) >= 3
    return {"candidate_users": 1, "top1_axes": int(comp.iloc[0]["top1_evidence_axes"]), "status": "ok"}
