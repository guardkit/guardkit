"""ProjectOverviewEpisode schema for Graphiti integration.

This is a minimal STUB implementation for TDD RED phase.
All tests should FAIL at this stage.
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class ProjectOverviewEpisode:
    """Project overview for North Star context.

    STUB: This implementation is intentionally incomplete.
    Tests will fail until GREEN phase implementation.
    """

    entity_type: str = "project_overview"

    # Required fields
    project_name: str = ""
    purpose: str = ""
    target_users: str = ""

    # Tech stack
    primary_language: str = ""
    frameworks: List[str] = field(default_factory=list)
    key_dependencies: List[str] = field(default_factory=list)

    # Goals and constraints
    key_goals: List[str] = field(default_factory=list)
    constraints: List[str] = field(default_factory=list)

    # Quality info
    testing_strategy: str = ""
    deployment_target: str = ""

    def to_episode_content(self) -> str:
        """Convert to natural language for Graphiti.

        STUB: Not implemented yet. Tests will fail.
        """
        raise NotImplementedError("to_episode_content not implemented yet")

    def get_entity_id(self) -> str:
        """Stable entity ID for upsert.

        STUB: Not implemented yet. Tests will fail.
        """
        raise NotImplementedError("get_entity_id not implemented yet")
