"""Unit tests for Orchestrator."""
import pytest

from {{project_name}}.orchestrator.orchestrator import Orchestrator
from {{project_name}}.orchestrator.di_container import DIContainer
from {{project_name}}.agents.base_agent import BaseAgent
from {{project_name}}.models.result import AgentResult


class MockAgent(BaseAgent):
    """Mock agent for testing."""

    def execute(self, params, context):
        """Execute mock agent."""
        return AgentResult(
            success=True,
            data={"mock": "result"}
        )


def test_orchestrator_initialization(container):
    """Test orchestrator initialization."""
    orch = Orchestrator(container)
    assert orch.container == container
    assert len(orch.agents) == 0


def test_register_agent(orchestrator, container):
    """Test agent registration."""
    agent = MockAgent(container)
    orchestrator.register_agent("mock", agent)

    assert "mock" in orchestrator.agents
    assert orchestrator.get_agent("mock") == agent


def test_get_agent_not_found(orchestrator):
    """Test getting non-existent agent raises error."""
    with pytest.raises(ValueError, match="Agent not found"):
        orchestrator.get_agent("nonexistent")


def test_execute_workflow(orchestrator):
    """Test basic workflow execution."""
    result = orchestrator.execute_workflow(
        "test_workflow",
        {"input": "test"}
    )

    assert result.success
    assert "test_workflow" in result.steps
