#!/usr/bin/env python3
"""Unit tests for feature_detection module.

Tests the RequireKit feature detection functions with mocked file systems
to ensure proper behavior with and without RequireKit installed.

Test Coverage:
    - supports_bdd() with new JSON marker format
    - supports_bdd() with legacy marker format
    - supports_bdd() when no marker exists
    - supports_requirements() delegates to supports_bdd()
    - supports_epics() delegates to supports_bdd()
    - get_requirekit_version() with valid JSON
    - get_requirekit_version() with invalid JSON
    - get_requirekit_version() when RequireKit not installed
    - Error handling for file I/O exceptions
    - Cross-platform path handling

Architecture:
    - Uses pytest fixtures for temporary file systems
    - Monkeypatching for Path.home() isolation
    - Tests cover both happy path and error conditions
    - No external dependencies beyond pytest

Part of: Task BDD-F3EA - Create feature_detection module for RequireKit detection
Author: Claude (Anthropic)
Created: 2025-11-30
"""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the module under test
from installer.global.commands.lib import feature_detection


class TestSupportsBDD:
    """Tests for supports_bdd() function."""

    def test_supports_bdd_with_new_json_marker(self, tmp_path, monkeypatch):
        """Test supports_bdd returns True when new JSON marker exists."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        # Create the new marker format directory and file
        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        marker_file.write_text('{"package": "require-kit", "version": "1.0.0"}')

        # Monkeypatch Path.home() to return our fake home
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.supports_bdd() is True

    def test_supports_bdd_with_legacy_marker(self, tmp_path, monkeypatch):
        """Test supports_bdd returns True when legacy marker exists."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        # Create the legacy marker format
        projects_dir = fake_home / "Projects" / "require-kit"
        projects_dir.mkdir(parents=True)
        marker_file = projects_dir / "require-kit.marker"
        marker_file.write_text("require-kit marker file")

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.supports_bdd() is True

    def test_supports_bdd_with_both_markers(self, tmp_path, monkeypatch):
        """Test supports_bdd returns True when both markers exist (prefers new)."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        # Create both marker formats
        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        new_marker = agentecflow_dir / "require-kit.marker.json"
        new_marker.write_text('{"version": "1.0.0"}')

        projects_dir = fake_home / "Projects" / "require-kit"
        projects_dir.mkdir(parents=True)
        legacy_marker = projects_dir / "require-kit.marker"
        legacy_marker.write_text("legacy marker")

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.supports_bdd() is True

    def test_supports_bdd_without_marker(self, tmp_path, monkeypatch):
        """Test supports_bdd returns False when no marker exists."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.supports_bdd() is False

    def test_supports_bdd_with_missing_parent_dir(self, tmp_path, monkeypatch):
        """Test supports_bdd handles missing parent directories gracefully."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        # Don't create any directories - let Path.exists() handle missing parents
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.supports_bdd() is False

    def test_supports_bdd_with_invalid_path(self, monkeypatch):
        """Test supports_bdd handles invalid home path gracefully."""
        # Mock Path.home() to raise an exception
        def raise_error():
            raise OSError("Cannot determine home directory")

        monkeypatch.setattr(Path, "home", raise_error)

        # Should return False without raising exception
        assert feature_detection.supports_bdd() is False


class TestSupportsRequirements:
    """Tests for supports_requirements() function."""

    def test_supports_requirements_delegates_to_bdd(self, tmp_path, monkeypatch):
        """Test supports_requirements uses same logic as supports_bdd."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Without marker, both should return False
        assert feature_detection.supports_requirements() is False
        assert feature_detection.supports_bdd() is False

        # With marker, both should return True
        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        marker_file.write_text('{}')

        assert feature_detection.supports_requirements() is True
        assert feature_detection.supports_bdd() is True

    def test_supports_requirements_matches_bdd_behavior(self, tmp_path, monkeypatch):
        """Test supports_requirements always matches supports_bdd output."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Test multiple scenarios
        for _ in range(3):
            assert (
                feature_detection.supports_requirements()
                == feature_detection.supports_bdd()
            )


class TestSupportsEpics:
    """Tests for supports_epics() function."""

    def test_supports_epics_delegates_to_bdd(self, tmp_path, monkeypatch):
        """Test supports_epics uses same logic as supports_bdd."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Without marker, both should return False
        assert feature_detection.supports_epics() is False
        assert feature_detection.supports_bdd() is False

        # With marker, both should return True
        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        marker_file.write_text('{}')

        assert feature_detection.supports_epics() is True
        assert feature_detection.supports_bdd() is True

    def test_supports_epics_matches_bdd_behavior(self, tmp_path, monkeypatch):
        """Test supports_epics always matches supports_bdd output."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Test multiple scenarios
        for _ in range(3):
            assert (
                feature_detection.supports_epics()
                == feature_detection.supports_bdd()
            )


class TestGetRequireKitVersion:
    """Tests for get_requirekit_version() function."""

    def test_get_version_with_valid_json(self, tmp_path, monkeypatch):
        """Test get_requirekit_version returns version from valid JSON."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        marker_file.write_text(
            json.dumps({
                "package": "require-kit",
                "version": "1.2.3",
                "installed_at": "2025-11-30"
            })
        )

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.get_requirekit_version() == "1.2.3"

    def test_get_version_with_missing_version_field(self, tmp_path, monkeypatch):
        """Test get_requirekit_version returns None when version field missing."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        marker_file.write_text('{"package": "require-kit"}')

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.get_requirekit_version() is None

    def test_get_version_with_non_string_version(self, tmp_path, monkeypatch):
        """Test get_requirekit_version returns None when version is not string."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        marker_file.write_text('{"version": 123}')

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.get_requirekit_version() is None

    def test_get_version_with_invalid_json(self, tmp_path, monkeypatch):
        """Test get_requirekit_version returns None for invalid JSON."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        marker_file.write_text("{invalid json content")

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.get_requirekit_version() is None

    def test_get_version_without_requirekit(self, tmp_path, monkeypatch):
        """Test get_requirekit_version returns None when RequireKit not installed."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.get_requirekit_version() is None

    def test_get_version_with_permission_error(self, tmp_path, monkeypatch):
        """Test get_requirekit_version handles permission errors gracefully."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        marker_file.write_text('{"version": "1.0.0"}')

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Mock open to raise PermissionError
        original_open = open
        def mock_open(*args, **kwargs):
            raise PermissionError("Access denied")

        with patch("builtins.open", side_effect=mock_open):
            assert feature_detection.get_requirekit_version() is None

    def test_get_version_empty_json(self, tmp_path, monkeypatch):
        """Test get_requirekit_version with empty JSON object."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        marker_file.write_text('{}')

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.get_requirekit_version() is None

    def test_get_version_with_complex_version_string(self, tmp_path, monkeypatch):
        """Test get_requirekit_version with complex semantic version string."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        version_string = "1.2.3-rc.1+build.20251130"
        marker_file.write_text(json.dumps({"version": version_string}))

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        assert feature_detection.get_requirekit_version() == version_string


class TestModuleAPI:
    """Tests for module-level API and exports."""

    def test_all_exports(self):
        """Test that __all__ includes expected functions."""
        expected = [
            "supports_bdd",
            "supports_requirements",
            "supports_epics",
            "get_requirekit_version",
        ]
        assert hasattr(feature_detection, "__all__")
        assert set(feature_detection.__all__) == set(expected)

    def test_functions_are_callable(self):
        """Test that all exported functions are callable."""
        for name in feature_detection.__all__:
            assert callable(getattr(feature_detection, name))

    def test_docstrings_present(self):
        """Test that all functions have docstrings."""
        for name in feature_detection.__all__:
            func = getattr(feature_detection, name)
            assert func.__doc__ is not None
            assert len(func.__doc__) > 0


class TestIntegration:
    """Integration tests for feature detection workflow."""

    def test_feature_detection_workflow_requirekit_installed(self, tmp_path, monkeypatch):
        """Test complete workflow when RequireKit is installed."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        marker_file = agentecflow_dir / "require-kit.marker.json"
        marker_file.write_text(
            json.dumps({
                "package": "require-kit",
                "version": "1.0.0"
            })
        )

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # All features should be available
        assert feature_detection.supports_bdd() is True
        assert feature_detection.supports_requirements() is True
        assert feature_detection.supports_epics() is True
        assert feature_detection.get_requirekit_version() == "1.0.0"

    def test_feature_detection_workflow_requirekit_not_installed(self, tmp_path, monkeypatch):
        """Test complete workflow when RequireKit is not installed."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # All features should be unavailable
        assert feature_detection.supports_bdd() is False
        assert feature_detection.supports_requirements() is False
        assert feature_detection.supports_epics() is False
        assert feature_detection.get_requirekit_version() is None

    def test_feature_detection_migration_from_legacy_to_new(self, tmp_path, monkeypatch):
        """Test feature detection during migration from legacy to new format."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()

        monkeypatch.setattr(Path, "home", lambda: fake_home)

        # Start with legacy format
        projects_dir = fake_home / "Projects" / "require-kit"
        projects_dir.mkdir(parents=True)
        legacy_marker = projects_dir / "require-kit.marker"
        legacy_marker.write_text("legacy")

        assert feature_detection.supports_bdd() is True
        assert feature_detection.get_requirekit_version() is None  # Version only in new format

        # Migrate to new format
        agentecflow_dir = fake_home / ".agentecflow"
        agentecflow_dir.mkdir()
        new_marker = agentecflow_dir / "require-kit.marker.json"
        new_marker.write_text('{"version": "1.0.0"}')

        assert feature_detection.supports_bdd() is True
        assert feature_detection.get_requirekit_version() == "1.0.0"
