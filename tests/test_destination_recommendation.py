"""Pure synthetic next-destination MVP acceptance tests, no GeoLife cache."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from geolife.recommendation import Visit, suggest_destinations, evaluate_first_heldout
from geolife.recommendation.fixtures import fixture_visits


TZ = timezone(timedelta(hours=7))


def _time(day: int, hour: int = 8) -> datetime:
    return datetime(2026, 9, day, hour, tzinfo=TZ)


def test_no_future_leakage_and_ownership():
    a = [Visit("alice", "place_a", _time(1)), Visit("alice", "place_a", _time(2))]
    foreign = [Visit("bob", "place_b", _time(1)) for _ in range(25)]
    query = _time(10)
    baseline = suggest_destinations(a, owner_id="alice", query_at=query)
    changed = suggest_destinations(
        a + foreign + [Visit("alice", "future_spam", _time(11)) for _ in range(25)],
        owner_id="alice", query_at=query,
    )
    assert baseline == changed
    assert [x.place_id for x in changed] == ["place_a"]


def test_context_changes_order_and_excludes_origin():
    events = [
        Visit("owner", "popular", _time(day, 18), "origin_x")
        for day in (1, 2, 3, 4, 5)
    ] + [
        Visit("owner", "morning_choice", _time(day, 8), "origin_y")
        for day in (6, 7, 8, 9)
    ]
    query = _time(10)
    baseline = suggest_destinations(
        events, owner_id="owner", query_at=query,
        origin_place_id="origin_y", method="frequency",
    )
    contextual = suggest_destinations(
        events, owner_id="owner", query_at=query,
        origin_place_id="origin_y", method="contextual",
    )
    assert baseline[0].place_id == "popular"
    assert contextual[0].place_id == "morning_choice"
    no_origin = suggest_destinations(
        events, owner_id="owner", query_at=query,
        origin_place_id="morning_choice",
    )
    assert all(r.place_id != "morning_choice" for r in no_origin)
    assert all("0." not in " ".join(r.reasons) for r in contextual)


def test_abstain_not_fabricate_single_observation():
    visits = [Visit("a", "once", _time(1))]
    assert suggest_destinations(visits, owner_id="a", query_at=_time(2)) == []
    assert suggest_destinations(visits, owner_id="b", query_at=_time(2)) == []


def test_strict_timezones_bad_config_and_tie_determinism():
    with pytest.raises(ValueError, match="timezone-aware"):
        Visit("a", "x", datetime(2026, 9, 1))
    with pytest.raises(ValueError, match="timezone"):
        suggest_destinations([], owner_id="a", query_at=datetime(2026, 9, 1))
    with pytest.raises(ValueError, match="Invalid"):
        suggest_destinations([], owner_id="a", query_at=_time(1), k=0)
    with pytest.raises(ValueError, match="Unrecognized"):
        suggest_destinations([], owner_id="a", query_at=_time(1), method="secret")
    visits = [
        Visit("a", "z", _time(1)), Visit("a", "a", _time(1)),
        Visit("a", "z", _time(2)), Visit("a", "a", _time(2)),
    ]
    actual = suggest_destinations(
        visits, owner_id="a", query_at=_time(3), method="frequency",
    )
    assert [v.place_id for v in actual] == ["a", "z"]


def test_holdout_aggregate_and_novel_place_accounting():
    fixture = fixture_visits()
    assert len(fixture) == 4 * 21 * 2
    report = evaluate_first_heldout(fixture)
    assert report["evaluation_queries"] == 4
    assert report["novel_heldout_targets"] >= 1
    assert report["positive_targets_per_query"] == 1
    assert report["semantic_home_office_accuracy"] is None
    assert report["calibrated_recommendation_probability"] is None
    assert report["production_ready"] is False
    for method in ("frequency", "recency", "contextual"):
        metrics = report["methods"][method]
        assert 0 <= metrics["hit_at_1"] <= metrics["hit_at_3"] <= 1
        assert 0 <= metrics["no_suggestion_rate"] <= 1
        assert metrics["hit_at_3"] == metrics["recall_at_3"]
    # No owner IDs, private coordinates or place IDs leave the aggregate.
    assert "demo_000" not in str(report)
    assert "s0_" not in str(report)


def test_heldout_boundary_is_strict():
    visits = [
        Visit("a", "somewhere", _time(1)),
        Visit("a", "somewhere", _time(2)),
        Visit("a", "somewhere", _time(3)),
        Visit("a", "somewhere", _time(3)),
    ]
    with pytest.raises(ValueError, match="strict time boundary"):
        evaluate_first_heldout(visits)
