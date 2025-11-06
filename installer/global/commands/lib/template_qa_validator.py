"""
Template Q&A Input Validators.

Provides validation functions for Q&A session inputs.
Uses Python stdlib only (no external dependencies).

Part of TASK-001B: Interactive Q&A Session for /template-init (Greenfield)
"""

import re
from typing import Any, Optional, List
from pathlib import Path


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass


def validate_non_empty(value: str, field_name: str = "Input") -> str:
    """
    Validate that a string is non-empty after stripping whitespace.

    Args:
        value: Input string to validate
        field_name: Name of the field being validated (for error messages)

    Returns:
        Stripped value if valid

    Raises:
        ValidationError: If value is empty or only whitespace
    """
    stripped = value.strip()
    if not stripped:
        raise ValidationError(f"{field_name} cannot be empty")
    return stripped


def validate_template_name(name: str) -> str:
    """
    Validate template name follows naming conventions.

    Rules:
    - Must be non-empty
    - Must contain only alphanumeric, hyphens, and underscores
    - Must start with alphanumeric character
    - Length between 3-50 characters

    Args:
        name: Template name to validate

    Returns:
        Validated template name

    Raises:
        ValidationError: If name doesn't meet requirements
    """
    # Check non-empty
    name = validate_non_empty(name, "Template name")

    # Check length
    if len(name) < 3:
        raise ValidationError("Template name must be at least 3 characters long")
    if len(name) > 50:
        raise ValidationError("Template name must be at most 50 characters long")

    # Check pattern
    if not re.match(r"^[a-zA-Z0-9][a-zA-Z0-9_-]*$", name):
        raise ValidationError(
            "Template name must start with alphanumeric and contain only "
            "alphanumeric, hyphens, and underscores"
        )

    return name


def validate_choice(value: str, choices: List[tuple], field_name: str = "Choice") -> str:
    """
    Validate that input is one of the allowed choices.

    Args:
        value: Selected choice value
        choices: List of (display, value) tuples
        field_name: Name of the field being validated

    Returns:
        Validated choice value

    Raises:
        ValidationError: If value is not in choices
    """
    valid_values = [choice[1] for choice in choices]
    if value not in valid_values:
        raise ValidationError(
            f"{field_name} must be one of: {', '.join(valid_values)}"
        )
    return value


def validate_multi_choice(
    values: List[str], choices: List[tuple], field_name: str = "Choices"
) -> List[str]:
    """
    Validate that all inputs are valid choices.

    Args:
        values: List of selected choice values
        choices: List of (display, value, default) tuples
        field_name: Name of the field being validated

    Returns:
        List of validated choice values

    Raises:
        ValidationError: If any value is not in choices
    """
    if not values:
        raise ValidationError(f"{field_name} must have at least one selection")

    valid_values = [choice[1] for choice in choices]
    for value in values:
        if value not in valid_values:
            raise ValidationError(
                f"Invalid choice '{value}' in {field_name}. "
                f"Must be one of: {', '.join(valid_values)}"
            )

    return values


def validate_confirm(value: Any) -> bool:
    """
    Validate boolean/confirmation input.

    Accepts: y, yes, true, 1, n, no, false, 0 (case-insensitive)

    Args:
        value: Input to validate and convert to boolean

    Returns:
        Boolean value

    Raises:
        ValidationError: If value cannot be parsed as boolean
    """
    if isinstance(value, bool):
        return value

    str_value = str(value).lower().strip()

    if str_value in ("y", "yes", "true", "1"):
        return True
    elif str_value in ("n", "no", "false", "0"):
        return False
    else:
        raise ValidationError(
            "Invalid confirmation. Please enter 'y' or 'n' (yes/no)"
        )


def validate_file_path(path_str: str, must_exist: bool = False) -> Path:
    """
    Validate file path input.

    Args:
        path_str: Path string to validate
        must_exist: If True, validates that path exists

    Returns:
        Path object

    Raises:
        ValidationError: If path is invalid or doesn't exist (when must_exist=True)
    """
    path_str = validate_non_empty(path_str, "File path")

    try:
        path = Path(path_str).expanduser().resolve()
    except Exception as e:
        raise ValidationError(f"Invalid file path: {e}")

    if must_exist and not path.exists():
        raise ValidationError(f"File does not exist: {path}")

    return path


def validate_url(url: str) -> str:
    """
    Basic URL validation.

    Checks for http/https protocol and basic structure.

    Args:
        url: URL string to validate

    Returns:
        Validated URL

    Raises:
        ValidationError: If URL format is invalid
    """
    url = validate_non_empty(url, "URL")

    # Basic URL pattern check
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE,
    )

    if not url_pattern.match(url):
        raise ValidationError(
            "Invalid URL format. Must start with http:// or https://"
        )

    return url


def validate_version_string(version: str) -> str:
    """
    Validate version string format.

    Accepts semantic versioning (e.g., 1.0.0, 2.1.3-beta)

    Args:
        version: Version string to validate

    Returns:
        Validated version string

    Raises:
        ValidationError: If version format is invalid
    """
    version = validate_non_empty(version, "Version")

    # Semantic versioning pattern
    version_pattern = re.compile(
        r"^\d+\.\d+(?:\.\d+)?(?:-[a-zA-Z0-9-]+)?(?:\+[a-zA-Z0-9-]+)?$"
    )

    if not version_pattern.match(version):
        raise ValidationError(
            "Invalid version format. Use semantic versioning (e.g., 1.0.0, 2.1-beta)"
        )

    return version


def validate_list_input(
    input_str: str, separator: str = ",", min_items: int = 1, max_items: Optional[int] = None
) -> List[str]:
    """
    Validate and parse comma-separated list input.

    Args:
        input_str: Input string containing separated items
        separator: Separator character (default: comma)
        min_items: Minimum number of items required
        max_items: Maximum number of items allowed (None for unlimited)

    Returns:
        List of trimmed items

    Raises:
        ValidationError: If list doesn't meet requirements
    """
    # Split and trim
    items = [item.strip() for item in input_str.split(separator) if item.strip()]

    # Check minimum
    if len(items) < min_items:
        raise ValidationError(
            f"Must provide at least {min_items} item(s). Found {len(items)}"
        )

    # Check maximum
    if max_items is not None and len(items) > max_items:
        raise ValidationError(
            f"Must provide at most {max_items} item(s). Found {len(items)}"
        )

    return items


def validate_numeric_list(
    input_str: str,
    min_value: int = 1,
    max_value: Optional[int] = None,
    separator: str = ",",
) -> List[int]:
    """
    Validate and parse comma-separated numeric list.

    Used for multi-choice questions where user enters numbers.

    Args:
        input_str: Input string containing separated numbers
        min_value: Minimum valid number
        max_value: Maximum valid number (None for unlimited)
        separator: Separator character (default: comma)

    Returns:
        List of integers

    Raises:
        ValidationError: If list contains invalid numbers
    """
    items = validate_list_input(input_str, separator=separator, min_items=1)

    numbers = []
    for item in items:
        try:
            num = int(item)
        except ValueError:
            raise ValidationError(f"Invalid number: '{item}'")

        if num < min_value:
            raise ValidationError(f"Number {num} is below minimum {min_value}")

        if max_value is not None and num > max_value:
            raise ValidationError(f"Number {num} is above maximum {max_value}")

        numbers.append(num)

    return numbers


def validate_text_length(
    text: str, min_length: int = 0, max_length: Optional[int] = None, field_name: str = "Text"
) -> str:
    """
    Validate text length constraints.

    Args:
        text: Text to validate
        min_length: Minimum length (default: 0)
        max_length: Maximum length (None for unlimited)
        field_name: Name of the field being validated

    Returns:
        Validated text

    Raises:
        ValidationError: If text doesn't meet length requirements
    """
    if len(text) < min_length:
        raise ValidationError(
            f"{field_name} must be at least {min_length} characters long"
        )

    if max_length is not None and len(text) > max_length:
        raise ValidationError(
            f"{field_name} must be at most {max_length} characters long"
        )

    return text


# Module exports
__all__ = [
    "ValidationError",
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
]
