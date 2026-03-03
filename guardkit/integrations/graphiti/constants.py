"""Constants for Graphiti integration.

This module defines constants and enumerations used across
the Graphiti integration, including source types for episode metadata,
project group definitions, and system group definitions.

Group definitions are imported from guardkit._group_defs (single source
of truth) and re-exported here for the public integrations API.
"""

from enum import Enum

from guardkit._group_defs import (
    PROJECT_GROUPS,
    SYSTEM_GROUPS,
    PROJECT_GROUP_NAMES,
    SYSTEM_GROUP_IDS,
)


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


__all__ = [
    "SourceType",
    "PROJECT_GROUPS",
    "SYSTEM_GROUPS",
    "PROJECT_GROUP_NAMES",
    "SYSTEM_GROUP_IDS",
]
