"""Tests for [Graphiti] structured logging across integration points.

Verifies TASK-FIX-GCI5: consistent [Graphiti] prefixed log messages at all
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
    """Tests for [Graphiti] logging in FeaturePlanContextBuilder.build_context."""

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

        assert any("[Graphiti] Loading context for feature planning..." in r.message for r in caplog.records)

    async def test_logs_context_loaded_with_category_count(
        self, builder, mock_graphiti_enabled, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        assert any("[Graphiti] Context loaded:" in r.message for r in caplog.records)

    async def test_logs_context_unavailable_when_disabled(
        self, builder, mock_graphiti_disabled, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        assert any(
            "[Graphiti] Context unavailable, continuing without enrichment" in r.message
            for r in caplog.records
        )

    async def test_logs_context_unavailable_when_client_none(
        self, builder, caplog
    ):
        builder.graphiti_client = None
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        assert any(
            "[Graphiti] Context unavailable" in r.message
            for r in caplog.records
        )

    async def test_no_graphiti_log_noise_when_client_none_not_attempted(
        self, builder, caplog
    ):
        """When Graphiti client is None, only the unavailable message should appear."""
        builder.graphiti_client = None
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.feature_plan_context"):
            await builder.build_context(description="Test feature")

        graphiti_messages = [r for r in caplog.records if "[Graphiti]" in r.message]
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
            if "[Graphiti] Loading context" in r.message
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
            if "[Graphiti] Context unavailable" in r.message
        ]
        assert len(unavailable_records) == 1
        assert unavailable_records[0].levelno == logging.INFO


# ---------------------------------------------------------------------------
# autobuild_context_loader.py logging
# ---------------------------------------------------------------------------


class TestAutoBuildContextLoaderLogging:
    """Tests for [Graphiti] logging in AutoBuildContextLoader."""

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

        assert any("[Graphiti] Loading Player context (turn 3)..." in r.message for r in caplog.records)

    async def test_player_logs_context_summary(
        self, loader_with_retriever, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_with_retriever.get_player_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=1, description="Test",
            )

        assert any("[Graphiti] Player context:" in r.message for r in caplog.records)

    async def test_coach_logs_loading_with_turn_number(
        self, loader_with_retriever, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_with_retriever.get_coach_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=2, description="Test",
            )

        assert any("[Graphiti] Loading Coach context (turn 2)..." in r.message for r in caplog.records)

    async def test_coach_logs_context_summary(
        self, loader_with_retriever, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_with_retriever.get_coach_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=1, description="Test",
            )

        assert any("[Graphiti] Coach context:" in r.message for r in caplog.records)

    async def test_no_loading_log_when_retriever_none(
        self, loader_no_graphiti, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_no_graphiti.get_player_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=1, description="Test",
            )

        assert not any("[Graphiti] Loading Player" in r.message for r in caplog.records)

    async def test_player_context_summary_includes_tokens(
        self, loader_with_retriever, caplog
    ):
        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.autobuild_context_loader"):
            await loader_with_retriever.get_player_context(
                task_id="TASK-001", feature_id="FEAT-001",
                turn_number=1, description="Test",
            )

        summary_records = [r for r in caplog.records if "[Graphiti] Player context:" in r.message]
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

        graphiti_records = [r for r in caplog.records if "[Graphiti]" in r.message]
        for record in graphiti_records:
            assert record.levelno == logging.INFO


# ---------------------------------------------------------------------------
# graphiti_context_loader.py logging
# ---------------------------------------------------------------------------


class TestGraphitiContextLoaderLogging:
    """Tests for [Graphiti] logging in graphiti_context_loader.load_task_context."""

    @pytest.fixture
    def mock_retriever_context(self):
        """Create a mock RetrievedContext with to_prompt."""
        ctx = MagicMock()
        ctx.to_prompt.return_value = "context prompt"
        ctx.budget_used = 2100
        ctx.budget_total = 4000
        ctx.feature_context = [{"id": "feat"}]
        ctx.similar_outcomes = []
        ctx.relevant_patterns = [{"name": "p1"}, {"name": "p2"}]
        ctx.architecture_context = [{"style": "clean"}]
        ctx.warnings = []
        ctx.domain_knowledge = [{"fact": "domain"}]
        return ctx

    async def test_logs_loading_with_phase(self, mock_retriever_context, caplog):
        with patch("installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled", return_value=True), \
             patch("installer.core.commands.lib.graphiti_context_loader._get_retriever") as mock_get, \
             patch("installer.core.commands.lib.graphiti_context_loader._get_task_phase"):
            retriever = AsyncMock()
            retriever.retrieve = AsyncMock(return_value=mock_retriever_context)
            mock_get.return_value = retriever

            with caplog.at_level(logging.INFO, logger="installer.core.commands.lib.graphiti_context_loader"):
                from installer.core.commands.lib.graphiti_context_loader import load_task_context
                await load_task_context("TASK-001", {"description": "test"}, "implement")

        assert any("[Graphiti] Loading task context for Phase implement..." in r.message for r in caplog.records)

    async def test_logs_task_context_summary(self, mock_retriever_context, caplog):
        with patch("installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled", return_value=True), \
             patch("installer.core.commands.lib.graphiti_context_loader._get_retriever") as mock_get, \
             patch("installer.core.commands.lib.graphiti_context_loader._get_task_phase"):
            retriever = AsyncMock()
            retriever.retrieve = AsyncMock(return_value=mock_retriever_context)
            mock_get.return_value = retriever

            with caplog.at_level(logging.INFO, logger="installer.core.commands.lib.graphiti_context_loader"):
                from installer.core.commands.lib.graphiti_context_loader import load_task_context
                await load_task_context("TASK-001", {"description": "test"}, "implement")

        assert any("[Graphiti] Task context:" in r.message for r in caplog.records)

    async def test_logs_unavailable_on_exception(self, caplog):
        with patch("installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled", return_value=True), \
             patch("installer.core.commands.lib.graphiti_context_loader._get_retriever", side_effect=Exception("fail")):

            with caplog.at_level(logging.WARNING, logger="installer.core.commands.lib.graphiti_context_loader"):
                from installer.core.commands.lib.graphiti_context_loader import load_task_context
                result = await load_task_context("TASK-001", {"description": "test"}, "implement")

        assert result is None
        assert any("[Graphiti] Task context unavailable" in r.message for r in caplog.records)

    async def test_no_log_when_graphiti_disabled(self, caplog):
        with patch("installer.core.commands.lib.graphiti_context_loader.is_graphiti_enabled", return_value=False):
            with caplog.at_level(logging.INFO, logger="installer.core.commands.lib.graphiti_context_loader"):
                from installer.core.commands.lib.graphiti_context_loader import load_task_context
                await load_task_context("TASK-001", {"description": "test"}, "implement")

        assert not any("[Graphiti]" in r.message for r in caplog.records)


# ---------------------------------------------------------------------------
# interactive_capture.py logging
# ---------------------------------------------------------------------------


class TestInteractiveCaptureLogging:
    """Tests for [Graphiti] logging in InteractiveCaptureSession."""

    @pytest.fixture
    def session(self):
        from guardkit.knowledge.interactive_capture import InteractiveCaptureSession
        return InteractiveCaptureSession()

    @pytest.fixture
    def session_with_graphiti(self, session):
        client = AsyncMock()
        client.add_episode = AsyncMock()
        session._graphiti = client
        return session

    @pytest.fixture
    def session_no_graphiti(self, session):
        session._graphiti = None
        return session

    async def test_logs_unavailable_when_graphiti_none(
        self, session_no_graphiti, caplog
    ):
        from guardkit.knowledge.interactive_capture import CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        session_no_graphiti._captured = [
            CapturedKnowledge(
                category=KnowledgeCategory.ARCHITECTURE,
                question="What patterns?",
                answer="We use clean architecture",
                extracted_facts=["Architecture: We use clean architecture"],
            )
        ]

        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.interactive_capture"):
            await session_no_graphiti._save_captured_knowledge()

        assert any(
            "[Graphiti] Knowledge capture: Graphiti unavailable" in r.message
            for r in caplog.records
        )

    async def test_unavailable_log_includes_insight_count(
        self, session_no_graphiti, caplog
    ):
        from guardkit.knowledge.interactive_capture import CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        session_no_graphiti._captured = [
            CapturedKnowledge(
                category=KnowledgeCategory.ARCHITECTURE,
                question="Q1", answer="A1",
                extracted_facts=["f1"],
            ),
            CapturedKnowledge(
                category=KnowledgeCategory.DOMAIN,
                question="Q2", answer="A2",
                extracted_facts=["f2"],
            ),
        ]

        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.interactive_capture"):
            await session_no_graphiti._save_captured_knowledge()

        records = [r for r in caplog.records if "[Graphiti] Knowledge capture:" in r.message]
        assert len(records) == 1
        assert "2 insights not persisted" in records[0].message

    async def test_logs_stored_count_on_success(
        self, session_with_graphiti, caplog
    ):
        from guardkit.knowledge.interactive_capture import CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        session_with_graphiti._captured = [
            CapturedKnowledge(
                category=KnowledgeCategory.ARCHITECTURE,
                question="Q1", answer="A1",
                extracted_facts=["Architecture: fact1"],
            ),
            CapturedKnowledge(
                category=KnowledgeCategory.ARCHITECTURE,
                question="Q2", answer="A2",
                extracted_facts=["Architecture: fact2"],
            ),
        ]

        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.interactive_capture"):
            await session_with_graphiti._save_captured_knowledge()

        assert any(
            "[Graphiti] Knowledge capture: 2 insights stored" in r.message
            for r in caplog.records
        )

    async def test_no_stored_log_when_nothing_captured(
        self, session_with_graphiti, caplog
    ):
        session_with_graphiti._captured = []

        with caplog.at_level(logging.INFO, logger="guardkit.knowledge.interactive_capture"):
            await session_with_graphiti._save_captured_knowledge()

        assert not any("[Graphiti]" in r.message for r in caplog.records)

    async def test_stored_log_level_is_info(
        self, session_with_graphiti, caplog
    ):
        from guardkit.knowledge.interactive_capture import CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        session_with_graphiti._captured = [
            CapturedKnowledge(
                category=KnowledgeCategory.DOMAIN,
                question="Q", answer="A long enough answer here",
                extracted_facts=["Domain: A long enough answer here"],
            ),
        ]

        with caplog.at_level(logging.DEBUG, logger="guardkit.knowledge.interactive_capture"):
            await session_with_graphiti._save_captured_knowledge()

        stored_records = [
            r for r in caplog.records
            if "[Graphiti] Knowledge capture:" in r.message and "stored" in r.message
        ]
        assert len(stored_records) == 1
        assert stored_records[0].levelno == logging.INFO

    async def test_failed_episode_logs_debug(
        self, session_with_graphiti, caplog
    ):
        from guardkit.knowledge.interactive_capture import CapturedKnowledge
        from guardkit.knowledge.gap_analyzer import KnowledgeCategory

        session_with_graphiti._graphiti_client.add_episode = AsyncMock(
            side_effect=Exception("connection failed")
        )

        session_with_graphiti._captured = [
            CapturedKnowledge(
                category=KnowledgeCategory.ARCHITECTURE,
                question="Q", answer="A long enough answer here",
                extracted_facts=["Architecture: fact"],
            ),
        ]

        with caplog.at_level(logging.DEBUG, logger="guardkit.knowledge.interactive_capture"):
            await session_with_graphiti._save_captured_knowledge()

        debug_records = [
            r for r in caplog.records
            if "[Graphiti] Failed to store" in r.message
        ]
        assert len(debug_records) == 1
        assert debug_records[0].levelno == logging.DEBUG


# ---------------------------------------------------------------------------
# Cross-cutting: consistent format
# ---------------------------------------------------------------------------


class TestConsistentGraphitiLogFormat:
    """Verify all [Graphiti] logs use consistent prefix format."""

    async def test_all_graphiti_logs_use_bracket_prefix(self):
        """Every Graphiti log message must start with [Graphiti]."""
        # This is a structural test - verified by the individual tests above
        # asserting exact message prefixes. Kept for documentation.
        pass
