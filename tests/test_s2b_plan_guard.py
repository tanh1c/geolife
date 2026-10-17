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


def _partial_state_sample():
    """Model a stopped mid-apply: existing bucket/table/queues/alarm in state."""
    plan = _safe_sample()
    created = {
        "aws_s3_bucket.payloads",
        "aws_dynamodb_table.jobs",
        "aws_sqs_queue.jobs",
        "aws_sqs_queue.dead_letter",
        "aws_sqs_queue_redrive_allow_policy.dlq",
        "aws_cloudwatch_metric_alarm.dlq_not_empty",
    }
    prior_rows = [
        {"address": "data.aws_caller_identity.current", "mode": "data",
         "values": {"account_id": "123456789012"}},
    ]
    for r in plan["resource_changes"]:
        if r["address"] in created:
            r["change"]["actions"] = ["no-op"]
            r["change"]["before"] = copy.deepcopy(r["change"]["after"])
            prior_rows.append({
                "address": r["address"], "mode": "managed",
                "values": copy.deepcopy(r["change"]["before"]),
            })
    plan["prior_state"] = {"values": {"root_module": {"resources": prior_rows}}}
    return plan


def test_partial_state_recovery_accepts_only_prior_allowlisted_no_ops():
    plan = _partial_state_sample()
    with pytest.raises(guard.PlanRejected, match="prior state"):
        guard.validate_plan(plan, expected_account="123456789012")
    answer = guard.validate_plan(
        plan, expected_account="123456789012", allow_partial_state=True
    )
    assert answer["recovery_partial_state"] is True
    assert answer["changes"] == {
        "create": 4, "update": 0, "delete": 0, "no_op": 6,
    }
    assert answer["terraform_apply_authorized"] is False


def test_partial_state_recovery_rejects_in_place_updates():
    plan = _partial_state_sample()
    item = next(i for i in plan["resource_changes"]
                if i["address"] == "aws_s3_bucket.payloads")
    item["change"]["actions"] = ["update"]
    with pytest.raises(guard.PlanRejected, match="Unexpected action"):
        guard.validate_plan(plan, expected_account="123456789012", allow_partial_state=True)


def test_partial_state_recovery_rejects_deleted_or_recreated_resources():
    for actions in (["delete"], ["delete", "create"], ["create"]):
        plan = _partial_state_sample()
        item = next(i for i in plan["resource_changes"]
                    if i["address"] == "aws_dynamodb_table.jobs")
        item["change"]["actions"] = actions
        with pytest.raises(guard.PlanRejected):
            guard.validate_plan(
                plan, expected_account="123456789012", allow_partial_state=True
            )


def test_partial_state_recovery_rejects_outside_managed_state():
    plan = _partial_state_sample()
    plan["prior_state"]["values"]["root_module"]["resources"].append({
        "address": "aws_security_group.public", "mode": "managed",
        "values": {"id": "sg-unknown"}
    })
    with pytest.raises(guard.PlanRejected, match="out-of-scope"):
        guard.validate_plan(plan, expected_account="123456789012", allow_partial_state=True)


def test_partial_state_recovery_rejects_no_op_without_prior_managed():
    plan = _partial_state_sample()
    rows = plan["prior_state"]["values"]["root_module"]["resources"]
    rows[:] = [r for r in rows if r["address"] != "aws_s3_bucket.payloads"]
    with pytest.raises(guard.PlanRejected, match="No-op without"):
        guard.validate_plan(plan, expected_account="123456789012", allow_partial_state=True)


def test_refresh_drift_distinct_from_actual_noop_changes():
    plan = _partial_state_sample()
    bucket = next(row for row in plan["resource_changes"]
                  if row["address"] == "aws_s3_bucket.payloads")
    observed_after = copy.deepcopy(bucket["change"]["after"])
    plan["resource_drift"] = [{
        "address": "aws_s3_bucket.payloads",
        "mode": "managed",
        "change": {
            "actions": ["update"],
            "before": {**observed_after, "hosted_zone_id": "old"},
            "after": observed_after,
        },
    }]
    with pytest.raises(guard.PlanRejected, match="Drift requires"):
        guard.validate_plan(
            plan, expected_account="123456789012", allow_partial_state=True
        )
    review = guard.drift_summary(plan)
    assert review["count"] == 1
    assert review["drift"][0]["resource"] == "aws_s3_bucket.payloads"
    assert review["drift"][0]["changed_attribute_paths"] == ["hosted_zone_id"]
    assert review["displays_aws_attribute_values"] is False
    out = guard.validate_plan(
        plan, expected_account="123456789012", allow_partial_state=True,
        reviewed_drift_digest=review["fingerprint_sha256"],
    )
    assert out["reviewed_refresh_drift_count"] == 1
    assert out["changes"] == {"create": 4, "update": 0, "delete": 0, "no_op": 6}
    assert out["terraform_apply_authorized"] is False


def test_refresh_drift_rejects_changed_digest():
    plan = _partial_state_sample()
    bucket = next(row for row in plan["resource_changes"]
                  if row["address"] == "aws_s3_bucket.payloads")
    plan["resource_drift"] = [{
        "address": bucket["address"],
        "mode": "managed",
        "change": {
            "actions": ["update"],
            "before": {**bucket["change"]["after"], "id": "former"},
            "after": bucket["change"]["after"],
        },
    }]
    bad = guard.drift_summary(plan)["fingerprint_sha256"]
    plan["resource_drift"][0]["change"]["before"]["id"] = "modified"
    with pytest.raises(guard.PlanRejected, match="Drift requires"):
        guard.validate_plan(
            plan, expected_account="123456789012",
            allow_partial_state=True, reviewed_drift_digest=bad,
        )


def test_refresh_drift_rejects_unsupported_plan_action_even_if_reviewed():
    plan = _partial_state_sample()
    pending = next(row for row in plan["resource_changes"]
                   if row["address"] == "aws_s3_bucket_policy.payloads")
    plan["resource_drift"] = [{
        "address": pending["address"], "mode": "managed",
        "change": {"actions": ["update"], "before": {"policy": "old"},
                   "after": {"policy": "new"}},
    }]
    review = guard.drift_summary(plan)
    with pytest.raises(guard.PlanRejected, match="Security-sensitive|untracked or changing"):
        guard.validate_plan(
            plan, expected_account="123456789012", allow_partial_state=True,
            reviewed_drift_digest=review["fingerprint_sha256"],
        )


def test_refresh_drift_rejects_nonmatching_remote_and_planned_after():
    plan = _partial_state_sample()
    bucket = next(row for row in plan["resource_changes"]
                  if row["address"] == "aws_s3_bucket.payloads")
    plan["resource_drift"] = [{
        "address": bucket["address"], "mode": "managed",
        "change": {"actions": ["update"], "before": {"id": "old"},
                   "after": {"id": "new"}},
    }]
    review = guard.drift_summary(plan)
    with pytest.raises(guard.PlanRejected, match="after-state differs"):
        guard.validate_plan(
            plan, expected_account="123456789012", allow_partial_state=True,
            reviewed_drift_digest=review["fingerprint_sha256"],
        )


def test_refresh_drift_does_not_accept_delete_or_external_resource():
    plan = _partial_state_sample()
    plan["resource_drift"] = [{
        "address": "aws_s3_bucket.payloads", "mode": "managed",
        "change": {"actions": ["delete"], "before": {"id": "test"},
                   "after": {}},
    }]
    with pytest.raises(guard.PlanRejected, match="Unexpected drift operation"):
        guard.drift_summary(plan)
    plan["resource_drift"][0]["address"] = "aws_security_group.public"
    plan["resource_drift"][0]["change"]["actions"] = ["update"]
    with pytest.raises(guard.PlanRejected, match="Unexpected, duplicate or external"):
        guard.drift_summary(plan)


def test_refresh_drift_review_does_not_override_forbidden_changes():
    plan = _partial_state_sample()
    bucket = next(row for row in plan["resource_changes"]
                  if row["address"] == "aws_s3_bucket.payloads")
    observed_after = copy.deepcopy(bucket["change"]["after"])
    plan["resource_drift"] = [{
        "address": bucket["address"], "mode": "managed",
        "change": {"actions": ["update"],
                   "before": {**observed_after, "hosted_zone_id": "old"},
                   "after": observed_after},
    }]
    review = guard.drift_summary(plan)
    bucket["change"]["actions"] = ["delete", "create"]
    with pytest.raises(guard.PlanRejected):
        guard.validate_plan(
            plan, expected_account="123456789012", allow_partial_state=True,
            reviewed_drift_digest=review["fingerprint_sha256"],
        )


def test_security_sensitive_refresh_drift_rejected_even_with_correct_digest():
    plan = _partial_state_sample()
    ddb = next(row for row in plan["resource_changes"]
               if row["address"] == "aws_dynamodb_table.jobs")
    observed = copy.deepcopy(ddb["change"]["after"])
    plan["resource_drift"] = [{
        "address": ddb["address"], "mode": "managed",
        "change": {
            "actions": ["update"],
            "before": {**observed, "billing_mode": "PROVISIONED"},
            "after": observed,
        },
    }]
    digest = guard.drift_summary(plan)["fingerprint_sha256"]
    with pytest.raises(guard.PlanRejected, match="Security-sensitive"):
        guard.validate_plan(
            plan, expected_account="123456789012", allow_partial_state=True,
            reviewed_drift_digest=digest,
        )
