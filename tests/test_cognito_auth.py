from __future__ import annotations

import hashlib
import json
import time

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.testclient import TestClient
from jwt.algorithms import RSAAlgorithm

from geolife.api import async_jobs, cognito_auth
from geolife.api.app import app
from geolife.api.demo_auth import provision_account


class _OwnedJobs:
    def __init__(self):
        self.owner = ""

    def create(self, owner, **kwargs):
        self.owner = owner
        return {"job_id": "a" * 64, "status": "pending", "model_version": kwargs["variant"]}

    def get(self, owner, jid):
        if owner != self.owner:
            return None
        return {"job_id": jid, "status": "pending", "model_version": "cp2-v2-complete-link-200m"}


def _cognito_credentials(subject: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {subject}"}


def test_cognito_owner_scoped_routes_and_private_demo_unchanged(monkeypatch, tmp_path):
    db = tmp_path / "private_demo.sqlite3"
    provision_account(db, "demo_000", "000", "test-only-long-secret-for-000")
    monkeypatch.setenv("GEOLIFE_DEMO_AUTH_DB", str(db))
    monkeypatch.setenv("GEOLIFE_AUTH_MODE", "cognito")
    monkeypatch.setenv("GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER", "1")
    monkeypatch.setenv("GEOLIFE_S2B_ENABLE", "1")
    jobs = _OwnedJobs()
    app.dependency_overrides[async_jobs._backend] = lambda: jobs
    try:
        _assert_cognito_routes(monkeypatch)
    finally:
        app.dependency_overrides.pop(async_jobs._backend, None)


def _assert_cognito_routes(monkeypatch):
    def verified_subject(token):
        if token not in ("subject-a", "subject-b"):
            raise HTTPException(status_code=401, detail="Invalid bearer token")
        return ISSUER, token

    monkeypatch.setattr(cognito_auth, "verify_access_token", verified_subject)
    client = TestClient(app)
    owner_a = _cognito_credentials("subject-a")
    owner_b = _cognito_credentials("subject-b")
    when = {"when": "2026-09-24T08:00:00+07:00"}
    a = client.get("/v2/me/destination-suggestions", params=when, headers=owner_a)
    b = client.get("/v2/me/destination-suggestions", params=when, headers=owner_b)
    assert a.status_code == b.status_code == 200
    assert a.json()["status"] == b.json()["status"] == "suggested"
    assert {x["place_ref"] for x in a.json()["suggestions"]}.isdisjoint(
        {x["place_ref"] for x in b.json()["suggestions"]}
    )
    assert all(len(x["place_ref"].split("_", 1)[0]) == 33 for x in a.json()["suggestions"])
    assert "dataset_user_id" not in a.text
    assert a.json()["suggestions"][0]["place_ref"].endswith("_office")
    evening = client.get("/v2/me/destination-suggestions", params={"when": "2026-09-24T18:00:00+07:00"}, headers=owner_a)
    assert evening.status_code == 200
    assert evening.json()["suggestions"][0]["place_ref"].endswith("_home")
    assert "subject-a" not in evening.text
    submitted = client.post("/v2/jobs", json={"fixture": "short_observation"},
                            headers={**owner_a, "Idempotency-Key": "cognito-owner-001"})
    assert submitted.status_code == 202, submitted.text
    job_id = submitted.json()["job_id"]
    assert client.get(f"/v2/jobs/{job_id}", headers=owner_a).status_code == 200
    assert client.get(f"/v2/jobs/{job_id}", headers=owner_b).status_code == 404
    assert client.get("/v2/auth/me", headers=owner_a).status_code == 503
    assert client.post("/v2/auth/login", json={
        "account_id": "demo_000", "password": "test-only-long-secret-for-000",
    }).status_code == 503
    assert client.get("/v2/me/destination-suggestions", params=when,
                      headers={"Authorization": "Bearer demo-token"}).status_code == 401
    assert client.get(f"/v2/jobs/{job_id}",
                      headers={"Authorization": "Bearer demo-token"}).status_code == 401
    assert client.get("/v2/me/destination-suggestions", params=when).status_code == 401
    assert client.get(f"/v2/jobs/{job_id}").status_code == 401
    monkeypatch.delenv("GEOLIFE_DEMO_AUTH_DB")
    assert client.post("/v2/me/inferences", json={"points": []}, headers=owner_a).status_code == 503
    assert client.post("/v2/me/dataset-inferences", headers=owner_a).status_code == 503
    assert client.post("/v2/inferences", json={}, headers=owner_a).status_code == 404
    assert client.post("/v1/classify/000", json={}, headers=owner_a).status_code == 404


ISSUER = "https://cognito-idp.ap-southeast-1.amazonaws.com/ap-southeast-1_test"
CLIENT = "spa-client"


def _token(private_key, **overrides):
    claims = {
        "iss": ISSUER,
        "sub": "subject-123",
        "exp": int(time.time()) + 300,
        "token_use": "access",
        "client_id": CLIENT,
        "scope": "openid geolife-demo/read",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="RS256", headers={"kid": "test-key"})


def test_cognito_access_token_claims_and_signature(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    jwk = RSAAlgorithm.to_jwk(public_key, as_dict=True)
    jwk["kid"] = "test-key"
    monkeypatch.setenv("COGNITO_REGION", "ap-southeast-1")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "ap-southeast-1_test")
    monkeypatch.setenv("COGNITO_CLIENT_ID", CLIENT)
    monkeypatch.setattr(cognito_auth, "_jwks", lambda *_: {"keys": [jwk]})

    assert cognito_auth.verify_access_token(_token(private_key)) == (ISSUER, "subject-123")
    for invalid_claims in (
        {"iss": ISSUER + "-wrong"},
        {"token_use": "id"},
        {"client_id": "another-client"},
        {"scope": "openid"},
        {"exp": int(time.time()) - 60},
    ):
        try:
            cognito_auth.verify_access_token(_token(private_key, **invalid_claims))
        except HTTPException as exc:
            assert exc.status_code == 401
        else:
            raise AssertionError(f"accepted invalid claims: {invalid_claims}")

    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    try:
        cognito_auth.verify_access_token(_token(other_key))
    except HTTPException as exc:
        assert exc.status_code == 401
    else:
        raise AssertionError("accepted invalid signature")


def test_cognito_identity_is_issuer_and_subject_scoped(monkeypatch):
    monkeypatch.setattr(cognito_auth, "verify_access_token", lambda _: (ISSUER, "same-sub"))
    credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials="opaque")
    account = cognito_auth.cognito_current_account(credentials)
    assert account.issuer == ISSUER
    assert account.subject == "same-sub"
    assert account.dataset_user_id == ""
    assert account.owner_id == "cog_" + hashlib.sha256(
        f"{ISSUER}\x00same-sub".encode()
    ).hexdigest()[:60]


def test_research_curated_profiles_for_every_cognito_account(monkeypatch, tmp_path, caplog):
    from geolife.recommendation.fixtures import commute_points
    from geolife.api.schemas import ClassifyRequest
    from geolife.api.service import raw_request_to_stay_frame

    stays = raw_request_to_stay_frame(
        "001", ClassifyRequest.model_validate({"points": commute_points()})
    )
    stays.to_pickle(tmp_path / "stays.pkl")
    mapping = tmp_path / "cases.json"
    mapping.write_text(json.dumps({"cases": {"demo-profile": "001", "second-profile": "002"}}))
    monkeypatch.setenv("GEOLIFE_AUTH_MODE", "cognito")
    monkeypatch.setenv("GEOLIFE_RESEARCH_CASES", str(mapping))
    monkeypatch.setenv("GEOLIFE_STAYS_CACHE", str(tmp_path / "stays.pkl"))
    monkeypatch.setattr(cognito_auth, "verify_access_token", lambda token: (ISSUER, token) if token in ("subject-a", "subject-b") else (_ for _ in ()).throw(HTTPException(status_code=401)))
    client = TestClient(app, client=("127.0.0.1", 49152))
    base = "/v2/research/cases"
    assert client.get(base).status_code == 401
    assert client.get(base, headers=_cognito_credentials("bad")).status_code == 401
    headers = _cognito_credentials("subject-a")
    listed = client.get(base, headers=headers)
    assert listed.status_code == 200
    assert listed.json() == {"cases": [{"alias": "demo-profile", "user_id": "001"}, {"alias": "second-profile", "user_id": "002"}]}
    assert client.get(base, headers=_cognito_credentials("subject-b")).json() == listed.json()
    assert listed.headers["cache-control"] == "no-store"
    assert client.post(base, headers=headers, json={"alias": "unknown"}).status_code == 404
    assert client.post(base, headers=_cognito_credentials("subject-b"), json={"alias": "demo-profile"}).status_code == 200
    response = client.post(base, headers=headers, json={"alias": "demo-profile"})
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["case_alias"] == "demo-profile" and result["user_id"] == "001"
    assert result["stay_count"] > 0 and result["recurring_location_count"] > 0
    assert result["model_version"] == "cp2-v2-complete-link-200m"
    assert result["predictions"]["HOME"]["status"] == "emitted"
    assert result["predictions"]["OFFICE"]["status"] == "emitted"
    assert len(result["stops"]) == result["stay_count"]
    assert all(isinstance(stop["latitude"], float) and isinstance(stop["longitude"], float) for stop in result["stops"])
    assert {stop["label"] for stop in result["stops"]}.issubset({"HOME", "OFFICE", "STOP"})
    assert all(0 <= stop["index"] < result["stay_count"] for stop in result["stops"])
    assert all("arrival_time_utc" not in stop and "location_id" not in stop for stop in result["stops"])
    assert response.headers["cache-control"] == "no-store"
    ride = client.post(base, headers=headers, json={"alias": "demo-profile", "when": "2026-09-24T08:00:00+07:00"})
    assert ride.status_code == 200, ride.text
    suggestions = ride.json()["suggestions"]
    assert 1 <= len(suggestions) <= 3
    assert [item["rank"] for item in suggestions] == list(range(1, len(suggestions) + 1))
    assert all(item["place_ref"].startswith("loc_") and item["label"] in ("HOME", "OFFICE", "Điểm quen thuộc") for item in suggestions)
    assert all("latitude" not in item and "longitude" not in item for item in suggestions)
    assert client.post(base, headers=headers, json={"alias": "demo-profile", "when": "2026-09-24T08:00:00"}).status_code == 422
    assert client.post(base, headers=headers, json={"alias": "demo-profile", "when": "invalid"}).status_code == 422
    assert client.post(base, headers=headers, json={"alias": "unknown", "when": "2026-09-24T08:00:00+07:00"}).status_code == 404
    empty = client.post(base, headers=headers, json={"alias": "second-profile"})
    assert empty.json()["suggestions"] == []
    assert client.post(base, headers=headers, json={"alias": "second-profile", "when": "2026-09-24T08:00:00+07:00"}).json()["suggestions"] == []
    assert empty.status_code == 200 and empty.json()["user_id"] == "002" and empty.json()["stops"] == []
    assert empty.json()["predictions"]["HOME"]["status"] == "abstained"
    assert client.post(base, headers=headers, json={"alias": "001"}).status_code == 404
    assert client.post(base, headers=headers, json={"alias": "009"}).status_code == 404
    assert "latitude" not in client.get(base, headers=headers).text
    for value in (listed.text + response.text + client.post(base, headers=headers, json={"alias": "unknown"}).text):
        assert all(key not in value.lower() for key in ("dataset_user_id", "coordinate", "cache", "stays.pkl", "location_ref", "arrival_time_utc"))
    assert "latitude" not in listed.text and "longitude" not in listed.text
    assert "latitude" not in client.post(base, headers=headers, json={"alias": "unknown"}).text
    assert '"002"' not in response.text
    monkeypatch.delenv("GEOLIFE_STAYS_CACHE")
    unavailable = client.post(base, headers=headers, json={"alias": "demo-profile"})
    assert unavailable.status_code == 503
    assert unavailable.json() == {"detail": "Research preview unavailable"}
    monkeypatch.delenv("GEOLIFE_RESEARCH_CASES")
    assert client.get(base, headers=headers).status_code == 503
    assert all(private not in caplog.text for private in (str(tmp_path), "subject-a"))


def test_research_route_validates_signed_production_shaped_cognito_token(monkeypatch, tmp_path):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = RSAAlgorithm.to_jwk(private_key.public_key(), as_dict=True)
    jwk["kid"] = "test-key"
    monkeypatch.setenv("COGNITO_REGION", "ap-southeast-1")
    monkeypatch.setenv("COGNITO_USER_POOL_ID", "ap-southeast-1_test")
    monkeypatch.setenv("COGNITO_CLIENT_ID", CLIENT)
    monkeypatch.setenv("GEOLIFE_AUTH_MODE", "cognito")
    monkeypatch.setattr(cognito_auth, "_jwks", lambda *_: {"keys": [jwk]})
    mapping = tmp_path / "cases.json"
    mapping.write_text(json.dumps({"cases": {"demo-profile": "001"}}))
    monkeypatch.setenv("GEOLIFE_RESEARCH_CASES", str(mapping))
    client = TestClient(app, client=("198.51.100.9", 49152))
    assert client.get("/v2/research/cases").status_code == 401
    assert client.get("/v2/research/cases", headers=_cognito_credentials(_token(private_key, scope="openid"))).status_code == 401
    response = client.get("/v2/research/cases", headers=_cognito_credentials(_token(private_key)))
    assert response.status_code == 200
    assert response.json() == {"cases": [{"alias": "demo-profile", "user_id": "001"}]}
    assert response.headers["cache-control"] == "no-store"


def test_research_requires_cognito_even_from_public_client(monkeypatch, tmp_path):
    mapping = tmp_path / "cases.json"
    mapping.write_text(json.dumps({"cases": {"demo-profile": "001"}}))
    monkeypatch.setenv("GEOLIFE_AUTH_MODE", "cognito")
    monkeypatch.setenv("GEOLIFE_RESEARCH_CASES", str(mapping))
    monkeypatch.setattr(cognito_auth, "verify_access_token", lambda token: (ISSUER, token) if token == "subject-a" else (_ for _ in ()).throw(HTTPException(status_code=401)))
    client = TestClient(app, client=("198.51.100.9", 49152))
    assert client.get("/v2/research/cases", headers=_cognito_credentials("subject-a")).status_code == 200
    assert client.get("/v2/research/cases").status_code == 401
    assert client.get("/v2/research/cases", headers={**_cognito_credentials("bad"), "X-Forwarded-For": "127.0.0.1"}).status_code == 401


def test_private_research_routes_are_absent_from_public_openapi():
    paths = TestClient(app).get("/openapi.json").json()["paths"]
    assert all(not path.startswith("/v2/research") for path in paths)


def test_research_s3_cache_requires_pinned_version_hash_and_model(monkeypatch):
    import io

    import boto3
    from moto import mock_aws

    from geolife.api import research
    from geolife.api.schemas import ClassifyRequest
    from geolife.api.service import raw_request_to_stay_frame
    from geolife.recommendation.fixtures import commute_points

    stays = raw_request_to_stay_frame(
        "001", ClassifyRequest.model_validate({"points": commute_points()})
    )
    payload = io.BytesIO()
    stays.to_pickle(payload)
    raw = payload.getvalue()
    digest = hashlib.sha256(raw).hexdigest()
    monkeypatch.setattr(research, "CACHE_BYTES", len(raw))
    monkeypatch.setattr(research, "CACHE_SHA256", digest)
    bucket = "geolife-private-research-123456789012-ap-southeast-1"
    with mock_aws():
        s3 = boto3.client("s3", region_name="ap-southeast-1")
        s3.create_bucket(Bucket=bucket, CreateBucketConfiguration={"LocationConstraint": "ap-southeast-1"})
        s3.put_bucket_versioning(Bucket=bucket, VersioningConfiguration={"Status": "Enabled"})
        s3.put_public_access_block(Bucket=bucket, PublicAccessBlockConfiguration={
            "BlockPublicAcls": True, "IgnorePublicAcls": True,
            "BlockPublicPolicy": True, "RestrictPublicBuckets": True,
        })
        version = s3.put_object(Bucket=bucket, Key=research.CACHE_KEY, Body=raw, ServerSideEncryption="AES256", Metadata={"sha256": digest})["VersionId"]
        manifest = json.dumps({"bytes": len(raw), "sha256": digest, "s3_version_id": version, "model_version": research.BASELINE}).encode()
        manifest_version = s3.put_object(Bucket=bucket, Key=research.MANIFEST_KEY, Body=manifest, ServerSideEncryption="AES256")["VersionId"]
        monkeypatch.setenv("GEOLIFE_RESEARCH_S3_BUCKET", bucket)
        monkeypatch.setenv("GEOLIFE_RESEARCH_S3_VERSION", version)
        monkeypatch.setenv("GEOLIFE_RESEARCH_S3_MANIFEST_VERSION", manifest_version)
        assert len(research._trusted_research_stays()) == len(stays)
        monkeypatch.setenv("GEOLIFE_RESEARCH_S3_VERSION", "forged-version")
        with pytest.raises(HTTPException) as exc:
            research._trusted_research_stays()
        assert exc.value.status_code == 503
        monkeypatch.setenv("GEOLIFE_RESEARCH_S3_VERSION", version)
        s3.put_object(Bucket=bucket, Key=research.CACHE_KEY, Body=b"modified", ServerSideEncryption="AES256")
        assert len(research._trusted_research_stays()) == len(stays)
        monkeypatch.setenv("GEOLIFE_RESEARCH_S3_MANIFEST_VERSION", "forged-manifest")
        with pytest.raises(HTTPException) as exc:
            research._trusted_research_stays()
        assert exc.value.status_code == 503


def test_research_disabled_outside_cognito_mode(monkeypatch, tmp_path):
    mapping = tmp_path / "cases.json"
    mapping.write_text(json.dumps({"cases": {"demo-profile": "001"}}))
    monkeypatch.setenv("GEOLIFE_AUTH_MODE", "private_demo")
    monkeypatch.setenv("GEOLIFE_RESEARCH_CASES", str(mapping))
    monkeypatch.setattr(cognito_auth, "verify_access_token", lambda _: (ISSUER, "subject-a"))
    client = TestClient(app, client=("127.0.0.1", 49152))
    assert client.get("/v2/research/cases", headers=_cognito_credentials("subject-a")).status_code == 404


def test_research_rejects_untrusted_mapping_and_forged_dataset_selector(monkeypatch, tmp_path):
    mapping = tmp_path / "cases.json"
    mapping.write_text(json.dumps({"cases": {"demo-profile": "001"}}))
    monkeypatch.setenv("GEOLIFE_AUTH_MODE", "cognito")
    monkeypatch.setenv("GEOLIFE_RESEARCH_CASES", str(mapping))
    monkeypatch.setattr(cognito_auth, "verify_access_token", lambda _: (ISSUER, "subject-a"))
    client = TestClient(app, client=("127.0.0.1", 49152))
    headers = _cognito_credentials("subject-a")
    assert client.post("/v2/research/cases", headers=headers, json={"alias": "demo-profile", "dataset_user_id": "002"}).status_code == 422
    mapping.write_text(json.dumps({"cases": {"demo-profile": "../../private"}}))
    assert client.get("/v2/research/cases", headers=headers).status_code == 503
    assert "private" not in client.get("/v2/research/cases", headers=headers).text
