"""
Design decision entity for architecture knowledge.

This module provides the DesignDecision dataclass for capturing
design decision records (DDRs) in the knowledge graph. DDRs are
similar to ADRs but scoped to /system-design artefacts.

Public API:
    DesignDecision: Frozen dataclass for Design Decision Records (DDRs)

Example:
    from guardkit.knowledge.entities.design_decision import DesignDecision

    ddr = DesignDecision(
        number=1,
        title="Use CQRS Pattern",
        context="High read frequency, complex writes",
        decision="Implement CQRS",
        rationale="Independent scaling of reads and writes",
        alternatives_considered=["Simple CRUD", "Event Sourcing only"],
        consequences=["Eventual consistency"],
        related_components=["Order Management"],
        status="accepted",
    )
"""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class DesignDecision:
    """Captures a Design Decision Record (DDR).

    This entity represents a significant design decision for /system-design
    artefacts, following the DDR format (context, decision, rationale,
    alternatives, consequences).

    Attributes:
        number: DDR number (1, 2, 3, etc.)
        title: Decision title
        context: Why this decision was needed
        decision: What was decided
        rationale: Why this decision was chosen over alternatives
        alternatives_considered: Options that were evaluated
        consequences: List of consequences (positive and negative)
        related_components: Components affected by this decision
        status: Decision status (proposed, accepted, deprecated, superseded)
        superseded_by: Entity ID of the DDR that supersedes this one
        supersedes: Entity ID of the DDR that this one supersedes

    Example:
        ddr = DesignDecision(
            number=1,
            title="Use CQRS Pattern",
            context="Need read/write separation",
            decision="Implement CQRS",
            rationale="Allows independent scaling",
            status="accepted",
        )
    """

    # Required fields
    number: int
    title: str
    context: str
    decision: str
    rationale: str
    status: str  # proposed, accepted, deprecated, superseded

    # Optional fields with defaults
    alternatives_considered: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)
    related_components: List[str] = field(default_factory=list)
    superseded_by: Optional[str] = None
    supersedes: Optional[str] = None

    @property
    def entity_id(self) -> str:
        """Generate stable entity ID in format: DDR-{NNN}.

        The entity ID is deterministic - same number always produces
        the same ID regardless of other field values.

        Returns:
            Entity ID string (e.g., "DDR-001", "DDR-042")
        """
        return f"DDR-{self.number:03d}"

    def to_episode_body(self) -> dict:
        """Convert to Graphiti episode body.

        Creates a dictionary representation suitable for storage
        in Graphiti as an episode body. Returns only domain data;
        metadata fields are injected by GraphitiClient.

        Optional fields (alternatives_considered, superseded_by, supersedes)
        are excluded when empty/None to keep the body compact.

        Returns:
            Dictionary containing DDR fields (no _metadata).
        """
        body: dict = {
            "number": self.number,
            "title": self.title,
            "context": self.context,
            "decision": self.decision,
            "rationale": self.rationale,
            "status": self.status,
            "consequences": self.consequences,
            "related_components": self.related_components,
        }

        # Conditionally include optional fields
        if self.alternatives_considered:
            body["alternatives_considered"] = self.alternatives_considered

        if self.superseded_by is not None:
            body["superseded_by"] = self.superseded_by

        if self.supersedes is not None:
            body["supersedes"] = self.supersedes

        return body
