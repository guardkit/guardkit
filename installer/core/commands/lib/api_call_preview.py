#!/usr/bin/env python3
"""API call preview module for Phase 2.8 checkpoint verification.

This module provides functions to extract and display planned library API calls
from implementation plans. It helps users verify that the AI understood the library
APIs correctly before implementation begins.

Key Features:
    - Extracts API calls from code blocks in implementation plans
    - Detects library-specific API patterns (method calls, initialization)
    - Formats calls for clear visual display at Phase 2.8 checkpoint
    - Graceful handling when no libraries detected or plan lacks API calls
    - Token-efficient formatting (limits display to 10 calls per library)

Module Design:
    - No external dependencies beyond standard library (re, typing)
    - Pattern-based detection using compiled regex
    - Defensive error handling (returns empty on failures)
    - Type hints on all public functions
    - Logging for debugging without breaking execution

Integration:
    This module is called during Phase 2.8 (Human Checkpoint) after implementation
    planning. The API preview is shown only when:
    - Libraries were detected in Phase 2.1
    - Complexity >= 4 (not simple tasks)
    - Library context was not explicitly skipped

Example:
    >>> from installer.core.commands.lib.api_call_preview import extract_planned_api_calls
    >>> plan = '''
    ... ```python
    ... graphiti = Graphiti(uri, user, password)
    ... await graphiti.search(query)
    ... ```
    ... '''
    >>> calls = extract_planned_api_calls(plan, ["graphiti-core"])
    >>> for lib, lib_calls in calls.items():
    ...     print(f"{lib}: {len(lib_calls)} calls")
    graphiti-core: 2 calls

Part of: Library Knowledge Gap Detection System (TASK-LKG-005)
Author: Claude (Anthropic)
Created: 2026-01-30
"""

import logging
import re
from typing import Dict, List

# Configure logging (no propagation unless explicitly enabled by caller)
logger = logging.getLogger(__name__)

# Compiled regex patterns for code block extraction
_CODE_BLOCK_PATTERN = re.compile(
    r'```(?:python|py|javascript|js|typescript|ts)?\s*\n(.*?)```',
    re.DOTALL | re.IGNORECASE
)


def _normalize_library_name(library_name: str) -> str:
    """Normalize library name for pattern matching.

    Converts library name to a form suitable for regex pattern construction.
    Handles common naming conventions like hyphens and underscores.

    Args:
        library_name: Library name to normalize (e.g., "graphiti-core")

    Returns:
        Normalized name suitable for pattern matching (e.g., "graphiti")

    Examples:
        >>> _normalize_library_name("graphiti-core")
        'graphiti'
        >>> _normalize_library_name("fast_api")
        'fast'
    """
    # Remove common suffixes and prefixes
    name = library_name.lower().strip()

    # Split on hyphens and underscores, take first part as base name
    # This handles cases like "graphiti-core" -> "graphiti"
    parts = re.split(r'[-_]', name)
    return parts[0] if parts else name


def _extract_code_blocks(text: str) -> List[str]:
    """Extract code blocks from markdown text.

    Scans text for markdown code blocks (```...```) and returns their contents.
    Supports both language-tagged and untagged code blocks.

    Args:
        text: Implementation plan text containing code blocks

    Returns:
        List of code block contents (without markdown fences)

    Examples:
        >>> text = '```python\\ngraphiti = Graphiti()\\n```'
        >>> blocks = _extract_code_blocks(text)
        >>> len(blocks)
        1
        >>> 'graphiti = Graphiti()' in blocks[0]
        True
    """
    if not text:
        return []

    try:
        matches = _CODE_BLOCK_PATTERN.findall(text)
        return [m.strip() for m in matches if m.strip()]
    except Exception as e:
        logger.warning(f"Failed to extract code blocks: {e}")
        return []


def is_api_call(line: str, lib_name: str) -> bool:
    """Check if a line contains an API call for the specified library.

    Detects common API call patterns including:
    - Method calls: library.method(...)
    - Async calls: await library.method(...)
    - Initialization: library = Constructor(...)
    - Import statements: from library import ...

    Args:
        line: Single line of code to check
        lib_name: Library name to check for (e.g., "graphiti-core")

    Returns:
        True if line contains an API call for the library, False otherwise

    Examples:
        >>> is_api_call("graphiti = Graphiti(uri)", "graphiti-core")
        True
        >>> is_api_call("await graphiti.search(query)", "graphiti-core")
        True
        >>> is_api_call("# comment about graphiti", "graphiti-core")
        False
        >>> is_api_call("result = some_other_lib.call()", "graphiti-core")
        False
    """
    if not line or not lib_name:
        return False

    try:
        # Normalize library name for pattern matching
        normalized = _normalize_library_name(lib_name)

        # Also try with underscores (common in Python imports)
        normalized_underscore = lib_name.replace("-", "_").lower()

        # Build patterns for detection
        patterns = [
            # Method calls: graphiti.search( (with optional whitespace)
            rf'\b{re.escape(normalized)}\s*\.\s*\w+\s*\(',
            # Assignment: graphiti = Constructor( (includes lowercase function calls)
            rf'\b{re.escape(normalized)}\s*=',
            # Async calls: await graphiti.method( (with optional whitespace)
            rf'\bawait\s+{re.escape(normalized)}\s*\.\s*\w+',
            # Import with original name: from graphiti_core import
            rf'\bfrom\s+{re.escape(normalized_underscore)}\b',
            # Import: import graphiti_core
            rf'\bimport\s+{re.escape(normalized_underscore)}\b',
            # Constructor call: Graphiti( (capitalized version)
            rf'\b{re.escape(normalized.capitalize())}\s*\(',
            # Function call: graphiti( (lowercase version for function-style calls)
            rf'\b{re.escape(normalized)}\s*\(',
        ]

        # Check if any pattern matches
        line_lower = line.lower()
        for pattern in patterns:
            if re.search(pattern, line_lower):
                return True

        return False

    except Exception as e:
        logger.warning(f"Error checking API call pattern: {e}")
        return False


def extract_planned_api_calls(
    implementation_plan: str,
    library_names: List[str]
) -> Dict[str, List[str]]:
    """Extract planned API calls from implementation plan.

    Scans the implementation plan for code blocks containing API calls
    to the specified libraries. Returns a mapping of library names to
    the list of API calls found.

    Args:
        implementation_plan: The generated implementation plan text
        library_names: Libraries detected in Phase 2.1

    Returns:
        Dict mapping library name to list of API call lines.
        Empty dict if no API calls found or on error.

    Examples:
        >>> plan = '''
        ... Implementation:
        ... ```python
        ... graphiti = Graphiti(uri, user, password)
        ... await graphiti.build_indices()
        ... results = await graphiti.search(query)
        ... ```
        ... '''
        >>> calls = extract_planned_api_calls(plan, ["graphiti-core"])
        >>> len(calls["graphiti-core"])
        3
        >>> "graphiti = Graphiti(uri, user, password)" in calls["graphiti-core"]
        True
    """
    if not implementation_plan or not library_names:
        logger.debug("Empty plan or no libraries provided")
        return {}

    try:
        calls: Dict[str, List[str]] = {}

        # Extract all code blocks from plan
        code_blocks = _extract_code_blocks(implementation_plan)

        if not code_blocks:
            logger.debug("No code blocks found in implementation plan")
            return {}

        # For each library, find matching API calls
        for lib_name in library_names:
            lib_calls: List[str] = []

            for block in code_blocks:
                # Check each line in the code block
                for line in block.split('\n'):
                    stripped = line.strip()

                    # Skip empty lines and comments
                    if not stripped or stripped.startswith('#'):
                        continue

                    # Check if this line is an API call for this library
                    if is_api_call(stripped, lib_name):
                        lib_calls.append(stripped)

            # Only add to result if we found calls
            if lib_calls:
                calls[lib_name] = lib_calls

        return calls

    except Exception as e:
        logger.error(f"Failed to extract API calls: {e}")
        return {}


def format_api_preview(calls: Dict[str, List[str]]) -> str:
    """Format API calls for display at Phase 2.8 checkpoint.

    Generates a formatted string showing planned API calls grouped by library.
    Limits display to 10 calls per library to avoid overwhelming the user.

    Args:
        calls: Dict mapping library name to list of API calls

    Returns:
        Formatted string for display, or empty string if no calls

    Examples:
        >>> calls = {
        ...     "graphiti-core": [
        ...         "graphiti = Graphiti(uri, user, password)",
        ...         "await graphiti.search(query)"
        ...     ]
        ... }
        >>> preview = format_api_preview(calls)
        >>> "📚 PLANNED LIBRARY API CALLS" in preview
        True
        >>> "graphiti-core:" in preview
        True
    """
    if not calls:
        return ""

    try:
        lines = []
        lines.append("─" * 75)
        lines.append("📚 PLANNED LIBRARY API CALLS")
        lines.append("─" * 75)
        lines.append("")

        for lib_name, lib_calls in sorted(calls.items()):
            lines.append(f"{lib_name}:")

            # Display up to 10 calls
            display_calls = lib_calls[:10]
            for i, call in enumerate(display_calls, 1):
                lines.append(f"  {i}. {call}")

            # Show count if truncated
            if len(lib_calls) > 10:
                remaining = len(lib_calls) - 10
                lines.append(f"  ... and {remaining} more")

            lines.append("")

        lines.append("Do these match the library's actual API?")
        lines.append("")

        return "\n".join(lines)

    except Exception as e:
        logger.error(f"Failed to format API preview: {e}")
        return ""


def should_show_api_preview(task_context: dict) -> bool:
    """Determine if API preview should be shown at Phase 2.8 checkpoint.

    API preview is shown only when:
    - Libraries were detected in Phase 2.1
    - Library context was not explicitly skipped
    - Task complexity is >= 4 (not a simple task)

    Args:
        task_context: Task context dictionary containing:
            - library_context: Optional dict of library contexts
            - library_context_skipped: Optional bool
            - complexity: Optional int (defaults to 5 if not provided)

    Returns:
        True if API preview should be shown, False otherwise

    Examples:
        >>> should_show_api_preview({"complexity": 2})
        False
        >>> should_show_api_preview({"complexity": 5, "library_context": {"lib": {}}})
        True
        >>> should_show_api_preview({"library_context_skipped": True})
        False
    """
    if not isinstance(task_context, dict):
        return False

    try:
        # Check if libraries were detected
        if not task_context.get("library_context"):
            logger.debug("No library context found, skipping API preview")
            return False

        # Check if library context was explicitly skipped
        if task_context.get("library_context_skipped"):
            logger.debug("Library context was skipped, skipping API preview")
            return False

        # Check complexity threshold (simple tasks don't need API preview)
        complexity = task_context.get("complexity", 5)
        if complexity < 4:
            logger.debug(f"Task complexity {complexity} < 4, skipping API preview")
            return False

        return True

    except Exception as e:
        logger.error(f"Error checking API preview conditions: {e}")
        return False


# Public API
__all__ = [
    # Core extraction functions
    "extract_planned_api_calls",
    "is_api_call",

    # Formatting and display
    "format_api_preview",
    "should_show_api_preview",
]
