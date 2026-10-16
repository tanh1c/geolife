"""Read-only S2b Terraform JSON plan guard. NEVER calls AWS or Terraform apply.

Input from: terraform show -json <saved-plan> > <private-json-file>.
The JSON (and binary plan) may contain sensitive configuration; store OUTSIDE git,
inspect only locally, never upload/share the plan file. Script prints types/counts
only, not resource IDs, ARNs, secrets or Terraform configuration values.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


EXPECTED_RESOURCES = frozenset({
    "aws_s3_bucket.payloads",
    "aws_s3_bucket_public_access_block.payloads",
    "aws_s3_bucket_server_side_encryption_configuration.payloads",
    "aws_s3_bucket_lifecycle_configuration.payloads",
    "aws_s3_bucket_policy.payloads",
    "aws_dynamodb_table.jobs",
    "aws_sqs_queue.dead_letter",
    "aws_sqs_queue.jobs",
    "aws_sqs_queue_redrive_allow_policy.dlq",
    "aws_cloudwatch_metric_alarm.dlq_not_empty",
})


class PlanRejected(ValueError):
    """Fail closed for any unexpected S2b Terraform plan change."""


def validate_plan(data: dict, *, expected_account: str, expected_region: str = "ap-southeast-1") -> dict:
    if not re.fullmatch(r"\d{12}", expected_account):
        raise PlanRejected("Expected account must be twelve digits")
    if expected_region != "ap-southeast-1":
        raise PlanRejected("S2b experiment is restricted to ap-southeast-1")
    if data.get("errored"):
        raise PlanRejected("Terraform plan contains errors")

    variables = data.get("variables", {})
    region = variables.get("aws_region", {}).get("value")
    if region != expected_region:
        raise PlanRejected("Plan has incorrect AWS region")
    prefix = variables.get("prefix", {}).get("value")
    if prefix != "geolife-mle-s2b-dev":
        raise PlanRejected("Unknown project prefix or resource naming")

    resources = data.get("planned_values", {}).get("root_module", {}).get("resources", [])
    identities = [
        row.get("values", {}).get("account_id")
        for row in resources
        if row.get("address") == "data.aws_caller_identity.current"
    ]
    if len(identities) != 1 or identities[0] != expected_account:
        raise PlanRejected("AWS caller identity in the plan does not match expected account")

    changes = data.get("resource_changes", [])
    managed = [r for r in changes if r.get("mode", "managed") == "managed"]
    by_address: dict[str, dict] = {}
    for item in managed:
        address = item.get("address")
        if address in by_address:
            raise PlanRejected("Duplicate planned resource address")
        by_address[address] = item
    if set(by_address) != EXPECTED_RESOURCES:
        missing = sorted(EXPECTED_RESOURCES - set(by_address))
        extra = sorted(set(by_address) - EXPECTED_RESOURCES)
        raise PlanRejected(
            f"Plan resource set mismatch; missing_count={len(missing)}, unexpected_count={len(extra)}"
        )
    for address, item in by_address.items():
        change = item.get("change", {})
        if change.get("actions") != ["create"]:
            raise PlanRejected(f"Non-create Terraform action on {address}")
        if change.get("before") is not None:
            raise PlanRejected(f"Existing managed resource is targeted: {address}")

    for drift in data.get("resource_drift", []):
        if drift.get("change", {}).get("actions") not in (None, ["no-op"]):
            raise PlanRejected("Resource drift detected in S2b state")

    def after(key: str) -> dict:
        value = by_address[key].get("change", {}).get("after")
        return value if isinstance(value, dict) else {}

    s3 = after("aws_s3_bucket.payloads")
    if s3.get("force_destroy") is not False:
        raise PlanRejected("S3 force_destroy must be false")

    public = after("aws_s3_bucket_public_access_block.payloads")
    for flag in ("block_public_acls", "block_public_policy",
                 "ignore_public_acls", "restrict_public_buckets"):
        if public.get(flag) is not True:
            raise PlanRejected("All S3 public access blocks must be true")

    ddb = after("aws_dynamodb_table.jobs")
    if ddb.get("billing_mode") != "PAY_PER_REQUEST":
        raise PlanRejected("DynamoDB must be on-demand")
    ttl = ddb.get("ttl", [])
    if not ttl or ttl[0].get("enabled") is not True or ttl[0].get("attribute_name") != "expires_at":
        raise PlanRejected("DynamoDB TTL config is missing")
    if ddb.get("point_in_time_recovery", [{}])[0].get("enabled") is not False:
        raise PlanRejected("Unexpected DynamoDB point-in-time recovery cost")

    for name in ("jobs", "dead_letter"):
        queue = after(f"aws_sqs_queue.{name}")
        if queue.get("sqs_managed_sse_enabled") is not True:
            raise PlanRejected("SQS managed encryption must be enabled")
    if after("aws_sqs_queue.jobs").get("visibility_timeout_seconds") != 120:
        raise PlanRejected("SQS worker visibility must be 120 seconds")
    if after("aws_sqs_queue.jobs").get("message_retention_seconds") != 86400:
        raise PlanRejected("SQS test queue retention must be one day")

    alarm = after("aws_cloudwatch_metric_alarm.dlq_not_empty")
    for field in ("alarm_actions", "ok_actions", "insufficient_data_actions"):
        if alarm.get(field) not in (None, []):
            raise PlanRejected("CloudWatch alarm has an unreviewed external action")
    if alarm.get("threshold") not in (0, 0.0):
        raise PlanRejected("Unexpected DLQ alarm threshold")

    return {
        "decision": "GO_FOR_MANUAL_REVIEW_ONLY_NOT_APPLY",
        "expected_resources_to_create": len(by_address),
        "changes": {"create": len(by_address), "update": 0, "delete": 0},
        "region": expected_region,
        "identity_verified": True,
        "project": "geolife-s2b-synthetic-only",
        "terraform_apply_authorized": False,
        "required_next_gates": [
            "Confirm AWS budget and cost buffer manually (10 USD total)",
            "Review full Terraform plan locally, never share raw plan",
            "Review EC2 SSM/network and narrow IAM policy before attachment",
            "Explicit human approval before apply",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Reject any S2b plan beyond approved resource allowlist")
    parser.add_argument("plan_json", type=Path)
    parser.add_argument("--expected-account", required=True, help="Twelve-digit AWS account ID (local only)")
    args = parser.parse_args()
    try:
        data = json.loads(args.plan_json.read_text(encoding="utf-8-sig"))
        result = validate_plan(data, expected_account=args.expected_account)
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # Never print raw input or resource attributes, even for parse errors.
        raise SystemExit(f"S2B_PLAN_REJECTED: {type(exc).__name__}; inspect privately") from None
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
