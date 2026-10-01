from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


MODULE_PATH = (
    Path(__file__).resolve().parents[1]
    / "analysis"
    / "05c_stable_secondary_independent_evidence.py"
)


def _module():
    spec = spec_from_file_location("stage05c", MODULE_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_synthetic_self_check() -> None:
    result = _module().synthetic_self_check()
    assert result["status"] == "ok"
    assert result["candidate_users"] == 1
    assert result["top1_axes"] >= 3
