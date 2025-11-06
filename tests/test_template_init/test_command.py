"""
Unit tests for template_init command orchestrator

Tests the TemplateInitCommand class and orchestration workflow.
"""

import pytest
import json
import tempfile
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Add installer path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "global" / "commands" / "lib"))

from template_init.command import (
    TemplateInitCommand,
    template_init,
)
from template_init.models import GreenfieldTemplate
from template_init.errors import (
    QASessionCancelledError,
    TemplateGenerationError,
    TemplateSaveError,
    AgentSetupError,
)


class MockAnswers:
    """Mock GreenfieldAnswers"""

    template_name = "test-template"
    template_purpose = "Test template"
    primary_language = "Python"
    framework = "FastAPI"
    framework_version = "0.100.0"
    architecture_pattern = "Clean Architecture"
    unit_testing_framework = "pytest"
    error_handling = "Result[T]"


class MockTemplate:
    """Mock GreenfieldTemplate"""

    name = "test-template"
    manifest = {"name": "test", "version": "1.0.0"}
    settings = {"type": "greenfield"}
    claude_md = "# Test Template"
    project_structure = {"src": {"type": "directory"}}
    code_templates = {}
    inferred_analysis = None

    def to_dict(self):
        return {
            "name": self.name,
            "manifest": self.manifest,
            "settings": self.settings,
            "claude_md": self.claude_md,
            "project_structure": self.project_structure,
            "code_templates": self.code_templates,
        }


class MockAgentRecommendation:
    """Mock agent recommendation"""

    def __init__(self):
        self.use_global = [MockAgent("test-agent")]
        self.use_template = []
        self.use_custom = []
        self.generated = []

    def all_agents(self):
        return self.use_global + self.use_template + self.use_custom + self.generated


class MockAgent:
    """Mock agent definition"""

    def __init__(self, name):
        self.name = name
        self.full_definition = f"# {name}\n\nTest agent"


class TestTemplateInitCommand:
    """Test TemplateInitCommand class"""

    def test_create_command(self):
        """Test creating command instance"""
        with tempfile.TemporaryDirectory() as tmpdir:
            command = TemplateInitCommand(template_dir=Path(tmpdir))
            assert command is not None
            assert command.template_dir == Path(tmpdir)
            assert command.enable_external_agents is False

    def test_create_command_with_defaults(self):
        """Test creating command with default template directory"""
        command = TemplateInitCommand()
        assert command.template_dir == Path("installer/local/templates")
        assert command.enable_external_agents is False

    def test_create_command_with_external_agents(self):
        """Test creating command with external agents enabled"""
        command = TemplateInitCommand(enable_external_agents=True)
        assert command.enable_external_agents is True

    def test_execute_success(self):
        """Test successful command execution"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Setup mocks - patch where imports happen
            with patch("builtins.__import__", side_effect=self._mock_imports):
                # Execute
                command = TemplateInitCommand(template_dir=Path(tmpdir))

                # Mock the phase methods directly
                with patch.object(command, "_phase1_qa_session") as mock_phase1:
                    with patch.object(command, "_phase2_ai_generation") as mock_phase2:
                        with patch.object(command, "_phase3_agent_setup") as mock_phase3:
                            # Setup return values
                            mock_phase1.return_value = MockAnswers()
                            mock_phase2.return_value = MockTemplate()
                            mock_phase3.return_value = MockAgentRecommendation()

                            result = command.execute()

                            # Verify
                            assert result is True
                            assert mock_phase1.called
                            assert mock_phase2.called
                            assert mock_phase3.called

                            # Verify files created
                            template_dir = Path(tmpdir) / "test-template"
                            assert template_dir.exists()
                            assert (template_dir / "manifest.json").exists()
                            assert (template_dir / "settings.json").exists()
                            assert (template_dir / "CLAUDE.md").exists()
                            assert (template_dir / "agents").exists()

    def _mock_imports(self, name, *args, **kwargs):
        """Helper to mock imports"""
        if name == "template_qa_session":
            mock_module = Mock()
            mock_module.TemplateQASession = Mock
            return mock_module
        return __import__(name, *args, **kwargs)

    def test_execute_qa_cancelled(self):
        """Test execution when Q&A is cancelled"""
        command = TemplateInitCommand()

        # Mock phase1 to return None (cancelled)
        with patch.object(command, "_phase1_qa_session", return_value=None):
            result = command.execute()

            assert result is False

    def test_execute_keyboard_interrupt(self):
        """Test execution with KeyboardInterrupt"""
        command = TemplateInitCommand()

        # Mock phase1 to raise KeyboardInterrupt
        with patch.object(command, "_phase1_qa_session", side_effect=KeyboardInterrupt()):
            result = command.execute()

            assert result is False

    def test_execute_generation_error(self):
        """Test execution with generation error"""
        command = TemplateInitCommand()

        # Mock phases
        with patch.object(command, "_phase1_qa_session", return_value=MockAnswers()):
            with patch.object(command, "_phase2_ai_generation", side_effect=TemplateGenerationError("Generation failed")):
                result = command.execute()

                assert result is False

    def test_phase1_qa_session(self):
        """Test Phase 1: Q&A session - uses fallback"""
        command = TemplateInitCommand()

        # Test with minimal fallback (since TemplateQASession may not be available)
        with patch("builtins.input", side_effect=[
            "test-template",
            "Test template",
            "Python",
            "FastAPI",
            "Clean Architecture",
            "pytest",
            "Result[T]"
        ]):
            answers = command._phase1_qa_session()

            # Either gets real Q&A or fallback
            assert answers is not None
            assert hasattr(answers, "template_name")
            assert hasattr(answers, "primary_language")

    def test_phase1_qa_cancelled(self):
        """Test Phase 1 when Q&A cancelled - uses fallback"""
        command = TemplateInitCommand()

        # Test cancellation in fallback (empty input)
        with patch("builtins.input", return_value=""):
            with pytest.raises(QASessionCancelledError):
                command._phase1_qa_session()

    def test_phase2_ai_generation(self):
        """Test Phase 2: AI generation - uses real generator"""
        command = TemplateInitCommand()

        # Use real AITemplateGenerator (it's a stub, works fine)
        template = command._phase2_ai_generation(MockAnswers())

        assert template is not None
        assert hasattr(template, "name")
        assert hasattr(template, "manifest")
        assert hasattr(template, "settings")

    def test_phase2_generation_error(self):
        """Test Phase 2 with generation error"""
        from template_init.ai_generator import AITemplateGenerator

        command = TemplateInitCommand()

        # Mock the generator to raise an error
        with patch.object(AITemplateGenerator, "generate", side_effect=Exception("Generation failed")):
            with pytest.raises(TemplateGenerationError):
                command._phase2_ai_generation(MockAnswers())

    def test_phase3_agent_setup(self):
        """Test Phase 3: Agent setup"""
        command = TemplateInitCommand()
        template = MockTemplate()

        # Use fallback since TASK-009 not implemented
        agents = command._phase3_agent_setup(template)

        assert agents is not None
        assert hasattr(agents, "all_agents")
        assert len(agents.all_agents()) > 0

    def test_phase3_fallback_agent_setup(self):
        """Test Phase 3 fallback implementation"""
        command = TemplateInitCommand()
        template = MockTemplate()

        agents = command._fallback_agent_setup(template)

        assert agents is not None
        assert hasattr(agents, "use_global")
        assert hasattr(agents, "use_template")
        assert hasattr(agents, "use_custom")
        assert hasattr(agents, "generated")
        assert len(agents.use_global) > 0

    def test_phase4_save_template(self):
        """Test Phase 4: Save template"""
        with tempfile.TemporaryDirectory() as tmpdir:
            command = TemplateInitCommand(template_dir=Path(tmpdir))
            template = MockTemplate()
            agents = MockAgentRecommendation()

            command._phase4_save_template(template, agents)

            # Verify files created
            template_dir = Path(tmpdir) / "test-template"
            assert template_dir.exists()
            assert (template_dir / "manifest.json").exists()
            assert (template_dir / "settings.json").exists()
            assert (template_dir / "CLAUDE.md").exists()
            assert (template_dir / "agents").exists()
            assert (template_dir / "agents" / "test-agent.md").exists()

    def test_phase4_save_with_code_templates(self):
        """Test Phase 4 save with code templates"""
        with tempfile.TemporaryDirectory() as tmpdir:
            command = TemplateInitCommand(template_dir=Path(tmpdir))

            template = MockTemplate()
            template.code_templates = {
                "main.py": "print('hello')",
                "test.py": "def test(): pass",
            }

            agents = MockAgentRecommendation()

            command._phase4_save_template(template, agents)

            # Verify code templates saved
            template_dir = Path(tmpdir) / "test-template"
            templates_dir = template_dir / "templates"
            assert templates_dir.exists()
            assert (templates_dir / "main.py").exists()
            assert (templates_dir / "test.py").exists()

    def test_phase4_save_error(self):
        """Test Phase 4 with save error"""
        # Use invalid directory to trigger error
        command = TemplateInitCommand(template_dir=Path("/invalid/path/that/does/not/exist"))
        template = MockTemplate()
        agents = MockAgentRecommendation()

        with pytest.raises(TemplateSaveError):
            command._phase4_save_template(template, agents)

    def test_count_agents(self):
        """Test agent counting"""
        command = TemplateInitCommand()
        agents = MockAgentRecommendation()

        count = command._count_agents(agents)
        assert count == 1  # MockAgentRecommendation has 1 agent

    def test_count_agents_fallback(self):
        """Test agent counting with fallback object"""
        command = TemplateInitCommand()

        # Create object without all_agents() method
        class MinimalAgents:
            use_global = [MockAgent("agent1"), MockAgent("agent2")]
            use_template = []
            use_custom = []
            generated = [MockAgent("generated1")]

        minimal = MinimalAgents()
        count = command._count_agents(minimal)
        assert count == 3  # 2 global + 1 generated

    def test_minimal_qa_fallback(self):
        """Test minimal Q&A fallback"""
        command = TemplateInitCommand()

        # Mock input() calls
        inputs = [
            "test-template",
            "Test template purpose",
            "Python",
            "FastAPI",
            "Clean Architecture",
            "pytest",
            "Result[T]",
        ]

        with patch("builtins.input", side_effect=inputs):
            answers = command._minimal_qa_fallback()

            assert answers is not None
            assert answers.template_name == "test-template"
            assert answers.primary_language == "Python"
            assert answers.framework == "FastAPI"

    def test_minimal_qa_fallback_cancelled(self):
        """Test minimal Q&A fallback when cancelled"""
        command = TemplateInitCommand()

        # Return empty string to simulate cancellation
        with patch("builtins.input", return_value=""):
            answers = command._minimal_qa_fallback()
            assert answers is None


class TestTemplateInitEntryPoint:
    """Test template_init entry point function"""

    @patch("template_init.command.TemplateInitCommand")
    def test_template_init_function(self, mock_command_class):
        """Test template_init() entry point"""
        mock_command = Mock()
        mock_command.execute.return_value = True
        mock_command_class.return_value = mock_command

        result = template_init()

        assert result is True
        assert mock_command.execute.called

    @patch("template_init.command.TemplateInitCommand")
    def test_template_init_with_custom_dir(self, mock_command_class):
        """Test template_init() with custom directory"""
        mock_command = Mock()
        mock_command.execute.return_value = True
        mock_command_class.return_value = mock_command

        custom_dir = Path("/custom/path")
        result = template_init(template_dir=custom_dir)

        assert result is True
        mock_command_class.assert_called_once_with(template_dir=custom_dir)


class TestCompleteWorkflow:
    """Integration-like tests for complete workflow"""

    def test_complete_workflow_success(self):
        """Test complete workflow from Q&A to save - using real components"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Execute complete workflow using real components
            command = TemplateInitCommand(template_dir=Path(tmpdir))

            # Mock only the phase methods to control flow
            with patch.object(command, "_phase1_qa_session", return_value=MockAnswers()):
                # Let phase2 and phase3 use real implementations
                result = command.execute()

                # Verify success
                assert result is True

                # Verify files created
                template_dir = Path(tmpdir) / "test-template"
                assert template_dir.exists()

                # Verify manifest
                manifest_file = template_dir / "manifest.json"
                assert manifest_file.exists()
                with open(manifest_file) as f:
                    manifest = json.load(f)
                assert "name" in manifest
                assert manifest["name"] == "test-template"

                # Verify settings
                settings_file = template_dir / "settings.json"
                assert settings_file.exists()
                with open(settings_file) as f:
                    settings = json.load(f)
                assert "template" in settings

                # Verify CLAUDE.md
                claude_file = template_dir / "CLAUDE.md"
                assert claude_file.exists()
                with open(claude_file) as f:
                    claude_md = f.read()
                assert len(claude_md) > 0

                # Verify agents directory
                agents_dir = template_dir / "agents"
                assert agents_dir.exists()
                assert len(list(agents_dir.glob("*.md"))) > 0
