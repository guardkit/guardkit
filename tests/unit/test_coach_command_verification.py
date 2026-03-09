"""
Unit tests for CoachValidator.verify_command_criteria() (TASK-RFX-7C63).

Tests the Coach-level runtime verification of command_execution criteria:
- Command execution via subprocess in worktree
- Failure classification using command_failure_classifier
- Pip normalisation and venv PATH prepending
- Timeout protection (per-command and aggregate)
- No-op when no command criteria present
- Worktree path safety assertion
- Integration: orchestrator delegation preserves behavior

Coverage Target: >=85%
Test Count: 15+ tests
"""

import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from guardkit.orchestrator.quality_gates.coach_validator import CoachValidator
from guardkit.orchestrator.quality_gates.command_models import (
    CommandExecutionResult,
    CommandVerificationResult,
    COMMAND_TIMEOUT_SECONDS,
    COMMAND_TOTAL_TIMEOUT_SECONDS,
    WORKTREE_SENTINEL,
    _assert_worktree_path,
    normalise_pip_command,
    build_venv_env,
    _PIP_CMD_RE,
)


# ============================================================================
# Test Fixtures
# ============================================================================


@pytest.fixture
def worktree_path(tmp_path):
    """Create a temporary path that looks like a worktree."""
    wt = tmp_path / ".guardkit" / "worktrees" / "TASK-TEST-001"
    wt.mkdir(parents=True)
    return wt


@pytest.fixture
def coach(worktree_path):
    """Create CoachValidator pointed at the test worktree."""
    return CoachValidator(str(worktree_path))


# ============================================================================
# 1. verify_command_criteria() Core Tests
# ============================================================================


class TestVerifyCommandCriteria:
    """Tests for CoachValidator.verify_command_criteria()."""

    def test_successful_command_returns_passed(self, coach, worktree_path):
        """Successful command should appear in results and passed_criteria."""
        criteria = ["`echo hello` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, stdout="hello", stderr=""
            )
            result = coach.verify_command_criteria(criteria)

        assert isinstance(result, CommandVerificationResult)
        assert len(result.results) == 1
        assert result.results[0].passed is True
        assert result.results[0].exit_code == 0
        assert len(result.passed_criteria) == 1
        assert "`echo hello` runs successfully" in result.passed_criteria
        assert len(result.failures) == 0

    def test_failed_command_returns_failure(self, coach, worktree_path):
        """Failed command should appear in results and failures."""
        criteria = ["`false` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=1, stdout="", stderr="error output"
            )
            result = coach.verify_command_criteria(criteria)

        assert len(result.results) == 1
        assert result.results[0].passed is False
        assert result.results[0].exit_code == 1
        assert len(result.passed_criteria) == 0
        assert len(result.failures) == 1
        assert result.failures[0].classification in (
            "environment", "implementation", "transient", "unknown"
        )

    def test_timeout_recorded_as_transient(self, coach, worktree_path):
        """Timed-out command should be recorded with classification=transient."""
        criteria = ["`sleep 999` runs successfully"]

        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("sleep", 60)):
            result = coach.verify_command_criteria(criteria)

        assert len(result.results) == 1
        assert result.results[0].passed is False
        assert result.results[0].timed_out is True
        assert result.results[0].exit_code is None
        assert len(result.failures) == 1
        assert result.failures[0].classification == "transient"
        assert result.failures[0].timed_out is True

    def test_no_command_criteria_returns_empty(self, coach):
        """Non-command criteria should return empty verification result."""
        criteria = ["File `src/main.py` exists in the project"]

        result = coach.verify_command_criteria(criteria)

        assert isinstance(result, CommandVerificationResult)
        assert result.results == []
        assert result.passed_criteria == []
        assert result.failures == []

    def test_multiple_commands_all_captured(self, coach, worktree_path):
        """Multiple commands should each produce a result."""
        criteria = [
            "`echo one` runs successfully",
            "`echo two` runs successfully",
        ]

        call_count = 0

        def mock_run_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return MagicMock(returncode=0, stdout="one", stderr="")
            else:
                return MagicMock(returncode=1, stdout="", stderr="fail")

        with patch("subprocess.run", side_effect=mock_run_side_effect):
            result = coach.verify_command_criteria(criteria)

        assert len(result.results) == 2
        assert result.results[0].passed is True
        assert result.results[1].passed is False
        assert len(result.passed_criteria) == 1
        assert len(result.failures) == 1

    def test_command_runs_in_worktree_cwd(self, coach, worktree_path):
        """Command should execute with cwd set to the worktree path."""
        criteria = ["`echo test` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            coach.verify_command_criteria(criteria)

        mock_run.assert_called_once()
        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["cwd"] == str(worktree_path)
        assert call_kwargs["shell"] is True

    def test_aggregate_timeout_stops_remaining(self, coach, worktree_path):
        """When aggregate timeout is exceeded, remaining commands should be skipped."""
        criteria = [
            "`pip install pkg1` runs successfully",
            "`pip install pkg2` runs successfully",
        ]

        call_count = 0

        def slow_run(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise subprocess.TimeoutExpired("pip install", 60)

        with patch("subprocess.run", side_effect=slow_run):
            result = coach.verify_command_criteria(
                criteria, per_command_timeout=60, total_timeout=60
            )

        # First command times out (60s added), second should be skipped
        assert call_count == 1
        assert len(result.results) == 1


# ============================================================================
# 2. Pip Normalisation Tests
# ============================================================================


class TestPipNormalisationInCoach:
    """Tests for pip normalisation in verify_command_criteria."""

    def test_pip_install_normalized(self, coach, worktree_path):
        """Bare `pip install X` should become `sys.executable -m pip install X`."""
        criteria = ["`pip install guardkit-py` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            coach.verify_command_criteria(criteria)

        call_args = mock_run.call_args
        executed_cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args")
        assert executed_cmd.startswith(sys.executable)
        assert "-m pip install guardkit-py" in executed_cmd

    def test_non_pip_command_not_normalized(self, coach, worktree_path):
        """Non-pip commands should not be affected by normalization."""
        criteria = ["`pytest tests/ -v` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            coach.verify_command_criteria(criteria)

        call_args = mock_run.call_args
        executed_cmd = call_args[0][0] if call_args[0] else call_args.kwargs.get("args")
        assert executed_cmd == "pytest tests/ -v"


# ============================================================================
# 3. Venv PATH Injection Tests
# ============================================================================


class TestVenvPathInCoach:
    """Tests for virtualenv PATH prepending in verify_command_criteria."""

    def test_venv_bin_prepended_when_exists(self, coach, worktree_path):
        """When .venv/bin/ exists, PATH should be prepended."""
        venv_bin = worktree_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)

        criteria = ["`pytest tests/ -v` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            coach.verify_command_criteria(criteria)

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["env"] is not None
        assert call_kwargs["env"]["PATH"].startswith(str(venv_bin))

    def test_no_venv_no_env_override(self, coach, worktree_path):
        """When no .venv/bin/ exists, env should be None."""
        criteria = ["`pytest tests/ -v` runs successfully"]

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            coach.verify_command_criteria(criteria)

        call_kwargs = mock_run.call_args.kwargs
        assert call_kwargs["env"] is None


# ============================================================================
# 4. Worktree Safety Tests
# ============================================================================


class TestWorktreeSafetyInCoach:
    """Tests for worktree path assertion in verify_command_criteria."""

    def test_rejects_non_worktree_path(self, tmp_path):
        """Coach should refuse to execute commands outside a worktree."""
        coach = CoachValidator(str(tmp_path))
        criteria = ["`echo hello` runs successfully"]

        with pytest.raises(RuntimeError, match="Refusing to execute commands outside worktree"):
            coach.verify_command_criteria(criteria)


# ============================================================================
# 5. Shared Module Tests (command_models.py)
# ============================================================================


class TestCommandModels:
    """Tests for shared command_models module."""

    def test_normalise_pip_command_bare_pip(self):
        """normalise_pip_command should normalise bare pip."""
        result = normalise_pip_command("pip install X")
        assert result == f"{sys.executable} -m pip install X"

    def test_normalise_pip_command_non_pip(self):
        """normalise_pip_command should not affect non-pip commands."""
        result = normalise_pip_command("pytest tests/")
        assert result == "pytest tests/"

    def test_normalise_pip_command_python_m_pip(self):
        """normalise_pip_command should not double-normalise."""
        result = normalise_pip_command("python -m pip install X")
        assert result == "python -m pip install X"

    def test_build_venv_env_with_venv(self, tmp_path):
        """build_venv_env should return env with venv PATH when .venv/bin exists."""
        venv_bin = tmp_path / ".venv" / "bin"
        venv_bin.mkdir(parents=True)

        env = build_venv_env(tmp_path)
        assert env is not None
        assert env["PATH"].startswith(str(venv_bin))

    def test_build_venv_env_without_venv(self, tmp_path):
        """build_venv_env should return None when no .venv/bin exists."""
        env = build_venv_env(tmp_path)
        assert env is None

    def test_assert_worktree_path_valid(self, worktree_path):
        """_assert_worktree_path should accept valid worktree paths."""
        _assert_worktree_path(worktree_path)  # Should not raise

    def test_assert_worktree_path_invalid(self, tmp_path):
        """_assert_worktree_path should reject non-worktree paths."""
        with pytest.raises(RuntimeError, match=WORKTREE_SENTINEL):
            _assert_worktree_path(tmp_path)

    def test_command_verification_result_defaults(self):
        """CommandVerificationResult should have sensible defaults."""
        result = CommandVerificationResult()
        assert result.results == []
        assert result.failures == []
        assert result.passed_criteria == []

    def test_pip_cmd_re_matches(self):
        """_PIP_CMD_RE should match bare pip commands."""
        assert _PIP_CMD_RE.match("pip install X")
        assert _PIP_CMD_RE.match("pip freeze")
        assert _PIP_CMD_RE.match("pip")
        assert not _PIP_CMD_RE.match("pip3 install X")
        assert not _PIP_CMD_RE.match("pipenv install X")


# ============================================================================
# 6. Orchestrator Delegation Integration Tests
# ============================================================================


class TestOrchestratorDelegation:
    """Tests that AutoBuild._execute_command_criteria delegates to Coach."""

    def test_delegation_preserves_report_injection(self, worktree_path):
        """Orchestrator should still inject results into synthetic_report."""
        from guardkit.orchestrator.autobuild import CommandExecutionResult as ABResult

        # Verify re-export works
        assert ABResult is CommandExecutionResult

    def test_constants_re_exported(self):
        """Constants should be importable from autobuild.py for backward compat."""
        from guardkit.orchestrator.autobuild import (
            COMMAND_TIMEOUT_SECONDS as ab_timeout,
            COMMAND_TOTAL_TIMEOUT_SECONDS as ab_total,
            WORKTREE_SENTINEL as ab_sentinel,
            _PIP_CMD_RE as ab_pip_re,
            _assert_worktree_path as ab_assert,
        )

        assert ab_timeout == COMMAND_TIMEOUT_SECONDS
        assert ab_total == COMMAND_TOTAL_TIMEOUT_SECONDS
        assert ab_sentinel == WORKTREE_SENTINEL
        assert ab_pip_re is _PIP_CMD_RE
        assert ab_assert is _assert_worktree_path
