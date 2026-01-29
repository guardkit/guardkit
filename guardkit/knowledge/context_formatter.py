"""
Context formatting module for GuardKit session initialization.

This module formats CriticalContext into human-readable markdown for injection
into Claude Code sessions. The formatted output is designed to:
- Be concise but informative
- Highlight critical decisions and warnings
- Follow markdown formatting conventions
- Respect token limits

Example Usage:
    from guardkit.knowledge.context_loader import load_critical_context
    from guardkit.knowledge.context_formatter import format_context_for_injection

    context = await load_critical_context(command="feature-build")
    context_text = format_context_for_injection(context)

    # context_text is now ready for injection into the session prompt
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging

from guardkit.knowledge.context_loader import CriticalContext

logger = logging.getLogger(__name__)


@dataclass
class ContextFormatterConfig:
    """Configuration for context formatting.

    Attributes:
        max_decisions: Maximum number of architecture decisions to include
        max_failure_patterns: Maximum number of failure patterns to include
        max_quality_gates: Maximum number of quality gates to include
        max_system_context: Maximum number of system context items
        include_headers: Whether to include markdown section headers
    """
    max_decisions: int = 5
    max_failure_patterns: int = 3
    max_quality_gates: int = 3
    max_system_context: int = 3
    include_headers: bool = True


def format_context_for_injection(
    context: CriticalContext,
    config: Optional[ContextFormatterConfig] = None
) -> str:
    """Format context for injection into Claude Code session.

    Takes a CriticalContext and formats it as markdown for injection
    into the session prompt. Prioritizes architecture decisions and
    failure patterns as these are the most critical.

    Args:
        context: CriticalContext loaded from Graphiti
        config: Optional ContextFormatterConfig for customization

    Returns:
        Formatted markdown string ready for injection.
        Returns empty string if no meaningful context.

    Example:
        context = await load_critical_context(command="feature-build")
        text = format_context_for_injection(context)
        # text contains markdown with architecture decisions, etc.
    """
    if config is None:
        config = ContextFormatterConfig()

    sections = []

    # Critical decisions (always show first)
    decisions_section = _format_architecture_decisions_section(
        context.architecture_decisions[:config.max_decisions]
    )
    if decisions_section:
        sections.append(decisions_section)

    # Failure patterns (always show - prevent repeating mistakes)
    failure_section = _format_failure_patterns_section(
        context.failure_patterns[:config.max_failure_patterns]
    )
    if failure_section:
        sections.append(failure_section)

    # Quality gates (for task-work and feature-build)
    gates_section = _format_quality_gates_section(
        context.quality_gates[:config.max_quality_gates]
    )
    if gates_section:
        sections.append(gates_section)

    # System context (general knowledge - show if room)
    system_section = _format_system_context_section(
        context.system_context[:config.max_system_context]
    )
    if system_section:
        sections.append(system_section)

    return "\n".join(sections)


def _format_architecture_decisions_section(
    decisions: List[Dict[str, Any]]
) -> str:
    """Format architecture decisions section.

    Args:
        decisions: List of architecture decision results from Graphiti

    Returns:
        Formatted markdown section, or empty string if no decisions.
    """
    if not decisions:
        return ""

    lines = ["## Architecture Decisions (MUST FOLLOW)\n"]

    for decision in decisions:
        body = decision.get('body', {})
        if body is None:
            body = {}

        title = body.get('title', 'Unknown')
        decision_text = body.get('decision', '')

        # Handle None values
        if title is None:
            title = 'Unknown'
        if decision_text is None:
            decision_text = ''

        # Skip empty entries
        if not title and not decision_text:
            continue

        # Format as bullet point
        if decision_text:
            lines.append(f"- **{title}**: {decision_text}")
        else:
            lines.append(f"- **{title}**")

    lines.append("")  # Trailing newline

    # Return empty if only header
    if len(lines) <= 2:
        return ""

    return "\n".join(lines)


def _format_failure_patterns_section(
    patterns: List[Dict[str, Any]]
) -> str:
    """Format failure patterns section.

    Args:
        patterns: List of failure pattern results from Graphiti

    Returns:
        Formatted markdown section, or empty string if no patterns.
    """
    if not patterns:
        return ""

    lines = ["## Known Failures (AVOID THESE)\n"]

    for pattern in patterns:
        body = pattern.get('body', {})
        if body is None:
            body = {}

        description = body.get('description', '')

        # Handle None values
        if description is None:
            description = ''

        # Skip empty entries
        if not description:
            continue

        lines.append(f"- {description}")

    lines.append("")  # Trailing newline

    # Return empty if only header
    if len(lines) <= 2:
        return ""

    return "\n".join(lines)


def _format_quality_gates_section(
    gates: List[Dict[str, Any]]
) -> str:
    """Format quality gates section.

    Args:
        gates: List of quality gate results from Graphiti

    Returns:
        Formatted markdown section, or empty string if no gates.
    """
    if not gates:
        return ""

    lines = ["## Quality Gates\n"]

    for gate in gates:
        body = gate.get('body', {})
        if body is None:
            body = {}

        phase = body.get('phase', '')
        requirement = body.get('requirement', '')

        # Handle None values
        if phase is None:
            phase = ''
        if requirement is None:
            requirement = ''

        # Skip empty entries
        if not phase and not requirement:
            continue

        if phase and requirement:
            lines.append(f"- {phase}: {requirement}")
        elif phase:
            lines.append(f"- {phase}")
        else:
            lines.append(f"- {requirement}")

    lines.append("")  # Trailing newline

    # Return empty if only header
    if len(lines) <= 2:
        return ""

    return "\n".join(lines)


def _format_system_context_section(
    context_items: List[Dict[str, Any]]
) -> str:
    """Format system context section.

    Args:
        context_items: List of system context results from Graphiti

    Returns:
        Formatted markdown section, or empty string if no items.
    """
    if not context_items:
        return ""

    lines = ["## System Context\n"]

    for item in context_items:
        body = item.get('body', {})
        if body is None:
            body = {}

        name = body.get('name', '')
        description = body.get('description', '')

        # Handle None values
        if name is None:
            name = ''
        if description is None:
            description = ''

        # Skip empty entries
        if not name and not description:
            continue

        if name and description:
            # Truncate very long descriptions
            if len(description) > 200:
                description = description[:200] + "..."
            lines.append(f"- **{name}**: {description}")
        elif name:
            lines.append(f"- **{name}**")
        else:
            lines.append(f"- {description}")

    lines.append("")  # Trailing newline

    # Return empty if only header
    if len(lines) <= 2:
        return ""

    return "\n".join(lines)
