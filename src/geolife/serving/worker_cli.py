"""Bounded AWS S2b worker entrypoint for the installed serving image.

Run only after approved synthetic-only SQS provisioning and private IAM setup:
  python -m geolife.serving.worker_cli --max-polls 20
"""
from __future__ import annotations

import argparse

from .aws_s2b import AwsAsyncJobs, ConfigurationError


def main() -> None:
    parser = argparse.ArgumentParser(description="GeoLife S2b private synthetic worker")
    parser.add_argument("--max-polls", type=int, default=1)
    args = parser.parse_args()
    if not 1 <= args.max_polls <= 100:
        parser.error("--max-polls must be between 1 and 100")
    try:
        client = AwsAsyncJobs.from_environment()
    except ConfigurationError:
        parser.error("S2b disabled or not configured")
    received = 0
    for _ in range(args.max_polls):
        if client.process_once():
            received += 1
    print(f"synthetic_s2b_queue_messages_seen={received}")


if __name__ == "__main__":
    main()
