"""
Edge Case Tests for Template Q&A Implementation.

Tests edge cases, error conditions, and boundary scenarios for all Q&A modules.
Part of TASK-001B: Interactive Q&A Session for /template-init (Greenfield)
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
import sys
import tempfile
import json

# Add installer path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "installer" / "core" / "commands" / "lib"))

from template_qa_display import (
    print_banner,
    print_section_header,
    print_question,
    print_choices,
)
from template_qa_persistence import (
    save_session,
    load_session,
    session_exists,
    delete_session,
    PersistenceError,
    DEFAULT_SESSION_FILE,
)
from template_qa_validator import ValidationError
from template_qa_questions import Question


# ============================================================================
# Edge Cases: Display Functions (stdin/stdout)
# ============================================================================

def test_print_banner_custom_width(capsys):
    """Test banner printing with custom width"""
    print_banner("Test", width=30)
    captured = capsys.readouterr()
    assert "Test" in captured.out
    assert "=" * 30 in captured.out


def test_print_banner_long_text(capsys):
    """Test banner with text longer than default width"""
    long_text = "This is a very long banner text that exceeds normal width"
    print_banner(long_text)
    captured = capsys.readouterr()
    assert long_text in captured.out


def test_print_section_header_custom_width(capsys):
    """Test section header with custom width"""
    print_section_header("Custom", width=40)
    captured = capsys.readouterr()
    assert "Custom" in captured.out
    assert "-" * 40 in captured.out


def test_print_question_without_help(capsys):
    """Test question printing without help text"""
    print_question("What is your name?")
    captured = capsys.readouterr()
    assert "What is your name?" in captured.out
    assert "(" not in captured.out


def test_print_question_with_help(capsys):
    """Test question printing with help text"""
    print_question("Select framework", help_text="Choose one")
    captured = capsys.readouterr()
    assert "Select framework" in captured.out
    assert "Choose one" in captured.out
    assert "(" in captured.out


def test_print_choices_with_numbers(capsys):
    """Test printing choices with numbers"""
    choices = [("Option A", "a"), ("Option B", "b")]
    print_choices(choices, show_numbers=True)
    captured = capsys.readouterr()
    assert "[1]" in captured.out
    assert "[2]" in captured.out
    assert "Option A" in captured.out


def test_print_choices_without_numbers(capsys):
    """Test printing choices without numbers"""
    choices = [("Option A", "a"), ("Option B", "b")]
    print_choices(choices, show_numbers=False)
    captured = capsys.readouterr()
    assert "- Option A" in captured.out
    assert "- Option B" in captured.out
    assert "[1]" not in captured.out


def test_print_choices_with_default_indicator(capsys):
    """Test printing choices with default indicator"""
    choices = [("Option A", "a", False), ("Option B", "b", True)]
    print_choices(choices)
    captured = capsys.readouterr()
    assert "Option B" in captured.out
    assert "[DEFAULT]" in captured.out


def test_print_choices_empty_list(capsys):
    """Test printing empty choices list"""
    print_choices([])
    captured = capsys.readouterr()
    assert captured.out.strip() == ""


# ============================================================================
# Edge Cases: Persistence Functions
# ============================================================================

def test_save_session_creates_directories(tmp_path):
    """Test save_session creates parent directories"""
    session_file = tmp_path / "deep" / "nested" / "session.json"
    answers = {"name": "test"}
    result = save_session(answers, session_file)
    assert result.exists()
    assert session_file.exists()


def test_save_session_without_metadata(tmp_path):
    """Test save_session without metadata"""
    session_file = tmp_path / "session.json"
    answers = {"name": "test"}
    save_session(answers, session_file, include_metadata=False)

    with open(session_file) as f:
        data = json.load(f)
    assert "metadata" not in data
    assert data["answers"] == answers


def test_save_session_with_metadata(tmp_path):
    """Test save_session with metadata"""
    session_file = tmp_path / "session.json"
    answers = {"name": "test"}
    save_session(answers, session_file, include_metadata=True)

    with open(session_file) as f:
        data = json.load(f)
    assert "metadata" in data
    assert "saved_at" in data["metadata"]
    assert "version" in data["metadata"]


def test_save_session_default_path(tmp_path, monkeypatch):
    """Test save_session uses default path"""
    monkeypatch.chdir(tmp_path)
    answers = {"name": "test"}
    result = save_session(answers)
    assert result.name == DEFAULT_SESSION_FILE


def test_save_session_unicode_content(tmp_path):
    """Test save_session with unicode content"""
    session_file = tmp_path / "session.json"
    answers = {"name": "Test™", "description": "日本語"}
    save_session(answers, session_file)

    loaded = load_session(session_file)
    assert loaded["name"] == "Test™"
    assert loaded["description"] == "日本語"


def test_save_session_permission_error(tmp_path):
    """Test save_session with permission error"""
    # Create read-only directory
    readonly_dir = tmp_path / "readonly"
    readonly_dir.mkdir()
    session_file = readonly_dir / "session.json"
    readonly_dir.chmod(0o444)

    try:
        with pytest.raises(PersistenceError, match="Failed to save"):
            save_session({"name": "test"}, session_file)
    finally:
        readonly_dir.chmod(0o755)


def test_load_session_file_not_found(tmp_path):
    """Test load_session with non-existent file"""
    missing_file = tmp_path / "missing.json"
    with pytest.raises(PersistenceError, match="Session file not found"):
        load_session(missing_file)


def test_load_session_invalid_json(tmp_path):
    """Test load_session with invalid JSON"""
    session_file = tmp_path / "session.json"
    session_file.write_text("{ invalid json }")

    with pytest.raises(PersistenceError):
        load_session(session_file)


def test_load_session_legacy_format(tmp_path):
    """Test load_session with legacy format (no 'answers' key)"""
    session_file = tmp_path / "session.json"
    legacy_data = {"name": "test", "version": "1"}
    session_file.write_text(json.dumps(legacy_data))

    result = load_session(session_file)
    assert result == legacy_data


def test_load_session_new_format(tmp_path):
    """Test load_session with new format (with 'answers' key)"""
    session_file = tmp_path / "session.json"
    new_data = {
        "answers": {"name": "test"},
        "metadata": {"saved_at": "2024-01-01T00:00:00Z"}
    }
    session_file.write_text(json.dumps(new_data))

    result = load_session(session_file)
    assert result == {"name": "test"}


def test_load_session_default_path(tmp_path, monkeypatch):
    """Test load_session uses default path"""
    monkeypatch.chdir(tmp_path)
    session_file = Path(DEFAULT_SESSION_FILE)
    session_file.write_text(json.dumps({"answers": {"test": "value"}}))

    result = load_session()
    assert result == {"test": "value"}


def test_session_exists_file_exists(tmp_path):
    """Test session_exists returns True when file exists"""
    session_file = tmp_path / "session.json"
    session_file.write_text("{}")
    assert session_exists(session_file)


def test_session_exists_file_missing(tmp_path):
    """Test session_exists returns False when file missing"""
    session_file = tmp_path / "missing.json"
    assert not session_exists(session_file)


def test_session_exists_default_path(tmp_path, monkeypatch):
    """Test session_exists with default path"""
    monkeypatch.chdir(tmp_path)
    Path(DEFAULT_SESSION_FILE).write_text("{}")
    assert session_exists()


def test_delete_session_success(tmp_path):
    """Test delete_session removes file"""
    session_file = tmp_path / "session.json"
    session_file.write_text("{}")
    assert session_file.exists()

    delete_session(session_file)
    assert not session_file.exists()


def test_delete_session_missing_file(tmp_path):
    """Test delete_session with missing file"""
    session_file = tmp_path / "missing.json"
    # Should not raise error
    delete_session(session_file)


def test_delete_session_default_path(tmp_path, monkeypatch):
    """Test delete_session with default path"""
    monkeypatch.chdir(tmp_path)
    session_file = Path(DEFAULT_SESSION_FILE)
    session_file.write_text("{}")

    delete_session()
    assert not session_file.exists()


# ============================================================================
# Edge Cases: Question Object
# ============================================================================

def test_question_with_all_properties():
    """Test Question with all optional properties"""
    q = Question(
        id="test_id",
        section="Test Section",
        text="Test?",
        type="choice",
        choices=[("a", "1"), ("b", "2")],
        default="1",
        help_text="Help info",
        validation="choice",
        depends_on={"other_id": "value"}
    )
    assert q.id == "test_id"
    assert q.section == "Test Section"
    assert q.help_text == "Help info"


def test_question_minimal_properties():
    """Test Question with minimal properties"""
    q = Question(id="minimal", section="Test", text="Min?", type="text")
    assert q.id == "minimal"
    assert q.text == "Min?"
    assert q.section == "Test"
    assert q.default is None
    assert q.choices is None


def test_question_with_empty_choices():
    """Test Question with empty choices list"""
    q = Question(
        id="empty",
        section="Test",
        text="Choose?",
        type="choice",
        choices=[]
    )
    assert q.choices == []


# ============================================================================
# Edge Cases: Validator Functions
# ============================================================================

def test_validate_url_edge_cases():
    """Test URL validation edge cases"""
    from template_qa_validator import validate_url

    # Valid URLs
    assert validate_url("https://example.com")
    assert validate_url("http://example.com/path")
    assert validate_url("https://sub.example.co.uk/path?query=value")


def test_validate_version_valid_formats():
    """Test version string validation with valid formats"""
    from template_qa_validator import validate_version_string

    # Valid versions
    assert validate_version_string("1.0.0")
    assert validate_version_string("1.0")
    assert validate_version_string("2.1-beta")


def test_validate_numeric_list_edge_cases():
    """Test numeric list validation edge cases"""
    from template_qa_validator import validate_numeric_list

    # Valid numeric lists
    assert validate_numeric_list("1,2,3")
    assert validate_numeric_list("1")
    assert validate_numeric_list("1,2")


def test_validate_text_length_boundaries():
    """Test text length validation at boundaries"""
    from template_qa_validator import validate_text_length

    # At boundaries
    assert validate_text_length("abc", min_length=3)
    assert validate_text_length("abc", max_length=3)
    assert validate_text_length("abcd", min_length=2, max_length=5)


def test_validate_text_length_violations():
    """Test text length validation with violations"""
    from template_qa_validator import validate_text_length

    with pytest.raises(ValidationError, match="at least"):
        validate_text_length("ab", min_length=3)

    with pytest.raises(ValidationError, match="at most"):
        validate_text_length("abcdef", max_length=5)


# ============================================================================
# Integration: Circular Dependencies
# ============================================================================

def test_question_with_conditional_logic():
    """Test question with conditional dependencies"""
    q = Question(
        id="follow_up",
        section="Test",
        text="Follow-up?",
        type="text",
        depends_on={"initial": "yes"}
    )
    assert q.depends_on == {"initial": "yes"}


def test_multiple_questions_creation():
    """Test creating multiple Question objects"""
    questions = [
        Question(id="q1", section="S1", text="Q1?", type="text"),
        Question(id="q2", section="S1", text="Q2?", type="choice", choices=[("a", "1")]),
        Question(id="q3", section="S2", text="Q3?", type="confirm"),
    ]
    assert len(questions) == 3
    assert questions[0].id == "q1"
    assert questions[1].type == "choice"


# ============================================================================
# Boundary Tests: Large Inputs
# ============================================================================

def test_large_number_of_questions():
    """Test creating many questions"""
    questions = [
        Question(id=f"q{i}", section="Test", text=f"Question {i}?", type="text")
        for i in range(100)
    ]

    assert len(questions) == 100
    assert questions[50].id == "q50"


def test_very_long_text_input():
    """Test validation of very long text"""
    from template_qa_validator import validate_text_length

    long_text = "x" * 10000
    assert validate_text_length(long_text, max_length=20000)

    with pytest.raises(ValidationError):
        validate_text_length(long_text, max_length=5000)


def test_save_large_session(tmp_path):
    """Test saving session with many answers"""
    session_file = tmp_path / "large_session.json"

    # Create large answer dictionary
    answers = {f"key_{i}": f"value_{i}" for i in range(1000)}

    save_session(answers, session_file)
    loaded = load_session(session_file)

    assert len(loaded) == 1000


# ============================================================================
# Error Condition: Serialization
# ============================================================================

def test_save_session_with_non_serializable():
    """Test save_session with non-JSON-serializable object"""
    # Objects with custom types should fail
    bad_answers = {
        "normal": "value",
        "object": object()  # Not JSON serializable
    }

    with pytest.raises(PersistenceError, match="Failed to serialize"):
        save_session(bad_answers)


# ============================================================================
# Validator Edge Cases
# ============================================================================

def test_validate_choice_valid_selection():
    """Test choice validation with valid selection"""
    from template_qa_validator import validate_choice

    choices = [("Option A", "a"), ("Option B", "b")]
    result = validate_choice("a", choices)
    assert result == "a"


def test_validate_choice_invalid_selection():
    """Test choice validation with invalid selection"""
    from template_qa_validator import validate_choice

    choices = [("Option A", "a"), ("Option B", "b")]
    with pytest.raises(ValidationError, match="Choice must be one of"):
        validate_choice("c", choices)


def test_validate_multi_choice_valid():
    """Test multi-choice validation"""
    from template_qa_validator import validate_multi_choice

    choices = [("A", "a"), ("B", "b"), ("C", "c")]
    result = validate_multi_choice(["a", "c"], choices)
    assert result == ["a", "c"]


def test_validate_confirm_variations():
    """Test confirm validation with different inputs"""
    from template_qa_validator import validate_confirm

    assert validate_confirm("yes") is True
    assert validate_confirm("y") is True
    assert validate_confirm("no") is False
    assert validate_confirm("n") is False


def test_validate_file_path_exists(tmp_path):
    """Test file path validation for existing file"""
    from template_qa_validator import validate_file_path

    test_file = tmp_path / "test.txt"
    test_file.write_text("test")

    result = validate_file_path(str(test_file), must_exist=True)
    # validate_file_path returns a Path object
    assert isinstance(result, Path)
    assert result.exists()


def test_validate_file_path_nonexistent(tmp_path):
    """Test file path validation for non-existent file"""
    from template_qa_validator import validate_file_path

    missing_file = tmp_path / "missing.txt"

    with pytest.raises(ValidationError, match="does not exist"):
        validate_file_path(str(missing_file), must_exist=True)


def test_validate_list_input_min_max():
    """Test list input validation with min/max constraints"""
    from template_qa_validator import validate_list_input

    result = validate_list_input("a,b,c", min_items=2, max_items=5)
    assert result == ["a", "b", "c"]

    with pytest.raises(ValidationError, match="at least"):
        validate_list_input("a", min_items=2)

    with pytest.raises(ValidationError, match="at most"):
        validate_list_input("a,b,c,d,e", max_items=3)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
