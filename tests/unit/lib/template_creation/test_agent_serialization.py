"""
Unit tests for agent serialization methods.

Tests _serialize_agents() and _deserialize_agents() using updated _serialize_value().

TASK-PHASE-7-5-FIX-FOUNDATION: DRY improvement with _serialize_value()
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent.parent.parent / "installer" / "global"
commands_lib_path = lib_path / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))
if str(commands_lib_path) not in sys.path:
    sys.path.insert(0, str(commands_lib_path))


def import_module_from_path(module_name, file_path):
    """Import a module directly from file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


orchestrator_module = import_module_from_path(
    "template_create_orchestrator",
    commands_lib_path / "template_create_orchestrator.py"
)

TemplateCreateOrchestrator = orchestrator_module.TemplateCreateOrchestrator
OrchestrationConfig = orchestrator_module.OrchestrationConfig


# ========== Test Fixtures ==========

@pytest.fixture
def mock_config():
    """Mock orchestration configuration."""
    config = Mock(spec=OrchestrationConfig)
    config.verbose = False
    return config


@pytest.fixture
def mock_orchestrator(mock_config):
    """Create a mock orchestrator instance."""
    with patch.object(TemplateCreateOrchestrator, '__init__', lambda self, *args, **kwargs: None):
        orchestrator = TemplateCreateOrchestrator(mock_config)
        orchestrator.config = mock_config
        return orchestrator


# ========== Test Fixtures: Agent Objects ==========

class SimpleAgent:
    """Simple agent class (not Mock) to avoid recursion."""
    def __init__(self, name="test-agent"):
        self.name = name
        self.description = "Test agent for validation"
        self.priority = 7
        self.tags = ["python", "testing"]
        self.created_at = datetime(2024, 1, 15, 10, 30, 45)
        self.base_path = Path("/home/user")


class ComplexAgent:
    """Complex agent with nested structures."""
    def __init__(self):
        self.name = "complex-agent"
        self.description = "Complex test agent"
        self.priority = 8
        self.tags = ["python", "integration", "testing"]
        self.created_at = datetime(2024, 1, 15, 10, 30, 45)
        self.base_path = Path("/home/user/projects")
        self.config = {
            "timeout": 30,
            "retries": 3,
            "paths": [Path("/tmp"), Path("/home/user")],
            "created_at": datetime(2024, 1, 15, 10, 30, 45)
        }
        self.metadata = {
            "version": "1.0",
            "language": "python",
            "path": Path("/agents/complex")
        }


# ========== Unit Tests: Serialize Agents ==========

class TestSerializeAgents:
    """Test _serialize_agents() method."""

    def test_serialize_single_agent(self, mock_orchestrator):
        """Test serialization of single agent."""
        agents = [SimpleAgent()]
        result = mock_orchestrator._serialize_agents(agents)

        assert result is not None
        assert "agents" in result
        assert len(result["agents"]) == 1

    def test_serialize_multiple_agents(self, mock_orchestrator):
        """Test serialization of multiple agents."""
        agents = [SimpleAgent() for _ in range(3)]
        result = mock_orchestrator._serialize_agents(agents)

        assert "agents" in result
        assert len(result["agents"]) == 3

    def test_serialize_empty_agent_list(self, mock_orchestrator):
        """Test serialization of empty agent list."""
        result = mock_orchestrator._serialize_agents([])

        assert result is None

    def test_serialize_none_agents(self, mock_orchestrator):
        """Test serialization of None agents."""
        result = mock_orchestrator._serialize_agents(None)

        assert result is None

    def test_serialized_agent_contains_attributes(self, mock_orchestrator):
        """Test agent attributes are serialized."""
        agents = [SimpleAgent()]
        result = mock_orchestrator._serialize_agents(agents)

        serialized_agent = result["agents"][0]
        assert "name" in serialized_agent
        assert "description" in serialized_agent
        assert "priority" in serialized_agent
        assert "tags" in serialized_agent

    def test_serializes_complex_structures(self, mock_orchestrator):
        """Test complex agent with nested structures."""
        agents = [ComplexAgent()]
        result = mock_orchestrator._serialize_agents(agents)

        serialized_agent = result["agents"][0]

        # Verify Path objects converted to strings
        assert serialized_agent["base_path"] == "/home/user/projects"

        # Verify datetime objects converted to ISO format
        assert "2024-01-15" in serialized_agent["created_at"]

        # Verify nested structures handled
        assert isinstance(serialized_agent["config"], dict)
        assert serialized_agent["config"]["paths"][0] == "/tmp"


# ========== Unit Tests: Deserialize Agents ==========

class TestDeserializeAgents:
    """Test _deserialize_agents() method."""

    def test_deserialize_none(self, mock_orchestrator):
        """Test deserializing None returns empty list."""
        result = mock_orchestrator._deserialize_agents(None)

        assert result == []
        assert isinstance(result, list)

    def test_deserialize_empty_dict(self, mock_orchestrator):
        """Test deserializing empty dict returns empty list."""
        result = mock_orchestrator._deserialize_agents({})

        assert result == []

    def test_deserialize_single_agent(self, mock_orchestrator):
        """Test deserializing single agent."""
        # First serialize
        agents = [SimpleAgent()]
        serialized = mock_orchestrator._serialize_agents(agents)

        # Then deserialize
        result = mock_orchestrator._deserialize_agents(serialized)

        assert len(result) == 1
        agent = result[0]
        assert agent.name == "test-agent"
        assert agent.description == "Test agent for validation"

    def test_deserialize_multiple_agents(self, mock_orchestrator):
        """Test deserializing multiple agents."""
        agents = [SimpleAgent() for _ in range(2)]
        serialized = mock_orchestrator._serialize_agents(agents)

        result = mock_orchestrator._deserialize_agents(serialized)

        assert len(result) == 2
        assert all(hasattr(a, "name") for a in result)

    def test_deserialize_preserves_attributes(self, mock_orchestrator):
        """Test deserialized agents have all attributes."""
        agents = [SimpleAgent()]
        serialized = mock_orchestrator._serialize_agents(agents)

        result = mock_orchestrator._deserialize_agents(serialized)
        agent = result[0]

        # Deserialized objects have serialized values
        assert agent.name == "test-agent"
        assert agent.priority == 7

    def test_deserialize_handles_list_values(self, mock_orchestrator):
        """Test deserialized agents with list attributes."""
        agents = [SimpleAgent()]
        serialized = mock_orchestrator._serialize_agents(agents)

        result = mock_orchestrator._deserialize_agents(serialized)
        agent = result[0]

        # Tags should be preserved as list
        assert hasattr(agent, "tags")
        assert isinstance(agent.tags, list)


# ========== Integration Tests: Round-Trip ==========

class TestAgentSerializationRoundTrip:
    """Test serialize-deserialize round-trip consistency."""

    def test_simple_agent_round_trip(self, mock_orchestrator):
        """Test simple agent survives round-trip."""
        agents = [SimpleAgent()]

        # Round trip
        serialized = mock_orchestrator._serialize_agents(agents)
        deserialized = mock_orchestrator._deserialize_agents(serialized)

        # Verify key attributes preserved
        assert deserialized[0].name == "test-agent"
        assert deserialized[0].description == "Test agent for validation"

    def test_complex_agent_round_trip(self, mock_orchestrator):
        """Test complex agent with nested structures survives round-trip."""
        agents = [ComplexAgent()]

        serialized = mock_orchestrator._serialize_agents(agents)
        deserialized = mock_orchestrator._deserialize_agents(serialized)

        agent = deserialized[0]
        assert agent.name == "complex-agent"
        assert agent.priority == 8

    def test_agent_list_round_trip(self, mock_orchestrator):
        """Test list of agents survives round-trip."""
        agents = [SimpleAgent() for _ in range(5)]

        serialized = mock_orchestrator._serialize_agents(agents)
        deserialized = mock_orchestrator._deserialize_agents(serialized)

        assert len(deserialized) == len(agents)
        assert all(hasattr(a, "name") for a in deserialized)

    def test_json_serializable(self, mock_orchestrator):
        """Test serialized agents are JSON-serializable."""
        import json

        agents = [SimpleAgent()]
        serialized = mock_orchestrator._serialize_agents(agents)

        # Should not raise exception
        json_str = json.dumps(serialized)
        assert isinstance(json_str, str)


# ========== Unit Tests: Edge Cases ==========

class TestAgentSerializationEdgeCases:
    """Test edge cases for agent serialization."""

    def test_agent_with_none_attributes(self, mock_orchestrator):
        """Test agent with None attributes."""
        class MinimalAgent:
            def __init__(self):
                self.name = "test"
                self.description = None
                self.tags = None
                self.created_at = None

        agents = [MinimalAgent()]
        result = mock_orchestrator._serialize_agents(agents)

        serialized = result["agents"][0]
        assert serialized["description"] is None
        assert serialized["tags"] is None

    def test_agent_with_empty_collections(self, mock_orchestrator):
        """Test agent with empty collections."""
        class AgentWithEmpty:
            def __init__(self):
                self.name = "test"
                self.tags = []
                self.paths = {}

        agents = [AgentWithEmpty()]
        result = mock_orchestrator._serialize_agents(agents)

        serialized = result["agents"][0]
        assert serialized["tags"] == []
        assert serialized["paths"] == {}

    def test_agent_with_special_characters(self, mock_orchestrator):
        """Test agent with special characters in attributes."""
        class SpecialAgent:
            def __init__(self):
                self.name = "test-agent_v2"
                self.description = "Test with special chars: !@#$%^&*()"
                self.tags = ["python-3.11", "testing_framework"]

        agents = [SpecialAgent()]
        result = mock_orchestrator._serialize_agents(agents)

        serialized = result["agents"][0]
        assert "special chars" in serialized["description"]
        assert "python-3.11" in serialized["tags"]

    def test_agent_with_large_lists(self, mock_orchestrator):
        """Test agent with large tag list."""
        class LargeAgent:
            def __init__(self):
                self.name = "test"
                self.tags = [f"tag-{i}" for i in range(100)]

        agents = [LargeAgent()]
        result = mock_orchestrator._serialize_agents(agents)

        serialized = result["agents"][0]
        assert len(serialized["tags"]) == 100


# ========== DRY Principle Tests ==========

class TestAgentSerializationDRY:
    """Test DRY principle in agent serialization."""

    def test_uses_serialize_value_for_consistency(self, mock_orchestrator):
        """Test _serialize_agents uses _serialize_value consistently."""
        agents = [ComplexAgent()]
        result = mock_orchestrator._serialize_agents(agents)

        # All Path objects should be strings (via _serialize_value)
        agent_dict = result["agents"][0]

        # Direct attributes
        if "base_path" in agent_dict:
            assert isinstance(agent_dict["base_path"], str)

        # Nested in config dict
        if "config" in agent_dict and isinstance(agent_dict["config"], dict):
            if "paths" in agent_dict["config"]:
                for path in agent_dict["config"]["paths"]:
                    assert isinstance(path, str)

    def test_centralizes_serialization_logic(self, mock_orchestrator):
        """Test serialization logic is centralized."""
        # Should use same _serialize_value logic as other serialize methods
        class DateAgent:
            def __init__(self):
                self.name = "test"
                self.created_at = datetime(2024, 1, 15)

        agents = [DateAgent()]
        result = mock_orchestrator._serialize_agents(agents)

        # Datetime should be ISO format (via _serialize_value)
        agent_dict = result["agents"][0]
        assert "2024-01-15" in agent_dict["created_at"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
