"""CoachValidator BDD oracle gate tests (TASK-BDD-E8954).

Validates Coach behaviour for the ``bdd_results`` gate added in
TASK-BDD-E8954. The gate enforces the three-state model from the task spec:

- ``scenarios_failed > 0``  → reject (must_fix ``bdd_failure``)
- ``scenarios_pending > 0`` → approve **with feedback** (should_fix
                              ``bdd_pending``); MUST NOT block on pending alone
- ``bdd_results`` absent    → no gate active (back-compat: identical to today)

The broader CoachValidator test suite remains in
``tests/unit/test_coach_validator.py``. This file exists at the path named
in the AC for direct discoverability.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from guardkit.orchestrator.quality_gates import CoachValidator


# ---------------------------------------------------------------------------
# Fixtures (mirror those from the broader CoachValidator suite — copied here
# to keep this file self-contained per AC: it must be runnable in isolation)
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_worktree(tmp_path):
    worktree = tmp_path / "worktrees" / "TASK-001"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def task_work_results_dir(tmp_worktree):
    results_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
    results_dir.mkdir(parents=True)
    return results_dir


def _make_task_work_results(bdd_block: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """A passing baseline task_work_results, optionally with bdd_results attached."""
    results: Dict[str, Any] = {
        "quality_gates": {
            "tests_passing": True,
            "tests_passed": 15,
            "tests_failed": 0,
            "coverage": 85,
            "coverage_met": True,
            "all_passed": True,
        },
        "code_review": {"score": 82, "solid": 85, "dry": 80, "yagni": 82},
        "plan_audit": {"violations": 0, "file_count_match": True},
        "requirements_met": [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
        ],
    }
    if bdd_block is not None:
        results["bdd_results"] = bdd_block
    return results


def _make_task() -> Dict[str, Any]:
    return {
        "acceptance_criteria": [
            "OAuth2 authentication flow",
            "Token generation",
            "Token refresh",
        ],
    }


def _write(results_dir: Path, results: Dict[str, Any]) -> Path:
    results_path = results_dir / "task_work_results.json"
    results_path.write_text(json.dumps(results, indent=2))
    return results_path


# ---------------------------------------------------------------------------
# AC tests — names match those listed in TASK-BDD-E8954 acceptance criteria
# ---------------------------------------------------------------------------


def test_bdd_failure_rejects(tmp_worktree, task_work_results_dir):
    """AC: Coach rejects when ``bdd_results.scenarios_failed > 0``."""
    _write(
        task_work_results_dir,
        _make_task_work_results({
            "scenarios_passed": 1,
            "scenarios_failed": 1,
            "scenarios_pending": 0,
            "failures": [
                {
                    "feature_file": "features/login.feature",
                    "scenario_name": "User logs in",
                    "failing_step": "Then the user is greeted",
                    "reason": "AssertionError: assert 'Welcome' in 'Goodbye'",
                }
            ],
            "pending": [],
            "feature_files": ["features/login.feature"],
            "tag": "@task:TASK-001",
        }),
    )

    # Independent verification passes — only the BDD gate must reject.
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="15 passed in 1.45s",
            stderr="",
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _make_task())

    assert result.decision == "feedback"
    bdd_failure_issues = [i for i in result.issues if i.get("category") == "bdd_failure"]
    assert len(bdd_failure_issues) == 1
    assert bdd_failure_issues[0]["severity"] == "must_fix"
    assert bdd_failure_issues[0]["scenarios_failed"] == 1
    assert "BDD scenarios failed" in result.rationale


def test_bdd_pending_approves_with_feedback(tmp_worktree, task_work_results_dir):
    """AC: pending alone does NOT block; surfaces as ``should_fix`` feedback only."""
    _write(
        task_work_results_dir,
        _make_task_work_results({
            "scenarios_passed": 1,
            "scenarios_failed": 0,
            "scenarios_pending": 2,
            "failures": [],
            "pending": [
                {
                    "feature_file": "features/signup.feature",
                    "scenario_name": "User signs up",
                    "pending_step": "When the user signs up",
                },
                {
                    "feature_file": "features/signup.feature",
                    "scenario_name": "User confirms email",
                    "pending_step": "Then a confirmation email is sent",
                },
            ],
            "feature_files": ["features/signup.feature"],
            "tag": "@task:TASK-001",
        }),
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="15 passed in 1.45s",
            stderr="",
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _make_task())

    # Pending alone MUST NOT block approval.
    assert result.decision == "approve"
    # ...but pending items MUST surface in feedback as actionable work.
    bdd_pending_issues = [i for i in result.issues if i.get("category") == "bdd_pending"]
    assert len(bdd_pending_issues) == 1
    assert bdd_pending_issues[0]["severity"] == "should_fix"
    assert bdd_pending_issues[0]["scenarios_pending"] == 2


def test_bdd_results_absent_is_silent_skip(tmp_worktree, task_work_results_dir):
    """No ``bdd_results`` key → gate inactive (back-compat: identical to today)."""
    _write(task_work_results_dir, _make_task_work_results(bdd_block=None))

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="15 passed in 1.45s",
            stderr="",
        )
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _make_task())

    assert result.decision == "approve"
    bdd_issues = [
        i for i in result.issues if i.get("category", "").startswith("bdd_")
    ]
    assert bdd_issues == []


def test_bdd_failure_and_pending_both_surfaced(tmp_worktree, task_work_results_dir):
    """When both present: failure blocks; pending also surfaces in feedback."""
    _write(
        task_work_results_dir,
        _make_task_work_results({
            "scenarios_passed": 0,
            "scenarios_failed": 1,
            "scenarios_pending": 1,
            "failures": [
                {
                    "feature_file": "features/x.feature",
                    "scenario_name": "Real bug",
                    "failing_step": "Then something",
                    "reason": "AssertionError",
                }
            ],
            "pending": [
                {
                    "feature_file": "features/x.feature",
                    "scenario_name": "Future scenario",
                    "pending_step": "When something future",
                }
            ],
            "feature_files": ["features/x.feature"],
            "tag": "@task:TASK-001",
        }),
    )

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="ok", stderr="")
        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _make_task())

    assert result.decision == "feedback"
    categories = {i.get("category") for i in result.issues}
    assert "bdd_failure" in categories
    assert "bdd_pending" in categories
