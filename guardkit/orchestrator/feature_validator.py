"""Pre-flight feature validation for AutoBuild feature execution.

Since the cull (27 October 2026, GKT-057 and GKT-058) the task file
frontmatter is not checked: a missing field takes the default the runtime
already uses and a ``task_type`` value is kept as written.
``validate_feature_preflight``, ``REQUIRED_FRONTMATTER_FIELDS`` and
``_extract_frontmatter`` stay because specialist-agent imports them, and the
result types stay for the callers in ``feature_orchestrator``.
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

import yaml

from guardkit.orchestrator.feature_loader import Feature

logger = logging.getLogger(__name__)

# The frontmatter fields a task file normally carries. Read by
# specialist-agent's planner; GuardKit no longer checks them.
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
    """Kept for callers (feature_orchestrator, specialist-agent); returns an
    empty result. The frontmatter checks were deleted in the cull (27
    October 2026, GKT-057 and GKT-058).
    """
    return PreFlightValidationResult()


def validate_feature_environment(
    feature: Feature,
    repo_root: Path,
    worktree_python: Optional[str] = None,
) -> PreFlightValidationResult:
    """Env-level preflight: catch pytest-bdd ↔ tagged feature files gaps.

    Iterates ``feature.tasks`` and, for each task whose tag appears in any
    ``features/**/*.feature`` file, lazily probes the worktree environment
    for ``pytest_bdd``. Emits an error covering all affected tasks if the
    probe fails — moves the same outcome that ``bdd_runner.run_bdd_for_task``
    would surface inside the Player-Coach loop to before any SDK turn runs,
    keeping cost neutral.

    Function is purely additive — when no tagged feature files exist or
    pytest-bdd is importable, no issue is emitted and call sites observe
    no behavioural change.

    Parameters
    ----------
    feature : Feature
        Loaded feature to validate
    repo_root : Path
        Repository root directory (must contain ``features/`` for the
        check to fire)
    worktree_python : Optional[str]
        Optional path to a Python interpreter to probe; ``None`` falls
        back to the current interpreter (matches ``has_pytest_bdd``'s
        default)

    Returns
    -------
    PreFlightValidationResult
        Always empty since the R1 de-wire (see note below).

    R1 DE-WIRE (Rich 08-14): the pytest-bdd probe body is removed — it
    existed solely to pre-catch failures of the retired BDD oracle, and its
    error DEMANDED consumers install pytest-bdd for a chain that no longer
    runs. The signature is kept so call sites are untouched; the function is
    now a structural no-op. R2 deletes it with bdd_runner.py at graduation.
    """
    return PreFlightValidationResult()


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
        lines.append(f"{len(warning_task_ids)} task(s) have advice:")
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
