"""
Tests for conditional driver creation in GraphitiClient (TASK-FKDB-005).

Tests that initialize() and _check_connection() create either Neo4jDriver
or FalkorDriver based on the graph_store config field.

Coverage Target: >=85%
Test Count: 18 tests

Acceptance Criteria:
- AC-001: initialize() creates FalkorDriver when graph_store=falkordb
- AC-002: initialize() creates Graphiti(graph_driver=driver) for FalkorDB
- AC-003: initialize() still uses Graphiti(uri, user, pwd) for neo4j (backwards compatible)
- AC-004: _check_connection() works with both driver types
- AC-005: GraphitiClientFactory.get_thread_client() creates correct driver type
- AC-006: Each thread gets its own FalkorDriver instance (thread safety)
- AC-007: Log message says "Connected to FalkorDB" or "Connected to Neo4j"
- AC-008: Graceful degradation when falkordb package not installed
- AC-009: Tests for both driver paths, factory thread-safety, missing package
"""

import asyncio
import logging
import os
import threading
import pytest
from unittest.mock import MagicMock, AsyncMock, patch, call

from guardkit.knowledge.graphiti_client import (
    GraphitiConfig,
    GraphitiClient,
    GraphitiClientFactory,
)
import guardkit.knowledge.graphiti_client as graphiti_module


# ============================================================================
# 1. FalkorDB Driver Path in initialize() (5 tests) — AC-001, AC-002, AC-008
# ============================================================================


class TestInitializeFalkorDB:
    """Tests for initialize() with graph_store=falkordb."""

    @pytest.mark.asyncio
    async def test_initialize_creates_falkor_driver(self):
        """AC-001: initialize() creates FalkorDriver when graph_store=falkordb."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            falkordb_host="fdb-host",
            falkordb_port=6380,
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        mock_driver_instance = MagicMock()
        mock_driver_class = MagicMock(return_value=mock_driver_instance)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "guardkit.knowledge.graphiti_client._check_graphiti_core",
                return_value=True,
            ):
                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                        "graphiti_core.driver": MagicMock(),
                        "graphiti_core.driver.falkordb_driver": MagicMock(
                            FalkorDriver=mock_driver_class
                        ),
                    },
                ):
                    result = await client.initialize()

        assert result is True
        assert client._connected is True
        # AC-001: FalkorDriver created with correct host/port
        mock_driver_class.assert_called_once_with(
            host="fdb-host",
            port=6380,
            username=None,  # neo4j_user == "neo4j" → None
            password=None,  # neo4j_password == "password123" → None
        )

    @pytest.mark.asyncio
    async def test_initialize_falkordb_passes_graph_driver(self):
        """AC-002: initialize() creates Graphiti(graph_driver=driver) for FalkorDB."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        mock_driver_instance = MagicMock()
        mock_driver_class = MagicMock(return_value=mock_driver_instance)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "guardkit.knowledge.graphiti_client._check_graphiti_core",
                return_value=True,
            ):
                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                        "graphiti_core.driver": MagicMock(),
                        "graphiti_core.driver.falkordb_driver": MagicMock(
                            FalkorDriver=mock_driver_class
                        ),
                    },
                ):
                    await client.initialize()

        # AC-002: Graphiti created with graph_driver=driver (not uri/user/pwd)
        mock_graphiti_class.assert_called_once_with(graph_driver=mock_driver_instance)

    @pytest.mark.asyncio
    async def test_initialize_falkordb_with_custom_credentials(self):
        """FalkorDriver passes non-default credentials."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            neo4j_user="custom_user",
            neo4j_password="custom_pass",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        mock_driver_instance = MagicMock()
        mock_driver_class = MagicMock(return_value=mock_driver_instance)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "guardkit.knowledge.graphiti_client._check_graphiti_core",
                return_value=True,
            ):
                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                        "graphiti_core.driver": MagicMock(),
                        "graphiti_core.driver.falkordb_driver": MagicMock(
                            FalkorDriver=mock_driver_class
                        ),
                    },
                ):
                    await client.initialize()

        # Non-default credentials are passed through
        mock_driver_class.assert_called_once_with(
            host="localhost",
            port=6379,
            username="custom_user",
            password="custom_pass",
        )

    @pytest.mark.asyncio
    async def test_initialize_falkordb_import_error_graceful_degradation(self):
        """AC-008: Graceful degradation when falkordb package not installed."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
        )
        client = GraphitiClient(config)

        # Make graphiti_core available but falkordb_driver import fail
        mock_graphiti_class = MagicMock()

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "guardkit.knowledge.graphiti_client._check_graphiti_core",
                return_value=True,
            ):
                # Remove falkordb_driver from sys.modules to trigger ImportError
                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                    },
                ):
                    # Patch the import inside initialize to raise ImportError
                    original_import = __builtins__.__import__ if hasattr(__builtins__, '__import__') else __import__

                    def mock_import(name, *args, **kwargs):
                        if name == "graphiti_core.driver.falkordb_driver":
                            raise ImportError("No module named 'falkordb'")
                        return original_import(name, *args, **kwargs)

                    with patch("builtins.__import__", side_effect=mock_import):
                        result = await client.initialize()

        assert result is False
        assert client._connected is False

    @pytest.mark.asyncio
    async def test_initialize_falkordb_import_error_logs_warning(self, caplog):
        """AC-008: Missing falkordb package logs appropriate warning."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
        )
        client = GraphitiClient(config)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "guardkit.knowledge.graphiti_client._check_graphiti_core",
                return_value=True,
            ):
                original_import = __import__

                def mock_import(name, *args, **kwargs):
                    if name == "graphiti_core.driver.falkordb_driver":
                        raise ImportError("No module named 'falkordb'")
                    return original_import(name, *args, **kwargs)

                with patch("builtins.__import__", side_effect=mock_import):
                    with caplog.at_level(logging.WARNING):
                        await client.initialize()

        assert "falkordb package not installed" in caplog.text
        assert "pip install graphiti-core[falkordb]" in caplog.text


# ============================================================================
# 2. Neo4j Backwards Compatibility in initialize() (2 tests) — AC-003
# ============================================================================


class TestInitializeNeo4jBackwardsCompat:
    """Tests that Neo4j path remains unchanged."""

    @pytest.mark.asyncio
    async def test_initialize_neo4j_uses_uri_user_password(self):
        """AC-003: initialize() still uses Graphiti(uri, user, pwd) for neo4j."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="neo4j",
            neo4j_uri="bolt://my-neo4j:7687",
            neo4j_user="admin",
            neo4j_password="secret",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "guardkit.knowledge.graphiti_client._check_graphiti_core",
                return_value=True,
            ):
                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                    },
                ):
                    result = await client.initialize()

        assert result is True
        # AC-003: Neo4j uses positional args (uri, user, pwd)
        mock_graphiti_class.assert_called_once_with(
            "bolt://my-neo4j:7687",
            "admin",
            "secret",
        )

    @pytest.mark.asyncio
    async def test_initialize_default_config_uses_neo4j(self):
        """Default config (graph_store=neo4j) uses the Neo4j path."""
        config = GraphitiConfig(enabled=True)
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "guardkit.knowledge.graphiti_client._check_graphiti_core",
                return_value=True,
            ):
                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                    },
                ):
                    await client.initialize()

        # Default: uri, user, pwd (not graph_driver)
        mock_graphiti_class.assert_called_once_with(
            "bolt://localhost:7687",
            "neo4j",
            "password123",
        )


# ============================================================================
# 3. _check_connection() with Both Drivers (3 tests) — AC-004
# ============================================================================


class TestCheckConnectionBothDrivers:
    """Tests for _check_connection() with neo4j and falkordb."""

    @pytest.mark.asyncio
    async def test_check_connection_neo4j(self):
        """AC-004: _check_connection() works with neo4j driver."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="neo4j",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.close = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        with patch(
            "guardkit.knowledge.graphiti_client._check_graphiti_core",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                },
            ):
                result = await client._check_connection()

        assert result is True
        mock_graphiti_class.assert_called_once_with(
            "bolt://localhost:7687",
            "neo4j",
            "password123",
        )
        mock_graphiti_instance.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_connection_falkordb(self):
        """AC-004: _check_connection() works with falkordb driver."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            falkordb_host="fdb-host",
            falkordb_port=6380,
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.close = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        mock_driver_instance = MagicMock()
        mock_driver_class = MagicMock(return_value=mock_driver_instance)

        with patch(
            "guardkit.knowledge.graphiti_client._check_graphiti_core",
            return_value=True,
        ):
            with patch.dict(
                "sys.modules",
                {
                    "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                    "graphiti_core.driver": MagicMock(),
                    "graphiti_core.driver.falkordb_driver": MagicMock(
                        FalkorDriver=mock_driver_class
                    ),
                },
            ):
                result = await client._check_connection()

        assert result is True
        mock_driver_class.assert_called_once_with(
            host="fdb-host",
            port=6380,
        )
        mock_graphiti_class.assert_called_once_with(graph_driver=mock_driver_instance)

    @pytest.mark.asyncio
    async def test_check_connection_falkordb_import_error(self):
        """AC-004/AC-008: _check_connection() returns False when falkordb not installed."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
        )
        client = GraphitiClient(config)

        with patch(
            "guardkit.knowledge.graphiti_client._check_graphiti_core",
            return_value=True,
        ):
            original_import = __import__

            def mock_import(name, *args, **kwargs):
                if name == "graphiti_core.driver.falkordb_driver":
                    raise ImportError("No module named 'falkordb'")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                result = await client._check_connection()

        assert result is False


# ============================================================================
# 4. Log Messages (2 tests) — AC-007
# ============================================================================


class TestLogMessages:
    """Tests for correct log messages."""

    @pytest.mark.asyncio
    async def test_log_connected_to_falkordb(self, caplog):
        """AC-007: Log says 'Connected to FalkorDB' for falkordb config."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            falkordb_host="fdb-host",
            falkordb_port=6380,
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)
        mock_driver_class = MagicMock(return_value=MagicMock())

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "guardkit.knowledge.graphiti_client._check_graphiti_core",
                return_value=True,
            ):
                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                        "graphiti_core.driver": MagicMock(),
                        "graphiti_core.driver.falkordb_driver": MagicMock(
                            FalkorDriver=mock_driver_class
                        ),
                    },
                ):
                    with caplog.at_level(logging.INFO):
                        await client.initialize()

        assert "Connected to FalkorDB" in caplog.text
        assert "fdb-host:6380" in caplog.text

    @pytest.mark.asyncio
    async def test_log_connected_to_neo4j(self, caplog):
        """AC-007: Log says 'Connected to Neo4j' for neo4j config."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="neo4j",
            neo4j_uri="bolt://neo4j-host:7687",
        )
        client = GraphitiClient(config)

        mock_graphiti_instance = MagicMock()
        mock_graphiti_instance.build_indices_and_constraints = AsyncMock()
        mock_graphiti_class = MagicMock(return_value=mock_graphiti_instance)

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with patch(
                "guardkit.knowledge.graphiti_client._check_graphiti_core",
                return_value=True,
            ):
                with patch.dict(
                    "sys.modules",
                    {
                        "graphiti_core": MagicMock(Graphiti=mock_graphiti_class),
                    },
                ):
                    with caplog.at_level(logging.INFO):
                        await client.initialize()

        assert "Connected to Neo4j" in caplog.text
        assert "bolt://neo4j-host:7687" in caplog.text


# ============================================================================
# 5. Factory Thread-Safety with FalkorDB (4 tests) — AC-005, AC-006
# ============================================================================


class TestFactoryFalkorDBThreadSafety:
    """Tests for factory creating correct driver type per thread."""

    @pytest.fixture(autouse=True)
    def reset_factory(self):
        """Reset module-level factory before/after each test."""
        graphiti_module._factory = None
        graphiti_module._factory_init_attempted = False
        yield
        graphiti_module._factory = None
        graphiti_module._factory_init_attempted = False

    def test_factory_propagates_falkordb_config(self):
        """AC-005: Factory passes falkordb config to created clients."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            falkordb_host="fdb-host",
            falkordb_port=6380,
        )
        factory = GraphitiClientFactory(config)
        client = factory.create_client()

        assert client.config.graph_store == "falkordb"
        assert client.config.falkordb_host == "fdb-host"
        assert client.config.falkordb_port == 6380

    def test_factory_propagates_neo4j_config(self):
        """AC-005: Factory passes neo4j config to created clients."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="neo4j",
            neo4j_uri="bolt://custom:7687",
        )
        factory = GraphitiClientFactory(config)
        client = factory.create_client()

        assert client.config.graph_store == "neo4j"
        assert client.config.neo4j_uri == "bolt://custom:7687"

    def test_each_thread_gets_own_client_instance(self):
        """AC-006: Each thread gets its own client (not shared)."""
        config = GraphitiConfig(enabled=False, graph_store="falkordb")
        factory = GraphitiClientFactory(config)

        clients = {}
        barrier = threading.Barrier(2)

        def worker(name):
            mock = MagicMock(spec=GraphitiClient)
            factory.set_thread_client(mock)
            barrier.wait()
            clients[name] = factory.get_thread_client()

        t1 = threading.Thread(target=worker, args=("t1",))
        t2 = threading.Thread(target=worker, args=("t2",))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Different threads get different instances
        assert clients["t1"] is not clients["t2"]

    @pytest.mark.asyncio
    async def test_factory_create_and_init_falkordb_client(self):
        """AC-005: create_and_init_client initializes with FalkorDB config."""
        config = GraphitiConfig(
            enabled=True,
            graph_store="falkordb",
            falkordb_host="fdb-host",
            falkordb_port=6380,
        )
        factory = GraphitiClientFactory(config)

        mock_client = MagicMock(spec=GraphitiClient)
        mock_client.initialize = AsyncMock(return_value=True)

        with patch.object(factory, "create_client", return_value=mock_client):
            client = await factory.create_and_init_client()

        assert client is mock_client
        mock_client.initialize.assert_called_once()


# ============================================================================
# 6. _try_lazy_init Config Propagation (2 tests)
# ============================================================================


class TestLazyInitConfigPropagation:
    """Tests that lazy init passes graph_store config to factory."""

    @pytest.fixture(autouse=True)
    def reset_factory(self):
        """Reset module-level factory before/after each test."""
        graphiti_module._factory = None
        graphiti_module._factory_init_attempted = False
        yield
        graphiti_module._factory = None
        graphiti_module._factory_init_attempted = False

    def test_lazy_init_passes_falkordb_config(self):
        """_try_lazy_init creates factory with graph_store from settings."""
        from guardkit.knowledge.config import GraphitiSettings

        mock_settings = GraphitiSettings(
            enabled=True,
            graph_store="falkordb",
            falkordb_host="fdb-host",
            falkordb_port=6380,
        )

        with patch(
            "guardkit.knowledge.config.load_graphiti_config",
            return_value=mock_settings,
        ):
            # Mock get_thread_client to avoid actual connection
            with patch.object(
                GraphitiClientFactory,
                "get_thread_client",
                return_value=None,
            ):
                graphiti_module._try_lazy_init()

        factory = graphiti_module._factory
        assert factory is not None
        assert factory.config.graph_store == "falkordb"
        assert factory.config.falkordb_host == "fdb-host"
        assert factory.config.falkordb_port == 6380

    def test_lazy_init_passes_neo4j_config(self):
        """_try_lazy_init creates factory with neo4j config from settings."""
        from guardkit.knowledge.config import GraphitiSettings

        mock_settings = GraphitiSettings(
            enabled=True,
            graph_store="neo4j",
            neo4j_uri="bolt://custom:7687",
        )

        with patch(
            "guardkit.knowledge.config.load_graphiti_config",
            return_value=mock_settings,
        ):
            with patch.object(
                GraphitiClientFactory,
                "get_thread_client",
                return_value=None,
            ):
                graphiti_module._try_lazy_init()

        factory = graphiti_module._factory
        assert factory is not None
        assert factory.config.graph_store == "neo4j"
        assert factory.config.neo4j_uri == "bolt://custom:7687"
