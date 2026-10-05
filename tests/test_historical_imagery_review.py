from importlib.util import module_from_spec, spec_from_file_location
import json
from pathlib import Path
import sys

import pandas as pd
import pytest


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "07k_historical_imagery_review.py"
)


def _module():
    spec = spec_from_file_location("stage07k", MODULE_PATH)
    assert spec and spec.loader
    module = module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _panel():
    return pd.DataFrame(
        [
            {
                "user_id": "secret-user-a",
                "audit_group": "margin_near",
                "candidate_location_id": 1,
                "production_home_location_id": 0,
                "full_support_days": 4,
                "full_office_share": .31,
                "howde_matches_candidate": True,
                "recurrence_matches_candidate": False,
                "split_full_candidate_match_count": 1,
                "full_candidate_heldout_top1": False,
                "dropout_candidate_retention": .89,
                "bcl_evaluable": False,
            },
            {
                "user_id": "secret-user-b",
                "audit_group": "baseline",
                "candidate_location_id": 2,
                "production_home_location_id": 0,
                "full_support_days": 5,
                "full_office_share": .55,
                "howde_matches_candidate": True,
                "recurrence_matches_candidate": True,
                "split_full_candidate_match_count": 2,
                "full_candidate_heldout_top1": True,
                "dropout_candidate_retention": 1.0,
                "bcl_evaluable": True,
            },
        ]
    )


def _locations():
    return pd.DataFrame(
        [
            {"user_id":"secret-user-a","location_id":0,"latitude":39.90,"longitude":116.40},
            {"user_id":"secret-user-a","location_id":1,"latitude":39.91,"longitude":116.41},
            {"user_id":"secret-user-b","location_id":0,"latitude":39.80,"longitude":116.30},
            {"user_id":"secret-user-b","location_id":2,"latitude":39.82,"longitude":116.32},
        ]
    )


def _stays():
    return pd.DataFrame(
        [
            {"user_id":"secret-user-a","location_id":1,"arrival_local_date":"2008-01-01"},
            {"user_id":"secret-user-a","location_id":1,"arrival_local_date":"2008-01-03"},
            {"user_id":"secret-user-a","location_id":1,"arrival_local_date":"2008-01-10"},
            {"user_id":"secret-user-b","location_id":2,"arrival_local_date":"2009-02-01"},
        ]
    )


def test_blinded_manifest_excludes_user_and_group():
    module = _module()
    spatial = module.build_spatial_review_panel(
        _panel(), _locations(), _stays()
    )
    manifest = module.blinded_review_manifest(spatial)

    assert "user_id" not in manifest.columns
    assert "audit_group" not in manifest.columns
    assert set(manifest["audit_id"]) == set(spatial["audit_id"])
    assert manifest["observation_median_date"].notna().all()


def test_unblinding_key_keeps_private_link():
    module = _module()
    spatial = module.build_spatial_review_panel(
        _panel(), _locations(), _stays()
    )
    key = module.unblinding_key(spatial)
    assert {"audit_id","user_id","audit_group","candidate_location_id"}.issubset(key.columns)
    assert set(key["user_id"]) == {"secret-user-a","secret-user-b"}


def test_priority_contains_only_near_miss_ids():
    module = _module()
    spatial = module.build_spatial_review_panel(
        _panel(), _locations(), _stays()
    )
    priority = module.review_priority_ids(spatial)
    key = module.unblinding_key(spatial)
    joined = priority.merge(key[["audit_id","audit_group"]],on="audit_id")
    assert joined["audit_group"].tolist() == ["margin_near"]


def test_kml_is_blinded_and_has_rings(tmp_path):
    module = _module()
    spatial = module.build_spatial_review_panel(
        _panel(), _locations(), _stays()
    )
    priority = module.review_priority_ids(spatial)
    path = module.write_review_kml(
        spatial,
        tmp_path / "review.kml",
        audit_ids=priority["audit_id"],
    )
    text = path.read_text(encoding="utf-8")

    assert "secret-user-a" not in text
    assert "margin_near" not in text
    assert "Stage-07j" not in text
    assert "50m" in text
    assert "100m" in text
    assert "150m" in text
    assert "HOME reference" in text
    assert "Observation median" in text


def test_review_validation_accepts_rubric_and_rejects_unknown():
    module = _module()
    review = pd.DataFrame(
        [
            {
                "audit_id":"I01",
                "imagery_available":"yes",
                "structure_present":"yes",
                "candidate_inside_same_complex":"unclear",
                "visual_context_class":"education_campus",
                "visual_context_confidence":"medium",
            }
        ]
    )
    checked = module.validate_completed_review(review)
    assert len(checked) == 1

    bad = review.copy()
    bad.loc[0,"visual_context_class"] = "definitely_office"
    with pytest.raises(ValueError, match="visual_context_class"):
        module.validate_completed_review(bad)


def test_synthetic_self_check():
    module = _module()
    result = module.synthetic_self_check()
    assert result["status"] == "ok"
    assert result["rows"] == 2


def test_stage07k_notebook_contract():
    path = (
        Path(__file__).resolve().parents[1]
        / "notebooks"
        / "07k_historical_imagery_review.ipynb"
    )
    notebook = json.loads(path.read_text(encoding="utf-8"))
    code = "\n".join(
        "".join(cell.get("source", []))
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
    )

    required = [
        "07j audit reproduction: PASS",
        "blinding + spatial/date validation: PASS",
        "near_miss_9_blinded_historical_imagery_review_private.kml",
        "baseline16_blinded_historical_imagery_reference_private.kml",
        "historical_imagery_unblinding_key_private.pkl",
        "near_miss_9_blinded_review_manifest_private.csv",
        "historical_imagery_review_rubric.csv",
    ]
    for snippet in required:
        assert snippet in code

    assert "simplekml" not in code
