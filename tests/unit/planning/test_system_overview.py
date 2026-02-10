"""Tests for system_overview.py module.

TDD RED phase tests for TASK-SC-001. These tests verify the system overview
assembly and condensation logic that transforms Graphiti facts into structured
context for Claude Code injection.

Coverage Target: >=85%
Test Count: 20+ tests

Key patterns verified:
- Entity type inference from fact name/content (no explicit type field)
- Fact parsing into structured sections (components, decisions, concerns)
- Token-budgeted condensation with priority ordering
- Multiple format outputs (display, markdown, JSON)
- Graceful degradation (return defaults on error/no data)
- [Graphiti] prefix on all log messages
"""

import json
import pytest
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch

# These imports will fail until implementation exists (TDD RED phase)
from guardkit.planning.system_overview import (
    get_system_overview,
    condense_for_injection,
    format_overview_display,
    _extract_entity_type,
    _parse_component_fact,
    _parse_decision_fact,
    _parse_concern_fact,
    _estimate_tokens,
)


# =========================================================================
# FIXTURES
# =========================================================================


@pytest.fixture
def mock_sp() -> MagicMock:
    """Create a mock SystemPlanGraphiti instance."""
    sp = MagicMock()
    sp._available = True
    return sp


@pytest.fixture
def mock_sp_unavailable() -> MagicMock:
    """Create a mock SystemPlanGraphiti with _available=False."""
    sp = MagicMock()
    sp._available = False
    return sp


@pytest.fixture
def sample_facts() -> List[Dict[str, Any]]:
    """Create sample Graphiti facts for testing."""
    return [
        {
            "uuid": "uuid-001",
            "name": "Component: Order Management",
            "fact": "Component: Order Management handles order lifecycle. Responsibilities: create orders, track status. Dependencies: Inventory, Payment.",
            "created_at": "2024-01-01T00:00:00Z",
            "valid_at": "2024-01-01T00:00:00Z",
            "score": 0.95,
        },
        {
            "uuid": "uuid-002",
            "name": "Component: Inventory Service",
            "fact": "Component: Inventory Service manages stock levels. Uses CQRS pattern for read/write separation.",
            "created_at": "2024-01-01T00:00:00Z",
            "valid_at": "2024-01-01T00:00:00Z",
            "score": 0.93,
        },
        {
            "uuid": "uuid-003",
            "name": "ADR-SP-001: Use Event Sourcing",
            "fact": "ADR-SP-001: Use Event Sourcing for Order Aggregate. Status: accepted. Context: Orders require complete audit trail. Consequences: Full audit trail, Complex replay logic.",
            "created_at": "2024-01-01T00:00:00Z",
            "valid_at": "2024-01-01T00:00:00Z",
            "score": 0.90,
        },
        {
            "uuid": "uuid-004",
            "name": "ADR-SP-002: GraphQL API Gateway",
            "fact": "ADR-SP-002: GraphQL API Gateway. Status: superseded. Replaced by REST due to complexity.",
            "created_at": "2024-01-01T00:00:00Z",
            "valid_at": "2024-01-01T00:00:00Z",
            "score": 0.85,
        },
        {
            "uuid": "uuid-005",
            "name": "Crosscutting: Observability",
            "fact": "Observability is a cross-cutting concern. Unified logging, metrics, and tracing across all services. Implementation: OpenTelemetry SDK.",
            "created_at": "2024-01-01T00:00:00Z",
            "valid_at": "2024-01-01T00:00:00Z",
            "score": 0.88,
        },
        {
            "uuid": "uuid-006",
            "name": "System Context: E-Commerce Platform",
            "fact": "System Context: E-Commerce Platform. Purpose: Online retail with multi-tenant support. Methodology: DDD. Bounded contexts: Orders, Inventory, Customers.",
            "created_at": "2024-01-01T00:00:00Z",
            "valid_at": "2024-01-01T00:00:00Z",
            "score": 0.97,
        },
    ]


@pytest.fixture
def sample_architecture_summary(sample_facts) -> Dict[str, Any]:
    """Create sample architecture summary from get_architecture_summary."""
    return {
        "facts": sample_facts,
        "total": len(sample_facts),
    }


# =========================================================================
# 1. GET_SYSTEM_OVERVIEW TESTS (8 tests)
# =========================================================================


class TestGetSystemOverview:
    """Tests for get_system_overview function."""

    @pytest.mark.asyncio
    async def test_get_system_overview_full(
        self, mock_sp: MagicMock, sample_architecture_summary: Dict
    ):
        """Test get_system_overview with all fact types present."""
        mock_sp.get_architecture_summary = AsyncMock(return_value=sample_architecture_summary)

        result = await get_system_overview(mock_sp, verbose=False)

        assert result["status"] == "ok"
        assert "system" in result
        assert "components" in result
        assert "decisions" in result
        assert "concerns" in result
        assert len(result["components"]) == 2  # 2 component facts
        assert len(result["decisions"]) == 2  # 2 ADR facts
        assert len(result["concerns"]) == 1  # 1 crosscutting fact
        assert result["system"]["methodology"] == "DDD"

    @pytest.mark.asyncio
    async def test_get_system_overview_no_context(self, mock_sp: MagicMock):
        """Test get_system_overview returns no_context when no facts found."""
        mock_sp.get_architecture_summary = AsyncMock(return_value=None)

        result = await get_system_overview(mock_sp, verbose=False)

        assert result["status"] == "no_context"
        assert "system" not in result
        assert "components" not in result

    @pytest.mark.asyncio
    async def test_get_system_overview_empty_facts(self, mock_sp: MagicMock):
        """Test get_system_overview returns no_context when facts list is empty."""
        mock_sp.get_architecture_summary = AsyncMock(return_value={"facts": [], "total": 0})

        result = await get_system_overview(mock_sp, verbose=False)

        assert result["status"] == "no_context"

    @pytest.mark.asyncio
    async def test_get_system_overview_graphiti_unavailable(
        self, mock_sp_unavailable: MagicMock
    ):
        """Test get_system_overview returns no_context when sp._available is False."""
        result = await get_system_overview(mock_sp_unavailable, verbose=False)

        assert result["status"] == "no_context"
        # Should not call get_architecture_summary when unavailable
        mock_sp_unavailable.get_architecture_summary.assert_not_called()

    @pytest.mark.asyncio
    async def test_get_system_overview_verbose_mode(
        self, mock_sp: MagicMock, sample_architecture_summary: Dict
    ):
        """Test get_system_overview with verbose=True includes full content."""
        mock_sp.get_architecture_summary = AsyncMock(return_value=sample_architecture_summary)

        result = await get_system_overview(mock_sp, verbose=True)

        # Verbose mode should include full fact content in parsed items
        assert result["status"] == "ok"
        # Check that components have full_content field
        assert any("full_content" in comp or "content" in comp for comp in result["components"])

    @pytest.mark.asyncio
    async def test_get_system_overview_exception_handling(self, mock_sp: MagicMock):
        """Test get_system_overview returns no_context on exception."""
        mock_sp.get_architecture_summary = AsyncMock(side_effect=Exception("Network error"))

        with patch("guardkit.planning.system_overview.logger") as mock_logger:
            result = await get_system_overview(mock_sp, verbose=False)

            assert result["status"] == "no_context"
            mock_logger.warning.assert_called_once()
            assert "[Graphiti]" in mock_logger.warning.call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_system_overview_calls_get_architecture_summary(
        self, mock_sp: MagicMock, sample_architecture_summary: Dict
    ):
        """Test get_system_overview calls sp.get_architecture_summary()."""
        mock_sp.get_architecture_summary = AsyncMock(return_value=sample_architecture_summary)

        await get_system_overview(mock_sp, verbose=False)

        mock_sp.get_architecture_summary.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_system_overview_groups_facts_by_type(
        self, mock_sp: MagicMock, sample_architecture_summary: Dict
    ):
        """Test get_system_overview groups facts into correct sections."""
        mock_sp.get_architecture_summary = AsyncMock(return_value=sample_architecture_summary)

        result = await get_system_overview(mock_sp, verbose=False)

        # Verify correct grouping
        component_names = [c["name"] for c in result["components"]]
        assert "Order Management" in component_names
        assert "Inventory Service" in component_names

        decision_ids = [d.get("adr_id") or d.get("number") for d in result["decisions"]]
        assert "ADR-SP-001" in decision_ids or 1 in decision_ids
        assert "ADR-SP-002" in decision_ids or 2 in decision_ids


# =========================================================================
# 2. EXTRACT_ENTITY_TYPE TESTS (7 tests)
# =========================================================================


class TestExtractEntityType:
    """Tests for _extract_entity_type function."""

    def test_extract_entity_type_component(self):
        """Test _extract_entity_type recognizes Component: prefix."""
        fact = {
            "name": "Component: Order Management",
            "fact": "Component: Order Management handles orders.",
        }

        entity_type = _extract_entity_type(fact)

        assert entity_type == "component"

    def test_extract_entity_type_adr(self):
        """Test _extract_entity_type recognizes ADR- prefix."""
        fact = {
            "name": "ADR-SP-001: Use Event Sourcing",
            "fact": "ADR-SP-001: Use Event Sourcing for Order Aggregate.",
        }

        entity_type = _extract_entity_type(fact)

        assert entity_type == "architecture_decision"

    def test_extract_entity_type_concern_from_keyword(self):
        """Test _extract_entity_type recognizes cross-cutting keyword."""
        fact = {
            "name": "Observability",
            "fact": "Observability is a cross-cutting concern for all services.",
        }

        entity_type = _extract_entity_type(fact)

        assert entity_type == "crosscutting_concern"

    def test_extract_entity_type_concern_from_name(self):
        """Test _extract_entity_type recognizes Crosscutting: prefix."""
        fact = {
            "name": "Crosscutting: Security",
            "fact": "Security concern applies to all components.",
        }

        entity_type = _extract_entity_type(fact)

        assert entity_type == "crosscutting_concern"

    def test_extract_entity_type_system_context(self):
        """Test _extract_entity_type recognizes System Context prefix."""
        fact = {
            "name": "System Context: E-Commerce Platform",
            "fact": "System Context: E-Commerce Platform for online retail.",
        }

        entity_type = _extract_entity_type(fact)

        assert entity_type == "system_context"

    def test_extract_entity_type_unknown_fallback(self):
        """Test _extract_entity_type fallback for unknown patterns."""
        fact = {
            "name": "Random Fact",
            "fact": "Some random information without clear type.",
        }

        entity_type = _extract_entity_type(fact)

        # Should return a fallback value (could be "unknown" or "system_context")
        assert entity_type in ["unknown", "system_context"]

    def test_extract_entity_type_case_insensitive(self):
        """Test _extract_entity_type is case insensitive."""
        fact = {
            "name": "component: payment service",
            "fact": "component: payment service processes payments.",
        }

        entity_type = _extract_entity_type(fact)

        assert entity_type == "component"


# =========================================================================
# 3. PARSE FACT TESTS (9 tests)
# =========================================================================


class TestParseFactFunctions:
    """Tests for _parse_component_fact, _parse_decision_fact, _parse_concern_fact."""

    def test_parse_component_fact_extracts_name_and_description(self):
        """Test _parse_component_fact extracts name and description."""
        fact = {
            "name": "Component: Order Management",
            "fact": "Component: Order Management handles order lifecycle. Responsibilities: create orders, track status.",
            "uuid": "uuid-001",
        }

        result = _parse_component_fact(fact, verbose=False)

        assert result["name"] == "Order Management"
        assert "description" in result
        assert "order lifecycle" in result["description"].lower()

    def test_parse_component_fact_verbose_includes_full_content(self):
        """Test _parse_component_fact with verbose=True includes full content."""
        fact = {
            "name": "Component: Inventory Service",
            "fact": "Component: Inventory Service manages stock levels. Uses CQRS pattern.",
            "uuid": "uuid-002",
        }

        result = _parse_component_fact(fact, verbose=True)

        # Verbose mode should include full fact content
        assert "full_content" in result or "content" in result
        assert "CQRS pattern" in (result.get("full_content") or result.get("content"))

    def test_parse_decision_fact_extracts_adr_details(self):
        """Test _parse_decision_fact extracts ADR ID, title, status."""
        fact = {
            "name": "ADR-SP-001: Use Event Sourcing",
            "fact": "ADR-SP-001: Use Event Sourcing for Order Aggregate. Status: accepted. Context: Orders require complete audit trail.",
            "uuid": "uuid-003",
        }

        result = _parse_decision_fact(fact, verbose=False)

        assert result.get("adr_id") == "ADR-SP-001" or result.get("number") == "001"
        assert "title" in result
        assert "event sourcing" in result["title"].lower()
        assert result.get("status") == "accepted"

    def test_parse_decision_fact_handles_superseded_status(self):
        """Test _parse_decision_fact correctly parses superseded status."""
        fact = {
            "name": "ADR-SP-002: GraphQL API Gateway",
            "fact": "ADR-SP-002: GraphQL API Gateway. Status: superseded. Replaced by REST.",
            "uuid": "uuid-004",
        }

        result = _parse_decision_fact(fact, verbose=False)

        assert result.get("status") == "superseded"

    def test_parse_decision_fact_verbose_includes_context_and_consequences(self):
        """Test _parse_decision_fact with verbose=True includes context and consequences."""
        fact = {
            "name": "ADR-SP-001: Use Event Sourcing",
            "fact": "ADR-SP-001: Use Event Sourcing. Context: Full audit required. Consequences: Complex replay logic.",
            "uuid": "uuid-003",
        }

        result = _parse_decision_fact(fact, verbose=True)

        # Verbose mode should include context and consequences
        assert "context" in result or "full_content" in result
        if "context" in result:
            assert "audit" in result["context"].lower()

    def test_parse_concern_fact_extracts_name_and_description(self):
        """Test _parse_concern_fact extracts concern name and description."""
        fact = {
            "name": "Crosscutting: Observability",
            "fact": "Observability is a cross-cutting concern. Unified logging, metrics, and tracing.",
            "uuid": "uuid-005",
        }

        result = _parse_concern_fact(fact, verbose=False)

        assert result["name"] == "Observability"
        assert "description" in result
        assert "logging" in result["description"].lower() or "tracing" in result["description"].lower()

    def test_parse_concern_fact_verbose_includes_full_content(self):
        """Test _parse_concern_fact with verbose=True includes full content."""
        fact = {
            "name": "Crosscutting: Security",
            "fact": "Security concern: OAuth2 authentication for all services.",
            "uuid": "uuid-006",
        }

        result = _parse_concern_fact(fact, verbose=True)

        assert "full_content" in result or "content" in result

    def test_parse_component_fact_handles_minimal_data(self):
        """Test _parse_component_fact handles facts with minimal data."""
        fact = {
            "name": "Component: Payment",
            "fact": "Component: Payment",
            "uuid": "uuid-007",
        }

        result = _parse_component_fact(fact, verbose=False)

        assert result["name"] == "Payment"
        assert "description" in result

    def test_parse_decision_fact_handles_minimal_data(self):
        """Test _parse_decision_fact handles facts with minimal data."""
        fact = {
            "name": "ADR-SP-003: Use REST",
            "fact": "ADR-SP-003: Use REST",
            "uuid": "uuid-008",
        }

        result = _parse_decision_fact(fact, verbose=False)

        assert result.get("adr_id") == "ADR-SP-003" or result.get("number") == "003"


# =========================================================================
# 4. CONDENSE_FOR_INJECTION TESTS (6 tests)
# =========================================================================


class TestCondenseForInjection:
    """Tests for condense_for_injection function."""

    def test_condense_for_injection_within_budget(self):
        """Test condense_for_injection returns output under max_tokens."""
        overview = {
            "status": "ok",
            "system": {"name": "E-Commerce Platform", "methodology": "DDD"},
            "components": [
                {"name": "Order Management", "description": "Handles order lifecycle"},
                {"name": "Inventory Service", "description": "Manages stock levels"},
            ],
            "decisions": [
                {"adr_id": "ADR-SP-001", "title": "Use Event Sourcing", "status": "accepted"}
            ],
            "concerns": [{"name": "Observability", "description": "Unified logging"}],
        }

        result = condense_for_injection(overview, max_tokens=800)

        estimated_tokens = _estimate_tokens(result)
        assert estimated_tokens <= 800
        assert "E-Commerce Platform" in result
        assert "DDD" in result

    def test_condense_for_injection_priority_order(self):
        """Test condense_for_injection includes components before descriptions."""
        overview = {
            "status": "ok",
            "system": {"name": "Platform", "methodology": "Microservices"},
            "components": [
                {"name": "Service A", "description": "Very long description " * 50},
                {"name": "Service B", "description": "Another long description " * 50},
            ],
            "decisions": [],
            "concerns": [],
        }

        result = condense_for_injection(overview, max_tokens=100)

        # Should include component names even if descriptions are cut
        assert "Service A" in result
        assert "Service B" in result
        # Priority: methodology + component names → ADR titles → descriptions

    def test_condense_for_injection_empty_overview(self):
        """Test condense_for_injection with empty overview returns empty/minimal string."""
        overview = {"status": "no_context"}

        result = condense_for_injection(overview, max_tokens=800)

        assert result == "" or "no context" in result.lower()

    def test_condense_for_injection_respects_token_budget(self):
        """Test condense_for_injection stops when budget exhausted."""
        overview = {
            "status": "ok",
            "system": {"methodology": "DDD"},
            "components": [{"name": f"Component {i}", "description": "Desc " * 100} for i in range(20)],
            "decisions": [],
            "concerns": [],
        }

        result = condense_for_injection(overview, max_tokens=200)

        estimated_tokens = _estimate_tokens(result)
        assert estimated_tokens <= 200

    def test_condense_for_injection_includes_methodology(self):
        """Test condense_for_injection includes methodology in output."""
        overview = {
            "status": "ok",
            "system": {"methodology": "Event-Driven Architecture"},
            "components": [],
            "decisions": [],
            "concerns": [],
        }

        result = condense_for_injection(overview, max_tokens=800)

        assert "Event-Driven Architecture" in result

    def test_condense_for_injection_handles_missing_sections(self):
        """Test condense_for_injection handles overview with missing sections."""
        overview = {
            "status": "ok",
            "system": {"methodology": "Microservices"},
            # Missing components, decisions, concerns
        }

        result = condense_for_injection(overview, max_tokens=800)

        assert "Microservices" in result
        # Should not crash on missing sections


# =========================================================================
# 5. ESTIMATE_TOKENS TESTS (3 tests)
# =========================================================================


class TestEstimateTokens:
    """Tests for _estimate_tokens function."""

    def test_estimate_tokens_simple_heuristic(self):
        """Test _estimate_tokens uses simple heuristic (words * 1.3)."""
        text = "This is a simple test with ten words total here now."

        tokens = _estimate_tokens(text)

        # 10 words * 1.3 = 13 tokens (approximately)
        assert tokens >= 10
        assert tokens <= 15

    def test_estimate_tokens_empty_string(self):
        """Test _estimate_tokens returns 0 for empty string."""
        tokens = _estimate_tokens("")

        assert tokens == 0

    def test_estimate_tokens_long_text(self):
        """Test _estimate_tokens scales with text length."""
        short_text = "Short text"
        long_text = "This is a much longer piece of text with many more words " * 10

        short_tokens = _estimate_tokens(short_text)
        long_tokens = _estimate_tokens(long_text)

        assert long_tokens > short_tokens * 5


# =========================================================================
# 6. FORMAT_OVERVIEW_DISPLAY TESTS (8 tests)
# =========================================================================


class TestFormatOverviewDisplay:
    """Tests for format_overview_display function."""

    def test_format_display_default_terminal_format(self):
        """Test format_overview_display with default display format."""
        overview = {
            "status": "ok",
            "system": {"name": "E-Commerce Platform", "methodology": "DDD"},
            "components": [{"name": "Order Management", "description": "Handles orders"}],
            "decisions": [{"adr_id": "ADR-SP-001", "title": "Use Event Sourcing"}],
            "concerns": [{"name": "Observability"}],
        }

        result = format_overview_display(overview, section="all", format="display")

        # Terminal display should be ~40-60 lines, formatted for readability
        assert "E-Commerce Platform" in result
        assert "Order Management" in result
        assert "ADR-SP-001" in result
        assert "Observability" in result
        # Should have section headers
        assert "Components" in result or "COMPONENTS" in result

    def test_format_display_json_format(self):
        """Test format_overview_display with JSON format."""
        overview = {
            "status": "ok",
            "system": {"methodology": "Microservices"},
            "components": [{"name": "Service A"}],
        }

        result = format_overview_display(overview, section="all", format="json")

        # Should be valid JSON
        parsed = json.loads(result)
        assert parsed["status"] == "ok"
        assert parsed["system"]["methodology"] == "Microservices"

    def test_format_display_markdown_format(self):
        """Test format_overview_display with markdown format."""
        overview = {
            "status": "ok",
            "system": {"methodology": "DDD"},
            "components": [{"name": "Component A", "description": "Does stuff"}],
        }

        result = format_overview_display(overview, section="all", format="markdown")

        # Should have markdown headers
        assert "#" in result or "##" in result
        assert "Component A" in result

    def test_format_display_section_filter_components(self):
        """Test format_overview_display with section=components filter."""
        overview = {
            "status": "ok",
            "components": [{"name": "Component A"}],
            "decisions": [{"adr_id": "ADR-SP-001"}],
            "concerns": [{"name": "Security"}],
        }

        result = format_overview_display(overview, section="components", format="display")

        assert "Component A" in result
        # Should not include decisions or concerns
        assert "ADR-SP-001" not in result
        assert "Security" not in result

    def test_format_display_section_filter_decisions(self):
        """Test format_overview_display with section=decisions filter."""
        overview = {
            "status": "ok",
            "components": [{"name": "Component A"}],
            "decisions": [{"adr_id": "ADR-SP-001", "title": "Use Event Sourcing"}],
        }

        result = format_overview_display(overview, section="decisions", format="display")

        assert "ADR-SP-001" in result
        assert "Component A" not in result

    def test_format_display_section_filter_crosscutting(self):
        """Test format_overview_display with section=crosscutting filter."""
        overview = {
            "status": "ok",
            "concerns": [{"name": "Observability", "description": "Logging and metrics"}],
            "components": [{"name": "Component A"}],
        }

        result = format_overview_display(overview, section="crosscutting", format="display")

        assert "Observability" in result
        assert "Component A" not in result

    def test_format_display_empty_overview(self):
        """Test format_overview_display with no_context status."""
        overview = {"status": "no_context"}

        result = format_overview_display(overview, section="all", format="display")

        assert "no context" in result.lower() or "not available" in result.lower()

    def test_format_display_handles_missing_sections(self):
        """Test format_overview_display handles overview with missing sections."""
        overview = {
            "status": "ok",
            "system": {"methodology": "Microservices"},
            # Missing components, decisions, concerns
        }

        result = format_overview_display(overview, section="all", format="display")

        # Should not crash
        assert "Microservices" in result


# =========================================================================
# 7. INTEGRATION TESTS (3 tests)
# =========================================================================


class TestIntegration:
    """Integration tests combining multiple functions."""

    @pytest.mark.asyncio
    async def test_full_workflow_overview_to_condensed(
        self, mock_sp: MagicMock, sample_architecture_summary: Dict
    ):
        """Test full workflow: get_system_overview -> condense_for_injection."""
        mock_sp.get_architecture_summary = AsyncMock(return_value=sample_architecture_summary)

        overview = await get_system_overview(mock_sp, verbose=False)
        condensed = condense_for_injection(overview, max_tokens=800)

        assert overview["status"] == "ok"
        assert len(condensed) > 0
        assert _estimate_tokens(condensed) <= 800

    @pytest.mark.asyncio
    async def test_full_workflow_overview_to_display(
        self, mock_sp: MagicMock, sample_architecture_summary: Dict
    ):
        """Test full workflow: get_system_overview -> format_overview_display."""
        mock_sp.get_architecture_summary = AsyncMock(return_value=sample_architecture_summary)

        overview = await get_system_overview(mock_sp, verbose=False)
        display = format_overview_display(overview, section="all", format="display")

        assert overview["status"] == "ok"
        assert len(display) > 0
        assert "E-Commerce Platform" in display

    @pytest.mark.asyncio
    async def test_full_workflow_no_context_graceful_degradation(
        self, mock_sp: MagicMock
    ):
        """Test graceful degradation when no context available."""
        mock_sp.get_architecture_summary = AsyncMock(return_value=None)

        overview = await get_system_overview(mock_sp, verbose=False)
        condensed = condense_for_injection(overview, max_tokens=800)
        display = format_overview_display(overview, section="all", format="display")

        assert overview["status"] == "no_context"
        assert condensed == "" or "no context" in condensed.lower()
        assert "no context" in display.lower()
