"""Deterministic, fictional-only replay checks."""
from __future__ import annotations

from scripts.replay_s2b_synthetic_drift import CATEGORIES, evaluate, js_bits, replay, summarize


def test_replay_uses_disjoint_chronological_fixture_events(monkeypatch):
    import scripts.replay_s2b_synthetic_drift as drift

    observed = []
    original = drift.evaluate

    def capture(reference, windows):
        observed.append((reference, windows))
        return original(reference, windows)

    monkeypatch.setattr(drift, "evaluate", capture)
    drift.replay()
    assert len(observed) == 2
    for reference, windows in observed:
        assert len(reference) == 100
        assert len(windows) == 5 and all(len(window) == 50 for window in windows)
        assert all(id(event) not in {id(reference_event) for reference_event in reference}
                   for window in windows for event in window)





def test_math_and_two_label_abstention():
    assert js_bits([25, 25, 25, 25], [12, 13, 12, 13]) < .01
    assert summarize([("emitted", "abstained"), ("abstained", "abstained")])[1] == .75
    assert len(CATEGORIES) == 4


def test_consecutive_sparse_and_spike_reset():
    baseline = [("emitted", "abstained")] * 100
    shifted = [("abstained", "abstained")] * 50
    normal = baseline[:50]
    statuses = [w["status"] for w in evaluate(
        baseline, [normal, shifted, normal, shifted, shifted[:49], shifted, shifted],
    )]
    assert statuses == ["normal", "normal", "normal", "normal", "insufficient_support",
                        "normal", "simulated_alert"]


def test_replay_deterministic_privacy_and_variant_partition():
    first = replay()
    assert first == replay()
    assert first["scope"] == "simulated_offline_replay"
    assert len(first["variants"]) == 2
    expected = {
        "home_emitted_office_emitted", "home_emitted_office_abstained",
        "home_abstained_office_emitted", "home_abstained_office_abstained",
    }
    for variant in first["variants"].values():
        reference, windows = variant["reference"], variant["windows"]
        assert len(windows) == 5 and sum(reference["categories"].values()) == 100
        assert set(reference["categories"]) == expected
        assert windows[-1]["status"] == "simulated_alert"
        assert all(set(w["categories"]) == expected and sum(w["categories"].values()) == w["count"]
                   for w in windows)
        assert all("job_id" not in w and "latitude" not in w for w in windows)
