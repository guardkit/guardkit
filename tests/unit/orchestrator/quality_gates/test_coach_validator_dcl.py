"""Unit tests for the Coach's DCL oracle gate (Phase D, design §1 / D1).

``_check_dcl_results`` is the dcl spec-track sibling of ``_check_bdd_results``:
same ``(blocking, non_blocking)`` shape; compile/derivation failures block as
``dcl_failure``; a pass or an absent key is tolerated (never silent-green on a
malformed status).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


@pytest.fixture
def validator(tmp_path: Path) -> CoachValidator:
    (tmp_path / "features").mkdir()
    return CoachValidator(worktree_path=str(tmp_path), task_id="TASK-STAT-001")


def test_absent_dcl_results_is_tolerated(validator: CoachValidator):
    blocking, non_blocking = validator._check_dcl_results({})
    assert blocking == []
    assert non_blocking == []


def test_pass_status_is_green(validator: CoachValidator):
    results = {
        "dcl_results": {
            "status": "pass",
            "dcl_file": "features/stats/stats.dcl",
            "feature": "stats",
            "run_ids": ["A-OUTCOME"],
        }
    }
    blocking, non_blocking = validator._check_dcl_results(results)
    assert blocking == []
    assert non_blocking == []


def test_compile_error_blocks(validator: CoachValidator):
    results = {
        "dcl_results": {
            "status": "compile_error",
            "dcl_file": "features/stats/stats.dcl",
            "feature": "stats",
            "error_count": 2,
            "errors": ["unexpected token 'capabilty' (line 4)", "unknown type"],
        }
    }
    blocking, non_blocking = validator._check_dcl_results(results)
    assert len(blocking) == 1
    issue = blocking[0]
    assert issue["severity"] == "must_fix"
    assert issue["category"] == "dcl_failure"
    assert issue["error_count"] == 2
    assert "unexpected token" in issue["description"]
    assert non_blocking == []


def test_derivation_error_blocks(validator: CoachValidator):
    results = {
        "dcl_results": {
            "status": "derivation_error",
            "dcl_file": "features/stats/stats.dcl",
            "feature": "stats",
            "derivation_error": "capability 'X' has no binding entry",
        }
    }
    blocking, non_blocking = validator._check_dcl_results(results)
    assert len(blocking) == 1
    assert blocking[0]["category"] == "dcl_failure"
    assert "no binding entry" in blocking[0]["description"]


def test_unrecognised_status_never_silent_green(validator: CoachValidator):
    results = {
        "dcl_results": {
            "status": "weird",
            "dcl_file": "features/stats/stats.dcl",
            "feature": "stats",
        }
    }
    blocking, _ = validator._check_dcl_results(results)
    assert len(blocking) == 1
    assert blocking[0]["category"] == "dcl_failure"
