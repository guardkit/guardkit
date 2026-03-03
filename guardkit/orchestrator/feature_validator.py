"""Pre-flight feature validation for AutoBuild feature execution.

Validates task file frontmatter before any SDK invocations, catching
issues like invalid task_type values or missing required fields early.

This module complements FeatureLoader.validate_feature() which handles
structural validation (file existence, dependency graph, orchestration
consistency). Pre-flight validation focuses on task file *content*
(frontmatter field completeness and value correctness).
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from guardkit.models.task_types import (
    TaskType,
    TASK_TYPE_ALIASES,
    VALID_TASK_TYPES,
)
from guardkit.orchestrator.feature_loader import Feature

logger = logging.getLogger(__name__)

# Required frontmatter fields for pre-flight validation
REQUIRED_FRONTMATTER_FIELDS = ("id", "title", "task_type", "complexity")


@dataclass
class ValidationIssue:
    """A single pre-flight validation issue.

    Attributes
    ----------
    task_id : str
        Task identifier from the feature YAML
    field : str
        Frontmatter field name that has an issue
    severity : str
        Either "error" (blocks execution) or "warning" (informational)
    message : str
        Human-readable description of the issue
    suggestion : Optional[str]
        Suggested fix (e.g., canonical value for aliases)
    """

    task_id: str
    field: str
    severity: str  # "error" or "warning"
    message: str
    suggestion: Optional[str] = None


@dataclass
class PreFlightValidationResult:
    """Result of pre-flight feature validation.

    Attributes
    ----------
    errors : List[ValidationIssue]
        Issues that block execution
    warnings : List[ValidationIssue]
        Informational issues (aliases, recommendations)
    """

    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)

    @property
    def has_errors(self) -> bool:
        """Whether any blocking errors were found."""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """Whether any warnings were found."""
        return len(self.warnings) > 0

    @property
    def is_valid(self) -> bool:
        """Whether validation passed (no blocking errors)."""
        return not self.has_errors


def _extract_frontmatter(task_file: Path) -> Optional[Dict]:
    """Extract YAML frontmatter from a task markdown file.

    Parameters
    ----------
    task_file : Path
        Path to the task markdown file

    Returns
    -------
    Optional[Dict]
        Parsed frontmatter dict, or None if file cannot be read
        or has no valid frontmatter.
    """
    try:
        content = task_file.read_text(encoding="utf-8")
    except OSError:
        return None

    if not content.startswith("---"):
        return None

    try:
        end_idx = content.index("---", 3)
    except ValueError:
        return None

    frontmatter_str = content[3:end_idx]
    try:
        frontmatter = yaml.safe_load(frontmatter_str)
    except yaml.YAMLError:
        return None

    if not isinstance(frontmatter, dict):
        return None

    return frontmatter


def validate_feature_preflight(
    feature: Feature,
    repo_root: Path,
) -> PreFlightValidationResult:
    """Validate all task frontmatter in a feature before execution.

    Iterates all tasks, loads each task file, parses YAML frontmatter,
    and validates required fields and task_type values. Collects ALL
    issues (batch, not fail-fast).

    Parameters
    ----------
    feature : Feature
        Loaded feature to validate
    repo_root : Path
        Repository root directory

    Returns
    -------
    PreFlightValidationResult
        Collected errors and warnings
    """
    result = PreFlightValidationResult()

    for task in feature.tasks:
        task_file = repo_root / task.file_path
        if not task_file.exists() or task_file.is_dir():
            # Structural validator already handles missing/invalid files
            continue

        frontmatter = _extract_frontmatter(task_file)
        if frontmatter is None:
            # No parseable frontmatter - skip gracefully
            continue

        # Validate required fields
        for field_name in REQUIRED_FRONTMATTER_FIELDS:
            if field_name not in frontmatter or frontmatter[field_name] is None:
                result.errors.append(
                    ValidationIssue(
                        task_id=task.id,
                        field=field_name,
                        severity="error",
                        message=f"Missing required field '{field_name}'",
                    )
                )

        # Validate task_type value (if present)
        task_type_str = frontmatter.get("task_type")
        if task_type_str is not None:
            # Check if it's an alias (valid but not canonical)
            if task_type_str in TASK_TYPE_ALIASES:
                canonical = TASK_TYPE_ALIASES[task_type_str].value
                result.warnings.append(
                    ValidationIssue(
                        task_id=task.id,
                        field="task_type",
                        severity="warning",
                        message=f"task_type '{task_type_str}' is a legacy alias",
                        suggestion=(
                            f"Change to '{canonical}' (canonical value)"
                        ),
                    )
                )
            elif task_type_str not in VALID_TASK_TYPES:
                # Truly invalid value
                valid_values = ", ".join(t.value for t in TaskType)
                valid_aliases = ", ".join(sorted(TASK_TYPE_ALIASES.keys()))
                result.errors.append(
                    ValidationIssue(
                        task_id=task.id,
                        field="task_type",
                        severity="error",
                        message=f"Invalid task_type '{task_type_str}'",
                        suggestion=(
                            f"Valid values: {valid_values}\n"
                            f"    Valid aliases: {valid_aliases}"
                        ),
                    )
                )

    return result


def format_preflight_report(result: PreFlightValidationResult) -> str:
    """Format pre-flight validation result as a human-readable report.

    Produces the banner format specified in the task requirements,
    suitable for display in the terminal.

    Parameters
    ----------
    result : PreFlightValidationResult
        Validation result to format

    Returns
    -------
    str
        Formatted report string
    """
    lines: List[str] = []
    separator = "=" * 64

    if result.has_errors:
        lines.append(separator)
        lines.append("PRE-FLIGHT VALIDATION FAILED")
        lines.append(separator)
        lines.append("")

        error_task_ids = {issue.task_id for issue in result.errors}
        lines.append(f"{len(error_task_ids)} task(s) have invalid frontmatter:")
        lines.append("")

        for issue in result.errors:
            lines.append(f"  {issue.task_id}: {issue.message}")
            if issue.suggestion:
                for suggestion_line in issue.suggestion.split("\n"):
                    lines.append(f"    {suggestion_line}")
            lines.append("")

        lines.append("Fix these issues and retry.")
        lines.append(separator)

    if result.has_warnings:
        if result.has_errors:
            lines.append("")

        lines.append(separator)
        lines.append("PRE-FLIGHT VALIDATION WARNINGS")
        lines.append(separator)
        lines.append("")

        warning_task_ids = {issue.task_id for issue in result.warnings}
        lines.append(f"{len(warning_task_ids)} task(s) use legacy aliases:")
        lines.append("")

        for issue in result.warnings:
            lines.append(f"  {issue.task_id}: {issue.message}")
            if issue.suggestion:
                lines.append(f"    Suggestion: {issue.suggestion}")
            lines.append(
                "    Note: Alias will work at runtime, "
                "but canonical values are preferred"
            )
            lines.append("")

        lines.append(separator)

    return "\n".join(lines)
