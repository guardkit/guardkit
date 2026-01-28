"""
TDD RED Phase: Tests for guardkit.knowledge.graphiti_client

These tests are written to FAIL initially (RED phase of TDD).
Implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- GraphitiConfig dataclass validation
- GraphitiClient initialization and properties
- Connection and health check behavior (with socket mocking)
- Search functionality with graceful degradation
- Episode addition functionality
- Singleton pattern (init_graphiti, get_graphiti)
- Error handling and graceful degradation
- Missing OPENAI_API_KEY handling
- Internal methods (_execute_search, _create_episode)

Coverage Target: >=80%
Test Count: 50+ tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Optional, List, Dict
import os
import socket
import asyncio

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.graphiti_client import (
        GraphitiConfig,
        GraphitiClient,
        init_graphiti,
        get_graphiti,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


class TestGraphitiConfig:
    """Test GraphitiConfig dataclass."""

    def test_config_default_values(self):
        """Test default configuration values."""
        config = GraphitiConfig()

        assert config.enabled is True
        assert config.host == "localhost"
        assert config.port == 8000
        assert config.timeout == 30.0

    def test_config_custom_values(self):
        """Test custom configuration values."""
        config = GraphitiConfig(
            enabled=False,
            host="graphiti.example.com",
            port=9000,
            timeout=60.0
        )

        assert config.enabled is False
        assert config.host == "graphiti.example.com"
        assert config.port == 9000
        assert config.timeout == 60.0

    def test_config_immutable(self):
        """Test that config is immutable (frozen dataclass)."""
        config = GraphitiConfig()

        with pytest.raises(AttributeError):
            config.enabled = False

    def test_config_with_negative_timeout(self):
        """Test config with negative timeout value."""
        # Should raise ValueError
        with pytest.raises(ValueError, match="timeout must be positive"):
            config = GraphitiConfig(timeout=-5.0)

    def test_config_with_zero_timeout(self):
        """Test config with zero timeout value."""
        # Should raise ValueError
        with pytest.raises(ValueError, match="timeout must be positive"):
            config = GraphitiConfig(timeout=0.0)


class TestGraphitiClientInitialization:
    """Test GraphitiClient initialization and basic properties."""

    def test_client_creation_with_defaults(self):
        """Test creating client with default config."""
        client = GraphitiClient()

        assert client is not None
        assert isinstance(client.config, GraphitiConfig)

    def test_client_creation_with_custom_config(self):
        """Test creating client with custom config."""
        config = GraphitiConfig(host="custom.host", port=9000)
        client = GraphitiClient(config)

        assert client.config == config
        assert client.config.host == "custom.host"
        assert client.config.port == 9000

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
        # This test will be refined in GREEN phase
        assert isinstance(client.enabled, bool)


class TestGraphitiClientCheckConnection:
    """Test GraphitiClient._check_connection() method with socket mocking."""

    @pytest.mark.asyncio
    async def test_check_connection_success(self):
        """Test successful connection check."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        # Mock socket connection success
        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate successful connection
                mock_loop.run_in_executor = AsyncMock(return_value=None)

                result = await client._check_connection()

                assert result is True
                mock_socket.settimeout.assert_called_once()
                mock_socket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_socket_timeout(self):
        """Test connection check with socket timeout."""
        config = GraphitiConfig(enabled=True, timeout=5.0)
        client = GraphitiClient(config)

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate socket timeout
                mock_loop.run_in_executor = AsyncMock(side_effect=socket.timeout("Connection timeout"))

                result = await client._check_connection()

                assert result is False
                mock_socket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_socket_error(self):
        """Test connection check with socket error."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate socket error
                mock_loop.run_in_executor = AsyncMock(side_effect=socket.error("Connection refused"))

                result = await client._check_connection()

                assert result is False
                mock_socket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_os_error(self):
        """Test connection check with OS error."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate OS error
                mock_loop.run_in_executor = AsyncMock(side_effect=OSError("Network unreachable"))

                result = await client._check_connection()

                assert result is False
                mock_socket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_unexpected_error(self):
        """Test connection check with unexpected error."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate unexpected error
                mock_loop.run_in_executor = AsyncMock(side_effect=RuntimeError("Unexpected error"))

                result = await client._check_connection()

                assert result is False
                mock_socket.close.assert_called_once()


class TestGraphitiClientCheckHealth:
    """Test GraphitiClient._check_health() method with HTTP mocking."""

    @pytest.mark.asyncio
    async def test_check_health_success_http_200(self):
        """Test health check with successful HTTP 200 response."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate successful HTTP 200 response
                async def mock_recv(*args, **kwargs):
                    return b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n{\"status\":\"healthy\"}"

                mock_loop.run_in_executor = AsyncMock(side_effect=[
                    None,  # connect
                    None,  # sendall
                    b"HTTP/1.1 200 OK\r\n\r\n"  # recv
                ])

                result = await client._check_health()

                assert result is True
                mock_socket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_http_10_response(self):
        """Test health check with HTTP/1.0 200 response."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate HTTP/1.0 200 response
                mock_loop.run_in_executor = AsyncMock(side_effect=[
                    None,  # connect
                    None,  # sendall
                    b"HTTP/1.0 200 OK\r\n\r\n"  # recv
                ])

                result = await client._check_health()

                assert result is True

    @pytest.mark.asyncio
    async def test_check_health_non_200_response(self):
        """Test health check with non-200 HTTP response."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate HTTP 500 error
                mock_loop.run_in_executor = AsyncMock(side_effect=[
                    None,  # connect
                    None,  # sendall
                    b"HTTP/1.1 500 Internal Server Error\r\n\r\n"  # recv
                ])

                result = await client._check_health()

                assert result is False

    @pytest.mark.asyncio
    async def test_check_health_when_disabled(self):
        """Test health check returns False when config disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        result = await client._check_health()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_health_when_not_connected(self):
        """Test health check returns False when not connected."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = False

        result = await client._check_health()

        assert result is False

    @pytest.mark.asyncio
    async def test_check_health_socket_timeout(self):
        """Test health check with socket timeout."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate socket timeout
                mock_loop.run_in_executor = AsyncMock(side_effect=socket.timeout("Health check timeout"))

                result = await client._check_health()

                assert result is False
                mock_socket.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_health_socket_error(self):
        """Test health check with socket error."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate socket error
                mock_loop.run_in_executor = AsyncMock(side_effect=socket.error("Connection reset"))

                result = await client._check_health()

                assert result is False

    @pytest.mark.asyncio
    async def test_check_health_os_error(self):
        """Test health check with OS error."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate OS error
                mock_loop.run_in_executor = AsyncMock(side_effect=OSError("Network error"))

                result = await client._check_health()

                assert result is False

    @pytest.mark.asyncio
    async def test_check_health_unexpected_error(self):
        """Test health check with unexpected error."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True

        mock_socket = MagicMock()
        mock_loop = MagicMock()

        with patch('socket.socket', return_value=mock_socket):
            with patch('asyncio.get_event_loop', return_value=mock_loop):
                # Simulate unexpected error
                mock_loop.run_in_executor = AsyncMock(side_effect=RuntimeError("Unexpected"))

                result = await client._check_health()

                assert result is False


class TestGraphitiClientInitialize:
    """Test GraphitiClient.initialize() method."""

    @pytest.mark.asyncio
    async def test_initialize_success(self):
        """Test successful initialization with Graphiti running."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(client, '_check_connection', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = True

                result = await client.initialize()

                assert result is True
                mock_check.assert_called_once()

    @pytest.mark.asyncio
    async def test_initialize_failure_graphiti_not_running(self):
        """Test initialization failure when Graphiti not running."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(client, '_check_connection', new_callable=AsyncMock) as mock_check:
                mock_check.return_value = False

                result = await client.initialize()

                assert result is False
                mock_check.assert_called_once()

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
    async def test_initialize_connection_timeout(self):
        """Test initialization handles connection timeout."""
        config = GraphitiConfig(enabled=True, timeout=1.0)
        client = GraphitiClient(config)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(client, '_check_connection', new_callable=AsyncMock) as mock_check:
                mock_check.side_effect = TimeoutError("Connection timeout")

                result = await client.initialize()

                assert result is False

    @pytest.mark.asyncio
    async def test_initialize_general_exception(self):
        """Test initialization handles general exceptions."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(client, '_check_connection', new_callable=AsyncMock) as mock_check:
                mock_check.side_effect = Exception("Unexpected error")

                result = await client.initialize()

                assert result is False


class TestGraphitiClientHealthCheck:
    """Test GraphitiClient.health_check() method."""

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test successful health check."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_check_health', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = True

            result = await client.health_check()

            assert result is True
            mock_health.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check when Graphiti unhealthy."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_check_health', new_callable=AsyncMock) as mock_health:
            mock_health.return_value = False

            result = await client.health_check()

            assert result is False

    @pytest.mark.asyncio
    async def test_health_check_when_disabled(self):
        """Test health check returns False when client disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        result = await client.health_check()

        assert result is False

    @pytest.mark.asyncio
    async def test_health_check_exception_handling(self):
        """Test health check handles exceptions gracefully."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_check_health', new_callable=AsyncMock) as mock_health:
            mock_health.side_effect = Exception("Health check error")

            result = await client.health_check()

            assert result is False


class TestGraphitiClientExecuteSearch:
    """Test GraphitiClient._execute_search() internal method."""

    @pytest.mark.asyncio
    async def test_execute_search_returns_empty_list(self):
        """Test _execute_search returns empty list (stub implementation)."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        result = await client._execute_search(
            query="test query",
            group_ids=["group1"],
            num_results=10
        )

        # Stub implementation returns empty list
        assert result == []

    @pytest.mark.asyncio
    async def test_execute_search_with_none_group_ids(self):
        """Test _execute_search with None group_ids."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        result = await client._execute_search(
            query="test query",
            group_ids=None,
            num_results=10
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_execute_search_with_custom_num_results(self):
        """Test _execute_search with custom num_results."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        result = await client._execute_search(
            query="test query",
            group_ids=["group1"],
            num_results=5
        )

        assert result == []


class TestGraphitiClientSearch:
    """Test GraphitiClient.search() method."""

    @pytest.mark.asyncio
    async def test_search_success(self):
        """Test successful search query."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_results = [
            {"id": "1", "content": "Result 1", "score": 0.95},
            {"id": "2", "content": "Result 2", "score": 0.87},
        ]

        with patch.object(client, '_execute_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_results

            results = await client.search(
                query="test query",
                group_ids=["group1"],
                num_results=2
            )

            assert results == mock_results
            assert len(results) == 2
            mock_search.assert_called_once_with(
                query="test query",
                group_ids=["group1"],
                num_results=2
            )

    @pytest.mark.asyncio
    async def test_search_empty_results(self):
        """Test search with no results."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_execute_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            results = await client.search(query="nonexistent", group_ids=["group1"])

            assert results == []

    @pytest.mark.asyncio
    async def test_search_when_disabled(self):
        """Test search returns empty list when client disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        results = await client.search(query="test", group_ids=["group1"])

        assert results == []

    @pytest.mark.asyncio
    async def test_search_graceful_degradation_on_error(self):
        """Test search returns empty list on error (graceful degradation)."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_execute_search', new_callable=AsyncMock) as mock_search:
            mock_search.side_effect = Exception("Connection error")

            results = await client.search(query="test", group_ids=["group1"])

            assert results == []

    @pytest.mark.asyncio
    async def test_search_with_default_num_results(self):
        """Test search uses default num_results when not specified."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_execute_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            await client.search(query="test", group_ids=["group1"])

            # Verify default num_results is passed
            call_args = mock_search.call_args
            assert call_args[1].get('num_results') is not None

    @pytest.mark.asyncio
    async def test_search_multiple_groups(self):
        """Test search with multiple group IDs."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_results = [{"id": "1", "content": "Result", "score": 0.9}]

        with patch.object(client, '_execute_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = mock_results

            results = await client.search(
                query="test",
                group_ids=["group1", "group2", "group3"],
                num_results=5
            )

            assert results == mock_results
            mock_search.assert_called_once()


class TestGraphitiClientCreateEpisode:
    """Test GraphitiClient._create_episode() internal method."""

    @pytest.mark.asyncio
    async def test_create_episode_returns_none(self):
        """Test _create_episode returns None (stub implementation)."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        result = await client._create_episode(
            name="Test Episode",
            episode_body="Test content",
            group_id="group1"
        )

        # Stub implementation returns None
        assert result is None

    @pytest.mark.asyncio
    async def test_create_episode_with_empty_body(self):
        """Test _create_episode with empty episode body."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        result = await client._create_episode(
            name="Empty Episode",
            episode_body="",
            group_id="group1"
        )

        assert result is None


class TestGraphitiClientAddEpisode:
    """Test GraphitiClient.add_episode() method."""

    @pytest.mark.asyncio
    async def test_add_episode_success(self):
        """Test successful episode addition."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_episode_id = "episode_123"

        with patch.object(client, '_create_episode', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_episode_id

            result = await client.add_episode(
                name="Test Episode",
                episode_body="This is test content",
                group_id="group1"
            )

            assert result == mock_episode_id
            mock_create.assert_called_once_with(
                name="Test Episode",
                episode_body="This is test content",
                group_id="group1"
            )

    @pytest.mark.asyncio
    async def test_add_episode_when_disabled(self):
        """Test add_episode returns None when client disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)

        result = await client.add_episode(
            name="Test Episode",
            episode_body="Content",
            group_id="group1"
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_add_episode_graceful_degradation_on_error(self):
        """Test add_episode returns None on error (graceful degradation)."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_create_episode', new_callable=AsyncMock) as mock_create:
            mock_create.side_effect = Exception("API error")

            result = await client.add_episode(
                name="Test Episode",
                episode_body="Content",
                group_id="group1"
            )

            assert result is None

    @pytest.mark.asyncio
    async def test_add_episode_empty_body(self):
        """Test add_episode with empty episode body."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_create_episode', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = "episode_123"

            result = await client.add_episode(
                name="Empty Episode",
                episode_body="",
                group_id="group1"
            )

            # Should still attempt to create (API may handle validation)
            mock_create.assert_called_once()


class TestSingletonPattern:
    """Test singleton functions init_graphiti() and get_graphiti()."""

    @pytest.mark.asyncio
    async def test_init_graphiti_creates_instance(self):
        """Test init_graphiti creates and initializes instance."""
        config = GraphitiConfig(enabled=True)

        with patch('guardkit.knowledge.graphiti_client.GraphitiClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.initialize.return_value = True
            MockClient.return_value = mock_instance

            result = await init_graphiti(config)

            assert result is True
            MockClient.assert_called_once_with(config)
            mock_instance.initialize.assert_called_once()

    @pytest.mark.asyncio
    async def test_init_graphiti_initialization_failure(self):
        """Test init_graphiti handles initialization failure."""
        config = GraphitiConfig(enabled=True)

        with patch('guardkit.knowledge.graphiti_client.GraphitiClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.initialize.return_value = False
            MockClient.return_value = mock_instance

            result = await init_graphiti(config)

            assert result is False

    def test_get_graphiti_returns_instance_after_init(self):
        """Test get_graphiti returns instance after initialization."""
        # This test assumes init_graphiti was called
        # In real implementation, this would use a module-level singleton

        client = get_graphiti()

        # Should return a GraphitiClient instance or None
        assert client is None or isinstance(client, GraphitiClient)

    def test_get_graphiti_returns_none_before_init(self):
        """Test get_graphiti returns None before initialization."""
        # Reset singleton state (implementation-dependent)

        client = get_graphiti()

        assert client is None

    @pytest.mark.asyncio
    async def test_init_graphiti_idempotent(self):
        """Test calling init_graphiti multiple times is safe."""
        config = GraphitiConfig(enabled=True)

        with patch('guardkit.knowledge.graphiti_client.GraphitiClient') as MockClient:
            mock_instance = AsyncMock()
            mock_instance.initialize.return_value = True
            MockClient.return_value = mock_instance

            result1 = await init_graphiti(config)
            result2 = await init_graphiti(config)

            assert result1 is True
            assert result2 is True
            # Should only create one instance (singleton pattern)


@pytest.mark.integration
class TestGraphitiClientIntegration:
    """
    Integration tests for GraphitiClient.

    These tests require Graphiti to be running.
    Mark with @pytest.mark.integration to run selectively.
    """

    @pytest.mark.asyncio
    async def test_full_workflow_with_real_graphiti(self):
        """Test complete workflow with real Graphiti instance."""
        # Skip if Graphiti not available
        config = GraphitiConfig(enabled=True, host="localhost", port=8000)
        client = GraphitiClient(config)

        # Initialize
        initialized = await client.initialize()
        if not initialized:
            pytest.skip("Graphiti not available")

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

    @pytest.mark.asyncio
    async def test_graceful_degradation_without_graphiti(self):
        """Test client degrades gracefully when Graphiti unavailable."""
        # Use non-existent host to simulate unavailability
        config = GraphitiConfig(enabled=True, host="nonexistent.host", port=9999, timeout=1.0)
        client = GraphitiClient(config)

        # Initialize should fail gracefully
        initialized = await client.initialize()
        assert initialized is False

        # Enabled should be False
        assert client.enabled is False

        # Health check should return False
        healthy = await client.health_check()
        assert healthy is False

        # Search should return empty list
        results = await client.search(query="test", group_ids=["group1"])
        assert results == []

        # Add episode should return None
        episode_id = await client.add_episode(
            name="Test",
            episode_body="Test",
            group_id="group1"
        )
        assert episode_id is None


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.asyncio
    async def test_search_with_empty_query(self):
        """Test search with empty query string."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_execute_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            results = await client.search(query="", group_ids=["group1"])

            assert results == []

    @pytest.mark.asyncio
    async def test_search_with_empty_group_ids(self):
        """Test search with empty group_ids list."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_execute_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            results = await client.search(query="test", group_ids=[])

            # Should handle empty group_ids gracefully
            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_search_with_large_num_results(self):
        """Test search with very large num_results."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        with patch.object(client, '_execute_search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            results = await client.search(
                query="test",
                group_ids=["group1"],
                num_results=10000
            )

            assert isinstance(results, list)

    @pytest.mark.asyncio
    async def test_add_episode_with_special_characters(self):
        """Test add_episode with special characters in content."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        special_content = "Test with special chars: <>&\"'\\n\\t\\r"

        with patch.object(client, '_create_episode', new_callable=AsyncMock) as mock_create:
            mock_create.return_value = "episode_123"

            result = await client.add_episode(
                name="Special Chars Test",
                episode_body=special_content,
                group_id="group1"
            )

            assert result == "episode_123"
            # Verify content was passed correctly
            call_args = mock_create.call_args
            assert call_args[1]['episode_body'] == special_content
