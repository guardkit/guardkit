---
id: TASK-GI-004
title: ADR Lifecycle Management
status: in_review
priority: 2
task_type: feature
created_at: 2026-01-24 00:00:00+00:00
parent_review: TASK-REV-GI01
feature_id: FEAT-GI
implementation_mode: task-work
wave: 4
conductor_workspace: wave4-1
complexity: 6
estimated_minutes: 240
dependencies:
- TASK-GI-001
tags:
- graphiti
- adr
- decision-capture
- high-priority
autobuild_state:
  current_turn: 4
  max_turns: 15
  worktree_path: /Users/richardwoollcott/Projects/appmilla_github/guardkit/.guardkit/worktrees/FEAT-GI
  base_branch: main
  started_at: '2026-01-28T22:41:00.856940'
  last_updated: '2026-01-28T23:15:42.774058'
  turns:
  - turn: 1
    decision: feedback
    feedback: '- task-work execution exceeded 900s timeout'
    timestamp: '2026-01-28T22:41:00.856940'
    player_summary: '[RECOVERED via git_only] Original error: SDK timeout after 900s:
      task-work execution exceeded 900s timeout'
    player_success: true
    coach_success: true
  - turn: 2
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-01-28T22:56:03.938832'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 3
    decision: feedback
    feedback: '- Tests did not pass during task-work execution'
    timestamp: '2026-01-28T23:03:11.791860'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
  - turn: 4
    decision: approve
    feedback: null
    timestamp: '2026-01-28T23:12:57.524695'
    player_summary: Implementation via task-work delegation
    player_success: true
    coach_success: true
---

# TASK-GI-004: ADR Lifecycle Management

## Overview

**Priority**: High
**Dependencies**: TASK-GI-001 (Core Infrastructure)
**Related ADR**: ADR-001-graphiti-integration-scope.md

## Problem Statement

Capture explicit Architecture Decision Records (ADRs) from decisions made during GuardKit workflows. When a decision is made during `/feature-plan` (clarifying questions), `/task-review` (acceptance), or `/task-work` (implementation choices), that decision should be recorded as an ADR in Graphiti so future sessions can query "why did we decide X?"

This feature handles **explicit ADRs** - decisions made consciously during workflows. Discovered ADRs (from code analysis) are handled by TASK-GI-007.

## Goals

1. **Capture Decisions**: Record significant decisions as ADRs automatically
2. **Rich Context**: Include rationale, alternatives considered, consequences
3. **Traceability**: Link ADRs to tasks/features that triggered them
4. **Queryable**: ADRs searchable via Graphiti semantic search
5. **Lifecycle**: Support ADR statuses (proposed, accepted, deprecated, superseded)

## User Stories

### US1: Decision Capture from Clarifying Questions
> As a developer using `/feature-plan`, when I answer a clarifying question that involves a scope or approach decision, that decision should be recorded as an ADR.

**Acceptance Criteria**:
- Clarifying question + answer is analyzed for decision significance
- Significant decisions create ADR with context from the question
- ADR links to the feature being planned
- Low-significance answers don't create ADRs (noise reduction)

### US2: Decision Capture from Task Review
> As a reviewer accepting or rejecting a task implementation, when I specify implementation approach preferences, those should become ADRs.

**Acceptance Criteria**:
- Task review acceptance with approach specification creates ADR
- Task review rejection with alternative suggestion creates ADR
- ADR includes the task context and review decision
- Rationale captured from review comments

### US3: Decision Capture from Implementation
> As a Claude Code session implementing a task, when I make a significant implementation choice (e.g., which library to use, which pattern to apply), that choice should be recorded.

**Acceptance Criteria**:
- Implementation decisions during Phase 3/4 can be flagged for ADR
- Agent can call `record_decision()` to create ADR
- Decision includes implementation context
- Links to task being implemented

## Technical Requirements

### ADR Entity Model

```python
# guardkit/knowledge/adr.py

from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ADRStatus(Enum):
    PROPOSED = "proposed"      # Decision under consideration
    ACCEPTED = "accepted"      # Decision made and active
    DEPRECATED = "deprecated"  # Decision no longer recommended
    SUPERSEDED = "superseded"  # Replaced by another ADR

class ADRTrigger(Enum):
    CLARIFYING_QUESTION = "clarifying_question"  # From /feature-plan
    TASK_REVIEW = "task_review"                  # From /task-review acceptance
    IMPLEMENTATION_CHOICE = "implementation"      # From /task-work
    MANUAL = "manual"                            # Explicitly created
    DISCOVERED = "discovered"                    # From code analysis (TASK-GI-007)

@dataclass
class ADREntity:
    """Architecture Decision Record stored in Graphiti."""

    # Identity
    id: str                              # ADR-XXXX
    title: str                           # Brief decision title
    status: ADRStatus = ADRStatus.ACCEPTED

    # Source
    trigger: ADRTrigger = ADRTrigger.MANUAL
    source_task_id: Optional[str] = None
    source_feature_id: Optional[str] = None
    source_command: Optional[str] = None  # e.g., "feature-plan", "task-review"

    # Decision content
    context: str = ""                    # What situation prompted this decision
    decision: str = ""                   # What we decided
    rationale: str = ""                  # Why we decided this
    alternatives_considered: List[str] = field(default_factory=list)
    consequences: List[str] = field(default_factory=list)

    # Relationships
    supersedes: Optional[str] = None     # ADR ID this replaces
    superseded_by: Optional[str] = None  # ADR ID that replaced this
    related_adrs: List[str] = field(default_factory=list)

    # Temporal
    created_at: datetime = field(default_factory=datetime.now)
    decided_at: Optional[datetime] = None
    deprecated_at: Optional[datetime] = None

    # Metadata
    tags: List[str] = field(default_factory=list)
    confidence: float = 1.0              # How confident in this decision (0-1)
```

### ADR Service

```python
# guardkit/knowledge/adr_service.py

class ADRService:
    """Service for creating and managing ADRs."""

    def __init__(self, client: GraphitiClient):
        self.client = client

    async def create_adr(self, adr: ADREntity) -> str:
        """Create a new ADR in Graphiti."""

        # Generate ID if not provided
        if not adr.id:
            adr.id = await self._generate_adr_id()

        # Store as episode
        await self.client.add_episode(
            name=f"adr_{adr.id}",
            episode_body=json.dumps(asdict(adr), default=str),
            group_id="adrs",
            source_description=f"ADR from {adr.trigger.value}"
        )

        return adr.id

    async def search_adrs(
        self,
        query: str,
        status: Optional[ADRStatus] = None,
        num_results: int = 10
    ) -> List[ADREntity]:
        """Search for ADRs by topic."""

        results = await self.client.search(
            query=query,
            group_ids=["adrs"],
            num_results=num_results
        )

        adrs = [self._parse_adr(r) for r in results]

        if status:
            adrs = [a for a in adrs if a.status == status]

        return adrs

    async def supersede_adr(
        self,
        old_adr_id: str,
        new_adr: ADREntity
    ) -> str:
        """Create new ADR that supersedes an existing one."""

        # Update old ADR
        old_adr = await self.get_adr(old_adr_id)
        old_adr.status = ADRStatus.SUPERSEDED
        old_adr.superseded_by = new_adr.id
        await self._update_adr(old_adr)

        # Create new ADR with reference
        new_adr.supersedes = old_adr_id
        return await self.create_adr(new_adr)
```

## Acceptance Criteria

- [ ] ADREntity model implementation
- [ ] ADRService with create, search, supersede, deprecate
- [ ] Decision significance detector
- [ ] Integration with clarifying questions handler
- [ ] Integration with task review
- [ ] Agent-callable `record_decision()` function
- [ ] ADR ID generation (ADR-XXXX format)
- [ ] Task/feature relationship edges in Graphiti
- [ ] Unit tests with >80% coverage
- [ ] Integration tests with Graphiti
- [ ] Documentation updated

## Testing Strategy

1. **Unit tests**: ADR entity creation and serialization
2. **Integration tests**: ADR creation and retrieval in Graphiti
3. **E2E tests**: Decision capture during command execution

## Files to Create/Modify

### New Files
- `guardkit/knowledge/adr.py`
- `guardkit/knowledge/adr_service.py`
- `guardkit/knowledge/decision_detector.py`
- `tests/knowledge/test_adr_service.py`

### Modified Files
- `guardkit/commands/lib/clarification/handler.py` (add ADR capture)
- `guardkit/commands/task_review.py` (add ADR capture)

## Open Questions

1. **Significance threshold**: What confidence threshold for auto-creating ADRs?
   - Recommendation: 0.4 for auto-create, allow manual creation for anything

2. **Human confirmation**: Should significant decisions ask for confirmation before creating ADR?
   - Recommendation: No for MVP - create automatically, can be deprecated later

3. **ADR numbering**: Sequential (ADR-001) or hash-based?
   - Recommendation: Sequential within project for human readability

---

## Related Documents

- [TASK-GI-001: Core Infrastructure](./TASK-GI-001-core-infrastructure.md)
- [TASK-GI-007: ADR Discovery from Code](./TASK-GI-007-adr-discovery.md) - For discovered ADRs
- [Unified Data Architecture Decision](../../docs/research/knowledge-graph-mcp/unified-data-architecture-decision.md)
