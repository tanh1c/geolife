from __future__ import annotations

import pandas as pd

from geolife.model import build_semantic_locations, infer_home_office
from geolife.staypoints import clean_trajectory, detect_staypoints

from .schemas import (
    AbstainedResult,
    AbstentionReason,
    ClassificationAbstention,
    ClassifiedLocation,
    ClassifyRequest,
    ClassifyResponse,
    EmittedResult,
    InferRequest,
    InferResponse,
    SemanticResult,
)


LABELS = ("HOME", "OFFICE")


def request_to_stay_frame(request: InferRequest) -> pd.DataFrame:
    """Convert one validated stay-event request into the frozen CP2 stay schema."""
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


def raw_request_to_stay_frame(user_id: str, request: ClassifyRequest) -> pd.DataFrame:
    """Run frozen CP1 cleaning + stay detection for a raw GPS sequence."""
    raw = pd.DataFrame.from_records(
        [
            {
                "timestamp": point.timestamp_utc,
                "latitude": point.latitude,
                "longitude": point.longitude,
            }
            for point in request.points
        ]
    )

    cleaned = clean_trajectory(raw)
    stays = detect_staypoints(cleaned)

    if stays.empty:
        return pd.DataFrame(
            columns=[
                "user_id",
                "arrival_time_utc",
                "departure_time_utc",
                "duration_s",
                "latitude",
                "longitude",
            ]
        )

    out = stays.rename(
        columns={
            "arrival_time": "arrival_time_utc",
            "departure_time": "departure_time_utc",
        }
    ).copy()
    out["user_id"] = user_id

    return out[
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
    """Run the frozen CP2 model from already-detected stay events."""
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


def _classification_abstentions(
    reason: AbstentionReason,
) -> list[ClassificationAbstention]:
    return [
        ClassificationAbstention(label=label, reason=reason)
        for label in LABELS
    ]


def classify_raw_request(user_id: str, request: ClassifyRequest) -> ClassifyResponse:
    """Mentor-facing v1: raw GPS -> cleaning -> stays -> HOME/OFFICE/POI."""
    normalized_user_id = user_id.strip()
    stays = raw_request_to_stay_frame(normalized_user_id, request)

    if stays.empty:
        return ClassifyResponse(
            user_id=normalized_user_id,
            locations=[],
            abstentions=_classification_abstentions(
                AbstentionReason.INSUFFICIENT_STAY_HISTORY
            ),
        )

    semantic_stays, location_summary = build_semantic_locations(stays)
    if semantic_stays.empty:
        return ClassifyResponse(
            user_id=normalized_user_id,
            locations=[],
            abstentions=_classification_abstentions(
                AbstentionReason.OUT_OF_SCOPE_GEOGRAPHY
            ),
        )

    recurring = location_summary.loc[location_summary["stay_count"] >= 2].copy()
    if recurring.empty:
        return ClassifyResponse(
            user_id=normalized_user_id,
            locations=[],
            abstentions=_classification_abstentions(
                AbstentionReason.INSUFFICIENT_RECURRING_HISTORY
            ),
        )

    emitted = infer_home_office(stays)
    emitted_by_label = {
        row.label: row
        for row in emitted.itertuples(index=False)
    }

    locations: list[ClassifiedLocation] = []
    abstentions: list[ClassificationAbstention] = []
    semantic_location_ids: set[int] = set()

    for label in LABELS:
        row = emitted_by_label.get(label)
        if row is None:
            abstentions.append(
                ClassificationAbstention(
                    label=label,
                    reason=AbstentionReason.INSUFFICIENT_SEMANTIC_EVIDENCE,
                )
            )
            continue

        location_id = int(row.location_id)
        semantic_location_ids.add(location_id)
        locations.append(
            ClassifiedLocation(
                label=label,
                location_id=location_id,
                confidence=float(row.evidence_strength),
                confidence_method="home_office_evidence",
            )
        )

    total_semantic_stays = max(int(len(semantic_stays)), 1)
    poi_candidates = recurring.loc[
        ~recurring["location_id"].astype(int).isin(semantic_location_ids)
    ].sort_values(
        ["stay_count", "total_dwell_h", "location_id"],
        ascending=[False, False, True],
        kind="stable",
    )

    for row in poi_candidates.itertuples(index=False):
        locations.append(
            ClassifiedLocation(
                label="POI",
                location_id=int(row.location_id),
                confidence=min(float(row.stay_count) / total_semantic_stays, 1.0),
                confidence_method="poi_visit_share",
            )
        )

    return ClassifyResponse(
        user_id=normalized_user_id,
        locations=locations,
        abstentions=abstentions,
    )
