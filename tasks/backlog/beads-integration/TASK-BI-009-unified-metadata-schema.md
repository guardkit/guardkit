---
id: TASK-BI-009
title: Create unified metadata schema for task backends
status: backlog
priority: medium
type: task
parent_id: beads-integration
blocking_ids: []
labels: [beads, dry, refactoring]
created_at: 2025-12-13
complexity: 4
methodology_mode: standard
---

# TASK-BI-009: Create Unified Metadata Schema

## Problem Statement

GuardKit currently has metadata definitions (status, priority, methodology mode) scattered across multiple files. With the introduction of the TaskBackend abstraction and Beads integration, this creates DRY violations and potential drift between backends.

**Current state:**
- Status enums defined in task parsing logic
- Priority mapping hardcoded in multiple places
- Methodology modes defined in command specs
- Beads has its own status/priority semantics

**Risk:** Without a unified schema, metadata mapping between backends will be inconsistent and error-prone.

## Acceptance Criteria

1. Create `installer/core/lib/task_models.py` with:
   - `TaskStatus` enum with backend mapping comments
   - `Priority` enum aligned with Beads (0-4 scale)
   - `MethodologyMode` enum (standard, tdd, bdd)
   - `TaskType` enum (task, epic, feature, bug)
   - Dataclass for core task fields

2. Include bidirectional mapping helpers:
   - `to_beads_status(guardkit_status) -> str`
   - `from_beads_status(beads_status) -> TaskStatus`
   - Similar for priority

3. Update `TaskBackend` base class to use these types

4. Add unit tests for all mappings

## Technical Approach

```python
# installer/core/lib/task_models.py

from enum import Enum
from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime

class TaskStatus(Enum):
    """Task status with Beads mapping."""
    BACKLOG = "backlog"        # Beads: "open"
    IN_PROGRESS = "in_progress"  # Beads: "in_progress"
    BLOCKED = "blocked"        # Beads: "blocked"
    IN_REVIEW = "in_review"    # Beads: "open" + label "in_review"
    REVIEW_COMPLETE = "review_complete"  # Beads: "open" + label
    COMPLETED = "completed"    # Beads: "closed"

    def to_beads(self) -> str:
        """Convert to Beads status string."""
        mapping = {
            TaskStatus.BACKLOG: "open",
            TaskStatus.IN_PROGRESS: "in_progress",
            TaskStatus.BLOCKED: "blocked",
            TaskStatus.IN_REVIEW: "open",
            TaskStatus.REVIEW_COMPLETE: "open",
            TaskStatus.COMPLETED: "closed",
        }
        return mapping[self]

    @classmethod
    def from_beads(cls, status: str, labels: List[str] = None) -> "TaskStatus":
        """Convert from Beads status string."""
        labels = labels or []
        if status == "closed":
            return cls.COMPLETED
        if status == "blocked":
            return cls.BLOCKED
        if status == "in_progress":
            return cls.IN_PROGRESS
        # Open status - check labels for specificity
        if "in_review" in labels:
            return cls.IN_REVIEW
        if "review_complete" in labels:
            return cls.REVIEW_COMPLETE
        return cls.BACKLOG


class Priority(Enum):
    """Priority aligned with Beads 0-4 scale."""
    CRITICAL = 0  # Beads: 0
    HIGH = 1      # Beads: 1
    MEDIUM = 2    # Beads: 2
    LOW = 3       # Beads: 3
    BACKLOG = 4   # Beads: 4

    def to_beads(self) -> int:
        return self.value

    @classmethod
    def from_beads(cls, priority: int) -> "Priority":
        return cls(min(priority, 4))


class MethodologyMode(Enum):
    """Development methodology mode."""
    STANDARD = "standard"
    TDD = "tdd"
    BDD = "bdd"


class TaskType(Enum):
    """Task type classification."""
    TASK = "task"
    EPIC = "epic"
    FEATURE = "feature"
    BUG = "bug"
    REVIEW = "review"


@dataclass
class TaskMetadata:
    """Core task metadata shared across backends."""
    id: str
    title: str
    status: TaskStatus
    priority: Priority
    task_type: TaskType = TaskType.TASK
    methodology_mode: MethodologyMode = MethodologyMode.STANDARD
    description: Optional[str] = None
    parent_id: Optional[str] = None
    blocking_ids: List[str] = None
    discovered_from: Optional[str] = None
    labels: List[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None

    # RequireKit integration
    requirements: List[str] = None
    bdd_scenarios: List[str] = None
    ears_spec: Optional[str] = None

    # Quality gate results
    complexity_score: Optional[int] = None
    quality_gate_results: Optional[dict] = None

    def __post_init__(self):
        self.blocking_ids = self.blocking_ids or []
        self.labels = self.labels or []
        self.requirements = self.requirements or []
        self.bdd_scenarios = self.bdd_scenarios or []
```

## Dependencies

- **Depends on:** TASK-BI-001 (TaskBackend interface)
- **Blocks:** None (but improves BI-002, BI-003 implementations)

## Effort Estimate

- **Complexity:** 4/10
- **Effort:** 2-3 hours
- **Wave:** Can be done in parallel with Wave 1

## Testing

```python
# tests/lib/test_task_models.py

def test_status_to_beads():
    assert TaskStatus.BACKLOG.to_beads() == "open"
    assert TaskStatus.COMPLETED.to_beads() == "closed"

def test_status_from_beads_with_labels():
    assert TaskStatus.from_beads("open", ["in_review"]) == TaskStatus.IN_REVIEW
    assert TaskStatus.from_beads("open", []) == TaskStatus.BACKLOG

def test_priority_roundtrip():
    for p in Priority:
        assert Priority.from_beads(p.to_beads()) == p
```

## References

- Review finding: G1 (DRY violation in metadata definitions)
- [TASK-REV-b8c3 Review Report](../../../.claude/reviews/TASK-REV-b8c3-review-report.md)
