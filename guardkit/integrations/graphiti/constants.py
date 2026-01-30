"""Constants for Graphiti integration.

This module defines constants and enumerations used across
the Graphiti integration, including source types for episode metadata.
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
