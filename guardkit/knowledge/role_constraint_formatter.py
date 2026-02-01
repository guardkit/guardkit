"""
Role Constraint Formatter for GuardKit.

This module provides formatting functions for role constraint configurations
retrieved from Graphiti, specifically for AutoBuild workflows. The formatted
output includes emoji markers for boundaries:
- ✓ for must_do items
- ✗ for must_not_do items
- ❓ for ask_before items

The output emphasizes role boundaries to prevent Player-Coach role reversal
where Player makes decisions or Coach implements code.

Public API:
    format_role_constraints: Format all role constraints for prompt injection
    format_role_constraints_for_actor: Format constraints for a specific actor

Example:
    from guardkit.knowledge.role_constraint_formatter import (
        format_role_constraints,
        format_role_constraints_for_actor,
    )

    role_constraints = [
        {
            "role": "player",
            "must_do": ["Write code", "Create tests"],
            "must_not_do": ["Approve work", "Validate quality"],
            "ask_before": ["Schema changes", "Auth changes"]
        },
        {
            "role": "coach",
            "must_do": ["Validate work", "Check quality"],
            "must_not_do": ["Write code", "Implement features"],
            "ask_before": ["Approving with failing tests"]
        }
    ]

    # Format all constraints
    output = format_role_constraints(role_constraints)

    # Format for specific actor
    player_output = format_role_constraints_for_actor(role_constraints, actor="player")

References:
    - TASK-GR6-007: Add role_constraints retrieval and formatting
    - FEAT-GR-006: Job-Specific Context Retrieval
    - TASK-REV-7549: Player-Coach role reversal finding
"""

from typing import Any, Dict, List, Optional


# Maximum items per section to prevent token explosion
MAX_ITEMS_PER_SECTION = 5


def format_role_constraints(
    role_constraints: Optional[List[Dict[str, Any]]],
    is_autobuild: bool = False,
) -> str:
    """Format role constraints for prompt injection.

    Converts role constraint configuration dictionaries into human-readable
    markdown format suitable for prompt injection. Includes emoji markers
    for clear boundary visualization:
    - ✓ for must_do items
    - ✗ for must_not_do items
    - ❓ for ask_before items

    Args:
        role_constraints: List of role constraint dictionaries.
            Each dict should contain:
            - role: str ("player" | "coach")
            - must_do: List[str] - Actions the role MUST perform
            - must_not_do: List[str] - Actions the role MUST NOT perform
            - ask_before: List[str] - Actions requiring confirmation
        is_autobuild: If True, adds emphasis for AutoBuild contexts

    Returns:
        Formatted markdown string ready for prompt injection.
        Returns empty string if role_constraints is None or empty.

    Example:
        constraints = [{"role": "player", "must_do": ["Write code"], ...}]
        output = format_role_constraints(constraints, is_autobuild=True)
        # Returns:
        # ### 🎭 Role Constraints
        #
        # ⚠️ *Enforce these boundaries - role reversal causes failures*
        #
        # **Player**:
        #   Must do:
        #     ✓ Write code
        #   Must NOT do:
        #     ✗ Approve work
        #   Ask before:
        #     ❓ Schema changes
    """
    # Handle None or empty input gracefully
    if not role_constraints:
        return ""

    # Filter out None and non-dict entries
    valid_constraints = [
        c for c in role_constraints
        if c is not None and isinstance(c, dict)
    ]

    if not valid_constraints:
        return ""

    lines = [
        "### 🎭 Role Constraints",
        "",
    ]

    # Add emphasis for AutoBuild contexts
    if is_autobuild:
        lines.append("⚠️ *Enforce these boundaries - role reversal causes failures*")
    else:
        lines.append("*Enforce these boundaries - constraints prevent errors*")
    lines.append("")

    # Format each role's constraints
    for constraint in valid_constraints[:2]:  # Limit to 2 roles (Player/Coach)
        role = constraint.get("role", "unknown")
        role_display = role.title()

        lines.append(f"**{role_display}**:")

        # Format must_do items with ✓ emoji
        must_do = constraint.get("must_do", [])
        if must_do:
            lines.append("  Must do:")
            for item in must_do[:MAX_ITEMS_PER_SECTION]:
                lines.append(f"    ✓ {item}")

        # Format must_not_do items with ✗ emoji
        must_not_do = constraint.get("must_not_do", [])
        if must_not_do:
            lines.append("  Must NOT do:")
            for item in must_not_do[:MAX_ITEMS_PER_SECTION]:
                lines.append(f"    ✗ {item}")

        # Format ask_before items with ❓ emoji
        ask_before = constraint.get("ask_before", [])
        if ask_before:
            lines.append("  Ask before:")
            for item in ask_before[:MAX_ITEMS_PER_SECTION]:
                lines.append(f"    ❓ {item}")

        lines.append("")

    return "\n".join(lines)


def format_role_constraints_for_actor(
    role_constraints: Optional[List[Dict[str, Any]]],
    actor: str,
    is_autobuild: bool = False,
) -> str:
    """Format role constraints for a specific actor (player/coach).

    Filters the role constraints to only include the specified actor's
    constraints, then formats them for prompt injection.

    Args:
        role_constraints: List of role constraint dictionaries
        actor: The actor to filter for ("player" | "coach")
        is_autobuild: If True, adds emphasis for AutoBuild contexts

    Returns:
        Formatted markdown string for the specified actor only.
        Returns empty string if actor not found or inputs invalid.

    Example:
        constraints = [
            {"role": "player", "must_do": ["Write code"], ...},
            {"role": "coach", "must_do": ["Validate work"], ...}
        ]
        output = format_role_constraints_for_actor(constraints, actor="player")
        # Returns only Player constraints
    """
    # Handle None or empty input
    if not role_constraints:
        return ""

    # Normalize actor to lowercase for comparison
    actor_lower = actor.lower()

    # Filter to specified actor
    filtered = [
        c for c in role_constraints
        if c is not None
        and isinstance(c, dict)
        and c.get("role", "").lower() == actor_lower
    ]

    if not filtered:
        return ""

    return format_role_constraints(filtered, is_autobuild=is_autobuild)
