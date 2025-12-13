---
id: TASK-BI-002
title: Implement MarkdownBackend (extract from task_utils.py)
status: backlog
priority: 1
created_at: 2025-12-13T00:00:00Z
parent_id: TASK-REV-BEADS
implementation_mode: task-work
wave: 1
conductor_workspace: wave1-2
complexity: 6
estimated_hours: 3-4
tags:
  - backend
  - markdown
  - refactor
  - phase-1
blocking_ids:
  - TASK-BI-001
---

# Implement MarkdownBackend

## Objective

Extract current task file operations from `task_utils.py` into a `MarkdownBackend` class implementing the `TaskBackend` interface. This becomes the default backend for standalone GuardKit.

## Context

Current task management uses direct file operations in `task_utils.py`. This task refactors those operations into a proper backend class while maintaining backward compatibility.

## Implementation Details

### Location

Create: `installer/core/backends/markdown.py`

### Key Methods to Implement

```python
from pathlib import Path
from typing import List, Optional
from .base import TaskBackend, Task, TaskStatus, ReadyWorkOptions, DependencyType

class MarkdownBackend(TaskBackend):
    """
    Default backend using local markdown files.
    Works standalone without any external dependencies.
    """

    TASKS_DIR = "tasks"
    STATE_DIRS = ["backlog", "in_progress", "in_review", "blocked",
                  "completed", "review_complete", "design_approved"]

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.tasks_dir = self.project_root / self.TASKS_DIR

    @property
    def backend_name(self) -> str:
        return "markdown"

    @property
    def supports_dependencies(self) -> bool:
        return True  # Basic support via frontmatter

    @property
    def supports_distributed(self) -> bool:
        return False  # Single machine only

    @property
    def supports_web_ui(self) -> bool:
        return False

    @property
    def supports_mcp(self) -> bool:
        return False

    def initialize(self) -> bool:
        """Create tasks directory structure if needed."""
        for state_dir in self.STATE_DIRS:
            (self.tasks_dir / state_dir).mkdir(parents=True, exist_ok=True)
        return True

    def is_available(self) -> bool:
        """Always available - no external dependencies."""
        return True

    def create(self, task: Task) -> Task:
        """Create task as markdown file with YAML frontmatter."""
        # Use existing id_generator if no ID provided
        # Write to backlog/ directory
        # Return task with ID populated
        pass

    def get(self, task_id: str) -> Optional[Task]:
        """Find and read task file across all state directories."""
        # Search all STATE_DIRS for task file
        # Parse frontmatter and body
        # Return Task dataclass
        pass

    def update(self, task: Task) -> Task:
        """Update task file, preserving body content."""
        # Find existing file
        # Update frontmatter fields
        # Preserve markdown body
        pass

    def close(self, task_id: str, reason: str) -> Task:
        """Move task to completed/ with close reason."""
        pass

    def list_ready(self, options: ReadyWorkOptions = None) -> List[Task]:
        """List tasks in backlog with no open blockers."""
        # Scan backlog/ directory
        # Filter out tasks with blocking_ids that aren't closed
        # Apply ReadyWorkOptions filters
        # Sort by priority
        pass

    def move_to_state(self, task_id: str, new_status: TaskStatus) -> Task:
        """Move task file to appropriate state directory."""
        # Map TaskStatus to directory name
        # Move file, update frontmatter status
        pass

    def add_dependency(self, task_id: str, depends_on_id: str,
                       dep_type: DependencyType = DependencyType.BLOCKS) -> bool:
        """Add dependency to task frontmatter."""
        # Only BLOCKS type supported in basic markdown
        # Update blocking_ids list
        pass

    def create_child(self, parent_id: str, task: Task) -> Task:
        """Create task with parent_id set."""
        task.parent_id = parent_id
        return self.create(task)

    def sync(self) -> bool:
        """No-op for local backend."""
        return True
```

### Extraction from task_utils.py

Migrate these functions to MarkdownBackend methods:

| Current Function | Backend Method |
|------------------|----------------|
| `parse_task_frontmatter()` | `_parse_frontmatter()` (private) |
| `write_task_frontmatter()` | `_write_task_file()` (private) |
| `update_task_frontmatter()` | `update()` |
| `read_task_file()` | `get()` |
| `create_task_frontmatter()` | `create()` |
| `move_task_to_blocked()` | `move_to_state()` |

### Backward Compatibility

Keep `task_utils.py` as a thin wrapper that delegates to MarkdownBackend:

```python
# task_utils.py (updated)
from ..backends import get_backend

def parse_task_frontmatter(content: str) -> dict:
    """Backward compatible wrapper."""
    return get_backend()._parse_frontmatter(content)
```

## Acceptance Criteria

- [ ] `MarkdownBackend` implements all `TaskBackend` methods
- [ ] Existing task files remain readable/writable
- [ ] Task ID generation uses existing `id_generator.py`
- [ ] State directory mapping matches current structure
- [ ] Backward compatibility wrappers in `task_utils.py`
- [ ] Unit tests for all CRUD operations
- [ ] Integration test: create → get → update → close → verify

## Testing

```python
# tests/backends/test_markdown.py
def test_create_and_get(temp_project):
    backend = MarkdownBackend(temp_project)
    backend.initialize()

    task = Task(id="", title="Test task", priority=1)
    created = backend.create(task)

    assert created.id.startswith("TASK-")
    assert (temp_project / "tasks/backlog" / f"{created.id}.md").exists()

    retrieved = backend.get(created.id)
    assert retrieved.title == "Test task"

def test_list_ready_respects_blockers(temp_project):
    backend = MarkdownBackend(temp_project)
    backend.initialize()

    blocker = backend.create(Task(id="", title="Blocker"))
    blocked = backend.create(Task(id="", title="Blocked"))
    backend.add_dependency(blocked.id, blocker.id)

    ready = backend.list_ready()
    assert blocker.id in [t.id for t in ready]
    assert blocked.id not in [t.id for t in ready]
```

## Dependencies

- TASK-BI-001 (TaskBackend interface)

## Notes

- Preserve existing frontmatter field names for compatibility
- Handle nested directories (feature folders) in task lookup
- Consider caching task list for performance
