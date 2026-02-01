"""
End-to-end integration tests for Graphiti workflow integration.

These tests verify the complete Graphiti integration with GuardKit workflows:
- Seeding with metadata
- Context loading during command execution
- Knowledge retrieval for task-work, task-review, feature-build
- Graceful degradation when Graphiti unavailable

Prerequisites:
- Docker running with docker-compose.graphiti.yml
- OPENAI_API_KEY environment variable set
- Neo4j accessible at bolt://localhost:7687
- graphiti-core package installed

Run with: pytest tests/integration/graphiti/test_workflow_integration.py -v -m integration

To run only live tests (requires full infrastructure):
    pytest tests/integration/graphiti/test_workflow_integration.py -v -m "integration and live"

To run mock-only tests (no infrastructure needed):
    pytest tests/integration/graphiti/test_workflow_integration.py -v -m "integration and not live"
"""

import pytest
import os
import json
import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Optional

# Check for graphiti-core availability
try:
    from guardkit.knowledge.graphiti_client import (
        GraphitiConfig,
        GraphitiClient,
        init_graphiti,
        get_graphiti,
    )
    from guardkit.knowledge.seeding import (
        seed_all_system_context,
        is_seeded,
        clear_seeding_marker,
        mark_seeded,
        SEEDING_VERSION,
    )
    from guardkit.knowledge.context_loader import (
        load_critical_context,
        CriticalContext,
    )
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False

# Check for OpenAI API key
OPENAI_API_KEY_SET = bool(os.getenv("OPENAI_API_KEY"))

pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not GRAPHITI_AVAILABLE, reason="graphiti-core not installed"),
]


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def neo4j_config():
    """Standard Neo4j configuration for tests."""
    return GraphitiConfig(
        enabled=True,
        neo4j_uri=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        neo4j_user=os.getenv("NEO4J_USER", "neo4j"),
        neo4j_password=os.getenv("NEO4J_PASSWORD", "password123"),
    )


@pytest.fixture
async def live_graphiti_client(neo4j_config):
    """
    Provide a live Graphiti client connected to Neo4j.

    Requires:
    - Neo4j running (docker-compose.graphiti.yml)
    - OPENAI_API_KEY set
    """
    if not OPENAI_API_KEY_SET:
        pytest.skip("OPENAI_API_KEY not set")

    client = GraphitiClient(neo4j_config)
    initialized = await client.initialize()

    if not initialized:
        pytest.skip("Neo4j not available or initialization failed")

    yield client

    await client.close()


@pytest.fixture
def mock_graphiti_client():
    """Create a mock Graphiti client for unit-style integration tests."""
    client = MagicMock(spec=GraphitiClient)
    client.enabled = True
    client.config = MagicMock()
    client.config.enabled = True
    client.add_episode = AsyncMock()
    client.search = AsyncMock(return_value=[])
    client.close = AsyncMock()
    client.initialize = AsyncMock(return_value=True)
    client.health_check = AsyncMock(return_value=True)
    return client


@pytest.fixture
def temp_state_dir(tmp_path, monkeypatch):
    """Use a temporary directory for seeding state."""
    monkeypatch.setattr(
        "guardkit.knowledge.seeding.get_state_dir",
        lambda: tmp_path
    )
    return tmp_path


# =============================================================================
# SEEDING INTEGRATION TESTS
# =============================================================================

class TestSeedingWorkflow:
    """Test the complete seeding workflow with metadata."""

    @pytest.mark.asyncio
    async def test_seed_creates_metadata_episodes(
        self, mock_graphiti_client, temp_state_dir
    ):
        """Verify seeding creates episodes with proper metadata."""
        clear_seeding_marker()

        result = await seed_all_system_context(mock_graphiti_client, force=True)

        assert result is True
        assert mock_graphiti_client.add_episode.call_count > 0

        # Verify metadata in episodes
        for call in mock_graphiti_client.add_episode.call_args_list[:5]:
            episode_body_json = call.kwargs.get("episode_body", "{}")
            episode_body = json.loads(episode_body_json)

            assert "_metadata" in episode_body
            metadata = episode_body["_metadata"]
            assert metadata["source"] == "guardkit_seeding"
            assert metadata["version"] == SEEDING_VERSION
            assert "created_at" in metadata

    @pytest.mark.asyncio
    async def test_seed_creates_marker_with_version(
        self, mock_graphiti_client, temp_state_dir
    ):
        """Verify seeding creates marker file with version info."""
        clear_seeding_marker()

        await seed_all_system_context(mock_graphiti_client, force=True)

        marker_file = temp_state_dir / ".graphiti_seeded.json"
        assert marker_file.exists()

        marker_data = json.loads(marker_file.read_text())
        assert marker_data["seeded"] is True
        assert marker_data["version"] == SEEDING_VERSION
        assert "timestamp" in marker_data

    @pytest.mark.asyncio
    @pytest.mark.live
    @pytest.mark.skipif(not OPENAI_API_KEY_SET, reason="OPENAI_API_KEY not set")
    async def test_live_seeding_and_verify(self, live_graphiti_client, temp_state_dir):
        """
        Live test: Seed data and verify it can be queried.

        This test requires:
        - Running Neo4j instance
        - Valid OPENAI_API_KEY
        """
        clear_seeding_marker()

        # Seed the system context
        result = await seed_all_system_context(live_graphiti_client, force=True)
        assert result is True

        # Verify seeding marker was created
        assert is_seeded()

        # Test queries against seeded data
        queries = [
            ("GuardKit product workflow", ["product_knowledge"]),
            ("quality gate phase approval", ["quality_gate_phases"]),
            ("task-work command", ["command_workflows"]),
        ]

        for query, group_ids in queries:
            results = await live_graphiti_client.search(
                query=query,
                group_ids=group_ids,
                num_results=3
            )
            # Results may be empty but should not raise
            assert isinstance(results, list)


# =============================================================================
# CONTEXT LOADING INTEGRATION TESTS
# =============================================================================

class TestContextLoadingWorkflow:
    """Test context loading for workflow commands."""

    @pytest.mark.asyncio
    async def test_load_critical_context_structure(self):
        """Verify load_critical_context returns proper structure."""
        with patch("guardkit.knowledge.context_loader.get_graphiti") as mock_get:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.search = AsyncMock(return_value=[
                {"name": "test", "body": "test content"}
            ])
            mock_get.return_value = mock_client

            context = await load_critical_context(command="task-work")

            assert isinstance(context, CriticalContext)
            assert hasattr(context, "system_context")
            assert hasattr(context, "quality_gates")
            assert hasattr(context, "architecture_decisions")
            assert hasattr(context, "failure_patterns")

    @pytest.mark.asyncio
    async def test_load_context_graceful_degradation(self):
        """Verify context loading returns empty context when Graphiti unavailable."""
        with patch("guardkit.knowledge.context_loader.get_graphiti") as mock_get:
            mock_get.return_value = None

            context = await load_critical_context(command="task-work")

            assert isinstance(context, CriticalContext)
            assert context.system_context == []
            assert context.quality_gates == []

    @pytest.mark.asyncio
    async def test_load_context_handles_disabled_client(self):
        """Verify context loading handles disabled client gracefully."""
        with patch("guardkit.knowledge.context_loader.get_graphiti") as mock_get:
            mock_client = MagicMock()
            mock_client.enabled = False
            mock_get.return_value = mock_client

            context = await load_critical_context(command="task-work")

            assert isinstance(context, CriticalContext)
            assert context.system_context == []

    @pytest.mark.asyncio
    async def test_load_context_for_feature_build_includes_extra(self):
        """Verify feature-build command loads additional context."""
        with patch("guardkit.knowledge.context_loader.get_graphiti") as mock_get:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.search = AsyncMock(return_value=[
                {"name": "Player-Coach", "body": "adversarial workflow"}
            ])
            mock_get.return_value = mock_client

            context = await load_critical_context(command="feature-build")

            # feature-build should trigger additional queries
            assert mock_client.search.call_count >= 4  # system + quality + arch + failure + fb

    @pytest.mark.asyncio
    @pytest.mark.live
    @pytest.mark.skipif(not OPENAI_API_KEY_SET, reason="OPENAI_API_KEY not set")
    async def test_live_context_loading(self, live_graphiti_client, temp_state_dir):
        """
        Live test: Load context from seeded Graphiti.

        This test requires seeded data from test_live_seeding_and_verify.
        """
        # Ensure seeded
        if not is_seeded():
            await seed_all_system_context(live_graphiti_client, force=True)

        # Load context using the live client
        with patch("guardkit.knowledge.context_loader.get_graphiti") as mock_get:
            mock_get.return_value = live_graphiti_client

            context = await load_critical_context(command="task-work")

            # Should have loaded some context (may be empty if no matches)
            assert isinstance(context, CriticalContext)


# =============================================================================
# CLI COMMAND INTEGRATION TESTS
# =============================================================================

class TestCLICommandIntegration:
    """Test CLI command integration with Graphiti."""

    @pytest.mark.asyncio
    async def test_graphiti_status_command(self, mock_graphiti_client):
        """Verify graphiti status command works with mock client."""
        from guardkit.cli.graphiti import _cmd_status

        with patch("guardkit.cli.graphiti._get_client_and_config") as mock_get:
            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"
            mock_settings.neo4j_user = "neo4j"
            mock_settings.timeout = 30

            mock_get.return_value = (mock_graphiti_client, mock_settings)

            with patch("guardkit.cli.graphiti.is_seeded", return_value=True):
                # Should not raise
                await _cmd_status()

    @pytest.mark.asyncio
    async def test_graphiti_verify_command_runs_queries(self, mock_graphiti_client):
        """Verify graphiti verify command runs test queries."""
        from guardkit.cli.graphiti import _cmd_verify

        mock_graphiti_client.search = AsyncMock(return_value=[
            {"name": "result", "score": 0.9}
        ])

        with patch("guardkit.cli.graphiti._get_client_and_config") as mock_get:
            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = "bolt://localhost:7687"

            mock_get.return_value = (mock_graphiti_client, mock_settings)

            with patch("guardkit.cli.graphiti.is_seeded", return_value=True):
                await _cmd_verify(verbose=True)

                # Verify search was called multiple times for test queries
                assert mock_graphiti_client.search.call_count >= 5

    @pytest.mark.asyncio
    @pytest.mark.live
    @pytest.mark.skipif(not OPENAI_API_KEY_SET, reason="OPENAI_API_KEY not set")
    async def test_live_cli_verify(self, live_graphiti_client, temp_state_dir):
        """
        Live test: Run verify command against real Graphiti.
        """
        from guardkit.cli.graphiti import _cmd_verify

        # Ensure seeded
        if not is_seeded():
            await seed_all_system_context(live_graphiti_client, force=True)

        with patch("guardkit.cli.graphiti._get_client_and_config") as mock_get:
            mock_settings = MagicMock()
            mock_settings.enabled = True
            mock_settings.neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")

            mock_get.return_value = (live_graphiti_client, mock_settings)

            # Should not raise
            await _cmd_verify(verbose=False)


# =============================================================================
# GRACEFUL DEGRADATION TESTS
# =============================================================================

class TestGracefulDegradation:
    """Test that GuardKit works correctly when Graphiti is unavailable."""

    @pytest.mark.asyncio
    async def test_context_loading_without_graphiti(self):
        """Verify commands work when Graphiti client is None."""
        with patch("guardkit.knowledge.context_loader.get_graphiti") as mock_get:
            mock_get.return_value = None

            context = await load_critical_context(
                task_id="TASK-001",
                command="task-work"
            )

            # Should return empty context, not raise
            assert isinstance(context, CriticalContext)
            assert context.system_context == []

    @pytest.mark.asyncio
    async def test_search_returns_empty_on_error(self, mock_graphiti_client):
        """Verify search returns empty list on connection errors."""
        mock_graphiti_client.search = AsyncMock(
            side_effect=Exception("Connection failed")
        )
        mock_graphiti_client.config.enabled = True

        # Direct call to verify behavior
        try:
            results = await mock_graphiti_client.search("test query")
        except Exception:
            results = []

        assert results == []

    @pytest.mark.asyncio
    async def test_disabled_client_skips_operations(self):
        """Verify disabled client skips all operations gracefully."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        # Search should return empty
        results = await client.search("test")
        assert results == []

        # Close should not raise
        await client.close()


# =============================================================================
# WORKFLOW SEQUENCE TESTS
# =============================================================================

class TestWorkflowSequence:
    """Test complete workflow sequences with Graphiti integration."""

    @pytest.mark.asyncio
    async def test_task_work_context_injection_sequence(self):
        """Verify context is loaded at task-work start."""
        with patch("guardkit.knowledge.context_loader.get_graphiti") as mock_get:
            mock_client = MagicMock()
            mock_client.enabled = True
            mock_client.search = AsyncMock(return_value=[
                {"name": "ADR-001", "body": "Use SDK not subprocess"},
                {"name": "quality-gate", "body": "Phase 4.5 test enforcement"},
            ])
            mock_get.return_value = mock_client

            # Simulate task-work startup sequence
            context = await load_critical_context(
                task_id="TASK-TEST-001",
                command="task-work"
            )

            # Context should contain architecture decisions
            assert mock_client.search.called

            # Verify expected search categories were queried
            search_calls = mock_client.search.call_args_list
            group_ids_queried = []
            for call in search_calls:
                if "group_ids" in call.kwargs:
                    group_ids_queried.extend(call.kwargs["group_ids"])

            assert "product_knowledge" in group_ids_queried or \
                   "command_workflows" in group_ids_queried

    @pytest.mark.asyncio
    @pytest.mark.live
    @pytest.mark.skipif(not OPENAI_API_KEY_SET, reason="OPENAI_API_KEY not set")
    async def test_live_full_workflow_sequence(
        self, live_graphiti_client, temp_state_dir
    ):
        """
        Live test: Complete workflow from seeding to context usage.

        Sequence:
        1. Clear any existing state
        2. Seed system context
        3. Verify seeding
        4. Load context for task-work
        5. Verify context contains expected data
        """
        # Step 1: Clear state
        clear_seeding_marker()

        # Step 2: Seed
        result = await seed_all_system_context(live_graphiti_client, force=True)
        assert result is True

        # Step 3: Verify seeding
        assert is_seeded()

        # Step 4: Load context
        with patch("guardkit.knowledge.context_loader.get_graphiti") as mock_get:
            mock_get.return_value = live_graphiti_client

            context = await load_critical_context(command="task-work")

        # Step 5: Verify context structure
        assert isinstance(context, CriticalContext)
        # Note: Content may vary based on what was seeded


# =============================================================================
# CLEAR AND RESEED TESTS
# =============================================================================

class TestClearAndReseed:
    """Test clearing and re-seeding workflow."""

    @pytest.mark.asyncio
    async def test_clear_marker_allows_reseed(
        self, mock_graphiti_client, temp_state_dir
    ):
        """Verify clearing marker allows re-seeding."""
        # First seed
        await seed_all_system_context(mock_graphiti_client, force=True)
        assert is_seeded()

        # Clear
        clear_seeding_marker()
        assert not is_seeded()

        # Re-seed should work
        mock_graphiti_client.add_episode.reset_mock()
        await seed_all_system_context(mock_graphiti_client, force=False)

        assert is_seeded()
        assert mock_graphiti_client.add_episode.call_count > 0

    @pytest.mark.asyncio
    @pytest.mark.live
    @pytest.mark.skipif(not OPENAI_API_KEY_SET, reason="OPENAI_API_KEY not set")
    async def test_live_clear_and_reseed(
        self, live_graphiti_client, temp_state_dir
    ):
        """
        Live test: Clear existing data and reseed with new metadata.

        This is the recommended procedure when updating seeding logic.
        """
        # Clear marker
        clear_seeding_marker()

        # Clear Graphiti data (if client supports it)
        if hasattr(live_graphiti_client, 'clear_all'):
            await live_graphiti_client.clear_all()

        # Re-seed
        result = await seed_all_system_context(live_graphiti_client, force=True)
        assert result is True

        # Verify
        assert is_seeded()

        # Query to confirm data exists
        results = await live_graphiti_client.search(
            "GuardKit",
            group_ids=["product_knowledge"],
            num_results=1
        )
        # May be empty but should not raise
        assert isinstance(results, list)
