"""Unit tests for Coach parallel wave test isolation (TASK-ABFIX-005).

Verifies:
- is_parallel property reflects wave_size correctly
- _classify_test_failure() returns ("parallel_contention", "high") in parallel waves
  when no infrastructure pattern matches (prevents spurious blocking)
- run_independent_tests() routes to _run_isolated_tests() when wave_size > 1
  and subprocess mode is active
- Serial tasks (wave_size=1) are NOT affected: code failures still return
  ("code", "n/a")

Defence-in-depth fix for parallel wave contention causing spurious Coach
independent-test failures when multiple tasks share the same worktree.
"""

import sys
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import subprocess

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import (
    CoachValidator,
    IndependentTestResult,
)


def test_effective_concurrency_is_end_appended_on_positional_apis() -> None:
    from guardkit.orchestrator.autobuild import AutoBuildOrchestrator
    from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

    changed_callables = (
        AutoBuildOrchestrator.__init__,
        AutoBuildOrchestrator._invoke_coach_safely,
        AutoBuildOrchestrator._invoke_coach_primary,
        FeatureOrchestrator._execute_task_owned,
        CoachValidator.__init__,
    )
    for changed_callable in changed_callables:
        assert list(inspect.signature(changed_callable).parameters)[-1] == (
            "effective_concurrency"
        )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_validator(
    tmp_path: Path,
    wave_size: int = 1,
    test_cmd: str = "pytest tests/ -v",
    effective_concurrency: int | None = None,
) -> CoachValidator:
    """Create a minimal CoachValidator for parallel isolation testing."""
    validator = CoachValidator(
        worktree_path=str(tmp_path),
        task_id="TASK-ABFIX-005",
        test_command=test_cmd,
        wave_size=wave_size,
        effective_concurrency=effective_concurrency,
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
        validator = _make_validator(
            tmp_path, wave_size=2, effective_concurrency=2
        )
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

    def test_nominal_parallel_effective_one_uses_real_checkout(
        self, tmp_path: Path
    ) -> None:
        validator = _make_validator(
            tmp_path, wave_size=2, effective_concurrency=1
        )

        with patch.object(validator, "_run_isolated_tests") as mock_isolated:
            with patch(
                "subprocess.run", return_value=_make_completed_process()
            ) as mock_run:
                validator.run_independent_tests(
                    task_work_results=_passing_task_work_results(),
                    task={"task_type": "feature"},
                    turn=1,
                )

        mock_isolated.assert_not_called()
        mock_run.assert_called_once()
        assert validator.is_parallel is True
        assert validator.test_isolation_concurrency == 1

    def test_explicit_none_keeps_nominal_parallel_isolation(
        self, tmp_path: Path
    ) -> None:
        validator = _make_validator(
            tmp_path, wave_size=2, effective_concurrency=None
        )
        isolated_result = _make_isolated_result(tests_passed=True)

        with patch.object(
            validator, "_run_isolated_tests", return_value=isolated_result
        ) as mock_isolated:
            validator.run_independent_tests(
                task_work_results=_passing_task_work_results(),
                task={"task_type": "feature"},
                turn=1,
            )

        mock_isolated.assert_called_once()
        assert validator.test_isolation_concurrency == 2

    def test_serialized_declared_git_command_runs_in_real_checkout(
        self, tmp_path: Path
    ) -> None:
        subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
        validator = _make_validator(
            tmp_path,
            wave_size=2,
            effective_concurrency=1,
            test_cmd="git rev-parse --is-inside-work-tree",
        )

        result = validator.run_independent_tests(
            task_work_results=_passing_task_work_results(),
            task={"task_type": "feature"},
            turn=1,
        )

        assert result.tests_passed is True
        assert "true" in result.raw_output.lower()

    def test_genuine_parallel_failure_is_not_retried_in_worktree(
        self, tmp_path: Path
    ) -> None:
        validator = _make_validator(
            tmp_path, wave_size=2, effective_concurrency=2
        )
        isolated_result = _make_isolated_result(tests_passed=False)

        with patch.object(
            validator, "_run_isolated_tests", return_value=isolated_result
        ), patch("subprocess.run") as mock_run:
            result = validator.run_independent_tests(
                task_work_results=_passing_task_work_results(),
                task={"task_type": "feature"},
                turn=1,
            )

        assert result is isolated_result
        mock_run.assert_not_called()

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

    def test_sdk_mode_bypasses_isolation_even_when_parallel(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """wave_size=2 + SDK mode → isolation NOT applied (SDK has its own isolation)."""
        # TASK-HMIG-011: run_independent_tests gates the SDK path on
        # `not _is_langgraph_harness()` (TASK-FIX-COACHTESTTO forces subprocess
        # under langgraph). Post-cutover the default harness is langgraph, so
        # the SDK path is only taken when GUARDKIT_HARNESS=sdk is in scope.
        # Pin it so this test exercises the sdk-bypasses-isolation branch.
        monkeypatch.setenv("GUARDKIT_HARNESS", "sdk")
        validator = _make_validator(
            tmp_path, wave_size=2, effective_concurrency=2
        )
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
                    result = validator.run_independent_tests(
                        task_work_results=_passing_task_work_results(),
                        task={"task_type": "feature"},
                        turn=1,
                    )

        assert result is isolated_result
        mock_sdk.assert_called_once()
        mock_isolated.assert_not_called()
        mock_run.assert_not_called()


# ---------------------------------------------------------------------------
# 4. Conditional approval in validate()
# ---------------------------------------------------------------------------


