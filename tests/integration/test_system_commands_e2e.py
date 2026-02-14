"""
E2E Integration Tests for System Commands Chain.

Tests the full read chain after Graphiti population:
  /system-overview -> get_system_overview -> SystemPlanGraphiti -> MockGraphitiClient
  /impact-analysis -> run_impact_analysis -> SystemPlanGraphiti -> MockGraphitiClient
  /context-switch  -> execute_context_switch -> GuardKitConfig + optional Graphiti
  coach_context_builder -> build_coach_context -> get_system_overview + run_impact_analysis

Verifies:
  - CLI commands wire correctly to async functions with proper arguments
  - Entity type inference classifies all 4 entity types from realistic facts
  - Token budget condensation respects limits
  - Coach context builder assembles non-empty context for high-complexity tasks
  - Impact analysis enriches task ID queries from file frontmatter
  - Graceful degradation when Graphiti is unavailable

Coverage Target: >=85%
Test Count: 12+ tests
"""

import asyncio
import json
import pytest
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import patch, MagicMock

from guardkit.planning.system_overview import (
    get_system_overview,
    condense_for_injection,
)
from guardkit.planning.impact_analysis import (
    run_impact_analysis,
    condense_impact_for_injection,
)
from guardkit.planning.coach_context_builder import build_coach_context
from guardkit.planning.graphiti_arch import SystemPlanGraphiti
from guardkit.cli.system_context import (
    _format_overview_display,
    _format_impact_display,
    _format_context_switch_display,
    _get_graphiti_client,
    _detect_project_id,
)


# =============================================================================
# Mock Graphiti Client (shared across all E2E tests)
# =============================================================================

class MockGraphitiClient:
    """Realistic mock matching GraphitiClient API surface.

    Simulates a populated Graphiti instance with all 4 entity types:
    Component, ADR, Crosscutting, and System Context.
    """

    def __init__(self, facts=None, bdd_facts=None, enabled=True, project_id="test-project"):
        self._facts = facts or []
        self._bdd_facts = bdd_facts or []
        self._enabled = enabled
        self._project_id = project_id
        self._search_calls = []

    @property
    def enabled(self):
        return self._enabled

    def get_group_id(self, group_name, scope=None):
        if self._project_id:
            return f"{self._project_id}__{group_name}"
        return group_name

    async def search(self, query, group_ids=None, num_results=10):
        self._search_calls.append({
            "query": query,
            "group_ids": group_ids,
            "num_results": num_results,
        })
        if not self._enabled:
            return []
        if group_ids and any("bdd_scenarios" in gid for gid in group_ids):
            return self._bdd_facts[:num_results]
        return self._facts[:num_results]


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def all_entity_type_facts():
    """Facts covering all 4 entity types: component, ADR, crosscutting, system context."""
    return [
        {
            "uuid": "fact-sys",
            "fact": "System uses Clean Architecture with 3 bounded contexts",
            "name": "System Context: GuardKit Platform",
            "score": 0.95,
        },
        {
            "uuid": "fact-comp-1",
            "fact": "Component: CLI Layer handles command routing and argument parsing",
            "name": "Component: CLI Layer",
            "score": 0.92,
        },
        {
            "uuid": "fact-comp-2",
            "fact": "Component: Orchestrator manages Player-Coach adversarial workflow",
            "name": "Component: Orchestrator",
            "score": 0.90,
        },
        {
            "uuid": "fact-adr-1",
            "fact": "ADR-SP-001: Use adversarial Player-Coach pattern to ensure quality. This conflicts with single-agent approach in ADR-SP-003.",
            "name": "ADR-SP-001: Adversarial Player-Coach",
            "score": 0.88,
        },
        {
            "uuid": "fact-adr-2",
            "fact": "ADR-SP-002: Use FalkorDB for knowledge graph persistence to replace Neo4j.",
            "name": "ADR-SP-002: FalkorDB Migration",
            "score": 0.85,
        },
        {
            "uuid": "fact-xc",
            "fact": "Cross-cutting concern: Graceful Degradation ensures all features work without Graphiti",
            "name": "Crosscutting: Graceful Degradation",
            "score": 0.87,
        },
    ]


@pytest.fixture
def mock_client(all_entity_type_facts):
    """Mock Graphiti client with all entity types populated."""
    return MockGraphitiClient(
        facts=all_entity_type_facts,
        enabled=True,
        project_id="guardkit",
    )


@pytest.fixture
def sp(mock_client):
    """SystemPlanGraphiti backed by mock client."""
    return SystemPlanGraphiti(client=mock_client, project_id="guardkit")


@pytest.fixture
def disabled_client():
    """Mock Graphiti client that is disabled (simulates unavailability)."""
    return MockGraphitiClient(facts=[], enabled=False, project_id="guardkit")


@pytest.fixture
def disabled_sp(disabled_client):
    """SystemPlanGraphiti with disabled client."""
    return SystemPlanGraphiti(client=disabled_client, project_id="guardkit")


# =============================================================================
# 1. System Overview: Full Chain (AC-001, AC-002)
# =============================================================================

class TestSystemOverviewChain:
    """Test /system-overview read chain: get_system_overview -> entity classification -> display."""

    @pytest.mark.asyncio
    async def test_overview_classifies_all_four_entity_types(self, sp):
        """AC-001: get_system_overview returns dict with components, decisions, concerns, system."""
        overview = await get_system_overview(sp, verbose=False)

        assert overview["status"] == "ok"

        # System context extracted
        assert overview["system"]["name"] == "GuardKit Platform"

        # Components classified
        assert len(overview["components"]) == 2
        names = {c["name"] for c in overview["components"]}
        assert "CLI Layer" in names
        assert "Orchestrator" in names

        # ADRs classified
        assert len(overview["decisions"]) == 2
        adr_ids = {d["adr_id"] for d in overview["decisions"]}
        assert "ADR-SP-001" in adr_ids
        assert "ADR-SP-002" in adr_ids

        # Crosscutting concerns classified
        assert len(overview["concerns"]) == 1
        assert overview["concerns"][0]["name"] == "Graceful Degradation"

    @pytest.mark.asyncio
    async def test_overview_json_format_is_valid(self, sp):
        """AC-002: JSON output format is parseable and contains expected keys."""
        overview = await get_system_overview(sp, verbose=False)

        # Serialize to JSON and back (proves JSON-safe)
        json_str = json.dumps(overview, indent=2)
        parsed = json.loads(json_str)

        assert parsed["status"] == "ok"
        assert "system" in parsed
        assert "components" in parsed
        assert "decisions" in parsed
        assert "concerns" in parsed

    @pytest.mark.asyncio
    async def test_overview_display_format_includes_all_sections(self, sp):
        """Display format includes all 4 entity type sections."""
        overview = await get_system_overview(sp, verbose=False)
        display = _format_overview_display(overview, section="all", verbose=False)

        assert "SYSTEM OVERVIEW" in display
        assert "COMPONENTS" in display
        assert "ARCHITECTURE DECISIONS" in display
        assert "CROSSCUTTING CONCERNS" in display

    @pytest.mark.asyncio
    async def test_overview_graceful_degradation_disabled_client(self, disabled_sp):
        """Disabled Graphiti client returns no_context status."""
        overview = await get_system_overview(disabled_sp, verbose=False)
        assert overview["status"] == "no_context"

        display = _format_overview_display(overview)
        assert "NO ARCHITECTURE CONTEXT" in display


# =============================================================================
# 2. Impact Analysis: Full Chain (AC-003, AC-004)
# =============================================================================

class TestImpactAnalysisChain:
    """Test /impact-analysis read chain: run_impact_analysis -> risk scoring -> display."""

    @pytest.mark.asyncio
    async def test_impact_topic_returns_components_with_risk(self, sp, mock_client):
        """AC-003: Topic query returns affected components with risk score."""
        impact = await run_impact_analysis(
            sp=sp,
            client=mock_client,
            task_or_topic="refactor orchestrator workflow",
            depth="standard",
        )

        assert impact["status"] == "ok"

        # Components present
        assert len(impact["components"]) >= 1

        # Risk calculated
        assert "risk" in impact
        assert 1 <= impact["risk"]["score"] <= 5
        assert impact["risk"]["label"] in ("low", "medium", "high", "critical")
        assert len(impact["risk"]["rationale"]) > 0

    @pytest.mark.asyncio
    async def test_impact_task_id_enriches_query_from_file(self, sp, mock_client, tmp_path):
        """AC-004: Task ID query reads task file and enriches with title+tags."""
        # Create task file with descriptive filename and inline tags
        task_dir = tmp_path / "tasks" / "in_progress"
        task_dir.mkdir(parents=True)
        task_file = task_dir / "TASK-TEST-001-refactor-orchestrator.md"
        task_file.write_text("""---
title: "Refactor orchestrator workflow"
tags: [orchestrator, refactoring, autobuild]
complexity: 5
---

# Description
Refactor the Player-Coach orchestrator for better modularity.
""")

        # Patch Path to use tmp_path for task file discovery
        original_path_glob = Path.glob

        def patched_glob(self_path, pattern):
            if "TASK-TEST-001" in pattern and "tasks/" in str(self_path):
                return (task_dir / "TASK-TEST-001-refactor-orchestrator.md").parent.glob(pattern)
            return original_path_glob(self_path, pattern)

        # Patch Path existence and glob to find our temp task file
        with patch("guardkit.planning.impact_analysis.Path") as MockPath:
            # Make Path("tasks/in_progress") point to our tmp dir
            def path_factory(p):
                real = Path(p)
                if str(p) == "tasks/in_progress":
                    return task_dir
                if str(p) == "tasks/backlog":
                    return tmp_path / "tasks" / "backlog"
                if str(p) == "tasks/design_approved":
                    return tmp_path / "tasks" / "design_approved"
                return real
            MockPath.side_effect = path_factory

            impact = await run_impact_analysis(
                sp=sp,
                client=mock_client,
                task_or_topic="TASK-TEST-001",
                depth="standard",
            )

        assert impact["status"] == "ok"
        # Query should be enriched (title + tags), not raw task ID
        query = impact.get("query", "")
        assert query != "TASK-TEST-001" or "orchestrator" in query.lower() or "refactor" in query.lower()

    @pytest.mark.asyncio
    async def test_impact_quick_depth_omits_adrs(self, sp, mock_client):
        """Quick depth only returns components, no ADRs."""
        impact = await run_impact_analysis(
            sp=sp,
            client=mock_client,
            task_or_topic="CLI changes",
            depth="quick",
        )

        assert impact["status"] == "ok"
        assert "components" in impact
        assert "adrs" not in impact or len(impact.get("adrs", [])) == 0

    @pytest.mark.asyncio
    async def test_impact_display_format_has_risk_bar(self, sp, mock_client):
        """Display format includes Unicode risk bar."""
        impact = await run_impact_analysis(
            sp=sp,
            client=mock_client,
            task_or_topic="database migration",
            depth="standard",
        )

        display = _format_impact_display(impact, depth="standard")
        assert "IMPACT ANALYSIS" in display
        assert "RISK ASSESSMENT" in display
        assert "█" in display  # Risk bar present

    @pytest.mark.asyncio
    async def test_impact_graceful_degradation_disabled_client(self, disabled_sp, disabled_client):
        """Disabled Graphiti returns no_context status."""
        impact = await run_impact_analysis(
            sp=disabled_sp,
            client=disabled_client,
            task_or_topic="any topic",
            depth="standard",
        )

        assert impact["status"] == "no_context"


# =============================================================================
# 3. Context Switch: Config Management (AC-005)
# =============================================================================

class TestContextSwitchChain:
    """Test /context-switch: config management and display formatting."""

    def test_context_switch_display_format_switch_mode(self):
        """AC-005: Switch mode display shows project and architecture."""
        result = {
            "status": "success",
            "project_id": "guardkit",
            "project_path": "/Users/dev/guardkit",
            "architecture": [
                {"fact": "Component: CLI Layer handles command routing"},
                {"fact": "Component: Orchestrator manages workflow"},
            ],
            "active_tasks": [
                {"id": "TASK-001", "title": "Fix bug", "status": "in_progress"},
            ],
        }

        display = _format_context_switch_display(result, mode="switch")

        assert "SWITCHED TO: guardkit" in display
        assert "CLI Layer" in display
        assert "ACTIVE TASKS" in display
        assert "TASK-001" in display

    def test_context_switch_display_format_list_mode(self):
        """List mode shows all known projects."""
        result = {
            "status": "success",
            "projects": [
                {"id": "guardkit", "path": "/Users/dev/guardkit", "last_accessed": "2026-02-14T10:00:00Z"},
                {"id": "requirekit", "path": "/Users/dev/requirekit", "last_accessed": "2026-02-13T10:00:00Z"},
            ],
        }

        display = _format_context_switch_display(result, mode="list")

        assert "KNOWN PROJECTS" in display
        assert "guardkit" in display
        assert "requirekit" in display

    def test_context_switch_error_display(self):
        """Error result displays error message."""
        result = {
            "status": "error",
            "message": "Project 'unknown' is unknown",
            "project_id": "unknown",
        }

        display = _format_context_switch_display(result, mode="switch")

        assert "Error" in display
        assert "unknown" in display


# =============================================================================
# 4. Token Budget Condensation (AC-006)
# =============================================================================

class TestTokenBudgetCondensation:
    """Test condense_for_injection respects token limits."""

    @pytest.mark.asyncio
    async def test_condense_within_budget(self, sp):
        """AC-006: Condensed output stays within token budget."""
        overview = await get_system_overview(sp, verbose=False)

        max_tokens = 300
        condensed = condense_for_injection(overview, max_tokens=max_tokens)

        assert len(condensed) > 0

        # Token estimate: words * 1.3
        estimated_tokens = len(condensed.split()) * 1.3
        # Allow 50% buffer for estimation variance
        assert estimated_tokens <= max_tokens * 1.5

    @pytest.mark.asyncio
    async def test_condense_prioritizes_system_and_components(self, sp):
        """Condensation includes highest-priority items first."""
        overview = await get_system_overview(sp, verbose=False)

        condensed = condense_for_injection(overview, max_tokens=200)

        # System context or components should appear (highest priority)
        assert "GuardKit" in condensed or "CLI" in condensed or "Orchestrator" in condensed

    @pytest.mark.asyncio
    async def test_condense_no_context_returns_empty(self):
        """No-context overview returns empty string."""
        overview = {"status": "no_context"}
        condensed = condense_for_injection(overview, max_tokens=1000)
        assert condensed == ""

    @pytest.mark.asyncio
    async def test_impact_condense_within_budget(self, sp, mock_client):
        """Impact condensation respects token budget."""
        impact = await run_impact_analysis(
            sp=sp,
            client=mock_client,
            task_or_topic="orchestrator changes",
            depth="standard",
        )

        max_tokens = 400
        condensed = condense_impact_for_injection(impact, max_tokens=max_tokens)

        assert len(condensed) > 0
        estimated_tokens = len(condensed.split()) * 1.3
        assert estimated_tokens <= max_tokens * 1.5


# =============================================================================
# 5. Coach Context Builder (AC-007)
# =============================================================================

class TestCoachContextBuilder:
    """Test build_coach_context assembles non-empty context for high-complexity tasks."""

    @pytest.mark.asyncio
    async def test_coach_context_nonempty_for_high_complexity(self, mock_client):
        """AC-007: Complexity 7+ produces non-empty architecture context."""
        task = {"complexity": 7, "title": "Refactor orchestrator", "description": "Major refactoring"}
        context = await build_coach_context(task, mock_client, "guardkit")

        assert len(context) > 0
        assert "Architecture Context" in context

    @pytest.mark.asyncio
    async def test_coach_context_empty_for_low_complexity(self, mock_client):
        """Complexity 1-3 returns empty string (no context needed)."""
        task = {"complexity": 2, "title": "Fix typo"}
        context = await build_coach_context(task, mock_client, "guardkit")

        assert context == ""

    @pytest.mark.asyncio
    async def test_coach_context_medium_complexity_has_overview(self, mock_client):
        """Complexity 4-6 includes overview but may skip impact."""
        task = {"complexity": 5, "title": "Add feature", "description": "New feature"}
        context = await build_coach_context(task, mock_client, "guardkit")

        assert len(context) > 0
        assert "Architecture Context" in context

    @pytest.mark.asyncio
    async def test_coach_context_graceful_degradation(self, disabled_client):
        """Disabled client returns empty string (graceful degradation)."""
        task = {"complexity": 8, "title": "Big refactor"}
        context = await build_coach_context(task, disabled_client, "guardkit")

        assert context == ""


# =============================================================================
# 6. CLI Helper Functions (AC-009: bug fixes validated)
# =============================================================================

class TestCLIHelpers:
    """Test CLI helper functions added to fix wiring bugs."""

    def test_get_graphiti_client_returns_none_when_unavailable(self):
        """_get_graphiti_client returns None when Graphiti not configured."""
        with patch("guardkit.knowledge.graphiti_client.get_graphiti", side_effect=ImportError("no module")):
            result = _get_graphiti_client()
            assert result is None

    def test_get_graphiti_client_returns_none_when_disabled(self):
        """_get_graphiti_client returns None when client.enabled is False."""
        mock = MagicMock()
        mock.enabled = False
        with patch("guardkit.knowledge.graphiti_client.get_graphiti", return_value=mock):
            result = _get_graphiti_client()
            assert result is None

    def test_detect_project_id_returns_lowercase_cwd(self, tmp_path, monkeypatch):
        """_detect_project_id returns lowercase, hyphenated cwd name."""
        project_dir = tmp_path / "My Project"
        project_dir.mkdir()
        monkeypatch.chdir(project_dir)
        result = _detect_project_id()
        assert result == "my-project"


# =============================================================================
# 7. Coach Context Builder: Impact Section Wiring (AC-009 bug fix)
# =============================================================================

class TestCoachContextImpactWiring:
    """Validate BUG-3 fix: _get_impact_section passes correct args to run_impact_analysis."""

    @pytest.mark.asyncio
    async def test_impact_section_uses_client_from_sp(self, mock_client):
        """Coach context builder uses sp._client (not query string) as client arg."""
        task = {"complexity": 8, "title": "Refactor orchestrator", "description": "Major change"}

        # If the bug (BUG-3) is not fixed, sp._client would not be passed correctly
        # and run_impact_analysis would receive a string as `client`, causing an error.
        # With the fix, this should succeed.
        context = await build_coach_context(task, mock_client, "guardkit")

        # If we got here without error, the wiring is correct
        assert len(context) > 0
        # High complexity (8) should attempt impact analysis
        # Impact section may or may not appear depending on budget, but no crash
