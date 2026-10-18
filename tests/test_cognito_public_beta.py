"""No Cognito/AWS traffic: locally signed test JWTs with generated RSA key."""
from __future__ import annotations

import json
import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient

from geolife.api import cognito_beta
from geolife.api.app import app

client = TestClient(app)
ME = "/v3/beta/me"
SUG = "/v3/beta/destination-suggestions"


@pytest.fixture()
def signed(monkeypatch):
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    monkeypatch.setenv("GEOLIFE_PUBLIC_BETA", "1")
    monkeypatch.setenv("GEOLIFE_COGNITO_REGION", "ap-southeast-1")
    monkeypatch.setenv("GEOLIFE_COGNITO_USER_POOL_ID", "ap-southeast-1_LOCALTEST")
    monkeypatch.setenv("GEOLIFE_COGNITO_CLIENT_ID", "test-public-client")
    monkeypatch.setenv("GEOLIFE_BETA_SUBJECT_FIXTURE_MAP", json.dumps({
        "synthetic-mentor-sub": "demo_000", "synthetic-tester-sub": "demo_001"
    }))
    monkeypatch.setattr(cognito_beta, "_jwks",
                        lambda _: SimpleNamespace(
                            get_signing_key_from_jwt=lambda _: SimpleNamespace(key=key.public_key())))
    def make(sub="synthetic-mentor-sub", **overrides):
        now = int(time.time())
        claims = {
            "iss": "https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_LOCALTEST",
            "sub": sub, "exp": now + 900, "iat": now - 5,
            "token_use": "access", "client_id": "test-public-client",
            "scope": "openid geolife-demo/read", "cognito:groups": ["geolife-demo-testers"]
        }
        claims.update(overrides)
        return {"Authorization": "Bearer " + jwt.encode(
            claims, key, algorithm="RS256", headers={"kid": "local-test-key"}
        )}
    return make


def test_public_mode_is_strict_allowlist(signed):
    assert client.get("/health").status_code == 200
    assert client.get(ME).status_code == 401
    for method, path in [
        ("get", "/docs"), ("get", "/openapi.json"), ("get", "/internal/metrics"),
        ("get", "/v2/model-info"), ("get", "/destination-demo"),
        ("post", "/v2/auth/login"), ("post", "/v2/me/dataset-inferences"),
        ("post", "/v2/jobs"), ("post", "/v1/classify/000")
    ]:
        response = getattr(client, method)(path)
        assert response.status_code == 404, (path, response.text)


def test_token_scope_group_owner_and_no_historical_data(signed):
    a = client.get(ME, headers=signed())
    b = client.get(ME, headers=signed("synthetic-tester-sub"))
    assert a.status_code == b.status_code == 200
    assert a.json()["app_user_id"] != b.json()["app_user_id"]
    assert a.json()["historical_geolife_access"] is False
    params = {"when": "2026-09-24T18:00:00+07:00", "owner_id": "demo_001",
              "dataset_user_id": "001"}
    a = client.get(SUG, params=params, headers=signed())
    b = client.get(SUG, params=params, headers=signed("synthetic-tester-sub"))
    assert a.status_code == b.status_code == 200
    assert a.json()["status"] == b.json()["status"] == "suggested"
    assert all(x["place_ref"].startswith("s0_") for x in a.json()["suggestions"])
    assert all(x["place_ref"].startswith("s1_") for x in b.json()["suggestions"])
    assert "dataset_user_id" not in a.text


@pytest.mark.parametrize("bad,status", [
    ({"token_use": "id"}, 401),
    ({"client_id": "not-this-app"}, 401),
    ({"iss": "https://attacker.invalid/"}, 401),
    ({"exp": 1}, 401),
    ({"scope": "openid"}, 403),
    ({"cognito:groups": []}, 403),
])
def test_bad_claims(signed, bad, status):
    assert client.get(ME, headers=signed(**bad)).status_code == status


def test_unmapped_tester_fails_and_missing_timezone_is_422(signed):
    assert client.get(ME, headers=signed("unmapped")).status_code == 403
    assert client.get(SUG, params={"when": "2026-09-24T18:00:00"},
                      headers=signed()).status_code == 422


def test_beta_disabled_by_default(signed, monkeypatch):
    monkeypatch.delenv("GEOLIFE_PUBLIC_BETA", raising=False)
    assert client.get(ME, headers=signed()).status_code == 404


def test_invalid_mapping_fails_closed(signed, monkeypatch):
    monkeypatch.setenv("GEOLIFE_BETA_SUBJECT_FIXTURE_MAP",
                       json.dumps({"a": "demo_000", "b": "demo_000"}))
    assert client.get(ME, headers=signed()).status_code == 503
