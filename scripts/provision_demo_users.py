"""Provision explicit GeoLife demo accounts. No public self-registration.

Examples:
  python scripts/provision_demo_users.py --db /private/geolife-demo.sqlite3 --user-id 000
  python scripts/provision_demo_users.py --db /private/geolife-demo.sqlite3 \
      --all --credentials /private/geolife-demo-credentials.csv

The --all option creates 182 *synthetic* demo accounts with random independent
passwords. It does NOT authenticate or identify the original GeoLife participants.
Credential CSV contains plaintext passwords: keep it offline, mode 0600, outside
the repository, and securely delete it after demo credential distribution.
"""
from __future__ import annotations

import argparse
import csv
import getpass
import os
import secrets
from pathlib import Path

from geolife.api.demo_auth import provision_account


def must_be_private_absolute(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        raise ValueError("Use an absolute path outside the Git repository")
    return path


def bulk_provision(db: Path, output: Path) -> int:
    if db == output:
        raise ValueError("Credential export path cannot be the auth database")
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd = os.open(output, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        with os.fdopen(fd, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["account_id", "dataset_user_id", "password"])
            for number in range(182):
                uid = f"{number:03d}"
                account_id = f"demo_{uid}"
                password = secrets.token_urlsafe(24)
                provision_account(db, account_id, uid, password)
                writer.writerow([account_id, uid, password])
    except Exception:
        # A partially provisioned DB needs explicit administrative review.
        raise
    return 182


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", required=True, help="Private absolute SQLite DB path")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--user-id", help="Single GeoLife ID (000..181)")
    mode.add_argument("--all", action="store_true", help="All 182 synthetic demo accounts")
    parser.add_argument("--account-id", help="Login name for single-account mode")
    parser.add_argument("--credentials", help="Private absolute CSV path for --all")
    args = parser.parse_args()
    db = must_be_private_absolute(args.db)
    if args.all:
        if not args.credentials:
            parser.error("--all requires --credentials")
        count = bulk_provision(db, must_be_private_absolute(args.credentials))
        print(f"Provisioned {count} demo accounts. Credentials stored privately; do not commit.")
        return
    if args.credentials:
        parser.error("--credentials is only used with --all")
    uid = args.user_id
    if uid is None or not (uid.isdigit() and len(uid) == 3):
        parser.error("Use --user-id 000..181")
    account = args.account_id or f"demo_{uid}"
    password = getpass.getpass("New demo password (12+ chars): ")
    provision_account(db, account, uid, password)
    print("Provisioned account:", account, "for dataset ID:", uid)


if __name__ == "__main__":
    main()
