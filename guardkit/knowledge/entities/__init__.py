"""
Knowledge graph entities module.

This module provides entity definitions for the knowledge graph integration,
including task outcomes, feature overviews, and related data structures.

Public API:
    OutcomeType: Enum for different outcome types
    TaskOutcome: Dataclass for capturing task outcomes
    FeatureOverviewEntity: Dataclass for capturing feature identity (TASK-GE-001)
"""

from guardkit.knowledge.entities.outcome import (
    OutcomeType,
    TaskOutcome,
)

from guardkit.knowledge.entities.feature_overview import (
    FeatureOverviewEntity,
)

__all__ = [
    "OutcomeType",
    "TaskOutcome",
    "FeatureOverviewEntity",
]
