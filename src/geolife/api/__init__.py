"""FastAPI serving layer for the GeoLife Track B1 API contracts."""

from .app import app
from .schemas import (
    AbstainedResult,
    AbstentionReason,
    ClassificationAbstention,
    ClassifiedLocation,
    ClassifyRequest,
    ClassifyResponse,
    EmittedResult,
    GpsPoint,
    HealthResponse,
    InferRequest,
    InferResponse,
    StayEvent,
)

__all__ = [
    "app",
    "AbstainedResult",
    "AbstentionReason",
    "ClassificationAbstention",
    "ClassifiedLocation",
    "ClassifyRequest",
    "ClassifyResponse",
    "EmittedResult",
    "GpsPoint",
    "HealthResponse",
    "InferRequest",
    "InferResponse",
    "StayEvent",
]
