"""Opt-in private synthetic destination recommendation API.

This route is deliberately synthetic-only. AuthN comes from an authenticated
account; account ownership is server-derived, never from query params.
No CP1 cache, GeoLife research user ID, coordinate or Evidence Score is read.
"""
from __future__ import annotations

import os
from dataclasses import replace
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from geolife.recommendation.destination import Visit, suggest_destinations
from geolife.recommendation.fixtures import commute_visits, fixture_visits

from .cognito_auth import synthetic_current_account
from .demo_auth import DemoAccount

router = APIRouter(tags=["synthetic-private-recommendation"])


class SuggestedPlace(BaseModel):
    rank: int = Field(ge=1, le=3)
    place_ref: str
    explanations: list[str]


class DestinationResponse(BaseModel):
    source: Literal["synthetic_fixture"] = "synthetic_fixture"
    model: Literal["context_ranker_s1_v0"] = "context_ranker_s1_v0"
    status: Literal["suggested", "abstained"]
    suggestions: list[SuggestedPlace]
    abstention_reason: str | None = None
    note: str = "Đề xuất từ dữ liệu synthetic; không phải nhãn HOME/OFFICE xác minh."


def _cognito_visits(owner_id: str) -> tuple[Visit, ...]:
    prefix = f"s{owner_id[4:36]}_"
    return tuple(
        replace(
            visit,
            owner_id=owner_id,
            place_id=visit.place_id.replace("s0_", prefix),
            origin_place_id=visit.origin_place_id.replace("s0_", prefix)
            if visit.origin_place_id else None,
        )
        for visit in commute_visits()
        if visit.owner_id == "demo_000"
    )


@router.get(
    "/v2/me/destination-suggestions",
    response_model=DestinationResponse,
    summary="Authenticated owner-scoped synthetic Top-3 destination suggestions",
)
def destination_suggestions(
    when: datetime = Query(description="Timezone-aware local date-time for the query"),
    origin_place_id: str | None = Query(default=None, min_length=1, max_length=64),
    account: DemoAccount = Depends(synthetic_current_account),
) -> DestinationResponse:
    if os.getenv("GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER", "") != "1":
        raise HTTPException(status_code=404, detail="Not found")
    if when.tzinfo is None or when.utcoffset() is None:
        raise HTTPException(status_code=422, detail="Timezone offset is required")
    owner_id = account.owner_id
    if account.is_cognito:
        visits = _cognito_visits(owner_id)
        if origin_place_id:
            origin_place_id = origin_place_id.replace("s0_", f"s{owner_id[4:36]}_")
    else:
        visits = fixture_visits()
    recs = suggest_destinations(
        visits, owner_id=owner_id, query_at=when,
        origin_place_id=origin_place_id, k=3,
    )
    if not recs:
        return DestinationResponse(
            status="abstained", suggestions=[],
            abstention_reason="insufficient_observed_repetition",
        )
    return DestinationResponse(
        status="suggested",
        suggestions=[
            SuggestedPlace(
                rank=s.rank, place_ref=s.place_id, explanations=list(s.reasons),
            )
            for s in recs
        ],
    )
