"""
Test Suite for Template Q&A Session.

Tests the main Q&A session flow including question asking, validation,
conditional logic, and session persistence.

Part of TASK-001B: Interactive Q&A Session for /template-init (Greenfield)
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import sys
import json

# Add installer path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "installer" / "global" / "commands" / "lib"))

from template_qa_session import (
    GreenfieldAnswers,
    TemplateQASession,
)
from template_qa_questions import Question, should_ask_question
from template_qa_persistence import (
    save_session,
    load_session,
    session_exists,
    delete_session,
)


# ============================================================================
# Test GreenfieldAnswers Dataclass
# ============================================================================

def test_greenfield_answers_creation():
    """Test creating GreenfieldAnswers with required fields"""
    answers = GreenfieldAnswers(
        template_name="test-template",
        template_purpose="quick_start",
        primary_language="python",
        framework="fastapi",
        framework_version="latest",
        architecture_pattern="clean",
        domain_modeling="rich",
        layer_organization="single",
        standard_folders=["src", "tests"],
        unit_testing_framework="auto",
        testing_scope=["unit", "integration"],
        test_pattern="aaa",
        error_handling="result",
        validation_approach="fluent",
        dependency_injection="builtin",
        configuration_approach="both",
    )

    assert answers.template_name == "test-template"
    assert answers.primary_language == "python"
    assert answers.framework == "fastapi"


def test_greenfield_answers_to_dict():
    """Test converting GreenfieldAnswers to dictionary"""
    answers = GreenfieldAnswers(
        template_name="test-template",
        template_purpose="quick_start",
        primary_language="python",
        framework="fastapi",
        framework_version="latest",
        architecture_pattern="clean",
        domain_modeling="rich",
        layer_organization="single",
        standard_folders=["src", "tests"],
        unit_testing_framework="auto",
        testing_scope=["unit"],
        test_pattern="aaa",
        error_handling="result",
        validation_approach="fluent",
        dependency_injection="builtin",
        configuration_approach="both",
    )

    data = answers.to_dict()
    assert isinstance(data, dict)
    assert data["template_name"] == "test-template"
    assert data["primary_language"] == "python"


def test_greenfield_answers_from_dict():
    """Test creating GreenfieldAnswers from dictionary"""
    data = {
        "template_name": "test-template",
        "template_purpose": "quick_start",
        "primary_language": "python",
        "framework": "fastapi",
        "framework_version": "latest",
        "architecture_pattern": "clean",
        "domain_modeling": "rich",
        "layer_organization": "single",
        "standard_folders": ["src", "tests"],
        "unit_testing_framework": "auto",
        "testing_scope": ["unit"],
        "test_pattern": "aaa",
        "error_handling": "result",
        "validation_approach": "fluent",
        "dependency_injection": "builtin",
        "configuration_approach": "both",
    }

    answers = GreenfieldAnswers.from_dict(data)
    assert answers.template_name == "test-template"
    assert answers.primary_language == "python"


def test_greenfield_answers_optional_fields():
    """Test GreenfieldAnswers with optional fields"""
    answers = GreenfieldAnswers(
        template_name="test",
        template_purpose="quick_start",
        primary_language="python",
        framework="fastapi",
        framework_version="latest",
        architecture_pattern="clean",
        domain_modeling="rich",
        layer_organization="single",
        standard_folders=["src"],
        unit_testing_framework="auto",
        testing_scope=["unit"],
        test_pattern="aaa",
        error_handling="result",
        validation_approach="fluent",
        dependency_injection="builtin",
        configuration_approach="both",
        # Optional fields
        ui_architecture="mvvm",
        navigation_pattern="recommended",
        data_access="repository",
    )

    assert answers.ui_architecture == "mvvm"
    assert answers.navigation_pattern == "recommended"
    assert answers.data_access == "repository"


# ============================================================================
# Test Session Initialization
# ============================================================================

def test_session_initialization():
    """Test TemplateQASession initialization"""
    session = TemplateQASession()
    assert session.answers == {}
    assert session.result is None
    assert session.skip_qa is False


def test_session_initialization_with_skip():
    """Test TemplateQASession initialization with skip_qa flag"""
    session = TemplateQASession(skip_qa=True)
    assert session.skip_qa is True


def test_session_initialization_with_session_file():
    """Test TemplateQASession initialization with custom session file"""
    custom_file = Path("/tmp/custom-session.json")
    session = TemplateQASession(session_file=custom_file)
    assert session.session_file == custom_file


# ============================================================================
# Test Conditional Question Logic
# ============================================================================

def test_should_ask_question_no_dependencies():
    """Test should_ask_question with no dependencies"""
    question = Question(
        id="test_question",
        section="Test",
        text="Test question?",
        type="text",
    )

    assert should_ask_question(question, {}) is True


def test_should_ask_question_with_boolean_dependency():
    """Test should_ask_question with boolean dependency"""
    question = Question(
        id="test_question",
        section="Test",
        text="Test question?",
        type="text",
        depends_on={"has_feature": True},
    )

    # Should ask when dependency is met
    assert should_ask_question(question, {"has_feature": True}) is True

    # Should not ask when dependency is not met
    assert should_ask_question(question, {"has_feature": False}) is False


def test_should_ask_question_with_list_dependency():
    """Test should_ask_question with list dependency"""
    question = Question(
        id="test_question",
        section="Test",
        text="Test question?",
        type="text",
        depends_on={"framework": ["maui", "blazor", "wpf"]},
    )

    # Should ask when framework matches
    assert should_ask_question(question, {"framework": "maui"}) is True
    assert should_ask_question(question, {"framework": "blazor"}) is True

    # Should not ask when framework doesn't match
    assert should_ask_question(question, {"framework": "fastapi"}) is False


def test_should_ask_question_missing_dependency_key():
    """Test should_ask_question when dependency key is missing"""
    question = Question(
        id="test_question",
        section="Test",
        text="Test question?",
        type="text",
        depends_on={"has_feature": True},
    )

    # Should not ask when dependency key is missing
    assert should_ask_question(question, {}) is False


# ============================================================================
# Test Framework Detection Helpers
# ============================================================================

def test_is_ui_framework():
    """Test UI framework detection"""
    session = TemplateQASession()

    # UI frameworks
    assert session._is_ui_framework("maui") is True
    assert session._is_ui_framework("blazor") is True
    assert session._is_ui_framework("wpf") is True
    assert session._is_ui_framework("react-nextjs") is True
    assert session._is_ui_framework("angular") is True

    # Non-UI frameworks
    assert session._is_ui_framework("fastapi") is False
    assert session._is_ui_framework("aspnet-core") is False


def test_is_backend_framework():
    """Test backend framework detection"""
    session = TemplateQASession()

    # Backend frameworks
    assert session._is_backend_framework("aspnet-core") is True
    assert session._is_backend_framework("fastapi") is True
    assert session._is_backend_framework("django") is True
    assert session._is_backend_framework("nestjs") is True

    # Non-backend frameworks
    assert session._is_backend_framework("maui") is False
    assert session._is_backend_framework("react-nextjs") is False


# ============================================================================
# Test Session Persistence
# ============================================================================

def test_save_and_load_session(tmp_path):
    """Test saving and loading session"""
    session_file = tmp_path / "test-session.json"
    answers = {
        "template_name": "test-template",
        "primary_language": "python",
        "framework": "fastapi",
    }

    # Save session
    save_session(answers, session_file)
    assert session_file.exists()

    # Load session
    loaded = load_session(session_file)
    assert loaded["template_name"] == "test-template"
    assert loaded["primary_language"] == "python"


def test_session_exists(tmp_path):
    """Test checking if session exists"""
    session_file = tmp_path / "test-session.json"

    # Should not exist initially
    assert session_exists(session_file) is False

    # Create session
    save_session({"test": "data"}, session_file)

    # Should exist now
    assert session_exists(session_file) is True


def test_delete_session(tmp_path):
    """Test deleting session"""
    session_file = tmp_path / "test-session.json"

    # Create session
    save_session({"test": "data"}, session_file)
    assert session_file.exists()

    # Delete session
    result = delete_session(session_file)
    assert result is True
    assert not session_file.exists()

    # Try deleting non-existent session
    result = delete_session(session_file)
    assert result is False


# ============================================================================
# Test Skip Q&A Mode
# ============================================================================

@patch("template_qa_session.input")
def test_skip_qa_uses_defaults(mock_input):
    """Test that skip_qa mode uses default values"""
    session = TemplateQASession(skip_qa=True)

    # Mock the entire flow
    with patch.object(session, "_section1_identity") as mock_s1, \
         patch.object(session, "_section2_technology") as mock_s2, \
         patch.object(session, "_section3_architecture") as mock_s3, \
         patch.object(session, "_section4_structure") as mock_s4, \
         patch.object(session, "_section5_testing") as mock_s5, \
         patch.object(session, "_section6_error_handling") as mock_s6, \
         patch.object(session, "_section7_dependencies") as mock_s7, \
         patch.object(session, "_section10_documentation") as mock_s10:

        # Set up minimal answers for building result
        session.answers = {
            "template_name": "my-template",
            "template_purpose": "quick_start",
            "primary_language": "csharp",
            "framework": "maui",
            "framework_version": "latest",
            "architecture_pattern": "mvvm",
            "domain_modeling": "rich",
            "layer_organization": "single",
            "standard_folders": ["src", "tests"],
            "unit_testing_framework": "auto",
            "testing_scope": ["unit", "integration"],
            "test_pattern": "aaa",
            "error_handling": "result",
            "validation_approach": "fluent",
            "dependency_injection": "builtin",
            "configuration_approach": "both",
        }

        result = session.run()

        # Should not prompt for input in skip mode
        mock_input.assert_not_called()

        # Result should use defaults
        assert result is not None
        assert isinstance(result, GreenfieldAnswers)


# ============================================================================
# Test Question Asking
# ============================================================================

@patch("template_qa_session.input")
def test_ask_text_question_with_default(mock_input):
    """Test asking text question with default value"""
    mock_input.return_value = ""  # User presses Enter (use default)

    session = TemplateQASession()
    question = Question(
        id="test_question",
        section="Test",
        text="Test question?",
        type="text",
        default="default_value",
    )

    result = session._ask_text(question)
    assert result == "default_value"


@patch("template_qa_session.input")
def test_ask_choice_question(mock_input):
    """Test asking choice question"""
    mock_input.return_value = "1"  # Select first option

    session = TemplateQASession()
    question = Question(
        id="test_question",
        section="Test",
        text="Test question?",
        type="choice",
        choices=[
            ("Option A", "a"),
            ("Option B", "b"),
        ],
    )

    result = session._ask_choice(question)
    assert result == "a"


@patch("template_qa_session.input")
def test_ask_multi_choice_question(mock_input):
    """Test asking multi-choice question"""
    mock_input.return_value = "1,2"  # Select first two options

    session = TemplateQASession()
    question = Question(
        id="test_question",
        section="Test",
        text="Test question?",
        type="multi_choice",
        choices=[
            ("Option A", "a", True),
            ("Option B", "b", False),
            ("Option C", "c", True),
        ],
    )

    result = session._ask_multi_choice(question)
    assert result == ["a", "b"]


@patch("template_qa_session.input")
def test_ask_confirm_question(mock_input):
    """Test asking confirmation question"""
    mock_input.return_value = "y"

    session = TemplateQASession()
    question = Question(
        id="test_question",
        section="Test",
        text="Test question?",
        type="confirm",
        default=True,
    )

    result = session._ask_confirm(question)
    assert result is True


# ============================================================================
# Test Build Result
# ============================================================================

def test_build_result():
    """Test building GreenfieldAnswers from session answers"""
    session = TemplateQASession()
    session.answers = {
        "template_name": "test-template",
        "template_purpose": "production",
        "primary_language": "python",
        "framework": "fastapi",
        "framework_version": "latest",
        "architecture_pattern": "clean",
        "domain_modeling": "rich",
        "layer_organization": "by-layer",
        "standard_folders": ["src", "tests", "docs"],
        "unit_testing_framework": "pytest",
        "testing_scope": ["unit", "integration", "e2e"],
        "test_pattern": "bdd",
        "error_handling": "exceptions",
        "validation_approach": "manual",
        "dependency_injection": "manual",
        "configuration_approach": "env",
        "api_pattern": "rest",
        "has_documentation": True,
        "documentation_input_method": "paths",
    }

    result = session._build_result()

    assert isinstance(result, GreenfieldAnswers)
    assert result.template_name == "test-template"
    assert result.template_purpose == "production"
    assert result.primary_language == "python"
    assert result.framework == "fastapi"
    assert result.api_pattern == "rest"


# ============================================================================
# Test Error Handling
# ============================================================================

@patch("template_qa_session.input")
@patch("template_qa_session.display")
def test_keyboard_interrupt_saves_session(mock_display, mock_input, tmp_path):
    """Test that Ctrl+C saves the session"""
    session_file = tmp_path / "interrupted-session.json"
    session = TemplateQASession(session_file=session_file)

    # Simulate KeyboardInterrupt during Q&A
    mock_input.side_effect = KeyboardInterrupt()

    session.answers = {"template_name": "test"}

    with pytest.raises(SystemExit):
        session.run()

    # Session should be saved
    assert session_file.exists()
    loaded = load_session(session_file)
    assert loaded["template_name"] == "test"


# ============================================================================
# Integration Tests
# ============================================================================

def test_complete_session_flow_with_defaults():
    """Test complete session flow using skip mode"""
    session = TemplateQASession(skip_qa=True)

    # Set minimal answers
    session.answers = {
        "template_name": "integration-test",
        "template_purpose": "quick_start",
        "primary_language": "csharp",
        "framework": "maui",
        "framework_version": "latest",
        "architecture_pattern": "mvvm",
        "domain_modeling": "rich",
        "layer_organization": "single",
        "standard_folders": ["src", "tests"],
        "unit_testing_framework": "auto",
        "testing_scope": ["unit"],
        "test_pattern": "aaa",
        "error_handling": "result",
        "validation_approach": "fluent",
        "dependency_injection": "builtin",
        "configuration_approach": "both",
    }

    with patch.object(session, "_section1_identity"), \
         patch.object(session, "_section2_technology"), \
         patch.object(session, "_section3_architecture"), \
         patch.object(session, "_section4_structure"), \
         patch.object(session, "_section5_testing"), \
         patch.object(session, "_section6_error_handling"), \
         patch.object(session, "_section7_dependencies"), \
         patch.object(session, "_section10_documentation"):

        result = session.run()

        assert result is not None
        assert isinstance(result, GreenfieldAnswers)
        assert result.template_name == "integration-test"


def test_session_serialization_round_trip(tmp_path):
    """Test that session can be saved and loaded without data loss"""
    session_file = tmp_path / "roundtrip-session.json"

    # Create session with answers
    original_answers = {
        "template_name": "roundtrip-test",
        "primary_language": "python",
        "framework": "fastapi",
        "testing_scope": ["unit", "integration"],
        "standard_folders": ["src", "tests", "docs"],
    }

    # Save
    save_session(original_answers, session_file)

    # Load
    loaded_answers = load_session(session_file)

    # Verify no data loss
    assert loaded_answers == original_answers


# ============================================================================
# Test Summary
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
