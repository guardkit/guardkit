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
