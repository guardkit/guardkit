"""
Integration tests for AI Agent Generator

Tests end-to-end workflow with realistic codebase analysis scenarios.
"""

import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock, patch
import json
import sys

# Add lib directory to path for imports
lib_path = Path(__file__).parent.parent.parent / "installer" / "global" / "lib"
sys.path.insert(0, str(lib_path))

from agent_generator.agent_generator import (
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
def minimal_inventory():
    """Create minimal agent inventory (only global agents)"""
    return AgentInventory(
        custom_agents=[],
        template_agents=[],
        global_agents=[]
    )


@pytest.fixture
def complex_maui_analysis(temp_dir):
    """Create realistic analysis for complex .NET MAUI Clean Architecture project"""
    # Create example files
    viewmodel_file = temp_dir / "HomeViewModel.cs"
    viewmodel_file.write_text("""
    public class HomeViewModel : BaseViewModel
    {
        private INotifyPropertyChanged _property;
        public string Title { get; set; }
    }
    """)

    repository_file = temp_dir / "UserRepository.cs"
    repository_file.write_text("""
    public class UserRepository : IUserRepository
    {
        public ErrorOr<User> GetUser(int id) { }
    }
    """)

    # Create mock layers
    domain_layer = Mock()
    domain_layer.name = "Domain"
    domain_layer.patterns = ["Repository", "Service"]
    domain_layer.directories = ["Repositories", "Services", "Entities"]

    application_layer = Mock()
    application_layer.name = "Application"
    application_layer.patterns = ["Engine", "Orchestrator"]
    application_layer.directories = ["Engines", "Orchestrators"]

    infrastructure_layer = Mock()
    infrastructure_layer.name = "Infrastructure"
    infrastructure_layer.patterns = ["Realm", "DatabaseContext"]
    infrastructure_layer.directories = ["Data", "Persistence"]

    presentation_layer = Mock()
    presentation_layer.name = "Presentation"
    presentation_layer.patterns = ["MVVM", "XAML"]
    presentation_layer.directories = ["ViewModels", "Views", "Controls"]

    # Create analysis
    analysis = Mock()
    analysis.language = "C#"
    analysis.architecture_pattern = "Clean Architecture"
    analysis.frameworks = [".NET MAUI", "Realm", "CommunityToolkit.MVVM"]
    analysis.patterns = [
        "MVVM",
        "Repository",
        "Service",
        "Engine",
        "Orchestrator",
        "ErrorOr",
        "XAML",
        "Realm"
    ]
    analysis.quality_assessment = "Uses ErrorOr<T> for error handling, MVVM with INotifyPropertyChanged"
    analysis.testing_framework = "xUnit"
    analysis.example_files = [viewmodel_file, repository_file]
    analysis.layers = [
        domain_layer,
        application_layer,
        infrastructure_layer,
        presentation_layer
    ]

    return analysis


@pytest.fixture
def react_fastapi_analysis(temp_dir):
    """Create realistic analysis for React + FastAPI monorepo"""
    # Create example files
    react_file = temp_dir / "UserProfile.tsx"
    react_file.write_text("""
    export const UserProfile: React.FC = () => {
        const { data } = useQuery('user', fetchUser);
        return <div>{data?.name}</div>;
    };
    """)

    fastapi_file = temp_dir / "main.py"
    fastapi_file.write_text("""
    from fastapi import FastAPI
    from pydantic import BaseModel

    app = FastAPI()

    class User(BaseModel):
        name: str
    """)

    # Create mock layers
    frontend_layer = Mock()
    frontend_layer.name = "Frontend"
    frontend_layer.patterns = ["Feature-Sliced", "React Query", "Tailwind"]
    frontend_layer.directories = ["features", "components", "hooks"]

    backend_layer = Mock()
    backend_layer.name = "Backend"
    backend_layer.patterns = ["FastAPI", "SQLAlchemy", "Pydantic"]
    backend_layer.directories = ["api", "models", "services"]

    # Create analysis
    analysis = Mock()
    analysis.language = "TypeScript/Python"
    analysis.architecture_pattern = "Monorepo"
    analysis.frameworks = [
        "React",
        "Next.js",
        "FastAPI",
        "SQLAlchemy",
        "TailwindCSS",
        "React Query"
    ]
    analysis.patterns = [
        "Feature-Sliced Architecture",
        "React Query",
        "FastAPI",
        "Pydantic",
        "SQLAlchemy ORM"
    ]
    analysis.quality_assessment = "Type-safe with TypeScript and Pydantic"
    analysis.testing_framework = "Vitest/pytest"
    analysis.example_files = [react_file, fastapi_file]
    analysis.layers = [frontend_layer, backend_layer]

    return analysis


class TestComplexCodebaseGeneration:
    """Test agent generation for complex real-world codebases"""

    def test_end_to_end_complex_maui_codebase(
        self,
        minimal_inventory,
        complex_maui_analysis
    ):
        """Test comprehensive agent generation for complex .NET MAUI project"""
        # Create realistic AI response for complex MAUI project
        ai_response = json.dumps([
            {
                "name": "mvvm-viewmodel-specialist",
                "description": "MVVM ViewModel patterns with INotifyPropertyChanged",
                "reason": "Project uses MVVM architecture in Presentation layer",
                "technologies": ["C#", "MVVM", ".NET MAUI", "INotifyPropertyChanged"],
                "priority": 9
            },
            {
                "name": "repository-pattern-specialist",
                "description": "Repository pattern with ErrorOr and thread-safety",
                "reason": "Project uses Repository pattern in Domain layer",
                "technologies": ["C#", "Repository Pattern", "ErrorOr"],
                "priority": 9
            },
            {
                "name": "service-pattern-specialist",
                "description": "Domain service patterns",
                "reason": "Project has Domain layer with Services subdirectory",
                "technologies": ["C#", "Service Pattern"],
                "priority": 8
            },
            {
                "name": "engine-pattern-specialist",
                "description": "Business logic engines with orchestration",
                "reason": "Project has Application layer with Engines subdirectory",
                "technologies": ["C#", "Engine Pattern"],
                "priority": 9
            },
            {
                "name": "realm-database-specialist",
                "description": "Realm database operations and migrations",
                "reason": "Project uses Realm in Infrastructure layer",
                "technologies": ["C#", "Realm", "Database"],
                "priority": 8
            },
            {
                "name": "erroror-pattern-specialist",
                "description": "ErrorOr<T> error handling pattern",
                "reason": "Project uses ErrorOr<T> for functional error handling",
                "technologies": ["C#", "ErrorOr", "Functional"],
                "priority": 7
            },
            {
                "name": "maui-xaml-specialist",
                "description": "MAUI XAML UI patterns and controls",
                "reason": "Project uses XAML for UI definition",
                "technologies": ["C#", "XAML", ".NET MAUI"],
                "priority": 8
            }
        ])

        # Create mock AI invoker
        mock_invoker = Mock(spec=AgentInvoker)
        mock_invoker.invoke.return_value = ai_response

        # Generate agents
        generator = AIAgentGenerator(
            inventory=minimal_inventory,
            ai_invoker=mock_invoker
        )

        generated = generator.generate(complex_maui_analysis)

        # Should generate 7 agents for complex project
        assert len(generated) >= 7, f"Expected ≥7 agents, got {len(generated)}"

        # Verify key agents are present
        agent_names = [a.name for a in generated]
        assert "mvvm-viewmodel-specialist" in agent_names
        assert "repository-pattern-specialist" in agent_names
        assert "engine-pattern-specialist" in agent_names
        assert "realm-database-specialist" in agent_names

        # Verify each agent has required attributes
        for agent in generated:
            assert agent.name
            assert agent.description
            assert len(agent.tools) > 0
            assert agent.confidence > 0
            assert agent.full_definition

    def test_end_to_end_react_fastapi_monorepo(
        self,
        minimal_inventory,
        react_fastapi_analysis
    ):
        """Test agent generation for React + FastAPI monorepo"""
        # Create realistic AI response for monorepo
        ai_response = json.dumps([
            {
                "name": "react-query-specialist",
                "description": "React Query data fetching patterns",
                "reason": "Project uses React Query for server state",
                "technologies": ["TypeScript", "React Query", "React"],
                "priority": 8
            },
            {
                "name": "feature-sliced-specialist",
                "description": "Feature-Sliced Architecture patterns",
                "reason": "Project uses Feature-Sliced Architecture",
                "technologies": ["TypeScript", "React", "Architecture"],
                "priority": 9
            },
            {
                "name": "fastapi-specialist",
                "description": "FastAPI endpoint and dependency injection patterns",
                "reason": "Project uses FastAPI for backend API",
                "technologies": ["Python", "FastAPI", "API"],
                "priority": 9
            },
            {
                "name": "pydantic-specialist",
                "description": "Pydantic models and validation",
                "reason": "Project uses Pydantic for data validation",
                "technologies": ["Python", "Pydantic", "Validation"],
                "priority": 8
            },
            {
                "name": "sqlalchemy-specialist",
                "description": "SQLAlchemy ORM patterns",
                "reason": "Project uses SQLAlchemy for database",
                "technologies": ["Python", "SQLAlchemy", "Database"],
                "priority": 8
            },
            {
                "name": "tailwind-specialist",
                "description": "TailwindCSS styling patterns",
                "reason": "Project uses TailwindCSS for styling",
                "technologies": ["TypeScript", "TailwindCSS", "CSS"],
                "priority": 6
            }
        ])

        # Create mock AI invoker
        mock_invoker = Mock(spec=AgentInvoker)
        mock_invoker.invoke.return_value = ai_response

        # Generate agents
        generator = AIAgentGenerator(
            inventory=minimal_inventory,
            ai_invoker=mock_invoker
        )

        generated = generator.generate(react_fastapi_analysis)

        # Should generate 6 agents for monorepo
        assert len(generated) >= 6, f"Expected ≥6 agents, got {len(generated)}"

        # Verify key agents are present
        agent_names = [a.name for a in generated]
        assert "react-query-specialist" in agent_names
        assert "fastapi-specialist" in agent_names
        assert "pydantic-specialist" in agent_names
        assert "sqlalchemy-specialist" in agent_names


class TestOrchestratorIntegration:
    """Test integration with template_create_orchestrator"""

    def test_orchestrator_workflow(self, minimal_inventory, complex_maui_analysis):
        """Test that generated agents work with orchestrator workflow"""
        # Create mock invoker that handles both JSON and markdown responses
        mock_invoker = Mock(spec=AgentInvoker)

        # First call returns JSON (for agent identification)
        # Second call returns markdown (for agent generation)
        mock_invoker.invoke.side_effect = [
            # First call: AI identification returns JSON
            json.dumps([
                {
                    "name": "test-specialist",
                    "description": "Testing patterns",
                    "reason": "Project uses xUnit",
                    "technologies": ["C#", "xUnit"],
                    "priority": 7
                }
            ]),
            # Second call: Agent generation returns markdown
            """---
name: test-specialist
description: Testing patterns for xUnit
tools: [Read, Write, Edit, Grep]
tags: [C#, xUnit, testing]
---

# Test Specialist

Expert in xUnit testing patterns for C# projects.
"""
        ]

        # Generate agents
        generator = AIAgentGenerator(
            inventory=minimal_inventory,
            ai_invoker=mock_invoker
        )

        generated = generator.generate(complex_maui_analysis)

        # Verify orchestrator can use generated agents
        assert len(generated) > 0

        # Each agent should be usable by orchestrator
        for agent in generated:
            # Verify agent has markdown definition (orchestrator requirement)
            assert "---" in agent.full_definition  # Has frontmatter
            assert agent.name in agent.full_definition
            assert len(agent.tools) > 0

    def test_generated_agents_saved_to_custom_dir(
        self,
        minimal_inventory,
        complex_maui_analysis,
        temp_dir
    ):
        """Test that generated agents can be saved to .claude/agents/"""
        import os

        # Change to temp directory
        original_cwd = os.getcwd()
        os.chdir(temp_dir)

        try:
            # Create AI response
            ai_response = json.dumps([
                {
                    "name": "save-test-specialist",
                    "description": "Test saving",
                    "reason": "Testing",
                    "technologies": ["Test"],
                    "priority": 5
                }
            ])

            mock_invoker = Mock(spec=AgentInvoker)
            mock_invoker.invoke.return_value = ai_response

            # Generate agents
            generator = AIAgentGenerator(
                inventory=minimal_inventory,
                ai_invoker=mock_invoker
            )

            generated = generator.generate(complex_maui_analysis)

            # Save to custom directory
            for agent in generated:
                saved_path = generator.save_agent_to_custom(agent)
                assert saved_path.exists()
                assert saved_path.name == f"{agent.name}.md"

        finally:
            os.chdir(original_cwd)


class TestAgentQuality:
    """Test quality of generated agents"""

    def test_agents_have_complete_metadata(
        self,
        minimal_inventory,
        complex_maui_analysis
    ):
        """Test that all generated agents have complete metadata"""
        ai_response = json.dumps([
            {
                "name": "quality-test-specialist",
                "description": "Quality testing",
                "reason": "Testing quality",
                "technologies": ["Test", "Quality"],
                "priority": 8
            }
        ])

        mock_invoker = Mock(spec=AgentInvoker)
        mock_invoker.invoke.return_value = ai_response

        generator = AIAgentGenerator(
            inventory=minimal_inventory,
            ai_invoker=mock_invoker
        )

        generated = generator.generate(complex_maui_analysis)

        for agent in generated:
            # Verify all required metadata
            assert agent.name
            assert agent.description
            assert len(agent.tools) > 0
            assert len(agent.tags) > 0
            assert agent.full_definition
            assert 0 <= agent.confidence <= 100
            assert isinstance(agent.reuse_recommended, bool)
            assert isinstance(agent.based_on_files, list)

    def test_agents_follow_naming_convention(
        self,
        minimal_inventory,
        complex_maui_analysis
    ):
        """Test that generated agent names follow convention"""
        ai_response = json.dumps([
            {
                "name": "naming-convention-specialist",
                "description": "Naming test",
                "reason": "Testing naming",
                "technologies": ["Test"],
                "priority": 5
            }
        ])

        mock_invoker = Mock(spec=AgentInvoker)
        mock_invoker.invoke.return_value = ai_response

        generator = AIAgentGenerator(
            inventory=minimal_inventory,
            ai_invoker=mock_invoker
        )

        generated = generator.generate(complex_maui_analysis)

        for agent in generated:
            # Names should be lowercase with hyphens
            assert agent.name.islower() or '-' in agent.name
            assert ' ' not in agent.name  # No spaces
            assert agent.name.endswith('-specialist') or agent.name.endswith('-agent')


class TestFallbackBehavior:
    """Test fallback to hard-coded detection"""

    def test_graceful_fallback_on_ai_error(
        self,
        minimal_inventory,
        complex_maui_analysis
    ):
        """Test that system falls back gracefully when AI fails"""
        # Create failing invoker
        failing_invoker = Mock(spec=AgentInvoker)
        failing_invoker.invoke.side_effect = Exception("AI service unavailable")

        generator = AIAgentGenerator(
            inventory=minimal_inventory,
            ai_invoker=failing_invoker
        )

        # Should not raise exception, should fall back
        generated = generator.generate(complex_maui_analysis)

        # Should still generate some agents via hard-coded fallback
        assert isinstance(generated, list)

    def test_fallback_identifies_basic_patterns(
        self,
        minimal_inventory,
        complex_maui_analysis
    ):
        """Test that fallback still identifies basic patterns"""
        # Create failing invoker
        failing_invoker = Mock(spec=AgentInvoker)
        failing_invoker.invoke.side_effect = Exception("AI failed")

        generator = AIAgentGenerator(
            inventory=minimal_inventory,
            ai_invoker=failing_invoker
        )

        # Use _identify_capability_needs which has fallback logic
        needs = generator._identify_capability_needs(complex_maui_analysis)

        # Should identify at least some basic patterns
        assert len(needs) > 0

        # Should have testing need (hard-coded pattern always detects testing_framework)
        test_needs = [n for n in needs if "test" in n.name.lower() or "xunit" in n.name.lower()]
        assert len(test_needs) > 0
