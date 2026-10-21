from __future__ import annotations

import json
import os
import time
from functools import lru_cache
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import InvalidTokenError

from .demo_auth import DemoAccount, _require_credentials

_BEARER = HTTPBearer(auto_error=False)
_JWKS_TTL = 300


def _config() -> tuple[str, str]:
    region = os.getenv("COGNITO_REGION", "ap-southeast-1")
    pool_id = os.getenv("COGNITO_USER_POOL_ID", "")
    client_id = os.getenv("COGNITO_CLIENT_ID", "")
    if not pool_id or not client_id:
        raise HTTPException(status_code=503, detail="Cognito authentication is not configured")
    return f"https://cognito-idp.{region}.amazonaws.com/{pool_id}", client_id


@lru_cache(maxsize=4)
def _jwks(issuer: str, bucket: int) -> dict[str, Any]:
    del bucket
    try:
        with urlopen(f"{issuer}/.well-known/jwks.json", timeout=3) as response:
            return json.loads(response.read())
    except (OSError, URLError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Identity provider unavailable") from None


def verify_access_token(token: str) -> tuple[str, str]:
    issuer, client_id = _config()
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise InvalidTokenError("Unsupported key")
        keys = _jwks(issuer, int(time.time()) // _JWKS_TTL).get("keys", [])
        jwk = next(key for key in keys if key.get("kid") == header["kid"])
        claims = jwt.decode(
            token, jwt.PyJWK.from_dict(jwk, algorithm="RS256").key,
            algorithms=["RS256"], issuer=issuer,
            options={"require": ["iss", "sub", "exp", "token_use", "client_id"]}, leeway=30,
        )
        if claims.get("token_use") != "access" or claims.get("client_id") != client_id:
            raise InvalidTokenError("Wrong token use or client")
        if "geolife-demo/read" not in str(claims.get("scope", "")).split():
            raise InvalidTokenError("Required scope missing")
        subject = claims.get("sub")
        if claims.get("iss") != issuer or not isinstance(subject, str) or not subject:
            raise InvalidTokenError("Wrong subject")
        return issuer, subject
    except (InvalidTokenError, StopIteration, KeyError, TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid bearer token") from None


def cognito_current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(_BEARER),
) -> DemoAccount:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=401, detail="Authentication required")
    issuer, subject = verify_access_token(credentials.credentials)
    return DemoAccount(account_id=subject, dataset_user_id="", issuer=issuer, subject=subject)


def synthetic_current_account(
    credentials: HTTPAuthorizationCredentials | None = Depends(_BEARER),
) -> DemoAccount:
    mode = os.getenv("GEOLIFE_AUTH_MODE", "private_demo")
    if mode == "cognito":
        return cognito_current_account(credentials)
    if mode == "private_demo":
        return _require_credentials(credentials)[0]
    raise HTTPException(status_code=503, detail="Authentication mode is not configured")
