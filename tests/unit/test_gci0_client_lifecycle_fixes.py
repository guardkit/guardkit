"""
Tests for TASK-FIX-GCI0: Graphiti Client Lifecycle Fixes

Validates three fixes:
1. graphiti_context_loader.py — await removed from sync get_graphiti() call
2. interactive_capture.py — lazy property for _graphiti
3. feature_plan_context.py — lazy property for graphiti_client

Coverage Target: >=85%
Test Count: 18 tests
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


# ============================================================================
# 1. Fix 1: graphiti_context_loader.py — await removed (4 tests)
# ============================================================================

class TestContextLoaderAwaitRemoved:
    """Verify that _get_retriever calls get_graphiti() synchronously."""

    @pytest.mark.asyncio
    async def test_get_retriever_calls_get_graphiti_synchronously(self):
        """get_graphiti() is called as sync function, not awaited."""
        from installer.core.commands.lib.graphiti_context_loader import _get_retriever

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.get_graphiti'
        ) as mock_get:
            mock_get.return_value = MagicMock()

            await _get_retriever()

            # get_graphiti should be called once, synchronously
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_retriever_passes_client_to_retriever(self):
        """get_graphiti() result is passed to JobContextRetriever."""
        from installer.core.commands.lib.graphiti_context_loader import _get_retriever
        from guardkit.knowledge.job_context_retriever import JobContextRetriever

        mock_client = MagicMock()

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.get_graphiti',
            return_value=mock_client,
        ):
            retriever = await _get_retriever()
            assert isinstance(retriever, JobContextRetriever)

    @pytest.mark.asyncio
    async def test_get_retriever_propagates_sync_exception(self):
        """If get_graphiti() raises synchronously, exception propagates."""
        from installer.core.commands.lib.graphiti_context_loader import _get_retriever

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.get_graphiti',
            side_effect=RuntimeError("Config missing"),
        ):
            with pytest.raises(RuntimeError, match="Config missing"):
                await _get_retriever()

    @pytest.mark.asyncio
    async def test_load_task_context_works_end_to_end(self):
        """Full load_task_context flow works with sync get_graphiti."""
        from installer.core.commands.lib.graphiti_context_loader import load_task_context

        mock_retriever = AsyncMock()
        mock_context = MagicMock()
        mock_context.to_prompt.return_value = "## Context"
        mock_retriever.retrieve.return_value = mock_context

        with patch(
            'installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled',
            return_value=True,
        ), patch(
            'installer.core.commands.lib.graphiti_context_loader._get_retriever',
            return_value=mock_retriever,
        ):
            result = await load_task_context(
                task_id="TASK-001",
                task_data={"description": "test"},
                phase="implement",
            )
            assert result == "## Context"


# ============================================================================
# 2. Fix 2: interactive_capture.py — lazy _graphiti property (7 tests)
# ============================================================================

class TestInteractiveCapturelazyGraphiti:
    """Verify lazy property behavior for _graphiti in InteractiveCaptureSession."""

    def test_init_does_not_call_get_graphiti(self):
        """__init__ should NOT call get_graphiti() (deferred to first access)."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()
            session = InteractiveCaptureSession()
            mock_get.assert_not_called()

    def test_first_access_calls_get_graphiti(self):
        """First access to _graphiti triggers get_graphiti()."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            session = InteractiveCaptureSession()
            client = session._graphiti

            mock_get.assert_called_once()
            assert client is mock_client

    def test_second_access_does_not_call_get_graphiti_again(self):
        """Subsequent accesses use cached result (no extra calls)."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = MagicMock()

            session = InteractiveCaptureSession()
            _ = session._graphiti
            _ = session._graphiti

            mock_get.assert_called_once()

    def test_lazy_property_returns_none_when_unavailable(self):
        """Lazy property returns None when get_graphiti() returns None."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_get.return_value = None

            session = InteractiveCaptureSession()
            assert session._graphiti is None

    def test_setter_allows_direct_assignment(self):
        """_graphiti setter allows mock injection for testing."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            session = InteractiveCaptureSession()

            mock_client = MagicMock()
            session._graphiti = mock_client

            assert session._graphiti is mock_client
            # get_graphiti should never have been called (setter bypasses lazy init)
            mock_get.assert_not_called()

    def test_setter_marks_resolved(self):
        """After setter, lazy init flag is set so get_graphiti is not called."""
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            session = InteractiveCaptureSession()
            session._graphiti = MagicMock()

            # Access again — should NOT trigger get_graphiti
            _ = session._graphiti
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_save_captured_knowledge_uses_lazy_client(self):
        """_save_captured_knowledge accesses _graphiti via lazy property."""
        from guardkit.knowledge.interactive_capture import (
            InteractiveCaptureSession,
            CapturedKnowledge,
        )
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        with patch('guardkit.knowledge.interactive_capture.get_graphiti') as mock_get:
            mock_graphiti = AsyncMock()
            mock_graphiti.add_episode = AsyncMock(return_value="episode-1")
            mock_get.return_value = mock_graphiti

            session = InteractiveCaptureSession()
            session._captured = [
                CapturedKnowledge(
                    category=KnowledgeCategory.ARCHITECTURE,
                    question="What patterns?",
                    answer="Repository pattern is used extensively.",
                    extracted_facts=["Architecture: Repository pattern"],
                )
            ]

            await session._save_captured_knowledge()

            # get_graphiti should have been called lazily during save
            mock_get.assert_called_once()
            mock_graphiti.add_episode.assert_called_once()


# ============================================================================
# 3. Fix 3: feature_plan_context.py — lazy graphiti_client property (7 tests)
# ============================================================================

class TestFeaturePlanContextBuilderLazyClient:
    """Verify lazy property behavior for graphiti_client."""

    PATCH_TARGET = 'guardkit.knowledge.graphiti_client.get_graphiti'

    def test_init_does_not_call_get_graphiti(self, tmp_path):
        """__init__ should NOT call get_graphiti() (deferred)."""
        with patch(self.PATCH_TARGET) as mock_get:
            from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

            project_root = tmp_path / "project"
            project_root.mkdir()
            builder = FeaturePlanContextBuilder(project_root=project_root)

            # get_graphiti should NOT be called during construction
            mock_get.assert_not_called()

    def test_first_access_calls_get_graphiti(self, tmp_path):
        """First access to graphiti_client triggers get_graphiti()."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        project_root = tmp_path / "project"
        project_root.mkdir()
        builder = FeaturePlanContextBuilder(project_root=project_root)

        with patch(self.PATCH_TARGET) as mock_get:
            mock_client = MagicMock()
            mock_get.return_value = mock_client

            client = builder.graphiti_client

            mock_get.assert_called_once()
            assert client is mock_client

    def test_second_access_uses_cache(self, tmp_path):
        """Subsequent accesses use cached result."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        project_root = tmp_path / "project"
        project_root.mkdir()
        builder = FeaturePlanContextBuilder(project_root=project_root)

        with patch(self.PATCH_TARGET) as mock_get:
            mock_get.return_value = MagicMock()

            _ = builder.graphiti_client
            _ = builder.graphiti_client

            mock_get.assert_called_once()

    def test_lazy_property_returns_none_when_unavailable(self, tmp_path):
        """Returns None when get_graphiti() returns None."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        project_root = tmp_path / "project"
        project_root.mkdir()
        builder = FeaturePlanContextBuilder(project_root=project_root)

        with patch(self.PATCH_TARGET, return_value=None):
            assert builder.graphiti_client is None

    def test_setter_allows_mock_injection(self, tmp_path):
        """graphiti_client setter works for test mock injection."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        project_root = tmp_path / "project"
        project_root.mkdir()
        builder = FeaturePlanContextBuilder(project_root=project_root)

        mock_client = MagicMock()
        builder.graphiti_client = mock_client

        assert builder.graphiti_client is mock_client

    def test_setter_prevents_lazy_init(self, tmp_path):
        """After setter, lazy init does not trigger get_graphiti."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        project_root = tmp_path / "project"
        project_root.mkdir()
        builder = FeaturePlanContextBuilder(project_root=project_root)

        builder.graphiti_client = MagicMock()

        with patch(self.PATCH_TARGET) as mock_get:
            _ = builder.graphiti_client
            mock_get.assert_not_called()

    @pytest.mark.asyncio
    async def test_build_context_uses_lazy_client(self, tmp_path):
        """build_context() accesses graphiti_client via lazy property."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        project_root = tmp_path / "project"
        project_root.mkdir()
        builder = FeaturePlanContextBuilder(project_root=project_root)

        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])
        builder.graphiti_client = mock_client

        result = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python",
        )

        # Should have used the injected client
        assert mock_client.search.called
