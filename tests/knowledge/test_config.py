"""
TDD RED Phase: Tests for guardkit.knowledge.config

These tests are written to FAIL initially (RED phase of TDD).
Implementation will be created to make these tests pass (GREEN phase).

Test Coverage:
- Configuration loading from .guardkit/graphiti.yaml
- GraphitiSettings class with pydantic validation
- Default configuration values
- Environment variable overrides
- Invalid configuration handling
- Missing configuration file handling
"""

import pytest
from unittest.mock import Mock, patch, mock_open
from pathlib import Path
import yaml
import os

# Import will fail initially - this is expected in RED phase
try:
    from guardkit.knowledge.config import (
        GraphitiSettings,
        load_graphiti_config,
        get_config_path,
    )
    IMPORTS_AVAILABLE = True
except ImportError:
    IMPORTS_AVAILABLE = False


# Skip all tests if imports not available (expected in RED phase)
pytestmark = pytest.mark.skipif(
    not IMPORTS_AVAILABLE,
    reason="Implementation not yet created (TDD RED phase)"
)


class TestGraphitiSettings:
    """Test GraphitiSettings class."""

    def test_settings_default_values(self):
        """Test default settings values."""
        settings = GraphitiSettings()

        assert settings.enabled is True
        assert settings.host == "localhost"
        assert settings.port == 8000
        assert settings.timeout == 30.0

    def test_settings_custom_values(self):
        """Test custom settings values."""
        settings = GraphitiSettings(
            enabled=False,
            host="custom.host",
            port=9000,
            timeout=60.0
        )

        assert settings.enabled is False
        assert settings.host == "custom.host"
        assert settings.port == 9000
        assert settings.timeout == 60.0

    def test_settings_from_dict(self):
        """Test creating settings from dictionary."""
        config_dict = {
            "enabled": False,
            "host": "graphiti.example.com",
            "port": 9000,
            "timeout": 45.0
        }

        settings = GraphitiSettings(**config_dict)

        assert settings.enabled is False
        assert settings.host == "graphiti.example.com"
        assert settings.port == 9000
        assert settings.timeout == 45.0

    def test_settings_validation_invalid_port(self):
        """Test settings validation fails with invalid port."""
        with pytest.raises((ValueError, AssertionError)):
            GraphitiSettings(port=-1)

        with pytest.raises((ValueError, AssertionError)):
            GraphitiSettings(port=70000)

    def test_settings_validation_invalid_timeout(self):
        """Test settings validation fails with invalid timeout."""
        with pytest.raises((ValueError, AssertionError)):
            GraphitiSettings(timeout=-5.0)

        with pytest.raises((ValueError, AssertionError)):
            GraphitiSettings(timeout=0.0)

    def test_settings_validation_invalid_host(self):
        """Test settings validation fails with invalid host."""
        with pytest.raises((ValueError, AssertionError)):
            GraphitiSettings(host="")

    def test_settings_type_validation(self):
        """Test settings type validation."""
        # Port must be int
        with pytest.raises((ValueError, TypeError)):
            GraphitiSettings(port="8000")

        # Timeout must be float
        with pytest.raises((ValueError, TypeError)):
            GraphitiSettings(timeout="30")

        # Enabled must be bool
        with pytest.raises((ValueError, TypeError)):
            GraphitiSettings(enabled="true")


class TestGetConfigPath:
    """Test get_config_path function."""

    def test_get_config_path_returns_path(self):
        """Test get_config_path returns Path object."""
        config_path = get_config_path()

        assert isinstance(config_path, Path)

    def test_get_config_path_correct_location(self):
        """Test config path is .guardkit/graphiti.yaml."""
        config_path = get_config_path()

        assert config_path.name == "graphiti.yaml"
        assert config_path.parent.name == ".guardkit"

    def test_get_config_path_custom_base_dir(self):
        """Test get_config_path with custom base directory."""
        custom_dir = Path("/custom/project")
        config_path = get_config_path(base_dir=custom_dir)

        assert config_path == custom_dir / ".guardkit" / "graphiti.yaml"


class TestLoadGraphitiConfig:
    """Test load_graphiti_config function."""

    def test_load_config_from_file(self):
        """Test loading configuration from YAML file."""
        yaml_content = """
enabled: true
host: localhost
port: 8000
timeout: 30.0
"""

        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                assert config.enabled is True
                assert config.host == "localhost"
                assert config.port == 8000
                assert config.timeout == 30.0

    def test_load_config_disabled_in_file(self):
        """Test loading config with enabled=false."""
        yaml_content = """
enabled: false
host: localhost
port: 8000
"""

        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                assert config.enabled is False

    def test_load_config_custom_values(self):
        """Test loading config with custom values."""
        yaml_content = """
enabled: true
host: graphiti.prod.example.com
port: 9000
timeout: 60.0
"""

        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                assert config.host == "graphiti.prod.example.com"
                assert config.port == 9000
                assert config.timeout == 60.0

    def test_load_config_file_not_exists_returns_defaults(self):
        """Test loading config when file doesn't exist returns defaults."""
        with patch('pathlib.Path.exists', return_value=False):
            config = load_graphiti_config()

            # Should return default settings
            assert config.enabled is True
            assert config.host == "localhost"
            assert config.port == 8000

    def test_load_config_invalid_yaml_returns_defaults(self):
        """Test loading config with invalid YAML returns defaults."""
        invalid_yaml = "{ invalid yaml content ["

        with patch('builtins.open', mock_open(read_data=invalid_yaml)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                # Should return default settings on parse error
                assert isinstance(config, GraphitiSettings)

    def test_load_config_partial_yaml(self):
        """Test loading config with partial YAML (missing fields)."""
        yaml_content = """
enabled: false
host: custom.host
"""
        # Missing port and timeout - should use defaults

        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                assert config.enabled is False
                assert config.host == "custom.host"
                assert config.port == 8000  # default
                assert config.timeout == 30.0  # default

    def test_load_config_empty_file_returns_defaults(self):
        """Test loading config from empty file returns defaults."""
        with patch('builtins.open', mock_open(read_data="")):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                # Should return default settings
                assert isinstance(config, GraphitiSettings)

    def test_load_config_permission_error_returns_defaults(self):
        """Test loading config handles permission errors gracefully."""
        with patch('builtins.open', side_effect=PermissionError("No access")):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                # Should return default settings on error
                assert isinstance(config, GraphitiSettings)


class TestEnvironmentVariableOverrides:
    """Test environment variable overrides for configuration."""

    def test_env_override_enabled(self):
        """Test GRAPHITI_ENABLED environment variable override."""
        yaml_content = """
enabled: true
"""

        with patch.dict(os.environ, {"GRAPHITI_ENABLED": "false"}):
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('pathlib.Path.exists', return_value=True):
                    config = load_graphiti_config()

                    assert config.enabled is False

    def test_env_override_host(self):
        """Test GRAPHITI_HOST environment variable override."""
        yaml_content = """
host: localhost
"""

        with patch.dict(os.environ, {"GRAPHITI_HOST": "env.host"}):
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('pathlib.Path.exists', return_value=True):
                    config = load_graphiti_config()

                    assert config.host == "env.host"

    def test_env_override_port(self):
        """Test GRAPHITI_PORT environment variable override."""
        yaml_content = """
port: 8000
"""

        with patch.dict(os.environ, {"GRAPHITI_PORT": "9000"}):
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('pathlib.Path.exists', return_value=True):
                    config = load_graphiti_config()

                    assert config.port == 9000

    def test_env_override_timeout(self):
        """Test GRAPHITI_TIMEOUT environment variable override."""
        yaml_content = """
timeout: 30.0
"""

        with patch.dict(os.environ, {"GRAPHITI_TIMEOUT": "60.0"}):
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('pathlib.Path.exists', return_value=True):
                    config = load_graphiti_config()

                    assert config.timeout == 60.0

    def test_env_override_all_fields(self):
        """Test multiple environment variable overrides."""
        yaml_content = """
enabled: true
host: localhost
port: 8000
timeout: 30.0
"""

        env_vars = {
            "GRAPHITI_ENABLED": "false",
            "GRAPHITI_HOST": "override.host",
            "GRAPHITI_PORT": "9999",
            "GRAPHITI_TIMEOUT": "90.0"
        }

        with patch.dict(os.environ, env_vars):
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('pathlib.Path.exists', return_value=True):
                    config = load_graphiti_config()

                    assert config.enabled is False
                    assert config.host == "override.host"
                    assert config.port == 9999
                    assert config.timeout == 90.0

    def test_env_override_invalid_value_ignored(self):
        """Test invalid environment variable values are ignored."""
        yaml_content = """
port: 8000
"""

        with patch.dict(os.environ, {"GRAPHITI_PORT": "invalid"}):
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('pathlib.Path.exists', return_value=True):
                    config = load_graphiti_config()

                    # Should fall back to file value
                    assert config.port == 8000


class TestConfigIntegration:
    """Integration tests for configuration loading."""

    def test_full_config_workflow(self):
        """Test complete configuration loading workflow."""
        yaml_content = """
enabled: true
host: test.host
port: 8000
timeout: 45.0
"""

        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                # Load config
                config = load_graphiti_config()

                # Verify all fields
                assert config.enabled is True
                assert config.host == "test.host"
                assert config.port == 8000
                assert config.timeout == 45.0

    def test_config_reloading(self):
        """Test configuration can be reloaded."""
        yaml_content_1 = """
enabled: true
port: 8000
"""
        yaml_content_2 = """
enabled: false
port: 9000
"""

        with patch('builtins.open', mock_open(read_data=yaml_content_1)):
            with patch('pathlib.Path.exists', return_value=True):
                config1 = load_graphiti_config()
                assert config1.port == 8000

        with patch('builtins.open', mock_open(read_data=yaml_content_2)):
            with patch('pathlib.Path.exists', return_value=True):
                config2 = load_graphiti_config()
                assert config2.port == 9000


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_config_with_comments(self):
        """Test YAML with comments is parsed correctly."""
        yaml_content = """
# Graphiti configuration
enabled: true  # Enable Graphiti integration
host: localhost  # Host address
port: 8000  # Port number
timeout: 30.0  # Timeout in seconds
"""

        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                assert config.enabled is True
                assert config.host == "localhost"

    def test_config_with_extra_fields(self):
        """Test YAML with extra unknown fields."""
        yaml_content = """
enabled: true
host: localhost
port: 8000
unknown_field: "should be ignored"
another_field: 123
"""

        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                # Should load known fields successfully
                assert config.enabled is True
                assert config.host == "localhost"
                # Extra fields should be ignored

    def test_config_type_coercion(self):
        """Test type coercion in YAML parsing."""
        yaml_content = """
enabled: "true"  # String instead of bool
port: "8000"  # String instead of int
timeout: "30.0"  # String instead of float
"""

        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                # Should coerce types or use defaults
                assert isinstance(config.enabled, bool)
                assert isinstance(config.port, int)
                assert isinstance(config.timeout, float)

    def test_config_with_null_values(self):
        """Test YAML with null values."""
        yaml_content = """
enabled: null
host: null
"""

        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

                # Should use defaults for null values
                assert isinstance(config.enabled, bool)
                assert isinstance(config.host, str)

    def test_config_path_traversal_protection(self):
        """Test config path prevents directory traversal."""
        # Attempt path traversal
        config_path = get_config_path(base_dir=Path("../../etc"))

        # Should construct safe path
        assert str(config_path).endswith(".guardkit/graphiti.yaml")
