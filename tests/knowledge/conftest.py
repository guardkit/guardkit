"""
Pytest configuration for knowledge module tests.

Sets up necessary environment variables and fixtures for testing
surviving knowledge modules (fleet-memory client, ADR service, entities, etc.).
"""

import os
import pytest


def pytest_collection_modifyitems(config, items):
    """Skip integration tests unless explicitly requested.

    Run with: pytest -m integration --run-integration
    """
    # Check if --run-integration was passed
    if config.getoption("--run-integration", default=False):
        return  # Don't skip integration tests

    skip_integration = pytest.mark.skip(
        reason="Integration tests require --run-integration flag"
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
        help="Run integration tests"
    )


# Set a dummy OPENAI_API_KEY for tests that don't explicitly clear it.
# This allows tests that mock connection checks to work without requiring
# the actual API key.
@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch):
    """Set up test environment with dummy API keys.

    This fixture runs automatically for all tests in this module.
    Tests can override by using patch.dict(os.environ, {}, clear=True).
    """
    # Only set if not already set (allows CI to provide real key)
    if "OPENAI_API_KEY" not in os.environ:
        monkeypatch.setenv("OPENAI_API_KEY", "test-api-key-for-unit-tests")
