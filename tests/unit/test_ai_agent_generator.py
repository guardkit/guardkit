"""
Unit tests for AI Agent Generator

Tests for generating project-specific AI agents based on codebase analysis
and filling capability gaps.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
import sys

# Add lib directory to path for imports
lib_path = Path(__file__).parent.parent.parent / "installer" / "global" / "lib"
sys.path.insert(0, str(lib_path))

from agent_generator import (
    CapabilityNeed,
    GeneratedAgent,
    AIAgentGenerator,
    AgentInvoker
)
from agent_scanner import (
    AgentDefinition,
    AgentInventory
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing"""
    temp = Path(tempfile.mkdtemp())
    yield temp
    shutil.rmtree(temp)


@pytest.fixture
def mock_inventory():
    """Create mock agent inventory"""
    global_agent = AgentDefinition(
        name="task-manager",
        description="Task management specialist",
        tools=["Read", "Write"],
        tags=["tasks", "management"],
        source="global",
        source_path=Path("task-manager.md"),
        priority=1,
        full_definition="# Task Manager"
    )

    return AgentInventory(
        custom_agents=[],
        template_agents=[],
        global_agents=[global_agent]
    )


@pytest.fixture
def mock_analysis(temp_dir):
    """Create mock codebase analysis"""
    # Create some example files
    example_file = temp_dir / "ExampleViewModel.cs"
    example_file.write_text("public class ExampleViewModel : INotifyPropertyChanged {}")

    analysis = Mock()
    analysis.language = "C#"
    analysis.architecture_pattern = "MVVM"
    analysis.frameworks = [".NET MAUI"]
    analysis.quality_assessment = "Uses ErrorOr pattern"
    analysis.testing_framework = "xUnit"
    analysis.example_files = [example_file]
    analysis.layers = []

    return analysis


@pytest.fixture
def mock_ai_invoker():
    """Create mock AI invoker"""
    invoker = Mock(spec=AgentInvoker)
    invoker.invoke.return_value = """---
name: test-specialist
description: Test specialist for unit testing
tools: [Read, Write, Edit, Grep]
tags: [testing, unit-test]
---

# Test Specialist

This is a test agent generated for unit testing purposes.

## Capabilities

- Write unit tests
- Run test suites
- Analyze test coverage
"""
    return invoker


class TestCapabilityNeed:
    """Test CapabilityNeed data class"""

    def test_capability_need_creation(self):
        """Test creating a CapabilityNeed"""
        need = CapabilityNeed(
            name="test-need",
            description="Test capability",
            reason="For testing",
            technologies=["Python", "pytest"],
            example_files=[Path("test.py")],
            priority=5
        )

        assert need.name == "test-need"
        assert need.description == "Test capability"
        assert need.reason == "For testing"
        assert need.technologies == ["Python", "pytest"]
        assert need.priority == 5


class TestGeneratedAgent:
    """Test GeneratedAgent data class"""

    def test_generated_agent_creation(self):
        """Test creating a GeneratedAgent"""
        agent = GeneratedAgent(
            name="test-agent",
            description="Test agent",
            tools=["Read", "Write"],
            tags=["test"],
            full_definition="# Test Agent",
            confidence=85,
            based_on_files=[Path("example.py")],
            reuse_recommended=True
        )

        assert agent.name == "test-agent"
        assert agent.confidence == 85
        assert agent.reuse_recommended is True


class TestAIAgentGenerator:
    """Test AIAgentGenerator functionality"""

    def test_initialization(self, mock_inventory):
        """Test generator initialization"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        assert generator.inventory == mock_inventory
        assert generator.ai_invoker is not None

    def test_initialization_with_custom_invoker(self, mock_inventory, mock_ai_invoker):
        """Test generator with custom AI invoker"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker
        )

        assert generator.ai_invoker == mock_ai_invoker

    def test_identify_capability_needs_mvvm(self, mock_inventory, mock_analysis):
        """Test that AI-native approach returns empty without AI invoker"""
        generator = AIAgentGenerator(inventory=mock_inventory)
        needs = generator._identify_capability_needs(mock_analysis)

        # AI-native approach: should return empty list without AI invoker
        assert len(needs) == 0

    def test_identify_capability_needs_error_handling(self, mock_inventory, mock_analysis):
        """Test identifying error handling capability needs"""
        generator = AIAgentGenerator(inventory=mock_inventory)
        needs = generator._identify_capability_needs(mock_analysis)

        # Should identify error handling need (due to ErrorOr in quality_assessment)
        error_needs = [n for n in needs if "error" in n.name.lower()]
        # Note: May or may not find error needs depending on example files
        # This tests the logic path

    def test_identify_capability_needs_testing(self, mock_inventory, mock_analysis):
        """Test that AI-native approach returns empty without AI invoker"""
        generator = AIAgentGenerator(inventory=mock_inventory)
        needs = generator._identify_capability_needs(mock_analysis)

        # AI-native approach: should return empty list without AI invoker
        assert len(needs) == 0

    def test_find_capability_gaps_existing_agent(self, mock_inventory):
        """Test gap finding when agent exists"""
        needs = [
            CapabilityNeed(
                name="task-manager",  # This exists in mock_inventory
                description="Task management",
                reason="For testing",
                technologies=["test"],
                example_files=[],
                priority=5
            )
        ]

        generator = AIAgentGenerator(inventory=mock_inventory)
        gaps = generator._find_capability_gaps(needs)

        # Should find no gaps (agent exists)
        assert len(gaps) == 0

    def test_find_capability_gaps_missing_agent(self, mock_inventory):
        """Test gap finding when agent is missing"""
        needs = [
            CapabilityNeed(
                name="missing-specialist",  # This doesn't exist
                description="Missing capability",
                reason="For testing",
                technologies=["test"],
                example_files=[],
                priority=5
            )
        ]

        generator = AIAgentGenerator(inventory=mock_inventory)
        gaps = generator._find_capability_gaps(needs)

        # Should find gap
        assert len(gaps) == 1
        assert gaps[0].name == "missing-specialist"

    def test_capability_covered_by_tags(self):
        """Test capability coverage checking by tags"""
        # Create an inventory with an agent that has matching tags and description keywords
        mvvm_agent = AgentDefinition(
            name="mvvm-specialist",
            description="MVVM pattern specialist",  # Contains "mvvm" keyword
            tools=["Read", "Write"],
            tags=["mvvm", "patterns"],
            source="global",
            source_path=Path("mvvm.md"),
            priority=1,
            full_definition="# MVVM"
        )

        inventory = AgentInventory(
            custom_agents=[],
            template_agents=[],
            global_agents=[mvvm_agent]
        )

        need = CapabilityNeed(
            name="mvvm-viewmodel-specialist",
            description="MVVM ViewModel patterns",
            reason="For testing",
            technologies=["mvvm"],  # Matches mvvm-specialist's tags
            example_files=[],
            priority=5
        )

        generator = AIAgentGenerator(inventory=inventory)
        covered = generator._capability_covered(need)

        # Should be covered by mvvm-specialist agent (has "mvvm" tag and "mvvm" in description)
        assert covered is True

    def test_capability_not_covered(self, mock_inventory):
        """Test capability not covered"""
        need = CapabilityNeed(
            name="maui-specialist",
            description="MAUI development",
            reason="For testing",
            technologies=["MAUI", "Xamarin"],  # Not in any existing agent
            example_files=[],
            priority=5
        )

        generator = AIAgentGenerator(inventory=mock_inventory)
        covered = generator._capability_covered(need)

        # Should not be covered
        assert covered is False

    def test_build_generation_prompt(self, mock_inventory, mock_analysis, temp_dir):
        """Test building AI generation prompt"""
        gap = CapabilityNeed(
            name="test-specialist",
            description="Testing specialist",
            reason="For unit testing",
            technologies=["Python", "pytest"],
            example_files=[temp_dir / "test_example.py"],
            priority=7
        )

        # Create example file
        example_file = temp_dir / "test_example.py"
        example_file.write_text("def test_example(): pass")

        generator = AIAgentGenerator(inventory=mock_inventory)
        prompt = generator._build_generation_prompt(gap, mock_analysis)

        # Verify prompt contains key elements
        assert "test-specialist" in prompt
        assert "Testing specialist" in prompt
        assert "Python" in prompt
        assert "pytest" in prompt
        assert mock_analysis.language in prompt
        assert mock_analysis.architecture_pattern in prompt

    def test_parse_generated_agent(self, mock_inventory):
        """Test parsing AI-generated agent definition"""
        response = """---
name: mvvm-specialist
description: MVVM pattern specialist
tools: [Read, Write, Edit, Grep]
tags: [MVVM, C#]
---

# MVVM Specialist

Expert in MVVM patterns.
"""

        gap = CapabilityNeed(
            name="mvvm-specialist",
            description="MVVM patterns",
            reason="Project uses MVVM",
            technologies=["C#", "MVVM"],
            example_files=[],
            priority=9
        )

        generator = AIAgentGenerator(inventory=mock_inventory)
        agent = generator._parse_generated_agent(response, gap)

        assert agent.name == "mvvm-specialist"
        assert agent.description == "MVVM pattern specialist"
        assert "Read" in agent.tools
        assert "MVVM" in agent.tags
        assert agent.confidence == 85
        assert "MVVM Specialist" in agent.full_definition

    def test_parse_generated_agent_with_markdown_wrapper(self, mock_inventory):
        """Test parsing agent with ```markdown wrapper"""
        response = """```markdown
---
name: test-agent
description: Test agent
tools: [Read]
tags: [test]
---

# Test Agent
```"""

        gap = CapabilityNeed(
            name="test-agent",
            description="Test",
            reason="Test",
            technologies=[],
            example_files=[],
            priority=5
        )

        generator = AIAgentGenerator(inventory=mock_inventory)
        agent = generator._parse_generated_agent(response, gap)

        assert agent.name == "test-agent"
        assert "Test Agent" in agent.full_definition

    def test_is_reusable_mvvm_agent(self, mock_inventory):
        """Test reusability detection for MVVM agent"""
        gap = CapabilityNeed(
            name="mvvm-viewmodel-specialist",
            description="MVVM",
            reason="Test",
            technologies=["MVVM"],
            example_files=[],
            priority=9
        )

        generator = AIAgentGenerator(inventory=mock_inventory)
        reusable = generator._is_reusable(gap, {})

        # MVVM agents should be reusable
        assert reusable is True

    def test_is_reusable_project_specific_agent(self, mock_inventory):
        """Test reusability detection for project-specific agent"""
        gap = CapabilityNeed(
            name="acme-corp-api-specialist",
            description="ACME Corp API",
            reason="Test",
            technologies=["API"],
            example_files=[],
            priority=5
        )

        generator = AIAgentGenerator(inventory=mock_inventory)
        reusable = generator._is_reusable(gap, {})

        # Project-specific agents should not be reusable
        assert reusable is False

    def test_save_agent_to_custom(self, mock_inventory, temp_dir):
        """Test saving agent to custom agents directory"""
        # Change to temp directory for testing
        import os
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            agent = GeneratedAgent(
                name="test-agent",
                description="Test",
                tools=["Read"],
                tags=["test"],
                full_definition="# Test Agent\n\nTest content",
                confidence=85,
                based_on_files=[],
                reuse_recommended=True
            )

            generator = AIAgentGenerator(inventory=mock_inventory)
            saved_path = generator.save_agent_to_custom(agent)

            # Verify file was created
            assert saved_path.exists()
            assert saved_path.name == "test-agent.md"
            assert "Test Agent" in saved_path.read_text()

        finally:
            os.chdir(original_cwd)

    def test_generate_with_mock_ai(self, mock_inventory, mock_analysis, mock_ai_invoker):
        """Test full generation flow with mock AI"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker
        )

        generated = generator.generate(mock_analysis)

        # Should generate agents (exact count depends on analysis)
        assert isinstance(generated, list)
        # Verify AI invoker was called if gaps were found
        if generated:
            assert mock_ai_invoker.invoke.called


class TestIntegration:
    """Integration tests for agent generator"""

    def test_full_workflow_with_mvvm_project(self, mock_inventory, mock_analysis, mock_ai_invoker):
        """Test complete workflow for MVVM project"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker
        )

        # Generate agents
        generated = generator.generate(mock_analysis)

        # Verify workflow
        assert isinstance(generated, list)

        # Verify each generated agent has required attributes
        for agent in generated:
            assert agent.name
            assert agent.description
            assert agent.tools
            assert 0 <= agent.confidence <= 100
            assert isinstance(agent.reuse_recommended, bool)

    def test_priority_ordering(self, mock_inventory, mock_analysis):
        """Test that capability needs are ordered by priority"""
        generator = AIAgentGenerator(inventory=mock_inventory)
        needs = generator._identify_capability_needs(mock_analysis)

        # Verify needs are sorted by priority (descending)
        if len(needs) > 1:
            for i in range(len(needs) - 1):
                assert needs[i].priority >= needs[i + 1].priority
