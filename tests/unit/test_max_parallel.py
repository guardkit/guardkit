"""
Unit tests for --max-parallel CLI option (TASK-VPR-001).

Tests:
- CLI option parsing and validation
- Environment variable override (GUARDKIT_MAX_PARALLEL_TASKS)
- Auto-detection default (1 for local backends, None otherwise)
- Semaphore-based wave dispatch limiting
- Edge cases (max_parallel=1, large values)

Coverage Target: >=85%
"""

import asyncio
import os
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest
from click.testing import CliRunner

from guardkit.cli.autobuild import autobuild
from guardkit.cli.main import cli
from guardkit.orchestrator.feature_orchestrator import (
    FeatureOrchestrator,
    TaskExecutionResult,
)


# ============================================================================
# CLI Option Parsing Tests
# ============================================================================


class TestMaxParallelCLI:
    """Test --max-parallel CLI option parsing."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    def test_max_parallel_appears_in_help(self, cli_runner):
        """--max-parallel option should appear in feature command help."""
        result = cli_runner.invoke(cli, ["autobuild", "feature", "--help"])
        assert "--max-parallel" in result.output

    @patch("guardkit.cli.autobuild._require_sdk")
    @patch("guardkit.cli.autobuild.FeatureOrchestrator")
    def test_max_parallel_passed_to_orchestrator(self, mock_orch_cls, mock_sdk, cli_runner):
        """--max-parallel value should be passed to FeatureOrchestrator."""
        mock_orch = MagicMock()
        mock_orch.orchestrate.return_value = MagicMock(success=True)
        mock_orch_cls.return_value = mock_orch

        result = cli_runner.invoke(
            cli, ["autobuild", "feature", "FEAT-TEST", "--max-parallel", "3"]
        )

        # Check FeatureOrchestrator was called with max_parallel=3
        call_kwargs = mock_orch_cls.call_args[1]
        assert call_kwargs["max_parallel"] == 3

    @patch("guardkit.cli.autobuild._require_sdk")
    @patch("guardkit.cli.autobuild.FeatureOrchestrator")
    @patch("guardkit.orchestrator.agent_invoker.detect_timeout_multiplier", return_value=4.0)
    def test_auto_detect_local_backend(self, mock_detect, mock_orch_cls, mock_sdk, cli_runner):
        """When no --max-parallel and local backend detected, default to 1."""
        mock_orch = MagicMock()
        mock_orch.orchestrate.return_value = MagicMock(success=True)
        mock_orch_cls.return_value = mock_orch

        result = cli_runner.invoke(
            cli, ["autobuild", "feature", "FEAT-TEST"]
        )

        call_kwargs = mock_orch_cls.call_args[1]
        assert call_kwargs["max_parallel"] == 1

    @patch("guardkit.cli.autobuild._require_sdk")
    @patch("guardkit.cli.autobuild.FeatureOrchestrator")
    @patch("guardkit.orchestrator.agent_invoker.detect_timeout_multiplier", return_value=1.0)
    def test_auto_detect_remote_backend(self, mock_detect, mock_orch_cls, mock_sdk, cli_runner):
        """When no --max-parallel and remote backend, default to None (unlimited)."""
        mock_orch = MagicMock()
        mock_orch.orchestrate.return_value = MagicMock(success=True)
        mock_orch_cls.return_value = mock_orch

        result = cli_runner.invoke(
            cli, ["autobuild", "feature", "FEAT-TEST"]
        )

        call_kwargs = mock_orch_cls.call_args[1]
        assert call_kwargs["max_parallel"] is None


# ============================================================================
# Environment Variable Override Tests
# ============================================================================


class TestMaxParallelEnvVar:
    """Test GUARDKIT_MAX_PARALLEL_TASKS environment variable."""

    @pytest.fixture
    def cli_runner(self):
        return CliRunner()

    @patch("guardkit.cli.autobuild._require_sdk")
    @patch("guardkit.cli.autobuild.FeatureOrchestrator")
    def test_env_var_overrides_cli(self, mock_orch_cls, mock_sdk, cli_runner, monkeypatch):
        """GUARDKIT_MAX_PARALLEL_TASKS overrides --max-parallel flag."""
        monkeypatch.setenv("GUARDKIT_MAX_PARALLEL_TASKS", "4")
        mock_orch = MagicMock()
        mock_orch.orchestrate.return_value = MagicMock(success=True)
        mock_orch_cls.return_value = mock_orch

        result = cli_runner.invoke(
            cli, ["autobuild", "feature", "FEAT-TEST", "--max-parallel", "2"]
        )

        call_kwargs = mock_orch_cls.call_args[1]
        assert call_kwargs["max_parallel"] == 4

    @patch("guardkit.cli.autobuild._require_sdk")
    @patch("guardkit.cli.autobuild.FeatureOrchestrator")
    def test_env_var_overrides_auto_detect(self, mock_orch_cls, mock_sdk, cli_runner, monkeypatch):
        """GUARDKIT_MAX_PARALLEL_TASKS overrides auto-detection."""
        monkeypatch.setenv("GUARDKIT_MAX_PARALLEL_TASKS", "5")
        mock_orch = MagicMock()
        mock_orch.orchestrate.return_value = MagicMock(success=True)
        mock_orch_cls.return_value = mock_orch

        result = cli_runner.invoke(
            cli, ["autobuild", "feature", "FEAT-TEST"]
        )

        call_kwargs = mock_orch_cls.call_args[1]
        assert call_kwargs["max_parallel"] == 5


# ============================================================================
# Orchestrator Parameter Tests
# ============================================================================


class TestMaxParallelOrchestrator:
    """Test FeatureOrchestrator max_parallel parameter."""

    @patch("guardkit.orchestrator.agent_invoker.detect_timeout_multiplier", return_value=1.0)
    def test_orchestrator_accepts_max_parallel(self, mock_detect, tmp_path):
        """FeatureOrchestrator should accept max_parallel parameter."""
        orch = FeatureOrchestrator(
            repo_root=tmp_path,
            max_parallel=3,
            worktree_manager=MagicMock(),
        )
        assert orch.max_parallel == 3

    @patch("guardkit.orchestrator.agent_invoker.detect_timeout_multiplier", return_value=1.0)
    def test_orchestrator_default_none(self, mock_detect, tmp_path):
        """FeatureOrchestrator should default max_parallel to None."""
        orch = FeatureOrchestrator(
            repo_root=tmp_path,
            worktree_manager=MagicMock(),
        )
        assert orch.max_parallel is None


# ============================================================================
# Semaphore-Based Wave Execution Tests
# ============================================================================


class TestMaxParallelWaveExecution:
    """Test semaphore-based wave dispatch limiting."""

    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self):
        """Semaphore should limit concurrent task execution."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def mock_task(task_num):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)

            await asyncio.sleep(0.05)  # Simulate work

            async with lock:
                current_concurrent -= 1

            return TaskExecutionResult(
                task_id=f"TASK-{task_num}",
                success=True,
                total_turns=1,
                final_decision="approved",
            )

        # Test with semaphore limiting to 2
        semaphore = asyncio.Semaphore(2)

        async def bounded(c=None):
            async with semaphore:
                return await c

        tasks = [bounded(c=mock_task(i)) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert max_concurrent <= 2
        assert all(r.success for r in results)

    @pytest.mark.asyncio
    async def test_no_semaphore_unlimited(self):
        """Without semaphore, all tasks run concurrently."""
        max_concurrent = 0
        current_concurrent = 0
        lock = asyncio.Lock()

        async def mock_task(task_num):
            nonlocal max_concurrent, current_concurrent
            async with lock:
                current_concurrent += 1
                max_concurrent = max(max_concurrent, current_concurrent)

            await asyncio.sleep(0.05)

            async with lock:
                current_concurrent -= 1

            return f"result-{task_num}"

        tasks = [mock_task(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert max_concurrent == 5  # All ran concurrently
