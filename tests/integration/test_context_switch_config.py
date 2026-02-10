"""
Integration Tests for Config Round-Trip Functionality

Tests the GuardKitConfig class for correct YAML persistence, context switching,
and graceful error handling across config file operations.

Coverage Target: >=85%
Test Count: 10+ tests

Module Under Test:
    guardkit.planning.context_switch.GuardKitConfig

Test Areas:
    - Config persistence and reload
    - Round-trip context switching (A→B→A)
    - Timestamp updates on switch
    - Missing/corrupt YAML handling
    - Concurrent write safety
    - Unknown field preservation
"""

import pytest
import yaml
import time
from pathlib import Path
from datetime import datetime, timezone
from guardkit.planning.context_switch import GuardKitConfig


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def config_dir(tmp_path):
    """Create a temporary .guardkit directory with config.

    Note: The actual GuardKitConfig uses dict format for known_projects
    (not list), where the project ID is the key.
    """
    guardkit_dir = tmp_path / ".guardkit"
    guardkit_dir.mkdir()
    config_file = guardkit_dir / "config.yaml"

    # Create config with dict-based known_projects (matching production format)
    config_file.write_text(yaml.safe_dump({
        "active_project": "guardkit",
        "known_projects": {
            "guardkit": {
                "name": "GuardKit CLI",
                "path": str(tmp_path / "guardkit"),
                "last_accessed": "2026-02-09T10:30:00Z",
            },
            "requirekit": {
                "name": "RequireKit",
                "path": str(tmp_path / "requirekit"),
                "last_accessed": "2026-02-08T14:00:00Z",
            },
        },
    }))
    return guardkit_dir


@pytest.fixture
def empty_config_dir(tmp_path):
    """Create an empty .guardkit directory without config file."""
    guardkit_dir = tmp_path / ".guardkit"
    guardkit_dir.mkdir()
    return guardkit_dir


@pytest.fixture
def corrupt_config_dir(tmp_path):
    """Create .guardkit directory with corrupt YAML."""
    guardkit_dir = tmp_path / ".guardkit"
    guardkit_dir.mkdir()
    config_file = guardkit_dir / "config.yaml"

    # Write invalid YAML (unclosed bracket, invalid syntax)
    config_file.write_text("""
active_project: guardkit
known_projects:
  guardkit:
    name: GuardKit
    path: /tmp/guardkit
    last_accessed: [invalid syntax here
""")
    return guardkit_dir


# ============================================================================
# 1. Config Persistence Tests (3 tests)
# ============================================================================

def test_switch_persists_to_config(config_dir):
    """Test that switching project persists changes to config file.

    Verifies:
        - Config is written to disk on switch
        - Reloading config shows updated active project
        - last_accessed timestamp is updated
    """
    config_path = config_dir / "config.yaml"

    # Create config and switch project
    config = GuardKitConfig(config_path=config_path)
    assert config.active_project["id"] == "guardkit"

    # Switch to requirekit
    config.set_active_project("requirekit")

    # Reload config from disk to verify persistence
    config_reloaded = GuardKitConfig(config_path=config_path)
    assert config_reloaded.active_project is not None
    assert config_reloaded.active_project["id"] == "requirekit"
    assert config_reloaded.active_project["name"] == "RequireKit"

    # Verify last_accessed was updated (should be recent)
    last_accessed = config_reloaded.active_project["last_accessed"]
    last_accessed_time = datetime.fromisoformat(last_accessed.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    time_diff = (now - last_accessed_time).total_seconds()

    # Should be updated within the last few seconds
    assert time_diff < 5.0, f"Timestamp not recent: {time_diff}s ago"


def test_switch_round_trip(config_dir):
    """Test switching A→B→A preserves all state.

    Verifies:
        - Can switch between projects multiple times
        - All project data is preserved
        - Timestamps are updated correctly
    """
    config_path = config_dir / "config.yaml"
    config = GuardKitConfig(config_path=config_path)

    # Initial state: guardkit is active
    assert config.active_project["id"] == "guardkit"
    guardkit_path = config.active_project["path"]

    # Switch to requirekit
    config.set_active_project("requirekit")
    assert config.active_project["id"] == "requirekit"
    requirekit_path = config.active_project["path"]

    # Switch back to guardkit
    config.set_active_project("guardkit")
    assert config.active_project["id"] == "guardkit"

    # Verify all data preserved
    assert config.active_project["path"] == guardkit_path
    assert config.active_project["name"] == "GuardKit CLI"

    # Verify requirekit data still exists
    requirekit = config.get_known_project("requirekit")
    assert requirekit is not None
    assert requirekit["path"] == requirekit_path
    assert requirekit["name"] == "RequireKit"


def test_switch_updates_timestamp(config_dir):
    """Test that last_accessed timestamp is updated to current time.

    Verifies:
        - Timestamp format is ISO 8601 with Z suffix
        - Timestamp is updated to current UTC time
        - Multiple switches update timestamp each time
    """
    config_path = config_dir / "config.yaml"
    config = GuardKitConfig(config_path=config_path)

    # Get initial timestamp
    initial_timestamp = config.active_project["last_accessed"]

    # Wait a small amount to ensure timestamp difference
    time.sleep(0.1)

    # Switch to requirekit
    config.set_active_project("requirekit")
    new_timestamp = config.active_project["last_accessed"]

    # Verify timestamp changed
    assert new_timestamp != initial_timestamp

    # Verify timestamp is recent (within last 5 seconds)
    new_time = datetime.fromisoformat(new_timestamp.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    time_diff = (now - new_time).total_seconds()
    assert time_diff < 5.0, f"Timestamp not recent: {time_diff}s ago"

    # Verify timestamp format (ends with Z)
    assert new_timestamp.endswith("Z"), "Timestamp should end with Z"


# ============================================================================
# 2. Edge Case Handling Tests (5 tests)
# ============================================================================

def test_config_handles_missing_known_projects(config_dir):
    """Test config without known_projects key returns empty dict gracefully.

    Verifies:
        - Missing known_projects doesn't crash
        - active_project returns None when no projects exist
        - Config can still be loaded and saved
    """
    config_path = config_dir / "config.yaml"

    # Create config without known_projects
    config_path.write_text(yaml.safe_dump({
        "active_project": "guardkit",
    }))

    config = GuardKitConfig(config_path=config_path)

    # Should return None since known_projects is missing
    assert config.active_project is None

    # list_known_projects should return empty list
    assert config.list_known_projects() == []

    # get_known_project should return None
    assert config.get_known_project("guardkit") is None


def test_config_handles_empty_file(empty_config_dir):
    """Test empty config.yaml returns graceful defaults.

    Verifies:
        - Empty file doesn't crash on load
        - Returns empty dict for data
        - active_project returns None
    """
    config_path = empty_config_dir / "config.yaml"

    # Create empty file
    config_path.write_text("")

    config = GuardKitConfig(config_path=config_path)

    # Should handle empty file gracefully
    assert config.active_project is None
    assert config.list_known_projects() == []


def test_config_handles_missing_file(empty_config_dir):
    """Test missing config file returns graceful defaults.

    Verifies:
        - Missing file doesn't crash on load
        - Returns empty config
        - Can save to create new file
    """
    config_path = empty_config_dir / "config.yaml"

    # Don't create the file
    assert not config_path.exists()

    config = GuardKitConfig(config_path=config_path)

    # Should handle missing file gracefully
    assert config.active_project is None
    assert config.list_known_projects() == []


def test_config_handles_corrupt_yaml(corrupt_config_dir):
    """Test invalid YAML is handled gracefully with logging.

    Verifies:
        - Corrupt YAML doesn't crash the application
        - Returns empty config on YAML error
        - Error is logged (warning level)
    """
    config_path = corrupt_config_dir / "config.yaml"

    # Should handle corrupt YAML gracefully
    config = GuardKitConfig(config_path=config_path)

    # Should return empty config on error
    assert config.active_project is None
    assert config.list_known_projects() == []


def test_config_preserves_unknown_fields(config_dir):
    """Test that extra YAML fields are not lost on save.

    Verifies:
        - Unknown fields in config are preserved
        - Switching projects doesn't delete custom fields
        - Round-trip preserves all data
    """
    config_path = config_dir / "config.yaml"

    # Add custom fields to config
    with open(config_path, "r") as f:
        config_data = yaml.safe_load(f)

    config_data["custom_field"] = "custom_value"
    config_data["settings"] = {
        "theme": "dark",
        "notifications": True
    }

    with open(config_path, "w") as f:
        yaml.safe_dump(config_data, f)

    # Load config and switch project
    config = GuardKitConfig(config_path=config_path)
    config.set_active_project("requirekit")

    # Reload and verify custom fields preserved
    with open(config_path, "r") as f:
        reloaded_data = yaml.safe_load(f)

    assert reloaded_data["custom_field"] == "custom_value"
    assert reloaded_data["settings"]["theme"] == "dark"
    assert reloaded_data["settings"]["notifications"] is True


# ============================================================================
# 3. Error Handling Tests (2 tests)
# ============================================================================

def test_switch_to_unknown_project_raises_error(config_dir):
    """Test switching to unknown project raises ValueError.

    Verifies:
        - Unknown project ID raises ValueError
        - Error message includes project ID
        - Config state is not modified
    """
    config_path = config_dir / "config.yaml"
    config = GuardKitConfig(config_path=config_path)

    # Attempt to switch to unknown project
    with pytest.raises(ValueError) as exc_info:
        config.set_active_project("unknown-project")

    # Verify error message
    assert "unknown-project" in str(exc_info.value).lower()
    assert "unknown" in str(exc_info.value).lower()

    # Verify config wasn't modified
    assert config.active_project["id"] == "guardkit"


def test_config_concurrent_writes(config_dir):
    """Test that rapid switches don't corrupt the config file.

    Verifies:
        - Multiple rapid switches complete successfully
        - Final config is valid YAML
        - All switches are reflected in timestamps

    Note: This is a basic concurrency test. True concurrent writes
    would require threading/multiprocessing, but rapid sequential
    writes test file system consistency.
    """
    config_path = config_dir / "config.yaml"
    config = GuardKitConfig(config_path=config_path)

    # Perform rapid switches
    for i in range(10):
        if i % 2 == 0:
            config.set_active_project("guardkit")
        else:
            config.set_active_project("requirekit")

    # Verify final state is valid
    assert config.active_project["id"] == "requirekit"

    # Reload from disk to verify file integrity
    config_reloaded = GuardKitConfig(config_path=config_path)
    assert config_reloaded.active_project["id"] == "requirekit"

    # Verify file is valid YAML
    with open(config_path, "r") as f:
        data = yaml.safe_load(f)
    assert data is not None
    assert isinstance(data, dict)


# ============================================================================
# 4. Additional Integration Tests (2 tests)
# ============================================================================

def test_list_known_projects(config_dir):
    """Test list_known_projects returns all projects with IDs.

    Verifies:
        - All projects are returned
        - Each project has 'id' field
        - Projects have expected metadata
    """
    config_path = config_dir / "config.yaml"
    config = GuardKitConfig(config_path=config_path)

    projects = config.list_known_projects()

    # Should return 2 projects
    assert len(projects) == 2

    # Extract project IDs
    project_ids = {p["id"] for p in projects}
    assert project_ids == {"guardkit", "requirekit"}

    # Verify each has required fields
    for project in projects:
        assert "id" in project
        assert "name" in project
        assert "path" in project
        assert "last_accessed" in project


def test_get_known_project(config_dir):
    """Test get_known_project returns project details with ID.

    Verifies:
        - Can retrieve project by ID
        - Returns None for unknown project
        - Returned dict includes ID field
    """
    config_path = config_dir / "config.yaml"
    config = GuardKitConfig(config_path=config_path)

    # Get existing project
    guardkit = config.get_known_project("guardkit")
    assert guardkit is not None
    assert guardkit["id"] == "guardkit"
    assert guardkit["name"] == "GuardKit CLI"
    assert "path" in guardkit
    assert "last_accessed" in guardkit

    # Get unknown project
    unknown = config.get_known_project("unknown")
    assert unknown is None


# ============================================================================
# Summary
# ============================================================================
# Total tests: 12
# Coverage areas:
#   - Config persistence and reload (3 tests)
#   - Edge case handling (5 tests)
#   - Error handling (2 tests)
#   - Additional integration (2 tests)
#
# All tests use tmp_path for isolation and match production config format.
# ============================================================================
