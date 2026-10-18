"""Cognito signed access tokens for invitation-only synthetic demo.

Cognito sub is an app principal, NOT proof of GeoLife historical GPS ownership.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from functools import lru_cache

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_BEARER = HTTPBearer(auto_error=False)
_REGION = re.compile(r"^[a-z]{2}-[a-z]+-\d$")
_POOL = re.compile(r"^[a-z]{2}-[a-z]+-\d_[a-zA-Z0-9]+$")
_FIXTURE = re.compile(r"^demo_00[0-3]$")


def beta_enabled() -> bool:
    return os.getenv("GEOLIFE_PUBLIC_BETA") == "1"


def _settings() -> tuple[str, str, str, str, dict[str, str]]:
    region = os.getenv("GEOLIFE_COGNITO_REGION", "")
    pool = os.getenv("GEOLIFE_COGNITO_USER_POOL_ID", "")
    client_id = os.getenv("GEOLIFE_COGNITO_CLIENT_ID", "")
    group = os.getenv("GEOLIFE_COGNITO_TESTER_GROUP", "geolife-demo-testers")
    scope = os.getenv("GEOLIFE_COGNITO_SCOPE", "geolife-demo/read")
    try:
        mapping = json.loads(os.getenv("GEOLIFE_BETA_SUBJECT_FIXTURE_MAP", ""))
    except ValueError:
        mapping = None
    if not (_REGION.fullmatch(region) and _POOL.fullmatch(pool)
            and pool.startswith(region + "_") and client_id and group and scope
            and isinstance(mapping, dict) and 1 <= len(mapping) <= 4
            and all(isinstance(k, str) and k and isinstance(v, str)
                    and _FIXTURE.fullmatch(v) for k, v in mapping.items())
            and len(set(mapping.values())) == len(mapping)):
        raise HTTPException(503, "Beta identity configuration unavailable")
    return (f"https://cognito-idp.{region}.amazonaws.com/{pool}",
            client_id, group, scope, mapping)


@lru_cache(maxsize=4)
def _jwks(issuer: str) -> jwt.PyJWKClient:
    return jwt.PyJWKClient(issuer + "/.well-known/jwks.json",
                           cache_jwk_set=True, lifespan=300)


def current_beta_principal(
    credentials: HTTPAuthorizationCredentials | None = Depends(_BEARER),
) -> tuple[str, str]:
    """Return only (opaque app principal, synthetic fixture owner)."""
    if not beta_enabled():
        raise HTTPException(404, "Not found")
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(401, "Authentication required")
    issuer, client_id, group, scope, mapping = _settings()
    try:
        token = credentials.credentials
        key = _jwks(issuer).get_signing_key_from_jwt(token).key
        payload = jwt.decode(
            token, key, algorithms=["RS256"], issuer=issuer,
            options={"verify_aud": False,
                     "require": ["iss", "sub", "iat", "exp", "token_use", "client_id"]},
            leeway=0,
        )
    except (jwt.PyJWTError, ValueError, OSError):
        raise HTTPException(401, "Invalid access token") from None
    if payload.get("token_use") != "access" or payload.get("client_id") != client_id:
        raise HTTPException(401, "Invalid access token")
    if scope not in str(payload.get("scope", "")).split():
        raise HTTPException(403, "Insufficient scope")
    groups = payload.get("cognito:groups")
    if not isinstance(groups, list) or group not in groups:
        raise HTTPException(403, "Tester group required")
    sub = payload.get("sub")
    if not isinstance(sub, str) or not sub:
        raise HTTPException(401, "Invalid access token")
    owner = mapping.get(sub)
    if owner is None:
        raise HTTPException(403, "Unprovisioned test account")
    principal = hashlib.sha256((issuer + "\0" + sub).encode()).hexdigest()[:24]
    return principal, owner
