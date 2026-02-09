"""
Pytest configuration for knowledge module tests.

Sets up necessary environment variables and fixtures for testing
Graphiti client and configuration modules.
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
