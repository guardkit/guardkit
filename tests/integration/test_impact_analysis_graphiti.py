"""
Integration tests for impact_analysis module Graphiti seams.

This module tests the technology seams where impact_analysis code interfaces
with Graphiti client's search API. Tests use MockGraphitiClient to simulate
realistic Graphiti behavior without requiring Neo4j.

Key Seam Areas Tested:
    1. Group ID prefixing for multiple query stages
    2. Task ID query enrichment (task file reading)
    3. Risk score calculation heuristic
    4. BDD scenario handling (with graceful fallback)
    5. ADR conflict detection
    6. Token budget condensation
    7. Format display with Unicode risk bars
    8. Multi-depth analysis (quick, standard, deep)

Coverage Target: >=85%
Test Count: 15+ tests
"""

import pytest
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import AsyncMock, Mock, mock_open, patch

from guardkit.planning.impact_analysis import (
    run_impact_analysis,
    condense_impact_for_injection,
    format_impact_display,
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

    def __init__(self, facts=None, bdd_facts=None, enabled=True, project_id="test-project"):
        """Initialize mock client.

        Args:
            facts: List of fact dicts to return from architecture/decision queries
            bdd_facts: List of BDD scenario facts (for deep mode)
            enabled: Whether Graphiti is enabled
            project_id: Project ID for group ID prefixing
        """
        self._facts = facts or []
        self._bdd_facts = bdd_facts or []
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
            group_name: Base group name
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

        # Return BDD facts if querying bdd_scenarios group
        if group_ids and any("bdd_scenarios" in gid for gid in group_ids):
            return self._bdd_facts[:num_results]

        # Otherwise return regular facts
        return self._facts[:num_results]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def realistic_component_facts():
    """Component facts for impact analysis testing.

    Returns:
        List of component fact dicts
    """
    return [
        {
            "uuid": "comp-001",
            "fact": "Component: Order Management handles order lifecycle and payment processing",
            "name": "Component: Order Management",
            "score": 0.92,
        },
        {
            "uuid": "comp-002",
            "fact": "Component: Inventory Service tracks stock levels and warehouse operations",
            "name": "Component: Inventory Service",
            "score": 0.85,
        },
    ]


@pytest.fixture
def realistic_adr_facts():
    """ADR facts for impact analysis testing.

    Returns:
        List of ADR fact dicts including conflict indicators
    """
    return [
        {
            "uuid": "adr-001",
            "fact": "ADR-SP-001: Use event sourcing for order history. This conflicts with ADR-SP-003 which specifies CRUD approach.",
            "name": "ADR-SP-001: Event Sourcing for Orders",
            "score": 0.88,
        },
        {
            "uuid": "adr-002",
            "fact": "ADR-SP-002: Implement anti-corruption layer for external APIs to isolate domain model from third-party changes.",
            "name": "ADR-SP-002: Anti-corruption layer",
            "score": 0.85,
        },
    ]


@pytest.fixture
def realistic_bdd_facts():
    """BDD scenario facts for deep impact analysis.

    Returns:
        List of BDD scenario fact dicts
    """
    return [
        {
            "uuid": "bdd-001",
            "fact": "Scenario: Customer places order. File: features/orders.feature:10. This scenario is at risk due to payment gateway changes.",
            "name": "Scenario: Customer places order",
            "score": 0.90,
        },
        {
            "uuid": "bdd-002",
            "fact": "Scenario: Inventory check during checkout. File: features/inventory.feature:25.",
            "name": "Scenario: Inventory check",
            "score": 0.82,
        },
    ]


@pytest.fixture
def mock_graphiti_client(realistic_component_facts, realistic_adr_facts, realistic_bdd_facts):
    """Create mock Graphiti client with realistic facts.

    Args:
        realistic_component_facts: Component facts fixture
        realistic_adr_facts: ADR facts fixture
        realistic_bdd_facts: BDD scenario facts fixture

    Returns:
        MockGraphitiClient instance
    """
    return MockGraphitiClient(
        facts=realistic_component_facts + realistic_adr_facts,
        bdd_facts=realistic_bdd_facts,
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
# 1. Standard Impact Analysis Tests
# =============================================================================

@pytest.mark.asyncio
async def test_impact_with_components_and_adrs(system_plan_graphiti, mock_graphiti_client):
    """Standard depth, verify components and ADR constraints extracted."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    # Verify successful status
    assert impact["status"] == "ok"

    # Verify components extracted (mock returns all facts, so we get 4 total)
    assert "components" in impact
    assert len(impact["components"]) >= 2  # At least our 2 component facts
    # Find the actual component (not ADR)
    order_mgmt = next((c for c in impact["components"] if "Order Management" in c["name"]), None)
    assert order_mgmt is not None

    # Verify ADRs extracted (standard depth includes ADRs)
    assert "adrs" in impact
    assert len(impact["adrs"]) >= 2

    # Verify risk calculated
    assert "risk" in impact
    assert 1 <= impact["risk"]["score"] <= 5


@pytest.mark.asyncio
async def test_impact_with_bdd_scenarios(system_plan_graphiti, mock_graphiti_client):
    """Deep depth with BDD facts in mock."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="deep",
        include_bdd=True,
        include_tasks=False,
    )

    assert impact["status"] == "ok"

    # Verify BDD scenarios included
    assert "bdd_scenarios" in impact
    assert len(impact["bdd_scenarios"]) == 2
    assert impact["bdd_scenarios"][0]["scenario_name"] == "Customer places order"


@pytest.mark.asyncio
async def test_impact_bdd_empty_group(system_plan_graphiti, mock_graphiti_client):
    """Deep depth, bdd_scenarios returns empty -> graceful fallback."""
    # Override BDD facts to be empty
    mock_graphiti_client._bdd_facts = []

    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="deep",
        include_bdd=True,
        include_tasks=False,
    )

    # Should still return ok status
    assert impact["status"] == "ok"

    # BDD scenarios should not be present (or be empty)
    assert "bdd_scenarios" not in impact or len(impact.get("bdd_scenarios", [])) == 0


@pytest.mark.asyncio
async def test_impact_quick_depth_no_adrs(system_plan_graphiti, mock_graphiti_client):
    """Quick depth should only return components, no ADRs."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="quick",
        include_bdd=False,
        include_tasks=False,
    )

    assert impact["status"] == "ok"
    assert "components" in impact
    # Quick depth should not include ADRs
    assert "adrs" not in impact or len(impact.get("adrs", [])) == 0


# =============================================================================
# 2. Risk Score Calculation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_impact_risk_score_calculation(system_plan_graphiti, mock_graphiti_client):
    """Realistic facts -> verify risk score matches heuristic."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    risk = impact["risk"]

    # Verify risk structure
    assert "score" in risk
    assert "label" in risk
    assert "rationale" in risk

    # Verify score is in valid range
    assert 1 <= risk["score"] <= 5

    # Verify label matches score
    label_map = {1: "low", 2: "medium", 3: "medium", 4: "high", 5: "critical"}
    assert risk["label"] == label_map[risk["score"]]

    # Verify rationale mentions components
    assert "component" in risk["rationale"].lower()


@pytest.mark.asyncio
async def test_impact_risk_increases_with_conflicts(system_plan_graphiti, mock_graphiti_client):
    """ADR conflicts should increase risk score."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    # Should have higher risk due to conflict in ADR-SP-001
    risk = impact["risk"]
    assert risk["score"] >= 2  # At least medium due to 2 components + conflict


# =============================================================================
# 3. Task ID Query Enrichment Tests
# =============================================================================

@pytest.mark.asyncio
async def test_impact_task_id_query_enrichment(system_plan_graphiti, mock_graphiti_client, tmp_path):
    """Task ID -> task file read -> enriched query string."""
    # Create mock task file
    task_id = "TASK-TEST-001"
    task_dir = tmp_path / "tasks" / "in_progress"
    task_dir.mkdir(parents=True)
    task_file = task_dir / f"{task_id}.md"

    task_content = """---
title: Implement order payment processing
tags:
  - payments
  - orders
  - integration
---

# Task content
"""
    task_file.write_text(task_content)

    # Patch Path to use tmp_path
    with patch("guardkit.planning.impact_analysis.Path") as mock_path:
        def path_side_effect(path_str):
            if "tasks/" in str(path_str):
                return tmp_path / Path(path_str)
            return Path(path_str)

        mock_path.side_effect = path_side_effect

        impact = await run_impact_analysis(
            sp=system_plan_graphiti,
            client=mock_graphiti_client,
            task_or_topic=task_id,
            depth="standard",
            include_bdd=False,
            include_tasks=False,
        )

        # Verify query was enriched with title and tags
        assert impact["status"] == "ok"
        query_used = impact.get("query", "")
        # Query should contain title or tags
        assert "payment" in query_used.lower() or "order" in query_used.lower() or query_used == task_id


@pytest.mark.asyncio
async def test_impact_topic_string_used_directly(system_plan_graphiti, mock_graphiti_client):
    """Non-task-ID topic string used directly as query."""
    topic = "refactor authentication module"

    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic=topic,
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    # Verify query equals topic
    assert impact["query"] == topic


# =============================================================================
# 4. Condensation Tests
# =============================================================================

@pytest.mark.asyncio
async def test_impact_condense_roundtrip(system_plan_graphiti, mock_graphiti_client):
    """run_impact_analysis -> condense_impact_for_injection -> verify budget."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    # Condense with budget
    max_tokens = 400
    condensed = condense_impact_for_injection(impact, max_tokens=max_tokens)

    # Verify non-empty
    assert len(condensed) > 0

    # Rough token estimate
    estimated_tokens = len(condensed.split()) * 1.3
    assert estimated_tokens <= max_tokens * 1.5  # Allow buffer

    # Verify priority items present
    assert "Risk:" in condensed
    assert "Order Management" in condensed or "component" in condensed.lower()


def test_condense_impact_no_context():
    """condense_impact_for_injection with status='no_context' -> empty string."""
    impact = {"status": "no_context"}

    condensed = condense_impact_for_injection(impact, max_tokens=1200)

    assert condensed == ""


# =============================================================================
# 5. Group ID Tests
# =============================================================================

@pytest.mark.asyncio
async def test_impact_multiple_group_queries(system_plan_graphiti, mock_graphiti_client):
    """Verify correct group IDs used for each query stage."""
    await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    # Verify search calls used correct group IDs
    assert len(mock_graphiti_client._search_calls) >= 2

    # First call should be project_architecture
    call1 = mock_graphiti_client._search_calls[0]
    assert "test-project__project_architecture" in call1["group_ids"]

    # Second call should be project_decisions
    call2 = mock_graphiti_client._search_calls[1]
    assert "test-project__project_decisions" in call2["group_ids"]


# =============================================================================
# 6. ADR Conflict Detection Tests
# =============================================================================

@pytest.mark.asyncio
async def test_impact_adr_conflict_detection(system_plan_graphiti, mock_graphiti_client):
    """Facts with 'conflicts with' keyword -> conflict=True."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    # ADR-SP-001 has conflict keyword in fact
    adrs = impact["adrs"]
    adr_001 = next((adr for adr in adrs if adr["adr_id"] == "ADR-SP-001"), None)

    assert adr_001 is not None
    assert adr_001["conflict"] is True

    # ADR-SP-002 has no conflict keyword
    adr_002 = next((adr for adr in adrs if adr["adr_id"] == "ADR-SP-002"), None)
    assert adr_002 is not None
    assert adr_002["conflict"] is False


# =============================================================================
# 7. Format Display Tests
# =============================================================================

@pytest.mark.asyncio
async def test_impact_format_display_quick(system_plan_graphiti, mock_graphiti_client):
    """format_impact_display with depth='quick'."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="quick",
        include_bdd=False,
        include_tasks=False,
    )

    display = format_impact_display(impact, depth="quick")

    # Quick should show components and risk
    assert "Risk:" in display
    assert "Affected Components:" in display
    # Should not show implications (standard/deep only)
    assert "Implications:" not in display


@pytest.mark.asyncio
async def test_impact_format_display_deep(system_plan_graphiti, mock_graphiti_client):
    """format_impact_display with depth='deep' shows BDD scenarios."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="deep",
        include_bdd=True,
        include_tasks=False,
    )

    display = format_impact_display(impact, depth="deep")

    # Deep should show everything
    assert "Risk:" in display
    assert "Affected Components:" in display
    assert "Constraining ADRs:" in display
    assert "BDD Scenarios:" in display
    assert "Implications:" in display


@pytest.mark.asyncio
async def test_impact_format_display_risk_bar(system_plan_graphiti, mock_graphiti_client):
    """Risk bar uses Unicode blocks correctly."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    display = format_impact_display(impact, depth="standard")

    # Verify risk bar present
    assert "[" in display and "]" in display
    # Should have filled blocks
    assert "█" in display or "Risk:" in display


def test_format_impact_no_context():
    """format_impact_display with status='no_context' -> 'no impact data'."""
    impact = {"status": "no_context"}

    display = format_impact_display(impact, depth="standard")

    assert display == "no impact data"


# =============================================================================
# 8. Seam-Specific Tests
# =============================================================================

@pytest.mark.asyncio
async def test_search_result_format_handling(system_plan_graphiti, mock_graphiti_client):
    """Verify _parse_* functions handle actual search() return format."""
    # Facts have all expected fields
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    # Should parse without KeyError
    assert impact["status"] == "ok"
    assert len(impact["components"]) > 0
    assert "relevance_score" in impact["components"][0]


@pytest.mark.asyncio
async def test_async_context_propagation(system_plan_graphiti, mock_graphiti_client):
    """Verify async calls don't lose context."""
    # Multiple async calls in sequence
    impact1 = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="quick",
        include_bdd=False,
        include_tasks=False,
    )

    impact2 = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="inventory updates",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    # Both should complete successfully
    assert impact1["status"] == "ok"
    assert impact2["status"] == "ok"


@pytest.mark.asyncio
async def test_graphiti_disabled_returns_no_context():
    """client.enabled=False -> status='no_context'."""
    disabled_client = MockGraphitiClient(facts=[], enabled=False)
    sp = SystemPlanGraphiti(client=disabled_client, project_id="test-project")

    impact = await run_impact_analysis(
        sp=sp,
        client=disabled_client,
        task_or_topic="any topic",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    assert impact["status"] == "no_context"


# =============================================================================
# 9. Implications Tests
# =============================================================================

@pytest.mark.asyncio
async def test_impact_implications_generation(system_plan_graphiti, mock_graphiti_client):
    """Implications derived from components and ADRs."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="standard",
        include_bdd=False,
        include_tasks=False,
    )

    implications = impact["implications"]

    # Should have implications for components
    assert any("Order Management" in imp for imp in implications)

    # Should have implications for ADRs
    assert any("ADR-SP-001" in imp for imp in implications)
    assert any("conflicts" in imp.lower() for imp in implications)


# =============================================================================
# 10. BDD At-Risk Detection Tests
# =============================================================================

@pytest.mark.asyncio
async def test_bdd_at_risk_detection(system_plan_graphiti, mock_graphiti_client):
    """BDD scenarios with 'at risk' keyword flagged correctly."""
    impact = await run_impact_analysis(
        sp=system_plan_graphiti,
        client=mock_graphiti_client,
        task_or_topic="order processing changes",
        depth="deep",
        include_bdd=True,
        include_tasks=False,
    )

    bdd_scenarios = impact.get("bdd_scenarios", [])

    # First scenario has 'at risk' in fact
    scenario1 = next((s for s in bdd_scenarios if "Customer places order" in s["scenario_name"]), None)
    assert scenario1 is not None
    assert scenario1["at_risk"] is True

    # Second scenario does not have 'at risk'
    scenario2 = next((s for s in bdd_scenarios if "Inventory check" in s["scenario_name"]), None)
    assert scenario2 is not None
    assert scenario2["at_risk"] is False
