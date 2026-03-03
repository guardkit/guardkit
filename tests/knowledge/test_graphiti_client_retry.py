"""
Tests for GraphitiClient retry with exponential backoff and circuit breaker
half-open state (TASK-IGR-002).

Tests:
- Retry with exponential backoff for transient errors
- Non-transient error fails immediately
- Transient error classification
- Circuit breaker half-open state (reset after 60s)
- Circuit breaker reset logging

Coverage Target: >=85%
"""

import time

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

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


class TestIsTransientError:
    """Test _is_transient_error static method."""

    def test_max_pending_queries_is_transient(self):
        err = Exception("Max pending queries exceeded")
        assert GraphitiClient._is_transient_error(err) is True

    def test_connection_error_is_transient(self):
        err = Exception("Connection refused")
        assert GraphitiClient._is_transient_error(err) is True

    def test_connection_lowercase_is_transient(self):
        err = Exception("connection reset by peer")
        assert GraphitiClient._is_transient_error(err) is True

    def test_timed_out_is_transient(self):
        err = Exception("Timed out waiting for response")
        assert GraphitiClient._is_transient_error(err) is True

    def test_timed_out_lowercase_is_transient(self):
        err = Exception("Request timed out")
        assert GraphitiClient._is_transient_error(err) is True

    def test_non_transient_error(self):
        err = Exception("Invalid query syntax")
        assert GraphitiClient._is_transient_error(err) is False

    def test_generic_error_not_transient(self):
        err = Exception("Something went wrong")
        assert GraphitiClient._is_transient_error(err) is False


class TestCreateEpisodeRetry:
    """Test retry with exponential backoff in _create_episode()."""

    @pytest.mark.asyncio
    async def test_retries_on_transient_error_then_succeeds(self):
        """Transient error on first attempt, success on second."""
        client = GraphitiClient()

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.side_effect = [
            Exception("Max pending queries exceeded"),
            mock_result,
        ]
        client._graphiti = mock_graphiti

        with patch('guardkit.knowledge.graphiti_client.datetime') as mock_dt, \
             patch('guardkit.knowledge.graphiti_client.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await client._create_episode("test", "content", "group")

        assert result == "episode-uuid"
        assert client._consecutive_failures == 0
        mock_sleep.assert_called_once_with(2)  # 2^(0+1) = 2s

    @pytest.mark.asyncio
    async def test_retries_twice_on_transient_errors_then_succeeds(self):
        """Transient errors on first two attempts, success on third."""
        client = GraphitiClient()

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.side_effect = [
            Exception("Connection refused"),
            Exception("Max pending queries exceeded"),
            mock_result,
        ]
        client._graphiti = mock_graphiti

        with patch('guardkit.knowledge.graphiti_client.datetime') as mock_dt, \
             patch('guardkit.knowledge.graphiti_client.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await client._create_episode("test", "content", "group")

        assert result == "episode-uuid"
        assert client._consecutive_failures == 0
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(2)  # First retry: 2s
        mock_sleep.assert_any_call(4)  # Second retry: 4s

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_records_failure(self):
        """All 3 attempts fail with transient errors, records failure."""
        client = GraphitiClient()

        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.side_effect = Exception("Max pending queries exceeded")
        client._graphiti = mock_graphiti

        with patch('guardkit.knowledge.graphiti_client.datetime') as mock_dt, \
             patch('guardkit.knowledge.graphiti_client.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await client._create_episode("test", "content", "group")

        assert result is None
        assert client._consecutive_failures == 1
        # Should have retried twice (attempts 0 and 1), then failed on attempt 2
        assert mock_sleep.call_count == 2

    @pytest.mark.asyncio
    async def test_non_transient_error_fails_immediately(self):
        """Non-transient error fails on first attempt without retrying."""
        client = GraphitiClient()

        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.side_effect = Exception("Invalid query syntax")
        client._graphiti = mock_graphiti

        with patch('guardkit.knowledge.graphiti_client.datetime') as mock_dt, \
             patch('guardkit.knowledge.graphiti_client.asyncio.sleep', new_callable=AsyncMock) as mock_sleep:
            result = await client._create_episode("test", "content", "group")

        assert result is None
        assert client._consecutive_failures == 1
        mock_sleep.assert_not_called()

    @pytest.mark.asyncio
    async def test_retry_logs_warning_with_attempt_count(self, caplog):
        """Retry attempts are logged at WARNING level."""
        client = GraphitiClient()

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.side_effect = [
            Exception("Max pending queries exceeded"),
            mock_result,
        ]
        client._graphiti = mock_graphiti

        with patch('guardkit.knowledge.graphiti_client.datetime') as mock_dt, \
             patch('guardkit.knowledge.graphiti_client.asyncio.sleep', new_callable=AsyncMock), \
             caplog.at_level("WARNING"):
            await client._create_episode("test", "content", "group")

        assert "Transient FalkorDB error (attempt 1/3)" in caplog.text
        assert "retrying in 2s" in caplog.text

    @pytest.mark.asyncio
    async def test_circuit_breaker_skips_retry(self):
        """Circuit breaker tripped returns None without any attempts."""
        client = GraphitiClient()
        client._circuit_breaker_tripped = True
        client._circuit_breaker_tripped_at = time.monotonic()
        client._graphiti = MagicMock()

        result = await client._create_episode("test", "content", "group")

        assert result is None
        client._graphiti.add_episode.assert_not_called()


class TestCircuitBreakerHalfOpen:
    """Test circuit breaker half-open state (reset after timeout)."""

    def test_check_circuit_breaker_returns_false_when_not_tripped(self):
        client = GraphitiClient()
        assert client._check_circuit_breaker() is False

    def test_check_circuit_breaker_returns_true_when_tripped_recently(self):
        client = GraphitiClient()
        client._circuit_breaker_tripped = True
        client._circuit_breaker_tripped_at = time.monotonic()
        assert client._check_circuit_breaker() is True

    def test_check_circuit_breaker_resets_after_timeout(self):
        """Circuit breaker resets after 60s (half-open state)."""
        client = GraphitiClient()
        client._circuit_breaker_tripped = True
        client._consecutive_failures = 3
        # Simulate tripped 61 seconds ago
        client._circuit_breaker_tripped_at = time.monotonic() - 61.0

        result = client._check_circuit_breaker()

        assert result is False
        assert client._circuit_breaker_tripped is False
        assert client._consecutive_failures == 0

    def test_check_circuit_breaker_does_not_reset_before_timeout(self):
        """Circuit breaker stays tripped before timeout elapses."""
        client = GraphitiClient()
        client._circuit_breaker_tripped = True
        client._consecutive_failures = 3
        # Simulate tripped 30 seconds ago
        client._circuit_breaker_tripped_at = time.monotonic() - 30.0

        result = client._check_circuit_breaker()

        assert result is True
        assert client._circuit_breaker_tripped is True
        assert client._consecutive_failures == 3

    def test_check_circuit_breaker_logs_reset(self, caplog):
        """Circuit breaker reset is logged at INFO level."""
        client = GraphitiClient()
        client._circuit_breaker_tripped = True
        client._consecutive_failures = 3
        client._circuit_breaker_tripped_at = time.monotonic() - 61.0

        with caplog.at_level("INFO"):
            client._check_circuit_breaker()

        assert "Circuit breaker reset" in caplog.text
        assert "half-open" in caplog.text

    def test_record_failure_sets_tripped_at_timestamp(self):
        """_record_failure() sets _circuit_breaker_tripped_at when tripping."""
        client = GraphitiClient()
        client._consecutive_failures = 2

        before = time.monotonic()
        client._record_failure()
        after = time.monotonic()

        assert client._circuit_breaker_tripped is True
        assert client._circuit_breaker_tripped_at is not None
        assert before <= client._circuit_breaker_tripped_at <= after

    def test_record_failure_does_not_set_timestamp_below_threshold(self):
        """_record_failure() does not set timestamp if breaker not tripped."""
        client = GraphitiClient()
        client._consecutive_failures = 0

        client._record_failure()

        assert client._circuit_breaker_tripped is False
        assert client._circuit_breaker_tripped_at is None

    def test_is_healthy_respects_half_open_reset(self):
        """is_healthy returns True after circuit breaker resets."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)
        client._connected = True
        client._circuit_breaker_tripped = True
        client._consecutive_failures = 3
        client._circuit_breaker_tripped_at = time.monotonic() - 61.0

        assert client.is_healthy is True
        assert client._circuit_breaker_tripped is False

    @pytest.mark.asyncio
    async def test_create_episode_works_after_circuit_breaker_reset(self):
        """_create_episode succeeds after circuit breaker resets (half-open)."""
        client = GraphitiClient()
        client._circuit_breaker_tripped = True
        client._consecutive_failures = 3
        # Simulate tripped 61 seconds ago — should auto-reset
        client._circuit_breaker_tripped_at = time.monotonic() - 61.0

        mock_episode = MagicMock()
        mock_episode.uuid = "episode-uuid"
        mock_result = MagicMock()
        mock_result.episode = mock_episode

        mock_graphiti = AsyncMock()
        mock_graphiti.add_episode.return_value = mock_result
        client._graphiti = mock_graphiti

        with patch('guardkit.knowledge.graphiti_client.datetime'):
            result = await client._create_episode("test", "content", "group")

        assert result == "episode-uuid"
        assert client._circuit_breaker_tripped is False
        assert client._consecutive_failures == 0

    def test_check_circuit_breaker_handles_none_timestamp(self):
        """Handles edge case where tripped but no timestamp (legacy state)."""
        client = GraphitiClient()
        client._circuit_breaker_tripped = True
        client._circuit_breaker_tripped_at = None

        # Should remain tripped (no timestamp to check elapsed time)
        assert client._check_circuit_breaker() is True
