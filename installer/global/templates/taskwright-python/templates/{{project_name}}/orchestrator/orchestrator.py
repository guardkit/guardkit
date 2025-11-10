"""Orchestrator for {{ProjectName}}."""
from typing import Dict, Any

from {{project_name}}.orchestrator.di_container import DIContainer
from {{project_name}}.agents.base_agent import BaseAgent
from {{project_name}}.models.result import WorkflowResult, AgentResult


class Orchestrator:
    """Central orchestrator for workflow coordination.

    The orchestrator coordinates complex workflows by delegating to specialized agents.

    Example:
        ```python
        orchestrator = Orchestrator(container)
        orchestrator.register_agent("analyzer", AnalyzerAgent(container))

        result = orchestrator.execute_workflow(
            "analyze",
            {"path": "src/"}
        )
        ```
    """

    def __init__(self, di_container: DIContainer):
        """Initialize orchestrator with DI container.

        Args:
            di_container: Dependency injection container
        """
        self.container = di_container
        self.agents: Dict[str, BaseAgent] = {}

    def register_agent(self, name: str, agent: BaseAgent) -> None:
        """Register a specialized agent.

        Args:
            name: Agent name for lookup
            agent: Agent instance
        """
        self.agents[name] = agent

    def execute_workflow(
        self,
        workflow_name: str,
        context: Dict[str, Any]
    ) -> WorkflowResult:
        """Execute a workflow by coordinating agents.

        Args:
            workflow_name: Name of workflow to execute
            context: Workflow context and parameters

        Returns:
            WorkflowResult with step results and overall status
        """
        result = WorkflowResult()

        # Example: Simple workflow execution
        # In a real implementation, you would:
        # 1. Load workflow definition
        # 2. Execute each step in sequence
        # 3. Pass context between steps
        # 4. Handle errors and rollback if needed

        try:
            # Placeholder for demonstration
            # Real implementation would load workflow steps and execute them
            result.add_step_result(
                workflow_name,
                {"status": "executed", "context": context}
            )
            return result.mark_success()

        except Exception as e:
            return result.mark_failed(str(e))

    def get_agent(self, agent_name: str) -> BaseAgent:
        """Get a registered agent by name.

        Args:
            agent_name: Name of agent to retrieve

        Returns:
            The agent instance

        Raises:
            ValueError: If agent not found
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agent not found: {agent_name}")
        return self.agents[agent_name]
