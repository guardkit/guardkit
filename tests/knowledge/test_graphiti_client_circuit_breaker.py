"""
Tests for GraphitiClient circuit breaker pattern (TASK-ACR-008).

Tests the circuit breaker implementation that prevents cascade failures
by disabling the client after consecutive failures.

Test Coverage:
- Circuit breaker state initialization
- is_healthy property with circuit breaker status
- _record_success() and _record_failure() methods
- Circuit breaker triggering after max failures
- Search operations with circuit breaker
- Episode creation with circuit breaker
- episode_exists with circuit breaker
- _check_health with circuit breaker

Coverage Target: >=90%
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock

try:
    from guardkit.knowledge.graphiti_client import (
        GraphitiConfig,
        GraphitiClient,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created"
)


class TestCircuitBreakerInitialization:
    """Test circuit breaker state initialization."""

    def test_circuit_breaker_state_initialized(self):
        """Test that circuit breaker state is initialized correctly."""
        client = GraphitiClient()

        assert hasattr(client, '_consecutive_failures')
        assert hasattr(client, '_circuit_breaker_tripped')
        assert hasattr(client, '_max_failures')

        assert client._consecutive_failures == 0
        assert client._circuit_breaker_tripped is False
        assert client._max_failures == 3


class TestIsHealthyProperty:
    """Test is_healthy property."""

    def test_is_healthy_when_enabled_connected_and_breaker_not_tripped(self):
        """Test is_healthy returns True when all conditions met."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True
        client._circuit_breaker_tripped = False

        assert client.is_healthy is True

    def test_is_healthy_when_disabled(self):
        """Test is_healthy returns False when client disabled."""
        config = GraphitiConfig(enabled=False)
        client = GraphitiClient(config)
        client._connected = True
        client._circuit_breaker_tripped = False

        assert client.is_healthy is False

    def test_is_healthy_when_not_connected(self):
        """Test is_healthy returns False when not connected."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = False
        client._circuit_breaker_tripped = False

        assert client.is_healthy is False

    def test_is_healthy_when_circuit_breaker_tripped(self):
        """Test is_healthy returns False when circuit breaker tripped."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True
        client._circuit_breaker_tripped = True

        assert client.is_healthy is False

    def test_enabled_property_unaffected_by_circuit_breaker(self):
        """Test that enabled property doesn't check circuit breaker."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True
        client._circuit_breaker_tripped = True

        # enabled property should still be True (doesn't check circuit breaker)
        assert client.enabled is True
        # but is_healthy should be False
        assert client.is_healthy is False


class TestRecordSuccessAndFailure:
    """Test _record_success() and _record_failure() methods."""

    def test_record_success_resets_consecutive_failures(self):
        """Test that _record_success() resets consecutive failures counter."""
        client = GraphitiClient()
        client._consecutive_failures = 2

        client._record_success()

        assert client._consecutive_failures == 0

    def test_record_failure_increments_counter(self):
        """Test that _record_failure() increments consecutive failures."""
        client = GraphitiClient()
        client._consecutive_failures = 0

        client._record_failure()

        assert client._consecutive_failures == 1

    def test_record_failure_trips_breaker_at_max(self):
        """Test that circuit breaker trips at max failures."""
        client = GraphitiClient()
        client._consecutive_failures = 2  # One away from max

        client._record_failure()  # This should trip the breaker

        assert client._consecutive_failures == 3
        assert client._circuit_breaker_tripped is True

    def test_record_failure_logs_warning_when_tripping(self, caplog):
        """Test that warning is logged when circuit breaker trips."""
        client = GraphitiClient()
        client._consecutive_failures = 2

        with caplog.at_level("WARNING"):
            client._record_failure()

        assert "Graphiti disabled after 3 consecutive failures" in caplog.text
        assert "continuing without knowledge graph context" in caplog.text


class TestSearchWithCircuitBreaker:
    """Test search operations with circuit breaker."""

    @pytest.mark.asyncio
    async def test_execute_search_returns_empty_when_breaker_tripped(self):
        """Test that _execute_search returns empty list when circuit breaker tripped."""
        client = GraphitiClient()
        client._circuit_breaker_tripped = True
        client._graphiti = MagicMock()  # Mock as initialized

        results = await client._execute_search("test query")

        assert results == []
        # Should not have called _graphiti.search
        client._graphiti.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_search_records_success_on_successful_search(self):
        """Test that _execute_search records success on successful operation."""
        client = GraphitiClient()
        client._consecutive_failures = 2  # Pre-existing failures

        # Mock successful search
        mock_edge = MagicMock()
        mock_edge.uuid = "test-uuid"
        mock_edge.fact = "test fact"
        mock_edge.name = "test name"
        mock_edge.created_at = "2025-01-01T00:00:00Z"
        mock_edge.valid_at = "2025-01-01T00:00:00Z"
        mock_edge.score = 0.95

        mock_graphiti = AsyncMock()
        mock_graphiti.search.return_value = [mock_edge]
        client._graphiti = mock_graphiti

        results = await client._execute_search("test query")

        assert len(results) == 1
        assert client._consecutive_failures == 0  # Should be reset

    @pytest.mark.asyncio
    async def test_execute_search_records_failure_on_exception(self):
        """Test that _execute_search records failure when exception occurs."""
        client = GraphitiClient()
        client._consecutive_failures = 0

        # Mock search that raises exception
        mock_graphiti = AsyncMock()
        mock_graphiti.search.side_effect = Exception("Connection error")
        client._graphiti = mock_graphiti

        results = await client._execute_search("test query")

        assert results == []
        assert client._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_execute_search_trips_breaker_after_max_failures(self):
        """Test that circuit breaker trips after max consecutive failures."""
        client = GraphitiClient()
        client._consecutive_failures = 0

        # Mock search that always fails
        mock_graphiti = AsyncMock()
        mock_graphiti.search.side_effect = Exception("Connection error")
        client._graphiti = mock_graphiti

        # Trigger 3 failures
        for i in range(3):
            await client._execute_search("test query")

        assert client._consecutive_failures == 3
        assert client._circuit_breaker_tripped is True

    @pytest.mark.asyncio
    async def test_search_early_returns_when_breaker_tripped(self):
        """Test that search() returns empty when circuit breaker is tripped via delegation."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._circuit_breaker_tripped = True
        client._graphiti = MagicMock()

        results = await client.search("test query")

        assert results == []


class TestCreateEpisodeWithCircuitBreaker:
    """Test episode creation with circuit breaker."""

    @pytest.mark.asyncio
    async def test_create_episode_returns_none_when_breaker_tripped(self):
        """Test that _create_episode returns None when circuit breaker tripped."""
        client = GraphitiClient()
        client._circuit_breaker_tripped = True
        client._graphiti = MagicMock()

        result = await client._create_episode("test", "content", "group")

        assert result is None
        # Should not have called _graphiti.add_episode
        client._graphiti.add_episode.assert_not_called()

    @pytest.mark.asyncio
    async def test_create_episode_records_success(self):
        """Test that _create_episode records success on successful creation."""
        client = GraphitiClient()
        client._consecutive_failures = 2

        # Mock successful episode creation
        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.return_value = mock_result
        client._graphiti = mock_graphiti

        with patch('guardkit.knowledge.graphiti_client.datetime') as mock_dt:
            result = await client._create_episode("test", "content", "group")

        assert result == "episode-uuid"
        assert client._consecutive_failures == 0  # Should be reset

    @pytest.mark.asyncio
    async def test_create_episode_records_failure_on_exception(self):
        """Test that _create_episode records failure when exception occurs."""
        client = GraphitiClient()
        client._consecutive_failures = 0

        # Mock episode creation that raises exception
        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.side_effect = Exception("Database error")
        client._graphiti = mock_graphiti

        with patch('guardkit.knowledge.graphiti_client.datetime'):
            result = await client._create_episode("test", "content", "group")

        assert result is None
        assert client._consecutive_failures == 1

    @pytest.mark.asyncio
    async def test_create_episode_trips_breaker_after_max_failures(self):
        """Test that circuit breaker trips after max consecutive failures."""
        client = GraphitiClient()
        client._consecutive_failures = 0

        # Mock episode creation that always fails
        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.side_effect = Exception("Database error")
        client._graphiti = mock_graphiti

        # Trigger 3 failures
        with patch('guardkit.knowledge.graphiti_client.datetime'):
            for i in range(3):
                await client._create_episode("test", "content", "group")

        assert client._consecutive_failures == 3
        assert client._circuit_breaker_tripped is True


class TestEpisodeExistsWithCircuitBreaker:
    """Test episode_exists with circuit breaker."""

    @pytest.mark.asyncio
    async def test_episode_exists_returns_not_found_when_breaker_tripped(self):
        """Test that episode_exists returns not_found when circuit breaker tripped."""
        from guardkit.integrations.graphiti.exists_result import ExistsResult

        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._circuit_breaker_tripped = True
        client._graphiti = MagicMock()

        result = await client.episode_exists("entity-id", "group-id")

        assert result.exists is False
        # Should not have called _graphiti.search
        client._graphiti.search.assert_not_called()


class TestCheckHealthWithCircuitBreaker:
    """Test _check_health with circuit breaker."""

    @pytest.mark.asyncio
    async def test_check_health_returns_false_when_breaker_tripped(self):
        """Test that _check_health returns False when circuit breaker tripped."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True
        client._graphiti = MagicMock()
        client._circuit_breaker_tripped = True

        result = await client._check_health()

        assert result is False
        # Should not have attempted health check search
        client._graphiti.search.assert_not_called()


class TestCircuitBreakerIntegration:
    """Integration tests for circuit breaker pattern."""

    @pytest.mark.asyncio
    async def test_mixed_success_failure_resets_counter(self):
        """Test that successes reset the failure counter."""
        client = GraphitiClient()

        # Mock graphiti with alternating success/failure
        mock_edge = MagicMock()
        mock_edge.uuid = "test-uuid"
        mock_edge.fact = "test fact"

        mock_graphiti = AsyncMock()
        client._graphiti = mock_graphiti

        # First call succeeds
        mock_graphiti.search.return_value = [mock_edge]
        await client._execute_search("query1")
        assert client._consecutive_failures == 0

        # Second call fails
        mock_graphiti.search.side_effect = Exception("Error")
        await client._execute_search("query2")
        assert client._consecutive_failures == 1

        # Third call succeeds - should reset counter
        mock_graphiti.search.side_effect = None
        mock_graphiti.search.return_value = [mock_edge]
        await client._execute_search("query3")
        assert client._consecutive_failures == 0
        assert client._circuit_breaker_tripped is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_prevents_further_operations(self):
        """Test that once tripped, circuit breaker blocks all operations."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        # Trip the circuit breaker
        client._consecutive_failures = 2
        client._record_failure()
        assert client._circuit_breaker_tripped is True

        # Mock as initialized
        client._graphiti = MagicMock()

        # All operations should return early without calling graphiti
        search_result = await client._execute_search("query")
        assert search_result == []

        episode_result = await client._create_episode("name", "body", "group")
        assert episode_result is None

        health_result = await client._check_health()
        assert health_result is False

        # episode_exists should return not found
        from guardkit.integrations.graphiti.exists_result import ExistsResult
        exists_result = await client.episode_exists("entity", "group")
        assert exists_result.exists is False

    @pytest.mark.asyncio
    async def test_circuit_breaker_with_different_operation_types(self):
        """Test circuit breaker counts failures across operation types."""
        client = GraphitiClient()

        mock_graphiti = AsyncMock()
        mock_graphiti.search.side_effect = Exception("Error")
        mock_graphiti.add_episode.side_effect = Exception("Error")
        client._graphiti = mock_graphiti

        # Fail with search
        await client._execute_search("query")
        assert client._consecutive_failures == 1

        # Fail with episode creation
        with patch('guardkit.knowledge.graphiti_client.datetime'):
            await client._create_episode("name", "body", "group")
        assert client._consecutive_failures == 2

        # Third failure trips the breaker
        await client._execute_search("query")
        assert client._consecutive_failures == 3
        assert client._circuit_breaker_tripped is True
