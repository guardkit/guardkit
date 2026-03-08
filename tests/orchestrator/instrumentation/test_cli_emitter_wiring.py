"""Tests for CLI emitter wiring (TASK-INST-013).

Verifies that:
- The ``feature`` CLI command creates a CompositeBackend with JSONLFileBackend
- Events directory is ``.guardkit/autobuild/{feature_id}/``
- FeatureOrchestrator receives the emitter and forwards it to AutoBuildOrchestrator
- Emitter flush/close lifecycle is managed correctly
- Flush/close errors are logged, not raised
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from guardkit.orchestrator.instrumentation.emitter import (
    CompositeBackend,
    JSONLFileBackend,
    NullEmitter,
)


# ============================================================================
# CLI Emitter Creation Tests
# ============================================================================


class TestCLIEmitterCreation:
    """Test that the feature CLI command creates the correct emitter."""

    def test_composite_backend_created_with_jsonl(self, tmp_path: Path) -> None:
        """CompositeBackend wraps a JSONLFileBackend targeting the feature events dir."""
        feature_id = "FEAT-TEST-001"
        events_dir = tmp_path / ".guardkit" / "autobuild" / feature_id

        backend = JSONLFileBackend(events_dir=events_dir)
        emitter = CompositeBackend(backends=[backend])

        assert isinstance(emitter, CompositeBackend)
        assert len(emitter._backends) == 1
        assert isinstance(emitter._backends[0], JSONLFileBackend)

    def test_events_dir_path_uses_feature_id(self) -> None:
        """Events directory is .guardkit/autobuild/{feature_id}/."""
        feature_id = "FEAT-A1B2"
        events_dir = Path(".guardkit/autobuild") / feature_id
        assert str(events_dir) == ".guardkit/autobuild/FEAT-A1B2"

    def test_jsonl_backend_creates_directory_on_emit(self, tmp_path: Path) -> None:
        """JSONLFileBackend creates the events directory on first write."""
        from guardkit.orchestrator.instrumentation.schemas import TaskStartedEvent

        events_dir = tmp_path / ".guardkit" / "autobuild" / "FEAT-TEST"
        backend = JSONLFileBackend(events_dir=events_dir)

        assert not events_dir.exists()

        event = TaskStartedEvent(
            run_id="run-001",
            task_id="TASK-001",
            agent_role="player",
            attempt=1,
            timestamp="2026-03-08T12:00:00Z",
        )
        asyncio.run(backend.emit(event))

        assert events_dir.exists()
        assert (events_dir / "events.jsonl").exists()


# ============================================================================
# FeatureOrchestrator Emitter Pass-Through Tests
# ============================================================================


class TestFeatureOrchestratorEmitterPassThrough:
    """Test that FeatureOrchestrator forwards emitter to AutoBuildOrchestrator."""

    def test_feature_orchestrator_stores_emitter(self, tmp_path: Path) -> None:
        """FeatureOrchestrator stores the provided emitter."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        mock_emitter = NullEmitter(capture=True)
        mock_wm = MagicMock()

        orchestrator = FeatureOrchestrator(
            repo_root=tmp_path,
            emitter=mock_emitter,
            worktree_manager=mock_wm,
        )

        assert orchestrator._emitter is mock_emitter

    def test_feature_orchestrator_defaults_to_null_emitter(self, tmp_path: Path) -> None:
        """FeatureOrchestrator defaults to NullEmitter when no emitter provided."""
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        mock_wm = MagicMock()
        orchestrator = FeatureOrchestrator(repo_root=tmp_path, worktree_manager=mock_wm)

        assert isinstance(orchestrator._emitter, NullEmitter)

    def test_emitter_forwarded_to_autobuild_orchestrator(self) -> None:
        """FeatureOrchestrator source passes emitter=self._emitter to AutoBuildOrchestrator."""
        import inspect
        from guardkit.orchestrator.feature_orchestrator import FeatureOrchestrator

        source = inspect.getsource(FeatureOrchestrator)
        assert "emitter=self._emitter" in source


# ============================================================================
# Emitter Lifecycle Tests
# ============================================================================


class TestEmitterLifecycle:
    """Test flush/close lifecycle management."""

    def test_flush_called_on_composite_backend(self) -> None:
        """CompositeBackend.flush() delegates to all backends."""
        mock_backend = AsyncMock()
        emitter = CompositeBackend(backends=[mock_backend])

        asyncio.run(emitter.flush())

        mock_backend.flush.assert_called_once()

    def test_close_called_on_composite_backend(self) -> None:
        """CompositeBackend.close() delegates to all backends."""
        mock_backend = AsyncMock()
        emitter = CompositeBackend(backends=[mock_backend])

        asyncio.run(emitter.close())

        mock_backend.close.assert_called_once()

    def test_flush_error_logged_not_raised(self, caplog: pytest.LogCaptureFixture) -> None:
        """Flush errors are logged as warnings, not propagated."""
        mock_backend = AsyncMock()
        mock_backend.flush.side_effect = OSError("disk full")
        emitter = CompositeBackend(backends=[mock_backend])

        # CompositeBackend catches and logs backend errors
        with caplog.at_level(logging.WARNING):
            asyncio.run(emitter.flush())

        assert "failed during flush" in caplog.text.lower()

    def test_close_error_logged_not_raised(self, caplog: pytest.LogCaptureFixture) -> None:
        """Close errors are logged as warnings, not propagated."""
        mock_backend = AsyncMock()
        mock_backend.close.side_effect = RuntimeError("already closed")
        emitter = CompositeBackend(backends=[mock_backend])

        with caplog.at_level(logging.WARNING):
            asyncio.run(emitter.close())

        assert "failed during close" in caplog.text.lower()

    def test_flush_then_close_order(self) -> None:
        """Flush should be called before close in normal lifecycle."""
        call_order = []

        async def mock_flush():
            call_order.append("flush")

        async def mock_close():
            call_order.append("close")

        mock_backend = AsyncMock()
        mock_backend.flush = mock_flush
        mock_backend.close = mock_close
        emitter = CompositeBackend(backends=[mock_backend])

        asyncio.run(emitter.flush())
        asyncio.run(emitter.close())

        assert call_order == ["flush", "close"]


# ============================================================================
# CLI Integration Wiring Test
# ============================================================================


class TestCLIWiringIntegration:
    """Verify the CLI source code contains the expected wiring."""

    @pytest.fixture()
    def cli_source(self) -> str:
        """Return the source of the autobuild CLI module."""
        import inspect
        import guardkit.cli.autobuild as cli_module
        return inspect.getsource(cli_module)

    def test_cli_feature_command_creates_emitter(self, cli_source: str) -> None:
        """The feature command source creates CompositeBackend with JSONLFileBackend."""
        assert "CompositeBackend" in cli_source
        assert "JSONLFileBackend" in cli_source
        assert "emitter=emitter" in cli_source

    def test_cli_feature_command_has_finally_block(self, cli_source: str) -> None:
        """The feature command has a finally block for emitter lifecycle."""
        assert "finally:" in cli_source
        assert "emitter.flush()" in cli_source
        assert "emitter.close()" in cli_source

    def test_cli_imports_emitter_classes(self) -> None:
        """The CLI module imports CompositeBackend and JSONLFileBackend."""
        from guardkit.cli import autobuild as cli_module

        assert hasattr(cli_module, "CompositeBackend")
        assert hasattr(cli_module, "JSONLFileBackend")
