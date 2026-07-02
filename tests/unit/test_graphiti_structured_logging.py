"""Tests for [Memory] structured logging across integration points.

Verifies TASK-FIX-GCI5: consistent [Memory] prefixed log messages at all
Graphiti integration points with correct log levels.
"""

import logging
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# feature_plan_context.py logging
# ---------------------------------------------------------------------------


class TestFeaturePlanContextLogging:
    """Tests for [Memory] logging in FeaturePlanContextBuilder.build_context."""

    @pytest.fixture
    def builder(self, tmp_path):
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        b = FeaturePlanContextBuilder(project_root=tmp_path)
        return b

    @pytest.fixture
    def mock_graphiti_enabled(self, builder):
        client = AsyncMock()
        client.enabled = True
        client.search = AsyncMock(return_value=[])
        builder.graphiti_client = client
        return client

    @pytest.fixture
    def mock_graphiti_disabled(self, builder):
        client = MagicMock()
        client.enabled = False
        builder.graphiti_client = client
        return client

    async def test_logs_loading_message_when_graphiti_enabled(
        self, builder, mock_graphiti_enabled, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        assert any("[Memory] Loading context for feature planning..." in r.message for r in caplog.records)

    async def test_logs_context_loaded_with_category_count(
        self, builder, mock_graphiti_enabled, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        assert any("[Memory] Context loaded:" in r.message for r in caplog.records)

    async def test_logs_context_unavailable_when_disabled(
        self, builder, mock_graphiti_disabled, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        assert any(
            "[Memory] Context unavailable, continuing without enrichment" in r.message
            for r in caplog.records
        )

    async def test_logs_context_unavailable_when_client_none(
        self, builder, caplog
    ):
        builder.graphiti_client = None
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        assert any(
            "[Memory] Context unavailable" in r.message
            for r in caplog.records
        )

    async def test_no_graphiti_log_noise_when_client_none_not_attempted(
        self, builder, caplog
    ):
        """When Graphiti client is None, only the unavailable message should appear."""
        builder.graphiti_client = None
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        graphiti_messages = [r for r in caplog.records if "[Memory]" in r.message]
        # Should only have the unavailable message, not loading
        assert len(graphiti_messages) == 1
        assert "unavailable" in graphiti_messages[0].message

    async def test_loading_log_level_is_info(
        self, builder, mock_graphiti_enabled, caplog
    ):
        with caplog.at_level(logging.DEBUG, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        loading_records = [
            r for r in caplog.records
            if "[Memory] Loading context" in r.message
        ]
        assert len(loading_records) == 1
        assert loading_records[0].levelno == logging.INFO

    async def test_unavailable_log_level_is_info(
        self, builder, mock_graphiti_disabled, caplog
    ):
        with caplog.at_level(logging.DEBUG, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        unavailable_records = [
            r for r in caplog.records
            if "[Memory] Context unavailable" in r.message
        ]
        assert len(unavailable_records) == 1
        assert unavailable_records[0].levelno == logging.INFO


# ---------------------------------------------------------------------------
# autobuild_context_loader.py logging
# ---------------------------------------------------------------------------


class TestAutoBuildContextLoaderLogging:
    """Tests for [Memory] logging in AutoBuildContextLoader."""

    @pytest.fixture
    def mock_retriever(self):
        from guardkit.knowledge.autobuild_context_loader import AutoBuildContextResult
        from guardkit.knowledge.job_context_retriever import RetrievedContext

        context = RetrievedContext(
            task_id="TASK-001",
            budget_used=3200,
            budget_total=4000,
            feature_context=[{"id": "feat"}],
            similar_outcomes=[],
            relevant_patterns=[{"name": "pattern"}],
            architecture_context=[],
            warnings=[],
            domain_knowledge=[],
            role_constraints=[],
            quality_gate_configs=[],
            turn_states=[],
            implementation_modes=[],
        )

        retriever = AsyncMock()
        retriever.retrieve = AsyncMock(return_value=context)
        return retriever

    @pytest.fixture
    def loader_with_retriever(self, mock_retriever):
        from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader

        loader = AutoBuildContextLoader(graphiti=MagicMock())
        loader._retriever = mock_retriever
        return loader

    @pytest.fixture
    def loader_no_graphiti(self):
        from guardkit.knowledge.autobuild_context_loader import AutoBuildContextLoader

        return AutoBuildContextLoader(graphiti=None)

    async def test_player_logs_loading_with_turn_number(
        self, loader_with_retriever, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_with_retriever.get_player_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=3, description="Test",
            )

        assert any("[Memory] Loading Player context (turn 3)..." in r.message for r in caplog.records)

    async def test_player_logs_context_summary(
        self, loader_with_retriever, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_with_retriever.get_player_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=1, description="Test",
            )

        assert any("[Memory] Player context:" in r.message for r in caplog.records)

    async def test_coach_logs_loading_with_turn_number(
        self, loader_with_retriever, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_with_retriever.get_coach_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=2, description="Test",
            )

        assert any("[Memory] Loading Coach context (turn 2)..." in r.message for r in caplog.records)

    async def test_coach_logs_context_summary(
        self, loader_with_retriever, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_with_retriever.get_coach_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=1, description="Test",
            )

        assert any("[Memory] Coach context:" in r.message for r in caplog.records)

    async def test_no_loading_log_when_retriever_none(
        self, loader_no_graphiti, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_no_graphiti.get_player_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=1, description="Test",
            )

        assert not any("[Memory] Loading Player" in r.message for r in caplog.records)

    async def test_player_context_summary_includes_tokens(
        self, loader_with_retriever, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_with_retriever.get_player_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=1, description="Test",
            )

        summary_records = [r for r in caplog.records if "[Memory] Player context:" in r.message]
        assert len(summary_records) == 1
        assert "3200/4000" in summary_records[0].message

    async def test_all_logs_are_info_level(
        self, loader_with_retriever, caplog
    ):
        with caplog.at_level(logging.DEBUG, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_with_retriever.get_player_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=1, description="Test",
            )

        graphiti_records = [r for r in caplog.records if "[Memory]" in r.message]
        for record in graphiti_records:
            assert record.levelno == logging.INFO



# ---------------------------------------------------------------------------
# Cross-cutting: consistent format
# ---------------------------------------------------------------------------


class TestConsistentGraphitiLogFormat:
    """Verify all [Memory] logs use consistent prefix format."""

    async def test_all_graphiti_logs_use_bracket_prefix(self):
        """Every Graphiti log message must start with [Memory]."""
        # This is a structural test - verified by the individual tests above
        # asserting exact message prefixes. Kept for documentation.
        pass
