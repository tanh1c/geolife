from __future__ import annotations

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from .schemas import HealthResponse, InferRequest, InferResponse
from .service import infer_request


app = FastAPI(
    title="GeoLife Home / Office API",
    version="1.0.0",
    description=(
        "HTTP serving layer for the frozen CP2 v1 Home / Office heuristic baseline. "
        "Evidence strength is not a calibrated probability."
    ),
)


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_, exc: RequestValidationError) -> JSONResponse:
    # FastAPI/Pydantic errors may include the rejected input value. Location
    # history is sensitive, so the API returns path/type/message without
    # echoing request-body values.
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
    "/v1/home-office/infer",
    response_model=InferResponse,
    tags=["inference"],
    summary="Infer Home / Office evidence from one user's CP1 stay events",
)
def infer_home_office_endpoint(request: InferRequest) -> InferResponse:
    return infer_request(request)
