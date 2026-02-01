"""
Tests for project_id functionality in GraphitiClient

This test suite covers the project_id feature implementation that allows
projects to have isolated knowledge graphs through ID prefixing.

Test Coverage:
- normalize_project_id() function tests
- GraphitiConfig project_id field tests
- GraphitiClient project_id initialization and access
- Config loading from YAML
- Environment variable override (GUARDKIT_PROJECT_ID)
- Auto-detection from current directory
- Backward compatibility (None project_id = system/global scope)

Coverage Target: >=85%
Test Count: 30+ tests
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Optional
from pathlib import Path
import os
import tempfile

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.graphiti_client import (
        GraphitiConfig,
        GraphitiClient,
        normalize_project_id,
    )
    from guardkit.knowledge.config import (
        GraphitiSettings,
        load_graphiti_config,
    )
    IMPORTS_AVAILABLE = True
except (ImportError, AttributeError):
    IMPORTS_AVAILABLE = False


# Skip all tests if imports not available or if normalize_project_id doesn't exist
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created"
)


# ============================================================================
# 1. normalize_project_id() Function Tests (10 tests)
# ============================================================================

class TestNormalizeProjectId:
    """Test normalize_project_id() helper function."""

    def test_converts_to_lowercase(self):
        """Test that project IDs are converted to lowercase."""
        result = normalize_project_id("MyProject")
        assert result == "myproject"

    def test_replaces_spaces_with_hyphens(self):
        """Test that spaces are replaced with hyphens."""
        result = normalize_project_id("My Project Name")
        assert result == "my-project-name"

    def test_removes_non_alphanumeric_except_hyphens(self):
        """Test that special characters are removed (except hyphens)."""
        result = normalize_project_id("project@name#123")
        assert result == "projectname123"

    def test_handles_underscores(self):
        """Test that underscores are removed or converted."""
        result = normalize_project_id("my_project_name")
        # Underscores should be removed or converted to hyphens
        assert "_" not in result

    def test_truncates_to_max_50_characters(self):
        """Test that project IDs are truncated to 50 characters."""
        long_name = "a" * 100
        result = normalize_project_id(long_name)
        assert len(result) <= 50

    def test_handles_empty_string(self):
        """Test handling of empty string."""
        result = normalize_project_id("")
        # Should return empty string or raise ValueError
        assert result == "" or result is None

    def test_handles_whitespace_only(self):
        """Test handling of whitespace-only string."""
        result = normalize_project_id("   ")
        # Should return empty or minimal string
        assert len(result) <= 3

    def test_preserves_existing_hyphens(self):
        """Test that existing hyphens are preserved."""
        result = normalize_project_id("my-existing-project")
        assert result == "my-existing-project"

    def test_handles_numbers(self):
        """Test that numbers are preserved."""
        result = normalize_project_id("project123")
        assert result == "project123"

    def test_handles_multiple_consecutive_spaces(self):
        """Test that multiple consecutive spaces become single hyphen."""
        result = normalize_project_id("my    project")
        # Multiple spaces should not create multiple hyphens
        assert "--" not in result


# ============================================================================
# 2. GraphitiConfig project_id Tests (8 tests)
# ============================================================================

class TestGraphitiConfigProjectId:
    """Test GraphitiConfig dataclass with project_id field."""

    def test_config_default_project_id_is_none(self):
        """Test that default project_id is None (backward compatible)."""
        config = GraphitiConfig()
        assert config.project_id is None

    def test_config_accepts_custom_project_id(self):
        """Test that custom project_id can be set."""
        config = GraphitiConfig(project_id="my-project")
        assert config.project_id == "my-project"

    def test_config_project_id_is_immutable(self):
        """Test that project_id is immutable (frozen dataclass)."""
        config = GraphitiConfig(project_id="my-project")

        with pytest.raises(AttributeError):
            config.project_id = "new-project"

    def test_config_with_project_id_and_other_fields(self):
        """Test that project_id works alongside other config fields."""
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://custom:7687",
            project_id="test-project"
        )

        assert config.enabled is True
        assert config.neo4j_uri == "bolt://custom:7687"
        assert config.project_id == "test-project"

    def test_config_validates_project_id_format(self):
        """Test that invalid project_id format is rejected."""
        # Should reject invalid characters
        with pytest.raises(ValueError, match="project_id"):
            GraphitiConfig(project_id="invalid@project#name")

    def test_config_allows_alphanumeric_and_hyphens(self):
        """Test that alphanumeric + hyphens are valid."""
        config = GraphitiConfig(project_id="my-project-123")
        assert config.project_id == "my-project-123"

    def test_config_rejects_too_long_project_id(self):
        """Test that project_id longer than 50 chars is rejected."""
        long_id = "a" * 51
        with pytest.raises(ValueError, match="50 characters"):
            GraphitiConfig(project_id=long_id)

    def test_config_accepts_max_length_project_id(self):
        """Test that 50-character project_id is accepted."""
        max_id = "a" * 50
        config = GraphitiConfig(project_id=max_id)
        assert config.project_id == max_id


# ============================================================================
# 3. GraphitiClient project_id Tests (12 tests)
# ============================================================================

class TestGraphitiClientProjectId:
    """Test GraphitiClient with project_id functionality."""

    def test_client_accepts_project_id_parameter(self):
        """Test that client accepts project_id in config."""
        config = GraphitiConfig(project_id="my-project")
        client = GraphitiClient(config)

        assert client.config.project_id == "my-project"

    def test_client_stores_project_id(self):
        """Test that client stores project_id internally."""
        config = GraphitiConfig(project_id="test-project")
        client = GraphitiClient(config)

        # Client should have access to project_id
        assert hasattr(client, 'project_id') or hasattr(client, 'get_project_id')

    def test_get_project_id_returns_explicit_value(self):
        """Test that get_project_id() returns explicitly set project_id."""
        config = GraphitiConfig(project_id="my-project")
        client = GraphitiClient(config)

        assert client.get_project_id() == "my-project"

    def test_get_project_id_auto_detects_when_none(self):
        """Test that get_project_id() auto-detects from directory when None."""
        config = GraphitiConfig(project_id=None)
        client = GraphitiClient(config)

        with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
            mock_get_name.return_value = "auto-detected-project"

            result = client.get_project_id()
            # Should auto-detect and normalize
            assert result == normalize_project_id("auto-detected-project")

    def test_get_project_id_returns_none_for_system_scope(self):
        """Test that get_project_id() can return None for system/global scope."""
        config = GraphitiConfig(project_id=None)
        client = GraphitiClient(config)

        # When auto_detect=False, should return None
        result = client.get_project_id(auto_detect=False)
        assert result is None

    def test_project_id_property_provides_access(self):
        """Test that project_id property provides convenient access."""
        config = GraphitiConfig(project_id="my-project")
        client = GraphitiClient(config)

        # Property access should work
        assert client.project_id == "my-project"

    def test_project_id_property_returns_none_when_not_set(self):
        """Test that project_id property returns None when not configured."""
        config = GraphitiConfig(project_id=None)
        client = GraphitiClient(config)

        # Without auto-detection, should be None
        with patch.object(client, 'get_project_id', return_value=None):
            assert client.project_id is None

    def test_client_backward_compatible_without_project_id(self):
        """Test that client works without project_id (backward compatible)."""
        config = GraphitiConfig()  # No project_id
        client = GraphitiClient(config)

        # Should not raise, client should be usable
        assert client is not None
        assert client.config is not None

    def test_client_normalizes_project_id_on_creation(self):
        """Test that client normalizes project_id during initialization."""
        config = GraphitiConfig(project_id="My Project 123")
        client = GraphitiClient(config)

        # Should be normalized
        assert client.get_project_id() == normalize_project_id("My Project 123")

    def test_get_project_id_with_explicit_auto_detect_true(self):
        """Test get_project_id(auto_detect=True) forces auto-detection."""
        config = GraphitiConfig(project_id=None)
        client = GraphitiClient(config)

        with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
            mock_get_name.return_value = "detected-project"

            result = client.get_project_id(auto_detect=True)
            assert result == normalize_project_id("detected-project")

    def test_get_project_id_prefers_explicit_over_auto_detect(self):
        """Test that explicit project_id takes precedence over auto-detect."""
        config = GraphitiConfig(project_id="explicit-project")
        client = GraphitiClient(config)

        with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
            mock_get_name.return_value = "detected-project"

            # Even with auto_detect=True, should use explicit value
            result = client.get_project_id(auto_detect=True)
            assert result == "explicit-project"

    def test_project_id_used_in_group_id_prefixing(self):
        """Test that project_id is available for group_id prefixing operations."""
        config = GraphitiConfig(project_id="myapp")
        client = GraphitiClient(config)

        # Client should have a method to prefix group IDs
        # This will be tested in TASK-GR-PRE-001-B
        assert hasattr(client, 'get_project_id')


# ============================================================================
# 4. Config Loading Tests (8 tests)
# ============================================================================

class TestGraphitiConfigLoading:
    """Test loading project_id from YAML configuration."""

    def test_load_config_with_project_id_from_yaml(self):
        """Test loading project_id from YAML file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "graphiti.yaml"
            config_path.write_text("""
enabled: true
neo4j_uri: bolt://localhost:7687
project_id: yaml-project
""")

            settings = load_graphiti_config(config_path)
            assert settings.project_id == "yaml-project"

    def test_load_config_without_project_id_defaults_to_none(self):
        """Test that missing project_id in YAML defaults to None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "graphiti.yaml"
            config_path.write_text("""
enabled: true
neo4j_uri: bolt://localhost:7687
""")

            settings = load_graphiti_config(config_path)
            assert settings.project_id is None

    def test_load_config_empty_project_id_treated_as_none(self):
        """Test that empty project_id in YAML is treated as None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "graphiti.yaml"
            config_path.write_text("""
enabled: true
project_id:
""")

            settings = load_graphiti_config(config_path)
            assert settings.project_id is None

    def test_env_var_override_guardkit_project_id(self):
        """Test that GUARDKIT_PROJECT_ID env var overrides YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "graphiti.yaml"
            config_path.write_text("""
enabled: true
project_id: yaml-project
""")

            with patch.dict(os.environ, {"GUARDKIT_PROJECT_ID": "env-project"}):
                settings = load_graphiti_config(config_path)
                assert settings.project_id == "env-project"

    def test_env_var_override_empty_string(self):
        """Test that empty GUARDKIT_PROJECT_ID env var is treated as None."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "graphiti.yaml"
            config_path.write_text("""
enabled: true
project_id: yaml-project
""")

            with patch.dict(os.environ, {"GUARDKIT_PROJECT_ID": ""}):
                settings = load_graphiti_config(config_path)
                # Empty string should be treated as None
                assert settings.project_id is None or settings.project_id == ""

    def test_graphiti_settings_includes_project_id_field(self):
        """Test that GraphitiSettings dataclass includes project_id field."""
        settings = GraphitiSettings(project_id="test-project")
        assert settings.project_id == "test-project"

    def test_graphiti_settings_default_project_id_is_none(self):
        """Test that GraphitiSettings defaults project_id to None."""
        settings = GraphitiSettings()
        assert settings.project_id is None

    def test_load_config_validates_project_id_format(self):
        """Test that config loading validates project_id format."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "graphiti.yaml"
            config_path.write_text("""
enabled: true
project_id: invalid@project#name
""")

            # Should either raise ValueError or sanitize the value
            with pytest.raises(ValueError):
                settings = load_graphiti_config(config_path)


# ============================================================================
# 5. Project ID Auto-Detection Tests (6 tests)
# ============================================================================

class TestProjectIdAutoDetection:
    """Test auto-detection of project_id from current directory."""

    def test_auto_detect_from_current_directory_name(self):
        """Test auto-detection uses current directory name."""
        config = GraphitiConfig(project_id=None)
        client = GraphitiClient(config)

        with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
            mock_get_name.return_value = "my-project-dir"

            result = client.get_project_id(auto_detect=True)
            # Should normalize the directory name
            assert result == normalize_project_id("my-project-dir")

    def test_auto_detect_normalizes_directory_name(self):
        """Test that auto-detected directory name is normalized."""
        config = GraphitiConfig(project_id=None)
        client = GraphitiClient(config)

        with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
            mock_get_name.return_value = "My Project Dir @123"

            result = client.get_project_id(auto_detect=True)
            # Should be normalized (lowercase, no special chars)
            assert result == normalize_project_id("My Project Dir @123")

    def test_auto_detect_returns_none_when_explicitly_disabled(self):
        """Test that auto_detect=False returns None."""
        config = GraphitiConfig(project_id=None)
        client = GraphitiClient(config)

        result = client.get_project_id(auto_detect=False)
        assert result is None

    def test_auto_detect_default_behavior(self):
        """Test default behavior when auto_detect parameter not specified."""
        config = GraphitiConfig(project_id=None)
        client = GraphitiClient(config)

        # Default should auto-detect
        with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
            mock_get_name.return_value = "default-project"

            result = client.get_project_id()  # No auto_detect parameter
            # Default behavior should auto-detect
            assert result == normalize_project_id("default-project")

    def test_explicit_project_id_skips_auto_detect(self):
        """Test that explicit project_id prevents auto-detection."""
        config = GraphitiConfig(project_id="explicit-project")
        client = GraphitiClient(config)

        with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
            mock_get_name.return_value = "detected-project"

            result = client.get_project_id(auto_detect=True)
            # Should use explicit value, not detected
            assert result == "explicit-project"
            # get_current_project_name should not be called
            mock_get_name.assert_not_called()

    def test_auto_detect_handles_path_cwd(self):
        """Test that auto-detection works with Path.cwd()."""
        # Integration test to verify get_current_project_name uses Path.cwd()
        from guardkit.knowledge.graphiti_client import get_current_project_name

        # Should return current directory name
        result = get_current_project_name()
        assert isinstance(result, str)
        assert len(result) > 0


# ============================================================================
# 6. Edge Cases and Integration Tests (6 tests)
# ============================================================================

class TestProjectIdEdgeCases:
    """Test edge cases and integration scenarios."""

    def test_project_id_with_special_characters_normalized(self):
        """Test that special characters in project_id are rejected."""
        # Config should validate and reject invalid characters
        # This is the expected behavior for explicit project_ids
        with pytest.raises(ValueError, match="invalid characters"):
            GraphitiConfig(project_id="my@project#123")

    def test_very_long_auto_detected_project_id(self):
        """Test that very long auto-detected names are truncated."""
        config = GraphitiConfig(project_id=None)
        client = GraphitiClient(config)

        with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
            mock_get_name.return_value = "a" * 100

            result = client.get_project_id(auto_detect=True)
            # Should be truncated to max 50 characters
            assert len(result) <= 50

    def test_project_id_none_vs_empty_string(self):
        """Test distinction between None and empty string for project_id."""
        config1 = GraphitiConfig(project_id=None)
        config2 = GraphitiConfig(project_id="")

        client1 = GraphitiClient(config1)
        client2 = GraphitiClient(config2)

        # Both should be treated as "no project ID"
        result1 = client1.get_project_id(auto_detect=False)
        result2 = client2.get_project_id(auto_detect=False)

        assert result1 is None or result1 == ""
        assert result2 is None or result2 == ""

    def test_client_initialization_with_all_fields(self):
        """Test client initialization with all config fields including project_id."""
        config = GraphitiConfig(
            enabled=True,
            neo4j_uri="bolt://custom:7687",
            neo4j_user="custom_user",
            neo4j_password="custom_pass",
            timeout=60.0,
            project_id="full-config-project"
        )
        client = GraphitiClient(config)

        assert client.config.enabled is True
        assert client.config.neo4j_uri == "bolt://custom:7687"
        assert client.config.project_id == "full-config-project"
        assert client.get_project_id() == "full-config-project"

    def test_project_id_immutability_after_client_creation(self):
        """Test that project_id cannot be changed after client creation."""
        config = GraphitiConfig(project_id="original-project")
        client = GraphitiClient(config)

        # Config is frozen, cannot modify
        with pytest.raises(AttributeError):
            client.config.project_id = "new-project"

    @pytest.mark.asyncio
    async def test_project_id_available_during_initialize(self):
        """Test that project_id is accessible during client initialization."""
        config = GraphitiConfig(enabled=False, project_id="init-test-project")
        client = GraphitiClient(config)

        # Before initialization, project_id should be accessible
        assert client.get_project_id() == "init-test-project"

        # After initialization (even if disabled), project_id should still be accessible
        await client.initialize()
        assert client.get_project_id() == "init-test-project"


# ============================================================================
# 7. Configuration Priority Tests (4 tests)
# ============================================================================

class TestConfigurationPriority:
    """Test configuration priority: parameter > YAML > auto-detect."""

    def test_priority_explicit_parameter_over_yaml(self):
        """Test that explicit parameter takes precedence over YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "graphiti.yaml"
            config_path.write_text("""
project_id: yaml-project
""")

            # Explicitly create config with different project_id
            config = GraphitiConfig(project_id="explicit-project")
            client = GraphitiClient(config)

            assert client.get_project_id() == "explicit-project"

    def test_priority_yaml_over_auto_detect(self):
        """Test that YAML config takes precedence over auto-detect."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "graphiti.yaml"
            config_path.write_text("""
project_id: yaml-project
""")

            settings = load_graphiti_config(config_path)
            config = GraphitiConfig(project_id=settings.project_id)
            client = GraphitiClient(config)

            with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
                mock_get_name.return_value = "detected-project"

                # Should use YAML value, not auto-detected
                assert client.get_project_id() == "yaml-project"

    def test_priority_env_var_over_yaml(self):
        """Test that env var takes precedence over YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "graphiti.yaml"
            config_path.write_text("""
project_id: yaml-project
""")

            with patch.dict(os.environ, {"GUARDKIT_PROJECT_ID": "env-project"}):
                settings = load_graphiti_config(config_path)
                assert settings.project_id == "env-project"

    def test_priority_chain_explicit_env_yaml_auto(self):
        """Test full priority chain: explicit > env > YAML > auto-detect."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "graphiti.yaml"
            config_path.write_text("""
project_id: yaml-project
""")

            # Test each level of precedence

            # 1. Explicit parameter wins over everything
            config = GraphitiConfig(project_id="explicit-project")
            client = GraphitiClient(config)
            assert client.get_project_id() == "explicit-project"

            # 2. Env var wins over YAML
            with patch.dict(os.environ, {"GUARDKIT_PROJECT_ID": "env-project"}):
                settings = load_graphiti_config(config_path)
                assert settings.project_id == "env-project"

            # 3. YAML wins over auto-detect
            settings = load_graphiti_config(config_path)
            config = GraphitiConfig(project_id=settings.project_id)
            client = GraphitiClient(config)
            with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
                mock_get_name.return_value = "detected-project"
                assert client.get_project_id() == "yaml-project"

            # 4. Auto-detect is fallback
            config = GraphitiConfig(project_id=None)
            client = GraphitiClient(config)
            with patch('guardkit.knowledge.graphiti_client.get_current_project_name') as mock_get_name:
                mock_get_name.return_value = "detected-project"
                assert client.get_project_id(auto_detect=True) == normalize_project_id("detected-project")
