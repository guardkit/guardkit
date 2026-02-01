"""ProjectOverviewEpisode schema for Graphiti integration.

This module provides the ProjectOverviewEpisode dataclass for storing
and serializing project overview information for Graphiti's North Star context.
"""

import re
from dataclasses import dataclass, field
from typing import List


@dataclass
class ProjectOverviewEpisode:
    """Project overview for North Star context.

    This dataclass captures essential project information including:
    - Project identity (name, purpose, target users)
    - Tech stack (language, frameworks, dependencies)
    - Goals and constraints
    - Quality information (testing, deployment)
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

        Generates well-formatted natural language content suitable for
        Graphiti episode ingestion. Content starts with a capital letter
        and includes proper punctuation.

        Raises:
            ValueError: If project_name is empty.

        Returns:
            str: Natural language description of the project.
        """
        if not self.project_name.strip():
            raise ValueError("project_name is required for episode content")

        # Filter empty strings from list fields
        frameworks = [f for f in self.frameworks if f.strip()]
        key_dependencies = [d for d in self.key_dependencies if d.strip()]
        key_goals = [g for g in self.key_goals if g.strip()]
        constraints = [c for c in self.constraints if c.strip()]

        # Build content sections
        lines = []

        # Project identity section
        lines.append(f"Project: {self.project_name}.")

        if self.purpose:
            lines.append(f"Purpose: {self.purpose}.")

        if self.target_users:
            lines.append(f"Target Users: {self.target_users}.")

        # Tech stack section
        if self.primary_language:
            lines.append(f"Primary Language: {self.primary_language}.")

        if frameworks:
            lines.append(f"Frameworks: {', '.join(frameworks)}.")

        if key_dependencies:
            lines.append(f"Key Dependencies: {', '.join(key_dependencies)}.")

        # Goals section
        if key_goals:
            goals_text = "; ".join(key_goals)
            lines.append(f"Key Goals: {goals_text}.")

        # Constraints section
        if constraints:
            constraints_text = "; ".join(constraints)
            lines.append(f"Constraints: {constraints_text}.")

        # Quality section
        if self.testing_strategy:
            lines.append(f"Testing Strategy: {self.testing_strategy}.")

        if self.deployment_target:
            lines.append(f"Deployment Target: {self.deployment_target}.")

        return " ".join(lines)

    def get_entity_id(self) -> str:
        """Stable entity ID for upsert.

        Generates a stable, normalized entity ID from the project name.
        Spaces and special characters are converted to underscores.
        Empty project names result in a default identifier.

        Returns:
            str: Entity ID in format "project_overview_{normalized_name}".
        """
        if not self.project_name.strip():
            return "project_overview_unnamed"

        # Normalize: replace spaces and special chars with underscores
        normalized = re.sub(r'[^a-zA-Z0-9_]', '_', self.project_name)
        # Collapse multiple underscores
        normalized = re.sub(r'_+', '_', normalized)
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')

        return f"project_overview_{normalized}"
