"""
Unit Tests for Agent System Orchestration

Tests the complete agent orchestration workflow including:
- Phase 1: Inventory
- Phase 2: Generation
- Phase 3: External discovery
- Phase 4: Recommendation building
- Phase 5: Summary display
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from lib.agent_orchestration.agent_orchestration import (
    AgentOrchestrator,
    AgentRecommendation,
    DiscoveredAgent,
    get_agents_for_template
)
from lib.agent_scanner.agent_scanner import (
    AgentDefinition,
    AgentInventory
)
from lib.agent_generator.agent_generator import GeneratedAgent
from lib.codebase_analyzer.models import (
    CodebaseAnalysis,
    TechnologyInfo,
    ArchitectureInfo,
    QualityInfo,
    ConfidenceScore,
    ConfidenceLevel
)


@pytest.fixture
def mock_analysis():
    """Create mock codebase analysis"""
    return CodebaseAnalysis(
        codebase_path="/test/project",
        technology=TechnologyInfo(
            primary_language="C#",
            frameworks=[".NET MAUI"],
            testing_frameworks=["xUnit"],
            build_tools=["dotnet"],
            databases=[],
            infrastructure=[],
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=95.0
            )
        ),
        architecture=ArchitectureInfo(
            patterns=["MVVM", "Repository"],
            architectural_style="Clean Architecture",
            layers=[],
            key_abstractions=["ViewModel", "Service"],
            dependency_flow="Inward",
            confidence=ConfidenceScore(
                level=ConfidenceLevel.HIGH,
                percentage=90.0
            )
        ),
        quality=QualityInfo(
            overall_score=85.0,
            solid_compliance=80.0,
            dry_compliance=85.0,
            yagni_compliance=90.0,
            code_smells=[],
            strengths=["Clear architecture"],
            improvements=["Add more tests"],
            confidence=ConfidenceScore(
                level=ConfidenceLevel.MEDIUM,
                percentage=85.0
            )
        )
    )


@pytest.fixture
def mock_inventory():
    """Create mock agent inventory"""
    custom_agent = AgentDefinition(
        name="custom-test-agent",
        description="Custom test agent",
        tools=["Read", "Write"],
        tags=["testing"],
        source="custom",
        source_path=Path(".claude/agents/custom-test-agent.md"),
        priority=3,
        full_definition="---\nname: custom-test-agent\n---\n# Custom Test Agent"
    )

    global_agent = AgentDefinition(
        name="architectural-reviewer",
        description="Reviews architecture",
        tools=["Read", "Analyze"],
        tags=["architecture"],
        source="global",
        source_path=Path("installer/core/agents/architectural-reviewer.md"),
        priority=1,
        full_definition="---\nname: architectural-reviewer\n---\n# Architectural Reviewer"
    )

    return AgentInventory(
        custom_agents=[custom_agent],
        template_agents=[],
        global_agents=[global_agent]
    )


@pytest.fixture
def mock_generated_agents():
    """Create mock generated agents"""
    return [
        GeneratedAgent(
            name="mvvm-specialist",
            description="MVVM pattern specialist",
            tools=["Read", "Write", "Edit"],
            tags=["MVVM", "C#"],
            full_definition="---\nname: mvvm-specialist\n---\n# MVVM Specialist",
            confidence=85,
            based_on_files=[Path("ViewModels/TestViewModel.cs")],
            reuse_recommended=True
        )
    ]


class TestAgentRecommendation:
    """Test AgentRecommendation data structure"""

    def test_all_agents(self, mock_inventory, mock_generated_agents):
        """Test all_agents returns all agent types"""
        recommendation = AgentRecommendation(
            use_custom=mock_inventory.custom_agents,
            use_template=[],
            use_global=mock_inventory.global_agents,
            generated=mock_generated_agents,
            external_suggestions=[]
        )

        all_agents = recommendation.all_agents()

        assert len(all_agents) == 3
        assert mock_inventory.custom_agents[0] in all_agents
        assert mock_inventory.global_agents[0] in all_agents
        assert mock_generated_agents[0] in all_agents

    def test_total_count(self, mock_inventory, mock_generated_agents):
        """Test total_count calculation"""
        recommendation = AgentRecommendation(
            use_custom=mock_inventory.custom_agents,
            use_template=[],
            use_global=mock_inventory.global_agents,
            generated=mock_generated_agents,
            external_suggestions=[]
        )

        assert recommendation.total_count() == 3

    def test_summary(self, mock_inventory, mock_generated_agents):
        """Test summary generation"""
        recommendation = AgentRecommendation(
            use_custom=mock_inventory.custom_agents,
            use_template=[],
            use_global=mock_inventory.global_agents,
            generated=mock_generated_agents,
            external_suggestions=[]
        )

        summary = recommendation.summary()

        assert "Total: 3 agents" in summary
        assert "Custom: 1" in summary
        assert "Global: 1" in summary
        assert "Generated: 1" in summary

    def test_summary_with_external(self, mock_inventory):
        """Test summary with external suggestions"""
        external = [
            DiscoveredAgent(
                name="external-agent",
                description="External agent",
                source_url="https://example.com",
                tags=["test"],
                relevance_score=85.0
            )
        ]

        recommendation = AgentRecommendation(
            use_custom=[],
            use_template=[],
            use_global=mock_inventory.global_agents,
            generated=[],
            external_suggestions=external
        )

        summary = recommendation.summary()

        assert "Suggestions: 1 (optional)" in summary


class TestAgentOrchestrator:
    """Test AgentOrchestrator workflow"""

    def test_initialization(self):
        """Test orchestrator initialization"""
        orchestrator = AgentOrchestrator(
            template_path=Path("templates/react/agents"),
            enable_external_discovery=True
        )

        assert orchestrator.template_path == Path("templates/react/agents")
        assert orchestrator.enable_external_discovery is True

    def test_initialization_defaults(self):
        """Test orchestrator with default parameters"""
        orchestrator = AgentOrchestrator()

        assert orchestrator.template_path is None
        assert orchestrator.enable_external_discovery is False

    @patch('lib.agent_orchestration.agent_orchestration.MultiSourceAgentScanner')
    @patch('lib.agent_orchestration.agent_orchestration.AIAgentGenerator')
    def test_recommend_agents_success(
        self,
        mock_generator_class,
        mock_scanner_class,
        mock_analysis,
        mock_inventory,
        mock_generated_agents
    ):
        """Test successful agent recommendation flow"""
        # Setup mocks
        mock_scanner = Mock()
        mock_scanner.scan.return_value = mock_inventory
        mock_scanner_class.return_value = mock_scanner

        mock_generator = Mock()
        mock_generator.generate.return_value = mock_generated_agents
        mock_generator_class.return_value = mock_generator

        # Run orchestration
        orchestrator = AgentOrchestrator()
        recommendation = orchestrator.recommend_agents(mock_analysis)

        # Verify
        assert recommendation is not None
        assert recommendation.total_count() > 0
        assert len(recommendation.use_custom) == 1
        assert len(recommendation.use_global) == 1
        assert len(recommendation.generated) == 1

        # Verify methods were called
        mock_scanner.scan.assert_called_once()
        mock_generator.generate.assert_called_once_with(mock_analysis)

    @patch('lib.agent_orchestration.agent_orchestration.MultiSourceAgentScanner')
    def test_recommend_agents_error_handling(
        self,
        mock_scanner_class,
        mock_analysis
    ):
        """Test error handling in recommend_agents"""
        # Setup mock to raise exception
        mock_scanner_class.side_effect = Exception("Scanner failed")

        # Should not crash
        orchestrator = AgentOrchestrator()
        recommendation = orchestrator.recommend_agents(mock_analysis)

        # Should return fallback recommendation
        assert recommendation is not None
        assert isinstance(recommendation, AgentRecommendation)

    @patch('lib.agent_orchestration.agent_orchestration.MultiSourceAgentScanner')
    def test_phase1_inventory(
        self,
        mock_scanner_class,
        mock_inventory
    ):
        """Test Phase 1: Inventory"""
        mock_scanner = Mock()
        mock_scanner.scan.return_value = mock_inventory
        mock_scanner_class.return_value = mock_scanner

        orchestrator = AgentOrchestrator()
        inventory = orchestrator._phase1_inventory()

        assert inventory == mock_inventory
        mock_scanner.scan.assert_called_once()

    @patch('lib.agent_orchestration.agent_orchestration.AIAgentGenerator')
    def test_phase2_generate(
        self,
        mock_generator_class,
        mock_analysis,
        mock_inventory,
        mock_generated_agents
    ):
        """Test Phase 2: Generation"""
        mock_generator = Mock()
        mock_generator.generate.return_value = mock_generated_agents
        mock_generator_class.return_value = mock_generator

        orchestrator = AgentOrchestrator()
        generated = orchestrator._phase2_generate(mock_analysis, mock_inventory)

        assert generated == mock_generated_agents
        mock_generator.generate.assert_called_once_with(mock_analysis)

    @patch('builtins.input', return_value='n')
    def test_phase3_external_discovery_disabled(
        self,
        mock_input,
        mock_analysis,
        mock_inventory,
        mock_generated_agents
    ):
        """Test Phase 3: External discovery disabled"""
        orchestrator = AgentOrchestrator(enable_external_discovery=False)
        external = orchestrator._phase3_external_discovery(
            mock_analysis,
            mock_inventory,
            mock_generated_agents
        )

        assert external == []
        # Input should not be called when disabled
        mock_input.assert_not_called()

    @patch('builtins.input', return_value='n')
    def test_phase3_external_discovery_user_declined(
        self,
        mock_input,
        mock_analysis,
        mock_inventory,
        mock_generated_agents
    ):
        """Test Phase 3: External discovery user declined"""
        orchestrator = AgentOrchestrator(enable_external_discovery=True)
        external = orchestrator._phase3_external_discovery(
            mock_analysis,
            mock_inventory,
            mock_generated_agents
        )

        assert external == []
        mock_input.assert_called_once()

    def test_phase4_build_recommendation(
        self,
        mock_inventory,
        mock_generated_agents
    ):
        """Test Phase 4: Build recommendation"""
        orchestrator = AgentOrchestrator()
        external = []

        recommendation = orchestrator._phase4_build_recommendation(
            mock_inventory,
            mock_generated_agents,
            external
        )

        assert recommendation.use_custom == mock_inventory.custom_agents
        assert recommendation.use_global == mock_inventory.global_agents
        assert recommendation.generated == mock_generated_agents
        assert recommendation.external_suggestions == []

    def test_phase5_display_summary(
        self,
        mock_inventory,
        mock_generated_agents,
        capsys
    ):
        """Test Phase 5: Display summary"""
        recommendation = AgentRecommendation(
            use_custom=mock_inventory.custom_agents,
            use_template=[],
            use_global=mock_inventory.global_agents,
            generated=mock_generated_agents,
            external_suggestions=[]
        )

        orchestrator = AgentOrchestrator()
        orchestrator._phase5_display_summary(recommendation)

        # Capture output
        captured = capsys.readouterr()

        # Verify output
        assert "Agent Setup Complete" in captured.out
        assert "Total: 3 agents" in captured.out
        assert "custom-test-agent" in captured.out
        assert "mvvm-specialist" in captured.out

    @patch('lib.agent_orchestration.agent_orchestration.MultiSourceAgentScanner')
    def test_fallback_recommendation(
        self,
        mock_scanner_class,
        mock_inventory
    ):
        """Test fallback recommendation"""
        mock_scanner = Mock()
        mock_scanner.scan.return_value = mock_inventory
        mock_scanner_class.return_value = mock_scanner

        orchestrator = AgentOrchestrator()
        recommendation = orchestrator._fallback_recommendation()

        assert recommendation is not None
        assert len(recommendation.use_custom) == 1
        assert len(recommendation.use_global) == 1
        assert len(recommendation.generated) == 0

    @patch('lib.agent_orchestration.agent_orchestration.MultiSourceAgentScanner')
    def test_fallback_recommendation_complete_failure(
        self,
        mock_scanner_class
    ):
        """Test fallback when everything fails"""
        mock_scanner_class.side_effect = Exception("Complete failure")

        orchestrator = AgentOrchestrator()
        recommendation = orchestrator._fallback_recommendation()

        # Should return empty recommendation
        assert recommendation is not None
        assert len(recommendation.use_custom) == 0
        assert len(recommendation.use_global) == 0
        assert len(recommendation.generated) == 0


class TestConvenienceFunction:
    """Test convenience function"""

    @patch('lib.agent_orchestration.agent_orchestration.AgentOrchestrator')
    def test_get_agents_for_template(
        self,
        mock_orchestrator_class,
        mock_analysis
    ):
        """Test get_agents_for_template convenience function"""
        mock_orchestrator = Mock()
        mock_recommendation = AgentRecommendation(
            use_custom=[],
            use_template=[],
            use_global=[],
            generated=[],
            external_suggestions=[]
        )
        mock_orchestrator.recommend_agents.return_value = mock_recommendation
        mock_orchestrator_class.return_value = mock_orchestrator

        # Call convenience function
        result = get_agents_for_template(
            analysis=mock_analysis,
            template_path=Path("templates/react/agents"),
            enable_external=True
        )

        # Verify orchestrator was created with correct params
        mock_orchestrator_class.assert_called_once_with(
            template_path=Path("templates/react/agents"),
            enable_external_discovery=True
        )

        # Verify recommend_agents was called
        mock_orchestrator.recommend_agents.assert_called_once_with(mock_analysis)

        # Verify result
        assert result == mock_recommendation

    @patch('lib.agent_orchestration.agent_orchestration.AgentOrchestrator')
    def test_get_agents_for_template_defaults(
        self,
        mock_orchestrator_class,
        mock_analysis
    ):
        """Test convenience function with default parameters"""
        mock_orchestrator = Mock()
        mock_recommendation = AgentRecommendation(
            use_custom=[],
            use_template=[],
            use_global=[],
            generated=[],
            external_suggestions=[]
        )
        mock_orchestrator.recommend_agents.return_value = mock_recommendation
        mock_orchestrator_class.return_value = mock_orchestrator

        # Call with defaults
        result = get_agents_for_template(analysis=mock_analysis)

        # Verify defaults
        mock_orchestrator_class.assert_called_once_with(
            template_path=None,
            enable_external_discovery=False
        )


class TestDiscoveredAgent:
    """Test DiscoveredAgent data structure"""

    def test_discovered_agent_creation(self):
        """Test creating DiscoveredAgent"""
        agent = DiscoveredAgent(
            name="test-agent",
            description="Test agent from community",
            source_url="https://github.com/example/agent",
            tags=["testing", "python"],
            relevance_score=85.5
        )

        assert agent.name == "test-agent"
        assert agent.description == "Test agent from community"
        assert agent.source_url == "https://github.com/example/agent"
        assert agent.tags == ["testing", "python"]
        assert agent.relevance_score == 85.5
