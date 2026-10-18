"""Opt-in private synthetic destination recommendation API.

This route is deliberately synthetic-only. AuthN comes from existing private
demo sessions; account ownership is server-derived, never from query params.
No CP1 cache, GeoLife research user ID, coordinate or Evidence Score is read.
"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from geolife.recommendation.destination import suggest_destinations
from geolife.recommendation.fixtures import fixture_visits

from .demo_auth import DemoAccount, current_account


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


@router.get(
    "/v2/me/destination-suggestions",
    response_model=DestinationResponse,
    summary="Authenticated owner-scoped synthetic Top-3 destination suggestions",
)
def destination_suggestions(
    when: datetime = Query(description="Timezone-aware local date-time for the query"),
    origin_place_id: str | None = Query(default=None, min_length=1, max_length=64),
    account: DemoAccount = Depends(current_account),
) -> DestinationResponse:
    if os.getenv("GEOLIFE_ENABLE_SYNTHETIC_RECOMMENDER", "") != "1":
        raise HTTPException(status_code=404, detail="Not found")
    if when.tzinfo is None or when.utcoffset() is None:
        raise HTTPException(status_code=422, detail="Timezone offset is required")
    recs = suggest_destinations(
        fixture_visits(), owner_id=account.account_id, query_at=when,
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
