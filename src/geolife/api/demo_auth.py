"""Explicitly provisioned demo accounts for *pseudonymous* GeoLife dataset IDs.

This is a single-project demo auth backend, not an identity provider. No GeoLife ID
is ever treated as proof of ownership. SQLite DB must live on a private mounted
filesystem, outside git. Tokens are random opaque bearer secrets; only their
SHA-256 digest is stored in the session table.
"""
from __future__ import annotations

import hashlib
import hmac
import os
import re
import secrets
import sqlite3
import time
from pathlib import Path

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

_ITERATIONS = 600_000
_TOKEN_TTL_SECONDS = 30 * 60
_BEARER = HTTPBearer(auto_error=False)
_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{3,64}$")
_DUMMY_SALT = bytes.fromhex("a4" * 16)
_DUMMY_HASH = hashlib.pbkdf2_hmac("sha256", b"demo-nonexistent", _DUMMY_SALT, _ITERATIONS)


class LoginBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    account_id: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=1024)


class LoginResult(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = _TOKEN_TTL_SECONDS
    account_id: str
    dataset_user_id: str


class DemoAccount(BaseModel):
    account_id: str
    dataset_user_id: str


def _db_path() -> Path:
    configured = os.getenv("GEOLIFE_DEMO_AUTH_DB")
    if not configured:
        raise HTTPException(
            status_code=503, detail="Demo login is not configured on this server"
        )
    path = Path(configured).expanduser()
    if not path.is_absolute():
        raise HTTPException(status_code=503, detail="Demo auth DB path must be absolute")
    if not path.exists():
        raise HTTPException(status_code=503, detail="Demo auth DB has not been provisioned")
    return path


def _connect(path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(f"file:{path}?mode=rw", uri=True, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn


def _schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS accounts (
          account_id TEXT PRIMARY KEY,
          dataset_user_id TEXT NOT NULL,
          password_salt BLOB NOT NULL,
          password_hash BLOB NOT NULL,
          failed_attempts INTEGER NOT NULL DEFAULT 0,
          locked_until INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS sessions (
          token_hash TEXT PRIMARY KEY,
          account_id TEXT NOT NULL,
          expires_at INTEGER NOT NULL,
          FOREIGN KEY(account_id) REFERENCES accounts(account_id)
        );
        CREATE INDEX IF NOT EXISTS sessions_expiry_idx ON sessions(expires_at);
        """
    )


def provision_account(path: Path, account_id: str, dataset_user_id: str, password: str) -> None:
    if not _ID_PATTERN.fullmatch(account_id):
        raise ValueError("account_id must be 3-64 ASCII letters/numbers/_/-")
    if not re.fullmatch(r"\d{3}", dataset_user_id) or not 0 <= int(dataset_user_id) <= 181:
        raise ValueError("GeoLife 1.3 dataset_user_id must be 000..181")
    if len(password) < 12:
        raise ValueError("Demo passwords must be at least 12 characters")
    path = path.expanduser().resolve()
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    if not path.exists():
        fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        os.close(fd)
    os.chmod(path, 0o600)
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, _ITERATIONS)
    with _connect(path) as conn:
        _schema(conn)
        if conn.execute(
            "SELECT 1 FROM accounts WHERE account_id=?", (account_id,)
        ).fetchone():
            raise ValueError("Account already exists. Refusing silent password reset.")
        conn.execute(
            "INSERT INTO accounts (account_id, dataset_user_id, password_salt, password_hash) "
            "VALUES (?, ?, ?, ?)", (account_id, dataset_user_id, salt, digest)
        )


def login(body: LoginBody) -> LoginResult:
    path = _db_path()
    now = int(time.time())
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT * FROM accounts WHERE account_id=?", (body.account_id,)
        ).fetchone()
        salt = bytes(row["password_salt"]) if row else _DUMMY_SALT
        expected = bytes(row["password_hash"]) if row else _DUMMY_HASH
        calculated = hashlib.pbkdf2_hmac(
            "sha256", body.password.encode("utf-8"), salt, _ITERATIONS
        )
        accepted = bool(row) and hmac.compare_digest(calculated, expected)
        if not accepted or (row and row["locked_until"] > now):
            if row and row["locked_until"] <= now:
                failed = row["failed_attempts"] + 1
                conn.execute(
                    "UPDATE accounts SET failed_attempts=?, locked_until=? WHERE account_id=?",
                    (failed, now + 900 if failed >= 5 else 0, body.account_id),
                )
            raise HTTPException(status_code=401, detail="Invalid account or password")

        conn.execute(
            "UPDATE accounts SET failed_attempts=0, locked_until=0 WHERE account_id=?",
            (body.account_id,),
        )
        token = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (token_hash, account_id, expires_at) VALUES (?, ?, ?)",
            (hashlib.sha256(token.encode()).hexdigest(), body.account_id, now + _TOKEN_TTL_SECONDS),
        )
        conn.execute("DELETE FROM sessions WHERE expires_at <= ?", (now,))
        return LoginResult(
            access_token=token,
            account_id=row["account_id"],
            dataset_user_id=row["dataset_user_id"],
        )


def _require_credentials(
    credentials: HTTPAuthorizationCredentials | None = Depends(_BEARER),
) -> tuple[DemoAccount, str]:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")
    digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
    with _connect(_db_path()) as conn:
        row = conn.execute(
            "SELECT a.account_id, a.dataset_user_id FROM sessions s "
            "JOIN accounts a ON s.account_id=a.account_id "
            "WHERE s.token_hash=? AND s.expires_at>?",
            (digest, int(time.time())),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return DemoAccount(account_id=row["account_id"], dataset_user_id=row["dataset_user_id"]), digest


def current_account(
    authenticated: tuple[DemoAccount, str] = Depends(_require_credentials),
) -> DemoAccount:
    return authenticated[0]


def logout(authenticated: tuple[DemoAccount, str] = Depends(_require_credentials)) -> dict[str, bool]:
    with _connect(_db_path()) as conn:
        conn.execute("DELETE FROM sessions WHERE token_hash=?", (authenticated[1],))
    return {"logged_out": True}
