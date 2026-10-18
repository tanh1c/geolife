"""Plan guard tests: synthetic plan JSON, no AWS."""
from __future__ import annotations

import sys
from pathlib import Path
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.mentor_beta_plan_guard import ALLOWED, validate


def good():
    return {
        "resource_changes": [
            {"mode": "managed", "address": a, "change": {"actions": ["create"]}}
            for a in sorted(ALLOWED)
        ],
        "variables": {
            "aws_region": {"value": "ap-southeast-1"},
            "account_id": {"value": "939169265033"},
            "api_gateway_origin": {"value": ""},
        },
    }


def test_exact_initial_plan():
    assert validate(good())["create"] == len(ALLOWED)


@pytest.mark.parametrize("mutation", [
    lambda x: x["resource_changes"].pop(),
    lambda x: x["resource_changes"].append({
        "mode": "managed", "address": "aws_instance.api",
        "change": {"actions": ["create"]}
    }),
    lambda x: x["resource_changes"][0]["change"].update(actions=["update"]),
    lambda x: x["resource_changes"][0]["change"].update(actions=["delete", "create"]),
    lambda x: x["variables"]["account_id"].update(value="000000000000"),
    lambda x: x["variables"]["aws_region"].update(value="us-west-2"),
    lambda x: x["variables"]["api_gateway_origin"].update(value="api.execute-api.ap-southeast-1.amazonaws.com"),
])
def test_refuses_unsafe_plan(mutation):
    p = good()
    mutation(p)
    with pytest.raises(ValueError):
        validate(p)
