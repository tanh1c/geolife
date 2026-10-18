"""Offline fictional fixture-mix replay; no AWS, users, GPS or statistical claim."""
from __future__ import annotations

import json
import math
import random

from geolife.serving.aws_s2b import run_synthetic_inference
from geolife.serving.job_simulation import MODEL_VARIANTS

SEED = 20261017
CATEGORIES = (("emitted", "emitted"), ("emitted", "abstained"),
              ("abstained", "emitted"), ("abstained", "abstained"))
CATEGORY_NAMES = ("home_emitted_office_emitted", "home_emitted_office_abstained",
                  "home_abstained_office_emitted", "home_abstained_office_abstained")


def category_counts(counts: list[int]) -> dict[str, int]:
    return dict(zip(CATEGORY_NAMES, counts))


def summarize(events: list[tuple[str, str]]) -> tuple[list[int], float]:
    counts = [events.count(category) for category in CATEGORIES]
    abstention = sum(h == "abstained" for h, _ in events) + sum(o == "abstained" for _, o in events)
    return counts, abstention / (2 * len(events))


def js_bits(reference: list[int], window: list[int]) -> float:
    p = [(x + .5) / (sum(reference) + 2) for x in reference]
    q = [(x + .5) / (sum(window) + 2) for x in window]
    return sum((a * math.log2(a / ((a + b) / 2)) + b * math.log2(b / ((a + b) / 2))) / 2
               for a, b in zip(p, q))


def evaluate(reference: list[tuple[str, str]], windows: list[list[tuple[str, str]]]) -> list[dict[str, object]]:
    if len(reference) != 100:
        raise ValueError("Reference requires 100 fictional events")
    baseline, baseline_abstention = summarize(reference)
    streak = 0
    output = []
    for index, events in enumerate(windows):
        if len(events) < 50:
            streak = 0
            output.append({"window": index, "count": len(events),
                           "categories": category_counts(summarize(events)[0]) if events else category_counts([0] * 4),
                           "status": "insufficient_support"})
            continue
        if len(events) != 50:
            raise ValueError("Windows must contain exactly 50 fictional events")
        counts, abstention = summarize(events)
        js = js_bits(baseline, counts)
        shift = abs(abstention - baseline_abstention)
        streak = streak + 1 if js > .10 or shift >= .20 else 0
        output.append({"window": index, "count": len(events),
                       "categories": category_counts(counts), "js_bits": round(js, 5),
                       "abstention_shift": round(shift, 5),
                       "status": "simulated_alert" if streak >= 2 else "normal"})
    return output


def replay(seed: int = SEED) -> dict[str, object]:
    rng = random.Random(seed)
    variants = {}
    for variant in sorted(MODEL_VARIANTS):
        results = {}
        for fixture in ("three_night_home", "short_observation"):
            value = run_synthetic_inference(fixture=fixture, variant=variant)
            results[fixture] = (value["home_status"], value["office_status"])
        def mix(home: int, short: int) -> list[tuple[str, str]]:
            events = [tuple([*results["three_night_home"]]) for _ in range(home)]
            events += [tuple([*results["short_observation"]]) for _ in range(short)]
            rng.shuffle(events)
            return events

        reference = mix(50, 50)
        windows = [mix(25, 25), mix(0, 50), mix(25, 25), mix(0, 50), mix(0, 50)]
        variants[variant] = {
            "reference": {"count": len(reference), "categories": category_counts(summarize(reference)[0])},
            "windows": evaluate(reference, windows),
        }
    return {"scope": "simulated_offline_replay", "seed": seed, "variants": variants,
            "notice": "Repeated fictional fixtures; input-mix alert only, not independent observations or production drift."}


if __name__ == "__main__":
    print(json.dumps(replay(), indent=2))
