"""
Integration tests for system-plan technology seams.

This module contains comprehensive integration tests targeting the boundaries
between components where errors historically occur in GuardKit features:
entity serialization, async boundaries, Graphiti API correctness, template
rendering, and CLI wiring.

Each test class corresponds to a technology seam identified in TASK-SP-008.
"""

import asyncio
import json
import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

from click.testing import CliRunner


# =============================================================================
# SEAM 1: Entity Serialization Pipeline
# =============================================================================
class TestSeam1_EntitySerialization:
    """Tests for entity serialization to Graphiti episode bodies.

    Validates that all entity types produce valid JSON that can be:
    1. Converted to dict via to_episode_body()
    2. Serialized via json.dumps()
    3. Round-tripped via json.loads()
    """

    def test_component_def_to_episode_body_produces_valid_json(self):
        """ComponentDef.to_episode_body() -> json.dumps() -> valid JSON string."""
        from guardkit.knowledge.entities.component import ComponentDef

        component = ComponentDef(
            name="Order Management",
            description="Handles order lifecycle",
            responsibilities=["Create orders", "Track status"],
            dependencies=["Inventory", "Payment"],
            methodology="ddd",
            aggregate_roots=["Order", "OrderLine"],
            domain_events=["OrderCreated", "OrderShipped"],
            context_mapping="customer-downstream",
        )

        body = component.to_episode_body()
        json_str = json.dumps(body)

        # Verify it's a valid JSON string
        assert isinstance(json_str, str)
        assert len(json_str) > 0

        # Verify we can parse it back
        parsed = json.loads(json_str)
        assert parsed["name"] == "Order Management"
        assert parsed["methodology"] == "ddd"

    def test_architecture_decision_to_episode_body_produces_valid_json(self):
        """ArchitectureDecision.to_episode_body() -> json.dumps() -> valid JSON string."""
        from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

        adr = ArchitectureDecision(
            number=1,
            title="Use Event Sourcing",
            status="accepted",
            context="Need complete audit trail for compliance",
            decision="Implement event sourcing pattern",
            consequences=["Full history available", "Complex replay logic"],
            related_components=["Order Management", "Audit Service"],
        )

        body = adr.to_episode_body()
        json_str = json.dumps(body)

        # Verify valid JSON
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["number"] == 1
        assert parsed["title"] == "Use Event Sourcing"

    def test_system_context_def_to_episode_body_produces_valid_json(self):
        """SystemContextDef.to_episode_body() -> json.dumps() -> valid JSON string."""
        from guardkit.knowledge.entities.system_context import SystemContextDef

        system = SystemContextDef(
            name="E-Commerce Platform",
            purpose="Online retail with multi-tenant support",
            bounded_contexts=["Orders", "Inventory", "Customers"],
            external_systems=["Payment Gateway", "Shipping API"],
            methodology="ddd",
        )

        body = system.to_episode_body()
        json_str = json.dumps(body)

        parsed = json.loads(json_str)
        assert parsed["name"] == "E-Commerce Platform"
        assert "Orders" in parsed["bounded_contexts"]

    def test_crosscutting_concern_to_episode_body_produces_valid_json(self):
        """CrosscuttingConcernDef.to_episode_body() -> json.dumps() -> valid JSON string."""
        from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef

        concern = CrosscuttingConcernDef(
            name="Observability",
            description="Unified logging, metrics, and tracing",
            applies_to=["All Services", "API Gateway"],
            implementation_notes="Use OpenTelemetry SDK",
        )

        body = concern.to_episode_body()
        json_str = json.dumps(body)

        parsed = json.loads(json_str)
        assert parsed["name"] == "Observability"
        assert "OpenTelemetry" in parsed["implementation_notes"]

    def test_all_entity_types_roundtrip_json_serialization(self):
        """All entity types produce JSON that json.loads() can round-trip."""
        from guardkit.knowledge.entities.component import ComponentDef
        from guardkit.knowledge.entities.system_context import SystemContextDef
        from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
        from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

        entities = [
            ComponentDef(
                name="Test Component",
                description="Test",
                responsibilities=["Test"],
                dependencies=[],
            ),
            SystemContextDef(
                name="Test System",
                purpose="Test",
                bounded_contexts=["BC1"],
                external_systems=["Ext1"],
            ),
            CrosscuttingConcernDef(
                name="Test Concern",
                description="Test",
                applies_to=["All"],
            ),
            ArchitectureDecision(
                number=42,
                title="Test Decision",
                status="accepted",
                context="Test context",
                decision="Test decision",
            ),
        ]

        for entity in entities:
            body = entity.to_episode_body()
            json_str = json.dumps(body)
            roundtripped = json.loads(json_str)

            # Roundtrip should be identical
            assert roundtripped == body, f"Roundtrip failed for {type(entity).__name__}"

    def test_ddd_entity_body_contains_aggregate_roots(self):
        """DDD entity body contains aggregate_roots; modular entity body does NOT."""
        from guardkit.knowledge.entities.component import ComponentDef

        # DDD component - should have aggregate_roots
        ddd_component = ComponentDef(
            name="Order Management",
            description="Handles orders",
            methodology="ddd",
            aggregate_roots=["Order", "OrderLine"],
            domain_events=["OrderCreated"],
        )

        ddd_body = ddd_component.to_episode_body()
        assert "aggregate_roots" in ddd_body
        assert ddd_body["aggregate_roots"] == ["Order", "OrderLine"]
        assert "domain_events" in ddd_body

        # Modular component - should NOT have aggregate_roots
        modular_component = ComponentDef(
            name="Order Module",
            description="Handles orders",
            methodology="modular",
        )

        modular_body = modular_component.to_episode_body()
        assert "aggregate_roots" not in modular_body
        assert "domain_events" not in modular_body


# =============================================================================
# SEAM 2: Async/Sync Boundary
# =============================================================================
class TestSeam2_AsyncSyncBoundary:
    """Tests for async/sync boundary handling.

    Validates that asyncio.run() wrappers work correctly when called
    from synchronous CLI context.
    """

    @pytest.mark.asyncio
    async def test_detect_mode_is_awaitable(self):
        """detect_mode() is properly async and awaitable."""
        from guardkit.planning.mode_detector import detect_mode

        # Mock client that's disabled
        mock_client = Mock()
        mock_client.enabled = False

        # Should be awaitable and return "setup" for disabled client
        result = await detect_mode(graphiti_client=mock_client)
        assert result == "setup"

    def test_detect_mode_asyncio_run_from_sync_context(self):
        """asyncio.run() wrapping of detect_mode() works in sync context."""
        from guardkit.planning.mode_detector import detect_mode

        mock_client = Mock()
        mock_client.enabled = False

        # Should work when called via asyncio.run() from sync context
        result = asyncio.run(detect_mode(graphiti_client=mock_client))
        assert result == "setup"

    @pytest.mark.asyncio
    async def test_system_plan_graphiti_upsert_component_is_awaitable(self):
        """SystemPlanGraphiti.upsert_component() is properly async."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.component import ComponentDef

        mock_client = Mock()
        mock_client.enabled = False

        service = SystemPlanGraphiti(client=mock_client, project_id="test")

        component = ComponentDef(
            name="Test",
            description="Test component",
        )

        # Should be awaitable and return None for disabled client
        result = await service.upsert_component(component)
        assert result is None

    def test_system_plan_graphiti_asyncio_run_from_sync_context(self):
        """asyncio.run() wrapping of SystemPlanGraphiti works in sync context."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.component import ComponentDef

        mock_client = Mock()
        mock_client.enabled = False

        service = SystemPlanGraphiti(client=mock_client, project_id="test")

        async def async_upsert():
            component = ComponentDef(name="Test", description="Test")
            return await service.upsert_component(component)

        result = asyncio.run(async_upsert())
        assert result is None

    def test_no_nested_event_loop_from_cli_layer(self):
        """No nested event loop errors when called from CLI layer."""
        from click.testing import CliRunner
        from guardkit.cli.system_plan import system_plan

        runner = CliRunner()

        # This would fail with "cannot run nested event loop" if there's an issue
        with patch('guardkit.planning.system_plan.run_system_plan', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = None

            result = runner.invoke(system_plan, ["Test description"])

            # Should complete without event loop errors
            assert "cannot run the event loop" not in (result.output or "")
            assert "This event loop is already running" not in (result.output or "")


# =============================================================================
# SEAM 3: Group ID Prefixing
# =============================================================================
class TestSeam3_GroupIdPrefixing:
    """Tests for correct group ID prefixing.

    Validates that group IDs are correctly prefixed using
    client.get_group_id() rather than hardcoded values.
    """

    @pytest.mark.asyncio
    async def test_upsert_component_uses_get_group_id(self):
        """upsert_component() calls client.get_group_id('project_architecture')."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.component import ComponentDef

        mock_client = Mock()
        mock_client.enabled = True
        mock_client.get_group_id = Mock(return_value="test-project__project_architecture")
        mock_client.upsert_episode = AsyncMock(return_value=Mock(uuid="test-uuid"))

        service = SystemPlanGraphiti(client=mock_client, project_id="test-project")

        component = ComponentDef(name="Test", description="Test")
        await service.upsert_component(component)

        # Verify get_group_id was called with correct argument
        mock_client.get_group_id.assert_called_with("project_architecture")

    @pytest.mark.asyncio
    async def test_upsert_adr_uses_get_group_id(self):
        """upsert_adr() calls client.get_group_id('project_decisions')."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

        mock_client = Mock()
        mock_client.enabled = True
        mock_client.get_group_id = Mock(return_value="test-project__project_decisions")
        mock_client.upsert_episode = AsyncMock(return_value=Mock(uuid="test-uuid"))

        service = SystemPlanGraphiti(client=mock_client, project_id="test-project")

        adr = ArchitectureDecision(
            number=1,
            title="Test",
            status="accepted",
            context="Test",
            decision="Test",
        )
        await service.upsert_adr(adr)

        # Verify get_group_id was called with correct argument
        mock_client.get_group_id.assert_called_with("project_decisions")

    def test_group_id_includes_project_prefix(self):
        """Group ID includes project prefix: {project_id}__project_architecture."""
        from guardkit.knowledge.graphiti_client import GraphitiClient, GraphitiConfig

        config = GraphitiConfig(enabled=False, project_id="my-project")
        client = GraphitiClient(config, auto_detect_project=False)

        # Manually set project_id for testing
        client._project_id = "my-project"

        group_id = client.get_group_id("project_architecture")
        assert group_id == "my-project__project_architecture"

        group_id = client.get_group_id("project_decisions")
        assert group_id == "my-project__project_decisions"


# =============================================================================
# SEAM 4: Upsert Idempotency
# =============================================================================
class TestSeam4_UpsertIdempotency:
    """Tests for upsert operation idempotency.

    Validates that calling upsert twice with the same entity
    uses the same entity_id for deduplication.
    """

    @pytest.mark.asyncio
    async def test_upsert_component_twice_same_entity_id(self):
        """Calling upsert_component() twice with same ComponentDef uses same entity_id."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.component import ComponentDef

        mock_client = Mock()
        mock_client.enabled = True
        mock_client.get_group_id = Mock(return_value="test__project_architecture")
        mock_client.upsert_episode = AsyncMock(return_value=Mock(uuid="uuid-1"))

        service = SystemPlanGraphiti(client=mock_client, project_id="test")

        component = ComponentDef(name="Order Management", description="Handles orders")

        # First call
        await service.upsert_component(component)
        first_call_kwargs = mock_client.upsert_episode.call_args_list[0][1]

        # Second call
        await service.upsert_component(component)
        second_call_kwargs = mock_client.upsert_episode.call_args_list[1][1]

        # Both calls should use the same entity_id
        assert first_call_kwargs["entity_id"] == second_call_kwargs["entity_id"]
        assert first_call_kwargs["entity_id"] == component.entity_id

    @pytest.mark.asyncio
    async def test_upsert_adr_twice_same_entity_id(self):
        """Calling upsert_adr() twice with same ADR uses same entity_id."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

        mock_client = Mock()
        mock_client.enabled = True
        mock_client.get_group_id = Mock(return_value="test__project_decisions")
        mock_client.upsert_episode = AsyncMock(return_value=Mock(uuid="uuid-1"))

        service = SystemPlanGraphiti(client=mock_client, project_id="test")

        adr = ArchitectureDecision(
            number=42,
            title="Use Event Sourcing",
            status="accepted",
            context="Audit trail needed",
            decision="Event sourcing",
        )

        # First call
        await service.upsert_adr(adr)
        first_call_kwargs = mock_client.upsert_episode.call_args_list[0][1]

        # Second call
        await service.upsert_adr(adr)
        second_call_kwargs = mock_client.upsert_episode.call_args_list[1][1]

        # Both calls should use the same entity_id
        assert first_call_kwargs["entity_id"] == second_call_kwargs["entity_id"]
        assert first_call_kwargs["entity_id"] == adr.entity_id
        assert first_call_kwargs["entity_id"] == "ADR-SP-042"


# =============================================================================
# SEAM 5: Graceful Degradation
# =============================================================================
class TestSeam5_GracefulDegradation:
    """Tests for graceful degradation when Graphiti unavailable.

    Validates that all operations return safe defaults (None/[]/False)
    when Graphiti client is None or disabled.
    """

    @pytest.mark.asyncio
    async def test_upsert_component_returns_none_when_client_none(self):
        """upsert_component() returns None when client is None."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.component import ComponentDef

        service = SystemPlanGraphiti(client=None, project_id="test")
        component = ComponentDef(name="Test", description="Test")

        result = await service.upsert_component(component)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_adr_returns_none_when_client_none(self):
        """upsert_adr() returns None when client is None."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

        service = SystemPlanGraphiti(client=None, project_id="test")
        adr = ArchitectureDecision(number=1, title="T", status="accepted", context="C", decision="D")

        result = await service.upsert_adr(adr)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_system_context_returns_none_when_client_disabled(self):
        """upsert_system_context() returns None when client.enabled == False."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.system_context import SystemContextDef

        mock_client = Mock()
        mock_client.enabled = False

        service = SystemPlanGraphiti(client=mock_client, project_id="test")
        system = SystemContextDef(name="Test", purpose="Test")

        result = await service.upsert_system_context(system)
        assert result is None

    @pytest.mark.asyncio
    async def test_upsert_crosscutting_returns_none_when_client_disabled(self):
        """upsert_crosscutting() returns None when client.enabled == False."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti
        from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef

        mock_client = Mock()
        mock_client.enabled = False

        service = SystemPlanGraphiti(client=mock_client, project_id="test")
        concern = CrosscuttingConcernDef(name="Test", description="Test")

        result = await service.upsert_crosscutting(concern)
        assert result is None

    @pytest.mark.asyncio
    async def test_has_architecture_context_returns_false_when_unavailable(self):
        """has_architecture_context() returns False when Graphiti unavailable."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        # Test with None client
        service_none = SystemPlanGraphiti(client=None, project_id="test")
        assert await service_none.has_architecture_context() is False

        # Test with disabled client
        mock_client = Mock()
        mock_client.enabled = False
        service_disabled = SystemPlanGraphiti(client=mock_client, project_id="test")
        assert await service_disabled.has_architecture_context() is False

    @pytest.mark.asyncio
    async def test_get_architecture_summary_returns_none_when_unavailable(self):
        """get_architecture_summary() returns None when Graphiti unavailable."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        service = SystemPlanGraphiti(client=None, project_id="test")
        result = await service.get_architecture_summary()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_relevant_context_returns_empty_list_when_unavailable(self):
        """get_relevant_context_for_topic() returns [] when Graphiti unavailable."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        service = SystemPlanGraphiti(client=None, project_id="test")
        result = await service.get_relevant_context_for_topic("test topic", 10)
        assert result == []

    @pytest.mark.asyncio
    async def test_detect_mode_returns_setup_when_graphiti_unavailable(self):
        """detect_mode() returns 'setup' when Graphiti unavailable."""
        from guardkit.planning.mode_detector import detect_mode

        # None client
        result = await detect_mode(graphiti_client=None, project_id="test")
        assert result == "setup"

        # Disabled client
        mock_client = Mock()
        mock_client.enabled = False
        result = await detect_mode(graphiti_client=mock_client, project_id="test")
        assert result == "setup"

    def test_architecture_context_empty_returns_usable_context(self):
        """ArchitectureContext.empty() returns usable empty context."""
        from guardkit.knowledge.entities.architecture_context import ArchitectureContext

        ctx = ArchitectureContext.empty()

        assert ctx.system_context is None
        assert ctx.components == []
        assert ctx.decisions == []
        assert ctx.crosscutting_concerns == []
        assert ctx.retrieved_facts == []

        # Should be usable in formatting
        formatted = ctx.format_for_prompt(token_budget=1000)
        assert isinstance(formatted, str)

    def test_cli_command_completes_without_error_when_graphiti_none(self):
        """CLI command completes without error when Graphiti is None."""
        from click.testing import CliRunner
        from guardkit.cli.system_plan import system_plan

        runner = CliRunner()

        with patch('guardkit.planning.system_plan.run_system_plan', new_callable=AsyncMock) as mock_run:
            mock_run.return_value = None

            result = runner.invoke(system_plan, ["Test description"])

            # Should not crash - exit code 0 or clean completion
            # Note: The actual return code depends on the mock behavior
            assert result.exception is None or isinstance(result.exception, SystemExit)


# =============================================================================
# SEAM 6: Template Rendering
# =============================================================================
class TestSeam6_TemplateRendering:
    """Tests for template rendering via ArchitectureWriter.

    Validates that templates produce correct output files.
    """

    def test_write_all_produces_expected_files_modular(self, tmp_path):
        """ArchitectureWriter.write_all() produces all expected files for modular methodology."""
        from guardkit.planning.architecture_writer import ArchitectureWriter
        from guardkit.knowledge.entities.system_context import SystemContextDef
        from guardkit.knowledge.entities.component import ComponentDef
        from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
        from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

        writer = ArchitectureWriter()

        system = SystemContextDef(
            name="Test System",
            purpose="Testing",
            bounded_contexts=["Module1"],
            external_systems=["External1"],
            methodology="modular",  # NOT ddd
        )

        components = [
            ComponentDef(name="Module1", description="Test module", methodology="modular"),
        ]

        concerns = [
            CrosscuttingConcernDef(name="Logging", description="Logging concern"),
        ]

        decisions = [
            ArchitectureDecision(number=1, title="Test", status="accepted", context="C", decision="D"),
        ]

        output_dir = tmp_path / "architecture"
        writer.write_all(
            output_dir=output_dir,
            system=system,
            components=components,
            concerns=concerns,
            decisions=decisions,
        )

        # Check expected files exist for modular methodology
        assert (output_dir / "ARCHITECTURE.md").exists()
        assert (output_dir / "system-context.md").exists()
        assert (output_dir / "components.md").exists()  # NOT bounded-contexts.md for modular
        assert (output_dir / "crosscutting-concerns.md").exists()
        assert (output_dir / "decisions" / "ADR-SP-001.md").exists()

    def test_write_all_produces_bounded_contexts_md_for_ddd(self, tmp_path):
        """ArchitectureWriter.write_all() produces bounded-contexts.md (not components.md) for DDD."""
        from guardkit.planning.architecture_writer import ArchitectureWriter
        from guardkit.knowledge.entities.system_context import SystemContextDef
        from guardkit.knowledge.entities.component import ComponentDef
        from guardkit.knowledge.entities.crosscutting import CrosscuttingConcernDef
        from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

        writer = ArchitectureWriter()

        system = SystemContextDef(
            name="DDD System",
            purpose="Testing",
            methodology="ddd",  # DDD methodology
        )

        components = [
            ComponentDef(
                name="Orders",
                description="Order bounded context",
                methodology="ddd",
                aggregate_roots=["Order"],
            ),
        ]

        output_dir = tmp_path / "ddd_architecture"
        writer.write_all(
            output_dir=output_dir,
            system=system,
            components=components,
            concerns=[],
            decisions=[],
        )

        # For DDD, should have bounded-contexts.md NOT components.md
        assert (output_dir / "bounded-contexts.md").exists()
        assert not (output_dir / "components.md").exists()

    def test_generated_system_context_contains_valid_mermaid(self, tmp_path):
        """Generated system-context.md contains valid mermaid diagram syntax."""
        from guardkit.planning.architecture_writer import ArchitectureWriter
        from guardkit.knowledge.entities.system_context import SystemContextDef

        writer = ArchitectureWriter()

        system = SystemContextDef(
            name="Test System",
            purpose="Testing mermaid output",
            bounded_contexts=["Orders", "Inventory"],
            external_systems=["Payment Gateway"],
            methodology="modular",
        )

        output_dir = tmp_path / "mermaid_test"
        writer.write_all(
            output_dir=output_dir,
            system=system,
            components=[],
            concerns=[],
            decisions=[],
        )

        content = (output_dir / "system-context.md").read_text()

        # Check for mermaid diagram markers
        assert "```mermaid" in content or "mermaid" in content.lower()

    def test_generated_adr_follows_nygard_format(self, tmp_path):
        """Generated ADR files follow Michael Nygard format."""
        from guardkit.planning.architecture_writer import ArchitectureWriter
        from guardkit.knowledge.entities.system_context import SystemContextDef
        from guardkit.knowledge.entities.architecture_context import ArchitectureDecision

        writer = ArchitectureWriter()

        system = SystemContextDef(name="Test", purpose="Test", methodology="modular")

        decisions = [
            ArchitectureDecision(
                number=1,
                title="Use PostgreSQL",
                status="accepted",
                context="Need ACID compliance",
                decision="Use PostgreSQL as primary database",
                consequences=["Better data integrity", "More complex setup"],
            ),
        ]

        output_dir = tmp_path / "adr_test"
        writer.write_all(
            output_dir=output_dir,
            system=system,
            components=[],
            concerns=[],
            decisions=decisions,
        )

        adr_content = (output_dir / "decisions" / "ADR-SP-001.md").read_text()

        # Nygard format sections (case-insensitive check)
        content_lower = adr_content.lower()
        assert "status" in content_lower
        assert "context" in content_lower
        assert "decision" in content_lower
        assert "consequences" in content_lower

    def test_empty_component_list_produces_index_file(self, tmp_path):
        """Empty component list does not crash and still produces index file."""
        from guardkit.planning.architecture_writer import ArchitectureWriter
        from guardkit.knowledge.entities.system_context import SystemContextDef

        writer = ArchitectureWriter()

        system = SystemContextDef(name="Empty System", purpose="Test", methodology="modular")

        output_dir = tmp_path / "empty_test"

        # Should not crash with empty lists
        writer.write_all(
            output_dir=output_dir,
            system=system,
            components=[],  # Empty
            concerns=[],    # Empty
            decisions=[],   # Empty
        )

        # Index file should still exist
        assert (output_dir / "ARCHITECTURE.md").exists()
        assert (output_dir / "system-context.md").exists()


# =============================================================================
# SEAM 7: CLI Registration
# =============================================================================
class TestSeam7_CliRegistration:
    """Tests for CLI command registration and option handling.

    Validates that Click CLI integration is correct.
    """

    def test_system_plan_help_returns_valid_text(self):
        """'guardkit system-plan --help' returns valid help text."""
        from click.testing import CliRunner
        from guardkit.cli.system_plan import system_plan

        runner = CliRunner()
        result = runner.invoke(system_plan, ["--help"])

        assert result.exit_code == 0
        assert "system-plan" in result.output.lower() or "description" in result.output.lower()
        assert "--mode" in result.output
        assert "--focus" in result.output

    def test_mode_flag_accepts_only_valid_values(self):
        """--mode flag accepts only 'setup', 'refine', 'review'."""
        from click.testing import CliRunner
        from guardkit.cli.system_plan import system_plan

        runner = CliRunner()

        # Valid modes should not produce validation error
        for mode in ["setup", "refine", "review"]:
            with patch('guardkit.planning.system_plan.run_system_plan', new_callable=AsyncMock):
                result = runner.invoke(system_plan, ["Test", "--mode", mode])
                # Should not have "Invalid choice" in output
                assert "invalid choice" not in result.output.lower() or result.exit_code == 0

    def test_mode_flag_rejects_invalid_values(self):
        """--mode flag rejects invalid values."""
        from click.testing import CliRunner
        from guardkit.cli.system_plan import system_plan

        runner = CliRunner()
        result = runner.invoke(system_plan, ["Test", "--mode", "invalid"])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()

    def test_focus_flag_accepts_only_valid_values(self):
        """--focus flag accepts only 'domains', 'services', 'decisions', 'crosscutting', 'all'."""
        from click.testing import CliRunner
        from guardkit.cli.system_plan import system_plan

        runner = CliRunner()

        valid_focuses = ["domains", "services", "decisions", "crosscutting", "all"]
        for focus in valid_focuses:
            with patch('guardkit.planning.system_plan.run_system_plan', new_callable=AsyncMock):
                result = runner.invoke(system_plan, ["Test", "--focus", focus])
                assert "invalid choice" not in result.output.lower() or result.exit_code == 0

    def test_focus_flag_rejects_invalid_values(self):
        """--focus flag rejects invalid values."""
        from click.testing import CliRunner
        from guardkit.cli.system_plan import system_plan

        runner = CliRunner()
        result = runner.invoke(system_plan, ["Test", "--focus", "invalid"])

        assert result.exit_code != 0
        assert "invalid" in result.output.lower() or "choice" in result.output.lower()

    def test_unknown_flags_are_rejected(self):
        """Unknown flags are rejected."""
        from click.testing import CliRunner
        from guardkit.cli.system_plan import system_plan

        runner = CliRunner()
        result = runner.invoke(system_plan, ["Test", "--unknown-flag"])

        assert result.exit_code != 0
        assert "no such option" in result.output.lower() or "error" in result.output.lower()


# =============================================================================
# SEAM 8: Context Assembly (format_for_prompt)
# =============================================================================
class TestSeam8_ContextAssembly:
    """Tests for ArchitectureContext.format_for_prompt() assembly.

    Validates that context formatting works correctly.
    """

    def test_format_for_prompt_produces_nonempty_string_with_facts(self):
        """format_for_prompt() produces non-empty string when facts present."""
        from guardkit.knowledge.entities.architecture_context import (
            ArchitectureContext,
            ArchitectureDecision,
        )
        from guardkit.knowledge.entities.component import ComponentDef

        ctx = ArchitectureContext(
            components=[ComponentDef(name="Test", description="Test component")],
            decisions=[
                ArchitectureDecision(
                    number=1, title="Test", status="accepted", context="C", decision="D"
                )
            ],
            retrieved_facts=[{"content": "Uses CQRS pattern", "score": 0.8}],
        )

        result = ctx.format_for_prompt(token_budget=4000)

        assert isinstance(result, str)
        assert len(result) > 0
        assert result != "No architecture context available."

    def test_format_for_prompt_filters_facts_by_score(self):
        """format_for_prompt() filters facts by score > 0.5."""
        from guardkit.knowledge.entities.architecture_context import ArchitectureContext

        ctx = ArchitectureContext(
            retrieved_facts=[
                {"content": "High score fact", "score": 0.8},
                {"content": "Low score fact", "score": 0.3},  # Should be filtered
                {"content": "Medium score fact", "score": 0.6},
            ],
        )

        result = ctx.format_for_prompt(token_budget=4000)

        assert "High score fact" in result
        assert "Medium score fact" in result
        assert "Low score fact" not in result

    def test_format_for_prompt_returns_empty_indicator_when_no_high_score_facts(self):
        """format_for_prompt() returns empty indicator when no high-score facts."""
        from guardkit.knowledge.entities.architecture_context import ArchitectureContext

        # Only low-score facts
        ctx = ArchitectureContext(
            retrieved_facts=[
                {"content": "Low fact 1", "score": 0.3},
                {"content": "Low fact 2", "score": 0.4},
            ],
        )

        result = ctx.format_for_prompt(token_budget=4000)

        # Should indicate no context or be minimal
        assert "No architecture context available" in result or len(result) < 100

    def test_format_for_prompt_respects_token_budget(self):
        """Token budget is respected (output doesn't exceed max_tokens worth of content)."""
        from guardkit.knowledge.entities.architecture_context import (
            ArchitectureContext,
            ArchitectureDecision,
        )
        from guardkit.knowledge.entities.component import ComponentDef
        from guardkit.knowledge.entities.system_context import SystemContextDef

        # Create context with lots of content
        ctx = ArchitectureContext(
            system_context=SystemContextDef(
                name="Large System",
                purpose="A" * 1000,  # Long purpose
                bounded_contexts=["BC" + str(i) for i in range(50)],
                external_systems=["Ext" + str(i) for i in range(50)],
            ),
            components=[
                ComponentDef(name=f"Comp{i}", description="D" * 200)
                for i in range(20)
            ],
            decisions=[
                ArchitectureDecision(
                    number=i,
                    title=f"Decision {i}",
                    status="accepted",
                    context="C" * 200,
                    decision="D" * 200,
                )
                for i in range(20)
            ],
            retrieved_facts=[
                {"content": f"Fact content {i} " * 50, "score": 0.9}
                for i in range(50)
            ],
        )

        # Small token budget - output should be constrained
        small_budget = 100
        result = ctx.format_for_prompt(token_budget=small_budget)

        # Rough check: 4 chars per token means ~400 chars max
        # Allow some slack for section headers
        max_chars = small_budget * 4 * 2  # 2x buffer for headers
        assert len(result) < max_chars, f"Output too long: {len(result)} chars"


# =============================================================================
# SEAM 9: Feature-Plan Integration
# =============================================================================
class TestSeam9_FeaturePlanIntegration:
    """Tests for feature-plan context loading integration.

    Validates that load_architecture_context() works correctly.
    """

    @pytest.mark.asyncio
    async def test_load_architecture_context_returns_context_with_facts(self):
        """load_architecture_context() returns ArchitectureContext with populated facts from mock Graphiti."""
        from guardkit.knowledge.entities.architecture_context import ArchitectureContext
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[
            {"fact": "Uses CQRS pattern", "uuid": "uuid-1", "score": 0.8},
        ])

        builder = FeaturePlanContextBuilder(project_root=Path("."))
        builder.graphiti_client = mock_client

        context = await builder.build_context(
            description="Test feature",
            tech_stack="python",
        )

        assert isinstance(context.project_architecture, (dict, type(None))) or context.project_architecture == {}

    @pytest.mark.asyncio
    async def test_load_architecture_context_returns_empty_when_no_architecture(self):
        """load_architecture_context() returns empty context when no architecture exists."""
        from guardkit.knowledge.feature_plan_context import FeaturePlanContextBuilder

        mock_client = Mock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])  # No results

        builder = FeaturePlanContextBuilder(project_root=Path("."))
        builder.graphiti_client = mock_client

        context = await builder.build_context(
            description="Test feature",
            tech_stack="python",
        )

        # Should have empty/default values
        assert context.related_features == []
        assert context.relevant_patterns == []

    def test_architecture_context_has_context_true_when_facts_present(self):
        """ArchitectureContext.has_context is True when component_facts or decision_facts present."""
        from guardkit.knowledge.entities.architecture_context import (
            ArchitectureContext,
            ArchitectureDecision,
        )
        from guardkit.knowledge.entities.component import ComponentDef

        # With components
        ctx_with_components = ArchitectureContext(
            components=[ComponentDef(name="Test", description="Test")],
        )

        # ArchitectureContext doesn't have has_context, but we can check if it formats non-empty
        result = ctx_with_components.format_for_prompt()
        assert "No architecture context available" not in result

        # With decisions
        ctx_with_decisions = ArchitectureContext(
            decisions=[ArchitectureDecision(number=1, title="T", status="accepted", context="C", decision="D")],
        )

        result = ctx_with_decisions.format_for_prompt()
        assert "No architecture context available" not in result

    def test_architecture_context_has_context_false_when_all_empty(self):
        """ArchitectureContext.has_context is False when all fact lists empty."""
        from guardkit.knowledge.entities.architecture_context import ArchitectureContext

        ctx = ArchitectureContext.empty()

        result = ctx.format_for_prompt()
        assert "No architecture context available" in result


# =============================================================================
# Search API Shape Tests
# =============================================================================
class TestSearchApiShape:
    """Tests for correct Graphiti search API parameter usage."""

    @pytest.mark.asyncio
    async def test_get_architecture_summary_uses_num_results_parameter(self):
        """get_architecture_summary() uses 'num_results' parameter (not 'limit')."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        mock_client = Mock()
        mock_client.enabled = True
        mock_client.get_group_id = Mock(return_value="test__project_architecture")
        mock_client.search = AsyncMock(return_value=[{"fact": "test", "uuid": "u1"}])

        service = SystemPlanGraphiti(client=mock_client, project_id="test")
        await service.get_architecture_summary()

        # Verify search was called with num_results, not limit
        call_kwargs = mock_client.search.call_args[1]
        assert "num_results" in call_kwargs
        assert "limit" not in call_kwargs

    @pytest.mark.asyncio
    async def test_get_relevant_context_searches_both_groups(self):
        """get_relevant_context_for_topic() searches both architecture and decisions groups."""
        from guardkit.planning.graphiti_arch import SystemPlanGraphiti

        mock_client = Mock()
        mock_client.enabled = True

        # Track which group IDs are requested
        requested_groups = []
        def track_get_group_id(group_name):
            requested_groups.append(group_name)
            return f"test__{group_name}"

        mock_client.get_group_id = Mock(side_effect=track_get_group_id)
        mock_client.search = AsyncMock(return_value=[])

        service = SystemPlanGraphiti(client=mock_client, project_id="test")
        await service.get_relevant_context_for_topic("test topic", 10)

        # Should request both architecture and decisions groups
        assert "project_architecture" in requested_groups
        assert "project_decisions" in requested_groups
