"""Strict saved-plan JSON review: bridge initial CREATE or in-place EC2 SG attach.

This is an offline decision gate, NOT AWS plan execution, approval, or APPLY.
Do not print plan JSON: it can include private infrastructure metadata.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

BRIDGE_RESOURCES = {
    "aws_security_group.alb",
    "aws_security_group.backend",
    "aws_vpc_security_group_egress_rule.alb_to_backend",
    "aws_vpc_security_group_ingress_rule.backend_from_alb",
    "aws_lb.private",
    "aws_lb_target_group.beta",
    "aws_lb_target_group_attachment.current_ec2",
    "aws_lb_listener.http_internal",
}
IMMUTABLE_EC2_FIELDS = (
    "id", "ami", "instance_type", "subnet_id", "iam_instance_profile",
    "associate_public_ip_address", "user_data", "private_ip",
)


def _managed_changes(plan: dict) -> list[dict]:
    rows = plan.get("resource_changes")
    if not isinstance(rows, list):
        raise ValueError("MISSING_RESOURCE_CHANGES")
    return [row for row in rows if row.get("mode") == "managed"]


def bridge_guard(plan: dict) -> dict:
    rows = _managed_changes(plan)
    seen: set[str] = set()
    for row in rows:
        address = row.get("address")
        actions = row.get("change", {}).get("actions")
        if address not in BRIDGE_RESOURCES or address in seen:
            raise ValueError("UNEXPECTED_OR_DUPLICATE_BRIDGE_RESOURCE")
        if actions != ["create"]:
            raise ValueError("BRIDGE_MUST_BE_CREATE_ONLY")
        seen.add(address)
    if seen != BRIDGE_RESOURCES:
        raise ValueError("INCOMPLETE_BRIDGE_RESOURCE_SET")
    variables = plan.get("variables", {})
    if variables.get("account_id", {}).get("value", "939169265033") != "939169265033":
        raise ValueError("WRONG_ACCOUNT")
    if variables.get("existing_ec2_instance_id", {}).get("value", "i-0dfcfa110c0fd8af1") != "i-0dfcfa110c0fd8af1":
        raise ValueError("WRONG_EC2_TARGET")
    if variables.get("beta_backend_port", {}).get("value", 18080) != 18080:
        raise ValueError("WRONG_BETA_PORT")
    return {"gate": "BRIDGE_CREATE_ONLY", "create": 8, "update": 0,
            "delete": 0, "replace": 0, "apply_approved": False}


def ec2_attach_guard(plan: dict, expected_backend_sg: str) -> dict:
    if not re.fullmatch(r"sg-[0-9a-f]{8,17}", expected_backend_sg):
        raise ValueError("INVALID_EXPECTED_BACKEND_SG")
    rows = _managed_changes(plan)
    changed = [r for r in rows if r.get("change", {}).get("actions") != ["no-op"]]
    if len(changed) != 1 or changed[0].get("address") != "aws_instance.api":
        raise ValueError("EC2_PLAN_MUST_HAVE_EXACTLY_ONE_UPDATE")
    change = changed[0]["change"]
    if change.get("actions") != ["update"]:
        raise ValueError("INSTANCE_REPLACEMENT_OR_DESTROY_BLOCKED")
    before, after = change.get("before"), change.get("after")
    if not isinstance(before, dict) or not isinstance(after, dict):
        raise ValueError("MISSING_INSTANCE_DIFF")
    # Compare EVERY serialized attribute, not just a handpicked subset.
    # A changed tag, user_data, IMDS setting, instance type, or computed field
    # is out-of-scope until a human separately reviews the discrepancy.
    for field in set(before) | set(after):
        if field != "vpc_security_group_ids" and before.get(field) != after.get(field):
            raise ValueError("NON_SG_INSTANCE_CHANGE_" + field.upper())
    old = before.get("vpc_security_group_ids")
    new = after.get("vpc_security_group_ids")
    if not isinstance(old, list) or not isinstance(new, list) or not old:
        raise ValueError("MISSING_EC2_SECURITY_GROUPS")
    if len(set(old)) != len(old) or len(set(new)) != len(new):
        raise ValueError("DUPLICATE_EC2_SECURITY_GROUPS")
    if set(new) != set(old) | {expected_backend_sg} or expected_backend_sg in old:
        raise ValueError("SG_ATTACHMENT_MUST_ONLY_ADD_REVIEWED_SG")
    return {"gate": "EC2_SG_ATTACH_IN_PLACE", "create": 0, "update": 1,
            "delete": 0, "replace": 0, "apply_approved": False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", choices=("bridge", "ec2-attach"), required=True)
    parser.add_argument("--plan-json", type=Path, required=True)
    parser.add_argument("--backend-sg", default="")
    args = parser.parse_args()
    try:
        plan = json.loads(args.plan_json.read_text(encoding="utf-8"))
        result = (bridge_guard(plan) if args.phase == "bridge" else
                  ec2_attach_guard(plan, args.backend_sg))
    except (OSError, ValueError, TypeError) as exc:
        print("PLAN_GUARD_FAIL", str(exc).splitlines()[0][:120])
        raise SystemExit(2) from None
    print("PLAN_GUARD_PASS", json.dumps(result))


if __name__ == "__main__":
    main()
