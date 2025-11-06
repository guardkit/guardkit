"""
Unit tests for Template Create Orchestrator

Tests the orchestration logic of template creation from existing codebases.
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
from dataclasses import dataclass

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent / "installer" / "global"
commands_lib_path = lib_path / "commands" / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))
if str(commands_lib_path) not in sys.path:
    sys.path.insert(0, str(commands_lib_path))

# Import the orchestrator module directly
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
OrchestrationResult = orchestrator_module.OrchestrationResult
run_template_create = orchestrator_module.run_template_create


# Test fixtures

@pytest.fixture
def mock_qa_answers():
    """Mock Q&A session answers"""
    return {
        'template_name': 'test-template',
        'codebase_path': '/fake/path',
        'primary_language': 'Python',
        'framework': 'FastAPI',
        'architecture_pattern': 'Clean Architecture',
        'template_purpose': 'quick_start'
    }


@pytest.fixture
def mock_analysis():
    """Mock codebase analysis"""
    analysis = Mock()
    analysis.overall_confidence = Mock(percentage=85)
    analysis.technology = Mock(
        primary_language='Python',
        frameworks=['FastAPI'],
        testing_frameworks=['pytest']
    )
    analysis.architecture = Mock(
        architectural_style='Clean Architecture',
        patterns=['Repository', 'DDD'],
        layers=[]
    )
    analysis.example_files = []
    return analysis


@pytest.fixture
def mock_manifest():
    """Mock template manifest"""
    manifest = Mock()
    manifest.name = 'test-template'
    manifest.language = 'Python'
    manifest.language_version = '>=3.9'
    manifest.architecture = 'Clean Architecture'
    manifest.complexity = 6
    manifest.confidence_score = 85
    manifest.to_dict = Mock(return_value={'name': 'test-template'})
    return manifest


@pytest.fixture
def mock_settings():
    """Mock template settings"""
    settings = Mock()
    settings.naming_conventions = {'class': Mock()}
    settings.layer_mappings = {'Domain': Mock()}
    settings.code_style = Mock(
        indentation='spaces',
        indent_size=4
    )
    return settings


@pytest.fixture
def mock_claude_md():
    """Mock CLAUDE.md"""
    claude_md = Mock()
    return claude_md


@pytest.fixture
def mock_templates():
    """Mock template collection"""
    templates = Mock()
    templates.templates = [Mock(), Mock(), Mock()]
    templates.total_count = 3
    return templates


@pytest.fixture
def mock_agents():
    """Mock generated agents"""
    return [
        Mock(name='agent-1', full_definition='# Agent 1'),
        Mock(name='agent-2', full_definition='# Agent 2')
    ]


# Test OrchestrationConfig

def test_orchestration_config_defaults():
    """Test OrchestrationConfig default values"""
    config = OrchestrationConfig()

    assert config.codebase_path is None
    assert config.output_path is None
    assert config.skip_qa is False
    assert config.max_templates is None
    assert config.dry_run is False
    assert config.save_analysis is False
    assert config.no_agents is False
    assert config.verbose is False


def test_orchestration_config_custom_values():
    """Test OrchestrationConfig with custom values"""
    config = OrchestrationConfig(
        codebase_path=Path('/test'),
        output_path=Path('/output'),
        skip_qa=True,
        max_templates=10,
        dry_run=True,
        save_analysis=True,
        no_agents=True,
        verbose=True
    )

    assert config.codebase_path == Path('/test')
    assert config.output_path == Path('/output')
    assert config.skip_qa is True
    assert config.max_templates == 10
    assert config.dry_run is True
    assert config.save_analysis is True
    assert config.no_agents is True
    assert config.verbose is True


# Test TemplateCreateOrchestrator initialization

def test_orchestrator_initialization():
    """Test orchestrator initializes correctly"""
    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    assert orchestrator.config == config
    assert orchestrator.errors == []
    assert orchestrator.warnings == []


# Test Phase 1: Q&A Session

@patch('installer.global.commands.lib.template_create_orchestrator.TemplateQASession')
def test_phase1_qa_session_success(mock_qa_class, mock_qa_answers):
    """Test successful Q&A session"""
    # Setup
    mock_qa_instance = Mock()
    mock_qa_instance.run.return_value = Mock(to_dict=Mock(return_value=mock_qa_answers))
    mock_qa_class.return_value = mock_qa_instance

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase1_qa_session()

    # Assert
    assert result == mock_qa_answers
    mock_qa_class.assert_called_once_with(skip_qa=False)
    mock_qa_instance.run.assert_called_once()


@patch('installer.global.commands.lib.template_create_orchestrator.TemplateQASession')
def test_phase1_qa_session_cancelled(mock_qa_class):
    """Test Q&A session cancellation"""
    # Setup
    mock_qa_instance = Mock()
    mock_qa_instance.run.return_value = None
    mock_qa_class.return_value = mock_qa_instance

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase1_qa_session()

    # Assert
    assert result is None


@patch('installer.global.commands.lib.template_create_orchestrator.TemplateQASession')
def test_phase1_qa_session_with_skip_qa(mock_qa_class, mock_qa_answers):
    """Test Q&A session with skip_qa flag"""
    # Setup
    mock_qa_instance = Mock()
    mock_qa_instance.run.return_value = Mock(to_dict=Mock(return_value=mock_qa_answers))
    mock_qa_class.return_value = mock_qa_instance

    config = OrchestrationConfig(skip_qa=True)
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase1_qa_session()

    # Assert
    mock_qa_class.assert_called_once_with(skip_qa=True)


# Test Phase 2: AI Analysis

@patch('installer.global.commands.lib.template_create_orchestrator.CodebaseAnalyzer')
@patch('installer.global.commands.lib.template_create_orchestrator.Path')
def test_phase2_ai_analysis_success(mock_path_class, mock_analyzer_class, mock_qa_answers, mock_analysis):
    """Test successful AI analysis"""
    # Setup
    mock_path_instance = Mock()
    mock_path_instance.exists.return_value = True
    mock_path_class.return_value = mock_path_instance

    mock_analyzer_instance = Mock()
    mock_analyzer_instance.analyze_codebase.return_value = mock_analysis
    mock_analyzer_class.return_value = mock_analyzer_instance

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase2_ai_analysis(mock_qa_answers)

    # Assert
    assert result == mock_analysis
    mock_analyzer_class.assert_called_once_with(max_files=10)


@patch('installer.global.commands.lib.template_create_orchestrator.Path')
def test_phase2_ai_analysis_codebase_not_found(mock_path_class, mock_qa_answers):
    """Test AI analysis with non-existent codebase"""
    # Setup
    mock_path_instance = Mock()
    mock_path_instance.exists.return_value = False
    mock_path_class.return_value = mock_path_instance

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase2_ai_analysis(mock_qa_answers)

    # Assert
    assert result is None


# Test Phase 3: Manifest Generation

@patch('installer.global.commands.lib.template_create_orchestrator.ManifestGenerator')
def test_phase3_manifest_generation_success(mock_generator_class, mock_analysis, mock_manifest):
    """Test successful manifest generation"""
    # Setup
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_manifest
    mock_generator_class.return_value = mock_generator_instance

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase3_manifest_generation(mock_analysis)

    # Assert
    assert result == mock_manifest
    mock_generator_class.assert_called_once_with(mock_analysis)
    mock_generator_instance.generate.assert_called_once()


# Test Phase 4: Settings Generation

@patch('installer.global.commands.lib.template_create_orchestrator.SettingsGenerator')
def test_phase4_settings_generation_success(mock_generator_class, mock_analysis, mock_settings):
    """Test successful settings generation"""
    # Setup
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_settings
    mock_generator_class.return_value = mock_generator_instance

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase4_settings_generation(mock_analysis)

    # Assert
    assert result == mock_settings
    mock_generator_class.assert_called_once_with(mock_analysis)
    mock_generator_instance.generate.assert_called_once()


# Test Phase 5: CLAUDE.md Generation

@patch('installer.global.commands.lib.template_create_orchestrator.ClaudeMdGenerator')
def test_phase5_claude_md_generation_success(mock_generator_class, mock_analysis, mock_claude_md):
    """Test successful CLAUDE.md generation"""
    # Setup
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_claude_md
    mock_generator_class.return_value = mock_generator_instance

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase5_claude_md_generation(mock_analysis)

    # Assert
    assert result == mock_claude_md
    mock_generator_class.assert_called_once_with(mock_analysis)
    mock_generator_instance.generate.assert_called_once()


# Test Phase 6: Template Generation

@patch('installer.global.commands.lib.template_create_orchestrator.TemplateGenerator')
def test_phase6_template_generation_success(mock_generator_class, mock_analysis, mock_templates):
    """Test successful template generation"""
    # Setup
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_templates
    mock_generator_class.return_value = mock_generator_instance

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase6_template_generation(mock_analysis)

    # Assert
    assert result == mock_templates
    mock_generator_class.assert_called_once_with(mock_analysis)
    mock_generator_instance.generate.assert_called_once_with(max_templates=None)


@patch('installer.global.commands.lib.template_create_orchestrator.TemplateGenerator')
def test_phase6_template_generation_with_max_templates(mock_generator_class, mock_analysis, mock_templates):
    """Test template generation with max_templates limit"""
    # Setup
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_templates
    mock_generator_class.return_value = mock_generator_instance

    config = OrchestrationConfig(max_templates=10)
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase6_template_generation(mock_analysis)

    # Assert
    mock_generator_instance.generate.assert_called_once_with(max_templates=10)


# Test Phase 7: Agent Recommendation

@patch('installer.global.commands.lib.template_create_orchestrator.scan_agents')
@patch('installer.global.commands.lib.template_create_orchestrator.AIAgentGenerator')
def test_phase7_agent_recommendation_success(mock_generator_class, mock_scan_agents, mock_analysis, mock_agents):
    """Test successful agent recommendation"""
    # Setup
    mock_inventory = Mock()
    mock_scan_agents.return_value = mock_inventory

    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_agents
    mock_generator_class.return_value = mock_generator_instance

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase7_agent_recommendation(mock_analysis)

    # Assert
    assert result == mock_agents
    mock_scan_agents.assert_called_once()
    mock_generator_class.assert_called_once_with(mock_inventory)
    mock_generator_instance.generate.assert_called_once_with(mock_analysis)


# Test Phase 8: Package Assembly

@patch('installer.global.commands.lib.template_create_orchestrator.json')
@patch('builtins.open', create=True)
def test_phase8_package_assembly_success(
    mock_open,
    mock_json,
    tmp_path,
    mock_manifest,
    mock_settings,
    mock_claude_md,
    mock_templates,
    mock_agents
):
    """Test successful package assembly"""
    # Setup
    config = OrchestrationConfig(output_path=tmp_path)
    orchestrator = TemplateCreateOrchestrator(config)

    # Mock generators
    with patch('installer.global.commands.lib.template_create_orchestrator.ManifestGenerator'):
        with patch('installer.global.commands.lib.template_create_orchestrator.SettingsGenerator') as mock_settings_gen:
            with patch('installer.global.commands.lib.template_create_orchestrator.ClaudeMdGenerator') as mock_claude_gen:
                with patch('installer.global.commands.lib.template_create_orchestrator.TemplateGenerator') as mock_template_gen:
                    # Setup mocks
                    mock_settings_instance = Mock()
                    mock_settings_gen.return_value = mock_settings_instance

                    mock_claude_instance = Mock()
                    mock_claude_gen.return_value = mock_claude_instance

                    mock_template_instance = Mock()
                    mock_template_gen.return_value = mock_template_instance

                    # Execute
                    result = orchestrator._phase8_package_assembly(
                        manifest=mock_manifest,
                        settings=mock_settings,
                        claude_md=mock_claude_md,
                        templates=mock_templates,
                        agents=mock_agents
                    )

                    # Assert
                    assert result == tmp_path
                    assert tmp_path.exists()


# Test Dry Run

@patch.object(TemplateCreateOrchestrator, '_phase1_qa_session')
@patch.object(TemplateCreateOrchestrator, '_phase2_ai_analysis')
@patch.object(TemplateCreateOrchestrator, '_phase3_manifest_generation')
@patch.object(TemplateCreateOrchestrator, '_phase4_settings_generation')
@patch.object(TemplateCreateOrchestrator, '_phase5_claude_md_generation')
@patch.object(TemplateCreateOrchestrator, '_phase6_template_generation')
@patch.object(TemplateCreateOrchestrator, '_phase7_agent_recommendation')
def test_dry_run_mode(
    mock_phase7,
    mock_phase6,
    mock_phase5,
    mock_phase4,
    mock_phase3,
    mock_phase2,
    mock_phase1,
    mock_qa_answers,
    mock_analysis,
    mock_manifest,
    mock_settings,
    mock_claude_md,
    mock_templates,
    mock_agents
):
    """Test dry run mode doesn't save files"""
    # Setup
    mock_phase1.return_value = mock_qa_answers
    mock_phase2.return_value = mock_analysis
    mock_phase3.return_value = mock_manifest
    mock_phase4.return_value = mock_settings
    mock_phase5.return_value = mock_claude_md
    mock_phase6.return_value = mock_templates
    mock_phase7.return_value = mock_agents

    config = OrchestrationConfig(dry_run=True)
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator.run()

    # Assert
    assert result.success is True
    assert result.output_path is None  # No files saved
    assert result.template_count == 3
    assert result.agent_count == 2


# Test Full Workflow

@patch.object(TemplateCreateOrchestrator, '_phase1_qa_session')
@patch.object(TemplateCreateOrchestrator, '_phase2_ai_analysis')
@patch.object(TemplateCreateOrchestrator, '_phase3_manifest_generation')
@patch.object(TemplateCreateOrchestrator, '_phase4_settings_generation')
@patch.object(TemplateCreateOrchestrator, '_phase5_claude_md_generation')
@patch.object(TemplateCreateOrchestrator, '_phase6_template_generation')
@patch.object(TemplateCreateOrchestrator, '_phase7_agent_recommendation')
@patch.object(TemplateCreateOrchestrator, '_phase8_package_assembly')
def test_full_workflow_success(
    mock_phase8,
    mock_phase7,
    mock_phase6,
    mock_phase5,
    mock_phase4,
    mock_phase3,
    mock_phase2,
    mock_phase1,
    tmp_path,
    mock_qa_answers,
    mock_analysis,
    mock_manifest,
    mock_settings,
    mock_claude_md,
    mock_templates,
    mock_agents
):
    """Test complete successful workflow"""
    # Setup
    mock_phase1.return_value = mock_qa_answers
    mock_phase2.return_value = mock_analysis
    mock_phase3.return_value = mock_manifest
    mock_phase4.return_value = mock_settings
    mock_phase5.return_value = mock_claude_md
    mock_phase6.return_value = mock_templates
    mock_phase7.return_value = mock_agents
    mock_phase8.return_value = tmp_path

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator.run()

    # Assert
    assert result.success is True
    assert result.template_name == 'test-template'
    assert result.output_path == tmp_path
    assert result.template_count == 3
    assert result.agent_count == 2
    assert result.confidence_score == 85

    # Verify all phases were called
    mock_phase1.assert_called_once()
    mock_phase2.assert_called_once()
    mock_phase3.assert_called_once()
    mock_phase4.assert_called_once()
    mock_phase5.assert_called_once()
    mock_phase6.assert_called_once()
    mock_phase7.assert_called_once()
    mock_phase8.assert_called_once()


# Test Error Handling

@patch.object(TemplateCreateOrchestrator, '_phase1_qa_session')
def test_qa_session_failure(mock_phase1):
    """Test handling of Q&A session failure"""
    # Setup
    mock_phase1.return_value = None

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator.run()

    # Assert
    assert result.success is False
    assert "Q&A session cancelled or failed" in result.errors


@patch.object(TemplateCreateOrchestrator, '_phase1_qa_session')
@patch.object(TemplateCreateOrchestrator, '_phase2_ai_analysis')
def test_ai_analysis_failure(mock_phase2, mock_phase1, mock_qa_answers):
    """Test handling of AI analysis failure"""
    # Setup
    mock_phase1.return_value = mock_qa_answers
    mock_phase2.return_value = None

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator.run()

    # Assert
    assert result.success is False
    assert "AI analysis failed" in result.errors


# Test Convenience Function

@patch.object(TemplateCreateOrchestrator, 'run')
def test_run_template_create_convenience_function(mock_run):
    """Test convenience function"""
    # Setup
    mock_result = OrchestrationResult(
        success=True,
        template_name='test',
        output_path=Path('/test'),
        manifest_path=None,
        settings_path=None,
        claude_md_path=None,
        template_count=5,
        agent_count=2,
        confidence_score=85,
        errors=[],
        warnings=[]
    )
    mock_run.return_value = mock_result

    # Execute
    result = run_template_create(
        codebase_path=Path('/test'),
        output_path=Path('/output'),
        skip_qa=True,
        max_templates=10,
        dry_run=True
    )

    # Assert
    assert result == mock_result
    mock_run.assert_called_once()


# Test No Agents Flag

@patch.object(TemplateCreateOrchestrator, '_phase1_qa_session')
@patch.object(TemplateCreateOrchestrator, '_phase2_ai_analysis')
@patch.object(TemplateCreateOrchestrator, '_phase3_manifest_generation')
@patch.object(TemplateCreateOrchestrator, '_phase4_settings_generation')
@patch.object(TemplateCreateOrchestrator, '_phase5_claude_md_generation')
@patch.object(TemplateCreateOrchestrator, '_phase6_template_generation')
@patch.object(TemplateCreateOrchestrator, '_phase7_agent_recommendation')
@patch.object(TemplateCreateOrchestrator, '_phase8_package_assembly')
def test_no_agents_flag(
    mock_phase8,
    mock_phase7,
    mock_phase6,
    mock_phase5,
    mock_phase4,
    mock_phase3,
    mock_phase2,
    mock_phase1,
    tmp_path,
    mock_qa_answers,
    mock_analysis,
    mock_manifest,
    mock_settings,
    mock_claude_md,
    mock_templates
):
    """Test no_agents flag skips agent generation"""
    # Setup
    mock_phase1.return_value = mock_qa_answers
    mock_phase2.return_value = mock_analysis
    mock_phase3.return_value = mock_manifest
    mock_phase4.return_value = mock_settings
    mock_phase5.return_value = mock_claude_md
    mock_phase6.return_value = mock_templates
    mock_phase8.return_value = tmp_path

    config = OrchestrationConfig(no_agents=True)
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator.run()

    # Assert
    assert result.success is True
    assert result.agent_count == 0
    mock_phase7.assert_not_called()  # Agent phase skipped


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
