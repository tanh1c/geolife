"""Stateless v2 serving API. The frozen v1 contracts remain unchanged.

Every request is handled independently; no raw GPS is persisted or logged here.
Release-routing controls are process environment variables, never client overrides.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import uuid
from typing import Annotated, Literal

import pandas as pd
from fastapi import APIRouter, Request
from pydantic import BaseModel, ConfigDict, Field

from geolife.model import HomeOfficeConfig, build_semantic_locations, infer_home_office

from .schemas import AbstentionReason, ClassifyRequest, GpsPoint
from .service import raw_request_to_stay_frame


router = APIRouter(tags=["inference-v2"])

BASELINE = "cp2-v2-complete-link-200m"
CANDIDATE = "cp2-v2-dbscan-100m"
SUPPORTED = (BASELINE, CANDIDATE)
EVIDENCE_METHOD = "dwell_share_margin_date_support"


class InferenceRequestV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    client_request_id: str | None = Field(
        default=None,
        min_length=1,
        max_length=128,
        pattern=r"^[A-Za-z0-9._-]+$",
        description="Optional opaque routing token; never use an email, user ID or GPS.",
    )
    points: list[GpsPoint] = Field(min_length=1, max_length=20_000)


class EmittedV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["emitted"] = "emitted"
    location_ref: str = Field(pattern=r"^L[0-9]+$")
    evidence_score: float = Field(ge=0, le=1)
    evidence_method: Literal["dwell_share_margin_date_support"] = EVIDENCE_METHOD


class AbstainedV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["abstained"] = "abstained"
    reason: AbstentionReason


OutcomeV2 = Annotated[EmittedV2 | AbstainedV2, Field(discriminator="status")]


class PredictionsV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    HOME: OutcomeV2
    OFFICE: OutcomeV2


class RecurringPlaceV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    location_ref: str
    semantic_type: Literal["OTHER_RECURRING"] = "OTHER_RECURRING"
    visit_share: float = Field(ge=0, le=1)


class ModelDescriptorV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    model_id: Literal["geolife-home-office"] = "geolife-home-office"
    model_version: Literal["cp2-v2-complete-link-200m", "cp2-v2-dbscan-100m"]
    release_id: str
    routing_mode: Literal["baseline", "canary"]


class ObservationV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    raw_points: int = Field(ge=0)
    detected_stays: int = Field(ge=0)
    recurring_locations: int = Field(ge=0)


class InferenceResponseV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: str
    api_version: Literal["v2"] = "v2"
    model: ModelDescriptorV2
    observation: ObservationV2
    predictions: PredictionsV2
    other_recurring_places: list[RecurringPlaceV2]


class ModelInfoV2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    api_version: Literal["v2"] = "v2"
    baseline_model: str
    candidate_model: str
    available_models: list[str]
    routing_mode: Literal["baseline", "canary"]
    canary_percent: int = Field(ge=0, le=100)
    release_id: str


def rollout_config() -> tuple[Literal["baseline", "canary"], int]:
    mode = os.getenv("GEOLIFE_ROLLOUT_MODE", "baseline").lower()
    if mode not in ("baseline", "canary"):
        raise ValueError("GEOLIFE_ROLLOUT_MODE must be baseline or canary")
    percent = int(os.getenv("GEOLIFE_CANARY_PERCENT", "10"))
    if not 0 <= percent <= 100:
        raise ValueError("GEOLIFE_CANARY_PERCENT must be in 0..100")
    return mode, percent


def selected_model(request: InferenceRequestV2, request_id: str) -> str:
    mode, percent = rollout_config()
    if mode == "baseline" or percent == 0:
        return BASELINE
    if percent == 100:
        return CANDIDATE
    # Stable partition for the same opaque client token.  Request IDs are
    # random when no token is provided; no raw trajectory or user ID is hashed.
    token = request.client_request_id or request_id
    salt = os.getenv("GEOLIFE_CANARY_SALT", "local-demo-only-not-a-secret")
    digest = hmac.new(
        salt.encode("utf-8"), token.encode("utf-8"), hashlib.sha256
    ).digest()
    bucket = int.from_bytes(digest[:8], "big") % 10_000
    return CANDIDATE if bucket < percent * 100 else BASELINE


def model_config(variant: str) -> HomeOfficeConfig:
    if variant == BASELINE:
        return HomeOfficeConfig()
    if variant == CANDIDATE:
        return HomeOfficeConfig(clustering_method="dbscan", dbscan_eps_m=100.0)
    raise ValueError("Unknown model variant")


def release_id() -> str:
    # Inject immutable Git SHA / image digest at deployment time.
    return os.getenv("GEOLIFE_RELEASE_ID", "local-unversioned")


def empty_predictions(reason: AbstentionReason) -> PredictionsV2:
    return PredictionsV2(
        HOME=AbstainedV2(reason=reason), OFFICE=AbstainedV2(reason=reason)
    )


def make_predictions(
    emitted: pd.DataFrame, absent_reason: AbstentionReason
) -> PredictionsV2:
    by_label = {row.label: row for row in emitted.itertuples(index=False)}
    results = {}
    for label in ("HOME", "OFFICE"):
        row = by_label.get(label)
        results[label] = (
            EmittedV2(
                location_ref=f"L{int(row.location_id)}",
                evidence_score=float(row.evidence_strength),
            )
            if row is not None
            else AbstainedV2(reason=absent_reason)
        )
    return PredictionsV2(**results)


def infer_v2(request: InferenceRequestV2) -> InferenceResponseV2:
    rid = str(uuid.uuid4())
    mode, _ = rollout_config()
    variant = selected_model(request, rid)
    cfg = model_config(variant)
    stays = raw_request_to_stay_frame("_single_request_", ClassifyRequest(points=request.points))

    # Only an aggregate support summary is returned.  No precise coordinates,
    # raw points or client identity enter the public response.
    count = len(stays)
    if count == 0:
        return InferenceResponseV2(
            request_id=rid,
            model=ModelDescriptorV2(
                model_version=variant, release_id=release_id(), routing_mode=mode
            ),
            observation=ObservationV2(
                raw_points=len(request.points), detected_stays=0, recurring_locations=0
            ),
            predictions=empty_predictions(AbstentionReason.INSUFFICIENT_STAY_HISTORY),
            other_recurring_places=[],
        )

    semantic, locations = build_semantic_locations(stays, config=cfg)
    if semantic.empty:
        reason = AbstentionReason.INSUFFICIENT_SEMANTIC_EVIDENCE
        recurring = locations.iloc[0:0]
        emitted = pd.DataFrame()
    else:
        recurring = locations.loc[locations["stay_count"] >= 2].copy()
        if recurring.empty:
            reason = AbstentionReason.INSUFFICIENT_RECURRING_HISTORY
            emitted = pd.DataFrame()
        else:
            reason = AbstentionReason.INSUFFICIENT_SEMANTIC_EVIDENCE
            emitted = infer_home_office(stays, config=cfg)

    predictions = make_predictions(emitted, reason)
    used_ids = set(
        int(row.location_id) for row in emitted.itertuples(index=False)
    ) if not emitted.empty else set()
    other = recurring.loc[
        ~recurring["location_id"].astype(int).isin(used_ids)
    ].sort_values(
        ["stay_count", "total_dwell_h", "location_id"],
        ascending=[False, False, True],
        kind="stable",
    )
    places = [
        RecurringPlaceV2(
            location_ref=f"L{int(row.location_id)}",
            visit_share=min(float(row.stay_count) / len(semantic), 1.0),
        )
        for row in other.itertuples(index=False)
    ]
    return InferenceResponseV2(
        request_id=rid,
        model=ModelDescriptorV2(
            model_version=variant, release_id=release_id(), routing_mode=mode
        ),
        observation=ObservationV2(
            raw_points=len(request.points),
            detected_stays=count,
            recurring_locations=len(recurring),
        ),
        predictions=predictions,
        other_recurring_places=places,
    )


@router.post(
    "/v2/inferences",
    response_model=InferenceResponseV2,
    summary="Stateless GPS -> HOME/OFFICE evidence + other recurring places",
    responses={
        200: {"description": "Valid input. HOME/OFFICE may abstain."},
        422: {"description": "Sanitized invalid request."},
        500: {"description": "Generic unexpected error."},
    },
)
def v2_inference_endpoint(
    request: InferenceRequestV2, http_request: Request
) -> InferenceResponseV2:
    response = infer_v2(request)
    http_request.state.model_variant = response.model.model_version
    return response


@router.get("/v2/model-info", response_model=ModelInfoV2, tags=["system"])
def v2_model_info() -> ModelInfoV2:
    mode, percent = rollout_config()
    return ModelInfoV2(
        baseline_model=BASELINE,
        candidate_model=CANDIDATE,
        available_models=list(SUPPORTED),
        routing_mode=mode,
        canary_percent=percent,
        release_id=release_id(),
    )


@router.get("/health/ready", tags=["system"])
def v2_readiness() -> dict[str, str]:
    # This is process/model readiness only, not a check for external AWS services.
    rollout_config()
    return {"status": "ready", "model": BASELINE}
