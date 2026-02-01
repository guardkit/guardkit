"""ImplementationModeEpisode schema for Graphiti integration.

This module provides the ImplementationModeEpisode dataclass for storing
and serializing implementation mode patterns and guidance for Graphiti.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ImplementationModeEpisode:
    """Implementation mode patterns and guidance."""

    entity_type: str = "implementation_mode"

    mode: str = ""  # "direct" | "task-work" | "manual"
    invocation_method: str = ""  # "sdk_query" | "subprocess" | "inline"
    result_location_pattern: str = ""
    state_recovery_strategy: str = ""

    when_to_use: List[str] = field(default_factory=list)
    pitfalls: List[str] = field(default_factory=list)

    def to_episode_content(self) -> str:
        """Convert to natural language for Graphiti."""
        return f"""
        Implementation Mode: {self.mode}

        Invocation: {self.invocation_method}
        Results Location: {self.result_location_pattern}
        State Recovery: {self.state_recovery_strategy}

        WHEN TO USE:
        {chr(10).join(f'- {w}' for w in self.when_to_use)}

        PITFALLS:
        {chr(10).join(f'- {p}' for p in self.pitfalls)}
        """

    def get_entity_id(self) -> str:
        """Stable entity ID for upsert."""
        return f"implementation_mode_{self.mode}"


IMPLEMENTATION_MODE_DEFAULTS = {
    "direct": ImplementationModeEpisode(
        mode="direct",
        invocation_method="inline",
        result_location_pattern="In current context",
        state_recovery_strategy="None needed - atomic execution",
        when_to_use=[
            "Simple, low-complexity tasks (1-3)",
            "No quality gates needed",
            "Quick fixes or documentation",
        ],
        pitfalls=[
            "No automatic testing",
            "No architectural review",
            "Easy to skip quality checks",
        ],
    ),
    "task-work": ImplementationModeEpisode(
        mode="task-work",
        invocation_method="subprocess",
        result_location_pattern=".claude/task-plans/{task_id}-implementation-plan.md",
        state_recovery_strategy="Resume from task file state",
        when_to_use=[
            "Medium to high complexity tasks (4+)",
            "Quality gates required",
            "Features, not just fixes",
        ],
        pitfalls=[
            "Task file must exist before invocation",
            "State persisted in markdown",
            "Subprocess coordination required",
        ],
    ),
    "manual": ImplementationModeEpisode(
        mode="manual",
        invocation_method="human",
        result_location_pattern="Varies",
        state_recovery_strategy="Human-driven",
        when_to_use=[
            "Research tasks",
            "Human decision required",
            "External tooling needed",
        ],
        pitfalls=[
            "No automation",
            "Manual tracking required",
        ],
    ),
}
