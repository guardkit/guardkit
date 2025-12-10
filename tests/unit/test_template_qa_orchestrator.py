"""
Tests for Template Q&A Orchestrator

Tests Q&A orchestration, config integration, and workflow.

TASK-9038: Create /template-qa Command for Optional Customization
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
import importlib

# Import using importlib to avoid 'global' keyword issue
_orchestrator_module = importlib.import_module('installer.core.lib.template_qa_orchestrator')
TemplateQAOrchestrator = _orchestrator_module.TemplateQAOrchestrator
QAOrchestrationConfig = _orchestrator_module.QAOrchestrationConfig
QAOrchestrationResult = _orchestrator_module.QAOrchestrationResult
run_template_qa = _orchestrator_module.run_template_qa

_config_handler_module = importlib.import_module('installer.core.lib.template_config_handler')
TemplateConfigHandler = _config_handler_module.TemplateConfigHandler
ConfigValidationError = _config_handler_module.ConfigValidationError


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create temporary directory for config files."""
    return tmp_path


@pytest.fixture
def mock_qa_session():
    """Create mock QA session."""
    session = Mock()
    session.run = Mock()
    session.answers = {}
    return session


@pytest.fixture
def mock_config_handler():
    """Create mock config handler."""
    handler = Mock(spec=TemplateConfigHandler)
    handler.config_file = Path(".template-create-config.json")
    return handler


@pytest.fixture
def mock_greenfield_answers():
    """Create mock GreenfieldAnswers."""
    answers = Mock()
    answers.template_name = "my-template"
    answers.primary_language = "csharp"
    answers.framework = "maui"
    answers.to_dict = Mock(return_value={
        "template_name": "my-template",
        "template_purpose": "quick_start",
        "primary_language": "csharp",
        "framework": "maui",
        "framework_version": "latest",
        "architecture_pattern": "mvvm",
        "domain_modeling": "rich",
        "layer_organization": "single",
        "standard_folders": ["src", "tests"],
        "unit_testing_framework": "xunit",
        "testing_scope": ["unit", "integration"],
        "test_pattern": "aaa",
        "error_handling": "result",
        "validation_approach": "fluent",
        "dependency_injection": "builtin",
        "configuration_approach": "both"
    })
    return answers


@pytest.fixture
def orchestration_config(temp_config_dir):
    """Create orchestration config."""
    return QAOrchestrationConfig(
        config_path=temp_config_dir,
        resume=False,
        verbose=False
    )


class TestOrchestrationWorkflow:
    """Test complete orchestration workflow."""

    def test_successful_new_config_workflow(
        self,
        orchestration_config,
        mock_qa_session,
        mock_config_handler,
        mock_greenfield_answers,
        temp_config_dir
    ):
        """Test successful workflow creating new config."""
        # Setup mocks
        mock_qa_session.run.return_value = mock_greenfield_answers
        mock_config_handler.save_config.return_value = temp_config_dir / ".template-create-config.json"

        # Create orchestrator
        orchestrator = TemplateQAOrchestrator(
            config=orchestration_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify success
        assert result.success is True
        assert result.config_file == temp_config_dir / ".template-create-config.json"
        assert result.template_name == "my-template"
        assert result.language == "csharp"
        assert result.framework == "maui"
        assert result.error is None

        # Verify calls
        mock_qa_session.run.assert_called_once()
        mock_config_handler.save_config.assert_called_once()

    def test_qa_session_cancelled(
        self,
        orchestration_config,
        mock_qa_session,
        mock_config_handler
    ):
        """Test handling of cancelled Q&A session."""
        # Setup mocks
        mock_qa_session.run.return_value = None  # Session cancelled

        # Create orchestrator
        orchestrator = TemplateQAOrchestrator(
            config=orchestration_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify failure
        assert result.success is False
        assert result.error == "Q&A session cancelled or failed"
        assert result.config_file is None

        # Verify save not called
        mock_config_handler.save_config.assert_not_called()

    def test_config_save_failure(
        self,
        orchestration_config,
        mock_qa_session,
        mock_config_handler,
        mock_greenfield_answers
    ):
        """Test handling of config save failure."""
        # Setup mocks
        mock_qa_session.run.return_value = mock_greenfield_answers
        mock_config_handler.save_config.side_effect = IOError("Permission denied")

        # Create orchestrator
        orchestrator = TemplateQAOrchestrator(
            config=orchestration_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify failure
        assert result.success is False
        assert result.error == "Failed to save configuration"

    def test_keyboard_interrupt_handling(
        self,
        orchestration_config,
        mock_qa_session,
        mock_config_handler
    ):
        """Test handling of keyboard interrupt."""
        # Setup mocks
        mock_qa_session.run.side_effect = KeyboardInterrupt()

        # Create orchestrator
        orchestrator = TemplateQAOrchestrator(
            config=orchestration_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify graceful exit
        assert result.success is False
        assert result.error == "User interrupted"


class TestResumeWorkflow:
    """Test resume from existing config workflow."""

    def test_successful_resume(
        self,
        temp_config_dir,
        mock_qa_session,
        mock_config_handler,
        mock_greenfield_answers
    ):
        """Test successful resume from existing config."""
        # Setup config
        resume_config = QAOrchestrationConfig(
            config_path=temp_config_dir,
            resume=True,
            verbose=False
        )

        # Setup mocks
        mock_config_handler.config_exists.return_value = True
        mock_config_handler.load_config.return_value = mock_greenfield_answers.to_dict()
        mock_config_handler.get_config_summary.return_value = {
            "template_name": "my-template",
            "language": "csharp",
            "framework": "maui",
            "architecture": "mvvm",
            "updated_at": "2024-01-15T10:30:00Z"
        }
        mock_qa_session.run.return_value = mock_greenfield_answers
        mock_config_handler.save_config.return_value = temp_config_dir / ".template-create-config.json"

        # Create orchestrator
        orchestrator = TemplateQAOrchestrator(
            config=resume_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify success
        assert result.success is True
        assert result.config_file is not None

        # Verify config loaded
        mock_config_handler.config_exists.assert_called_once()
        mock_config_handler.load_config.assert_called_once()

    def test_resume_config_not_found(
        self,
        temp_config_dir,
        mock_qa_session,
        mock_config_handler
    ):
        """Test resume when config file not found."""
        # Setup config
        resume_config = QAOrchestrationConfig(
            config_path=temp_config_dir,
            resume=True,
            verbose=False
        )

        # Setup mocks
        mock_config_handler.config_exists.return_value = False

        # Create orchestrator
        orchestrator = TemplateQAOrchestrator(
            config=resume_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify failure
        assert result.success is False
        assert result.error == "Config file not found or invalid"

        # Verify Q&A not run
        mock_qa_session.run.assert_not_called()

    def test_resume_invalid_config(
        self,
        temp_config_dir,
        mock_qa_session,
        mock_config_handler
    ):
        """Test resume when config file is invalid."""
        # Setup config
        resume_config = QAOrchestrationConfig(
            config_path=temp_config_dir,
            resume=True,
            verbose=False
        )

        # Setup mocks
        mock_config_handler.config_exists.return_value = True
        mock_config_handler.load_config.side_effect = ConfigValidationError("Invalid config")

        # Create orchestrator
        orchestrator = TemplateQAOrchestrator(
            config=resume_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify failure
        assert result.success is False
        assert result.error == "Config file not found or invalid"


class TestDependencyInjection:
    """Test dependency injection for testability."""

    def test_custom_qa_session_injection(
        self,
        orchestration_config,
        mock_qa_session,
        mock_config_handler,
        mock_greenfield_answers
    ):
        """Test injection of custom Q&A session."""
        # Setup mocks
        mock_qa_session.run.return_value = mock_greenfield_answers
        mock_config_handler.save_config.return_value = Path(".template-create-config.json")

        # Create orchestrator with injected session
        orchestrator = TemplateQAOrchestrator(
            config=orchestration_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify injected session was used
        assert result.success is True
        mock_qa_session.run.assert_called_once()

    def test_custom_config_handler_injection(
        self,
        orchestration_config,
        mock_qa_session,
        mock_config_handler,
        mock_greenfield_answers
    ):
        """Test injection of custom config handler."""
        # Setup mocks
        mock_qa_session.run.return_value = mock_greenfield_answers
        mock_config_handler.save_config.return_value = Path(".template-create-config.json")

        # Create orchestrator with injected handler
        orchestrator = TemplateQAOrchestrator(
            config=orchestration_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify injected handler was used
        assert result.success is True
        mock_config_handler.save_config.assert_called_once()


class TestConvenienceFunction:
    """Test convenience function."""

    @patch('installer.core.lib.template_qa_orchestrator.TemplateQAOrchestrator')
    def test_run_template_qa_function(self, mock_orchestrator_class, temp_config_dir):
        """Test run_template_qa convenience function."""
        # Setup mocks
        mock_orchestrator = Mock()
        mock_result = QAOrchestrationResult(
            success=True,
            config_file=temp_config_dir / ".template-create-config.json"
        )
        mock_orchestrator.run.return_value = mock_result
        mock_orchestrator_class.return_value = mock_orchestrator

        # Call function
        result = run_template_qa(
            config_path=temp_config_dir,
            resume=False,
            verbose=True
        )

        # Verify orchestrator created and run
        assert result.success is True
        mock_orchestrator_class.assert_called_once()
        mock_orchestrator.run.assert_called_once()


class TestErrorHandling:
    """Test error handling scenarios."""

    def test_unexpected_exception(
        self,
        orchestration_config,
        mock_qa_session,
        mock_config_handler
    ):
        """Test handling of unexpected exceptions."""
        # Setup mocks
        mock_qa_session.run.side_effect = RuntimeError("Unexpected error")

        # Create orchestrator
        orchestrator = TemplateQAOrchestrator(
            config=orchestration_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify error captured
        # The exception is caught by _run_qa_session, which returns None,
        # triggering "Q&A session cancelled or failed" error
        assert result.success is False
        assert result.error == "Q&A session cancelled or failed"

    def test_config_validation_error(
        self,
        orchestration_config,
        mock_qa_session,
        mock_config_handler,
        mock_greenfield_answers
    ):
        """Test handling of config validation errors."""
        # Setup mocks
        mock_qa_session.run.return_value = mock_greenfield_answers
        mock_config_handler.save_config.side_effect = ConfigValidationError("Invalid template name")

        # Create orchestrator
        orchestrator = TemplateQAOrchestrator(
            config=orchestration_config,
            qa_session=mock_qa_session,
            config_handler=mock_config_handler
        )

        # Run
        result = orchestrator.run()

        # Verify failure
        assert result.success is False
        assert result.error == "Failed to save configuration"


class TestIntegration:
    """Integration tests with real components."""

    def test_real_config_handler_integration(
        self,
        temp_config_dir,
        mock_qa_session,
        mock_greenfield_answers
    ):
        """Test integration with real config handler."""
        # Setup config
        config = QAOrchestrationConfig(
            config_path=temp_config_dir,
            resume=False,
            verbose=False
        )

        # Setup mock Q&A session
        mock_qa_session.run.return_value = mock_greenfield_answers

        # Create orchestrator with real config handler
        orchestrator = TemplateQAOrchestrator(
            config=config,
            qa_session=mock_qa_session,
            # config_handler will be created internally
        )

        # Run
        result = orchestrator.run()

        # Verify success
        assert result.success is True
        assert result.config_file.exists()

        # Verify config file content
        handler = TemplateConfigHandler(temp_config_dir)
        loaded_config = handler.load_config()

        assert loaded_config["template_name"] == "my-template"
        assert loaded_config["primary_language"] == "csharp"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
