"""
Tests for guardkit.knowledge.graphiti_client

These tests cover the graphiti-core library based implementation.

Test Coverage:
- GraphitiConfig dataclass validation
- GraphitiClient initialization and properties
- Connection initialization with graphiti-core
- Search functionality with graceful degradation
- Episode addition functionality
- Singleton pattern (init_graphiti, get_graphiti)
- Error handling and graceful degradation
- Missing OPENAI_API_KEY handling

Coverage Target: >=80%
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional, List
import os

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.graphiti_client import (
        GraphitiConfig,
        GraphitiClient,
        init_graphiti,
        get_graphiti,
        _check_graphiti_core,
    )
    import guardkit.knowledge.graphiti_client as graphiti_module
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False
    graphiti_module = None


# Skip all tests if imports not available
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created"
)


class TestGraphitiConfig:
    """Test GraphitiConfig dataclass."""

    def test_config_default_values(self):
        """Test default configuration values."""
        config = GraphitiConfig()

        assert config.enabled is True
        assert config.neo4j_uri == "bolt://localhost:7687"
        assert config.neo4j_user == "neo4j"
        assert config.neo4j_password == "password123"
        assert config.timeout == 30.0

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = GraphitiConfig(
            enabled=False,
            neo4j_uri="bolt://graphiti.example.com:7687",
            neo4j_user="custom_user",
            neo4j_password="custom_pass",
            timeout=60.0
        )

        assert config.enabled is False
        assert config.neo4j_uri == "bolt://graphiti.example.com:7687"
        assert config.neo4j_user == "custom_user"
        assert config.neo4j_password == "custom_pass"
        assert config.timeout == 60.0

    def test_config_immutable(self):
        """Test that config is immutable (frozen dataclass)."""
        config = GraphitiConfig()

        with pytest.raises(AttributeError):
            config.enabled = False

    def test_config_with_negative_timeout(self):
        """Test config with negative timeout value."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            GraphitiConfig(timeout=-5.0)

    def test_config_with_zero_timeout(self):
        """Test config with zero timeout value."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            GraphitiConfig(timeout=0.0)

    def test_config_backwards_compatibility_fields(self):
        """Test deprecated host/port fields still exist for backwards compatibility."""
        config = GraphitiConfig()

        # These fields should exist for backwards compatibility
        assert config.host == "localhost"
        assert config.port == 8000

    def test_config_default_provider_values(self):
        """Test default provider configuration values."""
        config = GraphitiConfig()

        assert config.llm_provider == "openai"
        assert config.llm_base_url is None
        assert config.llm_model is None
        assert config.embedding_provider == "openai"
        assert config.embedding_base_url is None
        assert config.embedding_model == "text-embedding-3-small"

    def test_config_vllm_provider_valid(self):
        """Test vllm provider with required base_url is accepted."""
        config = GraphitiConfig(
            llm_provider="vllm",
            llm_base_url="http://host:8000/v1",
            llm_model="Qwen/Qwen3-Coder-30B-A3B",
        )

        assert config.llm_provider == "vllm"
        assert config.llm_base_url == "http://host:8000/v1"
        assert config.llm_model == "Qwen/Qwen3-Coder-30B-A3B"

    def test_config_ollama_embedding_provider_valid(self):
        """Test ollama embedding provider with required base_url is accepted."""
        config = GraphitiConfig(
            embedding_provider="ollama",
            embedding_base_url="http://host:11434/v1",
            embedding_model="nomic-embed-text",
        )

        assert config.embedding_provider == "ollama"
        assert config.embedding_base_url == "http://host:11434/v1"
        assert config.embedding_model == "nomic-embed-text"

    def test_config_invalid_llm_provider(self):
        """Test invalid llm_provider raises ValueError."""
        with pytest.raises(ValueError, match="llm_provider must be one of"):
            GraphitiConfig(llm_provider="bedrock")

    def test_config_invalid_embedding_provider(self):
        """Test invalid embedding_provider raises ValueError."""
        with pytest.raises(ValueError, match="embedding_provider must be one of"):
            GraphitiConfig(embedding_provider="azure")

    def test_config_vllm_missing_base_url(self):
        """Test vllm provider without base_url raises ValueError."""
        with pytest.raises(ValueError, match="llm_base_url is required"):
            GraphitiConfig(llm_provider="vllm")

    def test_config_ollama_missing_embedding_base_url(self):
        """Test ollama embedding provider without base_url raises ValueError."""
        with pytest.raises(ValueError, match="embedding_base_url is required"):
            GraphitiConfig(embedding_provider="ollama")

    def test_config_provider_fields_immutable(self):
        """Test that new provider fields are immutable (frozen dataclass)."""
        config = GraphitiConfig()

        with pytest.raises(AttributeError):
            config.llm_provider = "vllm"
        with pytest.raises(AttributeError):
            config.embedding_provider = "vllm"
        with pytest.raises(AttributeError):
            config.embedding_model = "other-model"

    def test_config_both_providers_local(self):
        """Test both LLM and embedding providers set to local inference."""
        config = GraphitiConfig(
            llm_provider="vllm",
            llm_base_url="http://host:8000/v1",
            llm_model="Qwen/Qwen3-Coder-30B-A3B",
            embedding_provider="vllm",
            embedding_base_url="http://host:8001/v1",
            embedding_model="BAAI/bge-m3",
        )

        assert config.llm_provider == "vllm"
        assert config.embedding_provider == "vllm"
        assert config.llm_base_url == "http://host:8000/v1"
        assert config.embedding_base_url == "http://host:8001/v1"

    def test_config_openai_provider_no_base_url_required(self):
        """Test openai provider does not require base_url."""
        config = GraphitiConfig(llm_provider="openai")

        assert config.llm_provider == "openai"
        assert config.llm_base_url is None

    def test_config_default_max_concurrent_episodes(self):
        """Test that max_concurrent_episodes defaults to 3."""
        config = GraphitiConfig()
        assert config.max_concurrent_episodes == 3

    def test_config_custom_max_concurrent_episodes(self):
        """Test setting max_concurrent_episodes to a valid value."""
        config = GraphitiConfig(max_concurrent_episodes=5)
        assert config.max_concurrent_episodes == 5

    def test_config_max_concurrent_episodes_min_valid(self):
        """Test max_concurrent_episodes = 1 is valid (sequential mode)."""
        config = GraphitiConfig(max_concurrent_episodes=1)
        assert config.max_concurrent_episodes == 1

    def test_config_max_concurrent_episodes_zero_raises(self):
        """Test max_concurrent_episodes = 0 raises ValueError."""
        with pytest.raises(ValueError, match="max_concurrent_episodes must be >= 1"):
            GraphitiConfig(max_concurrent_episodes=0)

    def test_config_max_concurrent_episodes_bool_raises(self):
        """Test max_concurrent_episodes = True raises TypeError (bool is subclass of int)."""
        with pytest.raises(TypeError, match="max_concurrent_episodes must be int"):
            GraphitiConfig(max_concurrent_episodes=True)

    def test_config_is_transient_error_rate_limit(self):
        """_is_transient_error returns True for rate limit errors."""
        client = GraphitiClient()

        assert client._is_transient_error(Exception("Rate limit exceeded"))
        assert client._is_transient_error(Exception("rate_limit"))
        assert client._is_transient_error(Exception("HTTP 429 Too Many Requests"))
        assert client._is_transient_error(Exception("Too Many Requests"))

    def test_config_is_transient_error_connection(self):
        """_is_transient_error returns True for connection errors."""
        client = GraphitiClient()

        assert client._is_transient_error(Exception("Connection refused"))
        assert client._is_transient_error(Exception("Max pending queries exceeded"))
        assert client._is_transient_error(Exception("Timed out waiting for response"))

    def test_config_is_transient_error_non_transient(self):
        """_is_transient_error returns False for non-transient errors."""
        client = GraphitiClient()

        assert not client._is_transient_error(Exception("Syntax error in query"))
        assert not client._is_transient_error(Exception("Authentication failed"))
        assert not client._is_transient_error(Exception("Schema validation error"))


class TestGraphitiClientInitialization:
    """Test GraphitiClient initialization and basic properties."""

    def test_client_creation_with_defaults(self):
        """Test creating client with default config."""
        client = GraphitiClient()

        assert client is not None
        assert isinstance(client.config, GraphitiConfig)

    def test_client_creation_with_custom_config(self):
        """Test creating client with custom config."""
        config = GraphitiConfig(neo4j_uri="bolt://custom.host:7687", neo4j_user="admin")
        client = GraphitiClient(config)

        assert client.config == config
        assert client.config.neo4j_uri == "bolt://custom.host:7687"
        assert client.config.neo4j_user == "admin"

    def test_enabled_property_when_disabled_in_config(self):
        """Test enabled property returns False when disabled in config."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        assert client.enabled is False

    def test_enabled_property_when_enabled_in_config(self):
        """Test enabled property returns True when enabled in config."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        # Note: actual enabled status may depend on connection
        assert isinstance(client.enabled, bool)

    def test_client_initial_state(self):
        """Test client initial state before initialization."""
        client = GraphitiClient()

        assert client._graphiti is None
        assert client._connected is False


class TestGraphitiClientInitialize:
    """Test GraphitiClient.initialize() method."""

    @pytest.mark.asyncio
    async def test_initialize_when_disabled_in_config(self):
        """Test initialization returns False when disabled in config."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        result = await client.initialize()

        assert result is False

    @pytest.mark.asyncio
    async def test_initialize_missing_openai_api_key(self):
        """Test initialization fails gracefully without OPENAI_API_KEY."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.dict(os.environ, {}, clear=True):
            # OPENAI_API_KEY not set
            result = await client.initialize()

            assert result is False

    @pytest.mark.asyncio
    async def test_initialize_graphiti_core_not_available(self):
        """Test initialization fails gracefully when graphiti-core not installed."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch('guardkit.knowledge.graphiti_client._check_graphiti_core', return_value=False):
                result = await client.initialize()

                assert result is False

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization with graphiti-core."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        # Set up mock modules for both graphiti_core and graphiti_core.nodes
        mock_graphiti_module = MagicMock(Graphiti=mock_graphiti_class)
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            # Set up the module mocks before calling initialize
            # Also patch apply_falkordb_workaround since _check_graphiti_core()
            # calls it after importing graphiti_core, and the mocked module
            # causes inspect.getsource() to fail with TypeError
            with patch.dict('sys.modules', {
                'graphiti_core': mock_graphiti_module,
                'graphiti_core.nodes': mock_nodes_module
            }), patch(
                'guardkit.knowledge.falkordb_workaround.apply_falkordb_workaround',
                return_value=True,
            ):
                # Reset the global check flag to force re-check
                original = graphiti_module._graphiti_core_available
                graphiti_module._graphiti_core_available = None
                try:
                    result = await client.initialize()

                    assert result is True
                    assert client._connected is True
                    mock_graphiti_instance.build_indices_and_constraints.assert_called_once()
                finally:
                    graphiti_module._graphiti_core_available = original

    @pytest.mark.asyncio
    async def test_initialize_connection_failure(self):
        """Test initialization handles connection failure."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            # Reset and set graphiti-core as available
            graphiti_module._graphiti_core_available = None

            mock_graphiti_class = MagicMock(side_effect=Exception("Connection failed"))
            mock_module = MagicMock(Graphiti=mock_graphiti_class)
            with patch.dict('sys.modules', {'graphiti_core': mock_module}), \
                 patch('guardkit.knowledge.falkordb_workaround.apply_falkordb_workaround',
                       return_value=True):
                result = await client.initialize()

                assert result is False
                assert client._connected is False

    @pytest.mark.asyncio
    async def test_initialize_general_exception(self):
        """Test initialization handles general exceptions when check fails."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            # Force the graphiti-core check to fail
            graphiti_module._graphiti_core_available = False
            result = await client.initialize()
            graphiti_module._graphiti_core_available = None  # Reset

            assert result is False


class TestGraphitiClientHealthCheck:
    """Test GraphitiClient.health_check() method."""

    @pytest.mark.asyncio
    async def test_health_check_when_disabled(self):
        """Test health check returns False when client disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_when_not_connected(self):
        """Test health check returns False when not connected."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = False

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        result = await client.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self):
        """Test health check handles exceptions gracefully."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True
        client._graphiti = None  # Will cause _check_health to return False

        # Should not raise, should return False (graphiti is None)
        result = await client.health_check()

        # _check_health returns False when _graphiti is None
        assert result is False


class TestGraphitiClientSearch:
    """Test GraphitiClient.search() method."""

    @pytest.mark.asyncio
    async def test_search_when_disabled(self):
        """Test search returns empty list when client disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        results = await client.search(query="test", group_ids=["role_constraints"])

        assert results == []

    @pytest.mark.asyncio
    async def test_search_when_not_initialized(self):
        """Test search returns empty list when not initialized."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._graphiti = None

        results = await client.search(query="test", group_ids=["role_constraints"])

        assert results == []

    @pytest.mark.asyncio
    async def test_search_success(self):
        """Test successful search query."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        # Mock edge results
        mock_edge1 = MagicMock()
        mock_edge1.fact = "Test fact 1"
        mock_edge1.uuid = "uuid-1"

        mock_edge2 = MagicMock()
        mock_edge2.fact = "Test fact 2"
        mock_edge2.uuid = "uuid-2"

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[mock_edge1, mock_edge2])
        client._graphiti = mock_graphiti

        # Use system group to avoid project_id requirement
        results = await client.search(
            query="test query",
            group_ids=["role_constraints"],
            num_results=10
        )

        assert len(results) == 2
        assert results[0]["fact"] == "Test fact 1"
        assert results[0]["uuid"] == "uuid-1"
        assert results[1]["fact"] == "Test fact 2"
        # Verify search was called with correct parameters (system group stays unprefixed)
        mock_graphiti.search.assert_called_once_with("test query", group_ids=["role_constraints"], num_results=10)

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with no results."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Use system group to avoid project_id requirement
        results = await client.search(query="nonexistent", group_ids=["role_constraints"])

        assert results == []

    @pytest.mark.asyncio
    async def test_search_graceful_degradation_on_error(self):
        """Test search returns empty list on error (graceful degradation)."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(side_effect=Exception("Search error"))
        client._graphiti = mock_graphiti

        # Use system group to avoid project_id requirement
        results = await client.search(query="test", group_ids=["role_constraints"])

        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_default_num_results(self):
        """Test search uses default num_results when not specified."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Use system group to avoid project_id requirement
        await client.search(query="test", group_ids=["role_constraints"])

        # Verify default num_results (10) is passed along with group_ids (system group stays unprefixed)
        mock_graphiti.search.assert_called_once_with("test", group_ids=["role_constraints"], num_results=10)

    @pytest.mark.asyncio
    async def test_search_with_custom_num_results(self):
        """Test search with custom num_results."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Use system group to avoid project_id requirement
        await client.search(query="test", group_ids=["role_constraints"], num_results=5)

        # System group stays unprefixed
        mock_graphiti.search.assert_called_once_with("test", group_ids=["role_constraints"], num_results=5)


class TestGraphitiClientAddEpisode:
    """Test GraphitiClient.add_episode() method."""

    @pytest.mark.asyncio
    async def test_add_episode_when_disabled(self):
        """Test add_episode returns None when client disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        # Use system group to avoid project_id requirement
        result = await client.add_episode(
            name="Test Episode",
            episode_body="Content",
            group_id="role_constraints"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_add_episode_when_not_initialized(self):
        """Test add_episode returns None when not initialized."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._graphiti = None

        # Use system group to avoid project_id requirement
        result = await client.add_episode(
            name="Test Episode",
            episode_body="Content",
            group_id="role_constraints"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_add_episode_success(self):
        """Test successful episode addition."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid-123"

        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        # Mock the EpisodeType import inside _create_episode
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}):
            # Use system group to avoid project_id requirement
            result = await client.add_episode(
                name="Test Episode",
                episode_body="This is test content",
                group_id="role_constraints"
            )

            assert result == "episode-uuid-123"
            mock_graphiti.add_episode.assert_called_once()
            call_kwargs = mock_graphiti.add_episode.call_args[1]
            assert call_kwargs['name'] == "Test Episode"
            # Content includes original text plus auto-generated metadata
            assert "This is test content" in call_kwargs['episode_body']
            assert "_metadata" in call_kwargs['episode_body']
            # System group stays unprefixed
            assert call_kwargs['group_id'] == "role_constraints"

    @pytest.mark.asyncio
    async def test_add_episode_timeout(self):
        """Test add_episode returns None on timeout and records circuit breaker failure."""
        import asyncio as _asyncio

        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        # Create a coroutine that never completes
        async def hang_forever(**kwargs):
            await _asyncio.sleep(9999)

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = hang_forever
        client._graphiti = mock_graphiti

        # Mock the EpisodeType import
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        # Patch wait_for to use a very short timeout so the test is fast
        original_wait_for = _asyncio.wait_for

        async def fast_wait_for(coro, *, timeout):
            return await original_wait_for(coro, timeout=0.01)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}), \
             patch('guardkit.knowledge.graphiti_client.asyncio.wait_for', side_effect=fast_wait_for):
            initial_failures = client._consecutive_failures

            result = await client.add_episode(
                name="Slow Episode",
                episode_body="Content",
                group_id="role_constraints"
            )

            assert result is None
            assert client._consecutive_failures == initial_failures + 1

    @pytest.mark.asyncio
    async def test_add_episode_timeout_no_retry(self):
        """Test that timed-out episodes are not retried."""
        import asyncio as _asyncio

        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        call_count = 0

        async def hang_and_count(**kwargs):
            nonlocal call_count
            call_count += 1
            await _asyncio.sleep(9999)

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = hang_and_count
        client._graphiti = mock_graphiti

        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        original_wait_for = _asyncio.wait_for

        async def fast_wait_for(coro, *, timeout):
            return await original_wait_for(coro, timeout=0.01)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}), \
             patch('guardkit.knowledge.graphiti_client.asyncio.wait_for', side_effect=fast_wait_for):
            result = await client.add_episode(
                name="Slow Episode",
                episode_body="Content",
                group_id="role_constraints"
            )

            assert result is None
            # Only called once - timeout is not retried
            assert call_count == 1

    @pytest.mark.asyncio
    async def test_add_episode_group_specific_timeouts(self):
        """Test that different groups use appropriate tiered timeouts."""
        import asyncio as _asyncio

        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        captured_timeouts = []
        original_wait_for = _asyncio.wait_for

        async def capturing_wait_for(coro, *, timeout):
            captured_timeouts.append(timeout)
            return await original_wait_for(coro, timeout=timeout)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}), \
             patch('guardkit.knowledge.graphiti_client.asyncio.wait_for', side_effect=capturing_wait_for):
            # project_overview (endswith check) should use 300s
            await client._create_episode(
                name="Project Purpose",
                episode_body="Content",
                group_id="myproject__project_overview"
            )
            assert captured_timeouts[-1] == 300.0

            # rules group should use 180s
            captured_timeouts.clear()
            await client._create_episode(
                name="Code Style Rule",
                episode_body="Content",
                group_id="rules"
            )
            assert captured_timeouts[-1] == 180.0

            # role_constraints group should use 150s
            captured_timeouts.clear()
            await client._create_episode(
                name="Role Constraint",
                episode_body="Content",
                group_id="role_constraints"
            )
            assert captured_timeouts[-1] == 150.0

            # agents group should use 150s
            captured_timeouts.clear()
            await client._create_episode(
                name="Agent Specialist",
                episode_body="Content",
                group_id="agents"
            )
            assert captured_timeouts[-1] == 150.0

            # templates group should use 180s
            captured_timeouts.clear()
            await client._create_episode(
                name="Template Item",
                episode_body="Content",
                group_id="templates"
            )
            assert captured_timeouts[-1] == 180.0

            # Other groups should use 120s default
            captured_timeouts.clear()
            await client._create_episode(
                name="Implementation Mode",
                episode_body="Content",
                group_id="implementation_modes"
            )
            assert captured_timeouts[-1] == 120.0

    @pytest.mark.asyncio
    async def test_timeout_tier_rules_per_template_group_id(self):
        """Test that per-template rules group_ids get 180s timeout (TASK-FIX-7595).

        After TASK-SPR-18fc, seed_rules uses per-template group_ids like
        'guardkit__rules_fastapi_python' instead of bare 'rules'.
        These must still match the 180s timeout tier.
        """
        import asyncio as _asyncio

        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        captured_timeouts = []
        original_wait_for = _asyncio.wait_for

        async def capturing_wait_for(coro, *, timeout):
            captured_timeouts.append(timeout)
            return await original_wait_for(coro, timeout=timeout)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}), \
             patch('guardkit.knowledge.graphiti_client.asyncio.wait_for', side_effect=capturing_wait_for):
            # Prefixed per-template group_id (after _apply_group_prefix)
            await client._create_episode(
                name="Rule Episode",
                episode_body="Content",
                group_id="guardkit__rules_fastapi_python"
            )
            assert captured_timeouts[-1] == 180.0

            # Unprefixed per-template group_id (before _apply_group_prefix)
            captured_timeouts.clear()
            await client._create_episode(
                name="Rule Episode",
                episode_body="Content",
                group_id="rules_react_typescript"
            )
            assert captured_timeouts[-1] == 180.0

    @pytest.mark.asyncio
    async def test_timeout_tier_rules_bare_group_id(self):
        """Regression guard: bare 'rules' group_id still gets 180s (TASK-FIX-7595)."""
        import asyncio as _asyncio

        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        captured_timeouts = []
        original_wait_for = _asyncio.wait_for

        async def capturing_wait_for(coro, *, timeout):
            captured_timeouts.append(timeout)
            return await original_wait_for(coro, timeout=timeout)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}), \
             patch('guardkit.knowledge.graphiti_client.asyncio.wait_for', side_effect=capturing_wait_for):
            await client._create_episode(
                name="Rule Episode",
                episode_body="Content",
                group_id="rules"
            )
            assert captured_timeouts[-1] == 180.0

    @pytest.mark.asyncio
    async def test_add_episode_graceful_degradation_on_error(self):
        """Test add_episode returns None on error (graceful degradation)."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(side_effect=Exception("API error"))
        client._graphiti = mock_graphiti

        # Mock the EpisodeType import
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}):
            # Use system group to avoid project_id requirement
            result = await client.add_episode(
                name="Test Episode",
                episode_body="Content",
                group_id="role_constraints"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_add_episode_returns_none_when_no_result(self):
        """Test add_episode returns None when add_episode returns None."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=None)
        client._graphiti = mock_graphiti

        # Mock the EpisodeType import
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}):
            # Use system group to avoid project_id requirement
            result = await client.add_episode(
                name="Test Episode",
                episode_body="Content",
                group_id="role_constraints"
            )

            assert result is None


class TestGraphitiClientClose:
    """Test GraphitiClient.close() method."""

    @pytest.mark.asyncio
    async def test_close_when_not_initialized(self):
        """Test close is safe when not initialized."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._graphiti = None

        # Should not raise
        await client.close()

    @pytest.mark.asyncio
    async def test_close_success(self):
        """Test successful close."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.close = AsyncMock()
        client._graphiti = mock_graphiti

        await client.close()

        mock_graphiti.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_handles_exception(self):
        """Test close handles exceptions gracefully."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.close = AsyncMock(side_effect=Exception("Close error"))
        client._graphiti = mock_graphiti

        # Should not raise
        await client.close()


class TestSingletonPattern:
    """Test factory functions init_graphiti() and get_graphiti()."""

    @pytest.fixture(autouse=True)
    def reset_factory(self):
        """Reset module-level factory before/after each test."""
        original_factory = graphiti_module._factory
        original_attempted = graphiti_module._factory_init_attempted
        graphiti_module._factory = None
        graphiti_module._factory_init_attempted = False
        yield
        graphiti_module._factory = original_factory
        graphiti_module._factory_init_attempted = original_attempted

    @pytest.mark.asyncio
    async def test_init_graphiti_creates_factory(self):
        """Test init_graphiti creates factory and initializes thread client."""
        config = GraphitiConfig(enabled=True)

        with patch.object(graphiti_module, 'GraphitiClient') as MockClient:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=True)
            MockClient.return_value = mock_instance

            result = await init_graphiti(config)

            assert result is True
            assert graphiti_module._factory is not None
            assert graphiti_module._factory_init_attempted is True

    @pytest.mark.asyncio
    async def test_init_graphiti_initialization_failure(self):
        """Test init_graphiti handles initialization failure."""
        config = GraphitiConfig(enabled=True)

        with patch.object(graphiti_module, 'GraphitiClient') as MockClient:
            mock_instance = MagicMock()
            mock_instance.initialize = AsyncMock(return_value=False)
            MockClient.return_value = mock_instance

            result = await init_graphiti(config)
            assert result is False
            assert graphiti_module._factory is None

    def test_get_graphiti_returns_none_before_init(self):
        """Test get_graphiti returns None when factory not set and lazy-init skipped."""
        graphiti_module._factory_init_attempted = True
        client = get_graphiti()
        assert client is None

    def test_get_graphiti_returns_instance_after_init(self):
        """Test get_graphiti returns instance via factory."""
        from guardkit.knowledge.graphiti_client import GraphitiClientFactory

        mock_client = MagicMock(spec=GraphitiClient)
        mock_factory = MagicMock(spec=GraphitiClientFactory)
        mock_factory.get_thread_client.return_value = mock_client

        graphiti_module._factory = mock_factory
        client = get_graphiti()
        assert client is mock_client
        mock_factory.get_thread_client.assert_called_once()


class TestCheckGraphitiCore:
    """Test _check_graphiti_core() helper function."""

    def test_check_graphiti_core_available(self):
        """Test returns True when graphiti-core is available."""
        # Reset the cached value
        original = graphiti_module._graphiti_core_available
        graphiti_module._graphiti_core_available = None

        mock_graphiti = MagicMock()
        mock_episode_type = MagicMock()
        mock_nodes = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {
            'graphiti_core': mock_graphiti,
            'graphiti_core.nodes': mock_nodes
        }), patch(
            'guardkit.knowledge.falkordb_workaround.apply_falkordb_workaround',
            return_value=True,
        ):
            try:
                result = _check_graphiti_core()
                assert result is True
            finally:
                graphiti_module._graphiti_core_available = original

    def test_check_graphiti_core_not_available(self):
        """Test returns False when graphiti-core is not available."""
        # Force the cached value to False
        original = graphiti_module._graphiti_core_available
        graphiti_module._graphiti_core_available = False
        try:
            result = _check_graphiti_core()
            assert result is False
        finally:
            graphiti_module._graphiti_core_available = original


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self):
        """Test search with empty query string."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Use system group to avoid project_id requirement
        results = await client.search(query="", group_ids=["role_constraints"])

        assert results == []

    @pytest.mark.asyncio
    async def test_search_with_none_group_ids(self):
        """Test search with None group_ids."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        results = await client.search(query="test", group_ids=None)

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_empty_group_ids(self):
        """Test search with empty group_ids list."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        results = await client.search(query="test", group_ids=[])

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_large_num_results(self):
        """Test search with very large num_results."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti = MagicMock()
        mock_graphiti.search = AsyncMock(return_value=[])
        client._graphiti = mock_graphiti

        # Use system group to avoid project_id requirement
        results = await client.search(
            query="test",
            group_ids=["role_constraints"],
            num_results=10000
        )

        assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_add_episode_with_special_characters(self):
        """Test add_episode with special characters in content."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        special_content = "Test with special chars: <>&\"'\\n\\t\\r"

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        # Mock the EpisodeType import
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}):
            # Use system group to avoid project_id requirement
            result = await client.add_episode(
                name="Special Chars Test",
                episode_body=special_content,
                group_id="role_constraints"
            )

            assert result == "episode-uuid"
            # Verify content was passed correctly (includes original + metadata)
            call_kwargs = mock_graphiti.add_episode.call_args[1]
            assert special_content in call_kwargs['episode_body']
            assert "_metadata" in call_kwargs['episode_body']

    @pytest.mark.asyncio
    async def test_add_episode_with_empty_body(self):
        """Test add_episode with empty episode body."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = MagicMock()
        mock_graphiti.add_episode = AsyncMock(return_value=mock_result)
        client._graphiti = mock_graphiti

        # Mock the EpisodeType import
        mock_episode_type = MagicMock()
        mock_episode_type.text = "text"
        mock_nodes_module = MagicMock(EpisodeType=mock_episode_type)

        with patch.dict('sys.modules', {'graphiti_core.nodes': mock_nodes_module}):
            # Use system group to avoid project_id requirement
            result = await client.add_episode(
                name="Empty Episode",
                episode_body="",
                group_id="role_constraints"
            )

            # Should still attempt to create
            mock_graphiti.add_episode.assert_called_once()


@pytest.mark.integration
class TestGraphitiClientIntegration:
    """
    Integration tests for GraphitiClient.

    These tests require Neo4j to be running.
    Mark with @pytest.mark.integration to run selectively.
    """

    @pytest.mark.asyncio
    async def test_full_workflow_with_real_neo4j(self):
        """Test complete workflow with real Neo4j instance."""
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://localhost:7687",
            neo4j_user="neo4j",
            neo4j_password="password123"
        )
        client = GraphitiClient(config)

        # Initialize
        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Neo4j or graphiti-core not available")

        try:
            # Health check
            healthy = await client.health_check()
            assert healthy is True

            # Add episode
            episode_id = await client.add_episode(
                name="Integration Test Episode",
                episode_body="This is a test episode for integration testing",
                group_id="test_group"
            )
            assert episode_id is not None

            # Search for episode
            results = await client.search(
                query="integration testing",
                group_ids=["test_group"],
                num_results=5
            )
            assert isinstance(results, list)
        finally:
            await client.close()

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_neo4j(self):
        """Test client degrades gracefully when Neo4j unavailable."""
        # Use non-existent host to simulate unavailability
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://nonexistent.host:7687",
            timeout=1.0
        )
        client = GraphitiClient(config)

        # Initialize should fail gracefully
        initialized = await client.initialize()
        assert initialized is False

        # Enabled should be False (disabled after failed init)
        assert client.enabled is False

        # Health check should return False
        healthy = await client.health_check()
        assert healthy is False

        # Search should return empty list (use system group to avoid project_id requirement)
        results = await client.search(query="test", group_ids=["role_constraints"])
        assert results == []

        # Add episode should return None (use system group to avoid project_id requirement)
        episode_id = await client.add_episode(
            name="Test",
            episode_body="Test",
            group_id="role_constraints"
        )
        assert episode_id is None


# ============================================================================
# Circuit Breaker Reset Tests (TASK-SPR-5399)
# ============================================================================

class TestCircuitBreakerReset:
    """Test reset_circuit_breaker() method prevents cascade between categories."""

    def test_reset_clears_tripped_state(self):
        """Test reset_circuit_breaker clears tripped flag."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config, auto_detect_project=False)
        client._connected = True

        # Trip the circuit breaker
        client._circuit_breaker_tripped = True
        client._consecutive_failures = 3
        client._circuit_breaker_tripped_at = 12345.0

        # Reset
        client.reset_circuit_breaker()

        assert client._circuit_breaker_tripped is False
        assert client._consecutive_failures == 0
        assert client._circuit_breaker_tripped_at is None

    def test_reset_when_not_tripped_is_noop(self):
        """Test reset_circuit_breaker is safe when breaker is not tripped."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config, auto_detect_project=False)
        client._connected = True

        # Not tripped, 1 failure recorded
        client._consecutive_failures = 1

        client.reset_circuit_breaker()

        assert client._circuit_breaker_tripped is False
        assert client._consecutive_failures == 0
        assert client._circuit_breaker_tripped_at is None

    def test_is_healthy_after_reset(self):
        """Test client reports healthy after circuit breaker reset."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config, auto_detect_project=False)
        client._connected = True

        # Trip it
        for _ in range(3):
            client._record_failure()
        assert client.is_healthy is False

        # Reset
        client.reset_circuit_breaker()
        assert client.is_healthy is True

    def test_circuit_breaker_still_protects_within_category(self):
        """Test circuit breaker still trips after 3 failures (no regression)."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config, auto_detect_project=False)
        client._connected = True

        # Record 3 consecutive failures
        client._record_failure()
        client._record_failure()
        client._record_failure()

        assert client._circuit_breaker_tripped is True
        assert client.is_healthy is False

    def test_reset_between_categories_prevents_cascade(self):
        """Test reset between operations prevents failure cascade."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config, auto_detect_project=False)
        client._connected = True

        # Category 1: trip the breaker
        for _ in range(3):
            client._record_failure()
        assert client.is_healthy is False

        # Reset before category 2
        client.reset_circuit_breaker()
        assert client.is_healthy is True

        # Category 2: 1 failure should NOT trip breaker
        client._record_failure()
        assert client.is_healthy is True
        assert client._consecutive_failures == 1
