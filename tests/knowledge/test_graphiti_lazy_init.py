"""
Tests for Graphiti client lazy initialization (TASK-FIX-GCW6, updated TASK-FIX-GTP1).

Tests the lazy-init behavior of get_graphiti() which auto-initializes
the factory from config when it hasn't been explicitly initialized.

Coverage Target: >=80%
Test Organization:
    - Lazy-init success path
    - Lazy-init when Neo4j unavailable (graceful degradation)
    - Factory reuse (no re-init)
    - Config loading integration
    - Async context handling
    - init_graphiti interaction with lazy-init flag
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional

import guardkit.knowledge.graphiti_client as graphiti_module
from guardkit.knowledge.graphiti_client import (
    GraphitiConfig,
    GraphitiClient,
    GraphitiClientFactory,
    init_graphiti,
    get_graphiti,
    _try_lazy_init,
)


# Patch target for load_graphiti_config — it's imported locally inside
# _try_lazy_init via `from guardkit.knowledge.config import load_graphiti_config`
CONFIG_PATCH = "guardkit.knowledge.config.load_graphiti_config"
CLIENT_PATCH = "guardkit.knowledge.graphiti_client.GraphitiClient"


def _make_settings(
    enabled=True,
    neo4j_uri="bolt://localhost:7687",
    neo4j_user="neo4j",
    neo4j_password="pass",
    timeout=30.0,
    project_id=None,
):
    """Create a mock GraphitiSettings."""
    s = MagicMock()
    s.enabled = enabled
    s.neo4j_uri = neo4j_uri
    s.neo4j_user = neo4j_user
    s.neo4j_password = neo4j_password
    s.timeout = timeout
    s.project_id = project_id
    return s


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset the module-level factory before and after each test."""
    graphiti_module._factory = None
    graphiti_module._factory_init_attempted = False
    yield
    graphiti_module._factory = None
    graphiti_module._factory_init_attempted = False


# ============================================================================
# Test: Lazy-Init Success Path
# ============================================================================


class TestLazyInitSuccess:
    """Tests for successful lazy initialization."""

    def test_get_graphiti_triggers_lazy_init_when_none(self):
        """
        Given factory is None and init not attempted
        When get_graphiti() is called
        Then _try_lazy_init is called to initialize.
        """
        with patch(
            "guardkit.knowledge.graphiti_client._try_lazy_init",
            return_value=None,
        ) as mock_lazy:
            result = get_graphiti()
            mock_lazy.assert_called_once()

    def test_get_graphiti_returns_initialized_client(self):
        """
        Given lazy-init succeeds
        When get_graphiti() is called
        Then returns the initialized GraphitiClient.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.enabled = True

        with patch(
            "guardkit.knowledge.graphiti_client._try_lazy_init",
            return_value=mock_client,
        ):
            result = get_graphiti()
            assert result is mock_client

    def test_lazy_init_creates_factory_from_config(self):
        """
        Given valid config from load_graphiti_config
        When _try_lazy_init is called
        Then creates factory with correct config values.
        """
        settings = _make_settings(
            neo4j_uri="bolt://test:7687",
            neo4j_user="testuser",
            neo4j_password="testpass",
            timeout=60.0,
            project_id="test-project",
        )

        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=True)

        with patch(CONFIG_PATCH, return_value=settings), \
             patch(CLIENT_PATCH, return_value=mock_client):
            result = _try_lazy_init()

        assert graphiti_module._factory is not None
        config = graphiti_module._factory.config
        assert config.neo4j_uri == "bolt://test:7687"
        assert config.neo4j_user == "testuser"
        assert config.neo4j_password == "testpass"
        assert config.timeout == 60.0
        assert config.project_id == "test-project"

    def test_lazy_init_sets_factory(self):
        """
        Given successful lazy-init
        When _try_lazy_init completes
        Then module-level _factory is set.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=True)

        with patch(CONFIG_PATCH, return_value=_make_settings()), \
             patch(CLIENT_PATCH, return_value=mock_client):
            result = _try_lazy_init()

        assert graphiti_module._factory is not None
        assert graphiti_module._factory_init_attempted is True


# ============================================================================
# Test: Lazy-Init Graceful Degradation
# ============================================================================


class TestLazyInitGracefulDegradation:
    """Tests for graceful degradation when Neo4j is unavailable."""

    def test_lazy_init_returns_none_when_disabled(self):
        """
        Given config has enabled=False
        When _try_lazy_init is called
        Then returns None without creating factory.
        """
        with patch(CONFIG_PATCH, return_value=_make_settings(enabled=False)):
            result = _try_lazy_init()

        assert result is None
        assert graphiti_module._factory_init_attempted is True

    def test_lazy_init_returns_none_when_initialize_fails(self):
        """
        Given client.initialize() returns False (Neo4j unavailable)
        When _try_lazy_init is called
        Then returns None.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=False)

        with patch(CONFIG_PATCH, return_value=_make_settings()), \
             patch(CLIENT_PATCH, return_value=mock_client):
            result = _try_lazy_init()

        assert result is None

    def test_lazy_init_returns_none_on_import_error(self):
        """
        Given load_graphiti_config raises ImportError
        When _try_lazy_init is called
        Then returns None with no crash.
        """
        with patch(CONFIG_PATCH, side_effect=ImportError("yaml not available")):
            result = _try_lazy_init()

        assert result is None
        assert graphiti_module._factory_init_attempted is True

    def test_lazy_init_returns_none_on_connection_error(self):
        """
        Given client.initialize() raises an exception
        When _try_lazy_init is called
        Then returns None gracefully.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(side_effect=ConnectionError("refused"))

        with patch(CONFIG_PATCH, return_value=_make_settings()), \
             patch(CLIENT_PATCH, return_value=mock_client):
            result = _try_lazy_init()

        assert result is None
        assert graphiti_module._factory_init_attempted is True


# ============================================================================
# Test: Factory Reuse (No Re-Init)
# ============================================================================


class TestSingletonReuse:
    """Tests for factory reuse behavior."""

    def test_get_graphiti_returns_client_from_existing_factory(self):
        """
        Given factory is already set
        When get_graphiti() is called
        Then returns client from factory without lazy-init.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_factory = MagicMock(spec=GraphitiClientFactory)
        mock_factory.get_thread_client.return_value = mock_client
        graphiti_module._factory = mock_factory

        with patch(
            "guardkit.knowledge.graphiti_client._try_lazy_init"
        ) as mock_lazy:
            result = get_graphiti()
            mock_lazy.assert_not_called()
            assert result is mock_client

    def test_lazy_init_not_reattempted_after_failure(self):
        """
        Given lazy-init already attempted and failed
        When get_graphiti() is called again
        Then returns None without re-attempting.
        """
        graphiti_module._factory_init_attempted = True
        graphiti_module._factory = None

        with patch(
            "guardkit.knowledge.graphiti_client._try_lazy_init"
        ) as mock_lazy:
            result = get_graphiti()
            mock_lazy.assert_not_called()
            assert result is None

    def test_second_get_graphiti_reuses_factory(self):
        """
        Given first get_graphiti() lazy-inits successfully
        When get_graphiti() is called again
        Then returns client from same factory without re-initializing.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_factory = MagicMock(spec=GraphitiClientFactory)
        mock_factory.get_thread_client.return_value = mock_client
        call_count = 0

        def mock_lazy():
            nonlocal call_count
            call_count += 1
            graphiti_module._factory = mock_factory
            return mock_client

        with patch(
            "guardkit.knowledge.graphiti_client._try_lazy_init",
            side_effect=mock_lazy,
        ):
            result1 = get_graphiti()

        # Second call should use cached factory
        result2 = get_graphiti()

        assert result1 is mock_client
        assert result2 is mock_client
        assert call_count == 1


# ============================================================================
# Test: init_graphiti Interaction with Lazy-Init Flag
# ============================================================================


class TestInitGraphitiInteraction:
    """Tests for init_graphiti() interaction with the lazy-init flag."""

    @pytest.mark.asyncio
    async def test_init_graphiti_sets_attempted_flag(self):
        """
        Given init_graphiti is called explicitly
        When initialization completes
        Then _factory_init_attempted is set to True.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=True)

        with patch(CLIENT_PATCH, return_value=mock_client):
            await init_graphiti()

        assert graphiti_module._factory_init_attempted is True

    @pytest.mark.asyncio
    async def test_init_graphiti_success_sets_factory(self):
        """
        Given init_graphiti succeeds
        When initialization completes
        Then factory is set and get_graphiti returns a client.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=True)

        with patch(CLIENT_PATCH, return_value=mock_client):
            result = await init_graphiti()

        assert result is True
        assert graphiti_module._factory is not None
        # get_graphiti should return the thread-local client
        client = get_graphiti()
        assert client is mock_client

    @pytest.mark.asyncio
    async def test_init_graphiti_failure_clears_factory(self):
        """
        Given init_graphiti fails (initialize returns False)
        When initialization completes
        Then factory is None.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=False)

        with patch(CLIENT_PATCH, return_value=mock_client):
            result = await init_graphiti()

        assert result is False
        assert graphiti_module._factory is None

    @pytest.mark.asyncio
    async def test_init_graphiti_prevents_subsequent_lazy_init(self):
        """
        Given init_graphiti was called (even if it failed)
        When get_graphiti() is called
        Then no lazy-init is attempted.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=False)

        with patch(CLIENT_PATCH, return_value=mock_client):
            await init_graphiti()

        assert graphiti_module._factory is None

        with patch(
            "guardkit.knowledge.graphiti_client._try_lazy_init"
        ) as mock_lazy:
            result = get_graphiti()
            mock_lazy.assert_not_called()
            assert result is None


# ============================================================================
# Test: Async Context Handling
# ============================================================================


class TestAsyncContextHandling:
    """Tests for async context detection in lazy-init."""

    def test_lazy_init_in_sync_context_uses_asyncio_run(self):
        """
        Given no running asyncio loop
        When _try_lazy_init is called
        Then uses asyncio.run() for initialization via factory.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=True)

        with patch(CONFIG_PATCH, return_value=_make_settings()), \
             patch(CLIENT_PATCH, return_value=mock_client):
            result = _try_lazy_init()

        assert result is mock_client
        mock_client.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_lazy_init_in_async_context_defers_connection(self):
        """
        Given running asyncio loop
        When _try_lazy_init is called
        Then creates client but defers connection.
        """
        mock_client = MagicMock(spec=GraphitiClient)

        with patch(CONFIG_PATCH, return_value=_make_settings()), \
             patch(CLIENT_PATCH, return_value=mock_client):
            result = _try_lazy_init()

        # Client created but initialize NOT called (deferred)
        assert result is mock_client
        mock_client.initialize.assert_not_called()


# ============================================================================
# Test: Autobuild Auto-Init Integration
# ============================================================================


class TestAutobuildAutoInitIntegration:
    """Tests that autobuild auto-init block works with lazy-init."""

    def test_auto_init_block_gets_client_from_lazy_init(self):
        """
        Given get_graphiti() was not explicitly initialized
        When autobuild auto-init block calls get_graphiti()
        Then lazy-init provides a working client via factory.
        """
        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.enabled = True
        mock_client.initialize = AsyncMock(return_value=True)

        with patch(CONFIG_PATCH, return_value=_make_settings()), \
             patch(CLIENT_PATCH, return_value=mock_client):
            client = get_graphiti()

        assert client is not None
        assert client.enabled is True
