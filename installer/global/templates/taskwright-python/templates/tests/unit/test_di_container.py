"""Unit tests for DI Container."""
import pytest

from {{project_name}}.orchestrator.di_container import DIContainer


def test_register_and_get():
    """Test registering and getting a service."""
    container = DIContainer()
    test_service = "test_value"

    container.register("test", test_service)
    result = container.get("test")

    assert result == test_service


def test_get_nonexistent_service():
    """Test getting non-existent service raises error."""
    container = DIContainer()

    with pytest.raises(ValueError, match="Service not found"):
        container.get("nonexistent")


def test_register_factory():
    """Test factory registration and lazy instantiation."""
    container = DIContainer()
    call_count = 0

    def factory():
        nonlocal call_count
        call_count += 1
        return f"instance_{call_count}"

    container.register_factory("lazy_service", factory)

    # First call creates instance
    instance1 = container.get("lazy_service")
    assert instance1 == "instance_1"
    assert call_count == 1

    # Second call returns cached instance (singleton pattern)
    instance2 = container.get("lazy_service")
    assert instance2 == instance1
    assert call_count == 1  # Factory not called again


def test_has_service():
    """Test checking if service exists."""
    container = DIContainer()

    assert not container.has("test")

    container.register("test", "value")
    assert container.has("test")


def test_clear():
    """Test clearing all services."""
    container = DIContainer()
    container.register("service1", "value1")
    container.register_factory("service2", lambda: "value2")

    assert container.has("service1")
    assert container.has("service2")

    container.clear()

    assert not container.has("service1")
    assert not container.has("service2")
