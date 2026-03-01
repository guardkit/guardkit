"""
Tests for custom embedder/LLM client injection in GraphitiClient (TASK-GLI-003).

Tests that initialize() injects OpenAIEmbedder and OpenAIGenericClient when
config uses non-OpenAI providers (vllm, ollama), and maintains backward
compatibility when providers are "openai".

Coverage Target: >=85%
Test Count: 16 tests

Acceptance Criteria:
- AC-001: config.llm_provider != "openai" → OpenAIGenericClient created and injected
- AC-002: config.embedding_provider != "openai" → OpenAIEmbedder created and injected
- AC-003: provider == "openai" → no custom clients injected (Graphiti defaults)
- AC-004: local providers skip OPENAI_API_KEY requirement
- AC-005: backward compatibility — existing "openai" config works unchanged
- AC-006: both providers local → both kwargs passed
- AC-007: mixed providers → only relevant kwarg passed
"""

import os
import pytest
from unittest.mock import MagicMock, AsyncMock, patch

from guardkit.knowledge.graphiti_client import (
    GraphitiConfig,
    GraphitiClient,
)


# ============================================================================
# 1. _build_embedder() Tests (4 tests) — AC-002
# ============================================================================


class TestBuildEmbedder:
    """Tests for _build_embedder() helper method."""

    def test_openai_provider_returns_none(self):
        """AC-003: OpenAI embedding provider returns None (use Graphiti defaults)."""
        config = GraphitiConfig(enabled=True, embedding_provider="openai")
        client = GraphitiClient(config)

        result = client._build_embedder()

        assert result is None

    def test_vllm_provider_creates_openai_embedder(self):
        """AC-002: vllm embedding provider creates OpenAIEmbedder."""
        config = GraphitiConfig(
            enabled=True,
            embedding_provider="vllm",
            embedding_base_url="http://host:8001/v1",
            embedding_model="BAAI/bge-m3",
        )
        client = GraphitiClient(config)

        mock_embedder_instance = MagicMock()
        mock_embedder_class = MagicMock(return_value=mock_embedder_instance)
        mock_config_class = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "graphiti_core.embedder": MagicMock(
                    OpenAIEmbedder=mock_embedder_class,
                    OpenAIEmbedderConfig=mock_config_class,
                ),
            },
        ):
            result = client._build_embedder()

        assert result is mock_embedder_instance
        mock_config_class.assert_called_once_with(
            base_url="http://host:8001/v1",
            embedding_model="BAAI/bge-m3",
            api_key="local-key",
        )
        mock_embedder_class.assert_called_once()

    def test_ollama_provider_creates_openai_embedder(self):
        """AC-002: ollama embedding provider creates OpenAIEmbedder."""
        config = GraphitiConfig(
            enabled=True,
            embedding_provider="ollama",
            embedding_base_url="http://host:11434/v1",
            embedding_model="nomic-embed-text",
        )
        client = GraphitiClient(config)

        mock_embedder_instance = MagicMock()
        mock_embedder_class = MagicMock(return_value=mock_embedder_instance)
        mock_config_class = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "graphiti_core.embedder": MagicMock(
                    OpenAIEmbedder=mock_embedder_class,
                    OpenAIEmbedderConfig=mock_config_class,
                ),
            },
        ):
            result = client._build_embedder()

        assert result is mock_embedder_instance
        mock_config_class.assert_called_once_with(
            base_url="http://host:11434/v1",
            embedding_model="nomic-embed-text",
            api_key="local-key",
        )

    def test_embedder_uses_local_key_placeholder(self):
        """AC-002: Embedder config uses 'local-key' as API key placeholder."""
        config = GraphitiConfig(
            enabled=True,
            embedding_provider="vllm",
            embedding_base_url="http://host:8001/v1",
            embedding_model="test-model",
        )
        client = GraphitiClient(config)

        mock_config_class = MagicMock()
        mock_embedder_class = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "graphiti_core.embedder": MagicMock(
                    OpenAIEmbedder=mock_embedder_class,
                    OpenAIEmbedderConfig=mock_config_class,
                ),
            },
        ):
            client._build_embedder()

        call_kwargs = mock_config_class.call_args
        assert call_kwargs.kwargs["api_key"] == "local-key"


# ============================================================================
# 2. _build_llm_client() Tests (4 tests) — AC-001
# ============================================================================


class TestBuildLLMClient:
    """Tests for _build_llm_client() helper method."""

    def test_openai_provider_returns_none(self):
        """AC-003: OpenAI LLM provider returns None (use Graphiti defaults)."""
        config = GraphitiConfig(enabled=True, llm_provider="openai")
        client = GraphitiClient(config)

        result = client._build_llm_client()

        assert result is None

    def test_vllm_provider_creates_openai_generic_client(self):
        """AC-001: vllm LLM provider creates OpenAIGenericClient."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://host:8000/v1",
            llm_model="Qwen/Qwen3-Coder-30B-A3B",
        )
        client = GraphitiClient(config)

        mock_client_instance = MagicMock()
        mock_client_class = MagicMock(return_value=mock_client_instance)
        mock_config_class = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "graphiti_core.llm_client": MagicMock(LLMConfig=mock_config_class),
                "graphiti_core.llm_client.openai_generic_client": MagicMock(
                    OpenAIGenericClient=mock_client_class,
                ),
            },
        ):
            result = client._build_llm_client()

        assert result is mock_client_instance
        mock_config_class.assert_called_once_with(
            base_url="http://host:8000/v1",
            model="Qwen/Qwen3-Coder-30B-A3B",
            api_key="local-key",
        )
        mock_client_class.assert_called_once()

    def test_ollama_provider_creates_openai_generic_client(self):
        """AC-001: ollama LLM provider creates OpenAIGenericClient."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="ollama",
            llm_base_url="http://host:11434/v1",
            llm_model="llama3",
        )
        client = GraphitiClient(config)

        mock_client_instance = MagicMock()
        mock_client_class = MagicMock(return_value=mock_client_instance)
        mock_config_class = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "graphiti_core.llm_client": MagicMock(LLMConfig=mock_config_class),
                "graphiti_core.llm_client.openai_generic_client": MagicMock(
                    OpenAIGenericClient=mock_client_class,
                ),
            },
        ):
            result = client._build_llm_client()

        assert result is mock_client_instance
        mock_config_class.assert_called_once_with(
            base_url="http://host:11434/v1",
            model="llama3",
            api_key="local-key",
        )

    def test_llm_client_uses_local_key_placeholder(self):
        """AC-001: LLM client config uses 'local-key' as API key placeholder."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://host:8000/v1",
            llm_model="test-model",
        )
        client = GraphitiClient(config)

        mock_config_class = MagicMock()
        mock_client_class = MagicMock()

        with patch.dict(
            "sys.modules",
            {
                "graphiti_core.llm_client": MagicMock(LLMConfig=mock_config_class),
                "graphiti_core.llm_client.openai_generic_client": MagicMock(
                    OpenAIGenericClient=mock_client_class,
                ),
            },
        ):
            client._build_llm_client()

        call_kwargs = mock_config_class.call_args
        assert call_kwargs.kwargs["api_key"] == "local-key"


# ============================================================================
# 3. initialize() Integration — Both Providers Local (3 tests) — AC-006
# ============================================================================


class TestBothProvidersLocal:
    """Tests for initialize() when both providers are non-OpenAI."""

    @pytest.mark.asyncio
    async def test_both_local_passes_both_kwargs_neo4j(self):
        """AC-006: Both local providers pass both embedder and llm_client to Graphiti."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="neo4j",
            llm_provider="vllm",
            llm_base_url="http://host:8000/v1",
            llm_model="Qwen/Qwen3-Coder-30B-A3B",
            embedding_provider="vllm",
            embedding_base_url="http://host:8001/v1",
            embedding_model="BAAI/bge-m3",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        mock_embedder = MagicMock()
        mock_llm_client = MagicMock()

        with patch.object(client, "_build_embedder", return_value=mock_embedder):
            with patch.object(client, "_build_llm_client", return_value=mock_llm_client):
                with patch(
                    "guardkit.knowledge.graphiti_client._check_graphiti_core",
                    return_value=True,
                ):
                    with patch.dict(
                        "sys.modules",
                        {"graphiti_core": MagicMock(Graphiti=mock_graphiti_class)},
                    ):
                        result = await client.initialize()

        assert result is True
        call_kwargs = mock_graphiti_class.call_args
        assert call_kwargs.kwargs["embedder"] is mock_embedder
        assert call_kwargs.kwargs["llm_client"] is mock_llm_client

    @pytest.mark.asyncio
    async def test_both_local_no_openai_api_key_needed(self):
        """AC-004: Both local providers don't need OPENAI_API_KEY."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="neo4j",
            llm_provider="vllm",
            llm_base_url="http://host:8000/v1",
            llm_model="test-model",
            embedding_provider="vllm",
            embedding_base_url="http://host:8001/v1",
            embedding_model="test-embed",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        with patch.object(client, "_build_embedder", return_value=MagicMock()):
            with patch.object(client, "_build_llm_client", return_value=MagicMock()):
                with patch(
                    "guardkit.knowledge.graphiti_client._check_graphiti_core",
                    return_value=True,
                ):
                    with patch.dict(
                        "sys.modules",
                        {"graphiti_core": MagicMock(Graphiti=mock_graphiti_class)},
                    ):
                        # No OPENAI_API_KEY in environment
                        with patch.dict(os.environ, {}, clear=True):
                            result = await client.initialize()

        assert result is True

    @pytest.mark.asyncio
    async def test_both_local_with_falkordb(self):
        """AC-006: Both local providers work with FalkorDB driver."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            llm_provider="vllm",
            llm_base_url="http://host:8000/v1",
            llm_model="test-model",
            embedding_provider="vllm",
            embedding_base_url="http://host:8001/v1",
            embedding_model="test-embed",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)
        mock_driver_class = MagicMock(return_value=MagicMock())

        mock_embedder = MagicMock()
        mock_llm_client = MagicMock()

        with patch.object(client, "_build_embedder", return_value=mock_embedder):
            with patch.object(client, "_build_llm_client", return_value=mock_llm_client):
                with patch(
                    "guardkit.knowledge.graphiti_client._check_graphiti_core",
                    return_value=True,
                ):
                    with patch.dict(
                        "sys.modules",
                        {
                            "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                            "graphiti_core.driver": MagicMock(),
                            "graphiti_core.driver.falkordb_driver": MagicMock(
                                FalkorDriver=mock_driver_class
                            ),
                        },
                    ):
                        result = await client.initialize()

        assert result is True
        call_kwargs = mock_graphiti_class.call_args
        assert call_kwargs.kwargs["embedder"] is mock_embedder
        assert call_kwargs.kwargs["llm_client"] is mock_llm_client
        assert "graph_driver" in call_kwargs.kwargs


# ============================================================================
# 4. Backward Compatibility Tests (3 tests) — AC-003, AC-005
# ============================================================================


class TestBackwardCompatibility:
    """Tests that default OpenAI config works unchanged."""

    @pytest.mark.asyncio
    async def test_default_config_no_extra_kwargs(self):
        """AC-005: Default config (openai/openai) passes no embedder/llm_client."""
        config = GraphitiConfig(enabled=True, graph_store="neo4j")
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "guardkit.knowledge.graphiti_client._check_graphiti_core",
                return_value=True,
            ):
                with patch.dict(
                    "sys.modules",
                    {"graphiti_core": MagicMock(Graphiti=mock_graphiti_class)},
                ):
                    result = await client.initialize()

        assert result is True
        call_kwargs = mock_graphiti_class.call_args
        # No embedder or llm_client kwargs when both providers are openai
        assert "embedder" not in call_kwargs.kwargs
        assert "llm_client" not in call_kwargs.kwargs

    @pytest.mark.asyncio
    async def test_mixed_openai_llm_local_embedding(self):
        """AC-007: OpenAI LLM + local embedding → only embedder kwarg passed."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="neo4j",
            llm_provider="openai",
            embedding_provider="vllm",
            embedding_base_url="http://host:8001/v1",
            embedding_model="BAAI/bge-m3",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        mock_embedder = MagicMock()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(client, "_build_embedder", return_value=mock_embedder):
                with patch(
                    "guardkit.knowledge.graphiti_client._check_graphiti_core",
                    return_value=True,
                ):
                    with patch.dict(
                        "sys.modules",
                        {"graphiti_core": MagicMock(Graphiti=mock_graphiti_class)},
                    ):
                        result = await client.initialize()

        assert result is True
        call_kwargs = mock_graphiti_class.call_args
        assert call_kwargs.kwargs["embedder"] is mock_embedder
        assert "llm_client" not in call_kwargs.kwargs

    @pytest.mark.asyncio
    async def test_mixed_local_llm_openai_embedding(self):
        """AC-007: Local LLM + OpenAI embedding → only llm_client kwarg passed."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="neo4j",
            llm_provider="vllm",
            llm_base_url="http://host:8000/v1",
            llm_model="test-model",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        mock_llm_client = MagicMock()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch.object(client, "_build_llm_client", return_value=mock_llm_client):
                with patch(
                    "guardkit.knowledge.graphiti_client._check_graphiti_core",
                    return_value=True,
                ):
                    with patch.dict(
                        "sys.modules",
                        {"graphiti_core": MagicMock(Graphiti=mock_graphiti_class)},
                    ):
                        result = await client.initialize()

        assert result is True
        call_kwargs = mock_graphiti_class.call_args
        assert call_kwargs.kwargs["llm_client"] is mock_llm_client
        assert "embedder" not in call_kwargs.kwargs


# ============================================================================
# 5. OPENAI_API_KEY Requirement Tests (2 tests) — AC-004
# ============================================================================


class TestOpenAIAPIKeyRequirement:
    """Tests for OPENAI_API_KEY check with mixed providers."""

    @pytest.mark.asyncio
    async def test_openai_llm_requires_api_key(self):
        """AC-004: When LLM provider is openai, OPENAI_API_KEY is required."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="openai",
            embedding_provider="vllm",
            embedding_base_url="http://host:8001/v1",
            embedding_model="test",
        )
        client = GraphitiClient(config)

        with patch.dict(os.environ, {}, clear=True):
            result = await client.initialize()

        assert result is False

    @pytest.mark.asyncio
    async def test_openai_embedding_requires_api_key(self):
        """AC-004: When embedding provider is openai, OPENAI_API_KEY is required."""
        config = GraphitiConfig(
            enabled=True,
            llm_provider="vllm",
            llm_base_url="http://host:8000/v1",
            llm_model="test",
            embedding_provider="openai",
        )
        client = GraphitiClient(config)

        with patch.dict(os.environ, {}, clear=True):
            result = await client.initialize()

        assert result is False
