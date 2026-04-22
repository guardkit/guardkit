"""
Quality Gate YAML Generator for GuardKit.

Generates quality gate YAML configuration files from task definitions,
extracting and categorizing coach validation commands for automated
quality enforcement.

Coverage Target: >=85%
"""

from pathlib import Path
from typing import Optional

import yaml

from guardkit.planning.spec_parser import TaskDefinition


# Default required values for each gate category
GATE_REQUIRED_DEFAULTS: dict[str, bool] = {
    "lint": True,
    "unit_tests": True,
    "integration_tests": True,
    "type_check": False,
    "coverage": False,
    "custom": True,
}


def _categorize_command(command: str) -> str:
    """
    Categorize a validation command into a gate category.

    Args:
        command: The validation command string

    Returns:
        Category string: 'lint', 'unit_tests', 'integration_tests',
                        'type_check', 'coverage', or 'custom'
    """
    command_lower = command.lower()

    # Check for ruff (lint)
    if "ruff" in command_lower:
        return "lint"

    # Check for mypy (type check)
    if "mypy" in command_lower:
        return "type_check"

    # Check for coverage (must check before pytest to catch coverage commands)
    if "--cov" in command_lower:
        return "coverage"

    # Check for pytest (unit or integration tests)
    if "pytest" in command_lower:
        if "tests/integration/" in command or "tests/integration\\" in command:
            return "integration_tests"
        if "tests/unit/" in command or "tests/unit\\" in command:
            return "unit_tests"
        # Default pytest to unit_tests if no specific path
        return "unit_tests"

    # Everything else is custom
    return "custom"


def _collect_commands(tasks: list[TaskDefinition]) -> dict[str, list[str]]:
    """
    Collect and categorize all commands from tasks.

    Args:
        tasks: List of TaskDefinition objects

    Returns:
        Dictionary mapping category names to lists of commands
    """
    categorized: dict[str, list[str]] = {}

    for task in tasks:
        for command in task.coach_validation_commands:
            # Skip empty commands
            if not command or not command.strip():
                continue

            command = command.strip()
            category = _categorize_command(command)

            if category not in categorized:
                categorized[category] = []

            # Add command if not already present (deduplication)
            if command not in categorized[category]:
                categorized[category].append(command)

    return categorized


def _merge_commands(commands: list[str]) -> str:
    """
    Merge multiple commands in the same category into a single command string.

    For identical commands, only one is kept.
    For different commands, they are combined with semicolons.

    Args:
        commands: List of command strings

    Returns:
        Single merged command string
    """
    if not commands:
        return ""

    if len(commands) == 1:
        return commands[0]

    # Multiple different commands - combine with semicolons
    return " && ".join(commands)


def generate_quality_gates(
    feature_id: str,
    tasks: list[TaskDefinition],
    output_path: Optional[Path] = None,
) -> Path:
    """
    Generate a quality gates YAML file from task definitions.

    Extracts coach_validation_commands from all tasks, categorizes them,
    deduplicates identical commands, and writes to a YAML file.

    Args:
        feature_id: The feature identifier (e.g., "FEAT-FP-001")
        tasks: List of TaskDefinition objects containing validation commands
        output_path: Optional custom output path. If None, uses
                    .guardkit/quality-gates/{feature_id}.yaml

    Returns:
        Path to the generated YAML file

    Example output:
        feature_id: FEAT-XXX
        quality_gates:
          lint:
            command: "ruff check guardkit/planning/"
            required: true
          unit_tests:
            command: "pytest tests/unit/test_*.py -v --tb=short"
            required: true
    """
    # Determine output path
    if output_path is None:
        output_path = Path(".guardkit") / "quality-gates" / f"{feature_id}.yaml"

    # Ensure parent directories exist
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Collect and categorize commands
    categorized_commands = _collect_commands(tasks)

    # Build quality gates structure
    quality_gates: dict[str, dict[str, object]] = {}

    for category, commands in categorized_commands.items():
        merged_command = _merge_commands(commands)
        if merged_command:  # Only add if there's a command
            quality_gates[category] = {
                "command": merged_command,
                "required": GATE_REQUIRED_DEFAULTS.get(category, True),
            }

    # Build complete YAML structure
    yaml_data = {
        "feature_id": feature_id,
        "quality_gates": quality_gates,
    }

    # Write YAML file
    with open(output_path, "w") as f:
        yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

    return output_path
