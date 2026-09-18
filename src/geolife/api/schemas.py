from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AbstentionReason(str, Enum):
    OUT_OF_SCOPE_GEOGRAPHY = "out_of_scope_geography"
    INSUFFICIENT_RECURRING_HISTORY = "insufficient_recurring_history"
    INSUFFICIENT_SEMANTIC_EVIDENCE = "insufficient_semantic_evidence"


class StayEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    arrival_time_utc: datetime
    departure_time_utc: datetime
    latitude: float = Field(ge=-90.0, le=90.0)
    longitude: float = Field(ge=-180.0, le=180.0)

    @field_validator("arrival_time_utc", "departure_time_utc")
    @classmethod
    def require_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("timestamp must include a timezone offset")
        return value.astimezone(timezone.utc)

    @model_validator(mode="after")
    def require_positive_interval(self) -> "StayEvent":
        if self.departure_time_utc <= self.arrival_time_utc:
            raise ValueError("departure_time_utc must be after arrival_time_utc")
        return self


class InferRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str = Field(min_length=1, max_length=256)
    stays: list[StayEvent] = Field(min_length=1)

    @field_validator("user_id")
    @classmethod
    def normalize_user_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("user_id must not be blank")
        return normalized


class EmittedResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Literal["HOME", "OFFICE"]
    status: Literal["emitted"] = "emitted"
    location_id: int = Field(ge=0)
    evidence_strength: float = Field(ge=0.0, le=1.0)
    relevant_dwell_share: float = Field(ge=0.0, le=1.0)
    share_margin: float = Field(ge=0.0, le=1.0)
    relevant_dates: int = Field(ge=0)
    relevant_dwell_h: float = Field(ge=0.0)


class AbstainedResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: Literal["HOME", "OFFICE"]
    status: Literal["abstained"] = "abstained"
    reason: AbstentionReason


SemanticResult = Annotated[
    EmittedResult | AbstainedResult,
    Field(discriminator="status"),
]


class InferResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    model_contract: Literal["cp2-v1"] = "cp2-v1"
    results: list[SemanticResult] = Field(min_length=2, max_length=2)


class HealthResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["ok"] = "ok"
    service: Literal["geolife-home-office-api"] = "geolife-home-office-api"
    api_version: Literal["v1"] = "v1"
    model_contract: Literal["cp2-v1"] = "cp2-v1"
