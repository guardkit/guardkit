"""TASK-AB-NPDET01 — CoachValidator wiring for non-Python deterministic Phase-4.

Covers the integration of the declarative stack registry into CoachValidator:
- ``_detect_test_command`` consults the registry ONLY after the Python-first
  cascade misses, AND only in a single-task wave (the parallel-wave guard);
- ``run_independent_tests`` classifies absence stack-awarely (missing toolchain /
  zero-test => signal_absent) on BOTH the success and failure branch;
- the Python pytest absent classifier (TASK-AB-PERTASKFG01) is UNCHANGED when no
  stack profile is active (the regression pin).

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
# 1. Detection: registry consulted only after Python misses, single-task wave
# ============================================================================


class TestDetectionTaskIdPath:
    def test_dotnet_single_task_wave_returns_command_and_sets_profile(self, tmp_path):
        (tmp_path / "App.csproj").write_text("<Project/>")
        v = _detect_validator(tmp_path, wave_size=1)
        cmd = v._detect_test_command(_TASK_ID, task_work_results=None)
        assert cmd == "dotnet test"
        assert v._active_stack_profile is not None
        assert v._active_stack_profile.stack == "dotnet"

    def test_node_single_task_wave(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        v = _detect_validator(tmp_path, wave_size=1)
        assert v._detect_test_command(_TASK_ID, task_work_results=None) == "npm test"
        assert v._active_stack_profile.stack == "node"

    def test_go_single_task_wave(self, tmp_path):
        (tmp_path / "go.mod").write_text("module x")
        v = _detect_validator(tmp_path, wave_size=1)
        assert v._detect_test_command(_TASK_ID, task_work_results=None) == "go test ./..."
        assert v._active_stack_profile.stack == "go"

    def test_parallel_wave_defers_to_specialist(self, tmp_path):
        """wave_size>1: a whole-suite command would run sibling tasks' tests, so
        the registry is NOT consulted -> None (LLM specialist fallback) and the
        profile stays None. This guard is the load-bearing false-red defense."""
        (tmp_path / "go.mod").write_text("module x")
        v = _detect_validator(tmp_path, wave_size=2)
        assert v._detect_test_command(_TASK_ID, task_work_results=None) is None
        assert v._active_stack_profile is None

    def test_python_task_specific_tests_take_precedence(self, tmp_path):
        """A worktree with BOTH a go.mod and a Python task-specific test: the
        Python-first cascade wins -> pytest command, registry NEVER consulted
        (profile stays None)."""
        (tmp_path / "go.mod").write_text("module x")
        tests_dir = tmp_path / "tests"
        tests_dir.mkdir()
        # Matches the glob tests/**/test_{task_prefix}*.py
        (tests_dir / "test_task_foo_001_x.py").write_text("def test_x():\n    pass\n")
        v = _detect_validator(tmp_path, wave_size=1)
        cmd = v._detect_test_command(_TASK_ID, task_work_results=None)
        assert cmd is not None and cmd.startswith("pytest")
        assert v._active_stack_profile is None

    def test_unknown_stack_returns_none(self, tmp_path):
        """No marker, no Python tests -> None (today's specialist fallback)."""
        v = _detect_validator(tmp_path, wave_size=1)
        assert v._detect_test_command(_TASK_ID, task_work_results=None) is None
        assert v._active_stack_profile is None

    def test_profile_reset_between_calls(self, tmp_path):
        """A reused validator must not carry a stale profile: a second call on a
        worktree with no markers clears the profile set by the first."""
        (tmp_path / "App.csproj").write_text("<Project/>")
        v = _detect_validator(tmp_path, wave_size=1)
        v._detect_test_command(_TASK_ID, task_work_results=None)
        assert v._active_stack_profile is not None
        (tmp_path / "App.csproj").unlink()
        v._detect_test_command(_TASK_ID, task_work_results=None)
        assert v._active_stack_profile is None


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
# 3. REGRESSION PIN — Python pytest absent classifier UNCHANGED (no profile)
# ============================================================================


class TestPytestClassifierRegression:
    """When no non-Python stack profile is active, the pytest classifier
    (TASK-AB-PERTASKFG01 fix #4) must behave exactly as before. These mirror
    test_coach_signal_absent_classifier.py and pin must-fix #2: the registry was
    added as a post-Python fallback, NOT a refactor of the pytest path."""

    def _pytest_validator(self, tmp_path):
        v = CoachValidator(
            worktree_path=str(tmp_path), task_id=_TASK_ID, test_command="pytest tests/ -v"
        )
        v._coach_test_execution = "subprocess"
        assert v._active_stack_profile is None  # no stack profile on the pytest path
        return v

    def test_conftest_import_error_still_absent(self, tmp_path):
        v = self._pytest_validator(tmp_path)
        out = "ImportError while loading conftest '/wt/tests/conftest.py'.\n"
        with patch("subprocess.run", return_value=_proc(4, stdout=out)):
            r = v.run_independent_tests()
        assert r.signal_absent is True

    def test_no_tests_collected_exit5_still_absent(self, tmp_path):
        v = self._pytest_validator(tmp_path)
        with patch("subprocess.run", return_value=_proc(5, stdout="no tests ran")):
            r = v.run_independent_tests()
        assert r.signal_absent is True

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
