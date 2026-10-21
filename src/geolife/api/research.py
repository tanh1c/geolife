from __future__ import annotations

import hashlib
import io
import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Literal

import boto3
import pandas as pd

from geolife.recommendation.destination import Visit, suggest_destinations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from geolife.model import HomeOfficeConfig, build_semantic_locations, infer_home_office

from .cognito_auth import cognito_current_account
from .demo import _load_stays_cache, _trusted_cache_path
from .demo_auth import DemoAccount
from .v2 import BASELINE

router = APIRouter(prefix="/v2/research", tags=["research-demo"])
_ALIAS = re.compile(r"[a-z][a-z0-9-]{2,63}\Z")
_DATASET_ID = re.compile(r"\d{3}\Z")
CACHE_BYTES = 536002
CACHE_SHA256 = "94d6904ae834468a7615d1165678b00ae374c54d500d2167c1fe4af58b828e58"
CACHE_KEY = "approved/cp1/stays_baseline_v1.pkl"
MANIFEST_KEY = "approved/cp1/stays_baseline_v1.sha256.json"


def _trusted_research_stays() -> pd.DataFrame:
    bucket = os.getenv("GEOLIFE_RESEARCH_S3_BUCKET", "")
    if not bucket:
        cache = _trusted_cache_path()
        return _load_stays_cache(str(cache), cache.stat().st_mtime_ns)
    try:
        version = os.environ["GEOLIFE_RESEARCH_S3_VERSION"]
        manifest_version = os.environ["GEOLIFE_RESEARCH_S3_MANIFEST_VERSION"]
        if not version or not manifest_version or not re.fullmatch(r"geolife-private-research-\d{12}-ap-southeast-1", bucket):
            raise ValueError()
        s3 = boto3.client("s3", region_name="ap-southeast-1")
        manifest_obj = s3.get_object(Bucket=bucket, Key=MANIFEST_KEY, VersionId=manifest_version)
        try:
            assert manifest_obj["ServerSideEncryption"] == "AES256"
            manifest = json.loads(manifest_obj["Body"].read())
        finally:
            manifest_obj["Body"].close()
        if (manifest["bytes"], manifest["sha256"], manifest["s3_version_id"], manifest["model_version"]) != (CACHE_BYTES, CACHE_SHA256, version, BASELINE):
            raise ValueError()
        obj = s3.get_object(Bucket=bucket, Key=CACHE_KEY, VersionId=version)
        try:
            if obj["ServerSideEncryption"] != "AES256" or obj["ContentLength"] != CACHE_BYTES:
                raise ValueError()
            payload = obj["Body"].read(CACHE_BYTES + 1)
        finally:
            obj["Body"].close()
        if len(payload) != CACHE_BYTES or hashlib.sha256(payload).hexdigest() != CACHE_SHA256:
            raise ValueError()
        # Trusted Modal pickle only: fixed S3 key/version and pinned SHA-256 precede deserialization.
        frame = pd.read_pickle(io.BytesIO(payload))
        required = {"user_id", "arrival_time_utc", "departure_time_utc", "duration_s", "latitude", "longitude"}
        if not required.issubset(frame.columns):
            raise ValueError()
        frame = frame.copy()
        frame["user_id"] = frame["user_id"].astype(str).str.zfill(3)
        return frame[list(sorted(required))]
    except Exception:
        raise HTTPException(status_code=503, detail="Research preview unavailable") from None



class CaseSelection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    alias: str = Field(min_length=3, max_length=64)
    when: datetime | None = None


class DestinationSuggestion(BaseModel):
    rank: int
    place_ref: str
    label: Literal["HOME", "OFFICE", "Điểm quen thuộc"]
    explanations: list[str]


class LabelResult(BaseModel):
    status: Literal["emitted", "abstained"]
    evidence: str


class StayPoint(BaseModel):
    index: int
    latitude: float
    longitude: float
    label: Literal["HOME", "OFFICE", "STOP"]


class CaseResult(BaseModel):
    case_alias: str
    stops: list[StayPoint]
    user_id: str
    stay_count: int
    recurring_location_count: int
    model_version: str = BASELINE
    predictions: dict[str, LabelResult]
    suggestions: list[DestinationSuggestion] = Field(default_factory=list)
    note: str = "Historical heuristic inference, not GeoLife ground truth."


def _research_access(
    _account: DemoAccount = Depends(cognito_current_account),
) -> dict[str, str]:
    if os.getenv("GEOLIFE_AUTH_MODE") != "cognito":
        raise HTTPException(status_code=404, detail="Not found")
    configured = os.getenv("GEOLIFE_RESEARCH_CASES")
    if not configured:
        raise HTTPException(status_code=503, detail="Research preview unavailable")
    try:
        path = Path(configured)
        if not path.is_absolute() or not path.is_file():
            raise ValueError()
        mapping = json.loads(path.read_text(encoding="utf-8"))
        cases = mapping["cases"]
        if not isinstance(cases, dict) or not 1 <= len(cases) <= 6 or len(set(cases.values())) != len(cases):
            raise ValueError()
        if any(not isinstance(alias, str) or not _ALIAS.fullmatch(alias) or not isinstance(uid, str)
               or not _DATASET_ID.fullmatch(uid) or int(uid) > 181 for alias, uid in cases.items()):
            raise ValueError()
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise HTTPException(status_code=503, detail="Research preview unavailable") from None
    return cases


@router.get("/cases")
def list_cases(cases: dict[str, str] = Depends(_research_access)) -> dict[str, list[dict[str, str]]]:
    return {"cases": [{"alias": alias, "user_id": uid} for alias, uid in cases.items()]}


@router.post("/cases", response_model=CaseResult)
def infer_case(body: CaseSelection, cases: dict[str, str] = Depends(_research_access)) -> CaseResult:
    if body.alias not in cases:
        raise HTTPException(status_code=404, detail="Case not found")
    if body.when is not None and (body.when.tzinfo is None or body.when.utcoffset() is None):
        raise HTTPException(status_code=422, detail="Timezone offset is required")
    try:
        stays = _trusted_research_stays()
        own = stays.loc[stays.user_id.eq(cases[body.alias])].copy()
        semantic, locations = build_semantic_locations(own, config=HomeOfficeConfig())
        selected = infer_home_office(own, config=HomeOfficeConfig()) if not semantic.empty else semantic
    except Exception:
        raise HTTPException(status_code=503, detail="Research preview unavailable") from None
    labels = set(selected["label"]) if "label" in selected else set()
    by_location = dict(zip(selected["location_id"], selected["label"])) if labels else {}
    stops = [StayPoint(
        index=index, latitude=float(latitude), longitude=float(longitude),
        label=by_location.get(int(location_id), "STOP"),
    ) for index, (latitude, longitude, location_id) in enumerate(
        semantic[["latitude", "longitude", "location_id"]].itertuples(index=False, name=None)
    )] if body.when is None else []
    suggestions = []
    if body.when is not None and not semantic.empty:
        visits = [Visit(
            owner_id=cases[body.alias], place_id=f"loc_{int(location_id)}",
            observed_at=arrival.to_pydatetime(),
        ) for arrival, location_id in semantic[["arrival_time_utc", "location_id"]].itertuples(index=False, name=None)]
        suggestions = [DestinationSuggestion(
            rank=rec.rank, place_ref=rec.place_id,
            label=by_location.get(int(rec.place_id[4:]), "Điểm quen thuộc"),
            explanations=list(rec.reasons),
        ) for rec in suggest_destinations(visits, owner_id=cases[body.alias], query_at=body.when, k=3)]
    return CaseResult(
        case_alias=body.alias,
        stops=stops,
        suggestions=suggestions,
        user_id=cases[body.alias],
        stay_count=len(own),
        recurring_location_count=int(locations.stay_count.ge(2).sum()) if not locations.empty else 0,
        predictions={label: LabelResult(
            status="emitted" if label in labels else "abstained",
            evidence="Repeated visits in the model's local-time window" if label in labels
            else "Insufficient evidence under the frozen model thresholds",
        ) for label in ("HOME", "OFFICE")},
    )
