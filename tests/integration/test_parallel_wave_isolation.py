"""
Integration Tests for Parallel Wave Coach Test Isolation (TASK-ABFIX-005)

Exercises the integration seam: FeatureOrchestrator → AutoBuild(wave_size) →
CoachValidator(wave_size) → is_parallel → _classify_test_failure / conditional_approval.

Scenarios:
    1. Coach tests isolated from concurrent worktree mutations via tempdir copy
    2. parallel_contention classification for code failures in parallel waves
    3. Conditional approval for code failures in parallel waves when all gates passed
    4. Serial tasks (wave_size=1) unaffected by parallel wave mechanisms

Coverage Target: >=80%
Test Count: 6 tests

Run with:
    pytest tests/integration/test_parallel_wave_isolation.py -v
"""

import subprocess
from pathlib import Path
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch, call

import pytest

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    TurnRecord,
)
from guardkit.orchestrator.agent_invoker import (
    AgentInvocationResult,
    DEFAULT_SDK_TIMEOUT,
)
from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    CoachValidationResult,
    IndependentTestResult,
    QualityGateStatus,
    RequirementsValidation,
)
from guardkit.worktrees import Worktree


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree(tmp_path):
    """Create a mock Worktree."""
    wt = Mock(spec=Worktree)
    wt.task_id = "TASK-PAR-001"
    wt.path = tmp_path / "worktree"
    wt.path.mkdir(parents=True, exist_ok=True)
    wt.branch_name = "autobuild/TASK-PAR-001"
    wt.base_branch = "main"
    return wt


@pytest.fixture
def mock_progress_display():
    """Mock ProgressDisplay as context manager."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.console = Mock()
    display.console.print = Mock()
    return display


@pytest.fixture
def mock_worktree_manager(mock_worktree):
    """Mock WorktreeManager."""
    mgr = Mock()
    mgr.create.return_value = mock_worktree
    mgr.preserve_on_failure.return_value = None
    mgr.worktrees_dir = mock_worktree.path.parent
    return mgr


def _make_validator(tmp_path: Path, wave_size: int = 1) -> CoachValidator:
    """Create a CoachValidator with specified wave_size."""
    validator = CoachValidator(
        worktree_path=str(tmp_path),
        task_id="TASK-PAR-001",
        test_command="pytest tests/ -v",
        wave_size=wave_size,
    )
    # Force subprocess execution so isolation path is reachable
    validator._coach_test_execution = "subprocess"
    return validator


def _passing_gates() -> QualityGateStatus:
    """Create a QualityGateStatus with all gates passed."""
    return QualityGateStatus(
        tests_passed=True,
        coverage_met=True,
        arch_review_passed=True,
        plan_audit_passed=True,
    )


def _failing_gates() -> QualityGateStatus:
    """Create a QualityGateStatus with tests failed."""
    return QualityGateStatus(
        tests_passed=False,
        coverage_met=True,
        arch_review_passed=True,
        plan_audit_passed=True,
    )


def _passing_requirements() -> RequirementsValidation:
    """Create passing requirements validation."""
    return RequirementsValidation(
        criteria_total=1,
        criteria_met=1,
        all_criteria_met=True,
        missing=[],
    )


def _make_completed_process(
    returncode: int = 0,
    stdout: str = "5 passed",
    stderr: str = "",
) -> subprocess.CompletedProcess:
    """Create a mock CompletedProcess result."""
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


# ============================================================================
# Tests: Parallel vs Serial Classification
# ============================================================================


@pytest.mark.integration
class TestParallelClassificationIntegration:
    """Test that wave_size flows through and affects failure classification."""

    def test_parallel_wave_classifies_unmatched_failure_as_contention(self, tmp_path):
        """
        Verify that in a parallel wave (wave_size > 1), unmatched test
        failures are classified as ('parallel_contention', 'high')
        instead of ('code', 'n/a').
        """
        validator = _make_validator(tmp_path, wave_size=3)
        assert validator.is_parallel is True

        # Classify a generic test failure (no infrastructure pattern match)
        failure_class, confidence = validator._classify_test_failure(
            "FAILED: tests/test_feature.py::test_something - ValueError: custom error"
        )

        assert failure_class == "parallel_contention"
        assert confidence == "high"

    def test_serial_task_classifies_unmatched_failure_as_code(self, tmp_path):
        """
        Verify that in serial execution (wave_size=1), the same unmatched
        test failure is classified as ('code', 'n/a').
        """
        validator = _make_validator(tmp_path, wave_size=1)
        assert validator.is_parallel is False

        failure_class, confidence = validator._classify_test_failure(
            "FAILED: tests/test_feature.py::test_something - ValueError: custom error"
        )

        assert failure_class == "code"
        assert confidence == "n/a"

    def test_infrastructure_failure_not_reclassified_in_parallel(self, tmp_path):
        """
        Verify that infrastructure failures (e.g., connection errors)
        retain their classification regardless of wave_size.
        """
        validator = _make_validator(tmp_path, wave_size=3)

        # Infrastructure-pattern failure (connection error)
        failure_class, confidence = validator._classify_test_failure(
            "FAILED: tests/test_api.py - ConnectionRefusedError: "
            "[Errno 111] Connection refused"
        )

        # Should remain infrastructure, NOT reclassified as parallel_contention
        assert failure_class == "infrastructure"
        assert confidence == "high"


# ============================================================================
# Tests: Isolation Routing
# ============================================================================


@pytest.mark.integration
class TestIsolationRoutingIntegration:
    """Test that parallel waves route to isolated test execution."""

    def test_parallel_wave_routes_to_isolated_tests(self, tmp_path):
        """
        Verify that when wave_size > 1 and subprocess mode is active,
        run_independent_tests routes to _run_isolated_tests().
        """
        validator = _make_validator(tmp_path, wave_size=3)

        with patch.object(
            validator, "_run_isolated_tests",
            return_value=IndependentTestResult(
                tests_passed=True,
                test_command="pytest tests/ -v",
                test_output_summary="5 passed",
                duration_seconds=1.5,
                raw_output="5 passed",
            ),
        ) as mock_isolated:
            result = validator.run_independent_tests()

        # _run_isolated_tests should have been called (not direct subprocess)
        mock_isolated.assert_called_once()
        assert result.tests_passed is True

    def test_serial_task_runs_tests_directly(self, tmp_path):
        """
        Verify that serial tasks (wave_size=1) do NOT use _run_isolated_tests.
        """
        validator = _make_validator(tmp_path, wave_size=1)

        with patch.object(
            validator, "_run_isolated_tests",
        ) as mock_isolated, patch(
            "subprocess.run",
            return_value=_make_completed_process(returncode=0, stdout="5 passed"),
        ):
            result = validator.run_independent_tests()

        # _run_isolated_tests should NOT have been called for serial tasks
        mock_isolated.assert_not_called()


# ============================================================================
# Tests: Conditional Approval in Parallel Waves
# ============================================================================


@pytest.mark.integration
class TestConditionalApprovalIntegration:
    """Test conditional approval for parallel wave failures."""

    def test_parallel_contention_approved_when_all_gates_passed(self, tmp_path):
        """
        End-to-end: parallel_contention classification + all gates passed
        → conditional approval → validate() returns "approve" decision.
        """
        validator = _make_validator(tmp_path, wave_size=3)

        # Mock the internal methods to set up the scenario
        with patch.object(
            validator, "read_quality_gate_results",
            return_value={
                "tests_passed": True,
                "test_pass_rate": 100,
                "coverage": {"line": 85.0, "branch": 80.0},
                "arch_review": {"score": 80},
                "plan_audit": {"violations": 0},
            },
        ), patch.object(
            validator, "verify_quality_gates",
            return_value=_passing_gates(),
        ), patch.object(
            validator, "run_independent_tests",
            return_value=IndependentTestResult(
                tests_passed=False,
                test_command="pytest tests/ -v",
                test_output_summary="1 failed",
                duration_seconds=2.0,
                raw_output="FAILED: tests/test_feature.py - ValueError: custom error",
            ),
        ), patch.object(
            validator, "validate_requirements",
            return_value=_passing_requirements(),
        ):
            result = validator.validate(
                task_id="TASK-PAR-001",
                turn=1,
                task={
                    "task_type": "feature",
                    "acceptance_criteria": ["Feature works"],
                },
            )

        # Should conditionally approve despite test failure
        assert result.decision == "approve"

    def test_code_failure_in_serial_does_not_get_conditional_approval(self, tmp_path):
        """
        Verify that code failures in serial execution (wave_size=1) do NOT
        receive conditional approval — they should return 'feedback'.
        """
        validator = _make_validator(tmp_path, wave_size=1)

        with patch.object(
            validator, "read_quality_gate_results",
            return_value={
                "tests_passed": True,
                "test_pass_rate": 100,
                "coverage": {"line": 85.0, "branch": 80.0},
                "arch_review": {"score": 80},
                "plan_audit": {"violations": 0},
            },
        ), patch.object(
            validator, "verify_quality_gates",
            return_value=_passing_gates(),
        ), patch.object(
            validator, "run_independent_tests",
            return_value=IndependentTestResult(
                tests_passed=False,
                test_command="pytest tests/ -v",
                test_output_summary="1 failed",
                duration_seconds=2.0,
                raw_output="FAILED: tests/test_feature.py - ValueError: custom error",
            ),
        ), patch.object(
            validator, "validate_requirements",
            return_value=_passing_requirements(),
        ):
            result = validator.validate(
                task_id="TASK-PAR-001",
                turn=1,
                task={
                    "task_type": "feature",
                    "acceptance_criteria": ["Feature works"],
                },
            )

        # Serial code failures should NOT be conditionally approved
        assert result.decision == "feedback"


# ============================================================================
# Run Tests
# ============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "integration"])
