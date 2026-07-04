"""TASK-QAV-006 — L4 behavioural-oracle producer tests.

Tests the ``_produce_behavioural_oracle`` method on ``CoachValidator`` and
the end-to-end wiring into ``gather_evidence``.

Outcome branches exercised:
  - no oracle file → ``None`` (absent, AC-5)
  - independent failing oracle → ``{"status": "ran", "passed": False}`` (AC-1)
  - independent passing oracle → ``{"status": "ran", "passed": True}`` (AC-2)
  - Player-authored oracle → ``{"status": "not_independent"}`` (AC-3)
  - timeout → ``{"status": "ran", "passed": False, "timed_out": True}`` (AC-4)
  - failed-to-start → ``None`` (absent, AC-4)
  - end-to-end: guard overrides approve→feedback with failing oracle (AC-1)
"""

from __future__ import annotations

import json
import subprocess
import textwrap
import time
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest
import yaml

# Ensure the project root is on sys.path for imports.
_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_project_root))

from guardkit.orchestrator.quality_gates.coach_evidence import (
    CoachEvidenceBundle,
)
from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.coach_verification import HonestyVerification


# ============================================================================
# Helpers
# ============================================================================


def _make_validator(worktree_path: Path) -> CoachValidator:
    """Build a minimal CoachValidator pointing at *worktree_path*."""
    return CoachValidator(worktree_path=worktree_path)


def _base_payload(
    task_id: str,
    files_created: list[str],
    files_authored: list[str],
) -> Dict[str, Any]:
    """Return a minimal task_work_results payload that passes all quality gates."""
    return {
        "task_id": task_id,
        "turn": 1,
        "files_created": files_created,
        "files_modified": [],
        "files_authored": files_authored,
        "tests_passed": True,
        "tests_run": True,
        "test_results": {"line_coverage": 85.0},
        "quality_gates": {
            "all_passed": True,
            "tests_failed": 0,
            "tests_run": True,
            "coverage_met": True,
            "line_coverage": 85.0,
            "branch_coverage": 70.0,
            "line_threshold": 80.0,
            "branch_threshold": 60.0,
            "arch_review_score": 80,
            "arch_review_threshold": 60,
            "plan_audit_status": "clean",
        },
        "plan_audit": {"status": "clean"},
        "bdd_results": {
            "scenarios_attempted": 2,
            "scenarios_passed": 2,
            "scenarios_failed": 0,
        },
        "completion_promises": [],
        "requirements_met": [],
        "requirements_addressed": [],
        "code_review": {"status": "approved", "score": 80},
        "agent_invocations": [],
        "_synthetic": True,
    }


def _write_task_work_results(
    worktree_path: Path,
    task_id: str,
    payload: Dict[str, Any],
) -> Path:
    """Write a task_work_results.json into the standard autobuild path."""
    results_path = worktree_path / ".guardkit" / "autobuild" / task_id
    results_path.mkdir(parents=True, exist_ok=True)
    results_file = results_path / "task_work_results.json"
    results_file.write_text(json.dumps(payload, indent=2))
    for f in payload.get("files_created", []) + payload.get("files_modified", []):
        full_path = worktree_path / f
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if not full_path.exists():
            full_path.write_text("# placeholder\n")
    for f in payload.get("files_authored", []):
        full_path = worktree_path / f
        full_path.parent.mkdir(parents=True, exist_ok=True)
        if not full_path.exists():
            full_path.write_text("# placeholder\n")
    return results_file


def _make_task(
    task_id: str,
    task_type: str = "feature",
    acceptance_criteria: list[str] | None = None,
) -> Dict[str, Any]:
    return {
        "id": task_id,
        "task_type": task_type,
        "acceptance_criteria": acceptance_criteria or [],
        "requires_infrastructure": False,
    }


def _write_oracle(
    worktree_path: Path,
    name: str = "x",
    body: str = "",
) -> Path:
    """Write an oracle file at tests/acceptance/<name>_roundtrip.py."""
    oracle_dir = worktree_path / "tests" / "acceptance"
    oracle_dir.mkdir(parents=True, exist_ok=True)
    oracle_path = oracle_dir / f"{name}_roundtrip.py"
    if not body:
        body = (
            "def test_roundtrip():\n"
            "    assert True\n"
        )
    oracle_path.write_text(textwrap.dedent(body))
    return oracle_path


def _bundle(
    behavioural_oracle: Optional[Dict[str, Any]] = None,
) -> CoachEvidenceBundle:
    return CoachEvidenceBundle(
        honesty=HonestyVerification(
            verified=True, discrepancies=[], honesty_score=1.0, resolved_paths=[]
        ),
        gathering_status="complete",
        behavioural_oracle=behavioural_oracle,
    )


def _approve_events(task_id: str, turn: int) -> list:
    verdict: Dict[str, Any] = {
        "task_id": task_id,
        "turn": turn,
        "decision": "approve",
        "rationale": "All Player-reported gates pass; tests look green.",
        "criteria_verification": [],
    }
    text = "```json\n" + json.dumps(verdict) + "\n```"
    return [
        type("AssistantMessageEvent", (), {"text": text})(),
        type("ResultMessageEvent", (), {"session_id": None})(),
    ]


# ============================================================================
# AC-5: absence discipline — no oracle file → None
# ============================================================================


class TestAbsenceDiscipline:
    """AC-5: no oracle file → field stays None end-to-end."""

    def test_no_oracle_file_returns_none(self, tmp_path: Path) -> None:
        """When no tests/acceptance/*_roundtrip.py exists, producer returns None."""
        worktree_path = tmp_path / "worktree-absent"
        worktree_path.mkdir()
        validator = _make_validator(worktree_path)
        result = validator._produce_behavioural_oracle(authored_files=[])
        assert result is None

    def test_gather_evidence_keeps_none_when_absent(self, tmp_path: Path) -> None:
        """End-to-end: gather_evidence leaves behavioural_oracle=None when absent."""
        worktree_path = tmp_path / "worktree-absent-e2e"
        task_id = "TASK-QAV-006-ABSENT"
        _write_task_work_results(
            worktree_path,
            task_id,
            _base_payload(task_id, ["src/app.py"], ["src/app.py"]),
        )
        validator = _make_validator(worktree_path)
        task = _make_task(task_id, task_type="feature")
        bundle = validator.gather_evidence(task_id=task_id, turn=1, task=task)
        assert bundle.behavioural_oracle is None

    def test_to_dict_serializes_none(self, tmp_path: Path) -> None:
        """behavioural_oracle=None survives to_dict() unchanged."""
        bundle = _bundle(behavioural_oracle=None)
        d = bundle.to_dict()
        assert "behavioural_oracle" in d
        assert d["behavioural_oracle"] is None


# ============================================================================
# AC-1: producer wired, red→green — failing oracle → guard overrides
# ============================================================================


class TestProducerWired:
    """AC-1: independent failing oracle → ran-and-failed → guard overrides approve→feedback."""

    def test_failing_oracle_returns_ran_failed(self, tmp_path: Path) -> None:
        """An independent oracle that fails returns status=ran, passed=False."""
        worktree_path = tmp_path / "worktree-fail"
        oracle_path = _write_oracle(
            worktree_path,
            "failing",
            body="""
def test_roundtrip():
    assert False, "intentional failure"
""",
        )
        validator = _make_validator(worktree_path)
        result = validator._produce_behavioural_oracle(authored_files=[])
        assert result is not None
        assert result["status"] == "ran"
        assert result["passed"] is False
        assert result["oracle_path"] == str(
            Path("tests/acceptance/failing_roundtrip.py")
        )
        assert result["provenance"] == "independent"
        assert result["timed_out"] is False
        assert result["exit_code"] != 0

    def test_end_to_end_guard_override(self, tmp_path: Path) -> None:
        """Full pipeline: failing oracle → bundle has ran-failed → guard flips approve→feedback."""
        worktree_path = tmp_path / "worktree-e2e-fail"
        task_id = "TASK-QAV-006-E2E"
        _write_task_work_results(
            worktree_path,
            task_id,
            _base_payload(task_id, ["src/app.py", "tests/acceptance/x_roundtrip.py"], ["src/app.py"]),
        )
        # Write a failing oracle
        _write_oracle(
            worktree_path,
            "x",
            body="""
def test_roundtrip():
    assert False, "behavioural failure"
""",
        )
        validator = _make_validator(worktree_path)
        task = _make_task(task_id, task_type="feature")
        bundle = validator.gather_evidence(task_id=task_id, turn=1, task=task)

        assert bundle.behavioural_oracle is not None
        assert bundle.behavioural_oracle["status"] == "ran"
        assert bundle.behavioural_oracle["passed"] is False

    def test_passing_oracle_no_override(self, tmp_path: Path) -> None:
        """An independent passing oracle returns status=ran, passed=True."""
        worktree_path = tmp_path / "worktree-pass"
        _write_oracle(
            worktree_path,
            "passing",
            body="""
def test_roundtrip():
    assert True
""",
        )
        validator = _make_validator(worktree_path)
        result = validator._produce_behavioural_oracle(authored_files=[])
        assert result is not None
        assert result["status"] == "ran"
        assert result["passed"] is True


# ============================================================================
# AC-2: pass path
# ============================================================================


class TestPassPath:
    """AC-2: independent passing oracle populates ran+passed:true."""

    def test_passing_oracle_has_all_fields(self, tmp_path: Path) -> None:
        """Passing oracle includes oracle_path and provenance."""
        worktree_path = tmp_path / "worktree-pass-fields"
        _write_oracle(
            worktree_path,
            "ok",
            body="def test_ok():\n    assert True\n",
        )
        validator = _make_validator(worktree_path)
        result = validator._produce_behavioural_oracle(authored_files=[])
        assert result["status"] == "ran"
        assert result["passed"] is True
        assert "oracle_path" in result
        assert result["provenance"] == "independent"
        assert "duration" in result


# ============================================================================
# AC-3: independence
# ============================================================================


class TestIndependence:
    """AC-3: Player-authored oracle → not_independent + warning."""

    def test_player_authored_oracle_not_independent(self, tmp_path: Path) -> None:
        """When the oracle is in the authored set, status=not_independent."""
        worktree_path = tmp_path / "worktree-authored"
        _write_oracle(
            worktree_path,
            "my",
            body="def test_my():\n    assert True\n",
        )
        validator = _make_validator(worktree_path)
        result = validator._produce_behavioural_oracle(
            authored_files=["tests/acceptance/my_roundtrip.py"]
        )
        assert result is not None
        assert result["status"] == "not_independent"
        assert "oracle_path" in result
        assert result["provenance"] == "player_authored"

    def test_independent_oracle_not_in_authored_set(self, tmp_path: Path) -> None:
        """Oracle NOT in authored set → independent."""
        worktree_path = tmp_path / "worktree-independent"
        _write_oracle(
            worktree_path,
            "indep",
            body="def test_indep():\n    assert True\n",
        )
        validator = _make_validator(worktree_path)
        result = validator._produce_behavioural_oracle(
            authored_files=["src/app.py"]
        )
        assert result is not None
        assert result["status"] == "ran"
        assert result["provenance"] == "independent"


# ============================================================================
# AC-4: timeout asymmetry
# ============================================================================


class TestTimeoutAsymmetry:
    """AC-4: started-then-hung → ran-and-failed; failed-to-start → absent."""

    def test_timeout_returns_ran_failed_with_timed_out(self, tmp_path: Path) -> None:
        """A hanging oracle produces status=ran, passed=False, timed_out=True."""
        worktree_path = tmp_path / "worktree-timeout"
        _write_oracle(
            worktree_path,
            "hung",
            body="""
import time
def test_hung():
    time.sleep(3600)
    assert True
""",
        )
        validator = _make_validator(worktree_path)
        # Use a very short timeout for the test
        with patch.dict("os.environ", {"GUARDKIT_ORACLE_TIMEOUT": "0.1"}):
            result = validator._produce_behavioural_oracle(authored_files=[])
        assert result is not None
        assert result["status"] == "ran"
        assert result["passed"] is False
        assert result["timed_out"] is True

    def test_failed_to_start_returns_none(self, tmp_path: Path) -> None:
        """When the interpreter can't run pytest, producer returns None (absent)."""
        worktree_path = tmp_path / "worktree-failed-start"
        _write_oracle(
            worktree_path,
            "bad",
            body="def test_bad():\n    assert True\n",
        )
        validator = _make_validator(worktree_path)
        # Mock the interpreter to return a non-existent binary
        with patch.object(
            validator, "_pytest_interpreter", return_value="/nonexistent/python"
        ):
            result = validator._produce_behavioural_oracle(authored_files=[])
        # Should return None (absent) because the subprocess fails to start
        assert result is None


# ============================================================================
# AC-6: un-soften the dogfood
# ============================================================================


class TestUnsoftenDogfood:
    """AC-6: rewrite soft-pedaled tests with real oracle fixture."""

    def test_fs01_verdict_is_feedback_with_oracle(self, tmp_path: Path) -> None:
        """test_fs01_verdict_is_feedback_with_oracle: REAL verdict flip with a real failing oracle.

        Asserts bundle.behavioural_oracle is not None and that the guard
        would override approve→feedback.
        """
        worktree_path = tmp_path / "worktree-fs01-real"
        task_id = "TASK-QAV-005-FS01"
        _write_task_work_results(
            worktree_path,
            task_id,
            _base_payload(
                task_id,
                ["src/app.py", "src/wiring.py", "tests/acceptance/x_roundtrip.py"],
                ["src/app.py", "src/wiring.py"],
            ),
        )
        # Write a real failing oracle
        _write_oracle(
            worktree_path,
            "x",
            body="""
def test_roundtrip():
    assert False, "behavioural regression detected"
""",
        )
        validator = _make_validator(worktree_path)
        task = _make_task(task_id, task_type="feature")
        bundle = validator.gather_evidence(task_id=task_id, turn=1, task=task)

        # The key assertions from AC-6
        assert bundle.behavioural_oracle is not None
        assert bundle.behavioural_oracle["status"] == "ran"
        assert bundle.behavioural_oracle["passed"] is False

    def test_fs01_approves_with_l4_disabled(self, tmp_path: Path) -> None:
        """test_fs01_approves_with_l4_disabled: proves the gate is the difference.

        When no oracle file exists, behavioural_oracle stays None and the
        guard no-ops. The same fixture would approve.
        """
        worktree_path = tmp_path / "worktree-fs01-no-l4"
        task_id = "TASK-QAV-005-FS01"
        _write_task_work_results(
            worktree_path,
            task_id,
            _base_payload(
                task_id,
                ["src/app.py", "src/wiring.py"],
                ["src/app.py", "src/wiring.py"],
            ),
        )
        validator = _make_validator(worktree_path)
        task = _make_task(task_id, task_type="feature")
        bundle = validator.gather_evidence(task_id=task_id, turn=1, task=task)

        # Without the oracle file, behavioural_oracle should be None
        assert bundle.behavioural_oracle is None
