"""
Test Suite for Template Q&A Validators.

Tests all validation functions in template_qa_validator.py.
Part of TASK-001B: Interactive Q&A Session for /template-init (Greenfield)
"""

import pytest
from pathlib import Path
import sys

# Add installer path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "installer" / "global" / "commands" / "lib"))

from template_qa_validator import (
    ValidationError,
    validate_non_empty,
    validate_template_name,
    validate_choice,
    validate_multi_choice,
    validate_confirm,
    validate_file_path,
    validate_url,
    validate_version_string,
    validate_list_input,
    validate_numeric_list,
    validate_text_length,
)


# ============================================================================
# Test validate_non_empty
# ============================================================================

def test_validate_non_empty_success():
    """Test non-empty validation with valid input"""
    assert validate_non_empty("hello") == "hello"
    assert validate_non_empty("  hello  ") == "hello"
    assert validate_non_empty("hello world") == "hello world"


def test_validate_non_empty_failure():
    """Test non-empty validation with empty input"""
    with pytest.raises(ValidationError, match="cannot be empty"):
        validate_non_empty("")

    with pytest.raises(ValidationError, match="cannot be empty"):
        validate_non_empty("   ")


def test_validate_non_empty_custom_field_name():
    """Test non-empty validation with custom field name"""
    with pytest.raises(ValidationError, match="Template name cannot be empty"):
        validate_non_empty("", "Template name")


# ============================================================================
# Test validate_template_name
# ============================================================================

def test_validate_template_name_success():
    """Test template name validation with valid names"""
    assert validate_template_name("my-template") == "my-template"
    assert validate_template_name("dotnet-maui-mvvm-template") == "dotnet-maui-mvvm-template"
    assert validate_template_name("template_v2") == "template_v2"
    assert validate_template_name("Template123") == "Template123"


def test_validate_template_name_too_short():
    """Test template name validation with too short name"""
    with pytest.raises(ValidationError, match="at least 3 characters"):
        validate_template_name("ab")


def test_validate_template_name_too_long():
    """Test template name validation with too long name"""
    long_name = "a" * 51
    with pytest.raises(ValidationError, match="at most 50 characters"):
        validate_template_name(long_name)


def test_validate_template_name_invalid_characters():
    """Test template name validation with invalid characters"""
    with pytest.raises(ValidationError, match="alphanumeric"):
        validate_template_name("my template")  # Space

    with pytest.raises(ValidationError, match="alphanumeric"):
        validate_template_name("my@template")  # Special char

    with pytest.raises(ValidationError, match="start with alphanumeric"):
        validate_template_name("-my-template")  # Starts with hyphen


# ============================================================================
# Test validate_choice
# ============================================================================

def test_validate_choice_success():
    """Test choice validation with valid selection"""
    choices = [("Option A", "a"), ("Option B", "b"), ("Option C", "c")]
    assert validate_choice("a", choices) == "a"
    assert validate_choice("b", choices) == "b"


def test_validate_choice_failure():
    """Test choice validation with invalid selection"""
    choices = [("Option A", "a"), ("Option B", "b")]
    with pytest.raises(ValidationError, match="must be one of"):
        validate_choice("z", choices)


# ============================================================================
# Test validate_multi_choice
# ============================================================================

def test_validate_multi_choice_success():
    """Test multi-choice validation with valid selections"""
    choices = [("A", "a", True), ("B", "b", False), ("C", "c", True)]
    assert validate_multi_choice(["a", "b"], choices) == ["a", "b"]
    assert validate_multi_choice(["a"], choices) == ["a"]


def test_validate_multi_choice_empty():
    """Test multi-choice validation with empty list"""
    choices = [("A", "a", True), ("B", "b", False)]
    with pytest.raises(ValidationError, match="at least one selection"):
        validate_multi_choice([], choices)


def test_validate_multi_choice_invalid():
    """Test multi-choice validation with invalid selection"""
    choices = [("A", "a", True), ("B", "b", False)]
    with pytest.raises(ValidationError, match="Invalid choice"):
        validate_multi_choice(["a", "z"], choices)


# ============================================================================
# Test validate_confirm
# ============================================================================

def test_validate_confirm_true_values():
    """Test confirmation validation with true values"""
    assert validate_confirm("y") is True
    assert validate_confirm("Y") is True
    assert validate_confirm("yes") is True
    assert validate_confirm("YES") is True
    assert validate_confirm("true") is True
    assert validate_confirm("1") is True
    assert validate_confirm(True) is True


def test_validate_confirm_false_values():
    """Test confirmation validation with false values"""
    assert validate_confirm("n") is False
    assert validate_confirm("N") is False
    assert validate_confirm("no") is False
    assert validate_confirm("NO") is False
    assert validate_confirm("false") is False
    assert validate_confirm("0") is False
    assert validate_confirm(False) is False


def test_validate_confirm_invalid():
    """Test confirmation validation with invalid values"""
    with pytest.raises(ValidationError, match="Invalid confirmation"):
        validate_confirm("maybe")

    with pytest.raises(ValidationError, match="Invalid confirmation"):
        validate_confirm("123")


# ============================================================================
# Test validate_file_path
# ============================================================================

def test_validate_file_path_success(tmp_path):
    """Test file path validation with valid path"""
    test_file = tmp_path / "test.txt"
    test_file.write_text("test content")

    result = validate_file_path(str(test_file), must_exist=True)
    assert result.exists()


def test_validate_file_path_not_exists():
    """Test file path validation with non-existent path"""
    with pytest.raises(ValidationError, match="File does not exist"):
        validate_file_path("/nonexistent/path/file.txt", must_exist=True)


def test_validate_file_path_no_existence_check():
    """Test file path validation without existence check"""
    result = validate_file_path("/some/path/file.txt", must_exist=False)
    assert isinstance(result, Path)


def test_validate_file_path_empty():
    """Test file path validation with empty path"""
    with pytest.raises(ValidationError, match="cannot be empty"):
        validate_file_path("")


# ============================================================================
# Test validate_url
# ============================================================================

def test_validate_url_success():
    """Test URL validation with valid URLs"""
    assert validate_url("http://example.com") == "http://example.com"
    assert validate_url("https://example.com") == "https://example.com"
    assert validate_url("https://example.com/path") == "https://example.com/path"
    assert validate_url("http://localhost:8080") == "http://localhost:8080"
    assert validate_url("https://192.168.1.1") == "https://192.168.1.1"


def test_validate_url_invalid():
    """Test URL validation with invalid URLs"""
    with pytest.raises(ValidationError, match="Invalid URL format"):
        validate_url("not-a-url")

    with pytest.raises(ValidationError, match="Invalid URL format"):
        validate_url("ftp://example.com")  # Only http/https allowed

    with pytest.raises(ValidationError, match="cannot be empty"):
        validate_url("")


# ============================================================================
# Test validate_version_string
# ============================================================================

def test_validate_version_string_success():
    """Test version string validation with valid versions"""
    assert validate_version_string("1.0") == "1.0"
    assert validate_version_string("1.0.0") == "1.0.0"
    assert validate_version_string("2.1.3") == "2.1.3"
    assert validate_version_string("1.0-beta") == "1.0-beta"
    assert validate_version_string("2.0.0-alpha") == "2.0.0-alpha"
    assert validate_version_string("1.0.0+build123") == "1.0.0+build123"


def test_validate_version_string_invalid():
    """Test version string validation with invalid versions"""
    with pytest.raises(ValidationError, match="Invalid version format"):
        validate_version_string("1")

    with pytest.raises(ValidationError, match="Invalid version format"):
        validate_version_string("v1.0.0")

    with pytest.raises(ValidationError, match="Invalid version format"):
        validate_version_string("1.0.0.0.0")


# ============================================================================
# Test validate_list_input
# ============================================================================

def test_validate_list_input_success():
    """Test list input validation with valid input"""
    assert validate_list_input("a,b,c") == ["a", "b", "c"]
    assert validate_list_input("a, b, c") == ["a", "b", "c"]  # Spaces trimmed
    assert validate_list_input("item1") == ["item1"]


def test_validate_list_input_custom_separator():
    """Test list input validation with custom separator"""
    assert validate_list_input("a;b;c", separator=";") == ["a", "b", "c"]


def test_validate_list_input_min_items():
    """Test list input validation with minimum items constraint"""
    with pytest.raises(ValidationError, match="at least 2 item"):
        validate_list_input("a", min_items=2)


def test_validate_list_input_max_items():
    """Test list input validation with maximum items constraint"""
    with pytest.raises(ValidationError, match="at most 2 item"):
        validate_list_input("a,b,c", max_items=2)


# ============================================================================
# Test validate_numeric_list
# ============================================================================

def test_validate_numeric_list_success():
    """Test numeric list validation with valid input"""
    assert validate_numeric_list("1,2,3") == [1, 2, 3]
    assert validate_numeric_list("10, 20, 30") == [10, 20, 30]


def test_validate_numeric_list_invalid_number():
    """Test numeric list validation with invalid number"""
    with pytest.raises(ValidationError, match="Invalid number"):
        validate_numeric_list("1,abc,3")


def test_validate_numeric_list_out_of_range():
    """Test numeric list validation with out of range numbers"""
    with pytest.raises(ValidationError, match="below minimum"):
        validate_numeric_list("0,1,2", min_value=1)

    with pytest.raises(ValidationError, match="above maximum"):
        validate_numeric_list("1,5,10", max_value=5)


# ============================================================================
# Test validate_text_length
# ============================================================================

def test_validate_text_length_success():
    """Test text length validation with valid input"""
    assert validate_text_length("hello", min_length=3, max_length=10) == "hello"
    assert validate_text_length("hi", min_length=0, max_length=5) == "hi"


def test_validate_text_length_too_short():
    """Test text length validation with too short text"""
    with pytest.raises(ValidationError, match="at least 5 characters"):
        validate_text_length("hi", min_length=5)


def test_validate_text_length_too_long():
    """Test text length validation with too long text"""
    with pytest.raises(ValidationError, match="at most 5 characters"):
        validate_text_length("hello world", max_length=5)


# ============================================================================
# Integration Tests
# ============================================================================

def test_validation_error_inheritance():
    """Test that ValidationError is an Exception"""
    assert issubclass(ValidationError, Exception)


def test_validator_preserves_valid_input():
    """Test that validators don't modify valid input unnecessarily"""
    # Template name should be preserved exactly
    assert validate_template_name("MyTemplate123") == "MyTemplate123"

    # Choice should return exact value
    choices = [("A", "value_a"), ("B", "value_b")]
    assert validate_choice("value_a", choices) == "value_a"


def test_validator_error_messages_are_helpful():
    """Test that error messages provide useful information"""
    try:
        validate_template_name("ab")
    except ValidationError as e:
        assert "at least 3 characters" in str(e)

    try:
        validate_url("not-a-url")
    except ValidationError as e:
        assert "Invalid URL format" in str(e)


# ============================================================================
# Test Summary
# ============================================================================

def test_all_validators_have_tests():
    """Meta-test: ensure all exported validators are tested"""
    tested_functions = {
        "validate_non_empty",
        "validate_template_name",
        "validate_choice",
        "validate_multi_choice",
        "validate_confirm",
        "validate_file_path",
        "validate_url",
        "validate_version_string",
        "validate_list_input",
        "validate_numeric_list",
        "validate_text_length",
    }

    # Get all test functions
    test_functions = {name for name in globals() if name.startswith("test_validate_")}

    # Check that each validator has at least one test
    for validator in tested_functions:
        assert any(
            validator in test_name for test_name in test_functions
        ), f"No tests found for {validator}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
