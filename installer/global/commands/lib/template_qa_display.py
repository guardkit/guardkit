"""
Template Q&A Display Helpers.

Provides terminal output formatting for the Q&A session.
Uses Python stdlib only (no external dependencies).

Part of TASK-001B: Interactive Q&A Session for /template-init (Greenfield)
"""

import sys
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


def print_banner(text: str, width: int = 60) -> None:
    """
    Print a banner with centered text.

    Args:
        text: Text to display in banner
        width: Width of banner (default: 60)
    """
    print("\n" + "=" * width)
    print(f"  {text}")
    print("=" * width + "\n")


def print_section_header(section_name: str, width: int = 60) -> None:
    """
    Print a section header with separator lines.

    Args:
        section_name: Name of the section
        width: Width of header (default: 60)
    """
    print("\n" + "-" * width)
    print(f"  Section: {section_name}")
    print("-" * width + "\n")


def print_question(text: str, help_text: Optional[str] = None) -> None:
    """
    Print a question with optional help text.

    Args:
        text: Question text
        help_text: Optional help text to display
    """
    print(f"\n{text}")
    if help_text:
        print(f"  ({help_text})")


def print_choices(choices: List[tuple], show_numbers: bool = True) -> None:
    """
    Print a list of choices.

    Args:
        choices: List of (display, value) or (display, value, default) tuples
        show_numbers: Whether to show numbers before each choice
    """
    for i, choice in enumerate(choices, 1):
        display = choice[0]
        # Check if there's a default indicator (third element)
        default_indicator = ""
        if len(choice) > 2 and choice[2]:
            default_indicator = " [DEFAULT]"

        if show_numbers:
            print(f"  [{i}] {display}{default_indicator}")
        else:
            print(f"  - {display}{default_indicator}")


def prompt_choice(
    text: str,
    choices: List[tuple],
    default: Optional[str] = None,
    help_text: Optional[str] = None,
) -> str:
    """
    Display a choice question and get user input.

    Args:
        text: Question text
        choices: List of (display, value) tuples
        default: Default value if user presses Enter
        help_text: Optional help text

    Returns:
        Selected choice value
    """
    print_question(text, help_text)
    print_choices(choices)

    # Show default hint
    if default:
        default_display = next(
            (choice[0] for choice in choices if choice[1] == default), default
        )
        prompt = f"\nEnter number (default: {default_display}): "
    else:
        prompt = "\nEnter number: "

    return prompt


def prompt_multi_choice(
    text: str, choices: List[tuple], help_text: Optional[str] = None
) -> str:
    """
    Display a multi-choice question and get user input.

    Args:
        text: Question text
        choices: List of (display, value, default) tuples
        help_text: Optional help text

    Returns:
        Input prompt string
    """
    print_question(text, help_text)
    print_choices(choices)

    # Get defaults
    defaults = [str(i + 1) for i, choice in enumerate(choices) if len(choice) > 2 and choice[2]]

    if defaults:
        prompt = f"\nEnter numbers separated by commas (default: {','.join(defaults)}): "
    else:
        prompt = "\nEnter numbers separated by commas: "

    return prompt


def prompt_text(
    text: str, default: Optional[str] = None, help_text: Optional[str] = None
) -> str:
    """
    Display a text question and get user input prompt.

    Args:
        text: Question text
        default: Default value if user presses Enter
        help_text: Optional help text

    Returns:
        Input prompt string
    """
    print_question(text, help_text)

    if default:
        prompt = f"\nEnter value (default: {default}): "
    else:
        prompt = "\nEnter value: "

    return prompt


def prompt_confirm(
    text: str, default: bool = True, help_text: Optional[str] = None
) -> str:
    """
    Display a confirmation question and get user input prompt.

    Args:
        text: Question text
        default: Default value if user presses Enter
        help_text: Optional help text

    Returns:
        Input prompt string
    """
    print_question(text, help_text)

    if default:
        prompt = "\nConfirm (Y/n): "
    else:
        prompt = "\nConfirm (y/N): "

    return prompt


def print_error(message: str) -> None:
    """
    Print an error message to stderr.

    Args:
        message: Error message to display
    """
    print(f"\nError: {message}", file=sys.stderr)


def print_warning(message: str) -> None:
    """
    Print a warning message.

    Args:
        message: Warning message to display
    """
    print(f"\nWarning: {message}")


def print_success(message: str) -> None:
    """
    Print a success message.

    Args:
        message: Success message to display
    """
    print(f"\nSuccess: {message}")


def print_info(message: str) -> None:
    """
    Print an informational message.

    Args:
        message: Info message to display
    """
    print(f"\n{message}")


def print_summary_section(title: str, items: Dict[str, Any], indent: int = 2) -> None:
    """
    Print a section of the summary with key-value pairs.

    Args:
        title: Section title
        items: Dictionary of key-value pairs to display
        indent: Number of spaces to indent values
    """
    print(f"\n{title}:")
    indent_str = " " * indent

    for key, value in items.items():
        if isinstance(value, list):
            # Format lists
            value_str = ", ".join(str(v) for v in value)
            print(f"{indent_str}{key}: {value_str}")
        elif isinstance(value, dict):
            # Format nested dicts
            print(f"{indent_str}{key}:")
            for sub_key, sub_value in value.items():
                print(f"{indent_str}  {sub_key}: {sub_value}")
        elif value is None:
            # Skip None values
            continue
        else:
            print(f"{indent_str}{key}: {value}")


def print_complete_summary(answers: Dict[str, Any]) -> None:
    """
    Print a complete summary of all Q&A answers.

    Args:
        answers: Dictionary of all answers from the session
    """
    print_banner("Q&A Summary", width=60)

    # Section 1: Template Identity
    if "template_name" in answers or "template_purpose" in answers:
        print_summary_section(
            "Template Identity",
            {
                "Name": answers.get("template_name"),
                "Purpose": answers.get("template_purpose"),
            },
        )

    # Section 2: Technology Stack
    tech_items = {
        "Language": answers.get("primary_language"),
        "Framework": answers.get("framework"),
        "Version": answers.get("framework_version"),
    }
    if any(tech_items.values()):
        print_summary_section("Technology Stack", tech_items)

    # Section 3: Architecture
    arch_items = {
        "Pattern": answers.get("architecture_pattern"),
        "Domain Modeling": answers.get("domain_modeling"),
    }
    if any(arch_items.values()):
        print_summary_section("Architecture", arch_items)

    # Section 4: Project Structure
    struct_items = {
        "Organization": answers.get("layer_organization"),
        "Folders": answers.get("standard_folders"),
    }
    if any(struct_items.values()):
        print_summary_section("Project Structure", struct_items)

    # Section 5: Testing
    test_items = {
        "Framework": answers.get("unit_testing_framework"),
        "Scope": answers.get("testing_scope"),
        "Pattern": answers.get("test_pattern"),
    }
    if any(test_items.values()):
        print_summary_section("Testing Strategy", test_items)

    # Section 6: Error Handling
    error_items = {
        "Strategy": answers.get("error_handling"),
        "Validation": answers.get("validation_approach"),
    }
    if any(error_items.values()):
        print_summary_section("Error Handling", error_items)

    # Section 7: Dependency Management
    dep_items = {
        "Dependency Injection": answers.get("dependency_injection"),
        "Configuration": answers.get("configuration_approach"),
    }
    if any(dep_items.values()):
        print_summary_section("Dependency Management", dep_items)

    # Section 8: UI/Navigation (optional)
    ui_items = {
        "Architecture": answers.get("ui_architecture"),
        "Navigation": answers.get("navigation_pattern"),
    }
    if any(ui_items.values()):
        print_summary_section("UI/Navigation", ui_items)

    # Section 9: Additional Patterns (optional)
    additional_items = {
        "Data Access": answers.get("data_access"),
        "API Pattern": answers.get("api_pattern"),
        "State Management": answers.get("state_management"),
    }
    if any(additional_items.values()):
        print_summary_section("Additional Patterns", additional_items)

    # Section 10: Documentation (optional)
    doc_items = {
        "Has Documentation": answers.get("has_documentation"),
        "Input Method": answers.get("documentation_input_method"),
        "Usage": answers.get("documentation_usage"),
    }
    if answers.get("has_documentation"):
        print_summary_section("Documentation Input", doc_items)

    print()  # Final newline


def clear_line() -> None:
    """Clear the current terminal line."""
    print("\r" + " " * 80 + "\r", end="", flush=True)


def print_progress(current: int, total: int, prefix: str = "Progress") -> None:
    """
    Print a simple progress indicator.

    Args:
        current: Current step number
        total: Total number of steps
        prefix: Prefix text to display
    """
    percentage = int((current / total) * 100)
    print(f"\r{prefix}: {current}/{total} ({percentage}%)", end="", flush=True)


# Module exports
__all__ = [
    "print_banner",
    "print_section_header",
    "print_question",
    "print_choices",
    "prompt_choice",
    "prompt_multi_choice",
    "prompt_text",
    "prompt_confirm",
    "print_error",
    "print_warning",
    "print_success",
    "print_info",
    "print_summary_section",
    "print_complete_summary",
    "clear_line",
    "print_progress",
]
