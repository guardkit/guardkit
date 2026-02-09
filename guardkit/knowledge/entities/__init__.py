"""
Knowledge graph entities module.

This module provides entity definitions for the knowledge graph integration,
including task outcomes, feature overviews, failed approaches, turn states,
architecture entities, and related data structures.

Public API:
    OutcomeType: Enum for different outcome types
    TaskOutcome: Dataclass for capturing task outcomes
    FeatureOverviewEntity: Dataclass for capturing feature identity (TASK-GE-001)
    TurnMode: Enum for turn modes (TASK-GE-002)
    TurnStateEntity: Dataclass for capturing turn state (TASK-GE-002)
    Severity: Enum for failure severity levels (TASK-GE-004)
    FailedApproachEpisode: Dataclass for capturing failed approaches (TASK-GE-004)
    ComponentDef: Dataclass for component/bounded context definitions (TASK-SP-001)
    SystemContextDef: Dataclass for system context definitions (TASK-SP-001)
    CrosscuttingConcernDef: Dataclass for crosscutting concerns (TASK-SP-001)
    ArchitectureDecision: Dataclass for architecture decision records (TASK-SP-001)
    ArchitectureContext: Dataclass for aggregated architecture context (TASK-SP-001)
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

from guardkit.knowledge.entities.component import (
    ComponentDef,
)

from guardkit.knowledge.entities.system_context import (
    SystemContextDef,
)

from guardkit.knowledge.entities.crosscutting import (
    CrosscuttingConcernDef,
)

from guardkit.knowledge.entities.architecture_context import (
    ArchitectureDecision,
    ArchitectureContext,
)

__all__ = [
    "OutcomeType",
    "TaskOutcome",
    "FeatureOverviewEntity",
    "TurnMode",
    "TurnStateEntity",
    "Severity",
    "FailedApproachEpisode",
    "ComponentDef",
    "SystemContextDef",
    "CrosscuttingConcernDef",
    "ArchitectureDecision",
    "ArchitectureContext",
]
