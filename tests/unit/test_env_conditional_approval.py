"""
Tests for TASK-ABSR-2468: environment-class conditional approval branch.

Covers the fifth conditional-approval clause in
``CoachValidator.validate`` and the supporting ``_bootstrap_likely_broken``
helper. The clause fires when:

- ``failure_class == "infrastructure"``
- ``failure_confidence == "ambiguous"`` (ImportError / ModuleNotFoundError
  without service-client context)
- All Player gates passed
- The task did not declare ``requires_infrastructure`` (no overlap with
  the existing Docker-unavailable branch)
- ``<worktree>/.guardkit/bootstrap_state.json`` reports ``success: False``

Test layout mirrors the patterns established in
``tests/unit/test_coach_validator.py``.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch

import pytest

_test_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_test_root))

from guardkit.orchestrator.quality_gates import (
    CoachValidator,
    IndependentTestResult,
)


# ---------------------------------------------------------------------------
# Test fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_worktree(tmp_path):
    """Create a temporary worktree directory."""
    worktree = tmp_path / "worktrees" / "TASK-ABSR-2468"
    worktree.mkdir(parents=True)
    return worktree


@pytest.fixture
def task_work_results_dir(tmp_worktree):
    """Create the task-work results directory."""
    results_dir = tmp_worktree / ".guardkit" / "autobuild" / "TASK-001"
    results_dir.mkdir(parents=True)
    return results_dir


def _make_passing_results() -> Dict[str, Any]:
    """Task-work results with all Player gates passing."""
    return {
        "quality_gates": {
            "tests_passing": True,
            "tests_passed": 15,
            "tests_failed": 0,
            "coverage": 85,
            "coverage_met": True,
            "all_passed": True,
        },
        "code_review": {
            "score": 82,
            "solid": 85,
            "dry": 80,
            "yagni": 82,
        },
        "plan_audit": {
            "violations": 0,
            "file_count_match": True,
        },
        "requirements_met": [
            "Endpoint returns 200",
            "Schema validated",
            "Logs include request id",
        ],
    }


def _make_failing_results(failed_count: int = 1) -> Dict[str, Any]:
    """Task-work results with at least one Player gate failing."""
    return {
        "quality_gates": {
            "tests_passing": False,
            "tests_passed": 14,
            "tests_failed": failed_count,
            "coverage": 85,
            "coverage_met": True,
            "all_passed": False,
        },
        "code_review": {"score": 82, "solid": 85, "dry": 80, "yagni": 82},
        "plan_audit": {"violations": 0, "file_count_match": True},
        "requirements_met": [
            "Endpoint returns 200",
            "Schema validated",
            "Logs include request id",
        ],
    }


def _write_results(results_dir: Path, results: Dict[str, Any]) -> Path:
    path = results_dir / "task_work_results.json"
    path.write_text(json.dumps(results, indent=2))
    return path


def _make_task(
    requires_infrastructure: Optional[List[str]] = None,
    docker_available: bool = True,
) -> Dict[str, Any]:
    """Task data matching the format expected by CoachValidator."""
    return {
        "acceptance_criteria": [
            "Endpoint returns 200",
            "Schema validated",
            "Logs include request id",
        ],
        "requires_infrastructure": requires_infrastructure or [],
        "_docker_available": docker_available,
    }


def _write_bootstrap_state(worktree: Path, *, success: bool) -> Path:
    """Write a minimal bootstrap_state.json into the worktree."""
    state_dir = worktree / ".guardkit"
    state_dir.mkdir(parents=True, exist_ok=True)
    state_file = state_dir / "bootstrap_state.json"
    state_file.write_text(
        json.dumps(
            {
                "content_hash": "deadbeef",
                "success": success,
                "timestamp": "2026-04-27T00:00:00",
            },
            indent=2,
        )
    )
    return state_file


def _ambiguous_infra_result(cmd: str = "pytest tests/ -v") -> IndependentTestResult:
    """An IndependentTestResult that mocked classifiers will treat as ambiguous infra."""
    raw = (
        "ModuleNotFoundError: No module named 'opentelemetry'\n"
        "ImportError while loading conftest 'tests/conftest.py'."
    )
    return IndependentTestResult(
        tests_passed=False,
        test_command=cmd,
        test_output_summary=raw,
        duration_seconds=0.42,
        raw_output=raw,
    )


# ---------------------------------------------------------------------------
# _bootstrap_likely_broken helper unit tests
# ---------------------------------------------------------------------------


class TestBootstrapLikelyBroken:
    """Cover the three branches called out in the task acceptance criteria."""

    def test_returns_true_when_state_file_reports_failure(self, tmp_worktree):
        _write_bootstrap_state(tmp_worktree, success=False)
        validator = CoachValidator(str(tmp_worktree))
        assert validator._bootstrap_likely_broken({}) is True

    def test_returns_false_when_state_file_reports_success(self, tmp_worktree):
        _write_bootstrap_state(tmp_worktree, success=True)
        validator = CoachValidator(str(tmp_worktree))
        assert validator._bootstrap_likely_broken({}) is False

    def test_returns_false_when_state_file_missing(self, tmp_worktree):
        validator = CoachValidator(str(tmp_worktree))
        assert validator._bootstrap_likely_broken({}) is False

    def test_returns_false_on_parse_error(self, tmp_worktree):
        state_dir = tmp_worktree / ".guardkit"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "bootstrap_state.json").write_text("{not valid json")
        validator = CoachValidator(str(tmp_worktree))
        assert validator._bootstrap_likely_broken({}) is False

    def test_returns_false_when_payload_not_a_dict(self, tmp_worktree):
        state_dir = tmp_worktree / ".guardkit"
        state_dir.mkdir(parents=True, exist_ok=True)
        (state_dir / "bootstrap_state.json").write_text(
            json.dumps(["not", "a", "dict"])
        )
        validator = CoachValidator(str(tmp_worktree))
        assert validator._bootstrap_likely_broken({}) is False


# ---------------------------------------------------------------------------
# Conditional-approval clause tests (named in TASK-ABSR-2468 acceptance criteria)
# ---------------------------------------------------------------------------


class TestEnvironmentConditionalApproval:
    """Each test name maps 1:1 to an acceptance criterion in the task file."""

    def test_env_conditional_approve_only_when_bootstrap_failed(
        self, tmp_worktree, task_work_results_dir
    ):
        """Bootstrap broken + ambiguous infra failure + gates passed → approve."""
        _write_results(task_work_results_dir, _make_passing_results())
        _write_bootstrap_state(tmp_worktree, success=False)

        validator = CoachValidator(str(tmp_worktree))
        with patch.object(validator, "run_independent_tests") as mock_run:
            mock_run.return_value = _ambiguous_infra_result()
            with patch.object(
                validator,
                "_classify_test_failure",
                return_value=("infrastructure", "ambiguous"),
            ):
                result = validator.validate("TASK-001", 1, _make_task())

        assert result.decision == "approve"
        assert result.environment_conditional_approval is True
        assert result.approved_without_independent_tests is True
        assert "environment" in result.rationale.lower()

    def test_env_conditional_approve_does_not_apply_when_bootstrap_succeeded(
        self, tmp_worktree, task_work_results_dir
    ):
        """Bootstrap healthy → ImportError is a Player code defect, not env."""
        _write_results(task_work_results_dir, _make_passing_results())
        _write_bootstrap_state(tmp_worktree, success=True)

        validator = CoachValidator(str(tmp_worktree))
        with patch.object(validator, "run_independent_tests") as mock_run:
            mock_run.return_value = _ambiguous_infra_result()
            with patch.object(
                validator,
                "_classify_test_failure",
                return_value=("infrastructure", "ambiguous"),
            ):
                result = validator.validate("TASK-001", 1, _make_task())

        assert result.decision == "feedback"
        assert result.environment_conditional_approval is False

    def test_env_conditional_approve_does_not_apply_when_bootstrap_state_missing(
        self, tmp_worktree, task_work_results_dir
    ):
        """No bootstrap_state.json → cannot prove env failure → conservative reject."""
        _write_results(task_work_results_dir, _make_passing_results())
        # Deliberately do NOT write bootstrap_state.json

        validator = CoachValidator(str(tmp_worktree))
        with patch.object(validator, "run_independent_tests") as mock_run:
            mock_run.return_value = _ambiguous_infra_result()
            with patch.object(
                validator,
                "_classify_test_failure",
                return_value=("infrastructure", "ambiguous"),
            ):
                result = validator.validate("TASK-001", 1, _make_task())

        assert result.decision == "feedback"
        assert result.environment_conditional_approval is False

    def test_env_conditional_approve_does_not_apply_when_failure_class_is_code(
        self, tmp_worktree, task_work_results_dir
    ):
        """Non-infrastructure classification → clause never fires."""
        _write_results(task_work_results_dir, _make_passing_results())
        _write_bootstrap_state(tmp_worktree, success=False)

        validator = CoachValidator(str(tmp_worktree))
        # wave_size=1 so the parallel-code conditional doesn't fire either
        assert validator.is_parallel is False

        code_failure = IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/ -v",
            test_output_summary="AssertionError: 1 != 2",
            duration_seconds=0.5,
            raw_output="AssertionError: 1 != 2",
        )

        with patch.object(validator, "run_independent_tests") as mock_run:
            mock_run.return_value = code_failure
            with patch.object(
                validator,
                "_classify_test_failure",
                return_value=("code", "high"),
            ):
                result = validator.validate("TASK-001", 1, _make_task())

        assert result.decision == "feedback"
        assert result.environment_conditional_approval is False

    def test_env_conditional_approve_does_not_apply_when_gates_failed(
        self, tmp_worktree, task_work_results_dir
    ):
        """Player gates failing → clause must not paper over a real defect."""
        _write_results(task_work_results_dir, _make_failing_results(failed_count=2))
        _write_bootstrap_state(tmp_worktree, success=False)

        validator = CoachValidator(str(tmp_worktree))
        result = validator.validate("TASK-001", 1, _make_task())

        # Player gates failed → coach short-circuits before the conditional block.
        assert result.decision == "feedback"
        assert result.environment_conditional_approval is False

    def test_env_conditional_approve_does_not_apply_when_requires_infra_set(
        self, tmp_worktree, task_work_results_dir
    ):
        """When requires_infrastructure is set, the existing Docker branch owns this case."""
        _write_results(task_work_results_dir, _make_passing_results())
        _write_bootstrap_state(tmp_worktree, success=False)

        validator = CoachValidator(str(tmp_worktree))
        task = _make_task(
            requires_infrastructure=["postgres"],
            docker_available=True,  # Docker is up, so existing branch also won't fire
        )

        with patch.object(validator, "run_independent_tests") as mock_run:
            mock_run.return_value = _ambiguous_infra_result()
            with patch.object(
                validator,
                "_classify_test_failure",
                return_value=("infrastructure", "ambiguous"),
            ):
                result = validator.validate("TASK-001", 1, task)

        assert result.decision == "feedback"
        assert result.environment_conditional_approval is False

    def test_env_conditional_approve_marks_result_with_environment_flag(
        self, tmp_worktree, task_work_results_dir
    ):
        """When the clause fires, the result must carry environment_conditional_approval=True
        and the to_dict() payload must surface it for downstream summary code."""
        _write_results(task_work_results_dir, _make_passing_results())
        _write_bootstrap_state(tmp_worktree, success=False)

        validator = CoachValidator(str(tmp_worktree))
        with patch.object(validator, "run_independent_tests") as mock_run:
            mock_run.return_value = _ambiguous_infra_result()
            with patch.object(
                validator,
                "_classify_test_failure",
                return_value=("infrastructure", "ambiguous"),
            ):
                result = validator.validate("TASK-001", 1, _make_task())

        assert result.decision == "approve"
        assert result.environment_conditional_approval is True
        payload = result.to_dict()
        assert payload["environment_conditional_approval"] is True
        # And the existing approved_without_independent_tests flag still rides along
        assert payload["approved_without_independent_tests"] is True


# ---------------------------------------------------------------------------
# FEAT-J004-702C / TASK-J004-004 replay
# ---------------------------------------------------------------------------


class TestFeatJ004ReplayScenario:
    """Replay the scenario that motivated TASK-ABSR-2468.

    The original feedback-stall fired when:
      - The user opted into bootstrap_failure_mode: warn
      - Bootstrap silently failed (missing transitive dep)
      - Player completed the task and all task-work gates passed
      - Coach's independent pytest hit ImportError on the missing dep
      - Result: stalled in feedback loop until max_turns

    With the new branch wired up, the same situation should approve.
    """

    def test_replay_feat_j004_702c_environment_stall(self, tmp_worktree):
        # Replay uses the actual task id from the FEAT-J004-702C scenario,
        # so write task_work_results.json at the path the validator looks up.
        results_dir = (
            tmp_worktree / ".guardkit" / "autobuild" / "TASK-J004-004"
        )
        results_dir.mkdir(parents=True)
        _write_results(results_dir, _make_passing_results())
        _write_bootstrap_state(tmp_worktree, success=False)

        validator = CoachValidator(str(tmp_worktree))
        with patch.object(validator, "run_independent_tests") as mock_run:
            mock_run.return_value = _ambiguous_infra_result()
            with patch.object(
                validator,
                "_classify_test_failure",
                return_value=("infrastructure", "ambiguous"),
            ):
                result = validator.validate("TASK-J004-004", 3, _make_task())

        # The point of the regression test: this used to stall in feedback;
        # now it approves with the environment flag.
        assert result.decision == "approve"
        assert result.environment_conditional_approval is True
        assert result.task_id == "TASK-J004-004"
        assert result.turn == 3
