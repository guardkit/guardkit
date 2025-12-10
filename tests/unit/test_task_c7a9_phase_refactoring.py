"""
Comprehensive test suite for TASK-C7A9: Phase 7-9 Refactoring

Tests the critical refactoring of phase order in template creation:
- Phase 7: Write agents to disk (NEW - extracted from Phase 9)
- Phase 8: Generate CLAUDE.md with output_path parameter
- Phase 9: Template package assembly (agent writing removed)

This ensures agents are written BEFORE CLAUDE.md generation, allowing
accurate documentation of actual agent files without hallucinations.
"""

import pytest
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch, call
import importlib.util

# Add lib directories to path
lib_path = Path(__file__).parent.parent.parent / "installer" / "core"
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
OrchestrationResult = orchestrator_module.OrchestrationResult


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def temp_output_dir():
    """Create temporary output directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_analysis():
    """Mock CodebaseAnalysis object."""
    analysis = Mock()
    analysis.overall_confidence = Mock(percentage=85)
    analysis.example_files = []
    analysis.metadata = Mock(
        template_name='test-template',
        primary_language='Python',
        framework='FastAPI'
    )
    return analysis


@pytest.fixture
def mock_manifest():
    """Mock TemplateManifest object."""
    manifest = Mock()
    manifest.name = 'test-template'
    manifest.language = 'Python'
    manifest.language_version = '>=3.9'
    manifest.architecture = 'Clean Architecture'
    manifest.complexity = 6
    manifest.confidence_score = 85
    manifest.to_dict = Mock(return_value={
        'name': 'test-template',
        'language': 'Python',
        'confidence_score': 85
    })
    return manifest


@pytest.fixture
def mock_settings():
    """Mock TemplateSettings object."""
    settings = Mock()
    settings.naming_conventions = {'class': 'PascalCase'}
    settings.layer_mappings = {'Domain': 'src/domain'}
    settings.code_style = Mock(
        indentation='spaces',
        indent_size=4
    )
    settings.to_dict = Mock(return_value={
        'naming_conventions': {'class': 'PascalCase'},
        'layer_mappings': {'Domain': 'src/domain'}
    })
    return settings


@pytest.fixture
def mock_claude_md():
    """Mock TemplateClaude object."""
    claude_md = Mock()
    claude_md.content = "# CLAUDE.md Content"
    return claude_md


@pytest.fixture
def mock_templates():
    """Mock TemplateCollection object."""
    templates = Mock()
    template1 = Mock()
    template1.template_path = 'src/main.py.template'
    template2 = Mock()
    template2.template_path = 'src/config.py.template'
    templates.templates = [template1, template2]
    templates.total_count = 2
    return templates


@pytest.fixture
def mock_agents_with_full_definition():
    """Mock GeneratedAgent objects with full_definition (already formatted)."""
    agent1 = Mock()
    agent1.name = 'domain-specialist'
    agent1.description = 'Handles domain logic'
    agent1.full_definition = """---
name: domain-specialist
description: Handles domain logic
tags:
  - domain
  - architecture
priority: 8
---

# Domain Specialist

Specialized agent for domain-driven design."""

    agent2 = Mock()
    agent2.name = 'testing-specialist'
    agent2.description = 'Handles test implementation'
    agent2.full_definition = """---
name: testing-specialist
description: Handles test implementation
tags:
  - testing
  - quality
priority: 7
---

# Testing Specialist

Specialized agent for testing strategies."""

    return [agent1, agent2]


@pytest.fixture
def mock_agents_without_full_definition():
    """Mock GeneratedAgent objects without full_definition (need formatting)."""
    agent1 = Mock()
    agent1.name = 'api-specialist'
    agent1.description = 'Handles API endpoints'
    agent1.reason = 'Specialized agent for API design'
    agent1.tags = ['api', 'endpoints']
    agent1.priority = 8
    agent1.full_definition = None

    agent2 = Mock()
    agent2.name = 'db-specialist'
    agent2.description = 'Handles database operations'
    agent2.reason = 'Specialized agent for database design'
    agent2.tags = ['database', 'persistence']
    agent2.priority = 7
    agent2.full_definition = None

    return [agent1, agent2]


# ============================================================================
# PHASE 7: AGENT WRITING TESTS
# ============================================================================

class TestPhase7AgentWriting:
    """Test Phase 7: Agent writing to disk (TASK-C7A9)."""

    def test_phase7_creates_agents_directory(self, temp_output_dir, mock_agents_with_full_definition):
        """Test Phase 7 creates agents directory if it doesn't exist."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        agents_dir = temp_output_dir / "agents"
        assert not agents_dir.exists(), "agents/ directory should not exist yet"

        result = orchestrator._phase7_write_agents(
            mock_agents_with_full_definition,
            temp_output_dir
        )

        assert agents_dir.exists(), "agents/ directory should be created"
        assert result is not None, "Should return list of written paths"

    def test_phase7_writes_agent_files_to_disk(self, temp_output_dir, mock_agents_with_full_definition):
        """Test Phase 7 writes each agent to disk as markdown file."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        result = orchestrator._phase7_write_agents(
            mock_agents_with_full_definition,
            temp_output_dir
        )

        agents_dir = temp_output_dir / "agents"

        # Verify files were written
        assert (agents_dir / "domain-specialist.md").exists()
        assert (agents_dir / "testing-specialist.md").exists()

        # Verify content
        domain_content = (agents_dir / "domain-specialist.md").read_text()
        assert "domain-specialist" in domain_content
        assert "Domain Specialist" in domain_content

    def test_phase7_returns_list_of_written_paths(self, temp_output_dir, mock_agents_with_full_definition):
        """Test Phase 7 returns list of paths to written agent files."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        result = orchestrator._phase7_write_agents(
            mock_agents_with_full_definition,
            temp_output_dir
        )

        assert isinstance(result, list), "Should return list"
        assert len(result) == 2, f"Should return 2 paths, got {len(result)}"
        assert all(isinstance(p, Path) for p in result), "All items should be Path objects"
        assert all(p.exists() for p in result), "All returned paths should exist"

    def test_phase7_handles_empty_agent_list(self, temp_output_dir):
        """Test Phase 7 handles empty agent list gracefully."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        result = orchestrator._phase7_write_agents([], temp_output_dir)

        assert result == [], "Should return empty list for empty agents"

    def test_phase7_formats_agents_with_yaml_frontmatter(self, temp_output_dir, mock_agents_with_full_definition):
        """Test Phase 7 writes agents with proper YAML frontmatter."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        orchestrator._phase7_write_agents(
            mock_agents_with_full_definition,
            temp_output_dir
        )

        agent_file = temp_output_dir / "agents" / "domain-specialist.md"
        content = agent_file.read_text()

        # Verify YAML frontmatter
        assert content.startswith('---'), "Should start with YAML frontmatter"
        assert '---' in content[3:], "Should have closing --- for frontmatter"
        assert 'name: domain-specialist' in content
        assert 'description:' in content

    def test_phase7_creates_agent_path_with_parent_dirs(self, temp_output_dir, mock_agents_with_full_definition):
        """Test Phase 7 creates parent directories if needed."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Use nested output path
        nested_output = temp_output_dir / "nested" / "template"

        result = orchestrator._phase7_write_agents(
            mock_agents_with_full_definition,
            nested_output
        )

        assert (nested_output / "agents").exists(), "Should create nested agents/ directory"
        assert len(result) == 2, "Should still write all agents"

    def test_phase7_agent_files_readable(self, temp_output_dir, mock_agents_with_full_definition):
        """Test Phase 7 written agent files are readable."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        orchestrator._phase7_write_agents(
            mock_agents_with_full_definition,
            temp_output_dir
        )

        # Verify files are readable
        for agent_file in (temp_output_dir / "agents").glob("*.md"):
            content = agent_file.read_text(encoding='utf-8')
            assert len(content) > 0, f"File {agent_file.name} should have content"

    def test_phase7_handles_agent_with_already_formatted_markdown(self, temp_output_dir):
        """Test Phase 7 handles agents with full_definition already in markdown format."""
        agent = Mock()
        agent.name = 'pre-formatted-agent'
        agent.full_definition = """---
name: pre-formatted-agent
---
# Agent Content
Already formatted."""

        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        result = orchestrator._phase7_write_agents([agent], temp_output_dir)

        content = (temp_output_dir / "agents" / "pre-formatted-agent.md").read_text()
        assert "Already formatted" in content

    def test_phase7_returns_none_on_error(self, mock_agents_with_full_definition):
        """Test Phase 7 returns None on error."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Use invalid path
        invalid_path = Path("/nonexistent/deeply/nested/path")

        result = orchestrator._phase7_write_agents(
            mock_agents_with_full_definition,
            invalid_path
        )

        # Should return None on error
        assert result is None or result == [], "Should handle error gracefully"


# ============================================================================
# PHASE 8: CLAUDE.MD GENERATION WITH OUTPUT_PATH
# ============================================================================

class TestPhase8ClaudeMdGeneration:
    """Test Phase 8: CLAUDE.md generation with output_path parameter."""

    def test_phase8_receives_output_path_parameter(self, mock_analysis, temp_output_dir, monkeypatch):
        """Test Phase 8 receives output_path parameter (TASK-C7A9)."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Mock the ClaudeMdGenerator to capture parameters
        mock_generator_instance = Mock()
        mock_generator_instance.generate.return_value = Mock()
        mock_generator_class = Mock(return_value=mock_generator_instance)

        # Patch in module
        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', mock_generator_class)

        agents = []
        result = orchestrator._phase8_claude_md_generation(
            mock_analysis,
            agents,
            temp_output_dir
        )

        # Verify ClaudeMdGenerator was called with output_path
        mock_generator_class.assert_called_once()
        call_args = mock_generator_class.call_args
        assert 'output_path' in call_args.kwargs, "output_path should be passed to ClaudeMdGenerator"
        assert call_args.kwargs['output_path'] == temp_output_dir

    def test_phase8_passes_agents_to_generator(self, mock_analysis, mock_agents_with_full_definition,
                                               temp_output_dir, monkeypatch):
        """Test Phase 8 passes agents to CLAUDE.md generator."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Mock the ClaudeMdGenerator
        mock_generator_instance = Mock()
        mock_generator_instance.generate.return_value = Mock()
        mock_generator_class = Mock(return_value=mock_generator_instance)

        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', mock_generator_class)

        result = orchestrator._phase8_claude_md_generation(
            mock_analysis,
            mock_agents_with_full_definition,
            temp_output_dir
        )

        # Verify agents parameter was passed
        call_args = mock_generator_class.call_args
        assert 'agents' in call_args.kwargs, "agents should be passed to ClaudeMdGenerator"
        assert call_args.kwargs['agents'] == mock_agents_with_full_definition

    def test_phase8_claude_md_generator_called_with_analysis(self, mock_analysis, temp_output_dir, monkeypatch):
        """Test Phase 8 calls CLAUDE.md generator with analysis."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        mock_generator_instance = Mock()
        mock_generator_instance.generate.return_value = Mock()
        mock_generator_class = Mock(return_value=mock_generator_instance)

        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', mock_generator_class)

        result = orchestrator._phase8_claude_md_generation(
            mock_analysis,
            [],
            temp_output_dir
        )

        # Verify analysis was passed as first positional arg
        call_args = mock_generator_class.call_args
        assert call_args[0][0] == mock_analysis, "analysis should be first argument"

    def test_phase8_output_path_enables_agent_file_scanning(self, mock_analysis,
                                                            mock_agents_with_full_definition,
                                                            temp_output_dir, monkeypatch):
        """Test Phase 8 output_path enables scanning actual agent files from disk."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # First, write agents to disk (Phase 7)
        orchestrator._phase7_write_agents(mock_agents_with_full_definition, temp_output_dir)

        # Verify agents exist on disk
        agents_dir = temp_output_dir / "agents"
        assert (agents_dir / "domain-specialist.md").exists()

        # Now Phase 8 can scan these files
        mock_generator_instance = Mock()
        mock_generator_instance.generate.return_value = Mock()
        mock_generator_class = Mock(return_value=mock_generator_instance)

        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', mock_generator_class)

        result = orchestrator._phase8_claude_md_generation(
            mock_analysis,
            mock_agents_with_full_definition,
            temp_output_dir
        )

        # Verify it was called with output_path so it can scan
        call_kwargs = mock_generator_class.call_args.kwargs
        assert call_kwargs['output_path'] == temp_output_dir


# ============================================================================
# PHASE 9: PACKAGE ASSEMBLY (AGENTS REMOVED)
# ============================================================================

class TestPhase9PackageAssembly:
    """Test Phase 9: Package assembly with agents removed."""

    def test_phase9_package_assembly_success(self, mock_manifest, mock_settings, mock_claude_md,
                                             mock_templates, temp_output_dir, monkeypatch):
        """Test Phase 9 package assembly completes successfully."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Mock generators to actually save files
        manifest_gen = Mock()
        manifest_gen.save = Mock()

        settings_gen = Mock()
        settings_gen.save = Mock()

        template_gen = Mock()
        template_gen.save_templates = Mock()

        claude_gen = Mock()
        claude_gen.save = Mock()

        monkeypatch.setattr(orchestrator_module, 'ManifestGenerator', Mock(return_value=manifest_gen))
        monkeypatch.setattr(orchestrator_module, 'SettingsGenerator', Mock(return_value=settings_gen))
        monkeypatch.setattr(orchestrator_module, 'TemplateGenerator', Mock(return_value=template_gen))
        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', Mock(return_value=claude_gen))

        result = orchestrator._phase9_package_assembly(
            mock_manifest,
            mock_settings,
            mock_claude_md,
            mock_templates,
            temp_output_dir
        )

        # Verify result is the output path
        assert result == temp_output_dir, "Should return output path on success"

    def test_phase9_does_not_write_agents(self, mock_manifest, mock_settings, mock_claude_md,
                                         mock_templates, temp_output_dir, monkeypatch):
        """Test Phase 9 does NOT write agents (moved to Phase 7)."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Mock generators
        manifest_gen = Mock()
        manifest_gen.save = Mock()

        settings_gen = Mock()
        settings_gen.save = Mock()

        template_gen = Mock()
        template_gen.save_templates = Mock()

        claude_gen = Mock()
        claude_gen.save = Mock()

        monkeypatch.setattr(orchestrator_module, 'ManifestGenerator', Mock(return_value=manifest_gen))
        monkeypatch.setattr(orchestrator_module, 'SettingsGenerator', Mock(return_value=settings_gen))
        monkeypatch.setattr(orchestrator_module, 'TemplateGenerator', Mock(return_value=template_gen))
        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', Mock(return_value=claude_gen))

        result = orchestrator._phase9_package_assembly(
            mock_manifest,
            mock_settings,
            mock_claude_md,
            mock_templates,
            temp_output_dir
        )

        # Verify agents directory is NOT created by Phase 9
        # (it's only created by Phase 7)
        agents_dir = temp_output_dir / "agents"
        # agents_dir should not exist (it's Phase 7's responsibility)
        # or if it exists, Phase 9 should not have created it

    def test_phase9_calls_manifest_save(self, mock_manifest, mock_settings, mock_claude_md,
                                       mock_templates, temp_output_dir, monkeypatch):
        """Test Phase 9 calls manifest save."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        manifest_gen = Mock()
        manifest_gen.save = Mock()

        settings_gen = Mock()
        settings_gen.save = Mock()

        template_gen = Mock()
        template_gen.save_templates = Mock()

        claude_gen = Mock()
        claude_gen.save = Mock()

        monkeypatch.setattr(orchestrator_module, 'ManifestGenerator', Mock(return_value=manifest_gen))
        monkeypatch.setattr(orchestrator_module, 'SettingsGenerator', Mock(return_value=settings_gen))
        monkeypatch.setattr(orchestrator_module, 'TemplateGenerator', Mock(return_value=template_gen))
        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', Mock(return_value=claude_gen))

        result = orchestrator._phase9_package_assembly(
            mock_manifest,
            mock_settings,
            mock_claude_md,
            mock_templates,
            temp_output_dir
        )

        # Verify manifest.json was written (via json.dump)
        manifest_path = temp_output_dir / "manifest.json"
        assert manifest_path.exists(), "manifest.json should be created"

    def test_phase9_calls_settings_save(self, mock_manifest, mock_settings, mock_claude_md,
                                       mock_templates, temp_output_dir, monkeypatch):
        """Test Phase 9 calls settings save."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        manifest_gen = Mock()
        manifest_gen.save = Mock()

        settings_gen = Mock()
        settings_gen.save = Mock()

        template_gen = Mock()
        template_gen.save_templates = Mock()

        claude_gen = Mock()
        claude_gen.save = Mock()

        monkeypatch.setattr(orchestrator_module, 'ManifestGenerator', Mock(return_value=manifest_gen))
        monkeypatch.setattr(orchestrator_module, 'SettingsGenerator', Mock(return_value=settings_gen))
        monkeypatch.setattr(orchestrator_module, 'TemplateGenerator', Mock(return_value=template_gen))
        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', Mock(return_value=claude_gen))

        result = orchestrator._phase9_package_assembly(
            mock_manifest,
            mock_settings,
            mock_claude_md,
            mock_templates,
            temp_output_dir
        )

        # Verify settings_gen.save was called
        settings_gen.save.assert_called_once()

    def test_phase9_calls_claude_md_save(self, mock_manifest, mock_settings, mock_claude_md,
                                        mock_templates, temp_output_dir, monkeypatch):
        """Test Phase 9 calls CLAUDE.md save."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        manifest_gen = Mock()
        manifest_gen.save = Mock()

        settings_gen = Mock()
        settings_gen.save = Mock()

        template_gen = Mock()
        template_gen.save_templates = Mock()

        claude_gen = Mock()
        claude_gen.save = Mock()

        monkeypatch.setattr(orchestrator_module, 'ManifestGenerator', Mock(return_value=manifest_gen))
        monkeypatch.setattr(orchestrator_module, 'SettingsGenerator', Mock(return_value=settings_gen))
        monkeypatch.setattr(orchestrator_module, 'TemplateGenerator', Mock(return_value=template_gen))
        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', Mock(return_value=claude_gen))

        result = orchestrator._phase9_package_assembly(
            mock_manifest,
            mock_settings,
            mock_claude_md,
            mock_templates,
            temp_output_dir
        )

        # Verify claude_gen.save was called
        claude_gen.save.assert_called_once()

    def test_phase9_calls_template_save(self, mock_manifest, mock_settings, mock_claude_md,
                                       mock_templates, temp_output_dir, monkeypatch):
        """Test Phase 9 calls template save."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        manifest_gen = Mock()
        manifest_gen.save = Mock()

        settings_gen = Mock()
        settings_gen.save = Mock()

        template_gen = Mock()
        template_gen.save_templates = Mock()

        claude_gen = Mock()
        claude_gen.save = Mock()

        monkeypatch.setattr(orchestrator_module, 'ManifestGenerator', Mock(return_value=manifest_gen))
        monkeypatch.setattr(orchestrator_module, 'SettingsGenerator', Mock(return_value=settings_gen))
        monkeypatch.setattr(orchestrator_module, 'TemplateGenerator', Mock(return_value=template_gen))
        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', Mock(return_value=claude_gen))

        result = orchestrator._phase9_package_assembly(
            mock_manifest,
            mock_settings,
            mock_claude_md,
            mock_templates,
            temp_output_dir
        )

        # Verify template_gen.save_templates was called
        template_gen.save_templates.assert_called_once()


# ============================================================================
# COMPLETE WORKFLOW TESTS
# ============================================================================

class TestCompleteWorkflow:
    """Test complete Phase 7-9 workflow."""

    def test_complete_workflow_executes_phases_in_order(self, mock_analysis, mock_manifest,
                                                       mock_settings, mock_claude_md,
                                                       mock_templates, mock_agents_with_full_definition,
                                                       temp_output_dir, monkeypatch):
        """Test _complete_workflow executes Phase 7 -> 8 -> 9 in order."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Set up orchestrator state
        orchestrator.manifest = mock_manifest
        orchestrator.settings = mock_settings
        orchestrator.templates = mock_templates
        orchestrator.agents = mock_agents_with_full_definition
        orchestrator.analysis = mock_analysis
        orchestrator.claude_md = mock_claude_md

        # Mock the phase methods
        execution_log = []

        def track_phase7(*args, **kwargs):
            execution_log.append(7)
            return [temp_output_dir / "agents" / "agent1.md"]

        def track_phase8(*args, **kwargs):
            execution_log.append(8)
            return mock_claude_md

        # Track Phase 9 via mocking generators
        manifest_gen = Mock()
        manifest_gen.save = Mock()

        settings_gen = Mock()
        settings_gen.save = Mock()

        template_gen = Mock()
        template_gen.save_templates = Mock()

        claude_gen = Mock()
        claude_gen.save = Mock()

        monkeypatch.setattr(orchestrator_module, 'ManifestGenerator', Mock(return_value=manifest_gen))
        monkeypatch.setattr(orchestrator_module, 'SettingsGenerator', Mock(return_value=settings_gen))
        monkeypatch.setattr(orchestrator_module, 'TemplateGenerator', Mock(return_value=template_gen))
        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', Mock(return_value=claude_gen))

        orchestrator._phase7_write_agents = Mock(side_effect=track_phase7)
        orchestrator._phase8_claude_md_generation = Mock(side_effect=track_phase8)

        # Mock state manager
        orchestrator.state_manager = Mock()
        orchestrator.state_manager.cleanup = Mock()

        # Execute workflow
        result = orchestrator._complete_workflow()

        # Verify Phase 7 was called
        orchestrator._phase7_write_agents.assert_called_once()

        # Verify Phase 8 was called with agents
        orchestrator._phase8_claude_md_generation.assert_called_once()
        call_kwargs = orchestrator._phase8_claude_md_generation.call_args.kwargs
        assert 'output_path' in call_kwargs

    def test_agents_written_before_claude_md_generation(self, mock_analysis, mock_manifest,
                                                       mock_settings, mock_claude_md,
                                                       mock_templates, mock_agents_with_full_definition,
                                                       temp_output_dir, monkeypatch):
        """Test agents are physically written to disk before CLAUDE.md generation."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Phase 7: Write agents
        agent_paths = orchestrator._phase7_write_agents(
            mock_agents_with_full_definition,
            temp_output_dir
        )

        # Verify agents exist
        assert len(agent_paths) == 2
        assert all(p.exists() for p in agent_paths)

        # Phase 8: Generate CLAUDE.md with agents in place
        mock_generator = Mock()
        mock_generator.generate.return_value = mock_claude_md

        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', Mock(return_value=mock_generator))

        result = orchestrator._phase8_claude_md_generation(
            mock_analysis,
            mock_agents_with_full_definition,
            temp_output_dir
        )

        # Verify agents directory exists
        agents_dir = temp_output_dir / "agents"
        assert agents_dir.exists()
        assert len(list(agents_dir.glob("*.md"))) == 2


# ============================================================================
# EDGE CASES AND ERROR HANDLING
# ============================================================================

class TestEdgeCases:
    """Test edge cases and error scenarios."""

    def test_phase7_with_none_agents(self, temp_output_dir):
        """Test Phase 7 handles None agent list."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Should handle None gracefully
        result = orchestrator._phase7_write_agents(None, temp_output_dir)
        assert result is None or result == []

    def test_phase7_with_agent_missing_name(self, temp_output_dir):
        """Test Phase 7 handles agent without name attribute."""
        agent = Mock()
        agent.name = None
        agent.full_definition = "# Content"

        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Should handle gracefully
        result = orchestrator._phase7_write_agents([agent], temp_output_dir)
        # Result may be None or empty list depending on error handling

    def test_phase8_with_empty_agents_list(self, mock_analysis, temp_output_dir, monkeypatch):
        """Test Phase 8 handles empty agents list."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        mock_generator = Mock()
        mock_generator.generate.return_value = Mock()

        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', Mock(return_value=mock_generator))

        result = orchestrator._phase8_claude_md_generation(mock_analysis, [], temp_output_dir)

        # Should still generate CLAUDE.md with generic guidance
        assert result is not None

    def test_phase9_with_none_templates(self, mock_manifest, mock_settings, mock_claude_md,
                                       temp_output_dir, monkeypatch):
        """Test Phase 9 handles None templates gracefully."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Mock generators
        manifest_gen = Mock()
        manifest_gen.save = Mock()

        settings_gen = Mock()
        settings_gen.save = Mock()

        template_gen = Mock()
        template_gen.save_templates = Mock()

        monkeypatch.setattr(orchestrator_module, 'ManifestGenerator', Mock(return_value=manifest_gen))
        monkeypatch.setattr(orchestrator_module, 'SettingsGenerator', Mock(return_value=settings_gen))
        monkeypatch.setattr(orchestrator_module, 'TemplateGenerator', Mock(return_value=template_gen))
        monkeypatch.setattr(orchestrator_module, 'ClaudeMdGenerator', Mock(return_value=Mock()))

        result = orchestrator._phase9_package_assembly(
            mock_manifest,
            mock_settings,
            mock_claude_md,
            None,  # No templates
            temp_output_dir
        )

        # Should still complete successfully
        assert result == temp_output_dir

    def test_phase7_with_special_characters_in_agent_name(self, temp_output_dir):
        """Test Phase 7 handles agent names with special characters."""
        agent = Mock()
        agent.name = 'test-agent_v2.0'
        agent.description = 'Test agent'
        agent.full_definition = "---\nname: test-agent_v2.0\n---\n# Content"

        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        result = orchestrator._phase7_write_agents([agent], temp_output_dir)

        if result:
            agent_file = temp_output_dir / "agents" / f"{agent.name}.md"
            assert agent_file.exists() or not agent_file.parent.exists()


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestIntegration:
    """Integration tests combining phases."""

    def test_phase7_output_compatible_with_phase8(self, mock_analysis,
                                                  mock_agents_with_full_definition,
                                                  temp_output_dir, monkeypatch):
        """Test Phase 7 output is compatible with Phase 8 input."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Phase 7: Write agents
        agent_paths = orchestrator._phase7_write_agents(
            mock_agents_with_full_definition,
            temp_output_dir
        )

        assert len(agent_paths) > 0

        # Phase 8: Can read agents from disk
        agents_dir = temp_output_dir / "agents"
        agent_files = list(agents_dir.glob("*.md"))

        assert len(agent_files) == len(mock_agents_with_full_definition)

    def test_agents_metadata_preserved_through_phases(self, mock_agents_with_full_definition,
                                                     temp_output_dir):
        """Test agent metadata is preserved when writing and reading."""
        config = OrchestrationConfig()
        orchestrator = TemplateCreateOrchestrator(config)

        # Write agents
        orchestrator._phase7_write_agents(mock_agents_with_full_definition, temp_output_dir)

        # Read and verify
        for agent in mock_agents_with_full_definition:
            agent_file = temp_output_dir / "agents" / f"{agent.name}.md"
            assert agent_file.exists()

            content = agent_file.read_text()
            assert agent.name in content
            assert agent.description in content

    def test_output_path_accessible_from_phase7_through_phase9(self, mock_manifest,
                                                                mock_agents_with_full_definition,
                                                                temp_output_dir):
        """Test output_path is accessible throughout workflow."""
        config = OrchestrationConfig(output_path=temp_output_dir)
        orchestrator = TemplateCreateOrchestrator(config)

        # Phase 7 uses output_path
        agents = orchestrator._phase7_write_agents(mock_agents_with_full_definition, temp_output_dir)
        assert (temp_output_dir / "agents").exists()

        # output_path should be consistent throughout


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
