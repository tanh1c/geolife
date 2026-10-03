"""Stage 07f: BCL POI 2008 acquisition / provenance / CRS audit.

This stage is gate-first. It does not perform semantic WORK/OFFICE labeling.

Primary responsibilities:
- verify the official BCL / Figshare record at runtime;
- record public metadata, file availability and explicit license metadata;
- support deterministic cached or manual acquisition on Modal Volume;
- verify file size/checksum when metadata provides them;
- inspect ArcGIS Personal Geodatabase (.mdb) structure and CRS through
  system-tool reports produced by a Modal worker;
- keep unresolved access/license/CRS states explicitly blocked.

The downstream semantic join is intentionally out of scope.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import md5, sha256
import json
from pathlib import Path
import re
from typing import Any, Iterable
from urllib.parse import urlparse

import pandas as pd


BCL_OFFICIAL_URL = "https://www.beijingcitylab.org/data/data-011/index.html"
FIGSHARE_DOI = "10.6084/m9.figshare.28667492"
FIGSHARE_ARTICLE_ID = 28667492
FIGSHARE_API_URL = f"https://api.figshare.com/v2/articles/{FIGSHARE_ARTICLE_ID}"
EXPECTED_LOCATION_NAMESPACE = "production_complete_link_200m_beijing_policy_v1"

ALLOWED_ARCHIVE_SUFFIXES = {".mdb", ".zip"}
RECOGNIZED_REUSE_LICENSE_TOKENS = (
    "cc by",
    "creative commons attribution",
    "cc0",
    "public domain",
    "odc-by",
    "odbl",
)


@dataclass(frozen=True)
class GateDecision:
    metadata_access: str
    file_access: str
    license_status: str
    format_status: str
    crs_status: str
    runner_status: str
    notes: str


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def _normalise_license(metadata: dict[str, Any]) -> tuple[str, str]:
    license_value = metadata.get("license")
    if isinstance(license_value, dict):
        name = _as_text(license_value.get("name") or license_value.get("title"))
        url = _as_text(license_value.get("url"))
        return name, url
    if isinstance(license_value, str):
        return license_value.strip(), ""

    # Some Figshare responses expose license fields differently.
    name = _as_text(
        metadata.get("license_name")
        or metadata.get("licence")
        or metadata.get("licence_name")
    )
    url = _as_text(metadata.get("license_url") or metadata.get("licence_url"))
    return name, url


def license_is_explicit_reuse_candidate(name: str, url: str = "") -> bool:
    """Return whether metadata explicitly names a reusable licence candidate.

    Conservative automation policy:
    - allow CC BY, CC BY-SA, CC0/public-domain and ODC attribution/share-alike;
    - block NC and ND variants for automated downstream reuse review;
    - ambiguous/missing terms remain blocked.

    This is a technical gate, not legal advice.
    """
    haystack = f"{name} {url}".lower()
    blockers = (
        "noncommercial",
        "non-commercial",
        "cc by-nc",
        "/by-nc",
        "no derivatives",
        "no-derivatives",
        "cc by-nd",
        "/by-nd",
    )
    if any(token in haystack for token in blockers):
        return False

    allow = (
        "cc by ",
        "cc-by ",
        "creative commons attribution",
        "cc by-sa",
        "cc-by-sa",
        "cc0",
        "public domain",
        "odc-by",
        "odbl",
    )
    return any(token in haystack for token in allow)


def figshare_files(metadata: dict[str, Any]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for item in metadata.get("files") or []:
        if not isinstance(item, dict):
            continue
        name = _as_text(item.get("name"))
        download_url = _as_text(
            item.get("download_url")
            or item.get("url")
            or item.get("download_url_private")
        )
        suffix = Path(name).suffix.lower()
        rows.append(
            {
                "file_id": item.get("id"),
                "name": name,
                "suffix": suffix,
                "size_bytes": pd.to_numeric(
                    pd.Series([item.get("size")]), errors="coerce"
                ).iloc[0],
                "download_url": download_url,
                "computed_md5": _as_text(item.get("computed_md5")),
                "supplied_md5": _as_text(item.get("supplied_md5")),
                "is_link_only": bool(item.get("is_link_only", False)),
            }
        )
    return pd.DataFrame(
        rows,
        columns=[
            "file_id",
            "name",
            "suffix",
            "size_bytes",
            "download_url",
            "computed_md5",
            "supplied_md5",
            "is_link_only",
        ],
    )


def summarize_figshare_metadata(
    metadata: dict[str, Any] | None,
    *,
    http_status: int | None = None,
    error: str | None = None,
) -> pd.DataFrame:
    metadata = metadata or {}
    license_name, license_url = _normalise_license(metadata)
    files = figshare_files(metadata)
    total_bytes = (
        int(pd.to_numeric(files["size_bytes"], errors="coerce").fillna(0).sum())
        if not files.empty
        else 0
    )
    return pd.DataFrame(
        [
            {
                "http_status": http_status,
                "error": error,
                "article_id": metadata.get("id"),
                "title": _as_text(metadata.get("title")),
                "doi": _as_text(metadata.get("doi")),
                "url_public_api": FIGSHARE_API_URL,
                "license_name": license_name,
                "license_url": license_url,
                "file_count": int(len(files)),
                "downloadable_file_count": int(
                    files["download_url"].astype(bool).sum()
                    if not files.empty
                    else 0
                ),
                "total_file_bytes": total_bytes,
            }
        ]
    )


def evaluate_acquisition_gates(
    metadata: dict[str, Any] | None,
    *,
    http_status: int | None,
    error: str | None = None,
    inspected_crs: str | None = None,
    local_candidate_files: Iterable[str] = (),
) -> GateDecision:
    metadata = metadata or {}
    files = figshare_files(metadata)
    license_name, license_url = _normalise_license(metadata)

    metadata_ok = http_status == 200 and bool(metadata)
    metadata_access = "pass_public_metadata" if metadata_ok else "blocked_metadata_access"

    downloadable = (
        files.loc[files["download_url"].astype(bool)].copy()
        if not files.empty
        else files
    )
    local_candidates = [str(value) for value in local_candidate_files if str(value)]
    if not downloadable.empty:
        file_access = "pass_public_file"
    elif local_candidates:
        file_access = "pass_manual_or_cached_file"
    else:
        file_access = "blocked_no_file_available"

    if license_is_explicit_reuse_candidate(license_name, license_url):
        license_status = f"pass_explicit:{license_name or license_url}"
    elif license_name or license_url:
        license_status = f"blocked_unreviewed_explicit_license:{license_name or license_url}"
    else:
        license_status = "blocked_no_explicit_license_metadata"

    suffixes = {
        str(value).lower()
        for value in downloadable["suffix"].tolist()
        if str(value)
    }
    suffixes.update(Path(value).suffix.lower() for value in local_candidates)
    if ".mdb" in suffixes:
        format_status = "pass_mdb"
    elif ".zip" in suffixes:
        format_status = "inspect_archive_for_mdb"
    elif suffixes:
        format_status = "blocked_unexpected_file_format"
    else:
        format_status = "blocked_no_file_to_inspect"

    crs_text = _as_text(inspected_crs)
    crs_status = "pass_inspected_crs" if crs_text else "blocked_pending_mdb_crs_inspection"

    access_ready = file_access.startswith("pass_")
    license_ready = license_status.startswith("pass_")
    format_ready = format_status in {"pass_mdb", "inspect_archive_for_mdb"}
    crs_ready = crs_status.startswith("pass_")

    if metadata_ok and access_ready and license_ready and format_ready and crs_ready:
        runner_status = "ready_for_normalization"
    elif metadata_ok and access_ready and license_ready and format_ready:
        runner_status = "ready_for_mdb_inspection"
    else:
        runner_status = "blocked"

    notes = "; ".join(
        value
        for value in [
            error or "",
            f"files={len(files)}",
            f"local_candidates={len(local_candidates)}",
        ]
        if value
    )

    return GateDecision(
        metadata_access=metadata_access,
        file_access=file_access,
        license_status=license_status,
        format_status=format_status,
        crs_status=crs_status,
        runner_status=runner_status,
        notes=notes,
    )


def gates_frame(decision: GateDecision) -> pd.DataFrame:
    return pd.DataFrame([decision.__dict__])


def select_public_download_candidate(metadata: dict[str, Any]) -> dict[str, Any] | None:
    """Choose one deterministic Figshare file candidate.

    Prefer direct MDB, then ZIP. Multiple candidates of the same class are
    sorted by name and file id to keep reruns deterministic.
    """
    files = figshare_files(metadata)
    if files.empty:
        return None
    files = files.loc[files["download_url"].astype(bool)].copy()
    if files.empty:
        return None

    priority = {".mdb": 0, ".zip": 1}
    files = files.loc[files["suffix"].isin(priority)].copy()
    if files.empty:
        return None
    files["_priority"] = files["suffix"].map(priority)
    files["_file_id_sort"] = pd.to_numeric(
        files["file_id"], errors="coerce"
    ).fillna(10**18)
    row = files.sort_values(
        ["_priority", "name", "_file_id_sort"],
        kind="stable",
    ).iloc[0]
    return {
        key: row[key]
        for key in [
            "file_id",
            "name",
            "suffix",
            "size_bytes",
            "download_url",
            "computed_md5",
            "supplied_md5",
            "is_link_only",
        ]
    }


def hash_file(path: Path, *, algorithm: str = "sha256", chunk_size: int = 8 * 1024 * 1024) -> str:
    if algorithm == "sha256":
        digest = sha256()
    elif algorithm == "md5":
        digest = md5()
    else:
        raise ValueError(f"unsupported hash algorithm: {algorithm}")

    with Path(path).open("rb") as handle:
        while True:
            chunk = handle.read(chunk_size)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def verify_download(
    path: Path,
    *,
    expected_size: int | float | None = None,
    expected_md5: str | None = None,
) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        return {
            "exists": False,
            "size_ok": False,
            "md5_ok": False,
            "size_bytes": None,
            "sha256": None,
            "md5": None,
        }

    actual_size = path.stat().st_size
    expected_size_int = (
        int(expected_size)
        if expected_size is not None and not pd.isna(expected_size)
        else None
    )
    actual_md5 = hash_file(path, algorithm="md5")
    actual_sha256 = hash_file(path, algorithm="sha256")
    expected_md5_normalized = _as_text(expected_md5).lower()

    return {
        "exists": True,
        "size_ok": (
            True
            if expected_size_int is None
            else actual_size == expected_size_int
        ),
        "md5_ok": (
            True
            if not expected_md5_normalized
            else actual_md5.lower() == expected_md5_normalized
        ),
        "size_bytes": int(actual_size),
        "sha256": actual_sha256,
        "md5": actual_md5,
    }


def safe_member_path(root: Path, member_name: str) -> Path:
    """Resolve one archive member and reject path traversal."""
    root = Path(root).resolve()
    target = (root / member_name).resolve()
    if root != target and root not in target.parents:
        raise ValueError(f"unsafe archive path: {member_name}")
    return target


def discover_mdb_files(root: Path) -> list[Path]:
    root = Path(root)
    if not root.exists():
        return []
    return sorted(path for path in root.rglob("*.mdb") if path.is_file())


def parse_mdb_tables(stdout: str) -> list[str]:
    return [
        line.strip()
        for line in stdout.splitlines()
        if line.strip() and not line.strip().lower().startswith("msys")
    ]


def parse_ogrinfo_report(stdout: str) -> dict[str, Any]:
    """Parse a small subset of ogrinfo -so -al output needed for gates."""
    layers = re.findall(r"^Layer name:\s*(.+)$", stdout, flags=re.MULTILINE)
    geometry_types = re.findall(r"^Geometry:\s*(.+)$", stdout, flags=re.MULTILINE)
    feature_counts = [
        int(value.replace(",", ""))
        for value in re.findall(r"^Feature Count:\s*([0-9,]+)$", stdout, flags=re.MULTILINE)
    ]
    extents = re.findall(
        r"^Extent:\s*\(([^\n]+)\)$",
        stdout,
        flags=re.MULTILINE,
    )

    srs_blocks: list[str] = []
    lines = stdout.splitlines()
    for idx, line in enumerate(lines):
        if line.startswith("Layer SRS WKT:"):
            block = [line.split(":", 1)[1].strip()]
            j = idx + 1
            while j < len(lines):
                next_line = lines[j]
                if (
                    next_line.startswith("Data axis to CRS axis mapping:")
                    or next_line.startswith("FID Column")
                    or next_line.startswith("Geometry Column")
                    or re.match(r"^[A-Za-z0-9_\u4e00-\u9fff .-]+:\s", next_line)
                ):
                    break
                block.append(next_line.rstrip())
                j += 1
            srs = "\n".join(value for value in block if value).strip()
            if srs and srs.lower() not in {"(unknown)", "unknown"}:
                srs_blocks.append(srs)

    epsg_codes = sorted(
        set(
            re.findall(
                r'(?:AUTHORITY\\["EPSG","|ID\\["EPSG",)(\\d+)',
                stdout,
            )
        )
    )

    field_names: list[str] = []
    for line in lines:
        match = re.match(r"^\s{0,4}([^:]+):\s+(String|Integer|Integer64|Real|Date|DateTime|Binary)", line)
        if match:
            field_names.append(match.group(1).strip())

    return {
        "layers": layers,
        "layer_count": len(layers),
        "geometry_types": geometry_types,
        "feature_counts": feature_counts,
        "extents": extents,
        "srs_blocks": srs_blocks,
        "epsg_codes": epsg_codes,
        "field_names": sorted(set(field_names)),
    }


def summarize_mdb_inspection(report: dict[str, Any]) -> pd.DataFrame:
    ogr = report.get("ogr") or {}
    table_names = report.get("mdb_tables") or []
    return pd.DataFrame(
        [
            {
                "mdb_path": _as_text(report.get("mdb_path")),
                "mdbtools_available": bool(report.get("mdbtools_available")),
                "gdal_pgeo_available": bool(report.get("gdal_pgeo_available")),
                "table_count": int(len(table_names)),
                "layer_count": int(ogr.get("layer_count") or 0),
                "point_like_layer_count": int(
                    sum(
                        "point" in _as_text(value).lower()
                        for value in ogr.get("geometry_types") or []
                    )
                ),
                "max_feature_count": int(
                    max(ogr.get("feature_counts") or [0])
                ),
                "epsg_codes": ",".join(ogr.get("epsg_codes") or []),
                "crs_text_available": bool(ogr.get("srs_blocks")),
                "field_count": int(len(ogr.get("field_names") or [])),
                "inspection_error": _as_text(report.get("error")),
            }
        ]
    )


def choose_crs_text(report: dict[str, Any]) -> str:
    ogr = report.get("ogr") or {}
    epsg = ogr.get("epsg_codes") or []
    if epsg:
        return "EPSG:" + ",".join(epsg)
    srs_blocks = ogr.get("srs_blocks") or []
    return _as_text(srs_blocks[0]) if srs_blocks else ""


def build_bcl_eligible_anchor_summary(anchor_dates: pd.DataFrame) -> pd.DataFrame:
    required = {
        "user_id",
        "location_id",
        "median_observation_year",
        "location_namespace",
    }
    missing = required.difference(anchor_dates.columns)
    if missing:
        raise ValueError(f"anchor dates missing columns: {sorted(missing)}")

    if not anchor_dates["location_namespace"].eq(EXPECTED_LOCATION_NAMESPACE).all():
        raise ValueError("anchor dates use incompatible location namespace")

    years = pd.to_numeric(
        anchor_dates["median_observation_year"], errors="raise"
    ).astype(int)
    eligible = anchor_dates.loc[years.isin([2007, 2008, 2009])].copy()
    eligible["bcl_alignment_type"] = years.loc[eligible.index].map(
        lambda year: "exact_year" if year == 2008 else "nearest_year_proxy"
    )
    eligible["bcl_temporal_offset_years"] = (
        2008 - years.loc[eligible.index]
    ).astype(int)

    return pd.DataFrame(
        [
            {
                "candidate_anchors": int(len(anchor_dates)),
                "candidate_users": int(anchor_dates["user_id"].astype(str).nunique()),
                "bcl_eligible_anchors": int(len(eligible)),
                "bcl_eligible_users": int(eligible["user_id"].astype(str).nunique()),
                "bcl_exact_2008_anchors": int(
                    eligible["bcl_alignment_type"].eq("exact_year").sum()
                ),
                "bcl_proxy_anchors": int(
                    eligible["bcl_alignment_type"].eq("nearest_year_proxy").sum()
                ),
            }
        ]
    )


def acquisition_manifest(
    *,
    source_mode: str,
    source_url: str,
    local_path: str,
    file_verification: dict[str, Any],
    metadata_summary: pd.DataFrame,
    gate_decision: GateDecision,
    inspection_summary: pd.DataFrame | None = None,
) -> dict[str, Any]:
    manifest = {
        "source_id": "bcl_poi_2008",
        "official_url": BCL_OFFICIAL_URL,
        "figshare_doi": FIGSHARE_DOI,
        "figshare_article_id": FIGSHARE_ARTICLE_ID,
        "source_mode": source_mode,
        "source_url": source_url,
        "local_path": local_path,
        "file_verification": file_verification,
        "metadata_summary": (
            metadata_summary.iloc[0].where(pd.notna(metadata_summary.iloc[0]), None).to_dict()
            if not metadata_summary.empty
            else {}
        ),
        "gates": gate_decision.__dict__,
        "inspection_summary": (
            inspection_summary.iloc[0].where(pd.notna(inspection_summary.iloc[0]), None).to_dict()
            if inspection_summary is not None and not inspection_summary.empty
            else {}
        ),
        "semantic_claim_allowed": False,
        "occupation_inference_allowed": False,
    }
    return json.loads(json.dumps(manifest, default=str))


def synthetic_self_check() -> dict[str, Any]:
    metadata = {
        "id": FIGSHARE_ARTICLE_ID,
        "title": "Points of interest of China in 2008",
        "doi": FIGSHARE_DOI,
        "license": {
            "name": "CC BY 4.0",
            "url": "https://creativecommons.org/licenses/by/4.0/",
        },
        "files": [
            {
                "id": 1,
                "name": "poi2008.zip",
                "size": 100,
                "download_url": "https://example.invalid/poi2008.zip",
                "computed_md5": "abc",
            }
        ],
    }
    decision = evaluate_acquisition_gates(
        metadata,
        http_status=200,
        inspected_crs="EPSG:4326",
    )
    assert decision.runner_status == "ready_for_normalization"
    candidate = select_public_download_candidate(metadata)
    assert candidate and candidate["name"] == "poi2008.zip"

    parsed = parse_ogrinfo_report(
        """Layer name: POI
Geometry: Point
Feature Count: 6000000
Extent: (73.0, 18.0) - (135.0, 54.0)
Layer SRS WKT:
GEOGCRS[\"WGS 84\",ID[\"EPSG\",4326]]
name: String (255.0)
"""
    )
    assert parsed["layers"] == ["POI"]
    assert parsed["feature_counts"] == [6000000]
    assert "name" in parsed["field_names"]

    return {"status": "ok", "article_id": FIGSHARE_ARTICLE_ID}
