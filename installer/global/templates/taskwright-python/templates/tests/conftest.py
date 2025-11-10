"""Pytest configuration and shared fixtures."""
import pytest

from {{project_name}}.orchestrator.di_container import DIContainer
from {{project_name}}.orchestrator.orchestrator import Orchestrator


@pytest.fixture
def container():
    """Create a DI container for testing.

    Returns:
        DIContainer instance
    """
    container = DIContainer()
    # Register test services here
    return container


@pytest.fixture
def orchestrator(container):
    """Create an orchestrator for testing.

    Args:
        container: DI container fixture

    Returns:
        Orchestrator instance
    """
    return Orchestrator(container)
