"""Declared test commands of any language: the exit code is the verdict.

TASK-AB-NPDET01 once added a per-framework "a test ran" rule for .NET, Node
and Go (stack rows matched by marker files). It was removed on 1 November
2026 with the stack rows: no framework knowledge stays in central code, and
"no test signal" is left only where nothing ran at all. Marker-guessed
commands were removed on 31 October: commands come only from the declaration.

Pure subprocess-mocked.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator

_TASK_ID = "TASK-FOO-001"


@pytest.fixture(autouse=True)
def _programs_are_found(monkeypatch):
    """The run itself is mocked, so the lookup of the command's program is
    too (dotnet and go need not be installed where the suite runs)."""
    monkeypatch.setattr(
        "guardkit.orchestrator.quality_gates.coach_validator.missing_program",
        lambda *_args: None,
    )


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
    return v


# ============================================================================
# 2. Every declared command: the exit code is the verdict
# ============================================================================


class TestTheExitCodeIsTheVerdict:
    """31 October 2026: the per-framework "a test ran" rule for Node, Go and
    .NET is gone. Output that rule used to read as "no test signal" (a
    missing npm script, a Go module with no tests, .NET's "No test is
    available", a Vitest run with nothing to run) is now judged by the
    command's exit code alone, like every other declared command. A project
    that wants "no tests ran" to fail says so in its own command."""

    @pytest.mark.parametrize(
        "command,returncode,output,passed",
        [
            ("dotnet test", 0, "No test is available in Foo.dll", True),
            ("dotnet test", 1, "Failed!  - Failed: 2, Passed: 3", False),
            ("go test ./...", 0, "?   example.com/m [no test files]\n", True),
            ("go test ./...", 1, "--- FAIL: TestX\nFAIL\texample.com/m 0.01s\n", False),
            ("npm test", 1, 'npm error Missing script: "test"', False),
            ("npm test", 0, "No test files found, exiting with code 0", True),
            ("npm test", 0, "Tests  3 passed (3)", True),
        ],
    )
    def test_the_exit_code_decides(self, tmp_path, command, returncode, output, passed):
        v = CoachValidator(worktree_path=str(tmp_path), task_id=_TASK_ID, test_command=command)
        with patch("subprocess.run", return_value=_proc(returncode, stdout=output)):
            r = v.run_independent_tests()
        assert r.tests_passed is passed
        assert r.signal_absent is False
        assert r.check_could_not_run is False


# ============================================================================
# 3. No stack profile: the exit code decides
# ============================================================================


class TestPytestClassifierRegression:
    """A non-zero exit is a failure and zero a pass;
    pytest's own exit codes (4, 5) and phrases are not read for any command
    (31 October 2026)."""

    def _pytest_validator(self, tmp_path):
        v = CoachValidator(
            worktree_path=str(tmp_path), task_id=_TASK_ID, test_command="pytest tests/ -v"
        )
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
