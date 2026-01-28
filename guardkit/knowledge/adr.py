"""
ADR (Architecture Decision Record) Entity Model.

Provides dataclasses and enums for representing Architecture Decision Records
that are stored in Graphiti for knowledge graph persistence.

Public API:
    ADRStatus: Enum for ADR lifecycle states
    ADRTrigger: Enum for what triggered the ADR creation
    ADREntity: Dataclass representing a complete ADR

Example:
    from guardkit.knowledge.adr import ADREntity, ADRStatus, ADRTrigger

    adr = ADREntity(
        id="ADR-0001",
        title="Use PostgreSQL for primary database",
        status=ADRStatus.ACCEPTED,
        trigger=ADRTrigger.TASK_REVIEW,
        context="Need reliable ACID guarantees",
        decision="Use PostgreSQL 15",
        rationale="Strong ACID compliance, mature ecosystem"
    )
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional


class ADRStatus(Enum):
    """ADR lifecycle status.

    Represents the current state of an Architecture Decision Record.

    Values:
        PROPOSED: Decision under consideration
        ACCEPTED: Decision made and active
        DEPRECATED: Decision no longer recommended
        SUPERSEDED: Replaced by another ADR
    """
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class ADRTrigger(Enum):
    """What triggered the ADR creation.

    Tracks the source of the decision for traceability.

    Values:
        CLARIFYING_QUESTION: From /feature-plan clarifying questions
        TASK_REVIEW: From /task-review acceptance/rejection
        IMPLEMENTATION_CHOICE: From /task-work implementation decisions
        MANUAL: Explicitly created by user
        DISCOVERED: From code analysis (TASK-GI-007)
    """
    CLARIFYING_QUESTION = "clarifying_question"
    TASK_REVIEW = "task_review"
    IMPLEMENTATION_CHOICE = "implementation"
    MANUAL = "manual"
    DISCOVERED = "discovered"


@dataclass
class ADREntity:
    """Architecture Decision Record stored in Graphiti.

    Represents a complete ADR with all metadata, context, and relationships.
    Designed for storage in Graphiti as episodes with the "adrs" group.

    Attributes:
        id: ADR identifier (format: ADR-XXXX)
        title: Brief decision title
        status: Current lifecycle status (default: ACCEPTED)
        trigger: What triggered the ADR creation (default: MANUAL)
        source_task_id: Task ID that triggered this ADR
        source_feature_id: Feature ID that triggered this ADR
        source_command: Command that triggered this ADR (e.g., "feature-plan")
        context: What situation prompted this decision
        decision: What we decided
        rationale: Why we decided this
        alternatives_considered: List of alternatives that were considered
        consequences: List of consequences of this decision
        supersedes: ADR ID this replaces
        superseded_by: ADR ID that replaced this
        related_adrs: List of related ADR IDs
        created_at: When the ADR was created
        decided_at: When the decision was made
        deprecated_at: When the ADR was deprecated
        tags: List of searchable tags
        confidence: How confident in this decision (0-1)

    Example:
        adr = ADREntity(
            id="ADR-0001",
            title="Use PostgreSQL for primary database",
            context="Need reliable ACID guarantees for transactions",
            decision="Use PostgreSQL 15 as primary database",
            rationale="Strong ACID compliance, mature ecosystem, team expertise"
        )
    """

    # Identity (required)
    id: str
    title: str

    # Status (with defaults)
    status: ADRStatus = ADRStatus.ACCEPTED

    # Source (optional with defaults)
    trigger: ADRTrigger = ADRTrigger.MANUAL
    source_task_id: Optional[str] = None
    source_feature_id: Optional[str] = None
    source_command: Optional[str] = None

    # Decision content (with defaults)
    context: str = ""
    decision: str = ""
    rationale: str = ""
    alternatives_considered: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)

    # Relationships (optional)
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None
    related_adrs: List[str] = field(default_factory=list)

    # Temporal (with defaults)
    created_at: datetime = field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None

    # Metadata (with defaults)
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0
