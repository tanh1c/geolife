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


@app.get("/health", response_model=HealthResponse, tags=["system"])
def health() -> HealthResponse:
    return HealthResponse()


@app.post(
    "/v1/classify/{user_id}",
    response_model=ClassifyResponse,
    tags=["inference"],
    summary="Classify a raw GPS sequence into HOME / OFFICE / POI locations",
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
