"""
Unit tests for conditional approval diagnostic logging (TASK-BOOT-754A).

Verifies that CoachValidator logs DEBUG-level diagnostic information before
evaluating the 5-condition conditional_approval check, making it easier to
diagnose why conditional approval did or did not fire.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_task_work_results(
    tests_passed: bool = True,
    failed_count: int = 0,
    total_tests: int = 10,
    coverage_met: bool = True,
    line_coverage: int = 85,
    arch_score: int = 82,
    violations: int = 0,
    requirements_met: Optional[list] = None,
) -> Dict[str, Any]:
    if not tests_passed and failed_count == 0:
        failed_count = 1
    passed_count = total_tests - failed_count
    return {
        "quality_gates": {
            "tests_passing": tests_passed and failed_count == 0,
            "tests_passed": passed_count,
            "tests_failed": failed_count,
            "coverage": line_coverage,
            "coverage_met": coverage_met,
            "all_passed": tests_passed and coverage_met,
        },
        "code_review": {
            "score": arch_score,
            "solid": 85,
            "dry": 80,
            "yagni": 82,
        },
        "plan_audit": {
            "violations": violations,
            "file_count_match": True,
        },
        "requirements_met": requirements_met if requirements_met is not None else [
            "The thing works",
        ],
    }


def write_results(results_dir: Path, results: Dict[str, Any]) -> None:
    results_path = results_dir / "task_work_results.json"
    results_path.write_text(json.dumps(results, indent=2))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_worktree(tmp_path: Path) -> Path:
    worktree = tmp_path / "worktrees" / "TASK-BOOT-754A"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def task_work_results_dir(tmp_worktree: Path) -> Path:
    results_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-BOOT-754A"
    results_dir.mkdir(parents=True)
    return results_dir


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestConditionalApprovalLogging:
    """Tests that debug logging is emitted before conditional_approval evaluation."""

    def test_conditional_approval_log_emitted_on_infra_failure(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        Debug log is emitted with all 5 condition values when tests fail
        due to a high-confidence infrastructure error.
        """
        results = make_task_work_results(tests_passed=True, requirements_met=["The thing works"])
        write_results(task_work_results_dir, results)

        task = {
            "acceptance_criteria": ["The thing works"],
            "requires_infrastructure": ["docker"],
            "_docker_available": False,
        }

        # Independent tests fail with a high-confidence infra error
        with caplog.at_level(logging.DEBUG):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stdout="ConnectionRefusedError: [Errno 111]",
                    stderr="",
                )
                validator = CoachValidator(str(tmp_worktree))
                validator.validate("TASK-BOOT-754A", 1, task)

        log_text = caplog.text
        assert "conditional_approval check:" in log_text
        assert "failure_class=infrastructure" in log_text
        assert "confidence=high" in log_text
        assert "requires_infra=" in log_text
        assert "docker_available=" in log_text
        assert "all_gates_passed=" in log_text

    def test_conditional_approval_log_shows_docker_available_false(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        The log records docker_available=False when _docker_available is False in task.
        """
        results = make_task_work_results(tests_passed=True, requirements_met=["The thing works"])
        write_results(task_work_results_dir, results)

        task = {
            "acceptance_criteria": ["The thing works"],
            "requires_infrastructure": ["docker"],
            "_docker_available": False,
        }

        with caplog.at_level(logging.DEBUG):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stdout="ConnectionRefusedError",
                    stderr="",
                )
                validator = CoachValidator(str(tmp_worktree))
                validator.validate("TASK-BOOT-754A", 1, task)

        assert "docker_available=False" in caplog.text

    def test_conditional_approval_log_shows_docker_available_true(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        The log records docker_available=True when _docker_available is True (default).
        """
        results = make_task_work_results(tests_passed=True, requirements_met=["The thing works"])
        write_results(task_work_results_dir, results)

        task = {
            "acceptance_criteria": ["The thing works"],
            "requires_infrastructure": [],
            "_docker_available": True,
        }

        with caplog.at_level(logging.DEBUG):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=1,
                    stdout="ConnectionRefusedError",
                    stderr="",
                )
                validator = CoachValidator(str(tmp_worktree))
                validator.validate("TASK-BOOT-754A", 1, task)

        assert "docker_available=True" in caplog.text

    def test_conditional_approval_log_not_emitted_when_tests_pass(
        self,
        tmp_worktree: Path,
        task_work_results_dir: Path,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """
        The conditional_approval debug log is NOT emitted when independent tests pass,
        because the code path is only reached on test failure.
        """
        results = make_task_work_results(tests_passed=True, requirements_met=["The thing works"])
        write_results(task_work_results_dir, results)

        task = {
            "acceptance_criteria": ["The thing works"],
            "requires_infrastructure": ["docker"],
            "_docker_available": False,
        }

        # Independent tests pass
        with caplog.at_level(logging.DEBUG):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(
                    returncode=0,
                    stdout="10 passed",
                    stderr="",
                )
                validator = CoachValidator(str(tmp_worktree))
                validator.validate("TASK-BOOT-754A", 1, task)

        assert "conditional_approval check:" not in caplog.text
