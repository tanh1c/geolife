"""Offline Checkpoint 3 plan guard tests; no AWS or Terraform commands."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location(
    "checkpoint3_cloudwatch_plan_guard", ROOT / "scripts/checkpoint3_cloudwatch_plan_guard.py"
)
assert spec is not None and spec.loader is not None
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def sample_plan():
    dashboard = (ROOT / "docs/design/checkpoint3_s2b_dashboard_review.json").read_text(encoding="utf-8")
    values = {
        "aws_cloudwatch_log_group.s2b_telemetry": {
            "name": "/geolife/dev/s2b-telemetry", "retention_in_days": 7,
            "log_group_class": "STANDARD",
        },
        "aws_cloudwatch_dashboard.s2b_telemetry": {
            "dashboard_name": "geolife-dev-s2b-synthetic-review",
            "dashboard_body": dashboard,
        },
    }
    return {
        "configuration": {
            "provider_config": {"aws": {"name": "aws", "expressions": {
                "region": {"constant_value": "ap-southeast-1"},
            }}},
            "root_module": {"resources": [
                {"address": address, "mode": "managed", "type": guard.EXPECTED[address],
                 "provider_config_key": "aws"}
                for address in guard.EXPECTED
            ]},
        },
        "planned_values": {"root_module": {"resources": [
            {"address": address, "mode": "managed", "type": guard.EXPECTED[address],
             "values": copy.deepcopy(after)} for address, after in values.items()
        ]}},
        "resource_changes": [
            {"address": address, "mode": "managed", "type": guard.EXPECTED[address],
             "change": {"actions": ["create"], "before": None, "after": after}}
            for address, after in values.items()
        ],
    }


def test_exact_two_create_plan_and_dashboard_queue_names():
    plan = sample_plan()
    guard.check(plan)
    body = json.loads(plan["resource_changes"][1]["change"]["after"]["dashboard_body"])
    rows = [metric for widget in body["widgets"] for metric in widget["properties"]["metrics"]]
    assert len(body["widgets"]) == 8 and len(rows) == 25 and len(rows) <= 50
    assert {row[3] for row in rows if row[0] == "AWS/SQS"} == {
        "geolife-mle-s2b-dev-jobs", "geolife-mle-s2b-dev-dlq",
    }


@pytest.mark.parametrize("mutate", [
    lambda p: p["resource_changes"][0]["change"].update(actions=["update"]),
    lambda p: p["resource_changes"][0]["change"].update(actions=["delete", "create"]),
    lambda p: p["resource_changes"][0]["change"]["after"].update(retention_in_days=0),
    lambda p: p["resource_changes"][1]["change"]["after"].update(dashboard_body="{}"),
    lambda p: p["resource_changes"].append(copy.deepcopy(p["resource_changes"][0])),
    lambda p: p.update(resource_drift=[{"change": {"actions": ["update"]}}]),
    lambda p: p.update(prior_state={"values": {"root_module": {"resources": [{"address": "existing"}]}}}),
    lambda p: p["configuration"]["provider_config"]["aws"]["expressions"]["region"].update(
        constant_value="us-east-1"
    ),
    lambda p: p["configuration"]["root_module"].update(module_calls={"extra": {}}),
    lambda p: p["configuration"]["root_module"]["resources"][0].update(
        provider_config_key="aws.other"
    ),
    lambda p: p["planned_values"]["root_module"]["resources"][0]["values"].update(
        retention_in_days=1
    ),
    lambda p: p["planned_values"]["root_module"]["resources"].append({
        "address": "aws_security_group.open", "mode": "managed", "type": "aws_security_group",
    }),
    lambda p: p.update(output_changes={"secret": {"change": {"actions": ["create"]}}}),
    lambda p: p.update(variables={"aws_region": {"value": "us-east-1"}}),
])
def test_plan_guard_fails_closed(mutate):
    plan = sample_plan()
    mutate(plan)
    with pytest.raises((ValueError, KeyError)):
        guard.check(plan)
