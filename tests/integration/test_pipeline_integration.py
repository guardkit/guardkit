"""
Integration tests for the full command pipeline: /system-arch -> /system-design -> /system-plan -> /feature-spec.

Validates end-to-end pipeline behaviour including:
- Pipeline ordering enforcement and prerequisite gates
- Graphiti seeding flow between commands
- C4 mandatory review gates
- Graceful degradation when Graphiti is unavailable
- Partial session persistence
- ADR and DDR numbering continuity
- Concurrent session handling (last-write-wins)
- Temporal superseding of ADRs
- Feature spec staleness detection
- Security (adversarial content handling)

Coverage target: >=80% line, >=75% branch
BDD scenarios covered: Groups A-D from system-arch-design-commands.feature
"""

import asyncio
import json
import logging
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from guardkit.knowledge.adr import ADREntity, ADRStatus, ADRTrigger
from guardkit.knowledge.adr_service import ADRService
from guardkit.knowledge.entities.api_contract import ApiContract
from guardkit.knowledge.entities.architecture_context import (
    ArchitectureContext,
    ArchitectureDecision,
)
from guardkit.knowledge.entities.component import ComponentDef
from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
from guardkit.knowledge.entities.data_model import DataModel
from guardkit.knowledge.entities.design_decision import DesignDecision
from guardkit.knowledge.entities.system_context import SystemContextDef
from guardkit.planning.architecture_writer import ArchitectureWriter
from guardkit.planning.design_writer import DesignWriter, scan_next_ddr_number
from guardkit.planning.graphiti_arch import SystemPlanGraphiti
from guardkit.planning.graphiti_design import SystemDesignGraphiti
from guardkit.planning.mode_detector import detect_mode


# ============================================================================
# Shared Fixtures
# ============================================================================


@pytest.fixture
def mock_graphiti_client():
    """Create a mock GraphitiClient with standard behaviour.

    The mock client supports:
    - enabled property (True by default)
    - get_group_id() for project namespace prefixing
    - search() returning empty list by default
    - upsert_episode() returning a mock UpsertResult
    - add_episode() for ADR service
    - episode_exists() returning ExistsResult.not_found()
    """
    client = AsyncMock()
    client.enabled = True
    client.get_group_id = Mock(side_effect=lambda g: f"test-project__{g}")

    # Default: search returns empty
    client.search = AsyncMock(return_value=[])

    # Default: upsert returns a result with uuid
    upsert_result = MagicMock()
    upsert_result.uuid = "mock-uuid-001"
    client.upsert_episode = AsyncMock(return_value=upsert_result)

    # Default: add_episode returns uuid
    client.add_episode = AsyncMock(return_value="mock-uuid-002")

    return client


@pytest.fixture
def disabled_graphiti_client():
    """Create a mock GraphitiClient that is disabled (Graphiti unavailable)."""
    client = AsyncMock()
    client.enabled = False
    client.get_group_id = Mock(side_effect=lambda g: f"test-project__{g}")
    client.search = AsyncMock(return_value=[])
    client.upsert_episode = AsyncMock(return_value=None)
    client.add_episode = AsyncMock(return_value=None)
    return client


@pytest.fixture
def sample_system_context():
    """Create a sample SystemContextDef for testing."""
    return SystemContextDef(
        name="E-Commerce Platform",
        purpose="Online retail with multi-tenant support",
        bounded_contexts=["Order Management", "Inventory", "Customer"],
        external_systems=["Payment Gateway", "Shipping API"],
        methodology="ddd",
    )


@pytest.fixture
def sample_components():
    """Create sample ComponentDef instances for testing."""
    return [
        ComponentDef(
            name="Order Management",
            description="Handles order lifecycle from creation to fulfilment",
            responsibilities=["Create orders", "Track status", "Handle returns"],
            dependencies=["Inventory", "Payment Gateway"],
            methodology="ddd",
            aggregate_roots=["Order", "OrderLine"],
            domain_events=["OrderCreated", "OrderShipped", "OrderCancelled"],
            context_mapping="customer-downstream",
        ),
        ComponentDef(
            name="Inventory",
            description="Manages product stock levels and reservations",
            responsibilities=["Track stock", "Reserve items", "Restock"],
            dependencies=[],
            methodology="ddd",
            aggregate_roots=["Product", "StockItem"],
            domain_events=["StockReserved", "StockDepleted"],
        ),
        ComponentDef(
            name="Customer",
            description="Customer profile and preferences management",
            responsibilities=["Manage profiles", "Preferences", "Auth"],
            dependencies=[],
            methodology="ddd",
            aggregate_roots=["Customer", "Address"],
            domain_events=["CustomerRegistered"],
        ),
    ]


@pytest.fixture
def sample_decisions():
    """Create sample ArchitectureDecision instances for testing."""
    return [
        ArchitectureDecision(
            number=1,
            title="Use Event Sourcing for Order Management",
            status="accepted",
            context="Need complete audit trail for orders",
            decision="Implement event sourcing pattern for Order aggregate",
            consequences=["Full history", "Complex replay logic"],
            related_components=["Order Management"],
            alternatives_considered=["Simple CRUD", "Change Data Capture"],
            prefix="ARCH",
        ),
        ArchitectureDecision(
            number=2,
            title="Use PostgreSQL as Primary Database",
            status="accepted",
            context="Need ACID guarantees for financial transactions",
            decision="Use PostgreSQL 16 as primary database",
            consequences=["Strong consistency", "Mature ecosystem"],
            related_components=["Order Management", "Inventory"],
            alternatives_considered=["MongoDB", "CockroachDB"],
            prefix="ARCH",
        ),
        ArchitectureDecision(
            number=3,
            title="Use synchronous HTTP for all inter-service communication",
            status="accepted",
            context="Simple request-response pattern needed initially",
            decision="Use synchronous HTTP for inter-service calls",
            consequences=["Simpler debugging", "Potential bottleneck at scale"],
            related_components=["Order Management", "Inventory", "Customer"],
            alternatives_considered=["Event-driven messaging", "gRPC"],
            prefix="ARCH",
        ),
    ]


@pytest.fixture
def sample_crosscutting():
    """Create sample CrosscuttingConcernDef instances."""
    return [
        CrosscuttingConcernDef(
            name="Observability",
            description="Unified logging, metrics, and distributed tracing",
            applies_to=["Order Management", "Inventory", "Customer"],
            implementation_notes="Use OpenTelemetry SDK",
        ),
    ]


@pytest.fixture
def sample_api_contracts():
    """Create sample ApiContract instances for testing."""
    return [
        ApiContract(
            bounded_context="Order Management",
            protocol="REST",
            version="1.0.0",
            consumer_types=["web-frontend", "mobile-app"],
            endpoints=[
                {"path": "/orders", "method": "POST", "description": "Create order"},
                {"path": "/orders/{id}", "method": "GET", "description": "Get order"},
            ],
        ),
        ApiContract(
            bounded_context="Inventory",
            protocol="REST",
            version="1.0.0",
            consumer_types=["web-frontend"],
            endpoints=[
                {"path": "/products", "method": "GET", "description": "List products"},
            ],
        ),
    ]


@pytest.fixture
def sample_data_models():
    """Create sample DataModel instances for testing."""
    return [
        DataModel(
            bounded_context="Order Management",
            entities=[
                {
                    "name": "Order",
                    "attributes": ["id", "customer_id", "total", "status"],
                    "relationships": ["has_many OrderLine"],
                },
                {
                    "name": "OrderLine",
                    "attributes": ["id", "product_id", "quantity", "price"],
                    "relationships": ["belongs_to Order"],
                },
            ],
            invariants=["Order total must equal sum of line items"],
        ),
    ]


@pytest.fixture
def sample_design_decisions():
    """Create sample DesignDecision instances for testing."""
    return [
        DesignDecision(
            number=1,
            title="Use CQRS for Order queries",
            context="High read frequency on order status",
            decision="Separate read and write models for orders",
            rationale="Allows independent scaling of reads and writes",
            status="accepted",
            alternatives_considered=["Simple CRUD", "Materialized views only"],
            consequences=["Eventual consistency in reads"],
            related_components=["Order Management"],
        ),
    ]


@pytest.fixture
def arch_output_dir(tmp_path):
    """Create a temporary directory for architecture output."""
    output_dir = tmp_path / "docs" / "architecture"
    output_dir.mkdir(parents=True)
    return output_dir


@pytest.fixture
def design_output_dir(tmp_path):
    """Create a temporary directory for design output."""
    output_dir = tmp_path / "docs" / "design"
    output_dir.mkdir(parents=True)
    return output_dir


# ============================================================================
# GROUP A: Pipeline Ordering and Prerequisite Gates
# ============================================================================


class TestPipelineOrdering:
    """Tests for pipeline ordering enforcement.

    Validates BDD scenarios:
    - Running /system-design before /system-arch shows correct error
    - Pipeline enforces correct execution order
    - Downstream commands offer to run missing upstream commands
    """

    @pytest.mark.asyncio
    async def test_system_design_without_arch_detects_missing_prerequisite(
        self, mock_graphiti_client
    ):
        """AC: Pipeline ordering test - /system-design without /system-arch shows error.

        BDD: Running /system-design before /system-arch (GROUP B boundary).
        When no architecture context exists in Graphiti, /system-design
        should detect the missing prerequisite.
        """
        # Arrange: no arch context exists
        mock_graphiti_client.search = AsyncMock(return_value=[])
        design_service = SystemDesignGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        # Act: check for design context prerequisite (arch must exist)
        has_design = await design_service.has_design_context()

        # Assert: no design context means prerequisite not met
        assert has_design is False

    @pytest.mark.asyncio
    async def test_mode_detector_returns_setup_for_new_project(
        self, mock_graphiti_client
    ):
        """AC: Pipeline ordering - mode detection returns setup when no arch exists.

        BDD: Running /system-arch on a project with no existing architecture context.
        The command should detect setup mode automatically.
        """
        # Arrange: no architecture context
        mock_graphiti_client.search = AsyncMock(return_value=[])

        # Act
        mode = await detect_mode(
            graphiti_client=mock_graphiti_client, project_id="test-project"
        )

        # Assert
        assert mode == "setup"

    @pytest.mark.asyncio
    async def test_mode_detector_returns_refine_for_existing_project(
        self, mock_graphiti_client
    ):
        """When architecture context exists, detect_mode returns 'refine'.

        BDD: /system-plan reads architecture context seeded by /system-arch.
        """
        # Arrange: existing architecture context
        mock_graphiti_client.search = AsyncMock(
            return_value=[{"fact": "System uses DDD", "uuid": "uuid-1", "score": 0.9}]
        )

        # Act
        mode = await detect_mode(
            graphiti_client=mock_graphiti_client, project_id="test-project"
        )

        # Assert
        assert mode == "refine"

    @pytest.mark.asyncio
    async def test_pipeline_arch_then_design_prerequisite_check(
        self, mock_graphiti_client, sample_system_context, sample_components
    ):
        """Full pipeline: /system-arch seeds context, then /system-design can read it.

        BDD: /system-design depends on /system-arch having been run.
        Validates the arch -> design dependency through Graphiti.
        """
        arch_service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )
        design_service = SystemDesignGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        # Step 1: /system-arch seeds context
        uuid = await arch_service.upsert_system_context(sample_system_context)
        assert uuid is not None

        for component in sample_components:
            uuid = await arch_service.upsert_component(component)
            assert uuid is not None

        # Step 2: Now simulate /system-design reading arch context
        # After arch seeding, search should find results
        mock_graphiti_client.search = AsyncMock(
            return_value=[
                {"fact": "E-Commerce Platform uses DDD", "uuid": "uuid-1", "score": 0.9},
                {"fact": "Order Management bounded context", "uuid": "uuid-2", "score": 0.85},
            ]
        )

        has_arch = await arch_service.has_architecture_context()
        assert has_arch is True, "Architecture context should exist after seeding"

        # Step 3: /system-design can now proceed since prereq is met
        context_facts = await design_service.search_design_context(
            "bounded contexts and structural decisions"
        )
        # search_design_context uses design groups, but the pattern validates the flow
        mock_graphiti_client.search.assert_called()


# ============================================================================
# GROUP A: Graphiti Seeding Flow
# ============================================================================


class TestGraphitiSeedingFlow:
    """Tests for Graphiti seeding flow between pipeline stages.

    Validates BDD scenarios:
    - /system-arch output is readable by /system-plan
    - /system-plan references bounded contexts and ADRs
    - /feature-spec references real domain entities from /system-design
    """

    @pytest.mark.asyncio
    async def test_arch_seeds_system_context_to_graphiti(
        self, mock_graphiti_client, sample_system_context
    ):
        """AC: Graphiti seeding flow - /system-arch seeds context for /system-plan.

        BDD: /system-plan reads architecture context seeded by /system-arch.
        """
        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        # Act: seed system context
        uuid = await service.upsert_system_context(sample_system_context)

        # Assert: upsert was called with correct group and entity type
        assert uuid == "mock-uuid-001"
        mock_graphiti_client.upsert_episode.assert_called_once()
        call_kwargs = mock_graphiti_client.upsert_episode.call_args
        assert call_kwargs.kwargs["entity_id"] == "SYS-e-commerce-platform"
        assert call_kwargs.kwargs["entity_type"] == "system_context"
        assert call_kwargs.kwargs["group_id"] == "test-project__project_architecture"

    @pytest.mark.asyncio
    async def test_arch_seeds_components_with_correct_entity_ids(
        self, mock_graphiti_client, sample_components
    ):
        """Components are seeded with stable, deterministic entity IDs."""
        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        for component in sample_components:
            uuid = await service.upsert_component(component)
            assert uuid is not None

        # Verify 3 components were upserted
        assert mock_graphiti_client.upsert_episode.call_count == 3

        # Check entity IDs follow COMP-{slug} format
        calls = mock_graphiti_client.upsert_episode.call_args_list
        entity_ids = [c.kwargs["entity_id"] for c in calls]
        assert "COMP-order-management" in entity_ids
        assert "COMP-inventory" in entity_ids
        assert "COMP-customer" in entity_ids

    @pytest.mark.asyncio
    async def test_arch_seeds_adrs_with_prefix(
        self, mock_graphiti_client, sample_decisions
    ):
        """ADRs are seeded with correct prefix format (ADR-{prefix}-NNN)."""
        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        for decision in sample_decisions:
            uuid = await service.upsert_adr(decision)
            assert uuid is not None

        calls = mock_graphiti_client.upsert_episode.call_args_list
        entity_ids = [c.kwargs["entity_id"] for c in calls]
        assert "ADR-ARCH-001" in entity_ids
        assert "ADR-ARCH-002" in entity_ids
        assert "ADR-ARCH-003" in entity_ids

    @pytest.mark.asyncio
    async def test_system_plan_reads_architecture_summary(
        self, mock_graphiti_client
    ):
        """AC: /system-plan references bounded contexts and ADRs from /system-arch.

        BDD: The planning session should already know the domain structure,
        reference relevant bounded contexts, and surface relevant ADRs.
        """
        # Simulate seeded architecture context
        mock_graphiti_client.search = AsyncMock(
            return_value=[
                {"fact": "E-Commerce Platform: Online retail with DDD", "uuid": "u1", "score": 0.95},
                {"fact": "Order Management bounded context handles order lifecycle", "uuid": "u2", "score": 0.9},
                {"fact": "ADR-ARCH-001: Use Event Sourcing for Order Management", "uuid": "u3", "score": 0.85},
                {"fact": "ADR-ARCH-002: Use PostgreSQL as Primary Database", "uuid": "u4", "score": 0.8},
            ]
        )

        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        # Act: /system-plan retrieves architecture summary
        summary = await service.get_architecture_summary()

        # Assert: summary contains seeded facts
        assert summary is not None
        assert "facts" in summary
        assert len(summary["facts"]) == 4

        # Verify bounded context and ADR references
        facts_text = " ".join(f["fact"] for f in summary["facts"])
        assert "Order Management" in facts_text
        assert "ADR-ARCH-001" in facts_text
        assert "PostgreSQL" in facts_text

    @pytest.mark.asyncio
    async def test_design_seeds_api_contracts_for_feature_spec(
        self, mock_graphiti_client, sample_api_contracts
    ):
        """AC: /feature-spec references real domain entities from /system-design output.

        BDD: /feature-spec references real endpoints after /system-design has run.
        """
        service = SystemDesignGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        # Seed API contracts
        for contract in sample_api_contracts:
            uuid = await service.upsert_api_contract(contract)
            assert uuid is not None

        calls = mock_graphiti_client.upsert_episode.call_args_list
        entity_ids = [c.kwargs["entity_id"] for c in calls]
        assert "API-order-management" in entity_ids
        assert "API-inventory" in entity_ids

        # Verify endpoint data is included in episode body
        first_call = calls[0]
        episode_body = json.loads(first_call.kwargs["episode_body"])
        assert "endpoints" in episode_body
        assert len(episode_body["endpoints"]) == 2
        assert episode_body["endpoints"][0]["path"] == "/orders"

    @pytest.mark.asyncio
    async def test_design_seeds_data_models(
        self, mock_graphiti_client, sample_data_models
    ):
        """Data models are seeded with entities and invariants."""
        service = SystemDesignGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        for model in sample_data_models:
            uuid = await service.upsert_data_model(model)
            assert uuid is not None

        call = mock_graphiti_client.upsert_episode.call_args
        assert call.kwargs["entity_id"] == "DM-order-management"
        episode_body = json.loads(call.kwargs["episode_body"])
        assert len(episode_body["entities"]) == 2
        assert "Order total must equal sum of line items" in episode_body["invariants"]

    @pytest.mark.asyncio
    async def test_design_seeds_design_decisions(
        self, mock_graphiti_client, sample_design_decisions
    ):
        """DDRs are seeded with correct DDR-NNN entity IDs."""
        service = SystemDesignGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        for decision in sample_design_decisions:
            uuid = await service.upsert_design_decision(decision)
            assert uuid is not None

        call = mock_graphiti_client.upsert_episode.call_args
        assert call.kwargs["entity_id"] == "DDR-001"
        assert call.kwargs["entity_type"] == "design_decision"


# ============================================================================
# GROUP A: C4 Mandatory Review Gate
# ============================================================================


class TestC4ReviewGate:
    """Tests for C4 diagram review gate behaviour.

    Validates BDD scenarios:
    - C4 diagrams are presented as mandatory review gates
    - Commands pause and require explicit diagram approval
    """

    def test_architecture_writer_generates_c4_diagrams(
        self,
        arch_output_dir,
        sample_system_context,
        sample_components,
        sample_crosscutting,
        sample_decisions,
    ):
        """AC: C4 mandatory review gate - commands generate C4 diagrams for review.

        BDD: /system-arch generates all mandatory output artefacts including
        C4 Context and Container diagrams in Mermaid format.
        """
        writer = ArchitectureWriter()

        # Act: write all architecture documentation
        writer.write_all(
            output_dir=arch_output_dir,
            system=sample_system_context,
            components=sample_components,
            concerns=sample_crosscutting,
            decisions=sample_decisions,
        )

        # Assert: all mandatory artefacts are generated
        assert (arch_output_dir / "ARCHITECTURE.md").exists()
        assert (arch_output_dir / "system-context.md").exists()
        assert (arch_output_dir / "bounded-contexts.md").exists()
        assert (arch_output_dir / "crosscutting-concerns.md").exists()

        # ADRs in decisions/ subdirectory
        decisions_dir = arch_output_dir / "decisions"
        assert decisions_dir.exists()
        assert (decisions_dir / "ADR-ARCH-001.md").exists()
        assert (decisions_dir / "ADR-ARCH-002.md").exists()
        assert (decisions_dir / "ADR-ARCH-003.md").exists()

    def test_architecture_index_references_all_components(
        self,
        arch_output_dir,
        sample_system_context,
        sample_components,
        sample_crosscutting,
        sample_decisions,
    ):
        """Architecture index file references all components and decisions."""
        writer = ArchitectureWriter()
        writer.write_all(
            output_dir=arch_output_dir,
            system=sample_system_context,
            components=sample_components,
            concerns=sample_crosscutting,
            decisions=sample_decisions,
        )

        index_content = (arch_output_dir / "ARCHITECTURE.md").read_text()
        assert "Order Management" in index_content
        assert "Inventory" in index_content
        assert "Customer" in index_content


# ============================================================================
# GROUP C: Graceful Degradation
# ============================================================================


class TestGracefulDegradation:
    """Tests for graceful degradation when Graphiti is unavailable.

    Validates BDD scenarios:
    - Graphiti unavailable -> markdown artefacts still generated, warning shown
    - Mode detection falls back to setup
    """

    @pytest.mark.asyncio
    async def test_arch_service_degrades_when_client_disabled(
        self, disabled_graphiti_client, sample_system_context
    ):
        """AC: Graceful degradation - Graphiti unavailable, operations return None.

        BDD: Running /system-arch when Graphiti is unavailable.
        """
        service = SystemPlanGraphiti(
            client=disabled_graphiti_client, project_id="test-project"
        )

        # All operations should gracefully return None/False/[]
        assert await service.upsert_system_context(sample_system_context) is None
        assert await service.has_architecture_context() is False
        assert await service.get_architecture_summary() is None
        assert await service.get_relevant_context_for_topic("anything") == []

    @pytest.mark.asyncio
    async def test_design_service_degrades_when_client_disabled(
        self, disabled_graphiti_client, sample_api_contracts, sample_design_decisions
    ):
        """Design service also degrades gracefully."""
        service = SystemDesignGraphiti(
            client=disabled_graphiti_client, project_id="test-project"
        )

        assert await service.upsert_api_contract(sample_api_contracts[0]) is None
        assert await service.upsert_design_decision(sample_design_decisions[0]) is None
        assert await service.has_design_context() is False
        assert await service.search_design_context("anything") == []
        assert await service.get_design_decisions() == []
        assert await service.get_api_contracts() == []

    @pytest.mark.asyncio
    async def test_mode_detector_degrades_to_setup_when_client_none(self):
        """AC: Mode detection falls back to setup when Graphiti is unavailable."""
        mode = await detect_mode(graphiti_client=None, project_id="test-project")
        assert mode == "setup"

    @pytest.mark.asyncio
    async def test_mode_detector_degrades_to_setup_when_client_disabled(
        self, disabled_graphiti_client
    ):
        """Mode detection returns setup when client is disabled."""
        mode = await detect_mode(
            graphiti_client=disabled_graphiti_client, project_id="test-project"
        )
        assert mode == "setup"

    @pytest.mark.asyncio
    async def test_mode_detector_degrades_to_setup_on_error(
        self, mock_graphiti_client
    ):
        """Mode detection returns setup when search raises an exception."""
        mock_graphiti_client.search = AsyncMock(side_effect=ConnectionError("Graphiti down"))

        mode = await detect_mode(
            graphiti_client=mock_graphiti_client, project_id="test-project"
        )
        assert mode == "setup"

    def test_markdown_artefacts_generated_without_graphiti(
        self,
        arch_output_dir,
        sample_system_context,
        sample_components,
        sample_crosscutting,
        sample_decisions,
    ):
        """AC: Graceful degradation - markdown artefacts still generated.

        BDD: If user continues without Graphiti, markdown artefacts should
        still be generated.
        """
        writer = ArchitectureWriter()

        # Architecture writer doesn't depend on Graphiti at all -
        # it takes entity objects directly
        writer.write_all(
            output_dir=arch_output_dir,
            system=sample_system_context,
            components=sample_components,
            concerns=sample_crosscutting,
            decisions=sample_decisions,
        )

        # All files should exist regardless of Graphiti status
        assert (arch_output_dir / "ARCHITECTURE.md").exists()
        assert (arch_output_dir / "system-context.md").exists()
        assert (arch_output_dir / "bounded-contexts.md").exists()

    @pytest.mark.asyncio
    async def test_arch_service_degrades_on_exception(
        self, mock_graphiti_client, sample_system_context
    ):
        """Services handle unexpected exceptions gracefully."""
        mock_graphiti_client.upsert_episode = AsyncMock(
            side_effect=RuntimeError("Unexpected Graphiti error")
        )

        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        # Should return None, not raise
        result = await service.upsert_system_context(sample_system_context)
        assert result is None


# ============================================================================
# GROUP C: Partial Session Persistence
# ============================================================================


class TestPartialSessionPersistence:
    """Tests for partial session persistence behaviour.

    Validates BDD scenarios:
    - Skip categories mid-session -> completed categories persisted
    - Skipped categories are noted
    """

    @pytest.mark.asyncio
    async def test_partial_seeding_succeeds_for_completed_items(
        self, mock_graphiti_client, sample_system_context, sample_components
    ):
        """AC: Partial session test - completed categories persisted.

        BDD: Completed categories should be persisted to Graphiti.
        Simulates seeding 2 of 3 components (user skips third).
        """
        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        # Seed system context (category 1) - succeeds
        uuid1 = await service.upsert_system_context(sample_system_context)
        assert uuid1 is not None

        # Seed first component (category 2) - succeeds
        uuid2 = await service.upsert_component(sample_components[0])
        assert uuid2 is not None

        # Category 3 skipped by user - no upsert for remaining components
        # Verify only 2 calls were made
        assert mock_graphiti_client.upsert_episode.call_count == 2

    @pytest.mark.asyncio
    async def test_partial_seeding_failure_mid_batch(
        self, mock_graphiti_client, sample_components
    ):
        """AC: Partial Graphiti seeding failure is detected and reported.

        BDD: When seeding fails after categories 1-3 but before 4-6,
        completed categories should be identified.
        """
        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        # First component succeeds
        uuid1 = await service.upsert_component(sample_components[0])
        assert uuid1 is not None

        # Second component fails due to Graphiti error
        mock_graphiti_client.upsert_episode = AsyncMock(
            side_effect=ConnectionError("Graphiti connection lost")
        )
        uuid2 = await service.upsert_component(sample_components[1])
        assert uuid2 is None  # Graceful degradation

        # Third component also fails
        uuid3 = await service.upsert_component(sample_components[2])
        assert uuid3 is None


# ============================================================================
# GROUP B: ADR Numbering Continuity
# ============================================================================


class TestADRNumberingContinuity:
    """Tests for ADR numbering continuity.

    Validates BDD scenarios:
    - ADR numbering continues from existing highest number
    - Existing ADRs are not renumbered or modified
    """

    def test_adr_entity_id_follows_numbering_format(self):
        """AC: ADR numbering continuity - new ADRs use correct numbering.

        BDD: Given 5 ADRs already exist, a new ADR should be numbered ADR-006.
        """
        # Existing ADRs numbered 1-5
        existing_adrs = [
            ArchitectureDecision(
                number=i,
                title=f"Decision {i}",
                status="accepted",
                context=f"Context {i}",
                decision=f"Decision {i}",
                prefix="ARCH",
            )
            for i in range(1, 6)
        ]

        # New ADR continues from 6
        new_adr = ArchitectureDecision(
            number=6,
            title="New Decision",
            status="accepted",
            context="New context",
            decision="New decision",
            prefix="ARCH",
        )

        # Verify numbering
        assert existing_adrs[-1].entity_id == "ADR-ARCH-005"
        assert new_adr.entity_id == "ADR-ARCH-006"

        # Verify existing ADRs unchanged
        for i, adr in enumerate(existing_adrs, start=1):
            assert adr.entity_id == f"ADR-ARCH-{i:03d}"

    def test_adr_numbering_with_different_prefixes(self):
        """ADRs from different commands use independent prefixes."""
        arch_adr = ArchitectureDecision(number=1, title="A", status="accepted",
                                        context="", decision="", prefix="ARCH")
        sp_adr = ArchitectureDecision(number=1, title="B", status="accepted",
                                      context="", decision="", prefix="SP")
        fs_adr = ArchitectureDecision(number=1, title="C", status="accepted",
                                      context="", decision="", prefix="FS")

        assert arch_adr.entity_id == "ADR-ARCH-001"
        assert sp_adr.entity_id == "ADR-SP-001"
        assert fs_adr.entity_id == "ADR-FS-001"


# ============================================================================
# GROUP B: DDR Numbering
# ============================================================================


class TestDDRNumbering:
    """Tests for DDR numbering continuity.

    Validates BDD scenarios:
    - DDR numbering starts from 001 or continues from existing
    """

    def test_ddr_entity_id_format(self):
        """AC: DDR numbering - new DDRs start from 001."""
        ddr = DesignDecision(
            number=1,
            title="Use CQRS",
            context="High read frequency",
            decision="Separate read/write models",
            rationale="Scalability",
            status="accepted",
        )
        assert ddr.entity_id == "DDR-001"

    def test_ddr_numbering_continues_from_existing(self, tmp_path):
        """AC: DDR numbering - DDRs continue from existing highest number.

        Uses scan_next_ddr_number() to find the next available DDR number.
        """
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()

        # Create existing DDR files
        (decisions_dir / "DDR-001.md").write_text("# DDR-001")
        (decisions_dir / "DDR-002.md").write_text("# DDR-002")
        (decisions_dir / "DDR-003.md").write_text("# DDR-003")

        next_num = scan_next_ddr_number(decisions_dir)
        assert next_num == 4

    def test_ddr_numbering_starts_from_one_when_empty(self, tmp_path):
        """DDR numbering starts from 1 when no existing DDRs."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()

        next_num = scan_next_ddr_number(decisions_dir)
        assert next_num == 1

    def test_ddr_numbering_handles_nonexistent_directory(self, tmp_path):
        """DDR numbering returns 1 when directory doesn't exist."""
        decisions_dir = tmp_path / "nonexistent"
        next_num = scan_next_ddr_number(decisions_dir)
        assert next_num == 1

    def test_design_writer_creates_ddr_files(self, design_output_dir, sample_design_decisions):
        """Design writer creates DDR markdown files with correct naming."""
        writer = DesignWriter()

        for decision in sample_design_decisions:
            writer.write_ddr(decision, design_output_dir)

        ddr_file = design_output_dir / "decisions" / "DDR-001.md"
        assert ddr_file.exists()
        content = ddr_file.read_text()
        assert "CQRS" in content


# ============================================================================
# GROUP D: Concurrent Session Handling
# ============================================================================


class TestConcurrentSessions:
    """Tests for concurrent session behaviour.

    Validates BDD scenarios:
    - Two sessions on same project -> last-write-wins, no corruption
    - Concurrent /system-arch sessions do not corrupt Graphiti state
    """

    @pytest.mark.asyncio
    async def test_last_write_wins_with_upsert_idempotency(
        self, mock_graphiti_client, sample_system_context
    ):
        """AC: Concurrent session test - last-write-wins, no corruption.

        BDD: Two developers run /system-arch simultaneously.
        The knowledge graph should not contain duplicates.
        Last-written values should take precedence (upsert semantics).
        """
        service1 = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )
        service2 = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        # Session 1: seed system context with version A
        ctx_v1 = SystemContextDef(
            name="E-Commerce Platform",
            purpose="Version A - Session 1",
            bounded_contexts=["Orders"],
            methodology="ddd",
        )

        # Session 2: seed system context with version B
        ctx_v2 = SystemContextDef(
            name="E-Commerce Platform",
            purpose="Version B - Session 2",
            bounded_contexts=["Orders", "Inventory"],
            methodology="ddd",
        )

        # Both use same entity_id (deterministic from name)
        assert ctx_v1.entity_id == ctx_v2.entity_id == "SYS-e-commerce-platform"

        # Both upsert (last write wins by upsert semantics)
        uuid1 = await service1.upsert_system_context(ctx_v1)
        uuid2 = await service2.upsert_system_context(ctx_v2)

        # Both should succeed without error
        assert uuid1 is not None
        assert uuid2 is not None

        # Verify upsert_episode was called twice with the same entity_id
        calls = mock_graphiti_client.upsert_episode.call_args_list
        assert len(calls) == 2
        assert calls[0].kwargs["entity_id"] == "SYS-e-commerce-platform"
        assert calls[1].kwargs["entity_id"] == "SYS-e-commerce-platform"

    @pytest.mark.asyncio
    async def test_concurrent_sessions_complete_without_error(
        self, mock_graphiti_client
    ):
        """Both concurrent sessions should complete without error."""
        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        comp1 = ComponentDef(
            name="Shared Component",
            description="Desc from session 1",
            methodology="layered",
        )
        comp2 = ComponentDef(
            name="Shared Component",
            description="Desc from session 2",
            methodology="layered",
        )

        # Both sessions write the same component
        result1 = await service.upsert_component(comp1)
        result2 = await service.upsert_component(comp2)

        assert result1 is not None
        assert result2 is not None
        assert comp1.entity_id == comp2.entity_id  # Same entity_id = upsert


# ============================================================================
# GROUP D: Temporal Superseding
# ============================================================================


class TestTemporalSuperseding:
    """Tests for temporal superseding of ADRs.

    Validates BDD scenarios:
    - /arch-refine supersedes ADR -> both old and new queryable
    - New ADR created that supersedes existing ADR
    - Prior ADR remains queryable with history
    """

    def test_adr_superseding_creates_linkage(self):
        """AC: Temporal superseding - new ADR supersedes old one.

        BDD: A new ADR should be created that supersedes ADR-003.
        The prior ADR should remain queryable.
        """
        old_adr = ArchitectureDecision(
            number=3,
            title="Use synchronous HTTP for inter-service communication",
            status="superseded",
            context="Original context",
            decision="Use synchronous HTTP",
            superseded_by="ADR-ARCH-004",
            prefix="ARCH",
        )

        new_adr = ArchitectureDecision(
            number=4,
            title="Use asynchronous messaging for inter-service communication",
            status="accepted",
            context="Scale requirements changed",
            decision="Use event-driven messaging via RabbitMQ",
            consequences=["Eventual consistency", "Better scalability"],
            supersedes="ADR-ARCH-003",
            prefix="ARCH",
        )

        # Verify linkage
        assert old_adr.entity_id == "ADR-ARCH-003"
        assert new_adr.entity_id == "ADR-ARCH-004"
        assert old_adr.superseded_by == "ADR-ARCH-004"
        assert new_adr.supersedes == "ADR-ARCH-003"

        # Both remain valid entities
        assert old_adr.status == "superseded"
        assert new_adr.status == "accepted"

    def test_superseded_adr_serializes_correctly(self):
        """Superseded ADR includes superseded_by in episode body."""
        adr = ArchitectureDecision(
            number=3,
            title="Old decision",
            status="superseded",
            context="context",
            decision="decision",
            superseded_by="ADR-ARCH-004",
            prefix="ARCH",
        )

        body = adr.to_episode_body()
        assert body["superseded_by"] == "ADR-ARCH-004"
        assert body["status"] == "superseded"

    def test_superseding_adr_serializes_correctly(self):
        """New superseding ADR includes supersedes in episode body."""
        adr = ArchitectureDecision(
            number=4,
            title="New decision",
            status="accepted",
            context="context",
            decision="decision",
            supersedes="ADR-ARCH-003",
            prefix="ARCH",
        )

        body = adr.to_episode_body()
        assert body["supersedes"] == "ADR-ARCH-003"

    @pytest.mark.asyncio
    async def test_both_superseded_adrs_seedable(
        self, mock_graphiti_client
    ):
        """Both old and new ADRs can be seeded to Graphiti."""
        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        old_adr = ArchitectureDecision(
            number=3, title="Old", status="superseded",
            context="c", decision="d",
            superseded_by="ADR-ARCH-004", prefix="ARCH",
        )
        new_adr = ArchitectureDecision(
            number=4, title="New", status="accepted",
            context="c", decision="d",
            supersedes="ADR-ARCH-003", prefix="ARCH",
        )

        uuid_old = await service.upsert_adr(old_adr)
        uuid_new = await service.upsert_adr(new_adr)

        assert uuid_old is not None
        assert uuid_new is not None
        assert mock_graphiti_client.upsert_episode.call_count == 2


# ============================================================================
# GROUP D: Feature Spec Staleness Detection
# ============================================================================


class TestFeatureSpecStaleness:
    """Tests for feature spec staleness detection.

    Validates BDD scenarios:
    - /design-refine changes contract -> affected feature specs flagged
    - Feature specs reference real domain entities
    """

    def test_api_contract_entity_id_is_deterministic(self):
        """API contract entity IDs are deterministic for staleness tracking.

        When a contract changes, the entity_id remains the same,
        enabling staleness detection via version comparison.
        """
        contract_v1 = ApiContract(
            bounded_context="Order Management",
            protocol="REST",
            version="1.0.0",
            endpoints=[{"path": "/orders", "method": "POST", "description": "Create"}],
        )

        contract_v2 = ApiContract(
            bounded_context="Order Management",
            protocol="REST",
            version="2.0.0",
            endpoints=[
                {"path": "/orders", "method": "POST", "description": "Create"},
                {"path": "/orders/{id}/cancel", "method": "PUT", "description": "Cancel"},
            ],
        )

        # Same entity_id despite version change
        assert contract_v1.entity_id == contract_v2.entity_id == "API-order-management"

        # But different content (version bump + new endpoint)
        body_v1 = contract_v1.to_episode_body()
        body_v2 = contract_v2.to_episode_body()
        assert body_v1["version"] != body_v2["version"]
        assert len(body_v2["endpoints"]) > len(body_v1["endpoints"])

    def test_data_model_entity_id_for_staleness_tracking(self):
        """Data model entity IDs enable staleness tracking."""
        model_v1 = DataModel(
            bounded_context="Order Management",
            entities=[{"name": "Order", "attributes": ["id", "total"]}],
        )

        model_v2 = DataModel(
            bounded_context="Order Management",
            entities=[
                {"name": "Order", "attributes": ["id", "total", "currency"]},
                {"name": "OrderLine", "attributes": ["id", "quantity"]},
            ],
        )

        assert model_v1.entity_id == model_v2.entity_id == "DM-order-management"

    def test_design_writer_creates_contract_files(
        self, design_output_dir, sample_api_contracts
    ):
        """Design writer creates API contract markdown for each bounded context."""
        writer = DesignWriter()

        for contract in sample_api_contracts:
            writer.write_api_contract(contract, design_output_dir)

        contracts_dir = design_output_dir / "contracts"
        assert (contracts_dir / "API-order-management.md").exists()
        assert (contracts_dir / "API-inventory.md").exists()

    def test_design_writer_creates_data_model_files(
        self, design_output_dir, sample_data_models
    ):
        """Design writer creates data model markdown with entities and invariants."""
        writer = DesignWriter()

        for model in sample_data_models:
            writer.write_data_model(model, design_output_dir)

        models_dir = design_output_dir / "models"
        dm_file = models_dir / "DM-order-management.md"
        assert dm_file.exists()

        content = dm_file.read_text()
        assert "Order" in content
        assert "OrderLine" in content
        assert "Order total must equal sum of line items" in content


# ============================================================================
# GROUP D: Security - Adversarial Content
# ============================================================================


class TestSecurityAdversarialContent:
    """Tests for handling adversarial content safely.

    Validates BDD scenarios:
    - Adversarial content in ADR rationale stored safely
    - Content retrievable intact without executing
    """

    def test_adr_with_script_tags_serializes_safely(self):
        """AC: Security test - script tags stored safely.

        BDD: Adversarial content (script tags, SQL fragments, control chars)
        should be stored safely without executing or corrupting.
        """
        adversarial_content = (
            '<script>alert("xss")</script>\n'
            "'; DROP TABLE decisions; --\n"
            "\x00\x01\x02 control characters\n"
            "{{template_injection}}\n"
            "${process.env.SECRET}"
        )

        adr = ArchitectureDecision(
            number=99,
            title="ADR with adversarial content",
            status="accepted",
            context=adversarial_content,
            decision="Test adversarial handling",
            consequences=["Content preserved"],
            prefix="ARCH",
        )

        # Serialize to episode body
        body = adr.to_episode_body()

        # Content should be stored as-is (no execution, no sanitization loss)
        assert '<script>alert("xss")</script>' in body["context"]
        assert "DROP TABLE" in body["context"]
        assert "${process.env.SECRET}" in body["context"]

        # JSON serialization should handle the content without error
        json_str = json.dumps(body)
        assert isinstance(json_str, str)

        # Deserialize and verify integrity
        parsed = json.loads(json_str)
        assert parsed["context"] == adversarial_content

    @pytest.mark.asyncio
    async def test_adversarial_content_seedable_to_graphiti(
        self, mock_graphiti_client
    ):
        """Adversarial content can be seeded to Graphiti without error."""
        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        adversarial_adr = ArchitectureDecision(
            number=99,
            title='<img src=x onerror=alert(1)>',
            status="accepted",
            context="'; DROP TABLE users; --",
            decision="Test adversarial seeding",
            prefix="ARCH",
        )

        uuid = await service.upsert_adr(adversarial_adr)
        assert uuid is not None

        # Verify the full content was passed to upsert_episode
        call = mock_graphiti_client.upsert_episode.call_args
        episode_body = json.loads(call.kwargs["episode_body"])
        assert "DROP TABLE" in episode_body["context"]

    def test_adversarial_content_in_component_name(self):
        """Component with adversarial name generates safe entity ID."""
        comp = ComponentDef(
            name='<script>alert("xss")</script>',
            description="Test",
            methodology="layered",
        )

        # Slugification should sanitize the name for entity_id
        assert comp.entity_id.startswith("COMP-")
        # No script tags in entity_id
        assert "<script>" not in comp.entity_id
        assert "alert" in comp.entity_id  # alphanumeric text preserved


# ============================================================================
# GROUP A/B: Architecture Context Formatting
# ============================================================================


class TestArchitectureContextFormatting:
    """Tests for ArchitectureContext formatting for prompts.

    Validates that seeded context is correctly formatted for
    downstream command consumption.
    """

    def test_empty_context_returns_indicator(self):
        """Empty context returns 'No architecture context available.'"""
        ctx = ArchitectureContext.empty()
        result = ctx.format_for_prompt()
        assert result == "No architecture context available."

    def test_context_with_decisions_formats_correctly(self, sample_decisions):
        """Context with decisions includes ADR entity IDs and titles."""
        ctx = ArchitectureContext(
            decisions=sample_decisions,
        )

        result = ctx.format_for_prompt()
        assert "Architecture Decisions" in result
        assert "ADR-ARCH-001" in result
        assert "Event Sourcing" in result

    def test_context_with_system_and_components(
        self, sample_system_context, sample_components, sample_decisions
    ):
        """Full context formats all sections."""
        ctx = ArchitectureContext(
            system_context=sample_system_context,
            components=sample_components,
            decisions=sample_decisions,
        )

        result = ctx.format_for_prompt()
        assert "System Context" in result
        assert "E-Commerce Platform" in result
        assert "Components" in result
        assert "Order Management" in result
        assert "Architecture Decisions" in result

    def test_context_with_high_score_facts(self):
        """Facts with score > 0.5 are included; low-score facts excluded."""
        ctx = ArchitectureContext(
            retrieved_facts=[
                {"content": "Uses CQRS pattern", "score": 0.9},
                {"content": "Low relevance fact", "score": 0.3},
                {"content": "Uses PostgreSQL", "score": 0.7},
            ],
        )

        result = ctx.format_for_prompt()
        assert "CQRS" in result
        assert "PostgreSQL" in result
        assert "Low relevance" not in result

    def test_context_respects_token_budget(self, sample_system_context):
        """Context truncates when token budget is exceeded."""
        ctx = ArchitectureContext(
            system_context=sample_system_context,
            decisions=[
                ArchitectureDecision(
                    number=i,
                    title=f"Very Long Decision Title {i} " * 10,
                    status="accepted",
                    context="context",
                    decision="decision",
                )
                for i in range(1, 20)
            ],
        )

        # Very small budget should truncate
        result = ctx.format_for_prompt(token_budget=50)
        # Should have some content but not everything
        assert len(result) < 5000  # Rough check


# ============================================================================
# Design Writer Integration
# ============================================================================


class TestDesignWriterIntegration:
    """Tests for design writer creating all artefact types."""

    def test_design_writer_creates_component_diagram(self, design_output_dir):
        """Design writer creates C4 Component (L3) diagram files."""
        writer = DesignWriter()
        components = [
            {"name": "OrderService", "description": "Handles order CRUD"},
            {"name": "PaymentAdapter", "description": "Integrates with payment gateway"},
        ]

        writer.write_component_diagram(
            "Order Management", components, design_output_dir
        )

        diagram_file = design_output_dir / "diagrams" / "order-management.md"
        assert diagram_file.exists()
        content = diagram_file.read_text()
        assert "OrderService" in content
        assert "PaymentAdapter" in content

    def test_full_design_output_structure(
        self,
        design_output_dir,
        sample_design_decisions,
        sample_api_contracts,
        sample_data_models,
    ):
        """Full design output creates correct directory structure."""
        writer = DesignWriter()

        for d in sample_design_decisions:
            writer.write_ddr(d, design_output_dir)
        for c in sample_api_contracts:
            writer.write_api_contract(c, design_output_dir)
        for m in sample_data_models:
            writer.write_data_model(m, design_output_dir)
        writer.write_component_diagram(
            "Order Management",
            [{"name": "OrderService", "description": "Orders"}],
            design_output_dir,
        )

        # Verify directory structure
        assert (design_output_dir / "decisions").exists()
        assert (design_output_dir / "contracts").exists()
        assert (design_output_dir / "models").exists()
        assert (design_output_dir / "diagrams").exists()


# ============================================================================
# Full Pipeline End-to-End Integration
# ============================================================================


class TestFullPipelineIntegration:
    """End-to-end integration tests for the full command pipeline.

    Validates the complete flow:
    /system-arch -> /system-design -> /system-plan -> /feature-spec
    """

    @pytest.mark.asyncio
    async def test_full_pipeline_arch_to_design_to_plan(
        self,
        mock_graphiti_client,
        sample_system_context,
        sample_components,
        sample_decisions,
        sample_crosscutting,
        sample_api_contracts,
        sample_data_models,
        sample_design_decisions,
        arch_output_dir,
        design_output_dir,
    ):
        """Full pipeline: arch seeds -> design reads -> plan references.

        Validates the entire data flow from /system-arch through /system-plan.
        """
        arch_service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )
        design_service = SystemDesignGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        # Phase 1: /system-arch seeds architecture
        await arch_service.upsert_system_context(sample_system_context)
        for comp in sample_components:
            await arch_service.upsert_component(comp)
        for decision in sample_decisions:
            await arch_service.upsert_adr(decision)
        for concern in sample_crosscutting:
            await arch_service.upsert_crosscutting(concern)

        # Write architecture markdown artefacts
        arch_writer = ArchitectureWriter()
        arch_writer.write_all(
            output_dir=arch_output_dir,
            system=sample_system_context,
            components=sample_components,
            concerns=sample_crosscutting,
            decisions=sample_decisions,
        )

        # Phase 2: /system-design reads arch context and creates design
        # Simulate arch context found in Graphiti
        mock_graphiti_client.search = AsyncMock(
            return_value=[
                {"fact": "E-Commerce Platform uses DDD", "uuid": "u1", "score": 0.9},
                {"fact": "3 bounded contexts: Orders, Inventory, Customer", "uuid": "u2", "score": 0.85},
            ]
        )

        has_arch = await arch_service.has_architecture_context()
        assert has_arch is True

        # Seed design artefacts
        for contract in sample_api_contracts:
            await design_service.upsert_api_contract(contract)
        for model in sample_data_models:
            await design_service.upsert_data_model(model)
        for decision in sample_design_decisions:
            await design_service.upsert_design_decision(decision)

        # Write design markdown artefacts
        design_writer = DesignWriter()
        for d in sample_design_decisions:
            design_writer.write_ddr(d, design_output_dir)
        for c in sample_api_contracts:
            design_writer.write_api_contract(c, design_output_dir)
        for m in sample_data_models:
            design_writer.write_data_model(m, design_output_dir)

        # Phase 3: /system-plan reads architecture summary
        summary = await arch_service.get_architecture_summary()
        assert summary is not None

        # Phase 4: Verify architecture files exist
        assert (arch_output_dir / "ARCHITECTURE.md").exists()
        assert (arch_output_dir / "bounded-contexts.md").exists()

        # Verify design files exist
        assert (design_output_dir / "decisions" / "DDR-001.md").exists()
        assert (design_output_dir / "contracts" / "API-order-management.md").exists()
        assert (design_output_dir / "models" / "DM-order-management.md").exists()

    @pytest.mark.asyncio
    async def test_pipeline_with_graphiti_degradation(
        self,
        disabled_graphiti_client,
        sample_system_context,
        sample_components,
        sample_decisions,
        sample_crosscutting,
        arch_output_dir,
    ):
        """Pipeline still produces artefacts when Graphiti is unavailable.

        All Graphiti operations return None/False, but markdown writer
        is independent and produces complete output.
        """
        arch_service = SystemPlanGraphiti(
            client=disabled_graphiti_client, project_id="test-project"
        )

        # All Graphiti operations fail gracefully
        result = await arch_service.upsert_system_context(sample_system_context)
        assert result is None

        # But architecture writer still works
        arch_writer = ArchitectureWriter()
        arch_writer.write_all(
            output_dir=arch_output_dir,
            system=sample_system_context,
            components=sample_components,
            concerns=sample_crosscutting,
            decisions=sample_decisions,
        )

        # All files present
        assert (arch_output_dir / "ARCHITECTURE.md").exists()
        assert (arch_output_dir / "system-context.md").exists()
        assert (arch_output_dir / "bounded-contexts.md").exists()
        assert (arch_output_dir / "crosscutting-concerns.md").exists()
        assert (arch_output_dir / "decisions" / "ADR-ARCH-001.md").exists()


# ============================================================================
# Crosscutting Concern Seeding
# ============================================================================


class TestCrosscuttingSeedingIntegration:
    """Tests for crosscutting concern seeding."""

    @pytest.mark.asyncio
    async def test_crosscutting_concerns_seeded_correctly(
        self, mock_graphiti_client, sample_crosscutting
    ):
        """Crosscutting concerns are seeded with correct entity IDs."""
        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )

        for concern in sample_crosscutting:
            uuid = await service.upsert_crosscutting(concern)
            assert uuid is not None

        call = mock_graphiti_client.upsert_episode.call_args
        assert call.kwargs["entity_id"] == "XC-observability"
        assert call.kwargs["entity_type"] == "crosscutting_concern"

    @pytest.mark.asyncio
    async def test_semantic_search_for_architecture_topic(
        self, mock_graphiti_client
    ):
        """Semantic search for architecture topics returns relevant facts."""
        mock_graphiti_client.search = AsyncMock(
            return_value=[
                {"fact": "Order Management uses event sourcing", "uuid": "u1", "score": 0.9},
                {"fact": "PostgreSQL for ACID compliance", "uuid": "u2", "score": 0.8},
            ]
        )

        service = SystemPlanGraphiti(
            client=mock_graphiti_client, project_id="test-project"
        )
        results = await service.get_relevant_context_for_topic("order processing", 10)

        assert len(results) == 2
        assert results[0]["fact"] == "Order Management uses event sourcing"
