"""
Command failure classifier for AutoBuild command execution criteria.

Classifies command execution failures into categories to enable
advisory injection into Coach feedback (TASK-RFX-F7F5).

Categories:
    - environment: Missing system tools, command not found (suppressed)
    - implementation: Tracebacks in project files, import errors (included as advisory)
    - transient: Network/connectivity issues (suppressed)
    - unknown: Default classification (included with caveat)
"""

import logging
import re
from dataclasses import dataclass, field
from typing import List, Optional

logger = logging.getLogger(__name__)

# Environment failure patterns
_ENVIRONMENT_PATTERNS = [
    # Exit code 127 = command not found
    re.compile(r"command not found", re.IGNORECASE),
    re.compile(r"not found in PATH", re.IGNORECASE),
    re.compile(r"No such file or directory.*bin/", re.IGNORECASE),
    # ModuleNotFoundError for system tools (not project modules)
    re.compile(r"ModuleNotFoundError.*(?:pip|setuptools|wheel|virtualenv|venv)", re.IGNORECASE),
    # Permission denied for system commands
    re.compile(r"Permission denied.*(?:/usr/|/bin/|/sbin/)", re.IGNORECASE),
]

# Transient failure patterns
_TRANSIENT_PATTERNS = [
    re.compile(r"Connection\s*Refused", re.IGNORECASE),
    re.compile(r"Connection\s*Reset", re.IGNORECASE),
    re.compile(r"timeout", re.IGNORECASE),
    re.compile(r"DNS\s+resolution", re.IGNORECASE),
    re.compile(r"Name or service not known", re.IGNORECASE),
    re.compile(r"Temporary failure in name resolution", re.IGNORECASE),
    re.compile(r"Network\s+is\s+unreachable", re.IGNORECASE),
]

# Implementation failure patterns
_IMPLEMENTATION_PATTERNS = [
    re.compile(r"Traceback \(most recent call last\)", re.IGNORECASE),
    re.compile(r"ImportError:", re.IGNORECASE),
    re.compile(r"ModuleNotFoundError:", re.IGNORECASE),
    re.compile(r"SyntaxError:", re.IGNORECASE),
    re.compile(r"NameError:", re.IGNORECASE),
    re.compile(r"AttributeError:", re.IGNORECASE),
    re.compile(r"TypeError:", re.IGNORECASE),
    re.compile(r"ValueError:", re.IGNORECASE),
]


@dataclass
class CommandFailureRecord:
    """Record of a single command execution failure."""

    command: str
    criterion_text: str
    returncode: Optional[int]
    stderr: str
    stdout: str
    classification: str  # "environment", "implementation", "transient", "unknown"
    timed_out: bool = False


def classify_command_failure(
    returncode: Optional[int],
    stderr: str,
    stdout: str,
    command: str,
) -> str:
    """Classify a command execution failure into a category.

    Parameters
    ----------
    returncode : Optional[int]
        Process exit code (None if timed out).
    stderr : str
        Standard error output from the command.
    stdout : str
        Standard output from the command.
    command : str
        The command that was executed.

    Returns
    -------
    str
        One of: "environment", "implementation", "transient", "unknown".
    """
    combined = (stderr or "") + "\n" + (stdout or "")

    # Exit code 127 is always "command not found" → environment
    if returncode == 127:
        logger.debug("classify_command_failure: exit 127 → environment")
        return "environment"

    # Check environment patterns first
    for pattern in _ENVIRONMENT_PATTERNS:
        if pattern.search(combined):
            logger.debug(
                "classify_command_failure: environment pattern matched: %s",
                pattern.pattern,
            )
            return "environment"

    # Check transient patterns
    for pattern in _TRANSIENT_PATTERNS:
        if pattern.search(combined):
            logger.debug(
                "classify_command_failure: transient pattern matched: %s",
                pattern.pattern,
            )
            return "transient"

    # Check implementation patterns (tracebacks, import errors, etc.)
    for pattern in _IMPLEMENTATION_PATTERNS:
        if pattern.search(combined):
            # Distinguish: ModuleNotFoundError for system tools = environment
            # ModuleNotFoundError for project modules = implementation
            if "ModuleNotFoundError" in combined:
                match = re.search(
                    r"No module named '([^']+)'", combined, re.IGNORECASE
                )
                if match:
                    module_name = match.group(1).split(".")[0]
                    _SYSTEM_MODULES = {
                        "pip", "setuptools", "wheel", "virtualenv",
                        "venv", "ensurepip", "distutils",
                    }
                    if module_name in _SYSTEM_MODULES:
                        logger.debug(
                            "classify_command_failure: system module %s → environment",
                            module_name,
                        )
                        return "environment"

            logger.debug(
                "classify_command_failure: implementation pattern matched: %s",
                pattern.pattern,
            )
            return "implementation"

    # Default: unknown
    logger.debug("classify_command_failure: no pattern matched → unknown")
    return "unknown"


def build_command_failure_advisory(
    failures: List[CommandFailureRecord],
) -> Optional[str]:
    """Build advisory text from classified command failures.

    Only includes "implementation" and "unknown" failures.
    Environment and transient failures are suppressed.

    Parameters
    ----------
    failures : List[CommandFailureRecord]
        List of classified command failure records.

    Returns
    -------
    Optional[str]
        Advisory text to append to feedback, or None if no relevant failures.
    """
    if not failures:
        return None

    relevant = [
        f for f in failures
        if f.classification in ("implementation", "unknown")
    ]

    if not relevant:
        return None

    lines = ["[Command Execution Advisory]"]
    for f in relevant:
        label = f.classification
        if label == "unknown":
            label = "unknown (may be implementation-related)"

        # Truncate stderr for readability
        detail = (f.stderr or f.stdout or "").strip()
        if len(detail) > 300:
            detail = detail[:300] + "..."

        lines.append(f"- Command `{f.command[:80]}` failed ({label}):")
        if detail:
            lines.append(f"  {detail}")

    return "\n".join(lines)
