"""
Orchestrator Error Detection and Messaging

This module provides error detection and user-friendly error messaging
for the template-create orchestrator failures.

When the orchestrator cannot run (e.g., missing dependencies, file not found),
this module formats explicit error messages explaining:
- What went wrong
- How to fix it
- What happens next (fallback to manual creation)

Part of TASK-IMP-DDD9: Add explicit orchestrator failure messaging
"""

from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any


def detect_orchestrator_failure() -> Tuple[bool, Optional[str], Optional[Dict[str, Any]]]:
    """
    Check if the template-create orchestrator can run successfully.

    Performs pre-flight checks:
    1. Can import pydantic? (data validation library)
    2. Can import python-frontmatter? (YAML frontmatter parsing)
    3. Does orchestrator file exist?

    Returns:
        Tuple of (can_run, error_type, details):
        - can_run (bool): True if orchestrator can run, False otherwise
        - error_type (str | None): Type of error ('dependencies', 'generic', None)
        - details (dict | None): Error details (missing packages, error message, etc.)

    Example:
        >>> can_run, error_type, details = detect_orchestrator_failure()
        >>> if not can_run:
        ...     display_orchestrator_failure(error_type, details)
    """
    missing_packages = []

    # Check 1: Can import pydantic?
    try:
        import pydantic
    except ImportError:
        missing_packages.append('pydantic')

    # Check 2: Can import python-frontmatter?
    try:
        import frontmatter
    except ImportError:
        missing_packages.append('python-frontmatter')

    # If any packages missing, return dependency error
    if missing_packages:
        return (False, 'dependencies', {'missing_packages': missing_packages})

    # Check 3: Does orchestrator file exist?
    orchestrator_path = Path.home() / '.agentecflow/commands/lib/template_create_orchestrator.py'
    if not orchestrator_path.exists():
        return (
            False,
            'generic',
            {
                'error_message': f'Orchestrator not found at {orchestrator_path}',
                'solution': 'Reinstall GuardKit to restore orchestrator file'
            }
        )

    # All checks passed
    return (True, None, None)


def format_dependency_error(missing_packages: List[str]) -> str:
    """
    Format error message for missing Python dependencies.

    Args:
        missing_packages: List of package names that are missing

    Returns:
        Formatted error message string with install instructions

    Example:
        >>> msg = format_dependency_error(['pydantic', 'python-frontmatter'])
        >>> print(msg)
        ⚠️  ORCHESTRATOR UNAVAILABLE - MISSING DEPENDENCIES
        ...
    """
    separator = "=" * 70

    message = f"""
{separator}
⚠️  ORCHESTRATOR UNAVAILABLE - MISSING DEPENDENCIES
{separator}

The template-create orchestrator could not run due to missing Python packages.

Required packages:
"""

    # Add package list with descriptions
    package_descriptions = {
        'pydantic': 'data validation',
        'python-frontmatter': 'YAML parsing'
    }

    for pkg in missing_packages:
        desc = package_descriptions.get(pkg, 'required dependency')
        message += f"  • {pkg} ({desc})\n"

    message += f"""
Install with:
  python3 -m pip install --user pydantic python-frontmatter

After installation, re-run:
  /template-create [same arguments]

Proceeding with manual template creation...
Note: Manual creation will complete successfully but may omit some
      orchestrator features (e.g., agent enhancement task creation).
{separator}
"""

    return message


def format_timeout_error() -> str:
    """
    Format error message for orchestrator timeout.

    Returns:
        Formatted error message string with timeout explanation

    Example:
        >>> msg = format_timeout_error()
        >>> print(msg)
        ⚠️  ORCHESTRATOR TIMEOUT
        ...
    """
    separator = "=" * 70

    message = f"""
{separator}
⚠️  ORCHESTRATOR TIMEOUT
{separator}

The template-create orchestrator timed out waiting for user input.

This may be due to:
  • Interactive QA session requiring manual input
  • Long-running analysis on large codebase

Solutions:
  1. If you need the orchestrator, install dependencies and re-run
  2. Monitor the orchestrator for completion
  3. Proceed with manual creation (current fallback)

Proceeding with manual template creation...
{separator}
"""

    return message


def format_generic_error(error_message: str = None, exception: Exception = None) -> str:
    """
    Format generic orchestrator error message.

    Args:
        error_message: Optional custom error message
        exception: Optional exception object

    Returns:
        Formatted error message string with error details

    Example:
        >>> msg = format_generic_error(error_message="File not found")
        >>> print(msg)
        ⚠️  ORCHESTRATOR ERROR
        ...
    """
    separator = "=" * 70

    # Determine error message to display
    if error_message:
        error_text = error_message
    elif exception:
        error_text = str(exception)
    else:
        error_text = "Unknown error occurred"

    message = f"""
{separator}
⚠️  ORCHESTRATOR ERROR
{separator}

The template-create orchestrator encountered an error:

{error_text}

Proceeding with manual template creation...
Note: This is a fallback mode. Template will be created successfully
      but some orchestrator features may be unavailable.

Please report this issue:
  https://github.com/anthropics/guardkit/issues
{separator}
"""

    return message


def display_orchestrator_failure(error_type: str, details: Dict[str, Any] = None) -> None:
    """
    Display formatted error message to user based on failure type.

    This function prints a prominent, user-friendly error message that:
    - Explains what went wrong
    - Provides clear remediation steps
    - Announces fallback to manual creation

    Args:
        error_type: Type of error ('dependencies', 'timeout', 'generic')
        details: Optional error details dictionary

    Example:
        >>> display_orchestrator_failure('dependencies', {'missing_packages': ['pydantic']})
        ======================================================================
        ⚠️  ORCHESTRATOR UNAVAILABLE - MISSING DEPENDENCIES
        ...

    Note:
        This function prints directly to stdout for immediate visibility.
        Error messages use 70-character separator lines for visual distinction.
    """
    details = details or {}

    if error_type == 'dependencies':
        missing_packages = details.get('missing_packages', [])
        message = format_dependency_error(missing_packages)

    elif error_type == 'timeout':
        message = format_timeout_error()

    elif error_type == 'generic':
        error_message = details.get('error_message')
        exception = details.get('exception')
        message = format_generic_error(error_message=error_message, exception=exception)

    else:
        # Unknown error type - use generic format
        message = format_generic_error(error_message=f"Unknown error type: {error_type}")

    # Print with blank line before and after for visibility
    print(f"\n{message}\n")


# Convenience function for quick checks
def can_run_orchestrator() -> bool:
    """
    Simple boolean check if orchestrator can run.

    Returns:
        True if orchestrator can run, False otherwise

    Example:
        >>> if not can_run_orchestrator():
        ...     print("Orchestrator unavailable, using manual fallback")
    """
    can_run, _, _ = detect_orchestrator_failure()
    return can_run
