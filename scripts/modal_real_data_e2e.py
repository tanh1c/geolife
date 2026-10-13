"""Privacy-safe *real CP1 cache* -> CP2 -> authenticated HTTP demo E2E audit.

Run on an existing Modal Jupyter server WITH the private GeoLife Volume mounted.
This never reads raw .plt, never writes to the mounted Volume, and does not
print selected GeoLife user IDs, map coordinates, passwords, or tokens.

Requires trusted baseline cache and installed project:
    python scripts/modal_real_data_e2e.py

All credentials/sessions are ephemeral in /tmp; do not reuse real credentials.
The script is intentionally not a public endpoint or an automated deployment.
"""
from __future__ import annotations

import argparse
import json
import os
import secrets
import tempfile
from collections import Counter
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

from geolife.api.app import app
from geolife.api.demo import _load_stays_cache
from geolife.api.demo_auth import provision_account
from geolife.model import HomeOfficeConfig, build_semantic_locations, infer_home_office


DEFAULT_CACHE = (
    Path("/mnt/geolife-data/cache/03a_user_behavior_deep_dive")
    / "stays_baseline_v1.pkl"
)
ALL_USER_IDS = {f"{i:03d}" for i in range(182)}
FROZEN = {
    "stays": 5821,
    "stay_users": 136,
    "semantic_locations": 2015,
    "recurring_locations": 716,
    "recurring_users": 104,
    "home": 27,
    "office": 16,
}


class AuditGateFailure(Exception):
    """Only a non-sensitive static gate name may be shown in logs."""


def check(condition: bool, gate: str) -> None:
    if not condition:
        raise AuditGateFailure(gate)


def normalize_users(frame: pd.DataFrame) -> pd.DataFrame:
    required = {
        "user_id", "arrival_time_utc", "departure_time_utc",
        "duration_s", "latitude", "longitude",
    }
    check(required.issubset(frame.columns), "CP1_CACHE_SCHEMA")
    frame = frame.copy()
    frame["user_id"] = frame["user_id"].astype(str).str.zfill(3)
    check(set(frame.user_id).issubset(ALL_USER_IDS), "DATASET_USER_ID_DOMAIN")
    check(frame.user_id.notna().all(), "MISSING_DATASET_USER_ID")
    return frame


def select_cases(
    stays: pd.DataFrame,
    recurring_locations: pd.DataFrame,
    selected: pd.DataFrame,
) -> dict[str, str]:
    """Choose private test subjects dynamically; never log their identities."""
    stay_users = set(stays.user_id)
    home_users = set(selected.loc[selected.label.eq("HOME"), "user_id"])
    office_users = set(selected.loc[selected.label.eq("OFFICE"), "user_id"])
    recurring_users = set(recurring_locations.user_id)
    abstaining = recurring_users.difference(home_users | office_users)
    no_stay = ALL_USER_IDS.difference(stay_users)
    for key, group in (
        ("HOME_CASE", home_users),
        ("OFFICE_CASE", office_users),
        ("RECURRING_ABSTAIN_CASE", abstaining),
        ("NO_STAY_CASE", no_stay),
    ):
        check(bool(group), key)
    return {
        "HOME": sorted(home_users)[0],
        "OFFICE": sorted(office_users)[0],
        "RECURRING_ABSTAIN": sorted(abstaining)[0],
        "NO_STAY": sorted(no_stay)[0],
    }


def canonical_reference(stays: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, str]]:
    cfg = HomeOfficeConfig()
    semantic, locations = build_semantic_locations(stays, config=cfg)
    selected = infer_home_office(stays, config=cfg)
    recurring = locations.loc[locations.stay_count.ge(2)].copy()
    label_counts = Counter(selected.label)
    check(len(stays) == FROZEN["stays"], "FROZEN_STAYS")
    check(stays.user_id.nunique() == FROZEN["stay_users"], "FROZEN_STAY_USERS")
    check(len(semantic) == FROZEN["stays"], "FROZEN_SEMANTIC_STAYS")
    check(len(locations) == FROZEN["semantic_locations"], "FROZEN_SEMANTIC_LOCATIONS")
    check(len(recurring) == FROZEN["recurring_locations"], "FROZEN_RECURRING_LOCATIONS")
    check(recurring.user_id.nunique() == FROZEN["recurring_users"], "FROZEN_RECURRING_USERS")
    check(label_counts.get("HOME", 0) == FROZEN["home"], "FROZEN_HOME")
    check(label_counts.get("OFFICE", 0) == FROZEN["office"], "FROZEN_OFFICE")
    check(not selected.duplicated(["user_id", "label"]).any(), "UNIQUE_SELECTED_LABELS")
    return locations, selected, select_cases(stays, recurring, selected)


def validate_inference(
    response: dict,
    uid: str,
    stays: pd.DataFrame,
    locations: pd.DataFrame,
    selected: pd.DataFrame,
) -> None:
    """Exact *rounded-to-3-decimals* map/model parity for this private user."""
    user_stays = stays.loc[stays.user_id.eq(uid)]
    user_locations = locations.loc[locations.user_id.eq(uid)]
    user_recurring = user_locations.loc[user_locations.stay_count.ge(2)]
    user_selected = selected.loc[selected.user_id.eq(uid)]

    check(response["dataset_user_id"] == uid, "ACCOUNT_SCOPE_USER_ID")
    check(response["source"] == "dataset_cp1_cache", "ACCOUNT_SCOPE_SOURCE")
    check(response["detected_stays"] == len(user_stays), "PER_USER_STAYS")
    check(response["recurring_locations"] == len(user_recurring), "PER_USER_RECURRING")
    check(response["raw_points"] is None, "DATASET_NOT_REPARSED_AS_RAW")
    check(response["model_version"] == "cp2-v2-complete-link-200m", "FROZEN_MODEL_VERSION")
    check(response["coordinate_precision"] == "rounded_3_decimals", "MAP_PRECISION_POLICY")

    pred = response["predictions"]
    markers = response["map_locations"]
    check(set(pred) == {"HOME", "OFFICE"}, "LABEL_SCHEMA")
    check(all(set(m).issuperset({"label", "latitude", "longitude", "location_ref"}) for m in markers),
          "MAP_MARKER_SCHEMA")
    check(len(markers) == len({(m["label"], m["location_ref"]) for m in markers}),
          "DUPLICATE_MARKERS")
    for label in ("HOME", "OFFICE"):
        rows = user_selected.loc[user_selected.label.eq(label)]
        check(len(rows) <= 1, "UNEXPECTED_DUPLICATE_LABEL")
        matches = [m for m in markers if m["label"] == label]
        if rows.empty:
            check(pred[label]["status"] == "abstained", "UNEXPECTED_EMISSION")
            check(not matches, "UNEXPECTED_LABEL_MARKER")
            continue
        row = rows.iloc[0]
        check(pred[label]["status"] == "emitted", "MISSING_EMISSION")
        check(len(matches) == 1, "MISSING_LABEL_MARKER")
        ref = f"L{int(row.location_id)}"
        check(pred[label]["location_ref"] == ref, "LABEL_LOCATION_REF")
        check(matches[0]["location_ref"] == ref, "MAP_LOCATION_REF")
        check(abs(float(pred[label]["evidence_score"]) -
                  float(row.evidence_strength)) < 1e-9, "EVIDENCE_PARITY")

    selected_ids = {int(i) for i in user_selected.location_id}
    expected_keys = (
        {(str(row.label), f"L{int(row.location_id)}") for row in user_selected.itertuples(index=False)}
        | {("OTHER_RECURRING", f"L{int(row.location_id)}")
           for row in user_recurring.itertuples(index=False)
           if int(row.location_id) not in selected_ids}
    )
    actual_keys = {(m["label"], m["location_ref"]) for m in markers}
    check(actual_keys == expected_keys, "MAP_LABEL_MEMBERSHIP")
    summary_by_id = {
        int(row.location_id): row for row in user_locations.itertuples(index=False)
    }
    for marker in markers:
        loc = summary_by_id[int(marker["location_ref"][1:])]
        check(marker["latitude"] == round(float(loc.latitude), 3), "MAP_LATITUDE_PARITY")
        check(marker["longitude"] == round(float(loc.longitude), 3), "MAP_LONGITUDE_PARITY")
        check(marker["visit_count"] == int(loc.stay_count), "MAP_VISIT_COUNT")
        check(-90 <= marker["latitude"] <= 90 and -180 <= marker["longitude"] <= 180,
              "MAP_COORDINATE_RANGE")


def _synthetic_new_points() -> list[dict[str, object]]:
    # Completely synthetic fixture; no GPS read from private dataset.
    return [
        {
            "timestamp_utc": f"2009-01-{day:02d}T13:{minute:02d}:00Z",
            "latitude": 39.9, "longitude": 116.4,
        }
        for day in (5, 6, 7) for minute in (0, 5, 10, 15, 20)
    ]


def execute(cache: Path) -> dict:
    cache = cache.expanduser().resolve()
    check(cache.is_file(), "PRIVATE_CP1_CACHE_MISSING")
    # This is an admin-trusted local pickle, not an arbitrary uploaded file.
    stays = normalize_users(pd.read_pickle(cache))
    locations, labels, cases = canonical_reference(stays)
    check(len(set(cases.values())) >= 3, "INSUFFICIENT_DISTINCT_AUTH_SUBJECTS")

    # Explicit absolute /tmp: do not persist credentials or sessions to Modal Volume.
    with tempfile.TemporaryDirectory(prefix="geolife-e2e-", dir="/tmp") as private:
        db = Path(private) / "audit_auth.sqlite3"
        passwords: dict[str, str] = {}
        # Separate demo account per case, even if HOME and OFFICE share a user.
        for case, uid in cases.items():
            account = "audit_" + case.lower()
            password = secrets.token_urlsafe(36)
            provision_account(db, account, uid, password)
            passwords[case] = password

        _load_stays_cache.cache_clear()
        with patch.dict(os.environ, {
            "GEOLIFE_DEMO_AUTH_DB": str(db),
            "GEOLIFE_STAYS_CACHE": str(cache),
            "GEOLIFE_ROLLOUT_MODE": "baseline",
        }):
            with TestClient(app) as client:
                check(client.post("/v2/me/dataset-inferences").status_code == 401,
                      "NO_ANONYMOUS_DATASET_ACCESS")
                check(client.post("/v2/me/inferences", json={
                    "points": _synthetic_new_points()
                }).status_code == 401, "NO_ANONYMOUS_NEW_GPS")
                check(client.get("/v2/auth/me").status_code == 401,
                      "NO_ANONYMOUS_ACCOUNT_DETAILS")
                check(client.get("/demo").status_code == 200, "MAP_SHELL_ACCESS")
                responses: dict[str, dict] = {}
                auth_headers: dict[str, dict[str, str]] = {}
                for case, uid in cases.items():
                    account = "audit_" + case.lower()
                    login = client.post("/v2/auth/login", json={
                        "account_id": account,
                        "password": passwords[case],
                    })
                    check(login.status_code == 200, "LOGIN")
                    value = login.json()
                    check(value["dataset_user_id"] == uid, "LOGIN_SCOPE")
                    auth_headers[case] = {"Authorization": "Bearer " + value["access_token"]}
                    me = client.get("/v2/auth/me", headers=auth_headers[case])
                    check(me.status_code == 200 and
                          me.json()["dataset_user_id"] == uid, "AUTH_ME_SCOPE")
                    call = client.post(
                        "/v2/me/dataset-inferences", headers=auth_headers[case]
                    )
                    check(call.status_code == 200, "DATASET_HTTP_STATUS")
                    body = call.json()
                    validate_inference(body, uid, stays, locations, labels)
                    responses[case] = body

                check(responses["HOME"]["predictions"]["HOME"]["status"] == "emitted",
                      "HOME_CASE_INFERENCE")
                check(responses["OFFICE"]["predictions"]["OFFICE"]["status"] == "emitted",
                      "OFFICE_CASE_INFERENCE")
                check(all(v["status"] == "abstained"
                          for v in responses["RECURRING_ABSTAIN"]["predictions"].values()),
                      "RECURRING_ABSTAIN_INFERENCE")
                check(responses["RECURRING_ABSTAIN"]["recurring_locations"] > 0,
                      "RECURRING_ABSTAIN_WITH_RECURRING")
                check(responses["NO_STAY"]["detected_stays"] == 0 and
                      responses["NO_STAY"]["map_locations"] == [],
                      "NO_STAY_ABSTENTION")
                check(all(v["status"] == "abstained"
                          for v in responses["NO_STAY"]["predictions"].values()),
                      "NO_STAY_LABELS")

                # A cannot choose B's dataset by injecting any request body.
                different = next(case for case in cases
                                 if cases[case] != cases["HOME"])
                overridden = client.post(
                    "/v2/me/dataset-inferences",
                    headers=auth_headers["HOME"],
                    json={"dataset_user_id": cases[different]},
                )
                check(overridden.status_code == 200, "OVERRIDE_HTTP_STATUS")
                check(overridden.json() == responses["HOME"],
                      "CROSS_USER_REQUEST_BODY_OVERRIDE")
                check(client.post(
                    "/v2/me/dataset-inferences", headers={"Authorization": "Bearer invalid"}
                ).status_code == 401, "INVALID_SESSION")

                # The new-GPS route must not silently include dataset cached stays.
                new_gps = client.post(
                    "/v2/me/inferences",
                    headers=auth_headers["NO_STAY"],
                    json={"points": _synthetic_new_points()},
                )
                check(new_gps.status_code == 200, "NEW_GPS_HTTP_STATUS")
                gps_body = new_gps.json()
                check(gps_body["source"] == "new_gps" and gps_body["raw_points"] == 15,
                      "NEW_GPS_SOURCE")
                check(gps_body["detected_stays"] == 3, "NEW_GPS_CP1_STAYS")
                check(gps_body["predictions"]["HOME"]["status"] == "emitted",
                      "NEW_GPS_CP2_HOME")
                check(gps_body["dataset_user_id"] == cases["NO_STAY"],
                      "NEW_GPS_AUTH_SCOPE")

                logout = client.post("/v2/auth/logout", headers=auth_headers["HOME"])
                check(logout.status_code == 200, "LOGOUT_HTTP_STATUS")
                check(client.post(
                    "/v2/me/dataset-inferences", headers=auth_headers["HOME"]
                ).status_code == 401, "REVOKED_TOKEN")
                # Another account remains valid: logout is session-scoped.
                check(client.get(
                    "/v2/auth/me", headers=auth_headers["NO_STAY"]
                ).status_code == 200, "CROSS_ACCOUNT_SESSION_INDEPENDENCE")

        _load_stays_cache.cache_clear()

    # Deliberately only population-level metrics and gate labels, never UIDs,
    # marker coordinates, user-specific score/counts, tokens or passwords.
    return {
        "audit": "real_geolife_cp1_cache_api_e2e",
        "status": "PASS",
        "frozen": FROZEN.copy(),
        "case_types_tested": sorted(cases),
        "case_count": len(cases),
        "checks": [
            "frozen_full_release_parity",
            "authenticated_real_cache_inference",
            "per_user_map_label_coordinate_parity",
            "real_cache_home_office_recurring_abstain_no_stay",
            "request_body_user_override_blocked",
            "unauthorized_access_and_token_revocation",
            "synthetic_new_gps_mode",
        ],
        "cache_exported": False,
        "private_identifiers_exported": False,
        "credentials_persisted": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--cache", type=Path, default=DEFAULT_CACHE,
        help="Trusted, existing private CP1 stays_baseline_v1.pkl; default Modal Volume path",
    )
    args = parser.parse_args()
    try:
        report = execute(args.cache)
    except AuditGateFailure as err:
        print(json.dumps({"audit": "real_geolife_cp1_cache_api_e2e",
                          "status": "FAIL", "gate": str(err)}))
        return 1
    except Exception as err:
        # Never print exception messages or tracebacks: these may include
        # absolute private paths, credentials, GPS or dataset user IDs.
        print(json.dumps({"audit": "real_geolife_cp1_cache_api_e2e",
                          "status": "FAIL", "gate": "UNEXPECTED_" + type(err).__name__}))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
