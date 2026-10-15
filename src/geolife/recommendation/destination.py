"""Deterministic destination suggestions and strictly chronological offline audit.

Input visits must belong to an explicitly authorized owner. This pure module has
no storage/network access. The restricted demo API supplies only server-owned
synthetic events keyed to its authenticated account, never GeoLife research IDs.

The rank is a preference heuristic, not HOME/OFFICE confidence or probability.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from math import floor
from typing import Literal, Sequence


Method = Literal["contextual", "frequency", "recency"]


@dataclass(frozen=True)
class Visit:
    owner_id: str
    place_id: str
    observed_at: datetime
    origin_place_id: str | None = None

    def __post_init__(self) -> None:
        if not self.owner_id or not self.place_id:
            raise ValueError("Nonempty owner and place are required")
        if self.observed_at.tzinfo is None or self.observed_at.utcoffset() is None:
            raise ValueError("Visits require timezone-aware datetimes")


@dataclass(frozen=True)
class Suggestion:
    rank: int
    place_id: str
    reasons: tuple[str, ...]


def _ensure_time(query_at: datetime) -> None:
    if query_at.tzinfo is None or query_at.utcoffset() is None:
        raise ValueError("Query timestamp must contain a timezone offset")


def suggest_destinations(
    visits: Sequence[Visit],
    *,
    owner_id: str,
    query_at: datetime,
    origin_place_id: str | None = None,
    k: int = 3,
    method: Method = "contextual",
    min_place_visits: int = 2,
) -> list[Suggestion]:
    """Return Top-K for one owner; never silently include held-out future visits.

    All observations must precede query_at; foreign-owner events are discarded.
    A candidate requires at least min_place_visits *TRAIN* events. Current origin
    is excluded as a destination. Tie-breaks are deterministic and explicit.
    """
    _ensure_time(query_at)
    if not owner_id or not 1 <= k <= 5 or min_place_visits < 2:
        raise ValueError("Invalid owner, k or minimum history requirement")
    if method not in {"contextual", "frequency", "recency"}:
        raise ValueError("Unrecognized recommender method")
    history = [
        event for event in visits
        if event.owner_id == owner_id and event.observed_at < query_at
    ]
    by_place: dict[str, list[Visit]] = defaultdict(list)
    for event in history:
        if event.place_id != origin_place_id:
            by_place[event.place_id].append(event)

    choices: list[tuple[float, int, float, str, tuple[str, ...]]] = []
    for place, events in by_place.items():
        count = len(events)
        if count < min_place_visits:
            continue
        latest = max(row.observed_at for row in events)
        recency_days = max(0.0, (query_at - latest).total_seconds() / 86400)
        age_score = 1.0 / (1.0 + recency_days / 7.0)
        share = count / len(history)
        # Explicit query timezone makes local-clock comparisons meaningful.
        nearby_hour = sum(
            min((row.observed_at.astimezone(query_at.tzinfo).hour - query_at.hour) % 24,
                (query_at.hour - row.observed_at.astimezone(query_at.tzinfo).hour) % 24)
            <= 2
            for row in events
        ) / count
        same_weekday = sum(
            row.observed_at.astimezone(query_at.tzinfo).weekday() == query_at.weekday()
            for row in events
        ) / count
        from_origin = (
            sum(row.origin_place_id == origin_place_id for row in events) / count
            if origin_place_id is not None else 0.0
        )
        if method == "frequency":
            score = float(count)
        elif method == "recency":
            score = -recency_days
        else:
            # Feature scores are normalized, but their weighted sum is NOT a
            # calibrated chance of choosing this destination.
            score = (
                0.35 * share + 0.20 * age_score + 0.20 * nearby_hour
                + 0.10 * same_weekday + 0.15 * from_origin
            )
        reasons = ["Đã ghé nhiều lần"]
        if method == "contextual":
            if nearby_hour >= 0.5:
                reasons.append("Thường ghé vào giờ tương tự")
            if from_origin >= 0.5 and origin_place_id is not None:
                reasons.append("Có lịch sử đi từ điểm xuất phát này")
            if age_score >= 0.5:
                reasons.append("Đã ghé gần đây")
        choices.append((score, count, latest.timestamp(), place, tuple(reasons)))
    choices.sort(key=lambda row: (-row[0], -row[1], -row[2], row[3]))
    return [
        Suggestion(rank=i + 1, place_id=place, reasons=reasons)
        for i, (_, _, _, place, reasons) in enumerate(choices[:k])
    ]


def evaluate_last_event(
    visits: Sequence[Visit], *, train_fraction: float = 0.70
) -> dict[str, object]:
    """One next-place test event per eligible synthetic owner.

    Per owner, train contains the earliest floor(train_fraction * n) visits
    (minimum three), and prediction is made at the *first* held-out visit.
    Only origin and query time of that event are allowed as query context;
    its destination and all held-out observations are excluded from history.

    Hit@K and Recall@K are equal here because each query has exactly one
    future positive; the distinction is documented to avoid fake rigor.
    Every eligible query counts in the denominator, including abstentions and
    previously unseen targets. No owner-level rows leave this function.
    """
    if not 0.5 <= train_fraction < 1:
        raise ValueError("train_fraction must be within [0.5, 1)")
    owners: dict[str, list[Visit]] = defaultdict(list)
    for event in visits:
        owners[event.owner_id].append(event)
    accum = {
        method: {"hit_at_1": 0, "hit_at_3": 0, "no_suggestion": 0}
        for method in ("contextual", "frequency", "recency")
    }
    evaluated = 0
    novel_targets = 0
    ignored_small = 0
    for owner, timeline in sorted(owners.items()):
        timeline.sort(key=lambda event: (event.observed_at, event.place_id))
        split = max(3, floor(len(timeline) * train_fraction))
        if split >= len(timeline):
            ignored_small += 1
            continue
        train, target = timeline[:split], timeline[split]
        if train[-1].observed_at >= target.observed_at:
            raise ValueError("TRAIN and FUTURE require a strict time boundary")
        evaluated += 1
        if target.place_id not in {v.place_id for v in train}:
            novel_targets += 1
        for method in accum:
            recs = suggest_destinations(
                train, owner_id=owner, query_at=target.observed_at,
                origin_place_id=target.origin_place_id, k=3,
                method=method,
            )
            suggested = [item.place_id for item in recs]
            if not suggested:
                accum[method]["no_suggestion"] += 1
            if target.place_id in suggested[:1]:
                accum[method]["hit_at_1"] += 1
            if target.place_id in suggested:
                accum[method]["hit_at_3"] += 1
    if not evaluated:
        raise ValueError("No synthetic owner has enough chronology for holdout")
    methods = {
        name: {
            "hit_at_1": round(counts["hit_at_1"] / evaluated, 6),
            "hit_at_3": round(counts["hit_at_3"] / evaluated, 6),
            "recall_at_3": round(counts["hit_at_3"] / evaluated, 6),
            "no_suggestion_rate": round(counts["no_suggestion"] / evaluated, 6),
        }
        for name, counts in accum.items()
    }
    return {
        "experiment": "s1_synthetic_first_next_destination_first_heldout",
        "input_policy": "synthetic_only_no_geolife_user_history",
        "evaluation_queries": evaluated,
        "insufficient_history_owners": ignored_small,
        "novel_heldout_targets": novel_targets,
        "positive_targets_per_query": 1,
        "methods": methods,
        "semantic_home_office_accuracy": None,
        "calibrated_recommendation_probability": None,
        "production_ready": False,
    }
