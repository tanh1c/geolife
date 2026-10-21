"""Internal S2b synthetic async job API; NOT a public or private-GPS upload route."""
from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from .cognito_auth import synthetic_current_account
from .demo_auth import DemoAccount
from geolife.serving.aws_s2b import (
    AwsAsyncJobs, ConfigurationError, IdempotencyConflict, enabled,
)

router = APIRouter(tags=["async-s2b-synthetic"])


class SubmitJob(BaseModel):
    model_config = ConfigDict(extra="forbid")
    fixture: Literal["three_night_home", "short_observation"]
    model_version: Literal["cp2-v2-complete-link-200m", "cp2-v2-dbscan-100m"] = (
        "cp2-v2-complete-link-200m"
    )


class JobStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")
    job_id: str = Field(pattern=r"^[0-9a-f]{64}$")
    status: Literal["pending", "running", "succeeded", "failed"]
    model_version: str
    result: dict[str, object] | None = None


def _backend() -> AwsAsyncJobs:
    if not enabled():
        raise HTTPException(status_code=404, detail="Not found")
    try:
        return AwsAsyncJobs.from_environment()
    except ConfigurationError:
        raise HTTPException(status_code=503, detail="Async backend unavailable") from None


@router.post(
    "/v2/jobs", response_model=JobStatus, status_code=202,
    summary="Queue a fixed synthetic CP1/CP2 inference (S2b internal only)",
)
def submit_async_job(
    body: SubmitJob,
    response: Response,
    idempotency_key: str = Header(
        min_length=8, max_length=64, pattern=r"^[A-Za-z0-9._-]+$"
    ),
    account: DemoAccount = Depends(synthetic_current_account),
    backend: AwsAsyncJobs = Depends(_backend),
) -> JobStatus:
    try:
        obj = backend.create(
            owner=account.owner_id, key=idempotency_key,
            fixture=body.fixture, variant=body.model_version,
        )
    except IdempotencyConflict:
        raise HTTPException(
            status_code=409, detail="Idempotency-Key already used for another request"
        ) from None
    except Exception:
        # SDK errors or validation must not echo private AWS identities or data.
        raise HTTPException(status_code=503, detail="Async backend unavailable") from None
    response.headers["Location"] = "/v2/jobs/" + str(obj["job_id"])
    return JobStatus.model_validate(obj)


@router.get(
    "/v2/jobs/{job_id}", response_model=JobStatus,
    summary="Poll an account-owned synthetic inference job",
)
def poll_async_job(
    job_id: str,
    account: DemoAccount = Depends(synthetic_current_account),
    backend: AwsAsyncJobs = Depends(_backend),
) -> JobStatus:
    try:
        item = backend.get(owner=account.owner_id, jid=job_id)
    except Exception:
        raise HTTPException(status_code=503, detail="Async backend unavailable") from None
    if item is None:
        raise HTTPException(status_code=404, detail="Not found")
    return JobStatus.model_validate(item)
