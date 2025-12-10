"""
Unit tests for TASK-769D: template_create_orchestrator with AgentBridgeInvoker integration

Tests orchestrator passes bridge_invoker to CodebaseAnalyzer.
"""

import pytest
import sys
import importlib.util
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import tempfile

# Add lib directory to path
lib_path = Path(__file__).parent.parent.parent / "installer" / "core"
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


class TestOrchestratorWithBridgeInvoker:
    """Test TemplateCreateOrchestrator with AgentBridgeInvoker"""

    @pytest.fixture
    def temp_codebase(self):
        """Create a temporary codebase directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            (tmppath / "src").mkdir()
            (tmppath / "src" / "main.py").write_text("from fastapi import FastAPI")
            yield tmppath

    @pytest.fixture
    def mock_bridge_invoker(self):
        """Mock AgentBridgeInvoker"""
        mock = Mock()
        mock.invoke.return_value = '{"technology": {"primary_language": "Python"}}'
        return mock

    @pytest.fixture
    def mock_ai_analyzer(self):
        """Mock CodebaseAnalyzer"""
        mock_analysis = Mock()
        mock_analysis.overall_confidence = Mock(percentage=85)
        mock_analysis.codebase_path = '/test/codebase'
        mock_analysis.technology = Mock(
            primary_language='Python',
            frameworks=['FastAPI'],
            testing_frameworks=['pytest']
        )
        mock_analysis.architecture = Mock(
            architectural_style='Clean Architecture',
            patterns=['Repository'],
            layers=[]
        )
        mock_analysis.example_files = []
        mock_analysis.metadata = Mock(
            template_name='test-template',
            primary_language='Python',
            framework='FastAPI'
        )

        mock_class = Mock()
        mock_instance = Mock()
        mock_instance.analyze_codebase.return_value = mock_analysis
        mock_class.return_value = mock_instance
        return mock_class, mock_instance

    def test_orchestrator_passes_bridge_to_analyzer(self, temp_codebase, mock_bridge_invoker, monkeypatch):
        """Test orchestrator passes bridge_invoker to CodebaseAnalyzer"""
        mock_ai_class, mock_ai_instance = self.mock_ai_analyzer()

        # Patch CodebaseAnalyzer
        monkeypatch.setattr(orchestrator_module, "CodebaseAnalyzer", mock_ai_class)

        # Patch other dependencies to prevent actual execution
        monkeypatch.setattr(orchestrator_module, "ManifestGenerator", Mock(return_value=Mock(
            generate=Mock(return_value=Mock(to_dict=Mock(return_value={})))
        )))
        monkeypatch.setattr(orchestrator_module, "SettingsGenerator", Mock(return_value=Mock(
            generate=Mock(return_value=Mock(to_dict=Mock(return_value={})))
        )))
        monkeypatch.setattr(orchestrator_module, "TemplateGenerator", Mock(return_value=Mock(
            generate_templates=Mock(return_value=[])
        )))

        config = OrchestrationConfig(
            codebase_path=str(temp_codebase),
            output_dir=str(temp_codebase / "output"),
            bridge_invoker=mock_bridge_invoker,
            skip_agents=True,
            dry_run=True
        )

        orchestrator = TemplateCreateOrchestrator(config)

        try:
            orchestrator.run()
        except:
            pass  # Ignore execution errors, we just want to check initialization

        # Verify CodebaseAnalyzer was called with bridge_invoker
        mock_ai_class.assert_called()
        call_kwargs = mock_ai_class.call_args[1]
        assert 'bridge_invoker' in call_kwargs
        assert call_kwargs['bridge_invoker'] is mock_bridge_invoker

    def test_orchestrator_without_bridge_invoker(self, temp_codebase, monkeypatch):
        """Test orchestrator works without bridge_invoker (backward compatible)"""
        mock_ai_class, mock_ai_instance = self.mock_ai_analyzer()

        monkeypatch.setattr(orchestrator_module, "CodebaseAnalyzer", mock_ai_class)
        monkeypatch.setattr(orchestrator_module, "ManifestGenerator", Mock(return_value=Mock(
            generate=Mock(return_value=Mock(to_dict=Mock(return_value={})))
        )))
        monkeypatch.setattr(orchestrator_module, "SettingsGenerator", Mock(return_value=Mock(
            generate=Mock(return_value=Mock(to_dict=Mock(return_value={})))
        )))
        monkeypatch.setattr(orchestrator_module, "TemplateGenerator", Mock(return_value=Mock(
            generate_templates=Mock(return_value=[])
        )))

        config = OrchestrationConfig(
            codebase_path=str(temp_codebase),
            output_dir=str(temp_codebase / "output"),
            bridge_invoker=None,  # Explicitly None
            skip_agents=True,
            dry_run=True
        )

        orchestrator = TemplateCreateOrchestrator(config)

        try:
            orchestrator.run()
        except:
            pass

        # Verify CodebaseAnalyzer was called, bridge_invoker can be None
        mock_ai_class.assert_called()
        call_kwargs = mock_ai_class.call_args[1]
        assert 'bridge_invoker' in call_kwargs
        assert call_kwargs['bridge_invoker'] is None

    def test_config_stores_bridge_invoker(self, mock_bridge_invoker):
        """Test OrchestrationConfig stores bridge_invoker"""
        config = OrchestrationConfig(
            codebase_path="/test/path",
            output_dir="/test/output",
            bridge_invoker=mock_bridge_invoker
        )

        assert config.bridge_invoker is mock_bridge_invoker

    def test_config_default_bridge_invoker_is_none(self):
        """Test OrchestrationConfig defaults bridge_invoker to None"""
        config = OrchestrationConfig(
            codebase_path="/test/path",
            output_dir="/test/output"
        )

        assert config.bridge_invoker is None

    def test_phase1_passes_bridge_to_analyzer(self, temp_codebase, mock_bridge_invoker, monkeypatch):
        """Test _phase1_ai_analysis passes bridge_invoker to analyzer"""
        mock_ai_class, mock_ai_instance = self.mock_ai_analyzer()

        monkeypatch.setattr(orchestrator_module, "CodebaseAnalyzer", mock_ai_class)

        config = OrchestrationConfig(
            codebase_path=str(temp_codebase),
            output_dir=str(temp_codebase / "output"),
            bridge_invoker=mock_bridge_invoker,
            dry_run=True
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator._phase1_ai_analysis()

        # Verify bridge was passed
        mock_ai_class.assert_called_once()
        call_kwargs = mock_ai_class.call_args[1]
        assert call_kwargs['bridge_invoker'] is mock_bridge_invoker

        # Verify analyze was called
        mock_ai_instance.analyze_codebase.assert_called_once()

    def test_phase1_uses_metadata_when_provided(self, temp_codebase, monkeypatch):
        """Test _phase1_ai_analysis uses metadata when skip_ai_analysis=True"""
        mock_ai_class, mock_ai_instance = self.mock_ai_analyzer()

        monkeypatch.setattr(orchestrator_module, "CodebaseAnalyzer", mock_ai_class)

        metadata = {
            "primary_language": "Python",
            "framework": "FastAPI",
            "template_name": "my-template"
        }

        config = OrchestrationConfig(
            codebase_path=str(temp_codebase),
            output_dir=str(temp_codebase / "output"),
            skip_ai_analysis=True,
            metadata=metadata,
            dry_run=True
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator._phase1_ai_analysis()

        # When skip_ai_analysis=True, should use metadata, not call analyzer
        mock_ai_instance.analyze_codebase.assert_not_called()

    def test_integration_full_flow_with_bridge(self, temp_codebase, mock_bridge_invoker, monkeypatch):
        """Integration test: full flow with bridge_invoker"""
        # Mock all phases
        mock_analysis = Mock()
        mock_analysis.overall_confidence = Mock(percentage=85)
        mock_analysis.technology = Mock(primary_language='Python', frameworks=['FastAPI'])
        mock_analysis.architecture = Mock(architectural_style='Clean', patterns=[])
        mock_analysis.metadata = Mock(template_name='test', primary_language='Python')
        mock_analysis.example_files = []

        mock_ai_class = Mock()
        mock_ai_instance = Mock()
        mock_ai_instance.analyze_codebase.return_value = mock_analysis
        mock_ai_class.return_value = mock_ai_instance

        mock_manifest = Mock()
        mock_manifest.to_dict.return_value = {"name": "test"}

        mock_settings = Mock()
        mock_settings.to_dict.return_value = {"language": "Python"}

        monkeypatch.setattr(orchestrator_module, "CodebaseAnalyzer", mock_ai_class)
        monkeypatch.setattr(orchestrator_module, "ManifestGenerator", Mock(return_value=Mock(
            generate=Mock(return_value=mock_manifest)
        )))
        monkeypatch.setattr(orchestrator_module, "SettingsGenerator", Mock(return_value=Mock(
            generate=Mock(return_value=mock_settings)
        )))
        monkeypatch.setattr(orchestrator_module, "TemplateGenerator", Mock(return_value=Mock(
            generate_templates=Mock(return_value=[])
        )))
        monkeypatch.setattr(orchestrator_module, "AgentGenerator", Mock(return_value=Mock(
            generate_agents=Mock(return_value=[])
        )))
        monkeypatch.setattr(orchestrator_module, "ClaudeMdGenerator", Mock(return_value=Mock(
            generate=Mock(return_value=Mock(content="# CLAUDE.md"))
        )))

        config = OrchestrationConfig(
            codebase_path=str(temp_codebase),
            output_dir=str(temp_codebase / "output"),
            bridge_invoker=mock_bridge_invoker,
            skip_agents=True,
            dry_run=True
        )

        orchestrator = TemplateCreateOrchestrator(config)
        result = orchestrator.run()

        # Verify success
        assert result.success is True
        # Verify bridge was used in phase 1
        mock_ai_class.assert_called_once()
        assert mock_ai_class.call_args[1]['bridge_invoker'] is mock_bridge_invoker
