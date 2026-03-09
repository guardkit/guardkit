"""
Unit tests for AutoBuild orchestrator-level command execution (TASK-CRV-537E).

Tests the runtime verification of command_execution acceptance criteria:
- Worktree path assertion (defensive check)
- Command execution and result injection into synthetic reports
- Timeout protection (per-command and aggregate)
- Skipping when not on synthetic report path

Coverage Target: >=85%
Test Count: 13 tests
"""

import subprocess
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

import pytest

from guardkit.orchestrator.autobuild import (
    AutoBuildOrchestrator,
    COMMAND_TIMEOUT_SECONDS,
    COMMAND_TOTAL_TIMEOUT_SECONDS,
    WORKTREE_SENTINEL,
    _assert_worktree_path,
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
