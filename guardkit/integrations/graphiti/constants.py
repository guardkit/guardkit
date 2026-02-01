"""Constants for Graphiti integration.

This module defines constants and enumerations used across
the Graphiti integration, including source types for episode metadata,
project group definitions, and system group definitions.
"""

from enum import Enum


class SourceType(str, Enum):
    """Source types for episode metadata.

    Defines how an episode was created or added to the knowledge graph.

    Values:
        GUARDKIT_SEEDING: Episode created during initial project seeding
        USER_ADDED: Episode manually added by a user
        AUTO_CAPTURED: Episode automatically captured from system events
    """
    GUARDKIT_SEEDING = "guardkit_seeding"
    USER_ADDED = "user_added"
    AUTO_CAPTURED = "auto_captured"


# Project-specific group IDs with descriptions
PROJECT_GROUPS = {
    "project_overview": "High-level project purpose and goals",
    "project_architecture": "System architecture and patterns",
    "feature_specs": "Feature specifications and requirements",
    "project_decisions": "Architecture Decision Records (ADRs)",
    "project_constraints": "Constraints and limitations",
    "domain_knowledge": "Domain terminology and concepts",
}

# System-level group IDs with descriptions
SYSTEM_GROUPS = {
    "role_constraints": "Player/Coach role boundaries",
    "quality_gate_configs": "Task-type specific quality thresholds",
    "implementation_modes": "Direct vs task-work patterns",
}
