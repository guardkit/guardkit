"""Tests for impact_analysis.py module.

TDD RED phase tests for TASK-SC-003. These tests verify the impact analysis engine,
risk scoring, multi-depth query logic, and graceful degradation with missing BDD groups.

Coverage Target: >=85%
Test Count: 21+ tests

Key patterns verified:
- Multi-group Graphiti queries (components, ADRs, BDD, tasks)
- Risk scoring heuristic (1-5 scale with clamping)
- Task ID vs topic string query building
- Token-budgeted condensation for coach injection
- Depth tier filtering (quick, standard, deep)
- Graceful degradation when BDD group missing/empty
- [Graphiti] prefix on all log messages
"""

import json
import pytest
import re
from typing import Dict, List, Any, Optional
from unittest.mock import AsyncMock, MagicMock, patch, mock_open
from pathlib import Path

# These imports will fail until implementation exists (TDD RED phase)
from guardkit.planning.impact_analysis import (
    run_impact_analysis,
    condense_impact_for_injection,
    format_impact_display,
    _build_query,
    _calculate_risk,
    _parse_component_hits,
    _parse_adr_hits,
    _parse_bdd_hits,
    _derive_implications,
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
def mock_client() -> MagicMock:
    """Create a mock GraphitiClient instance."""
    client = MagicMock()
    client.enabled = True
    client.search = AsyncMock()
    client.get_group_id = MagicMock(side_effect=lambda name: f"test-project_{name}")
    return client


@pytest.fixture
def sample_component_hits() -> List[Dict[str, Any]]:
    """Create sample Graphiti component search results."""
    return [
        {
            "uuid": "uuid-comp-001",
            "name": "Component: Order Management",
            "fact": "Component: Order Management handles order lifecycle. Responsibilities: create orders, track status, cancel orders. Dependencies: Inventory, Payment.",
            "score": 0.95,
        },
        {
            "uuid": "uuid-comp-002",
            "name": "Component: Inventory Service",
            "fact": "Component: Inventory Service manages stock levels. Uses CQRS pattern for read/write separation. Handles stock allocation.",
            "score": 0.88,
        },
    ]


@pytest.fixture
def sample_adr_hits_conflict() -> List[Dict[str, Any]]:
    """Create sample ADR search results with conflicts."""
    return [
        {
            "uuid": "uuid-adr-001",
            "name": "ADR-SP-001: Use Event Sourcing",
            "fact": "ADR-SP-001: Use Event Sourcing for Order Aggregate. Status: accepted. Context: Orders require complete audit trail. Consequences: Full audit trail, Complex replay logic.",
            "score": 0.92,
        },
        {
            "uuid": "uuid-adr-002",
            "name": "ADR-SP-002: GraphQL API Gateway",
            "fact": "ADR-SP-002: GraphQL API Gateway. Status: superseded. This decision conflicts with ADR-SP-003 which mandates REST. Replaced by REST due to complexity.",
            "score": 0.85,
        },
    ]


@pytest.fixture
def sample_adr_hits_informational() -> List[Dict[str, Any]]:
    """Create sample ADR search results without conflicts."""
    return [
        {
            "uuid": "uuid-adr-003",
            "name": "ADR-SP-003: Use REST API",
            "fact": "ADR-SP-003: Use REST API for all services. Status: accepted. Context: Simplicity and wide adoption. Consequences: Standard tooling support.",
            "score": 0.90,
        },
    ]


@pytest.fixture
def sample_bdd_hits() -> List[Dict[str, Any]]:
    """Create sample BDD scenario search results."""
    return [
        {
            "uuid": "uuid-bdd-001",
            "name": "Scenario: Create order successfully",
            "fact": "Scenario: Create order successfully. File: features/orders.feature:10. Given user is authenticated, When user creates order with valid items, Then order is created and confirmation sent.",
            "score": 0.87,
        },
        {
            "uuid": "uuid-bdd-002",
            "name": "Scenario: Handle out-of-stock items",
            "fact": "Scenario: Handle out-of-stock items at risk due to inventory changes. File: features/inventory.feature:25. Given items are out of stock, When user attempts to order, Then appropriate error is returned.",
            "score": 0.82,
        },
    ]


@pytest.fixture
def mock_task_file_content() -> str:
    """Create sample task file content."""
    return """---
id: TASK-SC-005
title: Implement order processing feature
status: backlog
priority: high
tags:
  - orders
  - payment
  - inventory
---

# Task: Implement order processing feature

## Description
Build order processing pipeline that handles order creation, payment validation, and inventory reservation.

## Acceptance Criteria
- [ ] Order creation endpoint
- [ ] Payment integration
- [ ] Inventory checks
"""


# =========================================================================
# 1. RUN_IMPACT_ANALYSIS TESTS (4 tests)
# =========================================================================


class TestRunImpactAnalysis:
    """Tests for run_impact_analysis function."""

    @pytest.mark.asyncio
    async def test_run_impact_analysis_standard(
        self,
        mock_sp: MagicMock,
        mock_client: MagicMock,
        sample_component_hits: List[Dict],
        sample_adr_hits_informational: List[Dict],
    ):
        """Test run_impact_analysis with standard depth (components + ADRs)."""
        # Setup mock searches
        async def mock_search(query, group_ids, num_results):
            if "project_architecture" in group_ids[0]:
                return sample_component_hits
            elif "project_decisions" in group_ids[0]:
                return sample_adr_hits_informational
            return []

        mock_client.search = AsyncMock(side_effect=mock_search)

        result = await run_impact_analysis(
            sp=mock_sp,
            client=mock_client,
            task_or_topic="order processing",
            depth="standard",
            include_bdd=False,
            include_tasks=False,
        )

        assert result["status"] == "ok"
        assert "components" in result
        assert "adrs" in result
        assert "risk" in result
        assert len(result["components"]) == 2
        assert len(result["adrs"]) == 1
        assert result["risk"]["score"] >= 1
        assert result["risk"]["score"] <= 5

    @pytest.mark.asyncio
    async def test_run_impact_analysis_exception_handling(
        self,
        mock_sp: MagicMock,
        mock_client: MagicMock,
    ):
        """Test run_impact_analysis handles exceptions gracefully."""
        # Make search raise an exception
        mock_client.search = AsyncMock(side_effect=Exception("Search failed"))

        with patch("guardkit.planning.impact_analysis.logger") as mock_logger:
            result = await run_impact_analysis(
                sp=mock_sp,
                client=mock_client,
                task_or_topic="test query",
                depth="standard",
                include_bdd=False,
                include_tasks=False,
            )

            assert result["status"] == "no_context"
            mock_logger.warning.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_impact_analysis_quick(
        self,
        mock_sp: MagicMock,
        mock_client: MagicMock,
        sample_component_hits: List[Dict],
    ):
        """Test run_impact_analysis with quick depth (components only)."""
        mock_client.search = AsyncMock(return_value=sample_component_hits)

        result = await run_impact_analysis(
            sp=mock_sp,
            client=mock_client,
            task_or_topic="order processing",
            depth="quick",
            include_bdd=False,
            include_tasks=False,
        )

        assert result["status"] == "ok"
        assert "components" in result
        assert "adrs" not in result  # Quick mode doesn't query ADRs
        assert "bdd_scenarios" not in result
        assert len(result["components"]) == 2

    @pytest.mark.asyncio
    async def test_run_impact_analysis_deep_with_bdd(
        self,
        mock_sp: MagicMock,
        mock_client: MagicMock,
        sample_component_hits: List[Dict],
        sample_adr_hits_informational: List[Dict],
        sample_bdd_hits: List[Dict],
    ):
        """Test run_impact_analysis with deep depth and BDD scenarios present."""
        # Setup mock searches
        async def mock_search(query, group_ids, num_results):
            if "project_architecture" in group_ids[0]:
                return sample_component_hits
            elif "project_decisions" in group_ids[0]:
                return sample_adr_hits_informational
            elif "bdd_scenarios" in group_ids[0]:
                return sample_bdd_hits
            return []

        mock_client.search = AsyncMock(side_effect=mock_search)

        result = await run_impact_analysis(
            sp=mock_sp,
            client=mock_client,
            task_or_topic="order processing",
            depth="deep",
            include_bdd=True,
            include_tasks=True,
        )

        assert result["status"] == "ok"
        assert "components" in result
        assert "adrs" in result
        assert "bdd_scenarios" in result
        assert len(result["bdd_scenarios"]) == 2

    @pytest.mark.asyncio
    async def test_run_impact_analysis_deep_no_bdd(
        self,
        mock_sp: MagicMock,
        mock_client: MagicMock,
        sample_component_hits: List[Dict],
        sample_adr_hits_informational: List[Dict],
    ):
        """Test run_impact_analysis with deep depth but no BDD scenarios (graceful degradation)."""
        # Setup mock searches - BDD group returns empty
        async def mock_search(query, group_ids, num_results):
            if "project_architecture" in group_ids[0]:
                return sample_component_hits
            elif "project_decisions" in group_ids[0]:
                return sample_adr_hits_informational
            elif "bdd_scenarios" in group_ids[0]:
                return []  # Empty BDD results
            return []

        mock_client.search = AsyncMock(side_effect=mock_search)

        with patch("guardkit.planning.impact_analysis.logger") as mock_logger:
            result = await run_impact_analysis(
                sp=mock_sp,
                client=mock_client,
                task_or_topic="order processing",
                depth="deep",
                include_bdd=True,
                include_tasks=False,
            )

            # Should gracefully degrade - no BDD section
            assert result["status"] == "ok"
            assert "components" in result
            assert "adrs" in result
            assert "bdd_scenarios" not in result  # Graceful degradation

            # Should log degradation message
            mock_logger.info.assert_any_call(
                "[Graphiti] No BDD scenarios found, skipping BDD impact section"
            )


# =========================================================================
# 2. CALCULATE_RISK TESTS (4 tests)
# =========================================================================


class TestCalculateRisk:
    """Tests for _calculate_risk function."""

    def test_calculate_risk_low(self):
        """Test risk calculation for low risk scenario (1 component, no conflicts)."""
        components = [{"name": "Service A"}]
        adrs = [{"conflict": False}]
        bdd_scenarios = []

        result = _calculate_risk(components, adrs, bdd_scenarios)

        assert result["score"] == 1
        assert result["label"] == "low"
        assert "rationale" in result

    def test_calculate_risk_medium(self):
        """Test risk calculation for medium risk scenario (2 components, 1 ADR)."""
        components = [{"name": "Service A"}, {"name": "Service B"}]
        adrs = [{"conflict": False}]
        bdd_scenarios = []

        result = _calculate_risk(components, adrs, bdd_scenarios)

        # Base 1.0 + 0.5 for second component = 1.5, rounded to 2
        assert result["score"] >= 2
        assert result["score"] <= 3
        assert result["label"] in ["low", "medium"]

    def test_calculate_risk_high(self):
        """Test risk calculation for high risk scenario (3+ components, conflicts, BDD)."""
        components = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        adrs = [{"conflict": True}, {"conflict": False}]
        bdd_scenarios = [{"at_risk": True}]

        result = _calculate_risk(components, adrs, bdd_scenarios)

        # Base 1.0 + 1.0 (2 extra components) + 1.0 (conflict) + 0.25 (info ADR) + 0.3 (BDD) = 3.55
        # Should be clamped and rounded
        assert result["score"] >= 3
        assert result["score"] <= 5
        assert result["label"] in ["medium", "high", "critical"]

    def test_calculate_risk_clamping(self):
        """Test risk calculation clamps to 1-5 range."""
        # Extreme high scenario
        components = [{"name": f"Service {i}"} for i in range(10)]
        adrs = [{"conflict": True} for _ in range(5)]
        bdd_scenarios = [{"at_risk": True} for _ in range(3)]

        result = _calculate_risk(components, adrs, bdd_scenarios)

        # Should clamp to max 5
        assert result["score"] == 5
        assert result["label"] == "critical"

        # Extreme low scenario (should never go below 1)
        result_low = _calculate_risk([], [], [])
        assert result_low["score"] >= 1


# =========================================================================
# 3. BUILD_QUERY TESTS (3 tests)
# =========================================================================


class TestBuildQuery:
    """Tests for _build_query function."""

    def test_build_query_from_task_id(self, mock_task_file_content: str):
        """Test _build_query extracts query from task file when given task ID."""
        with patch("builtins.open", mock_open(read_data=mock_task_file_content)):
            with patch("pathlib.Path.exists", return_value=True):
                result = _build_query("TASK-SC-005")

                # Should extract title and tags from task file
                assert "order processing" in result.lower()
                # Should include tags for enrichment
                assert "orders" in result.lower() or "payment" in result.lower()

    def test_build_query_from_topic(self):
        """Test _build_query uses topic string directly when not a task ID."""
        result = _build_query("implement authentication system")

        # Should return the topic string as-is
        assert "authentication" in result.lower()
        assert "implement" in result.lower()

    def test_build_query_invalid_task_id(self):
        """Test _build_query falls back to task ID when file not found."""
        with patch("pathlib.Path.exists", return_value=False):
            result = _build_query("TASK-INVALID-999")

            # Should fall back to using the task ID itself as query
            assert "TASK-INVALID-999" in result or "invalid" in result.lower()

    def test_build_query_file_read_error(self):
        """Test _build_query handles file read errors gracefully."""
        with patch("pathlib.Path.exists", return_value=True):
            with patch("builtins.open", side_effect=IOError("Permission denied")):
                with patch("guardkit.planning.impact_analysis.logger") as mock_logger:
                    result = _build_query("TASK-SC-005")

                    # Should fall back to task ID
                    assert "TASK-SC-005" in result

                    # Should log the error (once per directory tried)
                    assert mock_logger.debug.call_count >= 1


# =========================================================================
# 4. PARSE FUNCTIONS TESTS (5 tests)
# =========================================================================


class TestParseFunctions:
    """Tests for _parse_component_hits, _parse_adr_hits, _parse_bdd_hits."""

    def test_parse_component_hits(self, sample_component_hits: List[Dict]):
        """Test _parse_component_hits extracts component details."""
        result = _parse_component_hits(sample_component_hits)

        assert len(result) == 2
        assert result[0]["name"] == "Order Management"
        assert "order lifecycle" in result[0]["description"].lower()
        assert result[0]["relevance_score"] == 0.95

    def test_parse_component_hits_without_prefix(self):
        """Test _parse_component_hits handles names without 'Component:' prefix."""
        hits = [
            {
                "uuid": "uuid-001",
                "name": "Authentication Service",
                "fact": "Authentication Service provides user authentication and authorization.",
                "score": 0.92,
            }
        ]

        result = _parse_component_hits(hits)

        assert len(result) == 1
        assert result[0]["name"] == "Authentication Service"
        assert "authentication" in result[0]["description"].lower()

    def test_parse_adr_hits_conflict(self, sample_adr_hits_conflict: List[Dict]):
        """Test _parse_adr_hits detects conflict keywords."""
        result = _parse_adr_hits(sample_adr_hits_conflict)

        assert len(result) == 2
        # First ADR has no conflict
        assert result[0]["adr_id"] == "ADR-SP-001"
        assert result[0]["conflict"] is False

        # Second ADR has conflict keyword
        assert result[1]["adr_id"] == "ADR-SP-002"
        assert result[1]["conflict"] is True

    def test_parse_adr_hits_informational(self, sample_adr_hits_informational: List[Dict]):
        """Test _parse_adr_hits handles informational ADRs (no conflicts)."""
        result = _parse_adr_hits(sample_adr_hits_informational)

        assert len(result) == 1
        assert result[0]["adr_id"] == "ADR-SP-003"
        assert result[0]["title"] == "Use REST API"
        assert result[0]["conflict"] is False

    def test_parse_bdd_hits(self, sample_bdd_hits: List[Dict]):
        """Test _parse_bdd_hits extracts scenario details."""
        result = _parse_bdd_hits(sample_bdd_hits)

        assert len(result) == 2
        assert "Create order successfully" in result[0]["scenario_name"]
        assert "features/orders.feature" in result[0]["file_location"]
        assert result[0]["at_risk"] is False

        # Second scenario has "at risk" keyword
        assert "Handle out-of-stock" in result[1]["scenario_name"]
        assert result[1]["at_risk"] is True

    def test_parse_bdd_hits_without_file_location(self):
        """Test _parse_bdd_hits handles missing file location."""
        hits = [
            {
                "uuid": "uuid-001",
                "name": "Scenario: User login",
                "fact": "Scenario: User login. User provides credentials and logs in.",
                "score": 0.85,
            }
        ]

        result = _parse_bdd_hits(hits)

        assert len(result) == 1
        assert result[0]["scenario_name"] == "User login"
        assert result[0]["file_location"] == ""
        assert result[0]["at_risk"] is False

    def test_missing_bdd_group_degrades(self):
        """Test _parse_bdd_hits handles empty/missing results gracefully."""
        result = _parse_bdd_hits([])

        assert result == []


# =========================================================================
# 5. DERIVE_IMPLICATIONS TESTS (1 test)
# =========================================================================


class TestDeriveImplications:
    """Tests for _derive_implications function."""

    def test_derive_implications(
        self,
        sample_component_hits: List[Dict],
        sample_adr_hits_conflict: List[Dict],
    ):
        """Test _derive_implications generates human-readable implications."""
        components = _parse_component_hits(sample_component_hits)
        adrs = _parse_adr_hits(sample_adr_hits_conflict)

        result = _derive_implications(components, adrs)

        # Should generate implications based on components and ADRs
        assert len(result) > 0
        assert any("Order Management" in imp for imp in result)

        # Should mention conflicts
        assert any("conflict" in imp.lower() or "ADR-SP-002" in imp for imp in result)


# =========================================================================
# 6. CONDENSE_IMPACT_FOR_INJECTION TESTS (2 tests)
# =========================================================================


class TestCondenseImpactForInjection:
    """Tests for condense_impact_for_injection function."""

    def test_condense_impact_within_budget(self):
        """Test condense_impact_for_injection respects token budget."""
        impact = {
            "status": "ok",
            "risk": {"score": 3, "label": "medium", "rationale": "Multiple components affected"},
            "components": [
                {"name": "Order Management", "description": "Handles order lifecycle"},
                {"name": "Inventory Service", "description": "Manages stock levels"},
            ],
            "adrs": [
                {"adr_id": "ADR-SP-001", "title": "Use Event Sourcing", "conflict": False}
            ],
        }

        result = condense_impact_for_injection(impact, max_tokens=200)

        estimated_tokens = _estimate_tokens(result)
        assert estimated_tokens <= 200

        # Should prioritize risk score and component names
        assert "risk" in result.lower() or "3" in result
        assert "Order Management" in result

    def test_condense_impact_empty(self):
        """Test condense_impact_for_injection with empty/no_context."""
        impact = {"status": "no_context"}

        result = condense_impact_for_injection(impact, max_tokens=1200)

        assert result == "" or "no context" in result.lower()

    def test_condense_impact_with_conflicts(self):
        """Test condense_impact_for_injection prioritizes conflict ADRs."""
        impact = {
            "status": "ok",
            "risk": {"score": 4, "label": "high", "rationale": "Conflicting ADRs"},
            "components": [
                {"name": "Payment Service", "description": "Handles payments"}
            ],
            "adrs": [
                {"adr_id": "ADR-SP-001", "title": "Use REST", "conflict": False},
                {"adr_id": "ADR-SP-002", "title": "Use GraphQL", "conflict": True},
            ],
            "implications": ["Payment Service needs refactoring"],
        }

        result = condense_impact_for_injection(impact, max_tokens=500)

        # Conflicts should appear before informational ADRs
        assert "CONFLICT" in result
        assert "ADR-SP-002" in result

    def test_condense_impact_tight_budget(self):
        """Test condense_impact_for_injection with very tight budget (truncates gracefully)."""
        impact = {
            "status": "ok",
            "risk": {"score": 2, "label": "low", "rationale": "Minimal impact"},
            "components": [
                {"name": "Service A"},
                {"name": "Service B"},
                {"name": "Service C"},
            ],
            "adrs": [
                {"adr_id": "ADR-001", "title": "Pattern 1", "conflict": False},
                {"adr_id": "ADR-002", "title": "Pattern 2", "conflict": False},
            ],
            "implications": ["Implication 1", "Implication 2", "Implication 3"],
        }

        result = condense_impact_for_injection(impact, max_tokens=50)

        estimated_tokens = _estimate_tokens(result)
        assert estimated_tokens <= 50

        # Should at least include risk (highest priority)
        assert "Risk" in result or "2" in result


# =========================================================================
# 7. FORMAT_IMPACT_DISPLAY TESTS (2 tests)
# =========================================================================


class TestFormatImpactDisplay:
    """Tests for format_impact_display function."""

    def test_format_impact_display_standard(self):
        """Test format_impact_display with standard depth."""
        impact = {
            "status": "ok",
            "risk": {"score": 3, "label": "medium", "rationale": "Multiple components affected"},
            "components": [
                {"name": "Order Management", "description": "Handles orders"}
            ],
            "adrs": [
                {"adr_id": "ADR-SP-001", "title": "Use Event Sourcing", "conflict": False}
            ],
            "implications": ["Order Management must implement event sourcing"],
        }

        result = format_impact_display(impact, depth="standard")

        # Should include risk bar
        assert "risk" in result.lower() or "medium" in result.lower()
        assert "Order Management" in result
        assert "ADR-SP-001" in result
        assert "implications" in result.lower()

    def test_format_impact_display_quick(self):
        """Test format_impact_display with quick depth (abbreviated)."""
        impact = {
            "status": "ok",
            "risk": {"score": 2, "label": "low", "rationale": "Single component"},
            "components": [{"name": "Service A"}],
        }

        result = format_impact_display(impact, depth="quick")

        # Should be more abbreviated
        assert "Service A" in result
        # Should not include ADRs or implications (not present in quick)
        assert len(result) < 500  # Reasonably short

    def test_format_impact_display_no_context(self):
        """Test format_impact_display with no_context status."""
        impact = {"status": "no_context"}

        result = format_impact_display(impact, depth="standard")

        assert "no impact data" in result.lower()

    def test_format_impact_display_deep_with_bdd(self):
        """Test format_impact_display with deep depth including BDD scenarios."""
        impact = {
            "status": "ok",
            "risk": {"score": 4, "label": "high", "rationale": "At-risk scenarios"},
            "components": [{"name": "Auth Service", "relevance_score": 0.95}],
            "adrs": [{"adr_id": "ADR-SEC-001", "title": "OAuth2", "conflict": True}],
            "bdd_scenarios": [
                {
                    "scenario_name": "User login",
                    "file_location": "features/auth.feature:15",
                    "at_risk": True,
                }
            ],
            "implications": ["Security review required"],
        }

        result = format_impact_display(impact, depth="deep")

        # Should include all sections
        assert "Auth Service" in result
        assert "ADR-SEC-001" in result
        assert "CONFLICT" in result
        assert "User login" in result
        assert "AT RISK" in result
        assert "features/auth.feature:15" in result
        assert "Security review required" in result


# =========================================================================
# 8. ESTIMATE_TOKENS TESTS (1 test)
# =========================================================================


class TestEstimateTokens:
    """Tests for _estimate_tokens function."""

    def test_estimate_tokens(self):
        """Test _estimate_tokens uses simple heuristic."""
        text = "This is a test with ten words total here."

        tokens = _estimate_tokens(text)

        # 10 words * 1.3 = 13 tokens approximately
        assert tokens >= 10
        assert tokens <= 15

        # Empty string
        assert _estimate_tokens("") == 0
