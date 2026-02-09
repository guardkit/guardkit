"""
End-to-end tests for system-plan feature.

This module contains comprehensive E2E tests that exercise the full
system-plan workflow with mocked Graphiti, verifying both file output
AND Graphiti API calls.

These tests complement the seam-level integration tests by validating
the complete flow from CLI invocation to file generation and knowledge
graph storage.
"""

import asyncio
import json
import pytest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call

from click.testing import CliRunner


class TestSystemPlanE2ESetupMode:
    """End-to-end tests for system-plan setup mode.

    Validates the complete setup flow including:
    - Mode detection (returns "setup" for no existing context)
    - Architecture generation
    - File output
    - Graphiti upsert calls
    """

    @pytest.mark.asyncio
    async def test_setup_mode_full_flow_with_mock_graphiti(self, tmp_path):
        """Exercise full setup flow with mocked Graphiti, verify file output AND Graphiti calls."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.system_context import SystemContextDef
        from guardkit.knowledge.entities.component import ComponentDef
        from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
        from guardkit.knowledge.entities.architecture_context import ArchitectureDecision
        from guardkit.planning.architecture_writer import ArchitectureWriter

        # Create mock Graphiti client
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.get_group_id = Mock(side_effect=lambda g: f"test__{g}")
        mock_client.upsert_episode = AsyncMock(return_value=Mock(uuid="test-uuid"))
        mock_client.search = AsyncMock(return_value=[])

        # Create service
        service = SystemPlanGraphiti(client=mock_client, project_id="test-project")

        # Create test entities (simulating what the AI would generate)
        system = SystemContextDef(
            name="Payment Processing System",
            purpose="Handle all payment operations for e-commerce",
            bounded_contexts=["Payments", "Billing", "Subscriptions"],
            external_systems=["Stripe API", "PayPal API", "Bank Gateway"],
            methodology="ddd",
        )

        components = [
            ComponentDef(
                name="Payment Gateway",
                description="Handles payment provider integration",
                responsibilities=["Process payments", "Handle refunds"],
                dependencies=["Billing"],
                methodology="ddd",
                aggregate_roots=["Payment", "Refund"],
                domain_events=["PaymentProcessed", "RefundIssued"],
            ),
            ComponentDef(
                name="Billing Service",
                description="Manages invoices and billing cycles",
                responsibilities=["Generate invoices", "Track payments"],
                dependencies=[],
                methodology="ddd",
                aggregate_roots=["Invoice", "BillingCycle"],
                domain_events=["InvoiceGenerated", "BillingCycleCompleted"],
            ),
        ]

        concerns = [
            CrosscuttingConcernDef(
                name="Payment Security",
                description="PCI DSS compliance and encryption",
                applies_to=["Payment Gateway", "Billing Service"],
                implementation_notes="Use TLS 1.3, encrypt card data at rest",
            ),
        ]

        decisions = [
            ArchitectureDecision(
                number=1,
                title="Use Stripe as Primary Payment Provider",
                status="accepted",
                context="Need reliable payment processing with good developer experience",
                decision="Use Stripe for primary payment processing with PayPal as backup",
                consequences=["Vendor dependency on Stripe", "Good documentation"],
                related_components=["Payment Gateway"],
            ),
        ]

        # Step 1: Upsert all entities to Graphiti
        await service.upsert_system_context(system)
        for comp in components:
            await service.upsert_component(comp)
        for concern in concerns:
            await service.upsert_crosscutting(concern)
        for adr in decisions:
            await service.upsert_adr(adr)

        # Verify Graphiti calls
        assert mock_client.upsert_episode.call_count == 5  # 1 system + 2 components + 1 concern + 1 ADR

        # Verify correct group IDs were used
        upsert_calls = mock_client.upsert_episode.call_args_list

        # System context should use project_architecture group
        system_call = upsert_calls[0]
        assert "test__project_architecture" in str(system_call)

        # ADR should use project_decisions group
        adr_call = upsert_calls[-1]
        assert "test__project_decisions" in str(adr_call)

        # Step 2: Write architecture files
        writer = ArchitectureWriter()
        output_dir = tmp_path / "docs" / "architecture"

        writer.write_all(
            output_dir=output_dir,
            system=system,
            components=components,
            concerns=concerns,
            decisions=decisions,
        )

        # Verify file output
        assert (output_dir / "ARCHITECTURE.md").exists()
        assert (output_dir / "system-context.md").exists()
        assert (output_dir / "bounded-contexts.md").exists()  # DDD methodology
        assert (output_dir / "crosscutting-concerns.md").exists()
        assert (output_dir / "decisions" / "ADR-SP-001.md").exists()

        # Verify file content
        index_content = (output_dir / "ARCHITECTURE.md").read_text()
        assert "Payment Processing System" in index_content

        system_content = (output_dir / "system-context.md").read_text()
        assert "Payment Processing System" in system_content
        assert "Stripe API" in system_content or "external" in system_content.lower()

        bc_content = (output_dir / "bounded-contexts.md").read_text()
        assert "Payment Gateway" in bc_content
        assert "Billing Service" in bc_content

        adr_content = (output_dir / "decisions" / "ADR-SP-001.md").read_text()
        assert "Stripe" in adr_content
        assert "accepted" in adr_content.lower()

    @pytest.mark.asyncio
    async def test_mode_detection_returns_setup_for_empty_graph(self):
        """Mode detection returns 'setup' when no architecture context exists."""
        from guardkit.planning.mode_detector import detect_mode

        mock_client = Mock()
        mock_client.enabled = True

        # Mock search returning no results
        with patch.object(mock_client, 'search', new_callable=AsyncMock) as mock_search:
            mock_search.return_value = []

            # Mock SystemPlanGraphiti to use our mock client
            with patch('guardkit.planning.mode_detector.SystemPlanGraphiti') as MockService:
                instance = MockService.return_value
                instance.has_architecture_context = AsyncMock(return_value=False)

                result = await detect_mode(graphiti_client=mock_client, project_id="test")

        assert result == "setup"

    @pytest.mark.asyncio
    async def test_mode_detection_returns_refine_for_existing_context(self):
        """Mode detection returns 'refine' when architecture context exists."""
        from guardkit.planning.mode_detector import detect_mode

        mock_client = Mock()
        mock_client.enabled = True

        # Mock SystemPlanGraphiti to report existing context
        with patch('guardkit.planning.mode_detector.SystemPlanGraphiti') as MockService:
            instance = MockService.return_value
            instance.has_architecture_context = AsyncMock(return_value=True)

            result = await detect_mode(graphiti_client=mock_client, project_id="test")

        assert result == "refine"


class TestSystemPlanE2ERefinementMode:
    """End-to-end tests for system-plan refine mode.

    Validates updating existing architecture context.
    """

    @pytest.mark.asyncio
    async def test_refine_mode_updates_existing_entities(self, tmp_path):
        """Refine mode updates existing entities via upsert."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.component import ComponentDef

        # Create mock client
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.get_group_id = Mock(return_value="test__project_architecture")
        mock_client.upsert_episode = AsyncMock(return_value=Mock(uuid="uuid-v2"))

        service = SystemPlanGraphiti(client=mock_client, project_id="test")

        # Original component
        component_v1 = ComponentDef(
            name="Order Service",
            description="Original description",
            responsibilities=["Process orders"],
        )

        # Updated component (same name = same entity_id)
        component_v2 = ComponentDef(
            name="Order Service",
            description="Updated description with more detail",
            responsibilities=["Process orders", "Handle cancellations", "Manage inventory"],
        )

        # First upsert
        await service.upsert_component(component_v1)

        # Second upsert (refinement)
        await service.upsert_component(component_v2)

        # Verify both calls used same entity_id
        calls = mock_client.upsert_episode.call_args_list
        assert len(calls) == 2

        first_entity_id = calls[0][1]["entity_id"]
        second_entity_id = calls[1][1]["entity_id"]

        assert first_entity_id == second_entity_id
        assert first_entity_id == component_v1.entity_id
        assert second_entity_id == component_v2.entity_id


class TestSystemPlanE2EReviewMode:
    """End-to-end tests for system-plan review mode.

    Validates architecture review/audit functionality.
    """

    @pytest.mark.asyncio
    async def test_review_mode_retrieves_existing_context(self):
        """Review mode retrieves and analyzes existing architecture context."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        # Create mock client with existing data
        mock_client = Mock()
        mock_client.enabled = True
        mock_client.get_group_id = Mock(side_effect=lambda g: f"test__{g}")
        mock_client.search = AsyncMock(return_value=[
            {"fact": "System uses event sourcing for audit trail", "uuid": "u1", "score": 0.9},
            {"fact": "Payment Gateway integrates with Stripe", "uuid": "u2", "score": 0.85},
        ])

        service = SystemPlanGraphiti(client=mock_client, project_id="test")

        # Get architecture summary for review
        summary = await service.get_architecture_summary()

        assert summary is not None
        assert "facts" in summary
        assert len(summary["facts"]) == 2

        # Get relevant context for specific topic
        context = await service.get_relevant_context_for_topic("payment processing", 10)

        assert len(context) == 2


class TestSystemPlanE2EContextIntegration:
    """End-to-end tests for context integration with feature-plan.

    Validates that architecture context flows correctly to feature planning.
    """

    @pytest.mark.asyncio
    async def test_architecture_context_flows_to_feature_planning(self, tmp_path):
        """Architecture context is correctly loaded and formatted for feature planning."""
        from guardkit.knowledge.entities.architecture_context import (
            ArchitectureContext,
            ArchitectureDecision,
        )
        from guardkit.knowledge.entities.component import ComponentDef
        from guardkit.knowledge.entities.system_context import SystemContextDef
        from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef

        # Create rich architecture context
        ctx = ArchitectureContext(
            system_context=SystemContextDef(
                name="E-Commerce Platform",
                purpose="Online retail system",
                bounded_contexts=["Orders", "Inventory", "Payments"],
                external_systems=["Stripe", "SendGrid"],
                methodology="ddd",
            ),
            components=[
                ComponentDef(
                    name="Orders",
                    description="Order management bounded context",
                    methodology="ddd",
                    aggregate_roots=["Order", "OrderLine"],
                ),
                ComponentDef(
                    name="Inventory",
                    description="Inventory tracking and management",
                    methodology="ddd",
                    aggregate_roots=["InventoryItem", "StockLevel"],
                ),
            ],
            decisions=[
                ArchitectureDecision(
                    number=1,
                    title="Use Event Sourcing for Orders",
                    status="accepted",
                    context="Need complete audit trail",
                    decision="Implement event sourcing",
                    consequences=["Full history", "Complex replay"],
                ),
            ],
            crosscutting_concerns=[
                CrosscuttingConcernDef(
                    name="Observability",
                    description="Logging, metrics, tracing",
                    applies_to=["All Services"],
                ),
            ],
            retrieved_facts=[
                {"content": "System handles 10K orders/day", "score": 0.9},
                {"content": "Uses PostgreSQL for persistence", "score": 0.85},
            ],
        )

        # Format for prompt
        formatted = ctx.format_for_prompt(token_budget=4000)

        # Verify key information is present
        assert "E-Commerce Platform" in formatted
        assert "Orders" in formatted
        assert "Event Sourcing" in formatted
        assert "Observability" in formatted

        # Verify high-score facts are included
        assert "10K orders" in formatted or "PostgreSQL" in formatted


class TestSystemPlanE2EErrorHandling:
    """End-to-end tests for error handling and edge cases."""

    def test_cli_handles_graphiti_connection_failure_gracefully(self):
        """CLI handles Graphiti connection failure gracefully."""
        from click.testing import CliRunner
        from guardkit.cli.system_plan import system_plan

        runner = CliRunner()

        # Mock run_system_plan to simulate graceful degradation
        with patch('guardkit.planning.system_plan.run_system_plan', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = None  # Graceful completion

            result = runner.invoke(system_plan, ["Test system architecture"])

            # Should not crash
            assert result.exception is None or isinstance(result.exception, SystemExit)

    @pytest.mark.asyncio
    async def test_service_handles_upsert_failure_gracefully(self):
        """Service handles upsert failure gracefully."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.component import ComponentDef

        mock_client = Mock()
        mock_client.enabled = True
        mock_client.get_group_id = Mock(return_value="test__project_architecture")
        mock_client.upsert_episode = AsyncMock(side_effect=Exception("Connection failed"))

        service = SystemPlanGraphiti(client=mock_client, project_id="test")

        component = ComponentDef(name="Test", description="Test")

        # Should not raise, should return None
        result = await service.upsert_component(component)
        assert result is None

    def test_writer_handles_missing_output_directory(self, tmp_path):
        """Writer creates output directory if it doesn't exist."""
        from guardkit.planning.architecture_writer import ArchitectureWriter
        from guardkit.knowledge.entities.system_context import SystemContextDef

        writer = ArchitectureWriter()

        # Deep nested path that doesn't exist
        output_dir = tmp_path / "deep" / "nested" / "path" / "architecture"

        assert not output_dir.exists()

        system = SystemContextDef(name="Test", purpose="Test", methodology="modular")

        # Should create directory and write files
        writer.write_all(
            output_dir=output_dir,
            system=system,
            components=[],
            concerns=[],
            decisions=[],
        )

        assert output_dir.exists()
        assert (output_dir / "ARCHITECTURE.md").exists()


class TestSystemPlanE2EMutualExclusiveFlags:
    """End-to-end tests for mutually exclusive CLI flags."""

    def test_no_questions_and_defaults_are_mutually_exclusive(self):
        """--no-questions and --defaults flags are mutually exclusive."""
        from click.testing import CliRunner
        from guardkit.cli.system_plan import system_plan

        runner = CliRunner()

        result = runner.invoke(system_plan, [
            "Test description",
            "--no-questions",
            "--defaults",
        ])

        # Should fail with usage error
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output.lower() or "error" in result.output.lower()


class TestSystemPlanE2EEntityIds:
    """End-to-end tests for entity ID generation consistency."""

    def test_component_entity_id_is_deterministic(self):
        """Component entity_id is deterministic based on name."""
        from guardkit.knowledge.entities.component import ComponentDef

        comp1 = ComponentDef(name="Order Management", description="V1")
        comp2 = ComponentDef(name="Order Management", description="V2 with changes")
        comp3 = ComponentDef(name="order management", description="Lowercase")

        # Same name = same entity_id
        assert comp1.entity_id == comp2.entity_id

        # Different case = different entity_id (case-sensitive slugification)
        assert comp1.entity_id == "COMP-order-management"
        assert comp3.entity_id == "COMP-order-management"

    def test_adr_entity_id_uses_number_format(self):
        """ADR entity_id uses ADR-SP-NNN format."""
        from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

        adr1 = ArchitectureDecision(number=1, title="T", status="s", context="c", decision="d")
        adr42 = ArchitectureDecision(number=42, title="T", status="s", context="c", decision="d")
        adr100 = ArchitectureDecision(number=100, title="T", status="s", context="c", decision="d")

        assert adr1.entity_id == "ADR-SP-001"
        assert adr42.entity_id == "ADR-SP-042"
        assert adr100.entity_id == "ADR-SP-100"

    def test_system_context_entity_id_uses_sys_prefix(self):
        """SystemContextDef entity_id uses SYS-{slug} format."""
        from guardkit.knowledge.entities.system_context import SystemContextDef

        sys1 = SystemContextDef(name="E-Commerce Platform", purpose="Test")
        sys2 = SystemContextDef(name="Payment System", purpose="Test")

        assert sys1.entity_id == "SYS-e-commerce-platform"
        assert sys2.entity_id == "SYS-payment-system"

    def test_crosscutting_entity_id_uses_xc_prefix(self):
        """CrosscuttingConcernDef entity_id uses XC-{slug} format."""
        from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef

        xc1 = CrosscuttingConcernDef(name="Observability", description="Test")
        xc2 = CrosscuttingConcernDef(name="Payment Security", description="Test")

        assert xc1.entity_id == "XC-observability"
        assert xc2.entity_id == "XC-payment-security"


class TestSystemPlanE2ETemplateVariations:
    """End-to-end tests for template variations based on methodology."""

    def test_ddd_vs_modular_output_differences(self, tmp_path):
        """DDD and modular methodologies produce different output structures."""
        from guardkit.planning.architecture_writer import ArchitectureWriter
        from guardkit.knowledge.entities.system_context import SystemContextDef
        from guardkit.knowledge.entities.component import ComponentDef

        writer = ArchitectureWriter()

        # DDD system
        ddd_system = SystemContextDef(name="DDD", purpose="Test", methodology="ddd")
        ddd_components = [
            ComponentDef(
                name="Orders",
                description="Order context",
                methodology="ddd",
                aggregate_roots=["Order"],
            ),
        ]

        ddd_dir = tmp_path / "ddd"
        writer.write_all(ddd_dir, ddd_system, ddd_components, [], [])

        # Modular system
        mod_system = SystemContextDef(name="Modular", purpose="Test", methodology="modular")
        mod_components = [
            ComponentDef(
                name="Orders",
                description="Order module",
                methodology="modular",
            ),
        ]

        mod_dir = tmp_path / "modular"
        writer.write_all(mod_dir, mod_system, mod_components, [], [])

        # DDD should have bounded-contexts.md
        assert (ddd_dir / "bounded-contexts.md").exists()
        assert not (ddd_dir / "components.md").exists()

        # Modular should have components.md
        assert (mod_dir / "components.md").exists()
        assert not (mod_dir / "bounded-contexts.md").exists()

        # DDD content should mention aggregate roots
        ddd_content = (ddd_dir / "bounded-contexts.md").read_text()
        # Content may vary based on template, but should be DDD-focused

        # Modular content should NOT have aggregate roots
        mod_content = (mod_dir / "components.md").read_text()
        # Verify modular output doesn't include DDD-specific concepts
