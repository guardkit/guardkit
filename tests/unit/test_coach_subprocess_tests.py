"""Unit tests for Coach subprocess test execution path.

Verifies that run_independent_tests() uses sys.executable for Python/pytest
commands and shell=True for non-Python commands (npm test, dotnet test).

Defence-in-depth fix for TASK-BOOT-43DE: eliminates PATH ambiguity when
the shell resolves `python3` to a different interpreter than the orchestrator.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call
import subprocess

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator


def _make_validator(tmp_path: Path, test_cmd: str = None) -> CoachValidator:
    """Create a minimal CoachValidator for subprocess path testing."""
    validator = CoachValidator(
        worktree_path=tmp_path,
        task_id="TASK-BOOT-43DE",
        test_command=test_cmd,
    )
    # Force subprocess execution mode (not SDK)
    validator._coach_test_execution = "subprocess"
    return validator


def _make_completed_process(returncode: int = 0, stdout: str = "5 passed", stderr: str = "") -> subprocess.CompletedProcess:
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


class TestPytestUsesSystemExecutable:
    """Pytest commands must use sys.executable to avoid PATH ambiguity."""

    def test_pytest_command_uses_sys_executable(self, tmp_path):
        """Plain 'pytest tests/' uses sys.executable -m pytest."""
        validator = _make_validator(tmp_path, test_cmd="pytest tests/ -v --tb=short")

        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            result = validator.run_independent_tests()

        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert isinstance(cmd, list), "pytest command must be passed as a list"
        assert cmd[0] == sys.executable, "First element must be sys.executable"
        assert cmd[1] == "-m"
        assert cmd[2] == "pytest"

    def test_pytest_preserves_extra_args(self, tmp_path):
        """Pytest flags after 'pytest' are preserved in the command."""
        validator = _make_validator(tmp_path, test_cmd="pytest tests/unit/test_foo.py -v --tb=short")

        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            validator.run_independent_tests()

        args, _ = mock_run.call_args
        cmd = args[0]
        assert "tests/unit/test_foo.py" in cmd
        assert "-v" in cmd
        assert "--tb=short" in cmd

    def test_pytest_command_no_shell(self, tmp_path):
        """Pytest commands must NOT use shell=True (avoids shell PATH lookup)."""
        validator = _make_validator(tmp_path, test_cmd="pytest tests/ -v")

        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            validator.run_independent_tests()

        _, kwargs = mock_run.call_args
        assert kwargs.get("shell", False) is False, "pytest must not use shell=True"

    def test_pytest_command_inherits_env(self, tmp_path):
        """Pytest subprocess must receive os.environ to inherit orchestrator environment."""
        import os
        validator = _make_validator(tmp_path, test_cmd="pytest tests/ -v")

        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            validator.run_independent_tests()

        _, kwargs = mock_run.call_args
        assert kwargs.get("env") is os.environ, "subprocess must inherit os.environ"

    def test_pytest_command_passes(self, tmp_path):
        """Passing pytest execution yields tests_passed=True."""
        validator = _make_validator(tmp_path, test_cmd="pytest tests/ -v")

        with patch("subprocess.run", return_value=_make_completed_process(returncode=0, stdout="3 passed")):
            result = validator.run_independent_tests()

        assert result.tests_passed is True

    def test_pytest_command_fails(self, tmp_path):
        """Failing pytest execution yields tests_passed=False."""
        validator = _make_validator(tmp_path, test_cmd="pytest tests/ -v")

        with patch("subprocess.run", return_value=_make_completed_process(returncode=1, stdout="1 failed")):
            result = validator.run_independent_tests()

        assert result.tests_passed is False

    def test_pytest_only_prefix_triggers_sys_executable(self, tmp_path):
        """Command must start with 'pytest' to trigger sys.executable path."""
        # e.g. "pytest" with just file args
        validator = _make_validator(tmp_path, test_cmd="pytest test_specific.py")

        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            validator.run_independent_tests()

        args, _ = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == sys.executable


class TestNonPythonCommandsUseShell:
    """Non-Python test commands must continue to use shell=True."""

    def test_npm_test_uses_shell(self, tmp_path):
        """npm test uses shell=True (not sys.executable)."""
        validator = _make_validator(tmp_path, test_cmd="npm test")

        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            validator.run_independent_tests()

        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert isinstance(cmd, str), "npm test must be passed as string"
        assert cmd == "npm test"
        assert kwargs.get("shell") is True

    def test_dotnet_test_uses_shell(self, tmp_path):
        """dotnet test uses shell=True (not sys.executable)."""
        validator = _make_validator(tmp_path, test_cmd="dotnet test")

        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            validator.run_independent_tests()

        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert isinstance(cmd, str), "dotnet test must be passed as string"
        assert cmd == "dotnet test"
        assert kwargs.get("shell") is True

    def test_npm_test_passes(self, tmp_path):
        """Passing npm test execution yields tests_passed=True."""
        validator = _make_validator(tmp_path, test_cmd="npm test")

        with patch("subprocess.run", return_value=_make_completed_process(returncode=0)):
            result = validator.run_independent_tests()

        assert result.tests_passed is True

    def test_dotnet_test_fails(self, tmp_path):
        """Failing dotnet test yields tests_passed=False."""
        validator = _make_validator(tmp_path, test_cmd="dotnet test")

        with patch("subprocess.run", return_value=_make_completed_process(returncode=1)):
            result = validator.run_independent_tests()

        assert result.tests_passed is False


class TestSubprocessCwdPinnedToWorktree:
    """The independent-test subprocess must run with cwd pinned to the worktree.

    Regression guard for TASK-FIX-COACHCWD01: pytest's ``--cov-report``
    artifacts (``coverage.json``, ``coverage.xml``, ``.coverage``) are written
    relative to the subprocess cwd. If cwd leaks to the host repo, those files
    pollute the host root (FEAT-9DDE run 3). The cwd pin keeps every relative
    artifact inside the worktree, which is later cleaned up — satisfying the
    ``evidence-boundary-narrower-than-write-surface`` family (every arm of the
    evidence loop scoped to the declared evidence root). A future edit that
    drops the ``cwd=`` kwarg silently re-opens the leak; this test fails loud
    instead.
    """

    def test_pytest_subprocess_cwd_is_worktree(self, tmp_path):
        """pytest commands run with cwd == the worktree root, not the host."""
        validator = _make_validator(
            tmp_path, test_cmd="pytest tests/test_foo.py -v --tb=short"
        )

        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            validator.run_independent_tests()

        _, kwargs = mock_run.call_args
        assert kwargs.get("cwd") == str(tmp_path), (
            "pytest subprocess cwd must be pinned to the worktree so "
            "coverage artifacts land inside it, never the host repo"
        )

    def test_shell_subprocess_cwd_is_worktree(self, tmp_path):
        """Non-Python (shell) commands also run with cwd == the worktree root."""
        validator = _make_validator(tmp_path, test_cmd="npm test")

        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            validator.run_independent_tests()

        _, kwargs = mock_run.call_args
        assert kwargs.get("cwd") == str(tmp_path), (
            "shell test-command subprocess cwd must be pinned to the worktree"
        )

    def test_worktree_relative_test_paths_preserved(self, tmp_path):
        """Worktree-relative test paths survive the cwd pin (discovery resolves).

        AC-2: the run-3 invocation used worktree-relative ``tests/...`` paths,
        so pinning cwd to the worktree keeps discovery working — the paths are
        passed through unchanged and resolve against the pinned cwd.
        """
        validator = _make_validator(
            tmp_path,
            test_cmd="pytest tests/test_a.py tests/unit/test_b.py -v --tb=short",
        )

        with patch("subprocess.run", return_value=_make_completed_process()) as mock_run:
            validator.run_independent_tests()

        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "tests/test_a.py" in cmd
        assert "tests/unit/test_b.py" in cmd
        assert kwargs.get("cwd") == str(tmp_path)
