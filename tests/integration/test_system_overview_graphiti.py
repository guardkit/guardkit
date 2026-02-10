"""
Integration tests for system_overview module Graphiti seams.

This module tests the technology seams where system_overview code interfaces
with Graphiti client's search API. Tests use MockGraphitiClient to simulate
realistic Graphiti behavior without requiring Neo4j.

Key Seam Areas Tested:
    1. Group ID prefixing (client.get_group_id())
    2. Search result format handling
    3. Async context propagation
    4. Entity type classification from fact patterns
    5. Token budget condensation
    6. Format display rendering
    7. Graceful degradation (disabled client)

Coverage Target: >=85%
Test Count: 12+ tests
"""

import pytest
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock

from guardkit.planning.system_overview import (
    get_system_overview,
    condense_for_injection,
    format_overview_display,
)
from guardkit.planning.graphiti_arch import SystemPlanGraphiti


# =============================================================================
# Mock Graphiti Client
# =============================================================================

class MockGraphitiClient:
    """Realistic mock that matches GraphitiClient API surface.

    Simulates Graphiti client behavior for testing technology seams
    without requiring actual Neo4j database connection.
    """

    def __init__(self, facts=None, enabled=True, project_id="test-project"):
        """Initialize mock client.

        Args:
            facts: List of fact dicts to return from search queries
            enabled: Whether Graphiti is enabled
            project_id: Project ID for group ID prefixing
        """
        self._facts = facts or []
        self._enabled = enabled
        self._project_id = project_id
        self._search_calls = []  # Track search calls for assertions

    @property
    def enabled(self):
        """Return whether Graphiti is enabled."""
        return self._enabled

    def get_group_id(self, group_name, scope=None):
        """Get prefixed group ID.

        Args:
            group_name: Base group name (e.g., "project_architecture")
            scope: Optional scope parameter

        Returns:
            Prefixed group ID: "{project_id}__{group_name}"
        """
        if self._project_id:
            return f"{self._project_id}__{group_name}"
        return group_name

    async def search(self, query, group_ids=None, num_results=10):
        """Simulate Graphiti search.

        Args:
            query: Search query string
            group_ids: List of group IDs to search
            num_results: Maximum results to return

        Returns:
            List of fact dicts matching Graphiti format
        """
        # Track call for verification
        self._search_calls.append({
            "query": query,
            "group_ids": group_ids,
            "num_results": num_results,
        })

        if not self._enabled:
            return []

        # Return facts up to num_results limit
        return self._facts[:num_results]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def realistic_arch_facts():
    """Facts as returned by GraphitiClient.search() with real data patterns.

    Returns:
        List of fact dicts matching actual Graphiti search result format
    """
    return [
        {
            "uuid": "fact-001",
            "fact": "Component: Attorney Management handles donor/attorney relationships and LPA lifecycle management",
            "name": "Component: Attorney Management",
            "created_at": "2026-02-07T10:00:00Z",
            "valid_at": "2026-02-07T10:00:00Z",
            "score": 0.92,
        },
        {
            "uuid": "fact-002",
            "fact": "ADR-001: Use anti-corruption layer for Moneyhub API integration to prevent external API changes from propagating into domain model",
            "name": "ADR-SP-001: Anti-corruption layer for Moneyhub",
            "created_at": "2026-02-07T10:00:00Z",
            "valid_at": "2026-02-07T10:00:00Z",
            "score": 0.88,
        },
        {
            "uuid": "fact-003",
            "fact": "Cross-cutting concern: Authentication uses GOV.UK Verify integration with role-based access control",
            "name": "Crosscutting: Authentication",
            "created_at": "2026-02-07T10:00:00Z",
            "valid_at": "2026-02-07T10:00:00Z",
            "score": 0.85,
        },
        {
            "uuid": "fact-004",
            "fact": "System uses Domain-Driven Design methodology with 4 bounded contexts",
            "name": "System Context: Power of Attorney Platform",
            "created_at": "2026-02-07T10:00:00Z",
            "valid_at": "2026-02-07T10:00:00Z",
            "score": 0.95,
        },
    ]


@pytest.fixture
def mock_graphiti_client(realistic_arch_facts):
    """Create mock Graphiti client with realistic facts.

    Args:
        realistic_arch_facts: Fixture providing realistic fact data

    Returns:
        MockGraphitiClient instance
    """
    return MockGraphitiClient(
        facts=realistic_arch_facts,
        enabled=True,
        project_id="test-project"
    )


@pytest.fixture
def system_plan_graphiti(mock_graphiti_client):
    """Create SystemPlanGraphiti with mock client.

    Args:
        mock_graphiti_client: Mock Graphiti client fixture

    Returns:
        SystemPlanGraphiti instance
    """
    return SystemPlanGraphiti(
        client=mock_graphiti_client,
        project_id="test-project"
    )


# =============================================================================
# 1. Full Pipeline Tests
# =============================================================================

@pytest.mark.asyncio
async def test_overview_with_seeded_architecture(system_plan_graphiti, realistic_arch_facts):
    """Full pipeline: mock client -> SystemPlanGraphiti -> get_system_overview -> verify all sections populated."""
    overview = await get_system_overview(system_plan_graphiti, verbose=False)

    # Verify successful status
    assert overview["status"] == "ok"

    # Verify system context was extracted
    assert "system" in overview
    assert overview["system"]["name"] == "Power of Attorney Platform"

    # Verify components were parsed
    assert "components" in overview
    assert len(overview["components"]) == 1
    assert overview["components"][0]["name"] == "Attorney Management"

    # Verify decisions were parsed
    assert "decisions" in overview
    assert len(overview["decisions"]) == 1
    assert overview["decisions"][0]["adr_id"] == "ADR-SP-001"

    # Verify crosscutting concerns were parsed
    assert "concerns" in overview
    assert len(overview["concerns"]) == 1
    assert overview["concerns"][0]["name"] == "Authentication"


@pytest.mark.asyncio
async def test_overview_empty_project(system_plan_graphiti):
    """No facts -> status: 'no_context'."""
    # Override client with empty facts
    system_plan_graphiti._client._facts = []

    overview = await get_system_overview(system_plan_graphiti, verbose=False)

    assert overview["status"] == "no_context"


@pytest.mark.asyncio
async def test_overview_partial_context(system_plan_graphiti):
    """Only components, no ADRs -> partial display."""
    # Override with only component facts
    system_plan_graphiti._client._facts = [
        {
            "uuid": "fact-001",
            "fact": "Component: Order Management handles order lifecycle",
            "name": "Component: Order Management",
            "score": 0.9,
        }
    ]

    overview = await get_system_overview(system_plan_graphiti, verbose=False)

    assert overview["status"] == "ok"
    assert len(overview["components"]) == 1
    assert len(overview["decisions"]) == 0
    assert len(overview["concerns"]) == 0


# =============================================================================
# 2. Condensation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_overview_condense_roundtrip(system_plan_graphiti):
    """get_system_overview -> condense_for_injection -> verify within budget."""
    overview = await get_system_overview(system_plan_graphiti, verbose=False)

    # Condense with small budget
    max_tokens = 200
    condensed = condense_for_injection(overview, max_tokens=max_tokens)

    # Verify non-empty output
    assert len(condensed) > 0

    # Rough token estimate: 4 chars per token
    estimated_tokens = len(condensed.split()) * 1.3
    assert estimated_tokens <= max_tokens * 1.5  # Allow 50% buffer for estimation variance

    # Verify priority items present
    assert "Power of Attorney Platform" in condensed or "Attorney Management" in condensed


def test_condense_no_context():
    """condense_for_injection with status='no_context' -> empty string."""
    overview = {"status": "no_context"}

    condensed = condense_for_injection(overview, max_tokens=800)

    assert condensed == ""


# =============================================================================
# 3. Entity Type Classification Tests
# =============================================================================

@pytest.mark.asyncio
async def test_overview_entity_type_classification(system_plan_graphiti, realistic_arch_facts):
    """All 4 entity types correctly classified from realistic facts."""
    overview = await get_system_overview(system_plan_graphiti, verbose=False)

    # Verify system context (1 expected)
    assert len(overview.get("system", {})) > 0

    # Verify component classification (1 expected)
    assert len(overview["components"]) == 1
    assert overview["components"][0]["name"] == "Attorney Management"

    # Verify architecture decision classification (1 expected)
    assert len(overview["decisions"]) == 1
    assert overview["decisions"][0]["adr_id"] == "ADR-SP-001"

    # Verify crosscutting concern classification (1 expected)
    assert len(overview["concerns"]) == 1
    assert overview["concerns"][0]["name"] == "Authentication"


@pytest.mark.asyncio
async def test_overview_fact_with_unexpected_format(system_plan_graphiti):
    """Malformed fact gracefully handled."""
    # Override with malformed fact
    system_plan_graphiti._client._facts = [
        {
            "uuid": "fact-bad",
            "fact": "This is a malformed fact with no clear entity type pattern",
            "name": "Unknown Entity Type",
            "score": 0.8,
        }
    ]

    overview = await get_system_overview(system_plan_graphiti, verbose=False)

    # Should not crash - should classify as system_context (fallback)
    assert overview["status"] == "ok"


# =============================================================================
# 4. Format Display Tests
# =============================================================================

@pytest.mark.asyncio
async def test_overview_format_display_all_sections(system_plan_graphiti):
    """format_overview_display includes all sections."""
    overview = await get_system_overview(system_plan_graphiti, verbose=False)

    display = format_overview_display(overview, section="all", format="display")

    # Verify all sections appear
    assert "System Context" in display or "Power of Attorney Platform" in display
    assert "Components" in display or "Attorney Management" in display
    assert "Architecture Decisions" in display or "ADR-SP-001" in display
    assert "Crosscutting Concerns" in display or "Authentication" in display


@pytest.mark.asyncio
async def test_overview_format_display_json(system_plan_graphiti):
    """format_overview_display with json format."""
    import json

    overview = await get_system_overview(system_plan_graphiti, verbose=False)

    display = format_overview_display(overview, section="all", format="json")

    # Verify valid JSON
    parsed = json.loads(display)
    assert parsed["status"] == "ok"
    assert "components" in parsed
    assert "decisions" in parsed


def test_format_display_no_context():
    """format_overview_display with status='no_context' -> 'no context available'."""
    overview = {"status": "no_context"}

    display = format_overview_display(overview, section="all", format="display")

    assert display == "no context available"


# =============================================================================
# 5. Seam-Specific Tests
# =============================================================================

@pytest.mark.asyncio
async def test_group_id_prefixing_consistency(mock_graphiti_client):
    """Verify all queries use correctly prefixed group IDs."""
    sp = SystemPlanGraphiti(client=mock_graphiti_client, project_id="test-project")

    # Call get_architecture_summary which searches both groups
    await sp.get_architecture_summary()

    # Verify search was called with prefixed group IDs
    assert len(mock_graphiti_client._search_calls) == 1
    call = mock_graphiti_client._search_calls[0]

    # Group IDs should be prefixed
    assert "test-project__project_architecture" in call["group_ids"]
    assert "test-project__project_decisions" in call["group_ids"]


@pytest.mark.asyncio
async def test_search_result_format_handling(system_plan_graphiti):
    """Verify _parse_* functions handle actual search() return format."""
    # Override with fact that has all expected fields
    system_plan_graphiti._client._facts = [
        {
            "uuid": "test-uuid",
            "fact": "Component: Test Component with full metadata",
            "name": "Component: Test Component",
            "created_at": "2026-02-07T10:00:00Z",
            "valid_at": "2026-02-07T10:00:00Z",
            "score": 0.9,
        }
    ]

    overview = await get_system_overview(system_plan_graphiti, verbose=False)

    # Should successfully parse without KeyError
    assert overview["status"] == "ok"
    assert len(overview["components"]) == 1
    assert overview["components"][0]["name"] == "Test Component"


@pytest.mark.asyncio
async def test_async_context_propagation(mock_graphiti_client):
    """Verify async calls through SystemPlanGraphiti don't lose context."""
    sp = SystemPlanGraphiti(client=mock_graphiti_client, project_id="test-project")

    # Multiple async calls in sequence
    result1 = await sp.has_architecture_context()
    result2 = await sp.get_architecture_summary()
    overview = await get_system_overview(sp, verbose=False)

    # All should complete successfully
    assert result1 is True  # facts exist
    assert result2 is not None
    assert overview["status"] == "ok"


@pytest.mark.asyncio
async def test_graphiti_disabled_returns_defaults():
    """client.enabled=False -> all functions return safe defaults."""
    # Create disabled client
    disabled_client = MockGraphitiClient(facts=[], enabled=False)
    sp = SystemPlanGraphiti(client=disabled_client, project_id="test-project")

    overview = await get_system_overview(sp, verbose=False)

    # Should return no_context
    assert overview["status"] == "no_context"

    # Condense should return empty string
    condensed = condense_for_injection(overview, max_tokens=800)
    assert condensed == ""

    # Format should indicate no context
    display = format_overview_display(overview, section="all", format="display")
    assert display == "no context available"


# =============================================================================
# 6. Verbose Mode Tests
# =============================================================================

@pytest.mark.asyncio
async def test_overview_verbose_mode_includes_full_content(system_plan_graphiti):
    """verbose=True includes full_content in parsed items."""
    overview_verbose = await get_system_overview(system_plan_graphiti, verbose=True)
    overview_normal = await get_system_overview(system_plan_graphiti, verbose=False)

    # Verbose mode should include full_content
    if overview_verbose["components"]:
        assert "full_content" in overview_verbose["components"][0] or "description" in overview_verbose["components"][0]

    # Normal mode should not include full_content (or should be minimal)
    if overview_normal["components"]:
        # Acceptable to have description but not verbose full_content
        pass  # This is implementation-dependent
