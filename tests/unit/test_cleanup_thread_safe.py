"""Test TASK-ACR-006: Thread-safe Graphiti client cleanup.

Verifies the three-branch cleanup logic:
1. Loop is running → run_coroutine_threadsafe
2. Loop is stopped but not closed → run_until_complete
3. Loop is closed → asyncio.run
"""

import asyncio
import concurrent.futures
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from guardkit.orchestrator.autobuild import AutoBuildOrchestrator


@pytest.fixture
def mock_worktree_manager():
    """Create a mock WorktreeManager."""
    manager = Mock()
    # Don't need to mock methods since we're testing cleanup directly
    return manager


class TestThreeBranchCleanup:
    """Test the three-branch cleanup logic for different event loop states."""

    def test_cleanup_running_loop_uses_run_coroutine_threadsafe(self, tmp_path, mock_worktree_manager):
        """AC-002: If original loop is still running, schedules close on it."""
        # Setup
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            verbose=False
        )

        # Mock loader with graphiti client
        mock_graphiti = AsyncMock()
        mock_graphiti.close = AsyncMock()
        mock_loader = Mock()
        mock_loader.graphiti = mock_graphiti

        # Mock event loop that is running
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_loop.is_closed.return_value = False

        # Mock future for run_coroutine_threadsafe
        mock_future = Mock()
        mock_future.result = Mock(return_value=None)

        # Store in thread loaders
        thread_id = threading.get_ident()
        orchestrator._thread_loaders[thread_id] = (mock_loader, mock_loop)

        # Patch run_coroutine_threadsafe
        with patch(
            "asyncio.run_coroutine_threadsafe", return_value=mock_future
        ) as mock_run_threadsafe:
            # Execute
            orchestrator._cleanup_thread_loaders()

            # Verify run_coroutine_threadsafe was called
            mock_run_threadsafe.assert_called_once()
            call_args = mock_run_threadsafe.call_args
            assert call_args[0][1] == mock_loop  # Loop passed as 2nd arg

            # Verify timeout was set
            mock_future.result.assert_called_once_with(timeout=30)

            # Verify graphiti.close was called
            assert mock_graphiti.close.call_count == 1

    def test_cleanup_stopped_loop_uses_run_until_complete(self, tmp_path, mock_worktree_manager):
        """AC-002 variant: If loop stopped but not closed, run directly."""
        # Setup
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            verbose=False
        )

        # Mock loader with graphiti client
        mock_graphiti = AsyncMock()
        mock_graphiti.close = AsyncMock()
        mock_loader = Mock()
        mock_loader.graphiti = mock_graphiti

        # Mock event loop that is stopped but not closed
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.is_closed.return_value = False
        mock_loop.run_until_complete = Mock()

        # Store in thread loaders
        thread_id = threading.get_ident()
        orchestrator._thread_loaders[thread_id] = (mock_loader, mock_loop)

        # Execute
        orchestrator._cleanup_thread_loaders()

        # Verify run_until_complete was called
        mock_loop.run_until_complete.assert_called_once()
        assert mock_graphiti.close.call_count == 1

    def test_cleanup_closed_loop_uses_asyncio_run(self, tmp_path, mock_worktree_manager):
        """AC-003: If original loop is closed, uses asyncio.run()."""
        # Setup
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            verbose=False
        )

        # Mock loader with graphiti client
        mock_graphiti = AsyncMock()
        mock_graphiti.close = AsyncMock()
        mock_loader = Mock()
        mock_loader.graphiti = mock_graphiti

        # Mock event loop that is closed
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.is_closed.return_value = True

        # Store in thread loaders
        thread_id = threading.get_ident()
        orchestrator._thread_loaders[thread_id] = (mock_loader, mock_loop)

        # Patch asyncio.run
        with patch("asyncio.run") as mock_asyncio_run:
            # Execute
            orchestrator._cleanup_thread_loaders()

            # Verify asyncio.run was called
            mock_asyncio_run.assert_called_once()
            assert mock_graphiti.close.call_count == 1

    def test_cleanup_suppresses_runtime_error(self, tmp_path, mock_worktree_manager):
        """AC-004: Catches and suppresses RuntimeError."""
        # Setup
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            verbose=False
        )

        # Mock loader with graphiti client that raises RuntimeError
        mock_graphiti = AsyncMock()
        mock_loader = Mock()
        mock_loader.graphiti = mock_graphiti

        # Mock event loop
        mock_loop = Mock()
        mock_loop.is_running.return_value = False
        mock_loop.is_closed.return_value = False
        mock_loop.run_until_complete.side_effect = RuntimeError(
            "Event loop is closed"
        )

        # Store in thread loaders
        thread_id = threading.get_ident()
        orchestrator._thread_loaders[thread_id] = (mock_loader, mock_loop)

        # Execute - should not raise
        orchestrator._cleanup_thread_loaders()

        # Verify cleanup completed without exception
        assert len(orchestrator._thread_loaders) == 0

    def test_cleanup_handles_none_loader_gracefully(self, tmp_path, mock_worktree_manager):
        """Verify None loader is skipped."""
        # Setup
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            verbose=False
        )

        # Mock event loop
        mock_loop = Mock()

        # Store None loader
        thread_id = threading.get_ident()
        orchestrator._thread_loaders[thread_id] = (None, mock_loop)

        # Execute - should not raise
        orchestrator._cleanup_thread_loaders()

        # Verify cleanup completed
        assert len(orchestrator._thread_loaders) == 0

    def test_cleanup_handles_none_graphiti_gracefully(self, tmp_path, mock_worktree_manager):
        """Verify loader with None graphiti is skipped."""
        # Setup
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            verbose=False
        )

        # Mock loader with None graphiti
        mock_loader = Mock()
        mock_loader.graphiti = None

        # Mock event loop
        mock_loop = Mock()

        # Store in thread loaders
        thread_id = threading.get_ident()
        orchestrator._thread_loaders[thread_id] = (mock_loader, mock_loop)

        # Execute - should not raise
        orchestrator._cleanup_thread_loaders()

        # Verify cleanup completed
        assert len(orchestrator._thread_loaders) == 0

    def test_cleanup_timeout_is_30_seconds(self, tmp_path, mock_worktree_manager):
        """AC-005: Cleanup has a timeout (30s)."""
        # Setup
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            verbose=False
        )

        # Mock loader with graphiti client
        mock_graphiti = AsyncMock()
        mock_graphiti.close = AsyncMock()
        mock_loader = Mock()
        mock_loader.graphiti = mock_graphiti

        # Mock event loop that is running
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_loop.is_closed.return_value = False

        # Mock future for run_coroutine_threadsafe
        mock_future = Mock()
        mock_future.result = Mock(return_value=None)

        # Store in thread loaders
        thread_id = threading.get_ident()
        orchestrator._thread_loaders[thread_id] = (mock_loader, mock_loop)

        # Patch run_coroutine_threadsafe
        with patch(
            "asyncio.run_coroutine_threadsafe", return_value=mock_future
        ) as mock_run_threadsafe:
            # Execute
            orchestrator._cleanup_thread_loaders()

            # Verify timeout=30
            mock_future.result.assert_called_once_with(timeout=30)

    def test_cleanup_uses_stored_loop_reference(self, tmp_path, mock_worktree_manager):
        """AC-001: Uses stored event loop reference for each thread's loader."""
        # Setup
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            verbose=False
        )

        # Mock loader with graphiti client
        mock_graphiti = AsyncMock()
        mock_graphiti.close = AsyncMock()
        mock_loader = Mock()
        mock_loader.graphiti = mock_graphiti

        # Create specific event loop instance
        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_loop.is_closed.return_value = False

        # Mock future
        mock_future = Mock()
        mock_future.result = Mock(return_value=None)

        # Store in thread loaders with specific loop
        thread_id = threading.get_ident()
        orchestrator._thread_loaders[thread_id] = (mock_loader, mock_loop)

        # Patch run_coroutine_threadsafe
        with patch(
            "asyncio.run_coroutine_threadsafe", return_value=mock_future
        ) as mock_run_threadsafe:
            # Execute
            orchestrator._cleanup_thread_loaders()

            # Verify the EXACT stored loop was used
            call_args = mock_run_threadsafe.call_args
            assert call_args[0][1] is mock_loop  # Identity check

    def test_cleanup_handles_timeout_gracefully(self, tmp_path, mock_worktree_manager):
        """AC-005: TimeoutError from future.result() is suppressed."""
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            verbose=False
        )

        mock_graphiti = AsyncMock()
        mock_graphiti.close = AsyncMock()
        mock_loader = Mock()
        mock_loader.graphiti = mock_graphiti

        mock_loop = Mock()
        mock_loop.is_running.return_value = True
        mock_loop.is_closed.return_value = False

        mock_future = Mock()
        mock_future.result = Mock(side_effect=concurrent.futures.TimeoutError())

        thread_id = threading.get_ident()
        orchestrator._thread_loaders[thread_id] = (mock_loader, mock_loop)

        with patch(
            "asyncio.run_coroutine_threadsafe", return_value=mock_future
        ):
            orchestrator._cleanup_thread_loaders()
            assert len(orchestrator._thread_loaders) == 0

    def test_cleanup_clears_all_loaders(self, tmp_path, mock_worktree_manager):
        """Verify all loaders are cleared after cleanup."""
        # Setup
        orchestrator = AutoBuildOrchestrator(
            repo_root=tmp_path,
            worktree_manager=mock_worktree_manager,
            verbose=False
        )

        # Create multiple mock loaders
        for i in range(3):
            mock_graphiti = AsyncMock()
            mock_graphiti.close = AsyncMock()
            mock_loader = Mock()
            mock_loader.graphiti = mock_graphiti

            mock_loop = Mock()
            mock_loop.is_running.return_value = False
            mock_loop.is_closed.return_value = True

            orchestrator._thread_loaders[i] = (mock_loader, mock_loop)

        # Patch asyncio.run
        with patch("asyncio.run"):
            # Execute
            orchestrator._cleanup_thread_loaders()

            # Verify all cleared
            assert len(orchestrator._thread_loaders) == 0
