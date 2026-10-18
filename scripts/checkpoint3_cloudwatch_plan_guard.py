"""Local-only allowlist for a privately saved Checkpoint 3 Terraform JSON plan."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


EXPECTED = {
    "aws_cloudwatch_log_group.s2b_telemetry": "aws_cloudwatch_log_group",
    "aws_cloudwatch_dashboard.s2b_telemetry": "aws_cloudwatch_dashboard",
}
DASHBOARD = Path(__file__).resolve().parent.parent / "docs/design/checkpoint3_s2b_dashboard_review.json"


def check(data: dict) -> None:
    if (data.get("errored") or data.get("resource_drift")
            or data.get("prior_state") or data.get("variables")
            or data.get("output_changes")):
        raise ValueError("Errored plan, drift, existing state, outputs or variable override")
    config_all = data.get("configuration", {})
    providers = config_all.get("provider_config", {})
    if (set(providers) != {"aws"}
            or providers["aws"].get("name") != "aws"
            or providers["aws"].get("expressions", {}).get("region", {}).get("constant_value") != "ap-southeast-1"):
        raise ValueError("Unexpected provider region or alias")
    config = config_all.get("root_module", {})
    resources = config.get("resources")
    if (not isinstance(resources, list) or len(resources) != len(EXPECTED)
            or config.get("module_calls") or config.get("outputs") or config.get("variables")
            or {row.get("address") for row in resources} != set(EXPECTED)
            or any(row.get("mode") != "managed" or row.get("type") != EXPECTED.get(row.get("address"))
                   or row.get("provider_config_key") != "aws" for row in resources)):
        raise ValueError("Unexpected Terraform configuration resources")
    planned = data.get("planned_values", {}).get("root_module", {})
    planned_resources = planned.get("resources")
    if (not isinstance(planned_resources, list) or len(planned_resources) != len(EXPECTED)
            or planned.get("child_modules")
            or {row.get("address") for row in planned_resources} != set(EXPECTED)
            or any(row.get("mode") != "managed" or row.get("type") != EXPECTED.get(row.get("address"))
                   for row in planned_resources)):
        raise ValueError("Unexpected Terraform planned resources")
    changes = data.get("resource_changes")
    if not isinstance(changes, list) or len(changes) != len(EXPECTED):
        raise ValueError("Expected exactly two new resources")
    seen = set()
    for row in changes:
        addr = row.get("address")
        change = row.get("change", {})
        if (addr not in EXPECTED or addr in seen or row.get("mode") != "managed"
                or row.get("type") != EXPECTED[addr] or change.get("actions") != ["create"]
                or change.get("before") is not None):
            raise ValueError("Unexpected resource or non-create action")
        after = change.get("after")
        planned_after = next(item["values"] for item in planned_resources if item["address"] == addr)
        if (not isinstance(after, dict)
                or any(value != planned_after.get(key) for key, value in after.items())):
            raise ValueError("Proposed resource differs from planned values")
        if addr.startswith("aws_cloudwatch_log_group"):
            if (after.get("name") != "/geolife/dev/s2b-telemetry"
                    or after.get("retention_in_days") != 7
                    or after.get("log_group_class") != "STANDARD"):
                raise ValueError("Unexpected log group configuration")
        elif (after.get("dashboard_name") != "geolife-dev-s2b-synthetic-review"
              or not isinstance(after.get("dashboard_body"), str)
              or json.loads(after["dashboard_body"]) != json.loads(DASHBOARD.read_text(encoding="utf-8"))):
            raise ValueError("Dashboard differs from locally reviewed JSON")
        seen.add(addr)
    if seen != set(EXPECTED):
        raise ValueError("Missing required resource")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check local JSON plan only; never applies Terraform")
    parser.add_argument("plan_json", type=Path)
    args = parser.parse_args()
    try:
        check(json.loads(args.plan_json.read_text(encoding="utf-8-sig")))
    except (OSError, ValueError, TypeError, KeyError):
        raise SystemExit("CHECKPOINT3_PLAN_REJECTED; inspect saved plan privately") from None
    print("REVIEW_ONLY: exactly two allowlisted creates; not apply authorization")


if __name__ == "__main__":
    main()
