"""Read-only S2b Terraform JSON plan guard. NEVER calls AWS or Terraform apply.

Input from: terraform show -json <saved-plan> > <private-json-file>.
The JSON (and binary plan) may contain sensitive configuration; store OUTSIDE git,
inspect only locally, never upload/share the plan file. Script prints types/counts
only, not resource IDs, ARNs, secrets or Terraform configuration values.
"""
from __future__ import annotations

import argparse
import hashlib
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


def drift_summary(data: dict) -> dict:
    """Summarize refresh-only differences WITHOUT exposing plan values or IDs.

    Printed paths/addresses describe schema fields, never before/after values.
    Hash covers exact drift objects, so acknowledgement is tied to this saved
    plan and is not a blanket 'ignore resource_drift' switch.
    """
    rows = data.get("resource_drift", [])
    if not isinstance(rows, list):
        raise PlanRejected("Invalid Terraform resource_drift")
    if len(rows) > len(EXPECTED_RESOURCES):
        raise PlanRejected("Unexpected number of drift entries")
    seen: set[str] = set()
    details: list[dict] = []

    def changed_paths(before: object, after: object, prefix: str = "") -> list[str]:
        if isinstance(before, dict) and isinstance(after, dict):
            found: list[str] = []
            for key in sorted(set(before) | set(after)):
                path = f"{prefix}.{key}" if prefix else key
                if key not in before or key not in after:
                    found.append(path)
                else:
                    found.extend(changed_paths(before[key], after[key], path))
            return found
        if before != after:
            # A list's element indexes can contain account/user identifiers.
            # Only display the parent attribute name, not indexes or values.
            return [prefix or "(root)"]
        return []

    for row in rows:
        if not isinstance(row, dict):
            raise PlanRejected("Malformed resource_drift item")
        addr = row.get("address")
        if (not isinstance(addr, str) or addr not in EXPECTED_RESOURCES
                or addr in seen or row.get("mode", "managed") != "managed"):
            raise PlanRejected("Unexpected, duplicate or external drift resource")
        seen.add(addr)
        change = row.get("change")
        if not isinstance(change, dict) or change.get("actions") not in (["update"], ["no-op"]):
            raise PlanRejected("Unexpected drift operation (delete/replace not allowed)")
        before, after = change.get("before"), change.get("after")
        if not isinstance(before, dict) or not isinstance(after, dict):
            raise PlanRejected("Missing structured drift before/after for review")
        paths = changed_paths(before, after)
        if change["actions"] == ["update"] and not paths:
            raise PlanRejected("Drift update with no observable changed attributes")
        details.append({
            "resource": addr,
            "observed_action": change["actions"][0],
            "changed_attribute_paths": paths,
        })
    blob = json.dumps(rows, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return {
        "count": len(details),
        "fingerprint_sha256": hashlib.sha256(blob.encode("utf-8")).hexdigest(),
        "drift": sorted(details, key=lambda d: d["resource"]),
        "displays_aws_attribute_values": False,
        "requires_manual_review": bool(details),
    }


def validate_plan(data: dict, *, expected_account: str, expected_region: str = "ap-southeast-1", allow_partial_state: bool = False, reviewed_drift_digest: str | None = None) -> dict:
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

    # Terraform's JSON plan includes distinct planned_values and prior_state.
    # Refreshed data source aws_caller_identity may exist ONLY in prior_state;
    # requiring planned_values caused a false NO-GO on the actual S2b plan.
    # Use both *unedited* representations, reject mismatches, and never
    # manufacture the identity from variables, user-provided text or plan paths.
    def resource_rows(values: object) -> list[dict]:
        if not isinstance(values, dict):
            return []
        root = values.get("root_module", {})
        if not isinstance(root, dict):
            return []
        rows = root.get("resources", [])
        if not isinstance(rows, list):
            raise PlanRejected("Malformed plan resource representation")
        return rows

    planned_rows = resource_rows(data.get("planned_values", {}))
    prior = data.get("prior_state", {})
    prior_values = prior.get("values", {}) if isinstance(prior, dict) else {}
    prior_rows = resource_rows(prior_values)

    # Default: first-time plan with no managed state (old behavior).
    # Explicit --allow-partial-state: after a FAILED apply, admit only
    # previously-managed resources from this exact approved S2b allowlist.
    managed_prior = {
        row.get("address") for row in prior_rows
        if row.get("mode", "managed") == "managed"
    }
    if managed_prior and not allow_partial_state:
        raise PlanRejected("S2b prior state contains existing managed resources")
    if not managed_prior.issubset(EXPECTED_RESOURCES):
        raise PlanRejected("S2b prior state includes unmanaged/out-of-scope resources")

    identities = [
        row.get("values", {}).get("account_id")
        for row in planned_rows + prior_rows
        if row.get("address") == "data.aws_caller_identity.current"
        and row.get("mode", "data") == "data"
    ]
    if not identities or any(identity != expected_account for identity in identities):
        raise PlanRejected("AWS caller identity in plan/prior_state differs from expected account")

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
    counts = {"create": 0, "update": 0, "delete": 0, "no_op": 0}
    for address, item in by_address.items():
        change = item.get("change", {})
        actions = change.get("actions")
        if actions == ["create"]:
            if change.get("before") is not None or address in managed_prior:
                raise PlanRejected(f"Unexpected create/recreate targeting managed resource: {address}")
            counts["create"] += 1
        elif actions == ["no-op"] and allow_partial_state:
            if address not in managed_prior or change.get("before") is None:
                raise PlanRejected(f"No-op without confirmed prior managed object: {address}")
            counts["no_op"] += 1
        else:
            # No in-place updates, replace, delete or import accepted blindly.
            raise PlanRejected(f"Unexpected action requiring human reconciliation: {address}")

    if allow_partial_state:
        no_ops = {
            addr for addr, item in by_address.items()
            if item.get("change", {}).get("actions") == ["no-op"]
        }
        if no_ops != managed_prior:
            raise PlanRejected("Prior managed object addresses must exactly match no-op objects")

    observation = drift_summary(data)
    observed_rows = data.get("resource_drift", [])
    if observed_rows and not allow_partial_state:
        raise PlanRejected("Unexpected refresh drift on first-time S2b plan")
    meaningful_drift = [
        row for row in observed_rows
        if row["change"]["actions"] != ["no-op"]
    ]
    if meaningful_drift:
        if (not isinstance(reviewed_drift_digest, str)
                or not re.fullmatch(r"[a-f0-9]{64}", reviewed_drift_digest)
                or reviewed_drift_digest != observation["fingerprint_sha256"]):
            raise PlanRejected(
                "Drift requires a review of field paths and exact --reviewed-drift-digest"
            )
        # Drift reports historical differences, not the changes to apply.
        # Constrain every drifted resource to *tracked* S2b state and an
        # unchanged planned operation. The refreshed observed object must be
        # identical to the planned no-op 'after' state. A drifting planned
        # create/update/replace/delete is NEVER eligible for acknowledgement.
        # Even a no-op planned action is not enough to bless a suspicious
        # refresh. Security-sensitive config drift requires a separate explicit
        # investigation, never a blanket digest override.
        protected_fragments = (
            "public_access", "acl", "policy", "encryption",
            "kms", "sse", "ttl", "point_in_time_recovery",
            "billing_mode", "redrive", "alarm_actions",
            "insufficient_data_actions", "ok_actions",
            "force_destroy", "visibility_timeout",
            "message_retention", "secure_transport",
            "block_public", "restrict_public",
            "principal", "permissions", "lifecycle",
        )
        for detail in observation["drift"]:
            if detail["observed_action"] == "no-op":
                continue
            if any(
                any(fragment in path.lower() for fragment in protected_fragments)
                for path in detail["changed_attribute_paths"]
            ):
                raise PlanRejected(
                    "Security-sensitive refresh drift requires separate investigation"
                )
        for row in meaningful_drift:
            addr = row["address"]
            planned = by_address.get(addr, {}).get("change", {})
            if addr not in managed_prior or planned.get("actions") != ["no-op"]:
                raise PlanRejected(f"Drift on untracked or changing resource: {addr}")
            if row["change"]["after"] != planned.get("after"):
                raise PlanRejected(f"Drift after-state differs from no-op plan: {addr}")

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
        "expected_resources_to_create": counts["create"],
        "changes": counts if allow_partial_state else {k: counts[k] for k in ("create", "update", "delete")},
        "recovery_partial_state": allow_partial_state,
        "reviewed_refresh_drift_count": len(meaningful_drift),
        "reviewed_refresh_drift_fingerprint": observation["fingerprint_sha256"] if meaningful_drift else None,
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
    parser.add_argument(
        "--allow-partial-state", action="store_true",
        help="Only for recovery after a failed apply; permit allowlisted prior resources as no-op",
    )
    parser.add_argument(
        "--inspect-drift", action="store_true",
        help="Read-only local report of resource drift field paths and SHA-256, not values",
    )
    parser.add_argument(
        "--reviewed-drift-digest", default=None,
        help="Exact drift SHA-256 after independent review; not an apply approval",
    )
    args = parser.parse_args()
    try:
        data = json.loads(args.plan_json.read_text(encoding="utf-8-sig"))
        if args.inspect_drift:
            print(json.dumps(drift_summary(data), indent=2))
            return
        result = validate_plan(
            data, expected_account=args.expected_account,
            allow_partial_state=args.allow_partial_state,
            reviewed_drift_digest=args.reviewed_drift_digest,
        )
    except (OSError, ValueError, KeyError, TypeError) as exc:
        # Never print raw input or resource attributes, even for parse errors.
        raise SystemExit(f"S2B_PLAN_REJECTED: {type(exc).__name__}; inspect privately") from None
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
