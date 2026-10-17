"""Plan guard synthetic tests; no AWS credentials or Terraform required."""
from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

import pytest


MODULE = Path(__file__).resolve().parents[1] / "scripts" / "s2b_plan_guard.py"
spec = importlib.util.spec_from_file_location("s2b_plan_guard", MODULE)
assert spec is not None and spec.loader is not None
guard = importlib.util.module_from_spec(spec)
spec.loader.exec_module(guard)


def _safe_sample():
    values = {
        "aws_s3_bucket.payloads": {"force_destroy": False},
        "aws_s3_bucket_public_access_block.payloads": {
            k: True for k in (
                "block_public_acls", "block_public_policy",
                "ignore_public_acls", "restrict_public_buckets",
            )
        },
        "aws_dynamodb_table.jobs": {
            "billing_mode": "PAY_PER_REQUEST",
            "ttl": [{"attribute_name": "expires_at", "enabled": True}],
            "point_in_time_recovery": [{"enabled": False}],
        },
        "aws_sqs_queue.jobs": {
            "sqs_managed_sse_enabled": True,
            "visibility_timeout_seconds": 120,
            "message_retention_seconds": 86400,
        },
        "aws_sqs_queue.dead_letter": {"sqs_managed_sse_enabled": True},
        "aws_cloudwatch_metric_alarm.dlq_not_empty": {
            "alarm_actions": [], "ok_actions": [],
            "insufficient_data_actions": [], "threshold": 0,
        },
    }
    return {
        "variables": {
            "aws_region": {"value": "ap-southeast-1"},
            "prefix": {"value": "geolife-mle-s2b-dev"},
        },
        "planned_values": {"root_module": {"resources": [
            {"address": "data.aws_caller_identity.current", "values": {
                "account_id": "123456789012",
            }},
        ]}},
        "resource_changes": [
            {"address": address, "mode": "managed", "change": {
                "actions": ["create"], "before": None,
                "after": values.get(address, {}),
            }}
            for address in sorted(guard.EXPECTED_RESOURCES)
        ],
    }


def test_exact_ten_create_only_plan_passes_private_review():
    approved = guard.validate_plan(_safe_sample(), expected_account="123456789012")
    assert approved["expected_resources_to_create"] == 10
    assert approved["changes"] == {"create": 10, "update": 0, "delete": 0}
    assert approved["terraform_apply_authorized"] is False


@pytest.mark.parametrize("change", [
    lambda p: p["resource_changes"][0]["change"].update({"actions": ["delete"]}),
    lambda p: p["resource_changes"].append({
        "address": "aws_security_group.open_public", "mode": "managed",
        "change": {"actions": ["create"], "before": None, "after": {}},
    }),
    lambda p: p["variables"]["aws_region"].update(value="us-east-1"),
    lambda p: p["variables"]["prefix"].update(value="unsafe-public-ingress"),
    lambda p: p["planned_values"]["root_module"]["resources"][0]["values"].update(
        account_id="999999999999"
    ),
    lambda p: next(
        item for item in p["resource_changes"]
        if item["address"] == "aws_s3_bucket_public_access_block.payloads"
    )["change"]["after"].update(block_public_policy=False),
    lambda p: next(
        item for item in p["resource_changes"]
        if item["address"] == "aws_s3_bucket.payloads"
    )["change"]["after"].update(force_destroy=True),
    lambda p: next(
        item for item in p["resource_changes"]
        if item["address"] == "aws_dynamodb_table.jobs"
    )["change"]["after"].update(billing_mode="PROVISIONED"),
    lambda p: next(
        item for item in p["resource_changes"]
        if item["address"] == "aws_sqs_queue.jobs"
    )["change"]["after"].update(sqs_managed_sse_enabled=False),
    lambda p: next(
        item for item in p["resource_changes"]
        if item["address"] == "aws_cloudwatch_metric_alarm.dlq_not_empty"
    )["change"]["after"].update(alarm_actions=["arn:aws:sns:fake"]),
])
def test_rejects_other_region_account_public_data_cost_or_destroy(change):
    plan = copy.deepcopy(_safe_sample())
    change(plan)
    with pytest.raises(guard.PlanRejected):
        guard.validate_plan(plan, expected_account="123456789012")


def test_rejects_drift_and_incorrect_expected_account():
    plan = _safe_sample()
    plan["resource_drift"] = [{"change": {"actions": ["update"]}}]
    with pytest.raises(guard.PlanRejected):
        guard.validate_plan(plan, expected_account="123456789012")
    with pytest.raises(guard.PlanRejected):
        guard.validate_plan(_safe_sample(), expected_account="111111111111")


def test_real_terraform_shape_identity_in_prior_state_only():
    """Regression: the operator's saved plan had account_id in prior_state."""
    plan = _safe_sample()
    plan["prior_state"] = {
        "format_version": "1.0",
        "values": {"root_module": {"resources": [
            {
                "address": "data.aws_caller_identity.current",
                "mode": "data",
                "type": "aws_caller_identity",
                "name": "current",
                "values": {"account_id": "123456789012"},
            },
        ]}},
    }
    plan["planned_values"] = {
        "root_module": {"resources": [
            {"address": row["address"], "mode": "managed"}
            for row in plan["resource_changes"]
        ]}
    }
    response = guard.validate_plan(plan, expected_account="123456789012")
    assert response["expected_resources_to_create"] == 10
    assert response["identity_verified"] is True
    assert response["terraform_apply_authorized"] is False


def test_rejects_mismatched_caller_id_across_prior_and_planned():
    plan = _safe_sample()
    plan["prior_state"] = {"values": {"root_module": {"resources": [
        {"address": "data.aws_caller_identity.current",
         "mode": "data",
         "values": {"account_id": "999999999999"}},
    ]}}}
    with pytest.raises(guard.PlanRejected, match="identity"):
        guard.validate_plan(plan, expected_account="123456789012")


def test_rejects_prior_state_existing_managed_resource():
    plan = _safe_sample()
    plan["prior_state"] = {"values": {"root_module": {"resources": [
        {"address": "aws_instance.legacy", "mode": "managed",
         "values": {"id": "i-existing"}},
        {"address": "data.aws_caller_identity.current", "mode": "data",
         "values": {"account_id": "123456789012"}},
    ]}}}
    with pytest.raises(guard.PlanRejected, match="prior state"):
        guard.validate_plan(plan, expected_account="123456789012")


def test_rejects_missing_identity_in_both_sections():
    plan = _safe_sample()
    plan["planned_values"] = {"root_module": {"resources": []}}
    with pytest.raises(guard.PlanRejected, match="identity"):
        guard.validate_plan(plan, expected_account="123456789012")


def test_rejects_wrong_prior_state_identity_when_planned_is_absent():
    plan = _safe_sample()
    plan["planned_values"] = {"root_module": {"resources": []}}
    plan["prior_state"] = {"values": {"root_module": {"resources": [
        {"address": "data.aws_caller_identity.current", "mode": "data",
         "values": {"account_id": "999999999999"}},
    ]}}}
    with pytest.raises(guard.PlanRejected, match="identity"):
        guard.validate_plan(plan, expected_account="123456789012")
