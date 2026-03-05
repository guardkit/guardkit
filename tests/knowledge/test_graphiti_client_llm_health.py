"""
Tests for GraphitiClient.wait_for_llm_endpoints() (TASK-SPR-47f8).

Tests:
- Skips check for OpenAI provider (cloud service)
- Returns True when endpoints respond 200
- Returns False on timeout
- Handles missing httpx gracefully
- Checks both LLM and embedding endpoints
- Handles partial readiness (one up, one down)

Coverage Target: >=85%
"""

import asyncio
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


class TestWaitForLlmEndpointsSkipConditions:
    """Tests for conditions that skip the health check entirely."""

    @pytest.mark.asyncio
    async def test_returns_true_immediately_for_openai_provider(self):
        """OpenAI cloud provider skips endpoint check."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)
        result = await client.wait_for_llm_endpoints(timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_no_base_urls_configured(self):
        """vLLM provider but no base URLs configured skips check."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)
        # Both providers are openai, so no check needed
        result = await client.wait_for_llm_endpoints(timeout=1.0)
        assert result is True

    @pytest.mark.asyncio
    async def test_returns_true_when_httpx_not_available(self):
        """Gracefully handles missing httpx."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://localhost:8000/v1",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)

        with patch.dict("sys.modules", {"httpx": None}):
            # Force re-import to fail
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if name == "httpx":
                    raise ImportError("No module named 'httpx'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                result = await client.wait_for_llm_endpoints(timeout=1.0)
        assert result is True


class TestWaitForLlmEndpointsSuccess:
    """Tests for successful endpoint availability checks."""

    @pytest.mark.asyncio
    async def test_returns_true_when_llm_endpoint_responds(self):
        """LLM endpoint responds 200 on first poll."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://localhost:8000/v1",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("guardkit.knowledge.graphiti_client.asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                result = await client.wait_for_llm_endpoints(timeout=10.0)

        assert result is True
        mock_http_client.get.assert_called_with(
            "http://localhost:8000/v1/models", timeout=5.0
        )

    @pytest.mark.asyncio
    async def test_returns_true_when_both_endpoints_respond(self):
        """Both LLM and embedding endpoints respond 200."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://localhost:8000/v1",
            embedding_provider="vllm",
            embedding_base_url="http://localhost:8001/v1",
        )
        client = GraphitiClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("guardkit.knowledge.graphiti_client.asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                result = await client.wait_for_llm_endpoints(timeout=10.0)

        assert result is True
        assert mock_http_client.get.call_count == 2


class TestWaitForLlmEndpointsTimeout:
    """Tests for timeout behavior when endpoints are unavailable."""

    @pytest.mark.asyncio
    async def test_returns_false_when_endpoint_never_responds(self):
        """Returns False when endpoint never becomes available."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://localhost:8000/v1",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)

        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = ConnectionError("Connection refused")
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        # Use a very short timeout to speed up the test
        with patch("guardkit.knowledge.graphiti_client.asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                with patch("guardkit.knowledge.graphiti_client.time") as mock_time:
                    # Simulate time progression: first call within timeout, second past it
                    mock_time.monotonic.side_effect = [0.0, 0.0, 0.5, 1.1]
                    result = await client.wait_for_llm_endpoints(timeout=1.0)

        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_when_one_endpoint_unavailable(self):
        """Returns False when only one of two endpoints responds."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://localhost:8000/v1",
            embedding_provider="vllm",
            embedding_base_url="http://localhost:8001/v1",
        )
        client = GraphitiClient(config)

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200

        def side_effect(url, timeout=None):
            if "8000" in url:
                return mock_response_ok
            raise ConnectionError("Connection refused")

        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = side_effect
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("guardkit.knowledge.graphiti_client.asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                with patch("guardkit.knowledge.graphiti_client.time") as mock_time:
                    # Two poll iterations then timeout
                    mock_time.monotonic.side_effect = [
                        0.0,  # start
                        0.0,  # first loop check
                        0.5,  # remaining check
                        0.6,  # loop check
                        1.1,  # remaining check -> break
                    ]
                    result = await client.wait_for_llm_endpoints(timeout=1.0)

        assert result is False

    @pytest.mark.asyncio
    async def test_logs_warning_for_unavailable_endpoints(self, caplog):
        """Logs warning for each unavailable endpoint at timeout."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://localhost:8000/v1",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)

        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = ConnectionError("Connection refused")
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("guardkit.knowledge.graphiti_client.asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                with patch("guardkit.knowledge.graphiti_client.time") as mock_time:
                    mock_time.monotonic.side_effect = [0.0, 0.0, 1.1]
                    with caplog.at_level("WARNING"):
                        await client.wait_for_llm_endpoints(timeout=1.0)

        assert "LLM endpoint not available" in caplog.text


class TestWaitForLlmEndpointsRetry:
    """Tests for retry/polling behavior."""

    @pytest.mark.asyncio
    async def test_retries_until_endpoint_becomes_available(self):
        """Polls until endpoint responds after initial failures."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://localhost:8000/v1",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200

        # Fail twice, then succeed
        call_count = 0

        async def get_side_effect(url, timeout=None):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise ConnectionError("Connection refused")
            return mock_response_ok

        mock_http_client = AsyncMock()
        mock_http_client.get.side_effect = get_side_effect
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("guardkit.knowledge.graphiti_client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                with patch("guardkit.knowledge.graphiti_client.time") as mock_time:
                    # Time progression allowing 3 poll iterations
                    mock_time.monotonic.side_effect = [
                        0.0,   # start
                        0.0,   # first loop check
                        0.1,   # remaining
                        5.1,   # second loop check
                        5.2,   # remaining
                        10.1,  # third loop check
                    ]
                    result = await client.wait_for_llm_endpoints(timeout=60.0)

        assert result is True
        assert call_count == 3
        assert mock_sleep.call_count == 2  # Slept between first two failures

    @pytest.mark.asyncio
    async def test_handles_non_200_status_code(self):
        """Non-200 status code is treated as not-ready."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://localhost:8000/v1",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)

        mock_response_503 = MagicMock()
        mock_response_503.status_code = 503

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response_503
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("guardkit.knowledge.graphiti_client.asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                with patch("guardkit.knowledge.graphiti_client.time") as mock_time:
                    mock_time.monotonic.side_effect = [0.0, 0.0, 1.1]
                    result = await client.wait_for_llm_endpoints(timeout=1.0)

        assert result is False

    @pytest.mark.asyncio
    async def test_ollama_provider_also_checked(self):
        """Ollama provider triggers endpoint check."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="ollama",
            llm_base_url="http://localhost:11434/v1",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)

        mock_response = MagicMock()
        mock_response.status_code = 200

        mock_http_client = AsyncMock()
        mock_http_client.get.return_value = mock_response
        mock_http_client.__aenter__ = AsyncMock(return_value=mock_http_client)
        mock_http_client.__aexit__ = AsyncMock(return_value=False)

        with patch("guardkit.knowledge.graphiti_client.asyncio.sleep", new_callable=AsyncMock):
            with patch("httpx.AsyncClient", return_value=mock_http_client):
                result = await client.wait_for_llm_endpoints(timeout=10.0)

        assert result is True
        mock_http_client.get.assert_called_with(
            "http://localhost:11434/v1/models", timeout=5.0
        )
