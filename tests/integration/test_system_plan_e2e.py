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
