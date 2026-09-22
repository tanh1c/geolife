from __future__ import annotations

from fastapi import FastAPI, Path
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .schemas import (
    ClassifyRequest,
    ClassifyResponse,
    HealthResponse,
    InferRequest,
    InferResponse,
    ServerError,
    ValidationErrorResponse,
)
from .service import classify_raw_request, infer_request


app = FastAPI(
    title="GeoLife Home / Office API",
    version="1.0.0",
    description=(
        "GeoLife location inference API. The mentor-facing v1 contract accepts raw GPS "
        "sequences at /v1/classify/{user_id}. Confidence values are heuristic evidence "
        "scores, not calibrated probabilities."
    ),
)

THREE_NIGHT_BEIJING_HOME_EXAMPLE = {
    "points": [
        {
            "timestamp_utc": f"2026-01-{day}T13:{minute:02d}:00Z",
            "latitude": 39.9042,
            "longitude": 116.4074,
        }
        for day in ("05", "06", "07")
        for minute in (0, 5, 10, 15, 20)
    ]
}


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
    # FastAPI/Pydantic errors may include rejected input values. Location
    # history is sensitive, so do not echo raw GPS values in validation errors.
    sanitized = []
    for error in exc.errors():
        sanitized.append(
            {
                key: value
                for key, value in error.items()
                if key not in {"input", "ctx"}
            }
        )
    return JSONResponse(status_code=422, content={"detail": sanitized})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request, _exc) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse()


@app.post(
    "/v1/classify/{user_id}",
    response_model=ClassifyResponse,
    tags=["inference"],
    summary="Classify a raw GPS sequence into HOME / OFFICE / POI locations",
    openapi_extra={
        "requestBody": {
            "content": {
                "application/json": {
                    "examples": {
                        "three_night_beijing_home": {
                            "summary": "Three 20-minute Beijing night stays that emit HOME",
                            "value": THREE_NIGHT_BEIJING_HOME_EXAMPLE,
                        }
                    }
                }
            }
        }
    },
    responses={
        200: {
            "description": "Valid request; the result may emit locations and/or abstain.",
            "content": {
                "application/json": {
                    "examples": {
                        "emitted_location": {
                            "summary": "HOME emitted and OFFICE abstained",
                            "value": {
                                "user_id": "demo-user",
                                "api_version": "v1",
                                "model_contract": "cp2-v1",
                                "locations": [
                                    {
                                        "label": "HOME",
                                        "location_id": 0,
                                        "confidence": 0.83,
                                        "confidence_method": "home_office_evidence",
                                    }
                                ],
                                "abstentions": [
                                    {
                                        "label": "OFFICE",
                                        "reason": "insufficient_semantic_evidence",
                                    }
                                ],
                            },
                        },
                        "valid_request_abstained": {
                            "summary": "Valid but insufficient history",
                            "value": {
                                "user_id": "demo-user",
                                "api_version": "v1",
                                "model_contract": "cp2-v1",
                                "locations": [],
                                "abstentions": [
                                    {"label": "HOME", "reason": "insufficient_stay_history"},
                                    {"label": "OFFICE", "reason": "insufficient_stay_history"},
                                ],
                            },
                        },
                    }
                }
            },
        },
        422: {
            "model": ValidationErrorResponse,
            "description": "Validation error; rejected GPS values are not echoed.",
            "content": {
                "application/json": {
                    "examples": {
                        "invalid_coordinate": {
                            "summary": "Latitude 91 is outside [-90, 90]",
                            "value": {
                                "detail": [
                                    {
                                        "type": "less_than_equal",
                                        "loc": ["body", "points", 0, "latitude"],
                                        "msg": "Input should be less than or equal to 90",
                                    }
                                ]
                            },
                        }
                    }
                }
            },
        },
        500: {
            "model": ServerError,
            "description": "Unexpected server failure.",
            "content": {
                "application/json": {
                    "example": {"detail": "Internal server error"}
                }
            },
        },
    },
)
def classify_endpoint(
    request: ClassifyRequest,
    user_id: str = Path(min_length=1, max_length=256),
) -> ClassifyResponse:
    return classify_raw_request(user_id, request)


@app.post(
    "/v1/home-office/infer",
    response_model=InferResponse,
    tags=["internal"],
    summary="Infer Home / Office evidence from already-detected stay events",
    deprecated=True,
)
def infer_home_office_endpoint(request: InferRequest) -> InferResponse:
    """Compatibility endpoint retained for model/API parity tests."""
    return infer_request(request)
