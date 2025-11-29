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
import tempfile

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

# Helper function to patch orchestrator dependencies
def patch_orchestrator_class(monkeypatch, class_name, mock_class):
    """Patch a class in the orchestrator module's namespace."""
    monkeypatch.setattr(orchestrator_module, class_name, mock_class)


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
    analysis.codebase_path = '/test/codebase'
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
    analysis.metadata = Mock(
        template_name='test-template',
        primary_language='Python',
        framework='FastAPI'
    )
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
    manifest.to_dict = Mock(return_value={'name': 'test-template', 'confidence_score': 85})
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
    claude_md.__str__ = Mock(return_value="# CLAUDE.md Content")
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


@pytest.fixture
def temp_codebase(tmp_path):
    """Create a temporary codebase directory"""
    codebase_dir = tmp_path / "test_codebase"
    codebase_dir.mkdir(exist_ok=True)

    # Create minimal Python project structure
    (codebase_dir / "main.py").write_text("print('hello')")
    (codebase_dir / "setup.py").write_text("# setup")

    return codebase_dir


# Test OrchestrationConfig

def test_orchestration_config_defaults():
    """Test OrchestrationConfig default values"""
    config = OrchestrationConfig()

    assert config.codebase_path is None
    assert config.output_path is None
    # skip_qa removed in TASK-51B2 (AI-native workflow)
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
        # skip_qa removed in TASK-51B2
        max_templates=10,
        dry_run=True,
        save_analysis=True,
        no_agents=True,
        verbose=True
    )

    assert config.codebase_path == Path('/test')
    assert config.output_path == Path('/output')
    # skip_qa removed in TASK-51B2
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


# TASK-51B2: Removed Phase 1 Q&A tests (AI-native workflow)
# The following tests are no longer applicable after refactor to AI-native analysis:
# - test_phase1_qa_session_success
# - test_phase1_qa_session_cancelled
# - test_phase1_qa_session_with_skip_qa
# Phase 1 now uses _phase1_ai_analysis() instead of _phase1_qa_session()

# Test Phase 1: AI Analysis (TASK-51B2)

def test_phase1_ai_analysis_success(temp_codebase, monkeypatch):
    """Test AI-native Phase 1 analysis success (TASK-51B2)"""
    # Setup mock analyzer
    mock_analyzer = Mock()
    mock_analysis = Mock()
    mock_analysis.overall_confidence.percentage = 95
    mock_analysis.metadata = Mock(
        primary_language='Python',
        framework='FastAPI',
        template_name='fastapi-python'
    )
    mock_analyzer.analyze_codebase.return_value = mock_analysis
    mock_analyzer_class = Mock(return_value=mock_analyzer)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'CodebaseAnalyzer', mock_analyzer_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute with real temp path
    result = orchestrator._phase1_ai_analysis(temp_codebase)

    # Assert - path exists is checked, so mock should be called
    assert result is not None
    mock_analyzer.analyze_codebase.assert_called_once_with(
        codebase_path=temp_codebase,
        template_context=None,  # AI-native: no context, AI infers everything
        save_results=False
    )


def test_phase1_ai_analysis_path_not_exists():
    """Test Phase 1 handles non-existent codebase path"""
    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)
    bad_path = Path("/nonexistent/path/definitely/does/not/exist")

    result = orchestrator._phase1_ai_analysis(bad_path)

    assert result is None


def test_phase1_ai_analysis_metadata_inference(temp_codebase, monkeypatch):
    """Test AI infers metadata when template_context is None (TASK-51B2)"""
    # Setup mock analyzer
    mock_analyzer = Mock()
    mock_analysis = Mock()
    mock_analysis.metadata = Mock(
        template_name='fastapi-python',
        primary_language='Python',
        framework='FastAPI'
    )
    mock_analysis.overall_confidence.percentage = 92
    mock_analyzer.analyze_codebase.return_value = mock_analysis
    mock_analyzer_class = Mock(return_value=mock_analyzer)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'CodebaseAnalyzer', mock_analyzer_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute with real temp path
    result = orchestrator._phase1_ai_analysis(temp_codebase)

    # Assert - path exists so analyzer is called
    assert result is not None
    assert result == mock_analysis

    # Assert - no template_context was provided (AI-native)
    call_args = mock_analyzer.analyze_codebase.call_args
    assert call_args.kwargs['template_context'] is None


# TASK-51B2: Old Phase 2 tests removed (AI analysis moved to Phase 1)
# - test_phase2_ai_analysis_success
# - test_phase2_ai_analysis_codebase_not_found

# Test Phase 2: Manifest Generation

def test_phase2_manifest_generation_success(mock_analysis, mock_manifest, monkeypatch):
    """Test successful manifest generation"""
    # Setup mock
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_manifest
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'ManifestGenerator', mock_generator_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase2_manifest_generation(mock_analysis)

    # Assert
    assert result == mock_manifest
    mock_generator_class.assert_called_once_with(mock_analysis)
    mock_generator_instance.generate.assert_called_once()


# Test Phase 3: Settings Generation

def test_phase3_settings_generation_success(mock_analysis, mock_settings, monkeypatch):
    """Test successful settings generation"""
    # Setup mock
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_settings
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'SettingsGenerator', mock_generator_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase3_settings_generation(mock_analysis)

    # Assert
    assert result == mock_settings
    mock_generator_class.assert_called_once_with(mock_analysis)
    mock_generator_instance.generate.assert_called_once()


# Test Phase 4: Template Generation

def test_phase4_template_generation_success(mock_analysis, mock_templates, monkeypatch):
    """Test successful template generation"""
    # Setup mock
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_templates
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'TemplateGenerator', mock_generator_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase4_template_generation(mock_analysis)

    # Assert
    assert result == mock_templates
    mock_generator_class.assert_called_once_with(mock_analysis)
    mock_generator_instance.generate.assert_called_once_with(max_templates=None)


def test_phase4_template_generation_with_max_templates(mock_analysis, mock_templates, monkeypatch):
    """Test template generation with max_templates limit"""
    # Setup mock
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_templates
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'TemplateGenerator', mock_generator_class)

    config = OrchestrationConfig(max_templates=10)
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase4_template_generation(mock_analysis)

    # Assert
    mock_generator_instance.generate.assert_called_once_with(max_templates=10)


# Test Phase 5: Agent Recommendation

def test_phase5_agent_recommendation_success(mock_analysis, mock_agents, monkeypatch):
    """Test successful agent recommendation"""
    # Mock AIAgentGenerator
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_agents
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch AIAgentGenerator in orchestrator module
    patch_orchestrator_class(monkeypatch, 'AIAgentGenerator', mock_generator_class)

    # Mock importlib.import_module to return a fake agent_scanner module
    original_import_module = importlib.import_module
    def mock_import_module(name, *args, **kwargs):
        if name == 'installer.global.lib.agent_scanner':
            mock_module = Mock()
            mock_scanner_inst = Mock()
            mock_scanner_inst.scan.return_value = Mock()  # mock inventory
            mock_module.MultiSourceAgentScanner = Mock(return_value=mock_scanner_inst)
            return mock_module
        return original_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib, 'import_module', mock_import_module)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase5_agent_recommendation(mock_analysis)

    # Assert
    assert result == mock_agents


# Test Phase 6: CLAUDE.md Generation

def test_phase6_claude_md_generation_success(mock_analysis, mock_claude_md, mock_agents, monkeypatch):
    """Test successful CLAUDE.md generation"""
    # Setup mock
    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_claude_md
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'ClaudeMdGenerator', mock_generator_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase6_claude_md_generation(mock_analysis, mock_agents)

    # Assert
    assert result == mock_claude_md
    mock_generator_class.assert_called_once_with(mock_analysis, agents=mock_agents)
    mock_generator_instance.generate.assert_called_once()


# Test Phase 7: Package Assembly

def test_phase7_package_assembly_success(
    tmp_path,
    mock_manifest,
    mock_settings,
    mock_claude_md,
    mock_templates,
    mock_agents,
    monkeypatch
):
    """Test successful package assembly"""
    # Setup - mock manifest.to_dict() to return a serializable dict
    mock_manifest.to_dict = Mock(return_value={'name': 'test-template', 'language': 'Python'})
    mock_manifest.name = 'test-template'

    # Mock templates with proper attributes
    mock_templates.total_count = 0  # Simplify for test

    # Mock the generator instances with save methods that create actual files
    def create_settings_file(settings, path):
        path.write_text('{"test": "settings"}')

    def create_claude_md_file(claude_md, path):
        path.write_text('# CLAUDE.md')

    mock_manifest_gen = Mock()
    mock_manifest_gen.save = Mock()

    mock_settings_gen = Mock()
    mock_settings_gen.save = Mock(side_effect=create_settings_file)

    mock_claude_gen = Mock()
    mock_claude_gen.save = Mock(side_effect=create_claude_md_file)

    mock_template_gen = Mock()
    mock_template_gen.save_templates = Mock()

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'ManifestGenerator', Mock(return_value=mock_manifest_gen))
    patch_orchestrator_class(monkeypatch, 'SettingsGenerator', Mock(return_value=mock_settings_gen))
    patch_orchestrator_class(monkeypatch, 'ClaudeMdGenerator', Mock(return_value=mock_claude_gen))
    patch_orchestrator_class(monkeypatch, 'TemplateGenerator', Mock(return_value=mock_template_gen))

    config = OrchestrationConfig(output_path=tmp_path)
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase7_package_assembly(
        manifest=mock_manifest,
        settings=mock_settings,
        claude_md=mock_claude_md,
        templates=mock_templates,
        agents=mock_agents
    )

    # Assert - path created
    assert result is not None
    assert result == tmp_path
    assert (tmp_path / "manifest.json").exists()
    assert (tmp_path / "settings.json").exists()
    assert (tmp_path / "CLAUDE.md").exists()


# Test Dry Run

def test_dry_run_mode(
    tmp_path,
    mock_analysis,
    mock_manifest,
    mock_settings,
    mock_claude_md,
    mock_templates,
    mock_agents,
    monkeypatch
):
    """Test dry run mode doesn't save files"""
    # Setup state manager mock
    mock_state_manager = Mock()
    mock_state_manager.save_state = Mock()  # Prevent JSON serialization
    mock_state_manager_class = Mock(return_value=mock_state_manager)

    # Patch StateManager in orchestrator module
    patch_orchestrator_class(monkeypatch, 'StateManager', mock_state_manager_class)

    # Create proper mock templates with string name attribute
    mock_template1 = Mock()
    mock_template1.name = "test_template1.py"  # String, not Mock
    mock_template1.template_path = "test/template1.py"
    mock_template2 = Mock()
    mock_template2.name = "test_template2.py"
    mock_template2.template_path = "test/template2.py"
    mock_template3 = Mock()
    mock_template3.name = "test_template3.py"
    mock_template3.template_path = "test/template3.py"
    mock_templates.templates = [mock_template1, mock_template2, mock_template3]
    mock_templates.total_count = 3

    mock_manifest.name = 'test-template'
    mock_manifest.confidence_score = 85

    # Mock phase methods
    mock_phase1 = Mock(return_value=mock_analysis)
    mock_phase2 = Mock(return_value=mock_manifest)
    mock_phase3 = Mock(return_value=mock_settings)
    mock_phase4 = Mock(return_value=mock_templates)
    mock_phase5 = Mock(return_value=mock_agents)
    mock_phase6 = Mock(return_value=mock_claude_md)

    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase1_ai_analysis', mock_phase1)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase2_manifest_generation', mock_phase2)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase3_settings_generation', mock_phase3)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase4_template_generation', mock_phase4)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase5_agent_recommendation', mock_phase5)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase6_claude_md_generation', mock_phase6)

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

def test_full_workflow_success(
    tmp_path,
    mock_analysis,
    mock_manifest,
    mock_settings,
    mock_claude_md,
    mock_templates,
    mock_agents,
    monkeypatch
):
    """Test complete successful workflow"""
    # Setup state manager mock
    mock_state_manager = Mock()
    mock_state_manager.save_state = Mock()  # Prevent JSON serialization
    mock_state_manager.cleanup = Mock()
    mock_state_manager_class = Mock(return_value=mock_state_manager)

    # Patch StateManager in orchestrator module
    patch_orchestrator_class(monkeypatch, 'StateManager', mock_state_manager_class)

    # Create proper mock templates with string name attribute
    mock_template1 = Mock()
    mock_template1.name = "test_template1.py"  # String, not Mock
    mock_template1.template_path = "test/template1.py"
    mock_template2 = Mock()
    mock_template2.name = "test_template2.py"
    mock_template2.template_path = "test/template2.py"
    mock_template3 = Mock()
    mock_template3.name = "test_template3.py"
    mock_template3.template_path = "test/template3.py"
    mock_templates.templates = [mock_template1, mock_template2, mock_template3]
    mock_templates.total_count = 3

    mock_manifest.name = 'test-template'
    mock_manifest.confidence_score = 85

    # Mock phase methods
    mock_phase1 = Mock(return_value=mock_analysis)
    mock_phase2 = Mock(return_value=mock_manifest)
    mock_phase3 = Mock(return_value=mock_settings)
    mock_phase4 = Mock(return_value=mock_templates)
    mock_phase5 = Mock(return_value=mock_agents)
    mock_phase6 = Mock(return_value=mock_claude_md)

    # Phase 7 creates the output directory and minimal files
    def mock_phase7_impl(*args, **kwargs):
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "manifest.json").write_text('{}')
        (tmp_path / "settings.json").write_text('{}')
        (tmp_path / "CLAUDE.md").write_text('# Test')
        return tmp_path
    mock_phase7 = Mock(side_effect=mock_phase7_impl)

    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase1_ai_analysis', mock_phase1)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase2_manifest_generation', mock_phase2)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase3_settings_generation', mock_phase3)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase4_template_generation', mock_phase4)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase5_agent_recommendation', mock_phase5)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase6_claude_md_generation', mock_phase6)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase7_package_assembly', mock_phase7)

    config = OrchestrationConfig(skip_validation=True)  # Skip validation to avoid file checks
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


# Test Error Handling

def test_ai_analysis_failure(monkeypatch):
    """Test handling of AI analysis failure"""
    # Setup state manager mock
    mock_state_manager = Mock()
    mock_state_manager.save_state = Mock()
    mock_state_manager_class = Mock(return_value=mock_state_manager)

    # Patch StateManager in orchestrator module
    patch_orchestrator_class(monkeypatch, 'StateManager', mock_state_manager_class)

    # Mock phase method to return None (failure)
    mock_phase1 = Mock(return_value=None)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase1_ai_analysis', mock_phase1)

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

    # Execute (TASK-51B2: removed skip_qa parameter)
    result = run_template_create(
        codebase_path=Path('/test'),
        output_path=Path('/output'),
        max_templates=10,
        dry_run=True
    )

    # Assert
    assert result == mock_result
    mock_run.assert_called_once()


# Test No Agents Flag

def test_no_agents_flag(
    tmp_path,
    mock_analysis,
    mock_manifest,
    mock_settings,
    mock_claude_md,
    mock_templates,
    monkeypatch
):
    """Test no_agents flag skips agent generation"""
    # Setup state manager mock
    mock_state_manager = Mock()
    mock_state_manager.save_state = Mock()  # Prevent JSON serialization
    mock_state_manager.cleanup = Mock()
    mock_state_manager_class = Mock(return_value=mock_state_manager)

    # Patch StateManager in orchestrator module
    patch_orchestrator_class(monkeypatch, 'StateManager', mock_state_manager_class)

    # Create proper mock templates with string name attribute
    mock_template1 = Mock()
    mock_template1.name = "test_template1.py"  # String, not Mock
    mock_template1.template_path = "test/template1.py"
    mock_template2 = Mock()
    mock_template2.name = "test_template2.py"
    mock_template2.template_path = "test/template2.py"
    mock_template3 = Mock()
    mock_template3.name = "test_template3.py"
    mock_template3.template_path = "test/template3.py"
    mock_templates.templates = [mock_template1, mock_template2, mock_template3]
    mock_templates.total_count = 3

    mock_manifest.name = 'test-template'
    mock_manifest.confidence_score = 85

    # Mock phase methods
    mock_phase1 = Mock(return_value=mock_analysis)
    mock_phase2 = Mock(return_value=mock_manifest)
    mock_phase3 = Mock(return_value=mock_settings)
    mock_phase4 = Mock(return_value=mock_templates)
    mock_phase5 = Mock()  # Should not be called
    mock_phase6 = Mock(return_value=mock_claude_md)

    # Phase 7 creates the output directory and minimal files
    def mock_phase7_impl(*args, **kwargs):
        tmp_path.mkdir(exist_ok=True)
        (tmp_path / "manifest.json").write_text('{}')
        (tmp_path / "settings.json").write_text('{}')
        (tmp_path / "CLAUDE.md").write_text('# Test')
        return tmp_path
    mock_phase7 = Mock(side_effect=mock_phase7_impl)

    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase1_ai_analysis', mock_phase1)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase2_manifest_generation', mock_phase2)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase3_settings_generation', mock_phase3)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase4_template_generation', mock_phase4)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase5_agent_recommendation', mock_phase5)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase6_claude_md_generation', mock_phase6)
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase7_package_assembly', mock_phase7)

    config = OrchestrationConfig(no_agents=True, skip_validation=True)  # Skip validation to avoid file checks
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator.run()

    # Assert
    assert result.success is True
    assert result.agent_count == 0
    mock_phase5.assert_not_called()  # Agent phase skipped


# ========== NEW TESTS FOR BRANCH COVERAGE ==========

def test_phase1_ai_analysis_exception_handling(temp_codebase, monkeypatch):
    """Test Phase 1 exception handling when analyzer raises exception"""
    # Setup mock analyzer that raises exception
    mock_analyzer = Mock()
    mock_analyzer.analyze_codebase.side_effect = Exception("Analysis error")
    mock_analyzer_class = Mock(return_value=mock_analyzer)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'CodebaseAnalyzer', mock_analyzer_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase1_ai_analysis(temp_codebase)

    # Assert - should return None on exception
    assert result is None


def test_phase2_manifest_generation_exception_handling(mock_analysis, monkeypatch):
    """Test Phase 2 exception handling when generator raises exception"""
    # Setup mock that raises exception
    mock_generator_instance = Mock()
    mock_generator_instance.generate.side_effect = Exception("Manifest generation error")
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'ManifestGenerator', mock_generator_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase2_manifest_generation(mock_analysis)

    # Assert - should return None on exception
    assert result is None


def test_phase3_settings_generation_exception_handling(mock_analysis, monkeypatch):
    """Test Phase 3 exception handling when generator raises exception"""
    # Setup mock that raises exception
    mock_generator_instance = Mock()
    mock_generator_instance.generate.side_effect = Exception("Settings generation error")
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'SettingsGenerator', mock_generator_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase3_settings_generation(mock_analysis)

    # Assert - should return None on exception
    assert result is None


def test_phase4_template_generation_exception_handling(mock_analysis, monkeypatch):
    """Test Phase 4 exception handling when generator raises exception"""
    # Setup mock that raises exception
    mock_generator_instance = Mock()
    mock_generator_instance.generate.side_effect = Exception("Template generation error")
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'TemplateGenerator', mock_generator_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase4_template_generation(mock_analysis)

    # Assert - should return None on exception
    assert result is None


def test_phase5_agent_recommendation_exception_handling(mock_analysis, monkeypatch):
    """Test Phase 5 exception handling when generator raises exception"""
    # Mock AIAgentGenerator that raises exception
    mock_generator_instance = Mock()
    mock_generator_instance.generate.side_effect = Exception("Agent generation error")
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch AIAgentGenerator in orchestrator module
    patch_orchestrator_class(monkeypatch, 'AIAgentGenerator', mock_generator_class)

    # Mock importlib.import_module to return a fake agent_scanner module
    original_import_module = importlib.import_module
    def mock_import_module(name, *args, **kwargs):
        if name == 'installer.global.lib.agent_scanner':
            mock_module = Mock()
            mock_scanner_inst = Mock()
            mock_scanner_inst.scan.return_value = Mock()  # mock inventory
            mock_module.MultiSourceAgentScanner = Mock(return_value=mock_scanner_inst)
            return mock_module
        return original_import_module(name, *args, **kwargs)

    monkeypatch.setattr(importlib, 'import_module', mock_import_module)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase5_agent_recommendation(mock_analysis)

    # Assert - should return empty list on exception
    assert result == []


def test_phase6_claude_md_generation_exception_handling(mock_analysis, mock_agents, monkeypatch):
    """Test Phase 6 exception handling when generator raises exception"""
    # Setup mock that raises exception
    mock_generator_instance = Mock()
    mock_generator_instance.generate.side_effect = Exception("CLAUDE.md generation error")
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'ClaudeMdGenerator', mock_generator_class)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase6_claude_md_generation(mock_analysis, mock_agents)

    # Assert - should return None on exception
    assert result is None


def test_phase7_package_assembly_exception_handling(
    tmp_path,
    mock_manifest,
    mock_settings,
    mock_claude_md,
    mock_templates,
    mock_agents,
    monkeypatch
):
    """Test Phase 7 exception handling when file I/O fails"""
    # Setup - mock manifest.to_dict() to raise exception
    mock_manifest.to_dict = Mock(side_effect=Exception("Serialization error"))
    mock_manifest.name = 'test-template'

    config = OrchestrationConfig(output_path=tmp_path)
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase7_package_assembly(
        manifest=mock_manifest,
        settings=mock_settings,
        claude_md=mock_claude_md,
        templates=mock_templates,
        agents=mock_agents
    )

    # Assert - should return None on exception
    assert result is None


def test_keyboard_interrupt_handling(monkeypatch):
    """Test handling of KeyboardInterrupt during workflow"""
    # Setup state manager mock
    mock_state_manager = Mock()
    mock_state_manager.save_state = Mock()
    mock_state_manager_class = Mock(return_value=mock_state_manager)

    # Patch StateManager in orchestrator module
    patch_orchestrator_class(monkeypatch, 'StateManager', mock_state_manager_class)

    # Mock phase method to raise KeyboardInterrupt
    mock_phase1 = Mock(side_effect=KeyboardInterrupt())
    monkeypatch.setattr(TemplateCreateOrchestrator, '_phase1_ai_analysis', mock_phase1)

    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator.run()

    # Assert
    assert result.success is False
    assert "User interrupted" in result.errors


# ========== TESTS FOR TASK-FDB2: --name FLAG ==========

def test_validate_template_name_valid():
    """Test validation of valid template names"""
    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Valid names
    valid_names = [
        "my-template",
        "api-123",
        "react-admin",
        "dotnet-api-template",
        "a-b-c"
    ]

    for name in valid_names:
        is_valid, error_msg = orchestrator._validate_template_name(name)
        assert is_valid is True, f"Expected {name} to be valid"
        assert error_msg == ""


def test_validate_template_name_invalid_pattern():
    """Test validation of invalid template name patterns"""
    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Invalid patterns
    invalid_names = [
        ("MyTemplate", "Template name must contain only lowercase letters, numbers, and hyphens"),
        ("my_template", "Template name must contain only lowercase letters, numbers, and hyphens"),
        ("my template", "Template name must contain only lowercase letters, numbers, and hyphens"),
        ("my.template", "Template name must contain only lowercase letters, numbers, and hyphens"),
        ("my@template", "Template name must contain only lowercase letters, numbers, and hyphens"),
    ]

    for name, expected_error in invalid_names:
        is_valid, error_msg = orchestrator._validate_template_name(name)
        assert is_valid is False, f"Expected {name} to be invalid"
        assert error_msg == expected_error


def test_validate_template_name_invalid_length():
    """Test validation of invalid template name lengths"""
    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    # Too short
    is_valid, error_msg = orchestrator._validate_template_name("ab")
    assert is_valid is False
    assert error_msg == "Template name must be 3-50 characters"

    # Too long
    is_valid, error_msg = orchestrator._validate_template_name("a" * 51)
    assert is_valid is False
    assert error_msg == "Template name must be 3-50 characters"


def test_validate_template_name_empty():
    """Test validation accepts empty name (uses AI generation)"""
    config = OrchestrationConfig()
    orchestrator = TemplateCreateOrchestrator(config)

    is_valid, error_msg = orchestrator._validate_template_name("")
    assert is_valid is True
    assert error_msg == ""


def test_custom_name_override(mock_analysis, monkeypatch):
    """Test custom template name overrides AI-generated name"""
    # Setup manifest generator mock
    mock_manifest = Mock()
    mock_manifest.name = "ai-generated-name"
    mock_manifest.language = "Python"
    mock_manifest.language_version = "3.9"
    mock_manifest.architecture = "Clean"
    mock_manifest.complexity = 5

    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_manifest
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'ManifestGenerator', mock_generator_class)

    config = OrchestrationConfig(custom_name="my-custom-name")
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase2_manifest_generation(mock_analysis)

    # Assert - manifest name should be overridden
    assert result is not None
    assert result.name == "my-custom-name"


def test_custom_name_override_invalid_name(mock_analysis, monkeypatch):
    """Test custom template name validation failure"""
    # Setup manifest generator mock
    mock_manifest = Mock()
    mock_manifest.name = "ai-generated-name"

    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_manifest
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'ManifestGenerator', mock_generator_class)

    # Test with invalid name (uppercase)
    config = OrchestrationConfig(custom_name="MyInvalidName")
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase2_manifest_generation(mock_analysis)

    # Assert - should return None due to validation failure
    assert result is None


def test_no_custom_name_uses_ai_generated(mock_analysis, monkeypatch):
    """Test that without custom_name, AI-generated name is used"""
    # Setup manifest generator mock
    mock_manifest = Mock()
    mock_manifest.name = "ai-generated-name"
    mock_manifest.language = "Python"
    mock_manifest.language_version = "3.9"
    mock_manifest.architecture = "Clean"
    mock_manifest.complexity = 5

    mock_generator_instance = Mock()
    mock_generator_instance.generate.return_value = mock_manifest
    mock_generator_class = Mock(return_value=mock_generator_instance)

    # Patch in orchestrator module
    patch_orchestrator_class(monkeypatch, 'ManifestGenerator', mock_generator_class)

    config = OrchestrationConfig()  # No custom_name
    orchestrator = TemplateCreateOrchestrator(config)

    # Execute
    result = orchestrator._phase2_manifest_generation(mock_analysis)

    # Assert - AI-generated name should be preserved
    assert result is not None
    assert result.name == "ai-generated-name"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
