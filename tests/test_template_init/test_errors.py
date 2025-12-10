"""
Unit tests for template_init error classes
"""

import pytest
import sys
from pathlib import Path

# Add installer path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "installer" / "core" / "commands" / "lib"))

from template_init.errors import (
    TemplateInitError,
    QASessionCancelledError,
    TemplateGenerationError,
    TemplateSaveError,
    AgentSetupError,
)


class TestErrorHierarchy:
    """Test error class hierarchy and inheritance"""

    def test_base_error(self):
        """Test TemplateInitError base class"""
        error = TemplateInitError("Base error")
        assert isinstance(error, Exception)
        assert str(error) == "Base error"

    def test_qa_cancelled_error(self):
        """Test QASessionCancelledError inherits from base"""
        error = QASessionCancelledError("Q&A cancelled")
        assert isinstance(error, TemplateInitError)
        assert isinstance(error, Exception)
        assert str(error) == "Q&A cancelled"

    def test_template_generation_error(self):
        """Test TemplateGenerationError inherits from base"""
        error = TemplateGenerationError("Generation failed")
        assert isinstance(error, TemplateInitError)
        assert isinstance(error, Exception)
        assert str(error) == "Generation failed"

    def test_template_save_error(self):
        """Test TemplateSaveError inherits from base"""
        error = TemplateSaveError("Save failed")
        assert isinstance(error, TemplateInitError)
        assert isinstance(error, Exception)
        assert str(error) == "Save failed"

    def test_agent_setup_error(self):
        """Test AgentSetupError inherits from base"""
        error = AgentSetupError("Agent setup failed")
        assert isinstance(error, TemplateInitError)
        assert isinstance(error, Exception)
        assert str(error) == "Agent setup failed"


class TestErrorRaising:
    """Test raising and catching errors"""

    def test_raise_base_error(self):
        """Test raising base TemplateInitError"""
        with pytest.raises(TemplateInitError) as exc_info:
            raise TemplateInitError("Base error message")

        assert str(exc_info.value) == "Base error message"

    def test_raise_qa_cancelled(self):
        """Test raising QASessionCancelledError"""
        with pytest.raises(QASessionCancelledError) as exc_info:
            raise QASessionCancelledError("User cancelled Q&A")

        assert str(exc_info.value) == "User cancelled Q&A"

    def test_raise_generation_error(self):
        """Test raising TemplateGenerationError"""
        with pytest.raises(TemplateGenerationError) as exc_info:
            raise TemplateGenerationError("AI generation failed")

        assert str(exc_info.value) == "AI generation failed"

    def test_raise_save_error(self):
        """Test raising TemplateSaveError"""
        with pytest.raises(TemplateSaveError) as exc_info:
            raise TemplateSaveError("Disk write failed")

        assert str(exc_info.value) == "Disk write failed"

    def test_raise_agent_error(self):
        """Test raising AgentSetupError"""
        with pytest.raises(AgentSetupError) as exc_info:
            raise AgentSetupError("Agent orchestration failed")

        assert str(exc_info.value) == "Agent orchestration failed"


class TestErrorCatching:
    """Test catching errors at different levels"""

    def test_catch_specific_error(self):
        """Test catching specific error type"""
        caught = False
        try:
            raise QASessionCancelledError("Cancelled")
        except QASessionCancelledError:
            caught = True

        assert caught

    def test_catch_base_error(self):
        """Test catching base error catches specific errors"""
        caught = False
        try:
            raise TemplateGenerationError("Generation failed")
        except TemplateInitError:
            caught = True

        assert caught

    def test_catch_exception(self):
        """Test catching as generic Exception"""
        caught = False
        try:
            raise TemplateSaveError("Save failed")
        except Exception:
            caught = True

        assert caught

    def test_multiple_error_types(self):
        """Test handling multiple error types"""
        errors = [
            QASessionCancelledError("Cancelled"),
            TemplateGenerationError("Generation failed"),
            TemplateSaveError("Save failed"),
            AgentSetupError("Agent failed"),
        ]

        for error in errors:
            with pytest.raises(TemplateInitError):
                raise error


class TestErrorMessages:
    """Test error messages and formatting"""

    def test_error_with_details(self):
        """Test error with detailed message"""
        error = TemplateGenerationError(
            "AI generation failed: Invalid manifest format at line 42"
        )
        assert "AI generation failed" in str(error)
        assert "line 42" in str(error)

    def test_error_with_cause(self):
        """Test error with cause chain"""
        try:
            try:
                raise ValueError("Invalid value")
            except ValueError as e:
                raise TemplateGenerationError("Generation failed") from e
        except TemplateGenerationError as e:
            assert isinstance(e.__cause__, ValueError)
            assert str(e.__cause__) == "Invalid value"

    def test_empty_error_message(self):
        """Test error with empty message"""
        error = TemplateInitError("")
        assert str(error) == ""

    def test_multiline_error_message(self):
        """Test error with multiline message"""
        message = """Template generation failed:
        - Invalid manifest format
        - Missing required fields
        - Syntax errors in CLAUDE.md"""

        error = TemplateGenerationError(message)
        assert "Template generation failed" in str(error)
        assert "Invalid manifest format" in str(error)
        assert "CLAUDE.md" in str(error)
