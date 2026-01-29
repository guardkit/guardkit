"""
Knowledge graph entities module.

This module provides entity definitions for the knowledge graph integration,
including task outcomes, feature overviews, failed approaches, turn states,
and related data structures.

Public API:
    OutcomeType: Enum for different outcome types
    TaskOutcome: Dataclass for capturing task outcomes
    FeatureOverviewEntity: Dataclass for capturing feature identity (TASK-GE-001)
    TurnMode: Enum for turn modes (TASK-GE-002)
    TurnStateEntity: Dataclass for capturing turn state (TASK-GE-002)
    Severity: Enum for failure severity levels (TASK-GE-004)
    FailedApproachEpisode: Dataclass for capturing failed approaches (TASK-GE-004)
"""

from guardkit.knowledge.entities.outcome import (
    OutcomeType,
    TaskOutcome,
)

from guardkit.knowledge.entities.feature_overview import (
    FeatureOverviewEntity,
)

from guardkit.knowledge.entities.turn_state import (
    TurnMode,
    TurnStateEntity,
)

from guardkit.knowledge.entities.failed_approach import (
    Severity,
    FailedApproachEpisode,
)

__all__ = [
    "OutcomeType",
    "TaskOutcome",
    "FeatureOverviewEntity",
    "TurnMode",
    "TurnStateEntity",
    "Severity",
    "FailedApproachEpisode",
]
