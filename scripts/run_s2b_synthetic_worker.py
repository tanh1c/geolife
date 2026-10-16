"""Run one local/SSM-only synthetic SQS worker process.

This script polls REAL AWS when enabled. It must only be run AFTER the operator
has reviewed the Terraform plan, attached scoped IAM and approved AWS costs.
It does not create any resources and never prints raw job/payload data.
"""
from __future__ import annotations

import argparse

from geolife.serving.aws_s2b import AwsAsyncJobs, ConfigurationError


def main() -> None:
    parser = argparse.ArgumentParser(description="GeoLife S2b SSM-only synthetic worker")
    parser.add_argument("--max-polls", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.max_polls <= 100:
        parser.error("--max-polls must be between 1 and 100")
    try:
        runner = AwsAsyncJobs.from_environment()
    except ConfigurationError:
        parser.error("S2b disabled or not configured")
    received = 0
    for _ in range(args.max_polls):
        if runner.process_once():
            received += 1
    # Aggregate only: no owner/account/job/coords/exception.
    print(f"synthetic_s2b_queue_messages_seen={received}")


if __name__ == "__main__":
    main()
