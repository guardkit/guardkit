"""Dependency Injection Container for {{ProjectName}}."""
from typing import Any, Callable, Dict, Type, TypeVar

T = TypeVar("T")


class DIContainer:
    """Simple dependency injection container.

    Supports both instance registration and factory-based lazy initialization.

    Example:
        ```python
        container = DIContainer()

        # Register instance
        container.register("config", Config())

        # Register factory (lazy)
        container.register_factory("service", lambda: Service(container))

        # Resolve
        service = container.get("service")
        ```
    """

    def __init__(self):
        """Initialize empty container."""
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}

    def register(self, name: str, service: Any) -> None:
        """Register a service instance.

        Args:
            name: Service name for lookup
            service: Service instance to register
        """
        self._services[name] = service

    def register_factory(self, name: str, factory: Callable[[], Any]) -> None:
        """Register a factory function for lazy instantiation.

        The factory is called only once, on first access. The instance is then cached.

        Args:
            name: Service name for lookup
            factory: Factory function that creates the service
        """
        self._factories[name] = factory

    def get(self, name: str) -> Any:
        """Resolve a service by name.

        Args:
            name: Service name to resolve

        Returns:
            The service instance

        Raises:
            ValueError: If service not found
        """
        # Return cached instance if exists
        if name in self._services:
            return self._services[name]

        # Create from factory if available
        if name in self._factories:
            service = self._factories[name]()
            self._services[name] = service  # Cache it
            return service

        raise ValueError(f"Service not found: {name}")

    def get_typed(self, service_type: Type[T]) -> T:
        """Resolve a service by type.

        Args:
            service_type: Type of service to resolve

        Returns:
            The service instance

        Raises:
            ValueError: If service not found
        """
        name = service_type.__name__
        return self.get(name)

    def has(self, name: str) -> bool:
        """Check if a service is registered.

        Args:
            name: Service name to check

        Returns:
            True if service is registered, False otherwise
        """
        return name in self._services or name in self._factories

    def clear(self) -> None:
        """Clear all registered services and factories."""
        self._services.clear()
        self._factories.clear()
