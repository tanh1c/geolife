from __future__ import annotations

import pandas as pd

from geolife.model import build_semantic_locations, infer_home_office

from .schemas import (
    AbstainedResult,
    AbstentionReason,
    EmittedResult,
    InferRequest,
    InferResponse,
    SemanticResult,
)


LABELS = ("HOME", "OFFICE")


def request_to_stay_frame(request: InferRequest) -> pd.DataFrame:
    """Convert one validated API request into the frozen CP2 stay-table schema."""
    records = [stay.model_dump() for stay in request.stays]
    frame = pd.DataFrame.from_records(records)

    frame["arrival_time_utc"] = pd.to_datetime(frame["arrival_time_utc"], utc=True)
    frame["departure_time_utc"] = pd.to_datetime(frame["departure_time_utc"], utc=True)
    frame["duration_s"] = (
        frame["departure_time_utc"] - frame["arrival_time_utc"]
    ).dt.total_seconds()
    frame["user_id"] = request.user_id

    return frame[
        [
            "user_id",
            "arrival_time_utc",
            "departure_time_utc",
            "duration_s",
            "latitude",
            "longitude",
        ]
    ]


def _emitted_result(row) -> EmittedResult:
    return EmittedResult(
        label=row.label,
        location_id=int(row.location_id),
        evidence_strength=float(row.evidence_strength),
        relevant_dwell_share=float(row.relevant_dwell_share),
        share_margin=float(row.share_margin),
        relevant_dates=int(row.relevant_dates),
        relevant_dwell_h=float(row.relevant_dwell_h),
    )


def _abstained(label: str, reason: AbstentionReason) -> AbstainedResult:
    return AbstainedResult(label=label, reason=reason)


def infer_request(request: InferRequest) -> InferResponse:
    """Run the frozen CP2 model and make abstention explicit for each label."""
    stays = request_to_stay_frame(request)

    semantic_stays, locations = build_semantic_locations(stays)

    if semantic_stays.empty:
        reason = AbstentionReason.OUT_OF_SCOPE_GEOGRAPHY
        results: list[SemanticResult] = [_abstained(label, reason) for label in LABELS]
        return InferResponse(user_id=request.user_id, results=results)

    recurring_locations = locations.loc[locations["stay_count"] >= 2]
    if recurring_locations.empty:
        reason = AbstentionReason.INSUFFICIENT_RECURRING_HISTORY
        results = [_abstained(label, reason) for label in LABELS]
        return InferResponse(user_id=request.user_id, results=results)

    emitted = infer_home_office(stays)
    emitted_by_label = {
        row.label: row
        for row in emitted.itertuples(index=False)
    }

    results = []
    for label in LABELS:
        row = emitted_by_label.get(label)
        if row is None:
            results.append(
                _abstained(
                    label,
                    AbstentionReason.INSUFFICIENT_SEMANTIC_EVIDENCE,
                )
            )
        else:
            results.append(_emitted_result(row))

    return InferResponse(user_id=request.user_id, results=results)
