"""
Tests for graph_store config field and FalkorDB connection params (TASK-FKDB-002).

Covers:
- GraphitiSettings: graph_store, falkordb_host, falkordb_port fields
- GraphitiConfig: graph_store, falkordb_host, falkordb_port fields
- load_graphiti_config(): new field defaults, YAML loading, env var overrides
- _try_lazy_init(): propagation of new fields to GraphitiConfig
- Validation: graph_store must be 'neo4j' or 'falkordb'
- Backwards compatibility: existing neo4j_* fields unchanged

Coverage Target: >=85%
"""

import os
import pytest
from unittest.mock import patch, mock_open, MagicMock

from guardkit.knowledge.config import GraphitiSettings, load_graphiti_config
from guardkit.knowledge.graphiti_client import GraphitiConfig


# ============================================================================
# 1. GraphitiSettings - New Fields (8 tests)
# ============================================================================

class TestGraphitiSettingsGraphStore:
    """Test graph_store, falkordb_host, falkordb_port on GraphitiSettings."""

    def test_default_graph_store_is_neo4j(self):
        """AC-001: graph_store defaults to 'neo4j'."""
        settings = GraphitiSettings()
        assert settings.graph_store == "neo4j"

    def test_default_falkordb_host(self):
        """AC-002: falkordb_host defaults to 'localhost'."""
        settings = GraphitiSettings()
        assert settings.falkordb_host == "localhost"

    def test_default_falkordb_port(self):
        """AC-002: falkordb_port defaults to 6379."""
        settings = GraphitiSettings()
        assert settings.falkordb_port == 6379

    def test_graph_store_neo4j_valid(self):
        """graph_store='neo4j' is accepted."""
        settings = GraphitiSettings(graph_store="neo4j")
        assert settings.graph_store == "neo4j"

    def test_graph_store_falkordb_valid(self):
        """graph_store='falkordb' is accepted."""
        settings = GraphitiSettings(graph_store="falkordb")
        assert settings.graph_store == "falkordb"

    def test_graph_store_invalid_raises_value_error(self):
        """graph_store with invalid value raises ValueError."""
        with pytest.raises(ValueError, match="graph_store must be 'neo4j' or 'falkordb'"):
            GraphitiSettings(graph_store="redis")

    def test_custom_falkordb_params(self):
        """Custom FalkorDB host and port are accepted."""
        settings = GraphitiSettings(
            graph_store="falkordb",
            falkordb_host="falkordb.prod.example.com",
            falkordb_port=6380,
        )
        assert settings.falkordb_host == "falkordb.prod.example.com"
        assert settings.falkordb_port == 6380

    def test_falkordb_port_validation(self):
        """falkordb_port must be 1-65535."""
        with pytest.raises(ValueError, match="falkordb_port must be between 1 and 65535"):
            GraphitiSettings(falkordb_port=0)
        with pytest.raises(ValueError, match="falkordb_port must be between 1 and 65535"):
            GraphitiSettings(falkordb_port=70000)


class TestGraphitiSettingsTypeValidation:
    """Test type validation for new fields."""

    def test_graph_store_type_must_be_str(self):
        """graph_store must be str."""
        with pytest.raises(TypeError, match="graph_store must be str"):
            GraphitiSettings(graph_store=123)

    def test_falkordb_host_type_must_be_str(self):
        """falkordb_host must be str."""
        with pytest.raises(TypeError, match="falkordb_host must be str"):
            GraphitiSettings(falkordb_host=123)

    def test_falkordb_port_type_must_be_int(self):
        """falkordb_port must be int (not bool)."""
        with pytest.raises(TypeError, match="falkordb_port must be int"):
            GraphitiSettings(falkordb_port="6379")
        with pytest.raises(TypeError, match="falkordb_port must be int"):
            GraphitiSettings(falkordb_port=True)


# ============================================================================
# 2. GraphitiConfig - New Fields (6 tests)
# ============================================================================

class TestGraphitiConfigGraphStore:
    """Test graph_store, falkordb_host, falkordb_port on GraphitiConfig."""

    def test_default_graph_store_is_neo4j(self):
        """AC-005: GraphitiConfig defaults graph_store to 'neo4j'."""
        config = GraphitiConfig()
        assert config.graph_store == "neo4j"

    def test_default_falkordb_host(self):
        """AC-005: GraphitiConfig defaults falkordb_host to 'localhost'."""
        config = GraphitiConfig()
        assert config.falkordb_host == "localhost"

    def test_default_falkordb_port(self):
        """AC-005: GraphitiConfig defaults falkordb_port to 6379."""
        config = GraphitiConfig()
        assert config.falkordb_port == 6379

    def test_graph_store_falkordb_valid(self):
        """GraphitiConfig accepts graph_store='falkordb'."""
        config = GraphitiConfig(graph_store="falkordb")
        assert config.graph_store == "falkordb"

    def test_graph_store_invalid_raises_value_error(self):
        """GraphitiConfig rejects invalid graph_store."""
        with pytest.raises(ValueError, match="graph_store must be 'neo4j' or 'falkordb'"):
            GraphitiConfig(graph_store="memgraph")

    def test_custom_falkordb_params(self):
        """GraphitiConfig accepts custom FalkorDB params."""
        config = GraphitiConfig(
            graph_store="falkordb",
            falkordb_host="falkordb.example.com",
            falkordb_port=6380,
        )
        assert config.falkordb_host == "falkordb.example.com"
        assert config.falkordb_port == 6380


# ============================================================================
# 3. load_graphiti_config() - New Fields (8 tests)
# ============================================================================

class TestLoadConfigGraphStore:
    """Test load_graphiti_config() with new fields."""

    def test_defaults_without_yaml(self):
        """AC-007: Defaults are correct when no YAML file exists."""
        with patch('pathlib.Path.exists', return_value=False):
            config = load_graphiti_config()
            assert config.graph_store == "neo4j"
            assert config.falkordb_host == "localhost"
            assert config.falkordb_port == 6379

    def test_yaml_graph_store_falkordb(self):
        """AC-007: graph_store loaded from YAML."""
        yaml_content = """
graph_store: falkordb
falkordb_host: fdb.example.com
falkordb_port: 6380
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()
                assert config.graph_store == "falkordb"
                assert config.falkordb_host == "fdb.example.com"
                assert config.falkordb_port == 6380

    def test_yaml_partial_only_graph_store(self):
        """Partial YAML with only graph_store, others use defaults."""
        yaml_content = """
graph_store: falkordb
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()
                assert config.graph_store == "falkordb"
                assert config.falkordb_host == "localhost"
                assert config.falkordb_port == 6379

    def test_yaml_invalid_graph_store_raises(self):
        """Invalid graph_store in YAML propagates ValueError from __post_init__."""
        yaml_content = """
graph_store: redis
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                with pytest.raises(ValueError, match="graph_store must be 'neo4j' or 'falkordb'"):
                    load_graphiti_config()


class TestEnvVarOverridesGraphStore:
    """Test GRAPH_STORE, FALKORDB_HOST, FALKORDB_PORT env var overrides."""

    def test_graph_store_env_override(self):
        """AC-003: GRAPH_STORE env var overrides config."""
        with patch.dict(os.environ, {"GRAPH_STORE": "falkordb"}):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()
                assert config.graph_store == "falkordb"

    def test_falkordb_host_env_override(self):
        """AC-004: FALKORDB_HOST env var overrides config."""
        with patch.dict(os.environ, {"FALKORDB_HOST": "fdb.env.example.com"}):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()
                assert config.falkordb_host == "fdb.env.example.com"

    def test_falkordb_port_env_override(self):
        """AC-004: FALKORDB_PORT env var overrides config."""
        with patch.dict(os.environ, {"FALKORDB_PORT": "6380"}):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()
                assert config.falkordb_port == 6380

    def test_env_overrides_yaml(self):
        """Env vars take precedence over YAML values."""
        yaml_content = """
graph_store: neo4j
falkordb_host: yaml.host
falkordb_port: 6379
"""
        env_vars = {
            "GRAPH_STORE": "falkordb",
            "FALKORDB_HOST": "env.host",
            "FALKORDB_PORT": "6380",
        }
        with patch.dict(os.environ, env_vars):
            with patch('builtins.open', mock_open(read_data=yaml_content)):
                with patch('pathlib.Path.exists', return_value=True):
                    config = load_graphiti_config()
                    assert config.graph_store == "falkordb"
                    assert config.falkordb_host == "env.host"
                    assert config.falkordb_port == 6380

    def test_invalid_falkordb_port_env_ignored(self):
        """Invalid FALKORDB_PORT env var is ignored, keeps default."""
        with patch.dict(os.environ, {"FALKORDB_PORT": "not_a_number"}):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()
                assert config.falkordb_port == 6379


# ============================================================================
# 4. Backwards Compatibility (4 tests)
# ============================================================================

class TestBackwardsCompatibility:
    """AC-006: Existing neo4j_* fields, NEO4J_* env vars, YAML continue to work."""

    def test_neo4j_fields_unchanged(self):
        """neo4j_uri, neo4j_user, neo4j_password defaults still work."""
        settings = GraphitiSettings()
        assert settings.neo4j_uri == "bolt://localhost:7687"
        assert settings.neo4j_user == "neo4j"
        assert settings.neo4j_password == "password123"

    def test_neo4j_env_vars_still_work(self):
        """NEO4J_URI, NEO4J_USER, NEO4J_PASSWORD env vars still work."""
        env_vars = {
            "NEO4J_URI": "bolt://custom:7687",
            "NEO4J_USER": "admin",
            "NEO4J_PASSWORD": "secret",
        }
        with patch.dict(os.environ, env_vars):
            with patch('pathlib.Path.exists', return_value=False):
                config = load_graphiti_config()
                assert config.neo4j_uri == "bolt://custom:7687"
                assert config.neo4j_user == "admin"
                assert config.neo4j_password == "secret"

    def test_neo4j_yaml_still_works(self):
        """neo4j_* YAML config still works."""
        yaml_content = """
neo4j_uri: bolt://yaml:7687
neo4j_user: yaml_user
neo4j_password: yaml_pass
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()
                assert config.neo4j_uri == "bolt://yaml:7687"
                assert config.neo4j_user == "yaml_user"
                assert config.neo4j_password == "yaml_pass"

    def test_new_fields_coexist_with_existing(self):
        """New graph_store fields coexist with existing config."""
        yaml_content = """
enabled: true
neo4j_uri: bolt://prod:7687
neo4j_user: prod_user
neo4j_password: prod_pass
graph_store: falkordb
falkordb_host: fdb.prod
falkordb_port: 6380
timeout: 60.0
"""
        with patch('builtins.open', mock_open(read_data=yaml_content)):
            with patch('pathlib.Path.exists', return_value=True):
                config = load_graphiti_config()
                # Old fields
                assert config.enabled is True
                assert config.neo4j_uri == "bolt://prod:7687"
                assert config.neo4j_user == "prod_user"
                assert config.timeout == 60.0
                # New fields
                assert config.graph_store == "falkordb"
                assert config.falkordb_host == "fdb.prod"
                assert config.falkordb_port == 6380


# ============================================================================
# 5. _try_lazy_init() Propagation (3 tests)
# ============================================================================

class TestLazyInitPropagation:
    """Test that _try_lazy_init propagates new fields to GraphitiConfig."""

    def test_graph_store_propagated(self):
        """graph_store is propagated from settings to config in _try_lazy_init."""
        from guardkit.knowledge import graphiti_client

        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "pass"
        mock_settings.timeout = 30.0
        mock_settings.project_id = None
        mock_settings.graph_store = "falkordb"
        mock_settings.falkordb_host = "fdb.test"
        mock_settings.falkordb_port = 6380

        # Reset module state
        original_factory = graphiti_client._factory
        original_attempted = graphiti_client._factory_init_attempted
        graphiti_client._factory = None
        graphiti_client._factory_init_attempted = False

        try:
            with patch(
                "guardkit.knowledge.config.load_graphiti_config",
                return_value=mock_settings,
            ):
                with patch.object(
                    graphiti_client.GraphitiClientFactory,
                    "get_thread_client",
                    return_value=None,
                ) as mock_get:
                    graphiti_client._try_lazy_init()

                    # Verify factory was created with correct config
                    assert graphiti_client._factory is not None
                    assert graphiti_client._factory.config.graph_store == "falkordb"
                    assert graphiti_client._factory.config.falkordb_host == "fdb.test"
                    assert graphiti_client._factory.config.falkordb_port == 6380
        finally:
            graphiti_client._factory = original_factory
            graphiti_client._factory_init_attempted = original_attempted

    def test_default_graph_store_propagated(self):
        """Default 'neo4j' graph_store propagates correctly."""
        from guardkit.knowledge import graphiti_client

        mock_settings = MagicMock()
        mock_settings.enabled = True
        mock_settings.neo4j_uri = "bolt://localhost:7687"
        mock_settings.neo4j_user = "neo4j"
        mock_settings.neo4j_password = "pass"
        mock_settings.timeout = 30.0
        mock_settings.project_id = None
        mock_settings.graph_store = "neo4j"
        mock_settings.falkordb_host = "localhost"
        mock_settings.falkordb_port = 6379

        original_factory = graphiti_client._factory
        original_attempted = graphiti_client._factory_init_attempted
        graphiti_client._factory = None
        graphiti_client._factory_init_attempted = False

        try:
            with patch(
                "guardkit.knowledge.config.load_graphiti_config",
                return_value=mock_settings,
            ):
                with patch.object(
                    graphiti_client.GraphitiClientFactory,
                    "get_thread_client",
                    return_value=None,
                ):
                    graphiti_client._try_lazy_init()

                    assert graphiti_client._factory is not None
                    assert graphiti_client._factory.config.graph_store == "neo4j"
                    assert graphiti_client._factory.config.falkordb_host == "localhost"
                    assert graphiti_client._factory.config.falkordb_port == 6379
        finally:
            graphiti_client._factory = original_factory
            graphiti_client._factory_init_attempted = original_attempted

    def test_disabled_settings_skip_propagation(self):
        """Disabled settings don't create factory (no propagation needed)."""
        from guardkit.knowledge import graphiti_client

        mock_settings = MagicMock()
        mock_settings.enabled = False

        original_factory = graphiti_client._factory
        original_attempted = graphiti_client._factory_init_attempted
        graphiti_client._factory = None
        graphiti_client._factory_init_attempted = False

        try:
            with patch(
                "guardkit.knowledge.config.load_graphiti_config",
                return_value=mock_settings,
            ):
                result = graphiti_client._try_lazy_init()
                assert result is None
                assert graphiti_client._factory is None
        finally:
            graphiti_client._factory = original_factory
            graphiti_client._factory_init_attempted = original_attempted
