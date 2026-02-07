"""
Feature overview entity definition.

This module provides the FeatureOverviewEntity dataclass for capturing
the "big picture" of major features in the knowledge graph. Feature overviews
provide critical context that prevents session context loss by ensuring
Claude Code sessions always know what a feature IS and IS NOT.

Public API:
    FeatureOverviewEntity: Dataclass for capturing feature identity

Example:
    from guardkit.knowledge.entities.feature_overview import FeatureOverviewEntity

    overview = FeatureOverviewEntity(
        id="feature-build",
        name="feature-build",
        tagline="Autonomous task implementation with Player-Coach validation",
        purpose="Execute multi-task features autonomously",
        what_it_is=["An autonomous orchestrator", "A quality enforcement system"],
        what_it_is_not=["NOT an assistant", "NOT an auto-merger"],
        invariants=["Player implements, Coach validates", "Worktrees preserved"],
        architecture_summary="Feature-build orchestrates multiple tasks in waves",
        key_components=["FeatureOrchestrator", "CoachValidator"],
        key_decisions=["ADR-FB-001", "ADR-FB-002"]
    )
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List


@dataclass
class FeatureOverviewEntity:
    """Captures the 'big picture' of a major feature.

    This entity captures the essential identity of a feature - what it is,
    what it's not, and the rules it must follow. This information is critical
    for preventing context loss in Claude Code sessions.

    Attributes:
        id: Feature identifier (FEAT-XXX or kebab-case name)
        name: Human-readable feature name
        tagline: One-line description of the feature

        purpose: What the feature exists to do
        what_it_is: Positive definitions (what this feature IS)
        what_it_is_not: Negative definitions (misconceptions to avoid)

        invariants: Rules that must NEVER be violated

        architecture_summary: 2-3 sentence architecture description
        key_components: Main components involved in the feature
        key_decisions: List of ADR IDs for related decisions

        created_at: When this overview was created
        updated_at: When this overview was last updated

    Example:
        overview = FeatureOverviewEntity(
            id="feature-build",
            name="feature-build",
            tagline="Autonomous task implementation",
            purpose="Execute features autonomously using Player-Coach pattern",
            what_it_is=["An autonomous orchestrator"],
            what_it_is_not=["NOT an assistant"],
            invariants=["Player implements, Coach validates"],
            architecture_summary="Feature-build orchestrates tasks in waves",
            key_components=["FeatureOrchestrator"],
            key_decisions=["ADR-FB-001"]
        )
    """

    # Identity
    id: str  # FEAT-XXX or feature name (e.g., "feature-build")
    name: str  # Human-readable name
    tagline: str  # One-line description

    # Purpose
    purpose: str  # What it exists to do
    what_it_is: List[str]  # Positive definitions
    what_it_is_not: List[str]  # Negative definitions (misconceptions)

    # Constraints
    invariants: List[str]  # Rules that must NEVER be violated

    # Architecture
    architecture_summary: str  # 2-3 sentence architecture
    key_components: List[str]  # Main components involved
    key_decisions: List[str]  # ADR IDs

    # Metadata with defaults
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Creates a dictionary representation suitable for storage
        in Graphiti as an episode body. Returns only domain data;
        metadata fields like entity_type, created_at, and updated_at
        are injected by GraphitiClient.

        Returns:
            Dictionary containing all feature overview fields.
        """
        return {
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "purpose": self.purpose,
            "what_it_is": self.what_it_is,
            "what_it_is_not": self.what_it_is_not,
            "invariants": self.invariants,
            "architecture_summary": self.architecture_summary,
            "key_components": self.key_components,
            "key_decisions": self.key_decisions
        }
