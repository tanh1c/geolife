"""Authenticated GeoLife demo: scoped cached-dataset and fresh-GPS inference.

The dataset mode deliberately reads the *existing private CP1 stays cache* for
low-latency demo; it does not rerun 18,670 .plt files on every HTTP request.
No 182-user data or cache is included in the Docker image/repository.

The returned map coordinates are rounded to ~100 m and should still be
considered sensitive. Never serve these endpoints without real demo auth + TLS.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from geolife.model import HomeOfficeConfig, build_semantic_locations, infer_home_office

from .demo_auth import (
    DemoAccount, LoginBody, LoginResult, current_account, login, logout
)
from .schemas import AbstentionReason, ClassifyRequest, GpsPoint
from .service import raw_request_to_stay_frame
from .v2 import BASELINE, EVIDENCE_METHOD


router = APIRouter(tags=["authenticated-demo"])
_CFG = HomeOfficeConfig()
_MAP_DECIMALS = 3


class DemoTrajectoryBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    points: list[GpsPoint] = Field(min_length=1, max_length=20_000)


class MapLocation(BaseModel):
    location_ref: str
    label: Literal["HOME", "OFFICE", "OTHER_RECURRING"]
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    evidence_score: float | None = Field(default=None, ge=0, le=1)
    visit_count: int = Field(ge=1)
    note: str


class DemoInferenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    dataset_user_id: str
    source: Literal["dataset_cp1_cache", "new_gps"]
    model_version: str = BASELINE
    coordinate_precision: Literal["rounded_3_decimals"] = "rounded_3_decimals"
    raw_points: int | None
    detected_stays: int
    recurring_locations: int
    predictions: dict[str, dict[str, object]]
    map_locations: list[MapLocation]
    warnings: list[str]


@lru_cache(maxsize=2)
def _load_stays_cache(path: str, stat_mtime_ns: int) -> pd.DataFrame:
    # Pickle is only safe for an explicitly trusted, admin-provided cache.
    # Never accept cache path or bytes from a request.
    frame = pd.read_pickle(path)
    required = {
        "user_id", "arrival_time_utc", "departure_time_utc",
        "duration_s", "latitude", "longitude",
    }
    if not required.issubset(frame.columns):
        raise ValueError("Unsupported frozen CP1 cache schema")
    frame = frame.copy()
    frame["user_id"] = frame["user_id"].astype(str).str.zfill(3)
    return frame[list(sorted(required))]


def _trusted_cache_path() -> Path:
    configured = os.getenv("GEOLIFE_STAYS_CACHE")
    if not configured:
        raise HTTPException(
            status_code=503, detail="Dataset mode unavailable: CP1 cache not mounted"
        )
    path = Path(configured).expanduser()
    if not path.is_absolute() or not path.is_file():
        raise HTTPException(
            status_code=503, detail="Dataset mode unavailable: invalid private cache path"
        )
    return path


def dataset_stays_for_account(account: DemoAccount) -> pd.DataFrame:
    path = _trusted_cache_path()
    try:
        frame = _load_stays_cache(str(path), path.stat().st_mtime_ns)
    except (OSError, ValueError, ImportError):
        raise HTTPException(status_code=503, detail="Dataset cache is unavailable") from None
    # Authorization mapping comes from server-issued session, never request args.
    return frame.loc[frame.user_id.eq(account.dataset_user_id)].copy()


def _round_coord(value: float) -> float:
    return round(float(value), _MAP_DECIMALS)


def _build_result(
    stays: pd.DataFrame,
    account: DemoAccount,
    *,
    source: Literal["dataset_cp1_cache", "new_gps"],
    raw_points: int | None,
) -> DemoInferenceResponse:
    warnings = [
        "HOME/OFFICE are heuristic labels, not GeoLife ground-truth annotations.",
        "OTHER_RECURRING is a recurring cluster, not a verified POI category.",
        "Map coordinates are rounded to 3 decimals (~100m); still location-sensitive.",
    ]
    base = dict(
        dataset_user_id=account.dataset_user_id,
        source=source, raw_points=raw_points,
        detected_stays=len(stays),
        recurring_locations=0,
        predictions={
            "HOME": {"status": "abstained", "reason": "insufficient_stay_history"},
            "OFFICE": {"status": "abstained", "reason": "insufficient_stay_history"},
        },
        map_locations=[], warnings=warnings,
    )
    if stays.empty:
        return DemoInferenceResponse(**base)

    semantic, location_summary = build_semantic_locations(stays, config=_CFG)
    if semantic.empty:
        for v in base["predictions"].values():
            v["reason"] = AbstentionReason.INSUFFICIENT_SEMANTIC_EVIDENCE.value
        return DemoInferenceResponse(**base)

    recurring = location_summary.loc[location_summary["stay_count"] >= 2].copy()
    base["recurring_locations"] = int(len(recurring))
    if recurring.empty:
        for v in base["predictions"].values():
            v["reason"] = AbstentionReason.INSUFFICIENT_RECURRING_HISTORY.value
        return DemoInferenceResponse(**base)

    selected = infer_home_office(stays, config=_CFG)
    emitted_ids: set[int] = set()
    loc_by_id = {
        int(row.location_id): row
        for row in location_summary.itertuples(index=False)
    }
    for row in selected.itertuples(index=False):
        lid = int(row.location_id)
        loc = loc_by_id.get(lid)
        if loc is None:
            raise RuntimeError("Emitted location not found in location summary")
        emitted_ids.add(lid)
        base["predictions"][row.label] = {
            "status": "emitted", "location_ref": f"L{lid}",
            "evidence_score": float(row.evidence_strength),
            "evidence_method": EVIDENCE_METHOD,
        }
        base["map_locations"].append(
            MapLocation(
                location_ref=f"L{lid}", label=row.label,
                latitude=_round_coord(loc.latitude),
                longitude=_round_coord(loc.longitude),
                evidence_score=float(row.evidence_strength),
                visit_count=int(loc.stay_count),
                note="Heuristic time-window inference",
            )
        )

    other = recurring.loc[
        ~recurring["location_id"].astype(int).isin(emitted_ids)
    ].sort_values(
        ["stay_count", "total_dwell_h", "location_id"],
        ascending=[False, False, True],
        kind="stable",
    )
    for row in other.itertuples(index=False):
        base["map_locations"].append(
            MapLocation(
                location_ref=f"L{int(row.location_id)}",
                label="OTHER_RECURRING",
                latitude=_round_coord(row.latitude),
                longitude=_round_coord(row.longitude),
                evidence_score=None,
                visit_count=int(row.stay_count),
                note="Frequent stop; POI semantic category unverified",
            )
        )
    return DemoInferenceResponse(**base)


@router.post(
    "/v2/auth/login", response_model=LoginResult,
    summary="Log in with an explicitly provisioned demo account",
)
def demo_login(body: LoginBody) -> LoginResult:
    return login(body)


@router.post("/v2/auth/logout", summary="Revoke current bearer session")
def demo_logout(account_logout: dict[str, bool] = Depends(logout)) -> dict[str, bool]:
    return account_logout


@router.get("/v2/auth/me", response_model=DemoAccount)
def demo_me(account: DemoAccount = Depends(current_account)) -> DemoAccount:
    return account


@router.post("/v2/me/dataset-inferences", response_model=DemoInferenceResponse)
def demo_dataset(
    account: DemoAccount = Depends(current_account),
) -> DemoInferenceResponse:
    stays = dataset_stays_for_account(account)
    return _build_result(stays, account, source="dataset_cp1_cache", raw_points=None)


@router.post("/v2/me/inferences", response_model=DemoInferenceResponse)
def demo_new_trajectory(
    body: DemoTrajectoryBody, account: DemoAccount = Depends(current_account),
) -> DemoInferenceResponse:
    stays = raw_request_to_stay_frame(
        account.dataset_user_id, ClassifyRequest(points=body.points)
    )
    return _build_result(stays, account, source="new_gps", raw_points=len(body.points))
