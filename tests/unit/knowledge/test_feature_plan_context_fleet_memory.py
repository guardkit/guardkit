"""Tests for fleet-memory integration in feature_plan_context.

Tests verify that FeaturePlanContextBuilder correctly routes through
fleet-memory when backend is configured as fleet_memory or dual.

Coverage Target: >=80%
Test Count: 8+ tests

Key behaviors verified:
- Routes through fleet_memory when backend=fleet_memory
- Routes through graphiti when backend=graphiti (default)
- Emits query_logger entries for fleet-memory reads
- Handles unmapped group_ids gracefully
- Handles fleet-memory read failures gracefully
"""

import pytest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def mock_fleet_client() -> MagicMock:
    """Create a mock FleetMemoryClient instance."""
    client = MagicMock()
    client.enabled = True
    client.search = AsyncMock(return_value=[
        {"fact": "Related feature from fleet-memory", "uuid": "test-uuid", "score": 0.9}
    ])
    # Set class name to match FleetMemoryClient for backend type detection
    client.__class__.__name__ = "FleetMemoryClient"
    return client


@pytest.fixture
def mock_graphiti_client() -> MagicMock:
    """Create a mock GraphitiClient instance."""
    client = MagicMock()
    client.enabled = True
    client.search = AsyncMock(return_value=[
        {"fact": "Related feature from graphiti", "uuid": "test-uuid-g", "score": 0.85}
    ])
    return client


@pytest.fixture
def builder(tmp_path: Path) -> FeaturePlanContextBuilder:
    """Create a FeaturePlanContextBuilder instance."""
    return FeaturePlanContextBuilder(project_root=tmp_path)


# =========================================================================
# FLEET_MEMORY BACKEND TESTS
# =========================================================================


class TestFleetMemoryIntegration:
    """Tests for fleet_memory backend routing."""

    @pytest.mark.asyncio
    async def test_uses_fleet_memory_client_when_configured(
        self, builder: FeaturePlanContextBuilder, mock_fleet_client: MagicMock
    ):
        """Test that fleet_memory backend uses FleetMemoryClient."""
        builder.graphiti_client = mock_fleet_client

        context = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python"
        )

        # Verify fleet-memory search was called
        assert mock_fleet_client.search.called
        assert context is not None

    @pytest.mark.asyncio
    async def test_fleet_memory_search_emits_query_log(
        self, builder: FeaturePlanContextBuilder, mock_fleet_client: MagicMock
    ):
        """Test that fleet-memory reads emit query_logger entries."""
        builder.graphiti_client = mock_fleet_client
        logged_queries = []

        def capture_log(**kwargs):
            logged_queries.append(kwargs)

        with patch("guardkit.knowledge.feature_plan_context.log_query", side_effect=capture_log):
            await builder.build_context(
                description="Test feature",
                context_files=[],
                tech_stack="python"
            )

            # Verify queries were logged
            assert len(logged_queries) > 0
            # Check that source indicates fleet_memory for at least one query
            assert any("fleet" in str(log.get("source", "")).lower() for log in logged_queries)


# =========================================================================
# GRAPHITI BACKEND TESTS (DEFAULT BEHAVIOR)
# =========================================================================


class TestGraphitiBackendPreserved:
    """Tests that graphiti backend behavior is unchanged."""

    @pytest.mark.asyncio
    async def test_graphiti_backend_uses_graphiti_client(
        self, builder: FeaturePlanContextBuilder, mock_graphiti_client: MagicMock
    ):
        """Test that graphiti backend (default) still uses GraphitiClient."""
        builder.graphiti_client = mock_graphiti_client

        context = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python"
        )

        # Verify graphiti search was called
        assert mock_graphiti_client.search.called
        assert context is not None


# =========================================================================
# ERROR HANDLING TESTS
# =========================================================================


class TestErrorHandling:
    """Tests for graceful degradation when fleet-memory fails."""

    @pytest.mark.asyncio
    async def test_fleet_memory_read_failure_graceful_degradation(
        self, builder: FeaturePlanContextBuilder
    ):
        """Test that fleet-memory read failure degrades gracefully."""
        failing_client = MagicMock()
        failing_client.enabled = True
        failing_client.search = AsyncMock(side_effect=Exception("Connection failed"))

        builder.graphiti_client = failing_client

        # Should not raise, returns context with empty lists
        context = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python"
        )

        assert context is not None
        assert context.related_features == []
        assert context.relevant_patterns == []

    @pytest.mark.asyncio
    async def test_unmapped_group_returns_empty(
        self, builder: FeaturePlanContextBuilder, mock_fleet_client: MagicMock
    ):
        """Test graceful handling of unmapped group_ids."""
        # Mock fleet client that returns empty for unmapped groups
        mock_fleet_client.search = AsyncMock(return_value=[])
        builder.graphiti_client = mock_fleet_client

        context = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python"
        )

        # Should handle gracefully with empty results
        assert context is not None
        assert context.related_features == []

    @pytest.mark.asyncio
    async def test_none_client_graceful_degradation(
        self, builder: FeaturePlanContextBuilder
    ):
        """Test graceful handling when client is None."""
        builder.graphiti_client = None

        context = await builder.build_context(
            description="Test feature",
            context_files=[],
            tech_stack="python"
        )

        # Should not raise, returns empty context
        assert context is not None
        assert context.related_features == []
        assert context.relevant_patterns == []


# =========================================================================
# Real-seam tests (FEAT-MEM-09 W1 / TASK-MEM09-FPCTX)
#
# The tests above MagicMock the client. Per
# .claude/rules/per-task-green-is-not-feature-green.md that is absent
# integration evidence. The tests below (a) exercise the REAL
# FleetMemoryClient.search() -> fleet_memory_mapping path (external
# fleet_memory.retrieval edge stubbed) for a KEPT read, and (b) prove the
# RETIRE-group reads were stripped (Fork A Hybrid).
# =========================================================================


def _install_fake_fleet_memory_retrieval(monkeypatch, *, context_block, coverage, captured):
    """Fake ONLY the external fleet_memory.retrieval edge, capturing the real
    SearchRequest the shim builds (mirrors tests/unit/knowledge/
    test_fleet_memory_client.py, TASK-MEM08-011)."""
    import sys
    import types

    class _FakeSearchRequest:
        def __init__(self, **kw):
            captured["request"] = kw

    async def _fake_search(request, store):
        return ["r1", "r2"]

    class _FakeAssembly:
        pass

    def _fake_assemble(results, token_budget):
        a = _FakeAssembly()
        a.context_block = context_block
        a.coverage_score = coverage
        return a

    retrieval = types.ModuleType("fleet_memory.retrieval")
    retrieval.SearchRequest = _FakeSearchRequest
    retrieval.search = _fake_search
    retrieval.assemble_context = _fake_assemble
    fm = types.ModuleType("fleet_memory")
    fm.retrieval = retrieval
    monkeypatch.setitem(sys.modules, "fleet_memory", fm)
    monkeypatch.setitem(sys.modules, "fleet_memory.retrieval", retrieval)


def _enabled_fleet_client():
    """A REAL FleetMemoryClient (NOT a mock), reads enabled + store pre-opened."""
    from guardkit.knowledge.fleet_memory_client import (
        FleetMemoryClient,
        FleetMemoryConfig,
    )

    client = FleetMemoryClient(
        FleetMemoryConfig(
            enabled=True,
            postgres_dsn="postgresql://t:t@localhost:5433/t",
            embed_url="http://localhost:9000/v1",
            embed_model="nomic-embed",
            embed_dims=768,
            nats_url="nats://localhost:4222",
        )
    )
    client._read_available = True
    client._store = object()
    return client


class TestFeaturePlanContextRealSeam:
    """Exercise the REAL fleet-memory read seam + prove the RETIRE strip."""

    @pytest.mark.asyncio
    async def test_feature_specs_read_resolves_migrate_group(
        self, builder: FeaturePlanContextBuilder, monkeypatch
    ):
        """A kept read (feature_specs) resolves via REAL fleet_memory_mapping to
        document / [feature, spec] (not a MagicMock)."""
        captured: dict = {}
        _install_fake_fleet_memory_retrieval(
            monkeypatch, context_block="feature X spec", coverage=0.7, captured=captured,
        )
        builder.graphiti_client = _enabled_fleet_client()
        monkeypatch.setattr(builder, "_log_fleet_memory_query", lambda **kw: None)

        results = await builder._safe_search(query="x", group_ids=["feature_specs"])

        req = captured["request"]
        assert req["payload_types"] == ["document"]
        assert req["domain_tags"] == ["feature", "spec"]
        assert results and results[0]["fact"] == "feature X spec"

    @pytest.mark.asyncio
    async def test_retire_group_reads_are_stripped(
        self, builder: FeaturePlanContextBuilder, monkeypatch
    ):
        """RETIRE-group reads removed: even with retrieval returning hits for every
        search, relevant_patterns / role_constraints / quality_gate_configs /
        implementation_modes stay empty (no read issued), while a kept read
        (related_features) is populated."""
        _install_fake_fleet_memory_retrieval(
            monkeypatch, context_block="a hit", coverage=0.6, captured={},
        )
        builder.graphiti_client = _enabled_fleet_client()
        monkeypatch.setattr(builder, "_log_fleet_memory_query", lambda **kw: None)

        ctx = await builder.build_context(description="Test feature", tech_stack="python")

        # kept read fires -> populated
        assert ctx.related_features, "feature_specs read should still populate related_features"
        # stripped RETIRE reads never fire -> stay empty (they'd be populated if searched)
        assert ctx.relevant_patterns == []
        assert ctx.role_constraints == []
        assert ctx.quality_gate_configs == []
        assert ctx.implementation_modes == []

    @pytest.mark.live
    @pytest.mark.asyncio
    async def test_build_context_returns_real_hits_live(
        self, builder: FeaturePlanContextBuilder
    ):
        """Operator-run proof: with the store ENABLED, build_context returns real
        enrichment. Skips cleanly when the store is disabled."""
        from guardkit.knowledge.fleet_memory_client import get_memory_client

        client = get_memory_client()
        if client is None or not getattr(client, "enabled", False):
            pytest.skip("fleet-memory store not enabled (Status: DISABLED)")

        ctx = await builder.build_context(description="autobuild coach", tech_stack="python")
        assert (
            ctx.related_features or ctx.warnings or ctx.similar_implementations
            or ctx.project_architecture
        ), "expected at least one kept enrichment field populated from the live store"
