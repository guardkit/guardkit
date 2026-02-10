"""Unit tests for guardkit.planning.context_switch module.

TDD RED phase: Tests written before implementation.
These tests define the expected behavior of the context_switch module.
"""

import pytest
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch
import tempfile
import yaml


# ============================================================================
# Test GuardKitConfig class
# ============================================================================

class TestGuardKitConfigLoad:
    """Tests for GuardKitConfig._load() and initialization."""

    def test_load_config_from_yaml(self, tmp_path: Path):
        """Test loading a valid config file."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_data = {
            "active_project": "my-project",
            "known_projects": {
                "my-project": {
                    "path": "/path/to/my-project",
                    "last_accessed": "2025-01-15T10:30:00Z"
                },
                "other-project": {
                    "path": "/path/to/other-project",
                    "last_accessed": "2025-01-10T08:00:00Z"
                }
            }
        }

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)

        assert config.active_project is not None
        assert config.active_project["path"] == "/path/to/my-project"

    def test_load_config_missing_file(self, tmp_path: Path):
        """Test graceful handling when config file doesn't exist."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_file = tmp_path / ".guardkit" / "config.yaml"
        # File doesn't exist

        config = GuardKitConfig(config_path=config_file)

        # Should return empty/None gracefully
        assert config.active_project is None
        assert config.list_known_projects() == []

    def test_load_config_invalid_yaml(self, tmp_path: Path):
        """Test handling of invalid YAML content."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: [")

        config = GuardKitConfig(config_path=config_file)

        # Should handle gracefully
        assert config.active_project is None


class TestGuardKitConfigActiveProject:
    """Tests for active_project property."""

    def test_active_project_returns_project_dict(self, tmp_path: Path):
        """Test that active_project returns the full project dict."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_data = {
            "active_project": "test-proj",
            "known_projects": {
                "test-proj": {
                    "path": "/home/user/test-proj",
                    "last_accessed": "2025-02-01T12:00:00Z",
                    "description": "Test project"
                }
            }
        }

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)

        active = config.active_project
        assert active is not None
        assert active["path"] == "/home/user/test-proj"
        assert "last_accessed" in active

    def test_active_project_none_when_not_set(self, tmp_path: Path):
        """Test that active_project is None when not configured."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_data = {
            "known_projects": {
                "test-proj": {"path": "/home/user/test-proj"}
            }
        }

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)

        assert config.active_project is None


class TestGuardKitConfigGetKnownProject:
    """Tests for get_known_project() method."""

    def test_get_known_project_returns_project(self, tmp_path: Path):
        """Test retrieving an existing project by ID."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_data = {
            "known_projects": {
                "proj-a": {"path": "/path/a", "last_accessed": "2025-01-01T00:00:00Z"},
                "proj-b": {"path": "/path/b", "last_accessed": "2025-01-02T00:00:00Z"}
            }
        }

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)

        project = config.get_known_project("proj-a")
        assert project is not None
        assert project["path"] == "/path/a"

    def test_get_known_project_returns_none_for_unknown(self, tmp_path: Path):
        """Test that unknown project ID returns None."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_data = {
            "known_projects": {
                "proj-a": {"path": "/path/a"}
            }
        }

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)

        project = config.get_known_project("unknown-proj")
        assert project is None


class TestGuardKitConfigSetActiveProject:
    """Tests for set_active_project() method."""

    def test_switch_to_known_project(self, tmp_path: Path):
        """Test switching to a known project updates active_project."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_data = {
            "active_project": "proj-a",
            "known_projects": {
                "proj-a": {"path": "/path/a", "last_accessed": "2025-01-01T00:00:00Z"},
                "proj-b": {"path": "/path/b", "last_accessed": "2025-01-02T00:00:00Z"}
            }
        }

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)
        config.set_active_project("proj-b")

        assert config.active_project["path"] == "/path/b"

        # Verify it's persisted
        with open(config_file) as f:
            saved = yaml.safe_load(f)
        assert saved["active_project"] == "proj-b"

    def test_switch_to_unknown_project_raises(self, tmp_path: Path):
        """Test that switching to unknown project raises ValueError."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_data = {
            "active_project": "proj-a",
            "known_projects": {
                "proj-a": {"path": "/path/a"}
            }
        }

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)

        with pytest.raises(ValueError, match="unknown"):
            config.set_active_project("unknown-proj")

    def test_switch_updates_last_accessed(self, tmp_path: Path):
        """Test that switching updates the last_accessed timestamp."""
        from guardkit.planning.context_switch import GuardKitConfig

        old_timestamp = "2025-01-01T00:00:00Z"
        config_data = {
            "active_project": "proj-a",
            "known_projects": {
                "proj-a": {"path": "/path/a", "last_accessed": old_timestamp},
                "proj-b": {"path": "/path/b", "last_accessed": old_timestamp}
            }
        }

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)
        config.set_active_project("proj-b")

        # Verify timestamp was updated
        with open(config_file) as f:
            saved = yaml.safe_load(f)

        new_timestamp = saved["known_projects"]["proj-b"]["last_accessed"]
        assert new_timestamp != old_timestamp


class TestGuardKitConfigListKnownProjects:
    """Tests for list_known_projects() method."""

    def test_list_known_projects(self, tmp_path: Path):
        """Test listing all known projects."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_data = {
            "known_projects": {
                "proj-a": {"path": "/path/a"},
                "proj-b": {"path": "/path/b"},
                "proj-c": {"path": "/path/c"}
            }
        }

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)
        projects = config.list_known_projects()

        assert len(projects) == 3
        project_ids = [p["id"] for p in projects]
        assert "proj-a" in project_ids
        assert "proj-b" in project_ids
        assert "proj-c" in project_ids

    def test_list_known_projects_empty(self, tmp_path: Path):
        """Test listing projects when none configured."""
        from guardkit.planning.context_switch import GuardKitConfig

        config_file = tmp_path / ".guardkit" / "config.yaml"
        # File doesn't exist

        config = GuardKitConfig(config_path=config_file)
        projects = config.list_known_projects()

        assert projects == []


# ============================================================================
# Test _find_active_tasks function
# ============================================================================

class TestFindActiveTasks:
    """Tests for _find_active_tasks() function."""

    def test_find_active_tasks(self, tmp_path: Path):
        """Test finding tasks from task directories."""
        from guardkit.planning.context_switch import _find_active_tasks

        # Create task directories
        in_progress = tmp_path / "tasks" / "in_progress"
        backlog = tmp_path / "tasks" / "backlog"
        in_progress.mkdir(parents=True)
        backlog.mkdir(parents=True)

        # Create task files with frontmatter
        task1 = in_progress / "TASK-001.md"
        task1.write_text("""---
id: TASK-001
title: Implement feature A
status: in_progress
---

# Task description
""")

        task2 = backlog / "TASK-002.md"
        task2.write_text("""---
id: TASK-002
title: Fix bug B
status: backlog
---

# Task description
""")

        tasks = _find_active_tasks(str(tmp_path))

        assert len(tasks) == 2
        # in_progress should come first
        assert tasks[0]["id"] == "TASK-001"
        assert tasks[0]["status"] == "in_progress"
        assert tasks[1]["id"] == "TASK-002"

    def test_find_active_tasks_no_path(self):
        """Test that None path returns empty list."""
        from guardkit.planning.context_switch import _find_active_tasks

        tasks = _find_active_tasks(None)

        assert tasks == []

    def test_find_active_tasks_nonexistent_path(self):
        """Test that nonexistent path returns empty list."""
        from guardkit.planning.context_switch import _find_active_tasks

        tasks = _find_active_tasks("/nonexistent/path")

        assert tasks == []

    def test_find_active_tasks_empty_directories(self, tmp_path: Path):
        """Test with existing but empty task directories."""
        from guardkit.planning.context_switch import _find_active_tasks

        # Create empty directories
        (tmp_path / "tasks" / "in_progress").mkdir(parents=True)
        (tmp_path / "tasks" / "backlog").mkdir(parents=True)

        tasks = _find_active_tasks(str(tmp_path))

        assert tasks == []


# ============================================================================
# Test execute_context_switch function
# ============================================================================

class TestExecuteContextSwitch:
    """Tests for execute_context_switch() async function."""

    @pytest.mark.asyncio
    async def test_switch_to_known_project_success(self, tmp_path: Path):
        """Test successful switch to a known project."""
        from guardkit.planning.context_switch import execute_context_switch, GuardKitConfig

        config_data = {
            "active_project": "proj-a",
            "known_projects": {
                "proj-a": {"path": str(tmp_path / "proj-a")},
                "proj-b": {"path": str(tmp_path / "proj-b")}
            }
        }

        # Create project directories
        (tmp_path / "proj-a").mkdir()
        (tmp_path / "proj-b").mkdir()

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)

        # Mock Graphiti client
        mock_client = MagicMock()
        mock_client.enabled = True
        mock_client.search = AsyncMock(return_value=[])

        result = await execute_context_switch(
            client=mock_client,
            target_project="proj-b",
            config=config
        )

        assert result["status"] == "success"
        assert result["project_id"] == "proj-b"

    @pytest.mark.asyncio
    async def test_switch_to_unknown_project_error(self, tmp_path: Path):
        """Test error when switching to unknown project."""
        from guardkit.planning.context_switch import execute_context_switch, GuardKitConfig

        config_data = {
            "active_project": "proj-a",
            "known_projects": {
                "proj-a": {"path": str(tmp_path / "proj-a")}
            }
        }

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)

        result = await execute_context_switch(
            client=None,
            target_project="unknown-proj",
            config=config
        )

        assert result["status"] == "error"
        assert "unknown" in result["message"].lower() or "not found" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_context_switch_graphiti_unavailable(self, tmp_path: Path):
        """Test graceful degradation when Graphiti is unavailable."""
        from guardkit.planning.context_switch import execute_context_switch, GuardKitConfig

        config_data = {
            "active_project": "proj-a",
            "known_projects": {
                "proj-a": {"path": str(tmp_path / "proj-a")},
                "proj-b": {"path": str(tmp_path / "proj-b")}
            }
        }

        (tmp_path / "proj-a").mkdir()
        (tmp_path / "proj-b").mkdir()

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)

        # Pass None for client (Graphiti unavailable)
        result = await execute_context_switch(
            client=None,
            target_project="proj-b",
            config=config
        )

        # Should still succeed, just without architecture info
        assert result["status"] == "success"
        assert result["project_id"] == "proj-b"
        # Architecture should be empty or indicate unavailable
        assert result.get("architecture") is None or result.get("architecture") == []

    @pytest.mark.asyncio
    async def test_execute_context_switch_with_active_tasks(self, tmp_path: Path):
        """Test that switch includes active tasks in result."""
        from guardkit.planning.context_switch import execute_context_switch, GuardKitConfig

        proj_path = tmp_path / "proj-b"
        proj_path.mkdir()

        # Create task directory with tasks
        in_progress = proj_path / "tasks" / "in_progress"
        in_progress.mkdir(parents=True)

        task1 = in_progress / "TASK-001.md"
        task1.write_text("""---
id: TASK-001
title: Current work
status: in_progress
---
""")

        config_data = {
            "active_project": "proj-a",
            "known_projects": {
                "proj-a": {"path": str(tmp_path / "proj-a")},
                "proj-b": {"path": str(proj_path)}
            }
        }

        (tmp_path / "proj-a").mkdir()

        config_file = tmp_path / ".guardkit" / "config.yaml"
        config_file.parent.mkdir(parents=True)
        with open(config_file, "w") as f:
            yaml.safe_dump(config_data, f)

        config = GuardKitConfig(config_path=config_file)

        result = await execute_context_switch(
            client=None,
            target_project="proj-b",
            config=config
        )

        assert result["status"] == "success"
        assert "active_tasks" in result
        assert len(result["active_tasks"]) == 1
        assert result["active_tasks"][0]["id"] == "TASK-001"


# ============================================================================
# Test format_context_switch_display function
# ============================================================================

class TestFormatContextSwitchDisplay:
    """Tests for format_context_switch_display() function."""

    def test_format_switch_display(self):
        """Test formatting the switch result for display."""
        from guardkit.planning.context_switch import format_context_switch_display

        result = {
            "status": "success",
            "project_id": "my-project",
            "project_path": "/home/user/my-project",
            "architecture": [
                {"fact": "Uses FastAPI for REST API", "name": "arch-1"}
            ],
            "active_tasks": [
                {"id": "TASK-001", "title": "Implement auth", "status": "in_progress"}
            ]
        }

        display = format_context_switch_display(result, mode="switch")

        assert "my-project" in display
        assert "TASK-001" in display or "Implement auth" in display

    def test_format_list_display(self, tmp_path: Path):
        """Test formatting project list for --list mode."""
        from guardkit.planning.context_switch import format_context_switch_display

        projects = [
            {"id": "proj-a", "path": "/path/a", "last_accessed": "2025-01-15T10:00:00Z"},
            {"id": "proj-b", "path": "/path/b", "last_accessed": "2025-01-10T10:00:00Z"}
        ]

        display = format_context_switch_display({"projects": projects}, mode="list")

        assert "proj-a" in display
        assert "proj-b" in display

    def test_format_current_display(self):
        """Test formatting current project info (no-args mode)."""
        from guardkit.planning.context_switch import format_context_switch_display

        result = {
            "status": "success",
            "project_id": "current-proj",
            "project_path": "/home/user/current-proj",
            "active_tasks": []
        }

        display = format_context_switch_display(result, mode="current")

        assert "current-proj" in display
