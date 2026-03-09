"""
Unit tests for AutoBuild orchestrator-level command execution (TASK-CRV-537E, TASK-RFX-528E).

Tests the runtime verification of command_execution acceptance criteria:
- Worktree path assertion (defensive check)
- Command execution and result injection into synthetic reports
- Timeout protection (per-command and aggregate)
- Skipping when not on synthetic report path
- CommandExecutionResult serialization (TASK-RFX-528E)
- Structured result capture and return values (TASK-RFX-528E)

Coverage Target: >=85%
Test Count: 30+ tests
"""

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    CommandExecutionResult,
    COMMAND_TIMEOUT_SECONDS,
    COMMAND_TOTAL_TIMEOUT_SECONDS,
    WORKTREE_SENTINEL,
    _assert_worktree_path,
    _PIP_CMD_RE,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def mock_worktree_manager():
    """Create mock WorktreeManager."""
    manager = Mock()
    manager.worktrees_dir = Path("/tmp/worktrees")
    return manager


@pytest.fixture
def mock_agent_invoker():
    """Create mock AgentInvoker."""
    return Mock()


@pytest.fixture
def mock_progress_display():
    """Create mock ProgressDisplay."""
    display = Mock()
    display.__enter__ = Mock(return_value=display)
    display.__exit__ = Mock(return_value=False)
    display.start_turn = Mock()
    display.complete_turn = Mock()
    display.render_summary = Mock()
    return display


@pytest.fixture
def orchestrator(mock_worktree_manager, mock_agent_invoker, mock_progress_display):
    """Create AutoBuildOrchestrator instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        repo_root = Path(tmpdir)
        yield AutoBuildOrchestrator(
            repo_root=repo_root,
            worktree_manager=mock_worktree_manager,
            agent_invoker=mock_agent_invoker,
            progress_display=mock_progress_display,
            verbose=False,
            max_turns=5,
            sdk_timeout=900,
            ablation_mode=False,
        )


@pytest.fixture
def worktree_path(tmp_path):
    """Create a temporary path that looks like a worktree."""
    wt = tmp_path / ".guardkit" / "worktrees" / "TASK-TEST-001"
    wt.mkdir(parents=True)
    return wt


# ============================================================================
# 1. _assert_worktree_path() Tests (5 tests)
# ============================================================================


class TestAssertWorktreePath:
    """Tests for the worktree path assertion guard."""

    def test_accepts_valid_worktree_path(self, worktree_path):
        """Valid worktree path should not raise."""
        _assert_worktree_path(worktree_path)

    def test_rejects_base_repo_path(self, tmp_path):
        """Path without worktree sentinel should raise RuntimeError."""
        with pytest.raises(RuntimeError, match="Refusing to execute commands outside worktree"):
            _assert_worktree_path(tmp_path)

    def test_rejects_root_path(self):
        """Root path should be rejected."""
        with pytest.raises(RuntimeError, match="Refusing to execute commands outside worktree"):
            _assert_worktree_path(Path("/"))

    def test_rejects_home_directory(self):
        """Home directory should be rejected."""
        with pytest.raises(RuntimeError, match=WORKTREE_SENTINEL):
            _assert_worktree_path(Path.home())

    def test_error_message_includes_path(self, tmp_path):
        """Error message should include the offending path."""
        with pytest.raises(RuntimeError, match=str(tmp_path.resolve())):
            _assert_worktree_path(tmp_path)


# ============================================================================
# 2. _execute_command_criteria() Tests (8 tests)
# ============================================================================


class TestExecuteCommandCriteria:
    """Tests for command execution and result injection."""

    def test_successful_command_injected_into_requirements_addressed(
        self, orchestrator, worktree_path
    ):
        """Successful command result should be injected into requirements_addressed."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pip install guardkit-py` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Successfully installed guardkit-py",
                stderr="",
            )
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        assert len(report["requirements_addressed"]) == 1
        assert "`pip install guardkit-py` runs successfully" in report["requirements_addressed"]

    def test_failed_command_not_injected(self, orchestrator, worktree_path):
        """Failed command should not be injected into requirements_addressed."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pip install nonexistent-pkg` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1,
                stdout="",
                stderr="ERROR: No matching distribution",
            )
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        assert len(report["requirements_addressed"]) == 0

    def test_timeout_does_not_inject(self, orchestrator, worktree_path):
        """Timed-out command should not be injected."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`sleep 999` runs successfully"]

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 60)):
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        assert len(report["requirements_addressed"]) == 0

    def test_command_runs_in_worktree_cwd(self, orchestrator, worktree_path):
        """Command should execute with cwd set to the worktree path."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`python -c 'import guardkit'` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args
        assert call_kwargs.kwargs["cwd"] == str(worktree_path)
        assert call_kwargs.kwargs["shell"] is True
        assert call_kwargs.kwargs["timeout"] == COMMAND_TIMEOUT_SECONDS

    def test_non_command_criteria_skipped(self, orchestrator, worktree_path):
        """Non-command criteria should not trigger subprocess.run."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["File `src/main.py` exists in the project"]

        with patch("subprocess.run") as mock_run:
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        mock_run.assert_not_called()

    def test_aggregate_timeout_stops_remaining_commands(
        self, orchestrator, worktree_path
    ):
        """When aggregate timeout is exceeded, remaining commands should be skipped."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = [
            "`pip install pkg1` runs successfully",
            "`pip install pkg2` runs successfully",
        ]

        call_count = 0

        def slow_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise subprocess.TimeoutExpired("pip install", COMMAND_TIMEOUT_SECONDS)

        with patch("subprocess.run", side_effect=slow_run):
            with patch(
                "guardkit.orchestrator.autobuild.COMMAND_TOTAL_TIMEOUT_SECONDS", 60
            ):
                orchestrator._execute_command_criteria(
                    synthetic_report=report,
                    acceptance_criteria=criteria,
                    worktree_path=worktree_path,
                )

        # First command times out (60s added), second should be skipped
        # since elapsed_total (60) >= COMMAND_TOTAL_TIMEOUT_SECONDS (60)
        assert call_count == 1

    def test_creates_requirements_addressed_key_if_missing(
        self, orchestrator, worktree_path
    ):
        """Should create requirements_addressed key if not present in report."""
        report = {"_synthetic": True}  # No requirements_addressed key
        criteria = ["`pip install guardkit-py` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        assert "requirements_addressed" in report
        assert len(report["requirements_addressed"]) == 1

    def test_no_command_criteria_is_noop(self, orchestrator, worktree_path):
        """When no command criteria exist, method should return without action."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["Module `guardkit.utils` contains error handling"]

        with patch("subprocess.run") as mock_run:
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        mock_run.assert_not_called()
        assert len(report["requirements_addressed"]) == 0


# ============================================================================
# 3. Pip Normalization Tests (6 tests) — TASK-RFX-BAD9
# ============================================================================


class TestPipNormalization:
    """Tests for bare pip → sys.executable -m pip normalization."""

    def test_pip_install_normalized(self, orchestrator, worktree_path):
        """Bare `pip install X` should become `sys.executable -m pip install X`."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pip install guardkit-py` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        call_args = mock_run.call_args
        executed_cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args")
        # Should use sys.executable -m pip instead of bare pip
        assert executed_cmd.startswith(sys.executable)
        assert "-m pip install guardkit-py" in executed_cmd

    def test_pip_freeze_normalized(self, orchestrator, worktree_path):
        """Bare `pip freeze` should be normalized."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pip freeze` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        call_args = mock_run.call_args
        executed_cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args")
        assert f"{sys.executable} -m pip freeze" == executed_cmd

    def test_pip_with_flags_normalized(self, orchestrator, worktree_path):
        """Bare `pip install --upgrade X` should be normalized."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pip install --upgrade requests` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        call_args = mock_run.call_args
        executed_cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args")
        assert "-m pip install --upgrade requests" in executed_cmd

    def test_python_m_pip_not_double_normalized(self, orchestrator, worktree_path):
        """Commands already using `python -m pip` should NOT be normalized."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`python -m pip install X` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        call_args = mock_run.call_args
        executed_cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args")
        # Should NOT be double-normalized — the original command stays as-is
        assert executed_cmd == "python -m pip install X"

    def test_non_pip_command_not_normalized(self, orchestrator, worktree_path):
        """Non-pip commands should not be affected by normalization."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pytest tests/ -v` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        call_args = mock_run.call_args
        executed_cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args")
        assert executed_cmd == "pytest tests/ -v"

    def test_pip_re_pattern_matches_correctly(self):
        """_PIP_CMD_RE should match bare pip commands but not pip3 or pipenv."""
        assert _PIP_CMD_RE.match("pip install X")
        assert _PIP_CMD_RE.match("pip freeze")
        assert _PIP_CMD_RE.match("pip")  # bare pip with no subcommand
        assert not _PIP_CMD_RE.match("pip3 install X")
        assert not _PIP_CMD_RE.match("pipenv install X")
        assert not _PIP_CMD_RE.match("python -m pip install X")


# ============================================================================
# 4. Virtualenv PATH Injection Tests (4 tests) — TASK-RFX-BAD9
# ============================================================================


class TestVenvPathInjection:
    """Tests for virtualenv PATH prepending when .venv/bin/ exists."""

    def test_venv_bin_prepended_when_exists(self, orchestrator, worktree_path):
        """When .venv/bin/ exists in worktree, PATH should be prepended."""
        venv_bin = worktree_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)

        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pytest tests/ -v` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["env"] is not None
        assert call_kwargs["env"]["PATH"].startswith(str(venv_bin))

    def test_no_venv_no_env_override(self, orchestrator, worktree_path):
        """When no .venv/bin/ exists, env should be None (inherit parent)."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pytest tests/ -v` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["env"] is None

    def test_venv_path_uses_os_pathsep(self, orchestrator, worktree_path):
        """PATH separator should use os.pathsep for platform compatibility."""
        venv_bin = worktree_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)

        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`echo hello` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        env_path = mock_run.call_args.kwargs["env"]["PATH"]
        # Should contain pathsep after venv_bin
        assert str(venv_bin) + os.pathsep in env_path

    def test_venv_and_pip_normalization_together(self, orchestrator, worktree_path):
        """Both pip normalization AND venv PATH should apply simultaneously."""
        venv_bin = worktree_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)

        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pip install guardkit-py` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        call_args = mock_run.call_args
        executed_cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args")
        call_kwargs = call_args.kwargs

        # Pip should be normalized
        assert sys.executable in executed_cmd
        assert "-m pip install guardkit-py" in executed_cmd

        # Venv PATH should be prepended
        assert call_kwargs["env"] is not None
        assert call_kwargs["env"]["PATH"].startswith(str(venv_bin))


# ============================================================================
# 5. CommandExecutionResult Serialization Tests (6 tests) — TASK-RFX-528E
# ============================================================================


class TestCommandExecutionResultSerialization:
    """Tests for CommandExecutionResult dataclass and to_dict() serialization."""

    def test_successful_result_to_dict(self):
        """Successful result should serialize all fields correctly."""
        result = CommandExecutionResult(
            criterion_text="`pip install X` runs successfully",
            extracted_command="pip install X",
            passed=True,
            exit_code=0,
            stdout="Successfully installed X",
            stderr="",
            elapsed_seconds=1.234,
            timed_out=False,
        )
        d = result.to_dict()
        assert d["criterion_text"] == "`pip install X` runs successfully"
        assert d["extracted_command"] == "pip install X"
        assert d["passed"] is True
        assert d["exit_code"] == 0
        assert d["stdout"] == "Successfully installed X"
        assert d["stderr"] == ""
        assert d["elapsed_seconds"] == 1.234
        assert d["timed_out"] is False

    def test_failed_result_to_dict(self):
        """Failed result should capture exit code and stderr."""
        result = CommandExecutionResult(
            criterion_text="`pip install bad` runs successfully",
            extracted_command="pip install bad",
            passed=False,
            exit_code=1,
            stdout="",
            stderr="ERROR: No matching distribution",
            elapsed_seconds=0.5,
            timed_out=False,
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert d["exit_code"] == 1
        assert "No matching distribution" in d["stderr"]

    def test_timeout_result_to_dict(self):
        """Timed-out result should have exit_code=None and timed_out=True."""
        result = CommandExecutionResult(
            criterion_text="`sleep 999` runs successfully",
            extracted_command="sleep 999",
            passed=False,
            exit_code=None,
            stdout="",
            stderr="",
            elapsed_seconds=60.0,
            timed_out=True,
        )
        d = result.to_dict()
        assert d["passed"] is False
        assert d["exit_code"] is None
        assert d["timed_out"] is True
        assert d["elapsed_seconds"] == 60.0

    def test_stdout_truncated_at_500_chars(self):
        """Long stdout should be truncated to 500 characters in to_dict."""
        long_output = "x" * 1000
        result = CommandExecutionResult(
            criterion_text="test",
            extracted_command="echo long",
            passed=True,
            exit_code=0,
            stdout=long_output,
        )
        d = result.to_dict()
        assert len(d["stdout"]) == 500

    def test_stderr_truncated_at_500_chars(self):
        """Long stderr should be truncated to 500 characters in to_dict."""
        long_output = "e" * 1000
        result = CommandExecutionResult(
            criterion_text="test",
            extracted_command="cmd",
            passed=False,
            exit_code=1,
            stderr=long_output,
        )
        d = result.to_dict()
        assert len(d["stderr"]) == 500

    def test_elapsed_seconds_rounded(self):
        """elapsed_seconds should be rounded to 3 decimal places."""
        result = CommandExecutionResult(
            criterion_text="test",
            extracted_command="cmd",
            passed=True,
            exit_code=0,
            elapsed_seconds=1.23456789,
        )
        d = result.to_dict()
        assert d["elapsed_seconds"] == 1.235

    def test_frozen_immutability(self):
        """CommandExecutionResult should be immutable (frozen=True)."""
        result = CommandExecutionResult(
            criterion_text="test",
            extracted_command="cmd",
            passed=True,
        )
        with pytest.raises(AttributeError):
            result.passed = False  # type: ignore[misc]

    def test_default_values(self):
        """Default values should be applied for optional fields."""
        result = CommandExecutionResult(
            criterion_text="test",
            extracted_command="cmd",
            passed=True,
        )
        assert result.exit_code is None
        assert result.stdout == ""
        assert result.stderr == ""
        assert result.elapsed_seconds == 0.0
        assert result.timed_out is False


# ============================================================================
# 6. Structured Result Capture Tests (7 tests) — TASK-RFX-528E
# ============================================================================


class TestStructuredResultCapture:
    """Tests for _execute_command_criteria returning List[CommandExecutionResult]."""

    def test_returns_list_on_success(self, orchestrator, worktree_path):
        """Successful command should return a result with passed=True."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pip install guardkit-py` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="OK", stderr=""
            )
            results = orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        assert len(results) == 1
        assert results[0].passed is True
        assert results[0].exit_code == 0
        assert results[0].timed_out is False

    def test_returns_list_on_failure(self, orchestrator, worktree_path):
        """Failed command should return a result with passed=False."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`pip install bad` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="error"
            )
            results = orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].exit_code == 1

    def test_returns_empty_list_no_command_criteria(self, orchestrator, worktree_path):
        """Non-command criteria should return empty list."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["File `src/main.py` exists"]

        with patch("subprocess.run") as mock_run:
            results = orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        assert results == []
        mock_run.assert_not_called()

    def test_timeout_result_captured(self, orchestrator, worktree_path):
        """Timed-out command should return result with timed_out=True."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`sleep 999` runs successfully"]

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 60)):
            results = orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        assert len(results) == 1
        assert results[0].passed is False
        assert results[0].timed_out is True
        assert results[0].exit_code is None

    def test_multiple_commands_all_captured(self, orchestrator, worktree_path):
        """Multiple commands should return a result for each."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = [
            "`pip install pkg1` runs successfully",
            "`pip install pkg2` runs successfully",
        ]

        call_count = 0

        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(returncode=0, stdout="OK", stderr="")
            else:
                return MagicMock(returncode=1, stdout="", stderr="fail")

        with patch("subprocess.run", side_effect=mock_run_side_effect):
            results = orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        assert len(results) == 2
        assert results[0].passed is True
        assert results[1].passed is False

    def test_results_still_inject_into_report(self, orchestrator, worktree_path):
        """Returning results should not break existing report injection behavior."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`echo hello` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="hello", stderr="")
            results = orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        # Both structured result AND report injection should work
        assert len(results) == 1
        assert results[0].passed is True
        assert len(report["requirements_addressed"]) == 1

    def test_result_captures_stdout_stderr(self, orchestrator, worktree_path):
        """Results should capture stdout and stderr from subprocess."""
        report = {"requirements_addressed": [], "_synthetic": True}
        criteria = ["`echo hello` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="hello world",
                stderr="some warning",
            )
            results = orchestrator._execute_command_criteria(
                synthetic_report=report,
                acceptance_criteria=criteria,
                worktree_path=worktree_path,
            )

        assert results[0].stdout == "hello world"
        assert results[0].stderr == "some warning"
