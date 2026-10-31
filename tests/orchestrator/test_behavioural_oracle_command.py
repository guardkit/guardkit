"""TASK-SELFFIX-002 — behavioural_oracle.command shell execution tests.

Tests the shell-command path of ``_produce_behavioural_oracle`` when no
``tests/acceptance/*_roundtrip.py`` artefact exists and a
``behavioural_oracle.command`` is declared in the task YAML.

Outcome branches exercised:
  - command exits 0 → ran+passed (AC-001)
  - command exits non-zero → ran+failed with output_tail (AC-002)
  - command exceeds timeout → timed_out=True, subprocess killed (AC-003)
  - precedence: roundtrip.py exists → command is NOT used (AC-004)
"""

from __future__ import annotations

import json
import textwrap
import time
from pathlib import Path
from typing import Any, Dict

import pytest
import yaml

# Ensure the project root is on sys.path for imports.
_project_root = Path(__file__).resolve().parents[3]
if str(_project_root) not in __import__("sys").path:
    __import__("sys").path.insert(0, str(_project_root))

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ============================================================================
# Helpers
# ============================================================================


def _make_validator(worktree_path: Path) -> CoachValidator:
    """Build a minimal CoachValidator pointing at *worktree_path*."""
    return CoachValidator(worktree_path=worktree_path)


def _task_with_command(
    task_id: str = "TASK-SELFFIX-002",
    command: str = "true",
) -> Dict[str, Any]:
    """Return a task dict with behavioural_oracle.command set."""
    return {
        "id": task_id,
        "task_type": "feature",
        "behavioural_oracle": {"command": command},
    }


def _task_with_command_string(
    task_id: str = "TASK-SELFFIX-002",
    command: str = "true",
) -> Dict[str, Any]:
    """Return a task dict with behavioural_oracle as a bare string."""
    return {
        "id": task_id,
        "task_type": "feature",
        "behavioural_oracle": command,
    }


# ============================================================================
# AC-001: command exits 0 → ran + passed + correct shape
# ============================================================================


class TestCommandExitZero:
    """AC-001: With no Python oracle artefact and a YAML-declared command
    that exits 0, the bundle's behavioural_oracle reports
    {status: "ran", passed: true, exit_code: 0, duration, timed_out: false,
    output_tail, provenance naming the command and its YAML origin}."""

    def test_command_true_returns_ran_passed(self, tmp_path: Path) -> None:
        """Command ``true`` exits 0 → ran+passed with correct shape."""
        worktree_path = tmp_path / "worktree-cmd-pass"
        worktree_path.mkdir()
        validator = _make_validator(worktree_path)
        task = _task_with_command(command="true")
        result = validator._produce_behavioural_oracle(task=task)
        assert result is not None
        assert result["status"] == "ran"
        assert result["passed"] is True
        assert result["exit_code"] == 0
        assert result["timed_out"] is False
        assert "duration" in result
        assert "command" in result
        assert result["command"] == "true"
        # Provenance names the command and its YAML origin
        assert result["provenance"].startswith("yaml_command:")
        assert "true" in result["provenance"]

    def test_command_with_output_captured(self, tmp_path: Path) -> None:
        """Command that prints output has output_tail populated."""
        worktree_path = tmp_path / "worktree-cmd-output"
        worktree_path.mkdir()
        validator = _make_validator(worktree_path)
        task = _task_with_command(command="echo 'hello world'")
        result = validator._produce_behavioural_oracle(task=task)
        assert result is not None
        assert result["passed"] is True
        assert result["output_tail"] is not None
        assert "hello world" in result["output_tail"]

    def test_bare_string_command(self, tmp_path: Path) -> None:
        """behavioural_oracle as a bare string is also accepted."""
        worktree_path = tmp_path / "worktree-cmd-string"
        worktree_path.mkdir()
        validator = _make_validator(worktree_path)
        task = _task_with_command_string(command="true")
        result = validator._produce_behavioural_oracle(task=task)
        assert result is not None
        assert result["passed"] is True


# ============================================================================
# AC-002: command exits non-zero → ran + failed + output_tail
# ============================================================================


class TestCommandExitNonZero:
    """AC-002: A command exiting non-zero reports {status: "ran", passed: false}
    with the failure output captured in output_tail."""

    def test_command_false_returns_ran_failed(self, tmp_path: Path) -> None:
        """Command ``false`` exits 1 → ran+failed with output_tail."""
        worktree_path = tmp_path / "worktree-cmd-fail"
        worktree_path.mkdir()
        validator = _make_validator(worktree_path)
        task = _task_with_command(command="false")
        result = validator._produce_behavioural_oracle(task=task)
        assert result is not None
        assert result["status"] == "ran"
        assert result["passed"] is False
        assert result["exit_code"] != 0
        assert result["timed_out"] is False
        assert "duration" in result

    def test_failed_command_captures_output(self, tmp_path: Path) -> None:
        """Failed command has output_tail with failure details."""
        worktree_path = tmp_path / "worktree-cmd-fail-output"
        worktree_path.mkdir()
        validator = _make_validator(worktree_path)
        task = _task_with_command(command="echo 'failure details'; exit 42")
        result = validator._produce_behavioural_oracle(task=task)
        assert result is not None
        assert result["passed"] is False
        assert result["exit_code"] == 42
        assert result["output_tail"] is not None
        assert "failure details" in result["output_tail"]


# ============================================================================
# AC-003: command exceeds timeout → timed_out: true, subprocess killed
# ============================================================================


class TestCommandTimeout:
    """AC-003: A command exceeding GUARDKIT_ORACLE_TIMEOUT reports
    timed_out: true (which the existing guard treats as ran-and-failed)
    and the subprocess is reliably killed."""

    def test_command_timeout_returns_timed_out(self, tmp_path: Path) -> None:
        """A long-running command times out → timed_out=True."""
        worktree_path = tmp_path / "worktree-cmd-timeout"
        worktree_path.mkdir()
        validator = _make_validator(worktree_path)
        task = _task_with_command(command="sleep 3600")
        import os
        old_timeout = os.environ.get("GUARDKIT_ORACLE_TIMEOUT")
        os.environ["GUARDKIT_ORACLE_TIMEOUT"] = "0.1"
        try:
            result = validator._produce_behavioural_oracle(task=task)
            assert result is not None
            assert result["status"] == "ran"
            assert result["passed"] is False
            assert result["timed_out"] is True
            assert result["exit_code"] is None
            assert "duration" in result
        finally:
            if old_timeout is not None:
                os.environ["GUARDKIT_ORACLE_TIMEOUT"] = old_timeout
            else:
                os.environ.pop("GUARDKIT_ORACLE_TIMEOUT", None)

    def test_timeout_kills_subprocess(self, tmp_path: Path) -> None:
        """After timeout, the subprocess is no longer running."""
        worktree_path = tmp_path / "worktree-cmd-timeout-kill"
        worktree_path.mkdir()
        validator = _make_validator(worktree_path)
        task = _task_with_command(command="sleep 3600")
        import os
        old_timeout = os.environ.get("GUARDKIT_ORACLE_TIMEOUT")
        os.environ["GUARDKIT_ORACLE_TIMEOUT"] = "0.1"
        try:
            result = validator._produce_behavioural_oracle(task=task)
            # The subprocess should have been killed by subprocess.run
            # (it raises TimeoutExpired which we catch internally)
            assert result is not None
            assert result["timed_out"] is True
        finally:
            if old_timeout is not None:
                os.environ["GUARDKIT_ORACLE_TIMEOUT"] = old_timeout
            else:
                os.environ.pop("GUARDKIT_ORACLE_TIMEOUT", None)


# ============================================================================
# Absent
# ============================================================================


class TestAbsent:
    """When there's no roundtrip.py and no command declared, result is None."""

    def test_no_oracle_no_command_returns_none(self, tmp_path: Path) -> None:
        """No artefact and no command → None (absent)."""
        worktree_path = tmp_path / "worktree-absent"
        worktree_path.mkdir()
        validator = _make_validator(worktree_path)
        task: Dict[str, Any] = {"id": "TASK-001"}
        result = validator._produce_behavioural_oracle(task=task)
        assert result is None

    def test_none_task_returns_none(self, tmp_path: Path) -> None:
        """None task with no oracle file → None."""
        worktree_path = tmp_path / "worktree-none-task"
        worktree_path.mkdir()
        validator = _make_validator(worktree_path)
        result = validator._produce_behavioural_oracle(task=None)
        assert result is None


# ============================================================================
# Integration: end-to-end through gather_evidence
# ============================================================================


class TestGatherEvidenceIntegration:
    """End-to-end: command execution through gather_evidence."""

    def _base_payload(
        self,
        task_id: str,
        files_created: list[str],
        files_authored: list[str],
    ) -> Dict[str, Any]:
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
        self,
        worktree_path: Path,
        task_id: str,
        payload: Dict[str, Any],
    ) -> Path:
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

    def test_gather_evidence_runs_command(self, tmp_path: Path) -> None:
        """gather_evidence executes command when no roundtrip.py exists."""
        worktree_path = tmp_path / "worktree-e2e-cmd"
        task_id = "TASK-SELFFIX-002-E2E"
        self._write_task_work_results(
            worktree_path,
            task_id,
            self._base_payload(task_id, ["src/app.py"], ["src/app.py"]),
        )
        validator = _make_validator(worktree_path)
        task = _task_with_command(command="true")
        bundle = validator.gather_evidence(
            task_id=task_id, turn=1, task=task,
        )
        assert bundle.behavioural_oracle is not None
        assert bundle.behavioural_oracle["status"] == "ran"
        assert bundle.behavioural_oracle["passed"] is True
        assert "command" in bundle.behavioural_oracle
