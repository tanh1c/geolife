"""Read-only reconciliation of S2b resources after a failed Terraform apply.

Does NOT mutate AWS, Terraform state, roles, queues, buckets, or instance state.
Exits NO-GO when any resource exists OR an API cannot positively verify absence.
Do not trust Terraform state alone after partial/failed apply.
"""
from __future__ import annotations

import argparse
import json
import re
from typing import Any


PREFIX = "geolife-mle-s2b-dev"
REGION = "ap-southeast-1"


def expected_names(account: str) -> dict[str, str]:
    if not re.fullmatch(r"\d{12}", account):
        raise ValueError("Expected AWS account must be 12 digits")
    return {
        "s3_bucket": f"{PREFIX}-{account}-{REGION}",
        "ddb_table": f"{PREFIX}-jobs",
        "sqs_jobs": f"{PREFIX}-jobs",
        "sqs_dlq": f"{PREFIX}-dlq",
        "cloudwatch_alarm": f"{PREFIX}-dlq-not-empty",
    }


def _status(check: Any, missing_codes: set[str]) -> str:
    try:
        check()
        return "PRESENT"
    except Exception as exc:
        # botocore ClientError carries a typed AWS error code. All other
        # exceptions, including lack of permission or timeouts, are NO-GO.
        payload = getattr(exc, "response", None)
        error = payload.get("Error", {}) if isinstance(payload, dict) else {}
        code = str(error.get("Code", ""))
        return "ABSENT" if code in missing_codes else "UNKNOWN"


def inspect(
    *,
    s3: Any,
    ddb: Any,
    sqs: Any,
    cloudwatch: Any,
    sts: Any,
    account: str,
) -> dict[str, object]:
    names = expected_names(account)
    try:
        reported_account = sts.get_caller_identity()["Account"]
    except Exception:
        return {"decision": "NO_GO", "reason": "identity_not_verified"}
    if reported_account != account:
        return {"decision": "NO_GO", "reason": "wrong_account"}

    checks = {
        "s3_bucket": _status(
            lambda: s3.head_bucket(Bucket=names["s3_bucket"]),
            {"404", "NoSuchBucket", "NotFound"},
        ),
        "ddb_table": _status(
            lambda: ddb.describe_table(TableName=names["ddb_table"]),
            {"ResourceNotFoundException"},
        ),
        "sqs_jobs": _status(
            lambda: sqs.get_queue_url(QueueName=names["sqs_jobs"]),
            {"AWS.SimpleQueueService.NonExistentQueue", "QueueDoesNotExist",
             "NonExistentQueue"},
        ),
        "sqs_dlq": _status(
            lambda: sqs.get_queue_url(QueueName=names["sqs_dlq"]),
            {"AWS.SimpleQueueService.NonExistentQueue", "QueueDoesNotExist",
             "NonExistentQueue"},
        ),
    }
    try:
        response = cloudwatch.describe_alarms(
            AlarmNames=[names["cloudwatch_alarm"]]
        )
        matches = response.get("MetricAlarms", []) + response.get("CompositeAlarms", [])
        checks["cloudwatch_alarm"] = "PRESENT" if matches else "ABSENT"
    except Exception:
        checks["cloudwatch_alarm"] = "UNKNOWN"

    all_absent = all(value == "ABSENT" for value in checks.values())
    return {
        "decision": "READY_FOR_NEW_PLAN_REVIEW_ONLY" if all_absent else "NO_GO",
        "source": "aws_read_only_resource_describes",
        "region": REGION,
        "checks": checks,
        "all_five_resources_confirmed_absent": all_absent,
        "terraform_apply_authorized": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Read-only verify no S2b AWS resources survived failed apply"
    )
    parser.add_argument("--profile", default="geolife-terraform")
    parser.add_argument("--expected-account", required=True)
    args = parser.parse_args()
    try:
        import boto3
        session = boto3.Session(profile_name=args.profile, region_name=REGION)
        result = inspect(
            s3=session.client("s3"), ddb=session.client("dynamodb"),
            sqs=session.client("sqs"), cloudwatch=session.client("cloudwatch"),
            sts=session.client("sts"), account=args.expected_account,
        )
    except Exception:
        result = {"decision": "NO_GO", "reason": "read_only_check_unavailable"}
    print(json.dumps(result, indent=2))
    if result["decision"] != "READY_FOR_NEW_PLAN_REVIEW_ONLY":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
