"""Integration tests for clarification-questioner agent discovery.

Tests verify that the clarification-questioner agent is properly installed
and has the required metadata for the agent discovery system.

These are smoke tests - they verify the agent file exists and has correct
structure, not the actual behavior of the agent.
"""

import pytest
from pathlib import Path
import yaml
import re


class TestClarificationAgentExists:
    """Test that clarification-questioner agent file exists and is readable."""

    def test_clarification_agent_exists_in_installer(self):
        """Verify clarification-questioner agent exists in installer/core/agents/."""
        agent_path = Path(__file__).resolve().parents[4] / "installer" / "core" / "agents" / "clarification-questioner.md"
        assert agent_path.exists(), f"Agent file not found at {agent_path}"
        assert agent_path.is_file(), f"Agent path is not a file: {agent_path}"

        content = agent_path.read_text()
        assert len(content) > 0, "Agent file is empty"

    def test_agent_file_has_frontmatter(self):
        """Verify agent file has YAML frontmatter."""
        agent_path = Path(__file__).resolve().parents[4] / "installer" / "core" / "agents" / "clarification-questioner.md"
        content = agent_path.read_text()

        # Check for YAML frontmatter markers
        assert content.startswith("---"), "Agent file does not start with YAML frontmatter"

        # Extract frontmatter
        parts = content.split("---", 2)
        assert len(parts) >= 3, "Agent file does not have valid YAML frontmatter structure"

        # Parse YAML (should not raise)
        frontmatter = yaml.safe_load(parts[1])
        assert frontmatter is not None, "Frontmatter could not be parsed"


class TestClarificationAgentFrontmatter:
    """Test that clarification-questioner agent has required frontmatter fields."""

    @pytest.fixture
    def agent_frontmatter(self) -> dict:
        """Load agent frontmatter."""
        agent_path = Path(__file__).resolve().parents[4] / "installer" / "core" / "agents" / "clarification-questioner.md"
        content = agent_path.read_text()
        parts = content.split("---", 2)
        return yaml.safe_load(parts[1])

    def test_has_name_field(self, agent_frontmatter: dict):
        """Verify agent has name field."""
        assert "name" in agent_frontmatter, "Agent missing 'name' field"
        assert agent_frontmatter["name"] == "clarification-questioner", f"Expected name 'clarification-questioner', got '{agent_frontmatter['name']}'"

    def test_has_description_field(self, agent_frontmatter: dict):
        """Verify agent has description field."""
        assert "description" in agent_frontmatter, "Agent missing 'description' field"
        assert len(agent_frontmatter["description"]) > 0, "Agent description is empty"

    def test_has_tools_field(self, agent_frontmatter: dict):
        """Verify agent has tools specification."""
        assert "tools" in agent_frontmatter, "Agent missing 'tools' field"
        tools = agent_frontmatter["tools"]
        # Tools can be a string or list
        if isinstance(tools, str):
            assert "Python" in tools or "Read" in tools or "Write" in tools, \
                f"Agent should specify relevant tools, got: {tools}"
        elif isinstance(tools, list):
            assert any(t in tools for t in ["Python", "Read", "Write", "Bash"]), \
                f"Agent should specify relevant tools, got: {tools}"

    def test_has_model_field(self, agent_frontmatter: dict):
        """Verify agent specifies model."""
        assert "model" in agent_frontmatter, "Agent missing 'model' field"
        assert agent_frontmatter["model"] in ["sonnet", "haiku", "opus"], \
            f"Agent model should be sonnet/haiku/opus, got: {agent_frontmatter['model']}"


class TestClarificationAgentDiscoveryMetadata:
    """Test that clarification-questioner agent has discovery metadata."""

    @pytest.fixture
    def agent_frontmatter(self) -> dict:
        """Load agent frontmatter."""
        agent_path = Path(__file__).resolve().parents[4] / "installer" / "core" / "agents" / "clarification-questioner.md"
        content = agent_path.read_text()
        parts = content.split("---", 2)
        return yaml.safe_load(parts[1])

    def test_has_stack_field(self, agent_frontmatter: dict):
        """Verify agent has stack field for discovery."""
        assert "stack" in agent_frontmatter, "Agent missing 'stack' field for discovery"
        stack = agent_frontmatter["stack"]
        assert isinstance(stack, list), f"Stack should be a list, got: {type(stack)}"
        assert "cross-stack" in stack, f"Clarification agent should be cross-stack, got: {stack}"

    def test_has_phase_field(self, agent_frontmatter: dict):
        """Verify agent has phase field for discovery."""
        assert "phase" in agent_frontmatter, "Agent missing 'phase' field for discovery"
        assert agent_frontmatter["phase"] == "orchestration", \
            f"Clarification agent should be in 'orchestration' phase, got: {agent_frontmatter['phase']}"

    def test_has_capabilities_field(self, agent_frontmatter: dict):
        """Verify agent has capabilities for discovery."""
        assert "capabilities" in agent_frontmatter, "Agent missing 'capabilities' field for discovery"
        capabilities = agent_frontmatter["capabilities"]
        assert isinstance(capabilities, list), f"Capabilities should be a list, got: {type(capabilities)}"
        assert len(capabilities) > 0, "Agent should have at least one capability"

    def test_has_keywords_field(self, agent_frontmatter: dict):
        """Verify agent has keywords for discovery matching."""
        assert "keywords" in agent_frontmatter, "Agent missing 'keywords' field for discovery"
        keywords = agent_frontmatter["keywords"]
        assert isinstance(keywords, list), f"Keywords should be a list, got: {type(keywords)}"

        # Check for expected keywords
        expected_keywords = ["clarification", "questions"]
        for kw in expected_keywords:
            assert kw in keywords, f"Agent missing expected keyword: {kw}"


class TestClarificationAgentCollaboration:
    """Test that clarification-questioner agent documents collaboration."""

    @pytest.fixture
    def agent_frontmatter(self) -> dict:
        """Load agent frontmatter."""
        agent_path = Path(__file__).resolve().parents[4] / "installer" / "core" / "agents" / "clarification-questioner.md"
        content = agent_path.read_text()
        parts = content.split("---", 2)
        return yaml.safe_load(parts[1])

    def test_has_collaborates_with_field(self, agent_frontmatter: dict):
        """Verify agent documents collaboration with other agents."""
        assert "collaborates_with" in agent_frontmatter, "Agent missing 'collaborates_with' field"
        collaborators = agent_frontmatter["collaborates_with"]
        assert isinstance(collaborators, list), f"collaborates_with should be a list, got: {type(collaborators)}"

    def test_collaborates_with_task_manager(self, agent_frontmatter: dict):
        """Verify agent collaborates with task-manager."""
        collaborators = agent_frontmatter.get("collaborates_with", [])
        assert "task-manager" in collaborators, \
            f"Clarification agent should collaborate with task-manager, got: {collaborators}"

    def test_has_priority_field(self, agent_frontmatter: dict):
        """Verify agent has priority field."""
        assert "priority" in agent_frontmatter, "Agent missing 'priority' field"


class TestClarificationAgentContent:
    """Test that clarification-questioner agent has expected content structure."""

    @pytest.fixture
    def agent_content(self) -> str:
        """Load agent content."""
        agent_path = Path(__file__).resolve().parents[4] / "installer" / "core" / "agents" / "clarification-questioner.md"
        return agent_path.read_text()

    def test_has_context_parameter_section(self, agent_content: str):
        """Verify agent documents context parameter."""
        assert "## Context Parameter" in agent_content or "Context Parameter" in agent_content, \
            "Agent should document context parameter"

    def test_has_decision_boundaries_section(self, agent_content: str):
        """Verify agent has ALWAYS/NEVER/ASK boundaries."""
        assert "### ALWAYS" in agent_content or "ALWAYS" in agent_content, \
            "Agent should have ALWAYS boundaries"
        assert "### NEVER" in agent_content or "NEVER" in agent_content, \
            "Agent should have NEVER boundaries"

    def test_documents_three_context_types(self, agent_content: str):
        """Verify agent documents all three context types."""
        context_types = ["review_scope", "implementation_prefs", "implementation_planning"]
        for ctx in context_types:
            assert ctx in agent_content, f"Agent should document context type: {ctx}"

    def test_has_python_code_examples(self, agent_content: str):
        """Verify agent includes Python code examples."""
        assert "```python" in agent_content, "Agent should include Python code examples"
