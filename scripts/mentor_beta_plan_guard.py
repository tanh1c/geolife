"""Initial Phase A CREATE-only plan guard. Not APPLY authorization."""
import argparse
import json
from pathlib import Path

ALLOWED = {
    "aws_s3_bucket.site",
    "aws_s3_bucket_public_access_block.site",
    "aws_s3_bucket_server_side_encryption_configuration.site",
    "aws_s3_bucket_versioning.site",
    "aws_cloudfront_origin_access_control.site",
    "aws_cloudfront_response_headers_policy.spa",
    "aws_cloudfront_distribution.site",
    "aws_s3_bucket_policy.site",
    "aws_cognito_user_pool.invite",
    "aws_cognito_user_group.testers",
    "aws_cognito_resource_server.demo",
    "aws_cognito_user_pool_domain.login",
    "aws_cognito_user_pool_client.spa",
    "aws_cognito_managed_login_branding.spa",
}


def validate(plan):
    changes = plan.get("resource_changes")
    if not isinstance(changes, list):
        raise ValueError("Missing resource_changes")
    observed = set()
    for change in changes:
        if change.get("mode") != "managed":
            continue
        addr = change.get("address")
        if addr not in ALLOWED or addr in observed:
            raise ValueError("Unexpected/duplicate managed resource")
        if change.get("change", {}).get("actions") != ["create"]:
            raise ValueError("Only initial CREATE actions are allowed")
        observed.add(addr)
    if observed != ALLOWED:
        raise ValueError("Missing approved resource creates")
    values = plan.get("variables", {})
    for key, expected in (
        ("aws_region", "ap-southeast-1"),
        ("account_id", "939169265033"),
        ("api_gateway_origin", ""),
    ):
        if key in values and values[key].get("value") != expected:
            raise ValueError("Unexpected plan variable " + key)
    return {"phase": "foundation", "create": len(observed), "update": 0,
            "delete": 0, "replace": 0, "apply_approved": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--plan-json", required=True, type=Path)
    args = p.parse_args()
    try:
        summary = validate(json.loads(args.plan_json.read_text(encoding="utf-8")))
    except (ValueError, OSError, TypeError) as ex:
        print("PLAN_GUARD_FAIL:", str(ex).splitlines()[0][:120])
        raise SystemExit(2)
    print("PLAN_GUARD_PASS:", json.dumps(summary))


if __name__ == "__main__":
    main()
