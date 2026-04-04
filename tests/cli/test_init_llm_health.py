"""
Tests for LLM health check in guardkit init.

Covers _check_llm_reachable() function and its integration
with the init system seeding flow.

Coverage Target: >=85%
"""

import pytest
from dataclasses import dataclass
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch


try:
    from guardkit.cli.init import _check_llm_reachable
    from guardkit.knowledge.graphiti_client import GraphitiConfig
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False

pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="CLI init module not available"
)


def _make_config(
    llm_provider: str = "vllm",
    llm_base_url: Optional[str] = "http://localhost:8000/v1",
) -> GraphitiConfig:
    """Create a minimal GraphitiConfig for testing."""
    return GraphitiConfig(
        llm_provider=llm_provider,
        llm_base_url=llm_base_url,
    )


@dataclass
class _FakeConfig:
    """Lightweight stand-in for GraphitiConfig that skips validation."""
    llm_provider: str = "vllm"
    llm_base_url: Optional[str] = None


# ============================================================================
# 1. OpenAI provider skips check
# ============================================================================


class TestOpenAISkipsCheck:
    """OpenAI cloud provider should always return True (no check needed)."""

    @pytest.mark.asyncio
    async def test_openai_returns_true(self):
        config = _FakeConfig(llm_provider="openai", llm_base_url=None)
        assert await _check_llm_reachable(config) is True

    @pytest.mark.asyncio
    async def test_openai_with_base_url_returns_true(self):
        config = _FakeConfig(llm_provider="openai", llm_base_url="http://example.com/v1")
        assert await _check_llm_reachable(config) is True


# ============================================================================
# 2. Missing base URL
# ============================================================================


class TestMissingBaseUrl:
    """vLLM/ollama without a base URL should return False."""

    @pytest.mark.asyncio
    async def test_vllm_no_url_returns_false(self):
        config = _FakeConfig(llm_provider="vllm", llm_base_url=None)
        assert await _check_llm_reachable(config) is False

    @pytest.mark.asyncio
    async def test_ollama_no_url_returns_false(self):
        config = _FakeConfig(llm_provider="ollama", llm_base_url=None)
        assert await _check_llm_reachable(config) is False


# ============================================================================
# 3. Reachable endpoint (httpx path)
# ============================================================================


class TestReachableEndpoint:
    """LLM endpoint responds successfully."""

    @pytest.mark.asyncio
    async def test_vllm_reachable_returns_true(self):
        mock_response = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            config = _make_config(llm_provider="vllm", llm_base_url="http://myhost:8000/v1")
            result = await _check_llm_reachable(config)

        assert result is True
        mock_client.get.assert_called_once_with(
            "http://myhost:8000/v1/models", timeout=5.0
        )

    @pytest.mark.asyncio
    async def test_ollama_reachable_returns_true(self):
        mock_response = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            config = _make_config(
                llm_provider="ollama",
                llm_base_url="http://localhost:11434/v1",
            )
            result = await _check_llm_reachable(config)

        assert result is True

    @pytest.mark.asyncio
    async def test_trailing_slash_stripped(self):
        mock_response = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            config = _make_config(llm_base_url="http://host:8000/v1/")
            result = await _check_llm_reachable(config)

        assert result is True
        mock_client.get.assert_called_once_with(
            "http://host:8000/v1/models", timeout=5.0
        )


# ============================================================================
# 4. Unreachable endpoint
# ============================================================================


class TestUnreachableEndpoint:
    """LLM endpoint is down or errors."""

    @pytest.mark.asyncio
    async def test_connection_error_returns_false(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=ConnectionError("refused"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            config = _make_config()
            result = await _check_llm_reachable(config)

        assert result is False

    @pytest.mark.asyncio
    async def test_timeout_returns_false(self):
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=TimeoutError("timed out"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            config = _make_config()
            result = await _check_llm_reachable(config)

        assert result is False

    @pytest.mark.asyncio
    async def test_non_200_returns_false(self):
        mock_response = MagicMock(status_code=503)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            config = _make_config()
            result = await _check_llm_reachable(config)

        assert result is False


# ============================================================================
# 5. urllib fallback when httpx not available
# ============================================================================


class TestUrllibFallback:
    """When httpx is not importable, fall back to urllib."""

    @pytest.mark.asyncio
    async def test_urllib_fallback_reachable(self):
        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        def mock_import(name, *args, **kwargs):
            if name == "httpx":
                raise ImportError("no httpx")
            return original_import(name, *args, **kwargs)

        config = _make_config()

        with patch("urllib.request.urlopen") as mock_urlopen:
            mock_urlopen.return_value = MagicMock()
            with patch("builtins.__import__", side_effect=mock_import):
                result = await _check_llm_reachable(config)

        assert result is True

    @pytest.mark.asyncio
    async def test_urllib_fallback_unreachable(self):
        import urllib.error

        original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

        def mock_import(name, *args, **kwargs):
            if name == "httpx":
                raise ImportError("no httpx")
            return original_import(name, *args, **kwargs)

        config = _make_config()

        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("refused")):
            with patch("builtins.__import__", side_effect=mock_import):
                result = await _check_llm_reachable(config)

        assert result is False


# ============================================================================
# 6. Custom timeout
# ============================================================================


class TestCustomTimeout:
    """Timeout parameter is forwarded to the HTTP client."""

    @pytest.mark.asyncio
    async def test_custom_timeout_forwarded(self):
        mock_response = MagicMock(status_code=200)
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)

        with patch("httpx.AsyncClient", return_value=mock_client):
            config = _make_config()
            await _check_llm_reachable(config, timeout=2.0)

        mock_client.get.assert_called_once_with(
            "http://localhost:8000/v1/models", timeout=2.0
        )
