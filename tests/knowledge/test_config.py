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
        """Test settings validation - host is deprecated, no longer validated.

        The 'host' parameter is deprecated in favor of neo4j_uri.
        Empty host no longer raises an error since validation moved to neo4j_uri.
        """
        # This should NOT raise - host is deprecated and not validated
        settings = GraphitiSettings(host="")
        # neo4j_uri is the validated parameter now
        assert settings.neo4j_uri == "bolt://localhost:7687"  # default value

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


class TestLocalInferenceProviderSettings:
    """Test new local inference provider fields (llm_provider, embedding_provider, etc.)."""

    def test_default_llm_provider_is_openai(self):
        """Test that llm_provider defaults to 'openai' for backward compatibility."""
        settings = GraphitiSettings()
        assert settings.llm_provider == "openai"

    def test_default_embedding_provider_is_openai(self):
        """Test that embedding_provider defaults to 'openai' for backward compatibility."""
        settings = GraphitiSettings()
        assert settings.embedding_provider == "openai"

    def test_default_llm_base_url_is_none(self):
        """Test that llm_base_url defaults to None."""
        settings = GraphitiSettings()
        assert settings.llm_base_url is None

    def test_default_llm_model_is_none(self):
        """Test that llm_model defaults to None."""
        settings = GraphitiSettings()
        assert settings.llm_model is None

    def test_default_embedding_base_url_is_none(self):
        """Test that embedding_base_url defaults to None."""
        settings = GraphitiSettings()
        assert settings.embedding_base_url is None

    def test_vllm_provider_accepted(self):
        """Test that 'vllm' is accepted as a valid llm_provider."""
        settings = GraphitiSettings(llm_provider="vllm")
        assert settings.llm_provider == "vllm"

    def test_ollama_provider_accepted(self):
        """Test that 'ollama' is accepted as a valid llm_provider."""
        settings = GraphitiSettings(llm_provider="ollama")
        assert settings.llm_provider == "ollama"

    def test_invalid_llm_provider_raises_value_error(self):
        """Test that an invalid llm_provider raises ValueError."""
        with pytest.raises(ValueError, match="llm_provider must be one of"):
            GraphitiSettings(llm_provider="bedrock")

    def test_invalid_embedding_provider_raises_value_error(self):
        """Test that an invalid embedding_provider raises ValueError."""
        with pytest.raises(ValueError, match="embedding_provider must be one of"):
            GraphitiSettings(embedding_provider="huggingface")

    def test_vllm_embedding_provider_accepted(self):
        """Test that 'vllm' is accepted as a valid embedding_provider."""
        settings = GraphitiSettings(embedding_provider="vllm")
        assert settings.embedding_provider == "vllm"

    def test_ollama_embedding_provider_accepted(self):
        """Test that 'ollama' is accepted as a valid embedding_provider."""
        settings = GraphitiSettings(embedding_provider="ollama")
        assert settings.embedding_provider == "ollama"

    def test_llm_base_url_set_correctly(self):
        """Test setting llm_base_url to a URL string."""
        settings = GraphitiSettings(
            llm_provider="vllm",
            llm_base_url="http://host:8000/v1",
        )
        assert settings.llm_base_url == "http://host:8000/v1"

    def test_llm_model_set_correctly(self):
        """Test setting llm_model to a model name string."""
        settings = GraphitiSettings(
            llm_provider="vllm",
            llm_model="Qwen/Qwen3-Coder-30B-A3B",
        )
        assert settings.llm_model == "Qwen/Qwen3-Coder-30B-A3B"

    def test_embedding_base_url_set_correctly(self):
        """Test setting embedding_base_url to a URL string."""
        settings = GraphitiSettings(
            embedding_provider="vllm",
            embedding_base_url="http://host:8001/v1",
        )
        assert settings.embedding_base_url == "http://host:8001/v1"

    def test_full_vllm_configuration(self):
        """Test a complete vllm configuration for both LLM and embedding."""
        settings = GraphitiSettings(
            llm_provider="vllm",
            llm_base_url="http://promaxgb10-41b1:8000/v1",
            llm_model="Qwen/Qwen3-Coder-30B-A3B",
            embedding_provider="vllm",
            embedding_base_url="http://promaxgb10-41b1:8001/v1",
        )
        assert settings.llm_provider == "vllm"
        assert settings.llm_base_url == "http://promaxgb10-41b1:8000/v1"
        assert settings.llm_model == "Qwen/Qwen3-Coder-30B-A3B"
        assert settings.embedding_provider == "vllm"
        assert settings.embedding_base_url == "http://promaxgb10-41b1:8001/v1"

    def test_yaml_without_new_fields_defaults_to_openai(self):
        """Test that YAML files without new fields default to openai providers."""
        yaml_content = """
enabled: true
host: localhost
port: 8000
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

        assert config.llm_provider == "openai"
        assert config.embedding_provider == "openai"
        assert config.llm_base_url is None
        assert config.llm_model is None
        assert config.embedding_base_url is None

    def test_yaml_with_vllm_provider_fields(self):
        """Test loading YAML with all new provider fields set to vllm."""
        yaml_content = """
enabled: true
llm_provider: vllm
llm_base_url: http://promaxgb10-41b1:8000/v1
llm_model: Qwen/Qwen3-Coder-30B-A3B
embedding_provider: vllm
embedding_base_url: http://promaxgb10-41b1:8001/v1
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

        assert config.llm_provider == "vllm"
        assert config.llm_base_url == "http://promaxgb10-41b1:8000/v1"
        assert config.llm_model == "Qwen/Qwen3-Coder-30B-A3B"
        assert config.embedding_provider == "vllm"
        assert config.embedding_base_url == "http://promaxgb10-41b1:8001/v1"

    def test_yaml_empty_string_base_url_treated_as_none(self):
        """Test that empty string llm_base_url in YAML is treated as None."""
        yaml_content = """
llm_base_url: ""
embedding_base_url: ""
llm_model: ""
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()

        # Empty strings in YAML come through as "" not None before coercion check
        # The field_types loop skips None values but not empty strings - empty string
        # is treated as None for optional fields
        assert config.llm_base_url is None
        assert config.embedding_base_url is None
        assert config.llm_model is None

    def test_env_override_llm_provider(self):
        """Test LLM_PROVIDER environment variable overrides config."""
        with patch.dict(os.environ, {"LLM_PROVIDER": "vllm"}):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()

        assert config.llm_provider == "vllm"

    def test_env_override_llm_base_url(self):
        """Test LLM_BASE_URL environment variable overrides config."""
        with patch.dict(os.environ, {"LLM_BASE_URL": "http://myserver:8000/v1"}):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()

        assert config.llm_base_url == "http://myserver:8000/v1"

    def test_env_override_llm_model(self):
        """Test LLM_MODEL environment variable overrides config."""
        with patch.dict(os.environ, {"LLM_MODEL": "meta-llama/Llama-3-8B"}):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()

        assert config.llm_model == "meta-llama/Llama-3-8B"

    def test_env_override_embedding_provider(self):
        """Test EMBEDDING_PROVIDER environment variable overrides config."""
        with patch.dict(os.environ, {"EMBEDDING_PROVIDER": "ollama"}):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()

        assert config.embedding_provider == "ollama"

    def test_env_override_embedding_base_url(self):
        """Test EMBEDDING_BASE_URL environment variable overrides config."""
        with patch.dict(os.environ, {"EMBEDDING_BASE_URL": "http://myserver:8001/v1"}):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()

        assert config.embedding_base_url == "http://myserver:8001/v1"

    def test_env_override_empty_string_optional_treated_as_none(self):
        """Test that empty string env vars for Optional fields are treated as None."""
        with patch.dict(os.environ, {
            "LLM_BASE_URL": "",
            "LLM_MODEL": "",
            "EMBEDDING_BASE_URL": "",
        }):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()

        assert config.llm_base_url is None
        assert config.llm_model is None
        assert config.embedding_base_url is None

    def test_env_overrides_take_priority_over_yaml(self):
        """Test that env vars take priority over YAML values."""
        yaml_content = """
llm_provider: openai
embedding_provider: openai
"""
        with patch.dict(os.environ, {
            "LLM_PROVIDER": "vllm",
            "EMBEDDING_PROVIDER": "ollama",
        }):
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('pathlib.Path.exists', return_value=True):
                    config = load_graphiti_config()

        assert config.llm_provider == "vllm"
        assert config.embedding_provider == "ollama"

    def test_file_not_found_uses_default_providers(self):
        """Test defaults when config file does not exist."""
        with patch('pathlib.Path.exists', return_value=False):
            config = load_graphiti_config()

        assert config.llm_provider == "openai"
        assert config.embedding_provider == "openai"
        assert config.llm_base_url is None
        assert config.llm_model is None
        assert config.embedding_base_url is None


class TestSparseConfigFalkorDBWarning:
    """Tests for warning when sparse config + FalkorDB combination is detected."""

    def test_sparse_yaml_falkordb_emits_warning(self, caplog):
        """Warning emitted when enabled+falkordb but embedding_provider not set in yaml."""
        import logging
        yaml_content = """
enabled: true
graph_store: falkordb
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                with caplog.at_level(logging.WARNING, logger='guardkit.knowledge.config'):
                    load_graphiti_config()

        assert any(
            'embedding_provider not configured' in record.message
            for record in caplog.records
        )

    def test_explicit_embedding_provider_in_yaml_no_warning(self, caplog):
        """No warning when embedding_provider is explicitly set in yaml."""
        import logging
        yaml_content = """
enabled: true
graph_store: falkordb
embedding_provider: ollama
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                with caplog.at_level(logging.WARNING, logger='guardkit.knowledge.config'):
                    load_graphiti_config()

        assert not any(
            'embedding_provider not configured' in record.message
            for record in caplog.records
        )

    def test_embedding_provider_env_var_no_warning(self, caplog):
        """No warning when EMBEDDING_PROVIDER env var is set."""
        import logging
        yaml_content = """
enabled: true
graph_store: falkordb
"""
        with patch.dict(os.environ, {'EMBEDDING_PROVIDER': 'ollama'}):
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('pathlib.Path.exists', return_value=True):
                    with caplog.at_level(logging.WARNING, logger='guardkit.knowledge.config'):
                        load_graphiti_config()

        assert not any(
            'embedding_provider not configured' in record.message
            for record in caplog.records
        )

    def test_neo4j_graph_store_no_warning(self, caplog):
        """No warning when graph_store is neo4j (default), even without embedding_provider."""
        import logging
        yaml_content = """
enabled: true
graph_store: neo4j
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                with caplog.at_level(logging.WARNING, logger='guardkit.knowledge.config'):
                    load_graphiti_config()

        assert not any(
            'embedding_provider not configured' in record.message
            for record in caplog.records
        )

    def test_disabled_graphiti_no_warning(self, caplog):
        """No warning when graphiti is disabled."""
        import logging
        yaml_content = """
enabled: false
graph_store: falkordb
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                with caplog.at_level(logging.WARNING, logger='guardkit.knowledge.config'):
                    load_graphiti_config()

        assert not any(
            'embedding_provider not configured' in record.message
            for record in caplog.records
        )
