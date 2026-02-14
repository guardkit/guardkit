"""
Pytest configuration for knowledge module tests.

Sets up necessary environment variables and fixtures for testing
Graphiti client and configuration modules.

FalkorDB Compatibility:
    Fixtures detect GRAPH_STORE env var to support both Neo4j and FalkorDB.
    Default: graph_store='neo4j' (backwards compatible).
    Set GRAPH_STORE=falkordb + FALKORDB_HOST/FALKORDB_PORT for FalkorDB tests.

Environment Variables:
    GRAPH_STORE: 'neo4j' (default) or 'falkordb'
    FALKORDB_HOST: FalkorDB host (default: 'localhost')
    FALKORDB_PORT: FalkorDB port (default: 6379)
"""

import os
import pytest


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless explicitly requested.

    Integration tests require Graphiti to be running.
    Run with: pytest -m integration --run-integration
    """
    # Check if --run-integration was passed
    if config.getoption("--run-integration", default=False):
        return  # Don't skip integration tests

    skip_integration = pytest.mark.skip(
        reason="Integration tests require --run-integration flag and running Graphiti"
    )
    for item in items:
        if "integration" in item.keywords:
            item.add_marker(skip_integration)


def pytest_addoption(parser):
    """Add --run-integration option to pytest."""
    parser.addoption(
        "--run-integration",
        action="store_true",
        default=False,
        help="Run integration tests (requires Graphiti to be running)"
    )


# Set a dummy OPENAI_API_KEY for tests that don't explicitly clear it.
# This allows tests that mock _check_connection to work without requiring
# the actual API key.
# Tests that need to verify OPENAI_API_KEY checking behavior
# (like test_initialize_missing_openai_api_key) use patch.dict to clear the env.
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment with dummy API keys.

    This fixture runs automatically for all tests in this module.
    Tests can override by using patch.dict(os.environ, {}, clear=True).
    """
    # Only set if not already set (allows CI to provide real key)
    if "OPENAI_API_KEY" not in os.environ:
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-unit-tests")


@pytest.fixture(autouse=True)
def reset_graphiti_singleton():
    """Reset the global Graphiti factory between tests.

    This fixture runs automatically for all tests to ensure clean state.
    The factory is reset to None before each test and restored after.
    """
    # Import here to avoid circular imports
    from guardkit.knowledge import graphiti_client

    # Save current state
    original_factory = graphiti_client._factory

    # Reset before test to ensure clean state
    graphiti_client._factory = None
    graphiti_client._factory_init_attempted = False

    yield

    # Reset after test (don't restore mock objects)
    graphiti_client._factory = None
    graphiti_client._factory_init_attempted = False


@pytest.fixture(autouse=True)
def clear_seeding_markers():
    """Clear seeding markers before and after each test.

    This fixture runs automatically to prevent test pollution from
    marker files created during testing.
    """
    from pathlib import Path

    def clear_marker():
        marker_path = Path.cwd() / ".guardkit" / "seeding" / ".graphiti_seeded.json"
        if marker_path.exists():
            marker_path.unlink()

    # Clear before test
    clear_marker()

    yield

    # Clear after test
    clear_marker()


@pytest.fixture
def graph_store():
    """Return the configured graph store backend.

    Reads GRAPH_STORE env var, defaulting to 'neo4j' for backwards
    compatibility. Use in tests that need to branch on backend type.
    """
    return os.environ.get("GRAPH_STORE", "neo4j")


@pytest.fixture
def falkordb_host():
    """Return the configured FalkorDB host.

    Reads FALKORDB_HOST env var, defaulting to 'localhost'.
    Only meaningful when graph_store='falkordb'.
    """
    return os.environ.get("FALKORDB_HOST", "localhost")


@pytest.fixture
def falkordb_port():
    """Return the configured FalkorDB port as an integer.

    Reads FALKORDB_PORT env var, defaulting to 6379.
    Only meaningful when graph_store='falkordb'.
    """
    return int(os.environ.get("FALKORDB_PORT", "6379"))


@pytest.fixture
def graph_connection_config(graph_store, falkordb_host, falkordb_port):
    """Return a dict with all graph connection parameters.

    Provides a single fixture combining graph_store, neo4j, and falkordb
    connection details for integration tests that need full connection config.
    """
    return {
        "graph_store": graph_store,
        "neo4j_uri": os.environ.get("NEO4J_URI", "bolt://localhost:7687"),
        "neo4j_user": os.environ.get("NEO4J_USER", "neo4j"),
        "neo4j_password": os.environ.get("NEO4J_PASSWORD", "password123"),
        "falkordb_host": falkordb_host,
        "falkordb_port": falkordb_port,
    }


@pytest.fixture(autouse=True)
def reset_falkordb_workaround():
    """Reset the FalkorDB workaround state between tests.

    Prevents test pollution from the module-level _workaround_applied flag
    in falkordb_workaround.py.
    """
    from guardkit.knowledge import falkordb_workaround

    original_applied = falkordb_workaround._workaround_applied
    yield
    falkordb_workaround._workaround_applied = original_applied
