"""TASK-AB-NPDET01 — CoachValidator wiring for non-Python deterministic Phase-4.

Covers the stack registry's absence classifier in CoachValidator:
- ``run_independent_tests`` classifies absence stack-awarely (missing toolchain /
  zero-test => signal_absent) on BOTH the success and failure branch;
- with no stack profile the exit code decides; no pytest-shaped reading is
  applied to a command's output (31 October 2026). Marker-guessed commands
  were removed the same day: commands come only from the declaration.

Pure subprocess-mocked — no guardkitfactory, no harness env var (these paths
force ``coach_test_execution='subprocess'`` and never dispatch select_harness).
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.quality_gates.stack_test_execution import (
    STACK_TEST_PROFILES,
)

_TASK_ID = "TASK-FOO-001"


def _profile(stack):
    return next(p for p in STACK_TEST_PROFILES if p.stack == stack)


def _proc(returncode, stdout="", stderr=""):
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def _detect_validator(tmp_path: Path, wave_size: int = 1) -> CoachValidator:
    """A validator with NO explicit test_command, so ``_detect_test_command``
    runs and (for a non-Python single-task wave) sets ``_active_stack_profile``."""
    v = CoachValidator(
        worktree_path=str(tmp_path), task_id=_TASK_ID, wave_size=wave_size
    )
    v._coach_test_execution = "subprocess"
    return v


# ============================================================================
# 2. run_independent_tests: stack-aware absent classification end-to-end
# ============================================================================


class TestRunIndependentTestsNonPython:
    def _validator_with_profile(self, tmp_path, stack):
        v = CoachValidator(
            worktree_path=str(tmp_path),
            task_id=_TASK_ID,
            test_command=_profile(stack).whole_suite_command,
        )
        v._coach_test_execution = "subprocess"
        v._active_stack_profile = _profile(stack)
        return v

    def test_dotnet_missing_toolchain_is_absent(self, tmp_path):
        v = self._validator_with_profile(tmp_path, "dotnet")
        with patch("subprocess.run", return_value=_proc(127, stderr="dotnet: not found")):
            r = v.run_independent_tests()
        assert r.signal_absent is True
        assert r.tests_passed is False

    def test_dotnet_zero_tests_exit0_is_absent_not_a_pass(self, tmp_path):
        """The exit-0 zero-test false-green guard: returncode 0 but 'No test is
        available' -> absent (UNKNOWN), tests_passed forced to False."""
        v = self._validator_with_profile(tmp_path, "dotnet")
        with patch("subprocess.run", return_value=_proc(0, stdout="No test is available in Foo.dll")):
            r = v.run_independent_tests()
        assert r.signal_absent is True
        assert r.tests_passed is False

    def test_dotnet_real_failure_is_ran_and_failed(self, tmp_path):
        v = self._validator_with_profile(tmp_path, "dotnet")
        with patch("subprocess.run", return_value=_proc(1, stdout="Failed!  - Failed: 2, Passed: 3")):
            r = v.run_independent_tests()
        assert r.signal_absent is False
        assert r.tests_passed is False

    def test_dotnet_pass(self, tmp_path):
        v = self._validator_with_profile(tmp_path, "dotnet")
        with patch("subprocess.run", return_value=_proc(0, stdout="Passed!  - Failed: 0, Passed: 5")):
            r = v.run_independent_tests()
        assert r.signal_absent is False
        assert r.tests_passed is True

    def test_go_all_testless_exit0_is_absent(self, tmp_path):
        v = self._validator_with_profile(tmp_path, "go")
        out = "?   ex/a\t[no test files]\n?   ex/b\t[no test files]\n"
        with patch("subprocess.run", return_value=_proc(0, stdout=out)):
            r = v.run_independent_tests()
        assert r.signal_absent is True
        assert r.tests_passed is False

    def test_go_mixed_module_pass_is_not_absent(self, tmp_path):
        v = self._validator_with_profile(tmp_path, "go")
        out = "ok  \tex/a\t0.012s\n?   ex/b\t[no test files]\n"
        with patch("subprocess.run", return_value=_proc(0, stdout=out)):
            r = v.run_independent_tests()
        assert r.signal_absent is False
        assert r.tests_passed is True

    def test_node_missing_script_is_absent(self, tmp_path):
        v = self._validator_with_profile(tmp_path, "node")
        with patch("subprocess.run", return_value=_proc(1, stderr='npm error Missing script: "test"')):
            r = v.run_independent_tests()
        assert r.signal_absent is True
        assert r.tests_passed is False

    def test_node_pass_with_no_tests_exit0_is_absent_not_a_pass(self, tmp_path):
        """Review hole #1 end-to-end: ``jest --passWithNoTests`` exits 0 having
        run zero tests -> absent (UNKNOWN), tests_passed forced False, NOT a pass."""
        v = self._validator_with_profile(tmp_path, "node")
        out = "> jest --passWithNoTests\n\nNo tests found, exiting with code 0\n"
        with patch("subprocess.run", return_value=_proc(0, stdout=out)):
            r = v.run_independent_tests()
        assert r.signal_absent is True
        assert r.tests_passed is False

    def test_node_real_pass_is_not_absent(self, tmp_path):
        v = self._validator_with_profile(tmp_path, "node")
        out = "PASS src/foo.test.js\nTests:       3 passed, 3 total\n"
        with patch("subprocess.run", return_value=_proc(0, stdout=out)):
            r = v.run_independent_tests()
        assert r.signal_absent is False
        assert r.tests_passed is True

    def test_node_passing_run_with_incidental_not_found_is_not_absent(self, tmp_path):
        """Review hole #2 end-to-end: a passing run whose output mentions a
        '404: Not Found' must NOT be false-red'd to absent/failed."""
        v = self._validator_with_profile(tmp_path, "node")
        out = "GET /missing -> 404: Not Found\n5 passing\n"
        with patch("subprocess.run", return_value=_proc(0, stdout=out)):
            r = v.run_independent_tests()
        assert r.signal_absent is False
        assert r.tests_passed is True


# ============================================================================
# 3. No stack profile: the exit code decides
# ============================================================================


class TestPytestClassifierRegression:
    """With no stack profile a non-zero exit is a failure and zero a pass;
    pytest's own exit codes (4, 5) and phrases are not read for any command
    (31 October 2026)."""

    def _pytest_validator(self, tmp_path):
        v = CoachValidator(
            worktree_path=str(tmp_path), task_id=_TASK_ID, test_command="pytest tests/ -v"
        )
        v._coach_test_execution = "subprocess"
        assert v._active_stack_profile is None  # no stack profile on the pytest path
        return v

    def test_exit_5_is_a_failure_not_an_absence(self, tmp_path):
        v = self._pytest_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(5, stdout="no tests ran")):
            r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is False

    def test_genuine_pytest_failure_still_not_absent(self, tmp_path):
        v = self._pytest_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(1, stdout="2 failed, 8 passed in 1.2s")):
            r = v.run_independent_tests()
        assert r.tests_passed is False
        assert r.signal_absent is False

    def test_pytest_pass_still_passes(self, tmp_path):
        v = self._pytest_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(0, stdout="10 passed in 0.9s")):
            r = v.run_independent_tests()
        assert r.tests_passed is True
        assert r.signal_absent is False
