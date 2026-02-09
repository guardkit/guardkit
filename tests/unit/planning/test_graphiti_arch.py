"""Tests for SystemPlanGraphiti Graphiti operations.

TDD RED phase tests for TASK-SP-003. These tests verify the persistence layer
that bridges entity definitions (Wave 1) with the interactive command (Wave 3).

Coverage Target: >=85%
Test Count: 40+ tests

Key patterns verified:
- All write operations use upsert_episode() (NOT add_episode())
- All write operations use client.get_group_id() for correct group prefixing
- All operations have graceful degradation (return None/[]/False on failure)
- [Graphiti] prefix on all log messages
"""

import json
import logging
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# These imports will fail until implementation exists (TDD RED phase)
from guardkit.planning.graphiti_arch import SystemPlanGraphiti

from guardkit.knowledge.entities.component import ComponentDef
from guardkit.knowledge.entities.system_context import SystemContextDef
from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
from guardkit.knowledge.entities.architecture_context import ArchitectureDecision


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def mock_client() -> MagicMock:
    """Create a mock GraphitiClient."""
    client = MagicMock()
    client.enabled = True
    client.get_group_id = MagicMock(side_effect=lambda group_name: f"test-project__{group_name}")
    return client


@pytest.fixture
def mock_client_disabled() -> MagicMock:
    """Create a disabled mock GraphitiClient."""
    client = MagicMock()
    client.enabled = False
    return client


@pytest.fixture
def mock_client_none() -> None:
    """Return None to test null client handling."""
    return None


@pytest.fixture
def sample_component() -> ComponentDef:
    """Create a sample component for testing."""
    return ComponentDef(
        name="Order Management",
        description="Handles order lifecycle and fulfillment",
        responsibilities=["Create orders", "Track order status"],
        dependencies=["Inventory", "Payment"],
        methodology="ddd",
        aggregate_roots=["Order", "OrderLine"],
        domain_events=["OrderCreated", "OrderShipped"],
        context_mapping="customer-downstream",
    )


@pytest.fixture
def sample_system_context() -> SystemContextDef:
    """Create a sample system context for testing."""
    return SystemContextDef(
        name="E-Commerce Platform",
        purpose="Online retail with multi-tenant support",
        bounded_contexts=["Orders", "Inventory", "Customers"],
        external_systems=["Payment Gateway", "Shipping API"],
        methodology="ddd",
    )


@pytest.fixture
def sample_crosscutting() -> CrosscuttingConcernDef:
    """Create a sample crosscutting concern for testing."""
    return CrosscuttingConcernDef(
        name="Observability",
        description="Unified logging, metrics, and tracing",
        applies_to=["All Services"],
        implementation_notes="Use OpenTelemetry SDK",
    )


@pytest.fixture
def sample_adr() -> ArchitectureDecision:
    """Create a sample ADR for testing."""
    return ArchitectureDecision(
        number=1,
        title="Use Event Sourcing for Order Aggregate",
        status="accepted",
        context="Orders require complete audit trail",
        decision="Implement event sourcing pattern",
        consequences=["Full audit trail", "Complex replay logic"],
        related_components=["Order Management"],
    )


@pytest.fixture
def graphiti_service(mock_client: MagicMock) -> SystemPlanGraphiti:
    """Create a SystemPlanGraphiti instance with mock client."""
    return SystemPlanGraphiti(client=mock_client, project_id="test-project")


@pytest.fixture
def graphiti_service_disabled(mock_client_disabled: MagicMock) -> SystemPlanGraphiti:
    """Create a SystemPlanGraphiti instance with disabled client."""
    return SystemPlanGraphiti(client=mock_client_disabled, project_id="test-project")


@pytest.fixture
def graphiti_service_null() -> SystemPlanGraphiti:
    """Create a SystemPlanGraphiti instance with null client."""
    return SystemPlanGraphiti(client=None, project_id="test-project")


# =========================================================================
# 1. CONSTRUCTOR AND AVAILABILITY TESTS (5 tests)
# =========================================================================


class TestConstructorAndAvailability:
    """Tests for SystemPlanGraphiti constructor and _available property."""

    def test_constructor_with_client_and_project_id(self, mock_client: MagicMock):
        """Test constructor accepts client and project_id."""
        service = SystemPlanGraphiti(client=mock_client, project_id="my-project")
        assert service._client is mock_client
        assert service._project_id == "my-project"

    def test_constructor_with_none_client(self):
        """Test constructor accepts None client."""
        service = SystemPlanGraphiti(client=None, project_id="my-project")
        assert service._client is None
        assert service._project_id == "my-project"

    def test_available_true_when_client_enabled(self, graphiti_service: SystemPlanGraphiti):
        """Test _available returns True when client exists and is enabled."""
        assert graphiti_service._available is True

    def test_available_false_when_client_disabled(
        self, graphiti_service_disabled: SystemPlanGraphiti
    ):
        """Test _available returns False when client is disabled."""
        assert graphiti_service_disabled._available is False

    def test_available_false_when_client_none(
        self, graphiti_service_null: SystemPlanGraphiti
    ):
        """Test _available returns False when client is None."""
        assert graphiti_service_null._available is False


# =========================================================================
# 2. UPSERT_COMPONENT TESTS (8 tests)
# =========================================================================


class TestUpsertComponent:
    """Tests for upsert_component method."""

    @pytest.mark.asyncio
    async def test_upsert_component_calls_upsert_episode(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_component: ComponentDef,
        mock_client: MagicMock,
    ):
        """Test upsert_component uses upsert_episode (NOT add_episode)."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-123"))

        result = await graphiti_service.upsert_component(sample_component)

        mock_client.upsert_episode.assert_called_once()
        assert result == "uuid-123"

    @pytest.mark.asyncio
    async def test_upsert_component_uses_correct_group_id(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_component: ComponentDef,
        mock_client: MagicMock,
    ):
        """Test upsert_component uses get_group_id for group prefixing."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-123"))

        await graphiti_service.upsert_component(sample_component)

        mock_client.get_group_id.assert_called_with("project_architecture")
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["group_id"] == "test-project__project_architecture"

    @pytest.mark.asyncio
    async def test_upsert_component_uses_stable_entity_id(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_component: ComponentDef,
        mock_client: MagicMock,
    ):
        """Test upsert_component uses component.entity_id for upsert."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-123"))

        await graphiti_service.upsert_component(sample_component)

        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_id"] == sample_component.entity_id
        assert call_kwargs["entity_id"] == "COMP-order-management"

    @pytest.mark.asyncio
    async def test_upsert_component_uses_json_episode_body(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_component: ComponentDef,
        mock_client: MagicMock,
    ):
        """Test upsert_component passes JSON-serialized episode body."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-123"))

        await graphiti_service.upsert_component(sample_component)

        call_kwargs = mock_client.upsert_episode.call_args[1]
        episode_body = call_kwargs["episode_body"]
        # Verify it's valid JSON
        parsed = json.loads(episode_body)
        assert parsed["name"] == "Order Management"

    @pytest.mark.asyncio
    async def test_upsert_component_returns_none_when_disabled(
        self,
        graphiti_service_disabled: SystemPlanGraphiti,
        sample_component: ComponentDef,
    ):
        """Test upsert_component returns None when client is disabled."""
        result = await graphiti_service_disabled.upsert_component(sample_component)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_component_returns_none_when_client_none(
        self,
        graphiti_service_null: SystemPlanGraphiti,
        sample_component: ComponentDef,
    ):
        """Test upsert_component returns None when client is None."""
        result = await graphiti_service_null.upsert_component(sample_component)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_component_returns_none_on_exception(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_component: ComponentDef,
        mock_client: MagicMock,
    ):
        """Test upsert_component returns None and logs on exception."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Network error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            result = await graphiti_service.upsert_component(sample_component)

            assert result is None
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_upsert_component_sets_correct_entity_type(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_component: ComponentDef,
        mock_client: MagicMock,
    ):
        """Test upsert_component sets entity_type based on methodology."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-123"))

        await graphiti_service.upsert_component(sample_component)

        call_kwargs = mock_client.upsert_episode.call_args[1]
        # DDD methodology => bounded_context
        assert call_kwargs["entity_type"] == "bounded_context"


# =========================================================================
# 3. UPSERT_ADR TESTS (8 tests)
# =========================================================================


class TestUpsertAdr:
    """Tests for upsert_adr method."""

    @pytest.mark.asyncio
    async def test_upsert_adr_calls_upsert_episode(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_adr: ArchitectureDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_adr uses upsert_episode (NOT add_episode)."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-456"))

        result = await graphiti_service.upsert_adr(sample_adr)

        mock_client.upsert_episode.assert_called_once()
        assert result == "uuid-456"

    @pytest.mark.asyncio
    async def test_upsert_adr_uses_project_decisions_group(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_adr: ArchitectureDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_adr uses 'project_decisions' group for ADRs."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-456"))

        await graphiti_service.upsert_adr(sample_adr)

        mock_client.get_group_id.assert_called_with("project_decisions")
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["group_id"] == "test-project__project_decisions"

    @pytest.mark.asyncio
    async def test_upsert_adr_uses_adr_entity_id_format(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_adr: ArchitectureDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_adr uses ADR-SP-NNN entity_id format."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-456"))

        await graphiti_service.upsert_adr(sample_adr)

        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_id"] == "ADR-SP-001"

    @pytest.mark.asyncio
    async def test_upsert_adr_uses_json_episode_body(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_adr: ArchitectureDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_adr passes JSON-serialized episode body."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-456"))

        await graphiti_service.upsert_adr(sample_adr)

        call_kwargs = mock_client.upsert_episode.call_args[1]
        episode_body = call_kwargs["episode_body"]
        parsed = json.loads(episode_body)
        assert parsed["title"] == "Use Event Sourcing for Order Aggregate"
        assert parsed["status"] == "accepted"

    @pytest.mark.asyncio
    async def test_upsert_adr_returns_none_when_disabled(
        self,
        graphiti_service_disabled: SystemPlanGraphiti,
        sample_adr: ArchitectureDecision,
    ):
        """Test upsert_adr returns None when client is disabled."""
        result = await graphiti_service_disabled.upsert_adr(sample_adr)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_adr_returns_none_when_client_none(
        self,
        graphiti_service_null: SystemPlanGraphiti,
        sample_adr: ArchitectureDecision,
    ):
        """Test upsert_adr returns None when client is None."""
        result = await graphiti_service_null.upsert_adr(sample_adr)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_adr_returns_none_on_exception(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_adr: ArchitectureDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_adr returns None and logs on exception."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("DB error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            result = await graphiti_service.upsert_adr(sample_adr)

            assert result is None
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_upsert_adr_sets_architecture_decision_entity_type(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_adr: ArchitectureDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_adr sets entity_type to 'architecture_decision'."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-456"))

        await graphiti_service.upsert_adr(sample_adr)

        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_type"] == "architecture_decision"


# =========================================================================
# 4. UPSERT_SYSTEM_CONTEXT TESTS (6 tests)
# =========================================================================


class TestUpsertSystemContext:
    """Tests for upsert_system_context method."""

    @pytest.mark.asyncio
    async def test_upsert_system_context_calls_upsert_episode(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_system_context: SystemContextDef,
        mock_client: MagicMock,
    ):
        """Test upsert_system_context uses upsert_episode."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-789"))

        result = await graphiti_service.upsert_system_context(sample_system_context)

        mock_client.upsert_episode.assert_called_once()
        assert result == "uuid-789"

    @pytest.mark.asyncio
    async def test_upsert_system_context_uses_project_architecture_group(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_system_context: SystemContextDef,
        mock_client: MagicMock,
    ):
        """Test upsert_system_context uses project_architecture group."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-789"))

        await graphiti_service.upsert_system_context(sample_system_context)

        mock_client.get_group_id.assert_called_with("project_architecture")
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["group_id"] == "test-project__project_architecture"

    @pytest.mark.asyncio
    async def test_upsert_system_context_uses_stable_entity_id(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_system_context: SystemContextDef,
        mock_client: MagicMock,
    ):
        """Test upsert_system_context uses SYS-{slug} entity_id."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-789"))

        await graphiti_service.upsert_system_context(sample_system_context)

        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_id"] == "SYS-e-commerce-platform"

    @pytest.mark.asyncio
    async def test_upsert_system_context_returns_none_when_disabled(
        self,
        graphiti_service_disabled: SystemPlanGraphiti,
        sample_system_context: SystemContextDef,
    ):
        """Test upsert_system_context returns None when disabled."""
        result = await graphiti_service_disabled.upsert_system_context(sample_system_context)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_system_context_returns_none_on_exception(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_system_context: SystemContextDef,
        mock_client: MagicMock,
    ):
        """Test upsert_system_context returns None and logs on exception."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            result = await graphiti_service.upsert_system_context(sample_system_context)

            assert result is None
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_upsert_system_context_sets_system_context_entity_type(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_system_context: SystemContextDef,
        mock_client: MagicMock,
    ):
        """Test upsert_system_context sets entity_type to 'system_context'."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-789"))

        await graphiti_service.upsert_system_context(sample_system_context)

        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_type"] == "system_context"


# =========================================================================
# 5. UPSERT_CROSSCUTTING TESTS (6 tests)
# =========================================================================


class TestUpsertCrosscutting:
    """Tests for upsert_crosscutting method."""

    @pytest.mark.asyncio
    async def test_upsert_crosscutting_calls_upsert_episode(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_crosscutting: CrosscuttingConcernDef,
        mock_client: MagicMock,
    ):
        """Test upsert_crosscutting uses upsert_episode."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-abc"))

        result = await graphiti_service.upsert_crosscutting(sample_crosscutting)

        mock_client.upsert_episode.assert_called_once()
        assert result == "uuid-abc"

    @pytest.mark.asyncio
    async def test_upsert_crosscutting_uses_project_architecture_group(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_crosscutting: CrosscuttingConcernDef,
        mock_client: MagicMock,
    ):
        """Test upsert_crosscutting uses project_architecture group."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-abc"))

        await graphiti_service.upsert_crosscutting(sample_crosscutting)

        mock_client.get_group_id.assert_called_with("project_architecture")
        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["group_id"] == "test-project__project_architecture"

    @pytest.mark.asyncio
    async def test_upsert_crosscutting_uses_stable_entity_id(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_crosscutting: CrosscuttingConcernDef,
        mock_client: MagicMock,
    ):
        """Test upsert_crosscutting uses XC-{slug} entity_id."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-abc"))

        await graphiti_service.upsert_crosscutting(sample_crosscutting)

        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_id"] == "XC-observability"

    @pytest.mark.asyncio
    async def test_upsert_crosscutting_returns_none_when_disabled(
        self,
        graphiti_service_disabled: SystemPlanGraphiti,
        sample_crosscutting: CrosscuttingConcernDef,
    ):
        """Test upsert_crosscutting returns None when disabled."""
        result = await graphiti_service_disabled.upsert_crosscutting(sample_crosscutting)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_crosscutting_returns_none_on_exception(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_crosscutting: CrosscuttingConcernDef,
        mock_client: MagicMock,
    ):
        """Test upsert_crosscutting returns None and logs on exception."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            result = await graphiti_service.upsert_crosscutting(sample_crosscutting)

            assert result is None
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_upsert_crosscutting_sets_crosscutting_concern_entity_type(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_crosscutting: CrosscuttingConcernDef,
        mock_client: MagicMock,
    ):
        """Test upsert_crosscutting sets entity_type to 'crosscutting_concern'."""
        mock_client.upsert_episode = AsyncMock(return_value=MagicMock(uuid="uuid-abc"))

        await graphiti_service.upsert_crosscutting(sample_crosscutting)

        call_kwargs = mock_client.upsert_episode.call_args[1]
        assert call_kwargs["entity_type"] == "crosscutting_concern"


# =========================================================================
# 6. HAS_ARCHITECTURE_CONTEXT TESTS (5 tests)
# =========================================================================


class TestHasArchitectureContext:
    """Tests for has_architecture_context method."""

    @pytest.mark.asyncio
    async def test_has_architecture_context_returns_true_when_found(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test has_architecture_context returns True when context exists."""
        mock_client.search = AsyncMock(
            return_value=[{"fact": "System context exists", "score": 0.9}]
        )

        result = await graphiti_service.has_architecture_context()

        assert result is True

    @pytest.mark.asyncio
    async def test_has_architecture_context_returns_false_when_not_found(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test has_architecture_context returns False when no context."""
        mock_client.search = AsyncMock(return_value=[])

        result = await graphiti_service.has_architecture_context()

        assert result is False

    @pytest.mark.asyncio
    async def test_has_architecture_context_returns_false_when_disabled(
        self,
        graphiti_service_disabled: SystemPlanGraphiti,
    ):
        """Test has_architecture_context returns False when disabled."""
        result = await graphiti_service_disabled.has_architecture_context()
        assert result is False

    @pytest.mark.asyncio
    async def test_has_architecture_context_returns_false_on_exception(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test has_architecture_context returns False on exception."""
        mock_client.search = AsyncMock(side_effect=Exception("Error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            result = await graphiti_service.has_architecture_context()

            assert result is False
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_has_architecture_context_searches_correct_group(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test has_architecture_context searches project_architecture group."""
        mock_client.search = AsyncMock(return_value=[])

        await graphiti_service.has_architecture_context()

        mock_client.search.assert_called_once()
        call_kwargs = mock_client.search.call_args[1]
        assert "project_architecture" in str(call_kwargs)


# =========================================================================
# 7. GET_ARCHITECTURE_SUMMARY TESTS (6 tests)
# =========================================================================


class TestGetArchitectureSummary:
    """Tests for get_architecture_summary method."""

    @pytest.mark.asyncio
    async def test_get_architecture_summary_returns_dict(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_architecture_summary returns dict with components and decisions."""
        mock_client.search = AsyncMock(
            return_value=[
                {"fact": "Component: Order Management", "score": 0.9},
                {"fact": "ADR-SP-001: Use Event Sourcing", "score": 0.85},
            ]
        )

        result = await graphiti_service.get_architecture_summary()

        assert result is not None
        assert isinstance(result, dict)
        assert "facts" in result

    @pytest.mark.asyncio
    async def test_get_architecture_summary_returns_none_when_disabled(
        self,
        graphiti_service_disabled: SystemPlanGraphiti,
    ):
        """Test get_architecture_summary returns None when disabled."""
        result = await graphiti_service_disabled.get_architecture_summary()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_architecture_summary_returns_none_when_no_data(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_architecture_summary returns None when no data found."""
        mock_client.search = AsyncMock(return_value=[])

        result = await graphiti_service.get_architecture_summary()

        assert result is None

    @pytest.mark.asyncio
    async def test_get_architecture_summary_returns_none_on_exception(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_architecture_summary returns None on exception."""
        mock_client.search = AsyncMock(side_effect=Exception("Error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            result = await graphiti_service.get_architecture_summary()

            assert result is None
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_architecture_summary_searches_both_groups(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_architecture_summary searches architecture and decisions groups."""
        mock_client.search = AsyncMock(return_value=[])

        await graphiti_service.get_architecture_summary()

        # Should search for both architecture facts and decisions
        assert mock_client.search.call_count >= 1

    @pytest.mark.asyncio
    async def test_get_architecture_summary_uses_num_results(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_architecture_summary uses num_results parameter."""
        mock_client.search = AsyncMock(return_value=[])

        await graphiti_service.get_architecture_summary()

        call_kwargs = mock_client.search.call_args[1]
        assert "num_results" in call_kwargs


# =========================================================================
# 8. GET_RELEVANT_CONTEXT_FOR_TOPIC TESTS (7 tests)
# =========================================================================


class TestGetRelevantContextForTopic:
    """Tests for get_relevant_context_for_topic method."""

    @pytest.mark.asyncio
    async def test_get_relevant_context_returns_list(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_relevant_context_for_topic returns list of dicts."""
        mock_client.search = AsyncMock(
            return_value=[
                {"fact": "Order uses event sourcing", "uuid": "1", "score": 0.9},
                {"fact": "Inventory uses CQRS", "uuid": "2", "score": 0.8},
            ]
        )

        result = await graphiti_service.get_relevant_context_for_topic(
            topic="order processing", num_results=5
        )

        assert isinstance(result, list)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_get_relevant_context_returns_empty_list_when_disabled(
        self,
        graphiti_service_disabled: SystemPlanGraphiti,
    ):
        """Test get_relevant_context returns empty list when disabled."""
        result = await graphiti_service_disabled.get_relevant_context_for_topic(
            topic="test", num_results=5
        )
        assert result == []

    @pytest.mark.asyncio
    async def test_get_relevant_context_returns_empty_list_on_exception(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_relevant_context returns empty list on exception."""
        mock_client.search = AsyncMock(side_effect=Exception("Error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            result = await graphiti_service.get_relevant_context_for_topic(
                topic="test", num_results=5
            )

            assert result == []
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_relevant_context_uses_topic_as_query(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_relevant_context uses topic as search query."""
        mock_client.search = AsyncMock(return_value=[])

        await graphiti_service.get_relevant_context_for_topic(
            topic="payment processing", num_results=5
        )

        call_args = mock_client.search.call_args
        assert "payment processing" in str(call_args)

    @pytest.mark.asyncio
    async def test_get_relevant_context_uses_num_results(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_relevant_context uses num_results parameter."""
        mock_client.search = AsyncMock(return_value=[])

        await graphiti_service.get_relevant_context_for_topic(
            topic="test", num_results=10
        )

        call_kwargs = mock_client.search.call_args[1]
        assert call_kwargs["num_results"] == 10

    @pytest.mark.asyncio
    async def test_get_relevant_context_searches_both_groups(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_relevant_context searches architecture and decisions groups."""
        mock_client.search = AsyncMock(return_value=[])

        await graphiti_service.get_relevant_context_for_topic(
            topic="test", num_results=5
        )

        # Should include both groups in search
        call_kwargs = mock_client.search.call_args[1]
        assert "group_ids" in call_kwargs

    @pytest.mark.asyncio
    async def test_get_relevant_context_returns_none_when_client_none(
        self,
        graphiti_service_null: SystemPlanGraphiti,
    ):
        """Test get_relevant_context returns empty list when client is None."""
        result = await graphiti_service_null.get_relevant_context_for_topic(
            topic="test", num_results=5
        )
        assert result == []


# =========================================================================
# 9. LOGGING TESTS (4 tests)
# =========================================================================


class TestLogging:
    """Tests for [Graphiti] prefix on log messages."""

    @pytest.mark.asyncio
    async def test_upsert_component_logs_with_graphiti_prefix(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_component: ComponentDef,
        mock_client: MagicMock,
    ):
        """Test upsert_component logs with [Graphiti] prefix."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            await graphiti_service.upsert_component(sample_component)

            call_args = mock_logger.warning.call_args[0][0]
            assert "[Graphiti]" in call_args

    @pytest.mark.asyncio
    async def test_upsert_adr_logs_with_graphiti_prefix(
        self,
        graphiti_service: SystemPlanGraphiti,
        sample_adr: ArchitectureDecision,
        mock_client: MagicMock,
    ):
        """Test upsert_adr logs with [Graphiti] prefix."""
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            await graphiti_service.upsert_adr(sample_adr)

            call_args = mock_logger.warning.call_args[0][0]
            assert "[Graphiti]" in call_args

    @pytest.mark.asyncio
    async def test_has_architecture_context_logs_with_graphiti_prefix(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test has_architecture_context logs with [Graphiti] prefix."""
        mock_client.search = AsyncMock(side_effect=Exception("Error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            await graphiti_service.has_architecture_context()

            call_args = mock_logger.warning.call_args[0][0]
            assert "[Graphiti]" in call_args

    @pytest.mark.asyncio
    async def test_get_relevant_context_logs_with_graphiti_prefix(
        self,
        graphiti_service: SystemPlanGraphiti,
        mock_client: MagicMock,
    ):
        """Test get_relevant_context logs with [Graphiti] prefix."""
        mock_client.search = AsyncMock(side_effect=Exception("Error"))

        with patch("guardkit.planning.graphiti_arch.logger") as mock_logger:
            await graphiti_service.get_relevant_context_for_topic("test", 5)

            call_args = mock_logger.warning.call_args[0][0]
            assert "[Graphiti]" in call_args
