"""
Tests for TASK-EMB-005: embedding dimension pre-flight check in GraphitiClient.

Coverage Target: >=85%
Test Count: 14 tests

Acceptance Criteria:
- AC-001: After FalkorDB connection, _check_embedding_dimensions() is called
- AC-002: Mismatched dims → ERROR logged with clear message
- AC-003: Fresh DB (no vector index) → skip gracefully
- AC-004: Check adds <2s (enforced by timeout)
- AC-005: Check failure does NOT block initialization
- AC-006: Tests cover matching dims, mismatched dims, empty DB, timeout
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from guardkit.knowledge.graphiti_client import (
    KNOWN_EMBEDDING_DIMS,
    GraphitiClient,
    GraphitiConfig,
)


# ============================================================================
# 1. KNOWN_EMBEDDING_DIMS Sanity Tests (3 tests)
# ============================================================================


class TestKnownEmbeddingDims:
    """Verify KNOWN_EMBEDDING_DIMS contains expected models."""

    def test_known_dims_contains_openai_models(self):
        """KNOWN_EMBEDDING_DIMS includes standard OpenAI model names."""
        assert "text-embedding-3-small" in KNOWN_EMBEDDING_DIMS
        assert KNOWN_EMBEDDING_DIMS["text-embedding-3-small"] == 1536
        assert "text-embedding-3-large" in KNOWN_EMBEDDING_DIMS
        assert KNOWN_EMBEDDING_DIMS["text-embedding-3-large"] == 3072
        assert "text-embedding-ada-002" in KNOWN_EMBEDDING_DIMS
        assert KNOWN_EMBEDDING_DIMS["text-embedding-ada-002"] == 1536

    def test_known_dims_contains_nomic_models(self):
        """KNOWN_EMBEDDING_DIMS includes nomic-embed models."""
        assert "nomic-embed-text-v1.5" in KNOWN_EMBEDDING_DIMS
        assert KNOWN_EMBEDDING_DIMS["nomic-embed-text-v1.5"] == 768
        assert "nomic-embed-text" in KNOWN_EMBEDDING_DIMS

    def test_known_dims_values_are_positive_ints(self):
        """All dimension values are positive integers."""
        for model, dim in KNOWN_EMBEDDING_DIMS.items():
            assert isinstance(dim, int), f"{model} dim must be int"
            assert dim > 0, f"{model} dim must be positive"


# ============================================================================
# 2. _check_embedding_dimensions() Skip Conditions (4 tests)
# ============================================================================


class TestCheckEmbeddingDimensionsSkipConditions:
    """_check_embedding_dimensions() skips silently in various conditions."""

    @pytest.mark.asyncio
    async def test_skips_for_neo4j_graph_store(self):
        """No check runs when graph_store is 'neo4j'."""
        config = GraphitiConfig(enabled=True, graph_store="neo4j")
        client = GraphitiClient(config)
        client._connected = True
        client._graphiti = MagicMock()

        # Should complete without error; _do_embedding_dimension_check not called
        with patch.object(
            client, "_do_embedding_dimension_check", new_callable=AsyncMock
        ) as mock_check:
            await client._check_embedding_dimensions()
            mock_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_not_connected(self):
        """No check runs when _connected is False."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
        )
        client = GraphitiClient(config)
        client._connected = False
        client._graphiti = MagicMock()

        with patch.object(
            client, "_do_embedding_dimension_check", new_callable=AsyncMock
        ) as mock_check:
            await client._check_embedding_dimensions()
            mock_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_skips_when_graphiti_is_none(self):
        """No check runs when _graphiti is None."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
        )
        client = GraphitiClient(config)
        client._connected = True
        client._graphiti = None

        with patch.object(
            client, "_do_embedding_dimension_check", new_callable=AsyncMock
        ) as mock_check:
            await client._check_embedding_dimensions()
            mock_check.assert_not_called()

    @pytest.mark.asyncio
    async def test_handles_timeout_gracefully(self):
        """Timeout in _do_embedding_dimension_check is caught; init proceeds."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
        )
        client = GraphitiClient(config)
        client._connected = True
        client._graphiti = MagicMock()

        async def slow_check():
            await asyncio.sleep(10)  # Exceeds 1.5s timeout

        with patch.object(client, "_do_embedding_dimension_check", side_effect=slow_check):
            # Should not raise; timeout is caught
            await asyncio.wait_for(
                client._check_embedding_dimensions(),
                timeout=3.0,
            )


# ============================================================================
# 3. _do_embedding_dimension_check() Logic Tests (4 tests)
# ============================================================================


class TestDoEmbeddingDimensionCheck:
    """Core logic: compare expected vs stored dimension."""

    @pytest.mark.asyncio
    async def test_logs_error_on_dimension_mismatch(self, caplog):
        """AC-002: ERROR is logged when expected dim != stored dim."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            embedding_model="text-embedding-3-small",  # expects 1536
        )
        client = GraphitiClient(config)
        client._connected = True
        client._graphiti = MagicMock()

        with patch.object(
            client,
            "_query_stored_embedding_dim",
            new_callable=AsyncMock,
            return_value=768,  # stored is 768, expected is 1536
        ):
            import logging
            with caplog.at_level(logging.ERROR, logger="guardkit.knowledge.graphiti_client"):
                await client._do_embedding_dimension_check()

        assert any(
            "Embedding dimension mismatch" in record.message
            for record in caplog.records
        ), "Expected ERROR log about dimension mismatch"
        assert any("1536" in record.message for record in caplog.records)
        assert any("768" in record.message for record in caplog.records)

    @pytest.mark.asyncio
    async def test_no_error_on_matching_dimensions(self, caplog):
        """AC-006: No ERROR logged when dims match."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            embedding_model="text-embedding-3-small",  # expects 1536
        )
        client = GraphitiClient(config)
        client._connected = True
        client._graphiti = MagicMock()

        with patch.object(
            client,
            "_query_stored_embedding_dim",
            new_callable=AsyncMock,
            return_value=1536,  # matching
        ):
            import logging
            with caplog.at_level(logging.ERROR, logger="guardkit.knowledge.graphiti_client"):
                await client._do_embedding_dimension_check()

        error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert not error_logs, f"Unexpected ERROR logs: {[r.message for r in error_logs]}"

    @pytest.mark.asyncio
    async def test_skips_when_stored_dim_is_none(self, caplog):
        """AC-003: Fresh DB — stored_dim is None → skip without error."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            embedding_model="text-embedding-3-small",
        )
        client = GraphitiClient(config)
        client._connected = True
        client._graphiti = MagicMock()

        with patch.object(
            client,
            "_query_stored_embedding_dim",
            new_callable=AsyncMock,
            return_value=None,
        ):
            import logging
            with caplog.at_level(logging.ERROR, logger="guardkit.knowledge.graphiti_client"):
                await client._do_embedding_dimension_check()

        error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert not error_logs

    @pytest.mark.asyncio
    async def test_skips_when_model_not_in_lookup_table(self, caplog):
        """Model not in KNOWN_EMBEDDING_DIMS → skip without error."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            embedding_provider="vllm",
            embedding_base_url="http://localhost:8001/v1",
            embedding_model="some-custom-model-unknown",
        )
        client = GraphitiClient(config)
        client._connected = True
        client._graphiti = MagicMock()

        query_mock = AsyncMock(return_value=1024)
        with patch.object(client, "_query_stored_embedding_dim", query_mock):
            import logging
            with caplog.at_level(logging.ERROR, logger="guardkit.knowledge.graphiti_client"):
                await client._do_embedding_dimension_check()

        # Query should not even be called if model is unknown
        query_mock.assert_not_called()
        error_logs = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert not error_logs


# ============================================================================
# 4. _query_stored_embedding_dim() Tests (4 tests)
# ============================================================================


class TestQueryStoredEmbeddingDim:
    """Query logic for FalkorDB vector index dimension."""

    @pytest.mark.asyncio
    async def test_returns_none_when_graphiti_is_none(self):
        """Returns None when _graphiti is not set."""
        config = GraphitiConfig(enabled=True, graph_store="falkordb")
        client = GraphitiClient(config)
        client._graphiti = None

        result = await client._query_stored_embedding_dim()
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_driver_has_no_execute_query(self):
        """Returns None when driver lacks execute_query method."""
        config = GraphitiConfig(enabled=True, graph_store="falkordb")
        client = GraphitiClient(config)
        mock_graphiti = MagicMock(spec=[])  # No attributes (spec=[])
        client._graphiti = mock_graphiti

        result = await client._query_stored_embedding_dim()
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_dimension_from_successful_query(self):
        """Parses dimension from a successful db.indexes() result."""
        config = GraphitiConfig(enabled=True, graph_store="falkordb")
        client = GraphitiClient(config)

        mock_record = {"dimension": 768}
        mock_result = MagicMock()
        mock_result.records = [mock_record]

        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(return_value=mock_result)

        mock_graphiti = MagicMock()
        mock_graphiti._driver = mock_driver
        client._graphiti = mock_graphiti

        result = await client._query_stored_embedding_dim()
        assert result == 768

    @pytest.mark.asyncio
    async def test_returns_none_when_query_raises_exception(self):
        """AC-005: Returns None (never raises) when execute_query fails."""
        config = GraphitiConfig(enabled=True, graph_store="falkordb")
        client = GraphitiClient(config)

        mock_driver = MagicMock()
        mock_driver.execute_query = AsyncMock(
            side_effect=RuntimeError("db.indexes() not supported")
        )

        mock_graphiti = MagicMock()
        mock_graphiti._driver = mock_driver
        client._graphiti = mock_graphiti

        # Must not raise
        result = await client._query_stored_embedding_dim()
        assert result is None


# ============================================================================
# 5. Integration: initialize() calls check after successful connection (1 test)
# ============================================================================


class TestInitializeCallsPreflight:
    """Verify initialize() wires up _check_embedding_dimensions() correctly."""

    @pytest.mark.asyncio
    async def test_initialize_calls_check_after_connection(self):
        """AC-001: _check_embedding_dimensions() is called after successful FalkorDB connect."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            embedding_provider="vllm",
            embedding_base_url="http://localhost:8001/v1",
            embedding_model="nomic-embed-text-v1.5",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)
        mock_driver_class = MagicMock(return_value=MagicMock())

        check_called = []

        async def fake_check():
            check_called.append(True)

        with patch.object(client, "_check_embedding_dimensions", side_effect=fake_check):
            with patch.object(client, "_build_embedder", return_value=MagicMock()):
                with patch.object(client, "_build_llm_client", return_value=None):
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
        assert check_called, "_check_embedding_dimensions() was not called"
