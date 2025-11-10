"""Base agent class for {{ProjectName}}."""
from abc import ABC, abstractmethod
from typing import Any, Dict

from {{project_name}}.orchestrator.di_container import DIContainer
from {{project_name}}.models.result import AgentResult


class BaseAgent(ABC):
    """Base class for all agents.

    Agents are specialized components that perform specific tasks within workflows.
    They have access to the DI container for resolving dependencies.

    Example:
        ```python
        class MyAgent(BaseAgent):
            async def execute(self, params, context):
                config = self.get_service("config")
                # Perform task
                return AgentResult(
                    success=True,
                    data={"result": "value"}
                )
        ```
    """

    def __init__(self, container: DIContainer):
        """Initialize agent with DI container.

        Args:
            container: Dependency injection container
        """
        self.container = container

    @abstractmethod
    def execute(
        self,
        params: Dict[str, Any],
        context: Dict[str, Any]
    ) -> AgentResult:
        """Execute the agent's task.

        Args:
            params: Parameters specific to this execution
            context: Shared context across workflow

        Returns:
            AgentResult with success status and data/error
        """
        pass

    def get_service(self, name: str) -> Any:
        """Get a service from the DI container.

        Args:
            name: Service name

        Returns:
            The service instance
        """
        return self.container.get(name)
