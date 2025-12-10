"""
Unit tests for AI Agent Generator with AI-powered detection

Tests for AI-based agent identification and hard-coded fallback.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, MagicMock, patch
import json
import sys

# Add lib directory to path for imports
lib_path = Path(__file__).parent.parent.parent.parent / "installer" / "core" / "lib"
sys.path.insert(0, str(lib_path))

from agent_generator.agent_generator import (
    CapabilityNeed,
    GeneratedAgent,
    AIAgentGenerator,
    AgentInvoker
)
from agent_scanner.agent_scanner import (
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
    """Create mock codebase analysis for complex project"""
    # Create some example files
    example_file = temp_dir / "ExampleViewModel.cs"
    example_file.write_text("public class ExampleViewModel : INotifyPropertyChanged {}")

    # Create mock layer objects
    domain_layer = Mock()
    domain_layer.name = "Domain"
    domain_layer.patterns = ["Repository", "Service"]
    domain_layer.directories = ["Repositories", "Services"]

    application_layer = Mock()
    application_layer.name = "Application"
    application_layer.patterns = ["Engine", "Orchestrator"]
    application_layer.directories = ["Engines", "Orchestrators"]

    analysis = Mock()
    analysis.language = "C#"
    analysis.architecture_pattern = "Clean Architecture"
    analysis.frameworks = [".NET MAUI", "Realm"]
    analysis.patterns = ["MVVM", "Repository", "Service", "Engine", "ErrorOr"]
    analysis.quality_assessment = "Uses ErrorOr pattern"
    analysis.testing_framework = "xUnit"
    analysis.example_files = [example_file]
    analysis.layers = [domain_layer, application_layer]

    return analysis


@pytest.fixture
def mock_ai_invoker_valid_json():
    """Create mock AI invoker that returns valid JSON"""
    invoker = Mock(spec=AgentInvoker)
    invoker.invoke.return_value = json.dumps([
        {
            "name": "repository-pattern-specialist",
            "description": "Repository pattern with ErrorOr",
            "reason": "Project uses Repository pattern in Domain layer",
            "technologies": ["C#", "Repository Pattern", "ErrorOr"],
            "priority": 9
        },
        {
            "name": "engine-pattern-specialist",
            "description": "Business logic engines",
            "reason": "Project has Application layer with Engines",
            "technologies": ["C#", "Engine Pattern"],
            "priority": 9
        },
        {
            "name": "mvvm-viewmodel-specialist",
            "description": "MVVM ViewModel patterns",
            "reason": "Project uses MVVM architecture",
            "technologies": ["C#", "MVVM", ".NET MAUI"],
            "priority": 8
        }
    ])
    return invoker


@pytest.fixture
def mock_ai_invoker_with_wrapper():
    """Create mock AI invoker that returns JSON with markdown wrapper"""
    invoker = Mock(spec=AgentInvoker)
    response_data = [
        {
            "name": "test-specialist",
            "description": "Testing specialist",
            "reason": "Project uses xUnit",
            "technologies": ["C#", "xUnit"],
            "priority": 7
        }
    ]
    invoker.invoke.return_value = f"```json\n{json.dumps(response_data)}\n```"
    return invoker


@pytest.fixture
def mock_ai_invoker_invalid_json():
    """Create mock AI invoker that returns invalid JSON"""
    invoker = Mock(spec=AgentInvoker)
    invoker.invoke.return_value = "This is not valid JSON at all"
    return invoker


class TestAIAgentIdentification:
    """Test AI-powered agent identification"""

    def test_ai_identifies_multiple_agents(
        self,
        mock_inventory,
        mock_analysis,
        mock_ai_invoker_valid_json
    ):
        """Test AI successfully identifies multiple agents from codebase"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker_valid_json
        )

        needs = generator._ai_identify_all_agents(mock_analysis)

        # Should identify 3 agents from mock response
        assert len(needs) == 3

        # Verify agent names
        names = [n.name for n in needs]
        assert "repository-pattern-specialist" in names
        assert "engine-pattern-specialist" in names
        assert "mvvm-viewmodel-specialist" in names

        # Verify priorities are sorted (descending)
        assert needs[0].priority >= needs[1].priority >= needs[2].priority

        # Verify AI invoker was called with correct agent
        mock_ai_invoker_valid_json.invoke.assert_called_once()
        call_args = mock_ai_invoker_valid_json.invoke.call_args
        assert call_args[1]['agent_name'] == "architectural-reviewer"

    def test_ai_returns_valid_json(
        self,
        mock_inventory,
        mock_analysis,
        mock_ai_invoker_valid_json
    ):
        """Test AI returns valid JSON that parses correctly"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker_valid_json
        )

        needs = generator._ai_identify_all_agents(mock_analysis)

        # Each need should have all required fields
        for need in needs:
            assert need.name
            assert need.description
            assert need.reason
            assert need.technologies
            assert isinstance(need.priority, int)
            assert 1 <= need.priority <= 10

    def test_parse_json_with_markdown_wrapper(
        self,
        mock_inventory,
        mock_analysis,
        mock_ai_invoker_with_wrapper
    ):
        """Test parsing JSON response with ```json wrapper"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker_with_wrapper
        )

        needs = generator._ai_identify_all_agents(mock_analysis)

        # Should successfully parse despite wrapper
        assert len(needs) == 1
        assert needs[0].name == "test-specialist"

    def test_fallback_on_invalid_json(
        self,
        mock_inventory,
        mock_analysis,
        mock_ai_invoker_invalid_json
    ):
        """Test fallback to hard-coded detection on invalid JSON"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker_invalid_json
        )

        # Should fall back to hard-coded detection
        needs = generator._identify_capability_needs(mock_analysis)

        # Hard-coded detection should still return some results
        assert isinstance(needs, list)
        # Should have identified some needs from hard-coded patterns
        # (exact count depends on mock_analysis structure)

    def test_fallback_on_ai_failure(self, mock_inventory, mock_analysis):
        """Test fallback when AI invocation fails"""
        # Create invoker that raises exception
        failing_invoker = Mock(spec=AgentInvoker)
        failing_invoker.invoke.side_effect = Exception("AI service unavailable")

        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=failing_invoker
        )

        # Should fall back gracefully
        needs = generator._identify_capability_needs(mock_analysis)

        # Should return hard-coded results
        assert isinstance(needs, list)

    def test_agent_priority_sorting(
        self,
        mock_inventory,
        mock_analysis,
        mock_ai_invoker_valid_json
    ):
        """Test that agents are sorted by priority (descending)"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker_valid_json
        )

        needs = generator._ai_identify_all_agents(mock_analysis)

        # Verify descending priority order
        for i in range(len(needs) - 1):
            assert needs[i].priority >= needs[i + 1].priority


class TestAIPromptBuilding:
    """Test AI prompt construction"""

    def test_build_comprehensive_prompt(self, mock_inventory, mock_analysis):
        """Test building comprehensive AI prompt"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        prompt = generator._build_ai_analysis_prompt(mock_analysis)

        # Verify all key sections are included
        assert "C#" in prompt
        assert "Clean Architecture" in prompt
        assert "MVVM" in prompt
        assert "Repository" in prompt
        assert "Domain" in prompt
        assert "Application" in prompt
        assert ".NET MAUI" in prompt
        assert "Realm" in prompt
        assert "xUnit" in prompt

        # Verify instructions are clear
        assert "JSON" in prompt
        assert "priority" in prompt.lower()
        assert "technologies" in prompt.lower()

    def test_prompt_includes_layers(self, mock_inventory, mock_analysis):
        """Test that prompt includes layer information"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        prompt = generator._build_ai_analysis_prompt(mock_analysis)

        # Verify layers are described
        assert "Domain" in prompt
        assert "Application" in prompt
        assert "Repository" in prompt
        assert "Service" in prompt
        assert "Engine" in prompt


class TestJSONResponseParsing:
    """Test JSON response parsing"""

    def test_parse_pure_json(self, mock_inventory, mock_analysis):
        """Test parsing pure JSON array"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        response = json.dumps([
            {
                "name": "test-agent",
                "description": "Test",
                "reason": "Testing",
                "technologies": ["Python"],
                "priority": 5
            }
        ])

        needs = generator._parse_ai_agent_response(response, mock_analysis)

        assert len(needs) == 1
        assert needs[0].name == "test-agent"

    def test_parse_json_with_code_block(self, mock_inventory, mock_analysis):
        """Test parsing JSON wrapped in ```json code block"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        response = "```json\n" + json.dumps([
            {
                "name": "wrapped-agent",
                "description": "Test",
                "reason": "Testing",
                "technologies": ["Python"],
                "priority": 5
            }
        ]) + "\n```"

        needs = generator._parse_ai_agent_response(response, mock_analysis)

        assert len(needs) == 1
        assert needs[0].name == "wrapped-agent"

    def test_parse_json_with_plain_code_block(self, mock_inventory, mock_analysis):
        """Test parsing JSON wrapped in ``` code block"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        response = "```\n" + json.dumps([
            {
                "name": "plain-wrapped-agent",
                "description": "Test",
                "reason": "Testing",
                "technologies": ["Python"],
                "priority": 5
            }
        ]) + "\n```"

        needs = generator._parse_ai_agent_response(response, mock_analysis)

        assert len(needs) == 1
        assert needs[0].name == "plain-wrapped-agent"

    def test_parse_invalid_json_raises_error(self, mock_inventory, mock_analysis):
        """Test that invalid JSON raises appropriate error"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        with pytest.raises((ValueError, json.JSONDecodeError)):
            generator._parse_ai_agent_response("not json", mock_analysis)

    def test_parse_non_array_raises_error(self, mock_inventory, mock_analysis):
        """Test that non-array JSON raises error"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        response = json.dumps({"name": "not-an-array"})

        with pytest.raises(ValueError, match="Failed to parse AI agent response"):
            generator._parse_ai_agent_response(response, mock_analysis)


class TestCapabilityNeedCreation:
    """Test creating CapabilityNeed from spec"""

    def test_create_need_from_valid_spec(self, mock_inventory):
        """Test creating CapabilityNeed from valid spec"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        spec = {
            "name": "test-specialist",
            "description": "Test specialist",
            "reason": "Project uses testing",
            "technologies": ["Python", "pytest"],
            "priority": 8
        }

        need = generator._create_capability_need_from_spec(spec, [])

        assert need.name == "test-specialist"
        assert need.description == "Test specialist"
        assert need.reason == "Project uses testing"
        assert need.technologies == ["Python", "pytest"]
        assert need.priority == 8

    def test_create_need_missing_required_field(self, mock_inventory):
        """Test that missing required field raises KeyError"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        spec = {
            "name": "incomplete-specialist",
            "description": "Missing fields"
            # Missing: reason, technologies
        }

        with pytest.raises(KeyError, match="Missing required fields"):
            generator._create_capability_need_from_spec(spec, [])

    def test_create_need_default_priority(self, mock_inventory):
        """Test that missing priority defaults to 7"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        spec = {
            "name": "default-priority",
            "description": "Test",
            "reason": "Testing",
            "technologies": ["Python"]
            # No priority specified
        }

        need = generator._create_capability_need_from_spec(spec, [])

        assert need.priority == 7  # Default value


class TestBackwardCompatibility:
    """Test backward compatibility with hard-coded detection"""

    def test_heuristic_fallback_works(self, mock_inventory, mock_analysis):
        """Test that heuristic fallback detection works"""
        generator = AIAgentGenerator(inventory=mock_inventory)

        needs = generator._heuristic_identify_agents(mock_analysis)

        # Should return some needs based on heuristic patterns
        assert isinstance(needs, list)
        # Should identify at least 3 agents (language, architecture, framework)
        assert len(needs) >= 3

    def test_identify_needs_uses_ai_first(
        self,
        mock_inventory,
        mock_analysis,
        mock_ai_invoker_valid_json
    ):
        """Test that _identify_capability_needs tries AI first"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker_valid_json
        )

        needs = generator._identify_capability_needs(mock_analysis)

        # Should use AI results (3 agents from mock)
        assert len(needs) == 3

        # Verify AI was called
        mock_ai_invoker_valid_json.invoke.assert_called_once()

    def test_identify_needs_falls_back_on_ai_error(
        self,
        mock_inventory,
        mock_analysis
    ):
        """Test that _identify_capability_needs falls back to heuristics on AI error"""
        # Create failing invoker
        failing_invoker = Mock(spec=AgentInvoker)
        failing_invoker.invoke.side_effect = Exception("AI failed")

        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=failing_invoker
        )

        needs = generator._identify_capability_needs(mock_analysis)

        # Should return heuristic results (fallback approach)
        assert isinstance(needs, list)
        # Should have at least 3 agents from heuristic fallback
        assert len(needs) >= 3


class TestIntegration:
    """Integration tests for AI agent generator"""

    def test_full_workflow_with_ai(
        self,
        mock_inventory,
        mock_analysis,
        mock_ai_invoker_valid_json
    ):
        """Test complete workflow with AI agent identification"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker_valid_json
        )

        # Generate agents
        generated = generator.generate(mock_analysis)

        # Should generate agents for gaps
        assert isinstance(generated, list)

        # Verify workflow executed
        mock_ai_invoker_valid_json.invoke.assert_called()

    def test_end_to_end_complex_codebase(
        self,
        mock_inventory,
        mock_analysis,
        mock_ai_invoker_valid_json
    ):
        """Test end-to-end generation for complex codebase"""
        generator = AIAgentGenerator(
            inventory=mock_inventory,
            ai_invoker=mock_ai_invoker_valid_json
        )

        # Run full generation
        generated = generator.generate(mock_analysis)

        # Verify comprehensive agent set
        # (exact count depends on gaps vs existing agents)
        assert isinstance(generated, list)

        # Each generated agent should have all attributes
        for agent in generated:
            assert agent.name
            assert agent.description
            assert agent.tools
            assert 0 <= agent.confidence <= 100
            assert isinstance(agent.reuse_recommended, bool)
