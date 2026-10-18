"""Isolated authenticated synthetic beta API; no GeoLife research cache access."""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from geolife.recommendation.destination import suggest_destinations
from geolife.recommendation.fixtures import fixture_visits
from .cognito_beta import current_beta_principal
from .recommendation import DestinationResponse, SuggestedPlace

router = APIRouter(prefix="/v3/beta", tags=["cognito-invite-only-beta"])


class BetaMe(BaseModel):
    app_user_id: str
    source: str = "cognito_test_principal"
    historical_geolife_access: bool = False


@router.get("/me", response_model=BetaMe)
def whoami(principal: tuple[str, str] = Depends(current_beta_principal)) -> BetaMe:
    return BetaMe(app_user_id=principal[0])


@router.get("/destination-suggestions", response_model=DestinationResponse)
def beta_suggestions(
    when: datetime = Query(description="Timezone-aware local query time"),
    origin_place_id: str | None = Query(default=None, min_length=1, max_length=64),
    principal: tuple[str, str] = Depends(current_beta_principal),
) -> DestinationResponse:
    if when.tzinfo is None or when.utcoffset() is None:
        raise HTTPException(422, "Timezone offset required")
    ranked = suggest_destinations(fixture_visits(), owner_id=principal[1],
                                  query_at=when, origin_place_id=origin_place_id, k=3)
    return DestinationResponse(
        status="suggested" if ranked else "abstained",
        suggestions=[SuggestedPlace(rank=r.rank, place_ref=r.place_id,
                                    explanations=list(r.reasons)) for r in ranked],
        abstention_reason=None if ranked else "insufficient_observed_repetition",
    )
