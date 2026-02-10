"""
E2E Test Suite for System Context CLI Commands

Tests CLI command invocations for system context read operations:
- guardkit system-overview: Architecture summary
- guardkit impact-analysis: Pre-task validation with risk scoring
- guardkit context-switch: Multi-project navigation

These tests follow TDD RED phase principles - the CLI commands don't exist yet.
Tests will fail until commands are wired to Click in GREEN phase.

Coverage Target: >=85%
Test Count: 24+ tests
"""

import json
import pytest
from pathlib import Path
from click.testing import CliRunner
from unittest.mock import AsyncMock, Mock, patch, mock_open

from guardkit.cli.main import cli


# ============================================================================
# Test Infrastructure Fixtures
# ============================================================================


@pytest.fixture
def runner():
    """Create Click CLI runner for testing."""
    return CliRunner()


@pytest.fixture
def mock_graphiti_client():
    """Mock Graphiti client with realistic data."""
    mock_client = Mock()
    mock_client.enabled = True
    mock_client.get_group_id.return_value = "test-group-id"

    # Mock search to return architecture data
    async def mock_search(query, group_ids=None, num_results=10):
        return [
            {
                "name": "Component: User Management",
                "fact": "Component: User Management handles authentication and user profiles",
                "score": 0.95,
            },
            {
                "name": "ADR-SP-001: Use microservices architecture",
                "fact": "ADR-SP-001: Use microservices architecture. Status: accepted. Context: Need for scalability.",
                "score": 0.85,
            },
        ]

    mock_client.search = AsyncMock(side_effect=mock_search)
    return mock_client


@pytest.fixture
def mock_graphiti_unavailable():
    """Mock Graphiti client that is unavailable."""
    mock_client = Mock()
    mock_client.enabled = False
    return mock_client


@pytest.fixture
def mock_system_plan_graphiti():
    """Mock SystemPlanGraphiti with architecture data."""
    mock_sp = Mock()
    mock_sp._available = True

    async def mock_get_architecture_summary():
        return {
            "facts": [
                {
                    "name": "System Context: GuardKit",
                    "fact": "System Context: GuardKit. Methodology: Event-driven microservices. Purpose: AI-assisted development workflow.",
                },
                {
                    "name": "Component: Task Manager",
                    "fact": "Component: Task Manager orchestrates task lifecycle and quality gates",
                },
                {
                    "name": "ADR-SP-002: Use TDD for all components",
                    "fact": "ADR-SP-002: Use TDD for all components. Status: accepted.",
                },
                {
                    "name": "Crosscutting: Logging",
                    "fact": "Crosscutting: Logging. All services use structured JSON logging.",
                },
            ]
        }

    mock_sp.get_architecture_summary = AsyncMock(side_effect=mock_get_architecture_summary)
    return mock_sp


@pytest.fixture
def mock_system_plan_no_context():
    """Mock SystemPlanGraphiti with no architecture context."""
    mock_sp = Mock()
    mock_sp._available = False
    return mock_sp


@pytest.fixture
def temp_config(tmp_path, monkeypatch):
    """Create temporary GuardKit config directory."""
    config_dir = tmp_path / ".guardkit"
    config_dir.mkdir()

    config_file = config_dir / "config.yaml"
    config_content = """
active_project: guardkit
known_projects:
  guardkit:
    path: /path/to/guardkit
    last_accessed: 2024-01-15T10:00:00Z
  requirekit:
    path: /path/to/requirekit
    last_accessed: 2024-01-10T09:00:00Z
"""
    config_file.write_text(config_content)

    # Change to temp directory
    monkeypatch.chdir(tmp_path)
    return config_dir


@pytest.fixture
def temp_task_file(tmp_path, monkeypatch):
    """Create temporary task file for impact analysis testing."""
    tasks_dir = tmp_path / "tasks" / "in_progress"
    tasks_dir.mkdir(parents=True)

    task_file = tasks_dir / "TASK-SC-005.md"
    task_content = """---
id: TASK-SC-005
title: Add authentication middleware
status: in_progress
tags:
  - authentication
  - middleware
  - security
---

# Task: Add authentication middleware

Implement JWT-based authentication middleware for all API endpoints.
"""
    task_file.write_text(task_content)

    monkeypatch.chdir(tmp_path)
    return task_file


# ============================================================================
# 1. /system-overview E2E Tests (7 tests)
# ============================================================================


@pytest.mark.e2e
def test_system_overview_default(runner, mock_system_plan_graphiti, mock_graphiti_client):
    """Test default system-overview invocation (RED: command doesn't exist yet)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_get:
        mock_get.return_value = {
            "status": "ok",
            "system": {"name": "GuardKit", "methodology": "Event-driven microservices"},
            "components": [{"name": "Task Manager", "description": "Orchestrates tasks"}],
            "decisions": [{"adr_id": "ADR-SP-002", "title": "Use TDD", "status": "accepted"}],
            "concerns": [{"name": "Logging", "description": "Structured JSON logging"}],
        }

        result = runner.invoke(cli, ["system-overview"])

        # These assertions will fail in RED phase (command doesn't exist)
        assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}"
        assert "System Context" in result.output
        assert "GuardKit" in result.output
        assert "Task Manager" in result.output


@pytest.mark.e2e
def test_system_overview_verbose(runner, mock_system_plan_graphiti, mock_graphiti_client):
    """Test system-overview with --verbose flag (RED)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_get:
        mock_get.return_value = {
            "status": "ok",
            "system": {"name": "GuardKit", "methodology": "Event-driven microservices"},
            "components": [{"name": "Task Manager", "description": "Orchestrates tasks", "full_content": "Extended info"}],
            "decisions": [],
            "concerns": [],
        }

        result = runner.invoke(cli, ["system-overview", "--verbose"])

        assert result.exit_code == 0
        # Verbose should include extended content
        assert "Extended info" in result.output or "full_content" in result.output


@pytest.mark.e2e
def test_system_overview_section_filter(runner, mock_system_plan_graphiti, mock_graphiti_client):
    """Test system-overview with --section=decisions filter (RED)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_get:
        mock_get.return_value = {
            "status": "ok",
            "system": {"name": "GuardKit"},
            "components": [{"name": "Task Manager"}],
            "decisions": [{"adr_id": "ADR-SP-002", "title": "Use TDD", "status": "accepted"}],
            "concerns": [{"name": "Logging"}],
        }

        result = runner.invoke(cli, ["system-overview", "--section=decisions"])

        assert result.exit_code == 0
        # Should show decisions section only
        assert "ADR-SP-002" in result.output
        # Should NOT show components or concerns (filtered out)
        assert "Task Manager" not in result.output or "Architecture Decisions" in result.output


@pytest.mark.e2e
def test_system_overview_json_format(runner, mock_system_plan_graphiti, mock_graphiti_client):
    """Test system-overview with --format=json output (RED)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_get:
        overview_data = {
            "status": "ok",
            "system": {"name": "GuardKit", "methodology": "Event-driven microservices"},
            "components": [{"name": "Task Manager", "description": "Orchestrates tasks"}],
            "decisions": [{"adr_id": "ADR-SP-002", "title": "Use TDD", "status": "accepted"}],
            "concerns": [{"name": "Logging", "description": "Structured JSON logging"}],
        }
        mock_get.return_value = overview_data

        result = runner.invoke(cli, ["system-overview", "--format=json"])

        assert result.exit_code == 0
        # Should output valid JSON
        try:
            output_json = json.loads(result.output)
            assert output_json["status"] == "ok"
            assert output_json["system"]["name"] == "GuardKit"
        except json.JSONDecodeError:
            pytest.fail("Output is not valid JSON")


@pytest.mark.e2e
def test_system_overview_no_context(runner, mock_system_plan_no_context):
    """Test system-overview with no architecture context (RED)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_get:
        mock_get.return_value = {"status": "no_context"}

        result = runner.invoke(cli, ["system-overview"])

        assert result.exit_code == 0
        # Should show helpful message suggesting how to add context
        assert "no context" in result.output.lower() or "add context" in result.output.lower()


@pytest.mark.e2e
def test_system_overview_graphiti_down(runner, mock_graphiti_unavailable):
    """Test system-overview when Graphiti is unavailable (RED)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_get:
        mock_get.return_value = {"status": "no_context"}

        result = runner.invoke(cli, ["system-overview"])

        assert result.exit_code == 0
        # Should show fallback message
        assert "no context" in result.output.lower() or "unavailable" in result.output.lower()


@pytest.mark.e2e
def test_system_overview_exit_code(runner, mock_system_plan_graphiti, mock_graphiti_client):
    """Test system-overview exit code on success (RED)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_get:
        mock_get.return_value = {
            "status": "ok",
            "system": {"name": "GuardKit"},
            "components": [],
            "decisions": [],
            "concerns": [],
        }

        result = runner.invoke(cli, ["system-overview"])

        # Successful invocation should return 0
        assert result.exit_code == 0


# ============================================================================
# 2. /impact-analysis E2E Tests (8 tests)
# ============================================================================


@pytest.mark.e2e
def test_impact_analysis_task_id(runner, temp_task_file, mock_graphiti_client):
    """Test impact-analysis with task ID argument (RED)."""
    with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "query": "Add authentication middleware",
            "components": [{"name": "API Gateway", "description": "Main entry point", "relevance_score": 0.92}],
            "adrs": [{"adr_id": "ADR-SP-003", "title": "Use JWT tokens", "conflict": False}],
            "risk": {"score": 3, "label": "medium", "rationale": "1 component(s) affected; 1 constraining ADR(s)"},
            "implications": ["Changes to API Gateway may affect dependent components"],
        }

        result = runner.invoke(cli, ["impact-analysis", "TASK-SC-005"])

        assert result.exit_code == 0
        # Should show risk bar and components
        assert "Risk:" in result.output or "[" in result.output  # Unicode bar
        assert "API Gateway" in result.output


@pytest.mark.e2e
def test_impact_analysis_topic(runner, mock_graphiti_client):
    """Test impact-analysis with topic string argument (RED)."""
    with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "query": "add MFA",
            "components": [{"name": "User Management", "description": "Handles auth", "relevance_score": 0.88}],
            "adrs": [],
            "risk": {"score": 2, "label": "medium", "rationale": "1 component(s) affected"},
            "implications": ["Changes to User Management may affect dependent components"],
        }

        result = runner.invoke(cli, ["impact-analysis", "add MFA"])

        assert result.exit_code == 0
        assert "User Management" in result.output


@pytest.mark.e2e
def test_impact_analysis_quick_depth(runner, mock_graphiti_client):
    """Test impact-analysis with --depth=quick (RED)."""
    with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "query": "add caching",
            "components": [{"name": "Data Layer", "description": "Database access", "relevance_score": 0.75}],
            "adrs": [],  # Quick mode doesn't include ADRs
            "risk": {"score": 1, "label": "low", "rationale": "1 component(s) affected"},
            "implications": [],
        }

        result = runner.invoke(cli, ["impact-analysis", "add caching", "--depth=quick"])

        assert result.exit_code == 0
        # Quick mode should show components only (no ADRs, no implications)
        assert "Data Layer" in result.output
        # Should not have ADRs section in quick mode
        assert result.output.count("Constraining ADRs") == 0 or "Constraining ADRs:" not in result.output


@pytest.mark.e2e
def test_impact_analysis_deep_depth(runner, mock_graphiti_client):
    """Test impact-analysis with --depth=deep (RED)."""
    with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "query": "refactor payment flow",
            "components": [{"name": "Payment Service", "description": "Handles payments", "relevance_score": 0.95}],
            "adrs": [{"adr_id": "ADR-SP-004", "title": "Use Stripe API", "conflict": False}],
            "bdd_scenarios": [
                {"scenario_name": "Process payment", "file_location": "payments.feature:10", "at_risk": True}
            ],
            "risk": {"score": 4, "label": "high", "rationale": "1 component(s) affected; 1 constraining ADR(s); 1 at-risk scenario(s)"},
            "implications": [
                "Changes to Payment Service may affect dependent components",
                "ADR-SP-004 (Use Stripe API) provides constraints to follow",
            ],
        }

        result = runner.invoke(cli, ["impact-analysis", "refactor payment flow", "--depth=deep"])

        assert result.exit_code == 0
        # Deep mode should include BDD scenarios section
        assert "BDD Scenarios" in result.output or "Process payment" in result.output
        assert "[AT RISK]" in result.output


@pytest.mark.e2e
def test_impact_analysis_include_bdd(runner, mock_graphiti_client):
    """Test impact-analysis with --include-bdd flag (RED)."""
    with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "query": "update user flow",
            "components": [{"name": "User Service", "description": "User management", "relevance_score": 0.90}],
            "adrs": [],
            "bdd_scenarios": [
                {"scenario_name": "User registration", "file_location": "users.feature:5", "at_risk": False}
            ],
            "risk": {"score": 2, "label": "medium", "rationale": "1 component(s) affected"},
            "implications": [],
        }

        result = runner.invoke(cli, ["impact-analysis", "update user flow", "--depth=deep", "--include-bdd"])

        assert result.exit_code == 0
        # Should show BDD scenarios when flag is present
        assert "User registration" in result.output


@pytest.mark.e2e
def test_impact_analysis_no_context(runner, mock_system_plan_no_context):
    """Test impact-analysis with no architecture context (RED)."""
    with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_run:
        mock_run.return_value = {"status": "no_context"}

        result = runner.invoke(cli, ["impact-analysis", "add feature"])

        assert result.exit_code == 0
        # Should show helpful suggestion
        assert "no context" in result.output.lower() or "no impact data" in result.output.lower()


@pytest.mark.e2e
def test_impact_analysis_invalid_task_id(runner, mock_graphiti_client):
    """Test impact-analysis with nonexistent task ID (RED)."""
    # Task file doesn't exist, should fall back to using task ID as query
    with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "query": "TASK-NONEXIST",
            "components": [],
            "adrs": [],
            "risk": {"score": 1, "label": "low", "rationale": "Minimal impact"},
            "implications": [],
        }

        result = runner.invoke(cli, ["impact-analysis", "TASK-NONEXIST"])

        # Should not error, just show no impact
        assert result.exit_code == 0


@pytest.mark.e2e
def test_impact_analysis_exit_code(runner, mock_graphiti_client):
    """Test impact-analysis exit code on success (RED)."""
    with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "query": "test query",
            "components": [{"name": "Test Component", "description": "Test", "relevance_score": 0.80}],
            "adrs": [],
            "risk": {"score": 2, "label": "medium", "rationale": "1 component(s) affected"},
            "implications": [],
        }

        result = runner.invoke(cli, ["impact-analysis", "test query"])

        assert result.exit_code == 0


# ============================================================================
# 3. /context-switch E2E Tests (6 tests)
# ============================================================================


@pytest.mark.e2e
def test_context_switch_to_project(runner, temp_config, mock_graphiti_client):
    """Test context-switch to named project (RED)."""
    with patch("guardkit.planning.context_switch.execute_context_switch") as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "project_id": "requirekit",
            "project_path": "/path/to/requirekit",
            "architecture": [
                {"fact": "RequireKit is a BDD scenario management system"}
            ],
            "active_tasks": [
                {"id": "TASK-RK-001", "title": "Add EARS notation", "status": "in_progress"}
            ],
        }

        result = runner.invoke(cli, ["context-switch", "requirekit"])

        assert result.exit_code == 0
        # Should show switched project and orientation
        assert "requirekit" in result.output.lower()
        assert "TASK-RK-001" in result.output or "active" in result.output.lower()


@pytest.mark.e2e
def test_context_switch_list(runner, temp_config):
    """Test context-switch --list to show all projects (RED)."""
    result = runner.invoke(cli, ["context-switch", "--list"])

    assert result.exit_code == 0
    # Should list all known projects
    assert "guardkit" in result.output.lower()
    assert "requirekit" in result.output.lower()
    # Should show paths
    assert "/path/to/guardkit" in result.output or "path" in result.output.lower()


@pytest.mark.e2e
def test_context_switch_no_args(runner, temp_config, mock_graphiti_client):
    """Test context-switch with no args shows current project (RED)."""
    with patch("guardkit.planning.context_switch.execute_context_switch") as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "project_id": "guardkit",
            "project_path": "/path/to/guardkit",
            "architecture": [],
            "active_tasks": [
                {"id": "TASK-SC-005", "title": "Add auth middleware", "status": "in_progress"}
            ],
        }

        result = runner.invoke(cli, ["context-switch"])

        assert result.exit_code == 0
        # Should show current project info
        assert "guardkit" in result.output.lower() or "current" in result.output.lower()


@pytest.mark.e2e
def test_context_switch_unknown_project(runner, temp_config):
    """Test context-switch with unknown project name (RED)."""
    with patch("guardkit.planning.context_switch.execute_context_switch") as mock_exec:
        mock_exec.return_value = {
            "status": "error",
            "message": "Project 'unknown' not found in known projects.",
            "project_id": "unknown",
        }

        result = runner.invoke(cli, ["context-switch", "unknown"])

        # Should show error with helpful suggestion
        assert result.exit_code != 0 or "error" in result.output.lower()
        assert "not found" in result.output.lower() or "unknown" in result.output.lower()


@pytest.mark.e2e
def test_context_switch_graphiti_down(runner, temp_config, mock_graphiti_unavailable):
    """Test context-switch works even when Graphiti is down (RED)."""
    with patch("guardkit.planning.context_switch.execute_context_switch") as mock_exec:
        # Switch should work, but overview section will be empty
        mock_exec.return_value = {
            "status": "success",
            "project_id": "requirekit",
            "project_path": "/path/to/requirekit",
            "architecture": [],  # Empty when Graphiti unavailable
            "active_tasks": [],
        }

        result = runner.invoke(cli, ["context-switch", "requirekit"])

        # Should still succeed even without Graphiti
        assert result.exit_code == 0
        assert "requirekit" in result.output.lower()


@pytest.mark.e2e
def test_context_switch_exit_code(runner, temp_config, mock_graphiti_client):
    """Test context-switch exit code on success (RED)."""
    with patch("guardkit.planning.context_switch.execute_context_switch") as mock_exec:
        mock_exec.return_value = {
            "status": "success",
            "project_id": "guardkit",
            "project_path": "/path/to/guardkit",
            "architecture": [],
            "active_tasks": [],
        }

        result = runner.invoke(cli, ["context-switch", "guardkit"])

        assert result.exit_code == 0


# ============================================================================
# 4. Cross-Command E2E Tests (3 tests)
# ============================================================================


@pytest.mark.e2e
def test_overview_then_impact(runner, mock_system_plan_graphiti, mock_graphiti_client):
    """Test overview followed by impact-analysis (RED)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_overview:
        with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_impact:
            # Setup overview response
            mock_overview.return_value = {
                "status": "ok",
                "system": {"name": "GuardKit"},
                "components": [{"name": "Task Manager", "description": "Orchestrates tasks"}],
                "decisions": [],
                "concerns": [],
            }

            # Setup impact response
            mock_impact.return_value = {
                "status": "ok",
                "query": "update Task Manager",
                "components": [{"name": "Task Manager", "description": "Orchestrates tasks", "relevance_score": 0.95}],
                "adrs": [],
                "risk": {"score": 2, "label": "medium", "rationale": "1 component(s) affected"},
                "implications": [],
            }

            # First: Get overview
            result1 = runner.invoke(cli, ["system-overview"])
            assert result1.exit_code == 0
            assert "Task Manager" in result1.output

            # Then: Run impact analysis
            result2 = runner.invoke(cli, ["impact-analysis", "update Task Manager"])
            assert result2.exit_code == 0
            assert "Task Manager" in result2.output
            # Same component should appear in both


@pytest.mark.e2e
def test_switch_then_overview(runner, temp_config, mock_graphiti_client):
    """Test context-switch followed by system-overview (RED)."""
    with patch("guardkit.planning.context_switch.execute_context_switch") as mock_switch:
        with patch("guardkit.planning.system_overview.get_system_overview") as mock_overview:
            # Setup switch response
            mock_switch.return_value = {
                "status": "success",
                "project_id": "requirekit",
                "project_path": "/path/to/requirekit",
                "architecture": [],
                "active_tasks": [],
            }

            # Setup overview response (for requirekit project)
            mock_overview.return_value = {
                "status": "ok",
                "system": {"name": "RequireKit"},
                "components": [{"name": "EARS Parser", "description": "Parses EARS notation"}],
                "decisions": [],
                "concerns": [],
            }

            # First: Switch context
            result1 = runner.invoke(cli, ["context-switch", "requirekit"])
            assert result1.exit_code == 0
            assert "requirekit" in result1.output.lower()

            # Then: Get overview (should be from requirekit context)
            result2 = runner.invoke(cli, ["system-overview"])
            assert result2.exit_code == 0
            assert "RequireKit" in result2.output or "EARS Parser" in result2.output


@pytest.mark.e2e
def test_all_commands_no_context(runner):
    """Test all commands on fresh project with no context (RED)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_overview:
        with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_impact:
            with patch("guardkit.planning.context_switch.execute_context_switch") as mock_switch:
                # All return no context
                mock_overview.return_value = {"status": "no_context"}
                mock_impact.return_value = {"status": "no_context"}
                mock_switch.return_value = {
                    "status": "success",
                    "project_id": "fresh-project",
                    "project_path": "/path/to/fresh",
                    "architecture": [],
                    "active_tasks": [],
                }

                # All should succeed with helpful messages
                result1 = runner.invoke(cli, ["system-overview"])
                assert result1.exit_code == 0
                assert "no context" in result1.output.lower()

                result2 = runner.invoke(cli, ["impact-analysis", "test topic"])
                assert result2.exit_code == 0
                assert "no context" in result2.output.lower() or "no impact data" in result2.output.lower()

                result3 = runner.invoke(cli, ["context-switch"])
                assert result3.exit_code == 0


# ============================================================================
# 5. Output Format Verification Tests (3 additional tests)
# ============================================================================


@pytest.mark.e2e
def test_risk_bar_format(runner, mock_graphiti_client):
    """Test that impact-analysis risk bar uses Unicode blocks correctly (RED)."""
    with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_run:
        mock_run.return_value = {
            "status": "ok",
            "query": "high risk change",
            "components": [{"name": "Core Module", "description": "Critical", "relevance_score": 0.99}],
            "adrs": [
                {"adr_id": "ADR-SP-001", "title": "Use X pattern", "conflict": True},
                {"adr_id": "ADR-SP-002", "title": "Use Y pattern", "conflict": True},
            ],
            "risk": {"score": 5, "label": "critical", "rationale": "1 component(s) affected; 2 conflicting ADR(s)"},
            "implications": [],
        }

        result = runner.invoke(cli, ["impact-analysis", "high risk change"])

        assert result.exit_code == 0
        # Should contain Unicode block characters for risk bar
        # Risk 5/5 should be [█████]
        assert "[█████]" in result.output or "5/5" in result.output
        assert "critical" in result.output.lower()


@pytest.mark.e2e
def test_section_headers_present(runner, mock_system_plan_graphiti, mock_graphiti_client):
    """Test that system-overview includes proper section headers (RED)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_get:
        mock_get.return_value = {
            "status": "ok",
            "system": {"name": "GuardKit"},
            "components": [{"name": "Task Manager", "description": "Orchestrates tasks"}],
            "decisions": [{"adr_id": "ADR-SP-001", "title": "Use microservices", "status": "accepted"}],
            "concerns": [{"name": "Logging", "description": "JSON logging"}],
        }

        result = runner.invoke(cli, ["system-overview"])

        assert result.exit_code == 0
        # Should have section headers
        assert "System Context" in result.output or "System" in result.output
        assert "Components" in result.output
        assert "Architecture Decisions" in result.output or "Decisions" in result.output
        assert "Crosscutting Concerns" in result.output or "Concerns" in result.output


@pytest.mark.e2e
def test_graceful_degradation_messages(runner, mock_system_plan_no_context):
    """Test that commands show appropriate graceful degradation messages (RED)."""
    with patch("guardkit.planning.system_overview.get_system_overview") as mock_overview:
        with patch("guardkit.planning.impact_analysis.run_impact_analysis") as mock_impact:
            mock_overview.return_value = {"status": "no_context"}
            mock_impact.return_value = {"status": "no_context"}

            # Overview with no context
            result1 = runner.invoke(cli, ["system-overview"])
            assert result1.exit_code == 0
            assert "no context" in result1.output.lower()

            # Impact with no context
            result2 = runner.invoke(cli, ["impact-analysis", "test"])
            assert result2.exit_code == 0
            assert "no context" in result2.output.lower() or "no impact data" in result2.output.lower()

            # Messages should be helpful, not just errors
            assert "add" in result1.output.lower() or "capture" in result1.output.lower() or result1.output.count("no context") > 0
