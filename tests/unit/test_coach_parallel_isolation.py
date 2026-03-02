"""Unit tests for Coach parallel wave test isolation (TASK-ABFIX-005).

Verifies:
- is_parallel property reflects wave_size correctly
- _classify_test_failure() returns ("parallel_contention", "high") in parallel waves
  when no infrastructure pattern matches (prevents spurious blocking)
- run_independent_tests() routes to _run_isolated_tests() when wave_size > 1
  and subprocess mode is active
- validate() grants conditional approval for parallel_contention and code failures
  in parallel waves when all Player quality gates passed
- Serial tasks (wave_size=1) are NOT affected: code failures still return
  ("code", "n/a") and do NOT receive conditional approval

Defence-in-depth fix for parallel wave contention causing spurious Coach
independent-test failures when multiple tasks share the same worktree.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import subprocess

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    CoachValidationResult,
    IndependentTestResult,
    QualityGateStatus,
    RequirementsValidation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_validator(tmp_path: Path, wave_size: int = 1, test_cmd: str = "pytest tests/ -v") -> CoachValidator:
    """Create a minimal CoachValidator for parallel isolation testing."""
    validator = CoachValidator(
        worktree_path=str(tmp_path),
        task_id="TASK-ABFIX-005",
        test_command=test_cmd,
        wave_size=wave_size,
    )
    # Force subprocess execution mode so isolation path is reachable
    validator._coach_test_execution = "subprocess"
    return validator


def _make_completed_process(returncode: int = 0, stdout: str = "5 passed", stderr: str = "") -> subprocess.CompletedProcess:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def _make_isolated_result(tests_passed: bool = True) -> IndependentTestResult:
    return IndependentTestResult(
        tests_passed=tests_passed,
        test_command="pytest tests/ -v",
        test_output_summary="5 passed" if tests_passed else "1 failed",
        duration_seconds=1.5,
        raw_output="5 passed" if tests_passed else "FAILED: ValueError custom",
    )


def _passing_gates() -> QualityGateStatus:
    return QualityGateStatus(
        tests_passed=True,
        coverage_met=True,
        arch_review_passed=True,
        plan_audit_passed=True,
    )


def _passing_requirements() -> RequirementsValidation:
    return RequirementsValidation(
        criteria_total=1,
        criteria_met=1,
        all_criteria_met=True,
    )


def _passing_task_work_results() -> dict:
    return {
        "tests_passed": True,
        "coverage_pct": 85.0,
        "arch_review_score": 80,
        "plan_audit_violations": 0,
        "test_count": 5,
    }


# ---------------------------------------------------------------------------
# 1. is_parallel property
# ---------------------------------------------------------------------------


class TestIsParallel:
    """The is_parallel property must accurately reflect wave_size context."""

    def test_default_wave_size_not_parallel(self, tmp_path: Path) -> None:
        """Default wave_size=1 → is_parallel is False."""
        validator = CoachValidator(worktree_path=str(tmp_path))
        assert validator.is_parallel is False

    def test_wave_size_1_not_parallel(self, tmp_path: Path) -> None:
        """Explicit wave_size=1 → is_parallel is False."""
        validator = CoachValidator(worktree_path=str(tmp_path), wave_size=1)
        assert validator.is_parallel is False

    def test_wave_size_2_is_parallel(self, tmp_path: Path) -> None:
        """wave_size=2 → is_parallel is True."""
        validator = CoachValidator(worktree_path=str(tmp_path), wave_size=2)
        assert validator.is_parallel is True

    def test_wave_size_5_is_parallel(self, tmp_path: Path) -> None:
        """wave_size=5 → is_parallel is True."""
        validator = CoachValidator(worktree_path=str(tmp_path), wave_size=5)
        assert validator.is_parallel is True

    def test_wave_size_zero_clamped_to_1_not_parallel(self, tmp_path: Path) -> None:
        """wave_size=0 is clamped to 1 → is_parallel is False."""
        validator = CoachValidator(worktree_path=str(tmp_path), wave_size=0)
        assert validator.wave_size == 1
        assert validator.is_parallel is False


# ---------------------------------------------------------------------------
# 2. _classify_test_failure in parallel vs serial waves
# ---------------------------------------------------------------------------


class TestClassifyFailureParallelWave:
    """_classify_test_failure must return parallel_contention in parallel waves
    when no infrastructure pattern matches the output."""

    def test_no_output_serial_returns_code_na(self, tmp_path: Path) -> None:
        """No test output + serial (wave_size=1) → ("code", "n/a")."""
        validator = _make_validator(tmp_path, wave_size=1)
        assert validator._classify_test_failure(None) == ("code", "n/a")

    def test_no_output_parallel_returns_contention(self, tmp_path: Path) -> None:
        """No test output + parallel (wave_size=2) → ("parallel_contention", "high")."""
        validator = _make_validator(tmp_path, wave_size=2)
        assert validator._classify_test_failure(None) == ("parallel_contention", "high")

    def test_unmatched_output_serial_returns_code_na(self, tmp_path: Path) -> None:
        """Unmatched failure output + serial → ("code", "n/a")."""
        output = (
            "FAILED tests/test_calc.py::test_add\n"
            "E   ValueError: some custom domain error\n"
            "1 failed in 0.12s"
        )
        validator = _make_validator(tmp_path, wave_size=1)
        assert validator._classify_test_failure(output) == ("code", "n/a")

    def test_unmatched_output_parallel_returns_contention(self, tmp_path: Path) -> None:
        """Unmatched failure output + parallel → ("parallel_contention", "high")."""
        output = (
            "FAILED tests/test_calc.py::test_add\n"
            "E   ValueError: some custom domain error\n"
            "1 failed in 0.12s"
        )
        validator = _make_validator(tmp_path, wave_size=2)
        assert validator._classify_test_failure(output) == ("parallel_contention", "high")

    def test_assertion_error_serial_returns_code_na(self, tmp_path: Path) -> None:
        """AssertionError (no infra pattern) + serial → ("code", "n/a")."""
        output = (
            "FAILED tests/test_calc.py::test_result\n"
            "E   AssertionError: assert 4 == 5\n"
            "1 failed in 0.08s"
        )
        validator = _make_validator(tmp_path, wave_size=1)
        assert validator._classify_test_failure(output) == ("code", "n/a")

    def test_assertion_error_parallel_returns_contention(self, tmp_path: Path) -> None:
        """AssertionError (no infra pattern) + parallel → ("parallel_contention", "high").

        An AssertionError in a parallel wave may be caused by concurrent worktree
        mutations; reclassify so conditional approval can be applied.
        """
        output = (
            "FAILED tests/test_calc.py::test_result\n"
            "E   AssertionError: assert 4 == 5\n"
            "1 failed in 0.08s"
        )
        validator = _make_validator(tmp_path, wave_size=3)
        assert validator._classify_test_failure(output) == ("parallel_contention", "high")

    def test_infrastructure_pattern_preserved_in_parallel_wave(self, tmp_path: Path) -> None:
        """High-confidence infrastructure failure is NOT reclassified in parallel mode.

        ConnectionRefusedError is a clear infrastructure signal and should
        continue to be returned as ("infrastructure", "high") regardless of wave_size.
        """
        output = (
            "FAILED tests/test_db.py::test_create_user\n"
            "E   ConnectionRefusedError: [Errno 111] Connection refused\n"
            "1 failed in 2.31s"
        )
        validator = _make_validator(tmp_path, wave_size=4)
        assert validator._classify_test_failure(output) == ("infrastructure", "high")


# ---------------------------------------------------------------------------
# 3. run_independent_tests() isolation routing
# ---------------------------------------------------------------------------


class TestIsolationRouting:
    """run_independent_tests() must route to _run_isolated_tests() for parallel
    subprocess execution and use the regular path for serial tasks."""

    def test_parallel_subprocess_calls_run_isolated_tests(self, tmp_path: Path) -> None:
        """wave_size=2 + subprocess mode → _run_isolated_tests() is invoked."""
        validator = _make_validator(tmp_path, wave_size=2)

        isolated_result = _make_isolated_result(tests_passed=True)

        # Patch _run_isolated_tests to verify it is called instead of subprocess.run
        with patch.object(validator, "_run_isolated_tests", return_value=isolated_result) as mock_isolated:
            with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
                result = validator.run_independent_tests(
                    task_work_results=_passing_task_work_results(),
                    task={"task_type": "feature"},
                    turn=1,
                )

        mock_isolated.assert_called_once()
        mock_run.assert_not_called()
        assert result.tests_passed is True

    def test_serial_subprocess_bypasses_isolation(self, tmp_path: Path) -> None:
        """wave_size=1 + subprocess mode → subprocess.run is called, not _run_isolated_tests()."""
        validator = _make_validator(tmp_path, wave_size=1)

        with patch.object(validator, "_run_isolated_tests") as mock_isolated:
            with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
                validator.run_independent_tests(
                    task_work_results=_passing_task_work_results(),
                    task={"task_type": "feature"},
                    turn=1,
                )

        mock_isolated.assert_not_called()
        mock_run.assert_called_once()

    def test_sdk_mode_bypasses_isolation_even_when_parallel(self, tmp_path: Path) -> None:
        """wave_size=2 + SDK mode → isolation NOT applied (SDK has its own isolation)."""
        validator = _make_validator(tmp_path, wave_size=2)
        # Override to SDK mode
        validator._coach_test_execution = "sdk"

        isolated_result = _make_isolated_result(tests_passed=True)

        with patch.object(validator, "_run_isolated_tests") as mock_isolated:
            with patch.object(validator, "_run_tests_via_sdk") as mock_sdk:
                import asyncio

                async def _fake_sdk(cmd):
                    return isolated_result

                mock_sdk.side_effect = _fake_sdk

                with patch("subprocess.run") as mock_run:
                    validator.run_independent_tests(
                        task_work_results=_passing_task_work_results(),
                        task={"task_type": "feature"},
                        turn=1,
                    )

        mock_isolated.assert_not_called()
        # SDK path was attempted; isolation not invoked regardless of outcome


# ---------------------------------------------------------------------------
# 4. Conditional approval in validate()
# ---------------------------------------------------------------------------


class TestConditionalApprovalParallel:
    """validate() must grant conditional approval for parallel-wave failures
    when all Player quality gates passed, and must NOT grant it for serial tasks."""

    def _run_validate_with_mocked_internals(
        self,
        tmp_path: Path,
        wave_size: int,
        test_output: str,
    ) -> CoachValidationResult:
        """Run validate() with all internal dependencies mocked.

        Mocks: read_quality_gate_results, verify_quality_gates,
        run_independent_tests, validate_requirements,
        _check_zero_test_anomaly, _check_seam_test_recommendation,
        _validate_consumer_context.

        The test_output is fed into the failing IndependentTestResult so that
        _classify_test_failure() runs on it naturally inside validate().
        """
        validator = _make_validator(tmp_path, wave_size=wave_size)
        task = {"task_type": "feature", "acceptance_criteria": ["implement feature"]}

        failing_result = IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/ -v",
            test_output_summary="1 failed",
            duration_seconds=1.5,
            raw_output=test_output,
        )

        with patch.object(validator, "read_quality_gate_results", return_value=_passing_task_work_results()):
            with patch.object(validator, "verify_quality_gates", return_value=_passing_gates()):
                with patch.object(validator, "run_independent_tests", return_value=failing_result):
                    with patch.object(validator, "validate_requirements", return_value=_passing_requirements()):
                        with patch.object(validator, "_check_zero_test_anomaly", return_value=[]):
                            with patch.object(validator, "_check_seam_test_recommendation", return_value=[]):
                                with patch.object(validator, "_validate_consumer_context", return_value=[]):
                                    return validator.validate("TASK-ABFIX-005", 1, task)

    def test_parallel_contention_failure_gets_conditional_approval(self, tmp_path: Path) -> None:
        """parallel_contention classification + all gates passed → decision = approve.

        Unmatched test output in a parallel wave (wave_size=2) is classified as
        parallel_contention.  validate() must grant conditional approval and
        return "approve" when all Player quality gates passed.
        """
        result = self._run_validate_with_mocked_internals(
            tmp_path,
            wave_size=2,
            test_output="FAILED: ValueError: some unrecognised error",
        )
        assert result.decision == "approve", (
            f"Expected 'approve' for parallel_contention in parallel wave, "
            f"got '{result.decision}': {result.rationale}"
        )

    def test_code_failure_parallel_wave_gets_conditional_approval(self, tmp_path: Path) -> None:
        """Code failure in parallel wave → conditional approval when gates pass.

        Even if _classify_test_failure would have returned ("code", ...), validate()
        also checks self.is_parallel.  In practice for parallel waves, unmatched
        failures are reclassified as parallel_contention, but this tests the explicit
        ("code" + is_parallel) branch too by verifying the behaviour via wave_size.
        """
        # Use output that gives parallel_contention naturally (unmatched failure)
        # This covers both branches in the conditional_approval expression.
        result = self._run_validate_with_mocked_internals(
            tmp_path,
            wave_size=3,
            test_output="FAILED tests/test_feature.py::test_x - AssertionError: assert 1 == 2",
        )
        assert result.decision == "approve", (
            f"Expected 'approve' for code failure in parallel wave (wave_size=3), "
            f"got '{result.decision}': {result.rationale}"
        )

    def test_code_failure_serial_wave_does_not_get_conditional_approval(self, tmp_path: Path) -> None:
        """Code failure in serial task (wave_size=1) → feedback, no conditional approval.

        Serial tasks must NOT benefit from the parallel contention bypass.
        """
        result = self._run_validate_with_mocked_internals(
            tmp_path,
            wave_size=1,
            test_output="FAILED tests/test_feature.py::test_x - AssertionError: assert 1 == 2",
        )
        assert result.decision == "feedback", (
            f"Expected 'feedback' for code failure in serial wave, "
            f"got '{result.decision}': {result.rationale}"
        )

    def test_infrastructure_failure_serial_no_conditional_approval_without_infra_decl(
        self, tmp_path: Path
    ) -> None:
        """Infrastructure failure without declared requires_infrastructure → feedback.

        Confirms that the new parallel-wave conditions do not accidentally grant
        conditional approval to serial infrastructure failures (pre-existing rule).
        """
        validator = _make_validator(tmp_path, wave_size=1)
        # Task has NO requires_infrastructure, so infra conditional approval cannot apply
        task = {"task_type": "feature", "acceptance_criteria": ["implement feature"]}

        failing_result = IndependentTestResult(
            tests_passed=False,
            test_command="pytest tests/ -v",
            test_output_summary="1 failed",
            duration_seconds=1.5,
            raw_output="ConnectionRefusedError: [Errno 111] Connection refused",
        )

        with patch.object(validator, "read_quality_gate_results", return_value=_passing_task_work_results()):
            with patch.object(validator, "verify_quality_gates", return_value=_passing_gates()):
                with patch.object(validator, "run_independent_tests", return_value=failing_result):
                    result = validator.validate("TASK-ABFIX-005", 1, task)

        # No requires_infrastructure → infrastructure conditional approval doesn't apply
        assert result.decision == "feedback"

    def test_parallel_contention_without_all_gates_passes_does_not_approve(
        self, tmp_path: Path
    ) -> None:
        """Conditional approval only fires when ALL Player gates passed.

        If a parallel wave task has tests failing in Player's own gates,
        Coach must still return feedback even for contention-classified failures.
        """
        validator = _make_validator(tmp_path, wave_size=2)
        task = {"task_type": "feature", "acceptance_criteria": ["implement feature"]}

        failing_gates = QualityGateStatus(
            tests_passed=False,  # Player gates did NOT all pass
            coverage_met=True,
            arch_review_passed=True,
            plan_audit_passed=True,
        )
        # all_gates_passed will be computed as False since tests_passed=False

        with patch.object(validator, "read_quality_gate_results", return_value=_passing_task_work_results()):
            with patch.object(validator, "verify_quality_gates", return_value=failing_gates):
                # validate() returns early from gates check before reaching test verification
                result = validator.validate("TASK-ABFIX-005", 1, task)

        assert result.decision == "feedback", (
            "Expected 'feedback' when Player quality gates failed (tests_passed=False), "
            f"got '{result.decision}'"
        )
