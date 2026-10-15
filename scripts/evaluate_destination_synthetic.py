"""Reproducible synthetic-only next-destination evaluation, no cloud/data access.

Usage: python scripts/evaluate_destination_synthetic.py
"""
from __future__ import annotations

import json

from geolife.recommendation import evaluate_first_heldout
from geolife.recommendation.fixtures import fixture_visits


def main() -> None:
    print(json.dumps(evaluate_first_heldout(fixture_visits()), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
