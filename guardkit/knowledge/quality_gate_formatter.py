"""
Quality Gate Formatter for GuardKit.

This module provides formatting functions for quality gate configurations
retrieved from Graphiti, specifically for AutoBuild workflows. The formatted
output includes clear thresholds and "do NOT adjust" messaging to prevent
threshold drift during execution.

Public API:
    format_quality_gates: Format quality gate configs for prompt injection

Example:
    from guardkit.knowledge.quality_gate_formatter import format_quality_gates

    quality_gates = [
        {
            "task_type": "feature",
            "coverage_threshold": 0.8,
            "arch_review_threshold": 60,
            "tests_required": True,
        }
    ]

    output = format_quality_gates(quality_gates)
    # Returns formatted markdown with thresholds

References:
    - TASK-GR6-008: Add quality_gate_configs retrieval and formatting
    - FEAT-GR-006: Job-Specific Context Retrieval
"""

from typing import Any, Dict, List, Optional


def format_quality_gates(
    quality_gates: Optional[List[Dict[str, Any]]]
) -> str:
    """Format quality gate configs for prompt injection.

    Converts quality gate configuration dictionaries into human-readable
    markdown format suitable for prompt injection. Includes "do NOT adjust"
    messaging to prevent threshold drift during AutoBuild execution.

    Args:
        quality_gates: List of quality gate config dictionaries.
            Each dict should contain:
            - task_type: str (scaffolding|feature|testing|documentation)
            - coverage_threshold: float (0-1) or None for "not required"
            - arch_review_threshold: int (0-100) or None for "not required"
            - tests_required: bool

    Returns:
        Formatted markdown string ready for prompt injection.
        Returns empty string if quality_gates is None or empty.

    Example:
        gates = [{"task_type": "feature", "coverage_threshold": 0.8, ...}]
        output = format_quality_gates(gates)
        # Returns:
        # ### 🎯 Quality Gate Configs
        #
        # *Use these thresholds - do NOT adjust mid-session*
        #
        # **feature**:
        #   - Coverage: ≥80%
        #   - Arch review: ≥60
        #   - Tests required: Yes
    """
    # Handle None or empty input gracefully
    if not quality_gates:
        return ""

    lines = [
        "### 🎯 Quality Gate Configs",
        "",
        "*Use these thresholds - do NOT adjust mid-session*",
        "",
    ]

    for config in quality_gates[:4]:  # Limit to 4 configs to save tokens
        task_type = config.get("task_type", "unknown")

        # Format coverage threshold
        coverage = _format_coverage_threshold(config.get("coverage_threshold"))

        # Format arch review threshold
        arch_review = _format_arch_review_threshold(config.get("arch_review_threshold"))

        # Format tests required
        tests_req = _format_tests_required(config.get("tests_required"))

        lines.append(f"**{task_type}**:")
        lines.append(f"  - Coverage: {coverage}")
        lines.append(f"  - Arch review: {arch_review}")
        lines.append(f"  - Tests required: {tests_req}")
        lines.append("")

    return "\n".join(lines)


def _format_coverage_threshold(threshold: Optional[float]) -> str:
    """Format coverage threshold as percentage or 'not required'.

    Args:
        threshold: Coverage threshold as float (0-1) or None

    Returns:
        Formatted string like "≥80%" or "not required"
    """
    if threshold is None:
        return "not required"

    # Convert 0-1 to percentage
    percentage = int(threshold * 100)
    return f"≥{percentage}%"


def _format_arch_review_threshold(threshold: Optional[int]) -> str:
    """Format architectural review threshold or 'not required'.

    Args:
        threshold: Arch review threshold (0-100) or None

    Returns:
        Formatted string like "≥60" or "not required"
    """
    if threshold is None:
        return "not required"

    return f"≥{threshold}"


def _format_tests_required(required: Optional[bool]) -> str:
    """Format tests required as Yes/No.

    Args:
        required: Whether tests are required (True/False/None)

    Returns:
        "Yes", "No", or "not required"
    """
    if required is None:
        return "not required"

    return "Yes" if required else "No"
