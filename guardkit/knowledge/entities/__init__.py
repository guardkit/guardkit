"""
Knowledge graph entities module.

This module provides entity definitions for the knowledge graph integration,
including task outcomes and related data structures.

Public API:
    OutcomeType: Enum for different outcome types
    TaskOutcome: Dataclass for capturing task outcomes
"""

from guardkit.knowledge.entities.outcome import (
    OutcomeType,
    TaskOutcome,
)

__all__ = [
    "OutcomeType",
    "TaskOutcome",
]
