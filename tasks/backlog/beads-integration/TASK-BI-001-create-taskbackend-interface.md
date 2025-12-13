---
id: TASK-BI-001
title: Create TaskBackend abstract interface
status: backlog
priority: 1
created_at: 2025-12-13T00:00:00Z
parent_id: TASK-REV-BEADS
implementation_mode: task-work
wave: 1
conductor_workspace: wave1-1
complexity: 5
estimated_hours: 2-3
tags:
  - architecture
  - abstraction
  - phase-1
---

# Create TaskBackend Abstract Interface

## Objective

Define the abstract base class `TaskBackend` that provides a unified interface for task persistence backends. This interface must support current GuardKit task operations while being extensible for Beads and future Backlog.md integration.

## Context

This is the foundation for the pluggable backend architecture. The interface design is already documented in `docs/proposals/integrations/unified-integration-architecture.md`.

## Implementation Details

### Location

Create: `installer/core/backends/base.py`

### Interface Definition

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum

class TaskStatus(Enum):
    BACKLOG = "backlog"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    REVIEW_COMPLETE = "review_complete"
    DESIGN_APPROVED = "design_approved"

class TaskType(Enum):
    TASK = "task"
    REVIEW = "review"
    EPIC = "epic"
    BUG = "bug"
    FEATURE = "feature"

class DependencyType(Enum):
    BLOCKS = "blocks"
    RELATED = "related"
    PARENT_CHILD = "parent-child"
    DISCOVERED_FROM = "discovered-from"

@dataclass
class Task:
    """Unified task representation across all backends."""
    id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.BACKLOG
    task_type: TaskType = TaskType.TASK
    priority: int = 2  # 1=highest, 4=lowest
    labels: List[str] = field(default_factory=list)
    parent_id: Optional[str] = None
    blocking_ids: List[str] = field(default_factory=list)
    discovered_from_id: Optional[str] = None

    # GuardKit-specific metadata
    quality_gate_results: Optional[Dict[str, Any]] = None
    acceptance_criteria: Optional[List[str]] = None
    implementation_notes: Optional[str] = None
    spec_ref: Optional[str] = None

    # External PM tool IDs
    external_ids: Optional[Dict[str, str]] = None

    # Timestamps
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    closed_at: Optional[str] = None
    close_reason: Optional[str] = None

@dataclass
class ReadyWorkOptions:
    """Options for querying ready work."""
    limit: int = 10
    priority_max: Optional[int] = None
    labels: Optional[List[str]] = None
    task_type: Optional[TaskType] = None

class TaskBackend(ABC):
    """Abstract interface for task persistence backends."""

    @abstractmethod
    def initialize(self) -> bool:
        """Initialize the backend. Returns True if successful."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if this backend is available and configured."""
        pass

    @abstractmethod
    def create(self, task: Task) -> Task:
        """Create a new task. Returns task with ID populated."""
        pass

    @abstractmethod
    def get(self, task_id: str) -> Optional[Task]:
        """Retrieve a task by ID."""
        pass

    @abstractmethod
    def update(self, task: Task) -> Task:
        """Update an existing task."""
        pass

    @abstractmethod
    def close(self, task_id: str, reason: str) -> Task:
        """Close/complete a task with a reason."""
        pass

    @abstractmethod
    def list_ready(self, options: ReadyWorkOptions = None) -> List[Task]:
        """List tasks ready to work on (no blockers)."""
        pass

    @abstractmethod
    def add_dependency(self, task_id: str, depends_on_id: str,
                       dep_type: DependencyType = DependencyType.BLOCKS) -> bool:
        """Add a dependency between tasks."""
        pass

    @abstractmethod
    def create_child(self, parent_id: str, task: Task) -> Task:
        """Create a child task under a parent."""
        pass

    @abstractmethod
    def sync(self) -> bool:
        """Sync state (git-based backends). No-op for local backends."""
        pass

    @abstractmethod
    def move_to_state(self, task_id: str, new_status: TaskStatus) -> Task:
        """Move task to a new state directory."""
        pass

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Human-readable backend name."""
        pass

    @property
    @abstractmethod
    def supports_dependencies(self) -> bool:
        """Whether this backend supports full dependency tracking."""
        pass

    @property
    @abstractmethod
    def supports_distributed(self) -> bool:
        """Whether this backend supports multi-machine sync."""
        pass

    @property
    @abstractmethod
    def supports_web_ui(self) -> bool:
        """Whether this backend has a web UI."""
        pass

    @property
    @abstractmethod
    def supports_mcp(self) -> bool:
        """Whether this backend has MCP integration."""
        pass
```

## Acceptance Criteria

- [ ] `TaskBackend` ABC defined with all required methods
- [ ] `Task` dataclass covers all current frontmatter fields
- [ ] `TaskStatus` enum matches current state directories
- [ ] `DependencyType` enum supports Beads' 4 dependency types
- [ ] `ReadyWorkOptions` enables filtering for `bd ready` equivalent
- [ ] Type hints complete for IDE support
- [ ] Unit tests for dataclass serialization

## Testing

```python
# tests/backends/test_base.py
def test_task_dataclass_serialization():
    task = Task(id="TASK-A1B2", title="Test task")
    assert task.status == TaskStatus.BACKLOG
    assert task.priority == 2

def test_task_with_all_fields():
    task = Task(
        id="TASK-A1B2",
        title="Full task",
        status=TaskStatus.IN_PROGRESS,
        labels=["guardkit", "integration"],
        blocking_ids=["TASK-0001"]
    )
    assert len(task.blocking_ids) == 1
```

## Dependencies

- None (foundational task)

## Notes

- Keep dataclass fields compatible with existing frontmatter
- Status enum values must match directory names in `tasks/`
- Consider `__post_init__` for default list initialization
