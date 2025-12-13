---
id: TASK-BI-006
title: Update CLI commands to use backend abstraction
status: backlog
priority: 1
created_at: 2025-12-13T00:00:00Z
parent_id: TASK-REV-BEADS
implementation_mode: task-work
wave: 3
conductor_workspace: wave3-2
complexity: 5
estimated_hours: 3-4
tags:
  - cli
  - integration
  - phase-3
blocking_ids:
  - TASK-BI-004
  - TASK-BI-005
---

# Update CLI Commands to Use Backend Abstraction

## Objective

Update `/task-create`, `/task-work`, `/task-complete`, and `/task-status` commands to use the TaskBackend abstraction instead of direct file operations.

## Context

Currently, task commands use `task_utils.py` for direct file manipulation. This task updates them to use `get_backend()` for transparent Beads/Markdown switching.

## Implementation Details

### Files to Update

1. `installer/core/commands/lib/task_create_helper.py`
2. `installer/core/commands/lib/task_work_helper.py`
3. `installer/core/commands/lib/task_completion_helper.py`
4. `installer/core/commands/lib/task_status_helper.py`

### Pattern for Updates

**Before (direct file operations):**
```python
from .task_utils import create_task_frontmatter, write_task_frontmatter

def create_task(title: str, **kwargs):
    frontmatter = create_task_frontmatter(task_id, title, **kwargs)
    task_file = tasks_dir / "backlog" / f"{task_id}.md"
    task_file.write_text(format_task_markdown(frontmatter))
```

**After (backend abstraction):**
```python
from ...backends import get_backend, Task, TaskType

def create_task(title: str, **kwargs) -> Task:
    backend = get_backend()

    task = Task(
        id="",  # Backend assigns ID
        title=title,
        priority=kwargs.get("priority", 2),
        task_type=TaskType(kwargs.get("task_type", "task")),
        labels=kwargs.get("labels", []),
        description=kwargs.get("description"),
        acceptance_criteria=kwargs.get("acceptance_criteria")
    )

    return backend.create(task)
```

### Specific Updates

#### task_create_helper.py

```python
from ...backends import get_backend, Task, TaskType

def create_task(
    title: str,
    priority: int = 2,
    task_type: str = "task",
    prefix: str = None,
    description: str = None,
    labels: list = None,
    acceptance_criteria: list = None,
    parent_id: str = None
) -> Task:
    """Create a new task using configured backend."""
    backend = get_backend()

    task = Task(
        id="",
        title=title,
        priority=priority,
        task_type=TaskType(task_type),
        labels=labels or [],
        description=description,
        acceptance_criteria=acceptance_criteria,
        parent_id=parent_id
    )

    created = backend.create(task)

    # Sync if backend supports it
    if backend.supports_distributed:
        backend.sync()

    return created
```

#### task_work_helper.py

```python
from ...backends import get_backend, TaskStatus, ReadyWorkOptions

def get_next_task(task_id: str = None) -> Optional[Task]:
    """Get task to work on - specified or from ready queue."""
    backend = get_backend()

    if task_id:
        return backend.get(task_id)

    # Use backend's ready queue
    ready = backend.list_ready(ReadyWorkOptions(limit=1))
    return ready[0] if ready else None

def start_task(task_id: str) -> Task:
    """Mark task as in progress."""
    backend = get_backend()
    task = backend.get(task_id)

    if not task:
        raise ValueError(f"Task {task_id} not found")

    task.status = TaskStatus.IN_PROGRESS
    return backend.update(task)
```

#### task_completion_helper.py

```python
from ...backends import get_backend, TaskStatus

def complete_task(task_id: str, reason: str = "Completed") -> Task:
    """Complete a task with quality gate verification."""
    backend = get_backend()

    task = backend.get(task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found")

    # Close the task
    completed = backend.close(task_id, reason)

    # Sync if distributed
    if backend.supports_distributed:
        backend.sync()

    return completed

def block_task(task_id: str, reason: str) -> Task:
    """Move task to blocked state."""
    backend = get_backend()
    return backend.move_to_state(task_id, TaskStatus.BLOCKED)
```

#### task_status_helper.py

```python
from ...backends import get_backend, BackendRegistry

def get_status_summary() -> dict:
    """Get task status summary."""
    backend = get_backend()

    # Get ready tasks
    ready = backend.list_ready()

    return {
        "backend": backend.backend_name,
        "distributed": backend.supports_distributed,
        "ready_count": len(ready),
        "ready_tasks": [{"id": t.id, "title": t.title, "priority": t.priority}
                       for t in ready[:5]]
    }

def show_backend_status() -> dict:
    """Show current backend configuration."""
    return {
        "current": BackendRegistry.detect_current(),
        "available": BackendRegistry.list_available()
    }
```

### Add Backend Status to /task-status Output

```
🛡️ GuardKit Status

Backend: beads
  Distributed: ✅
  Dependencies: ✅ (full graph)
  Ready Tasks: 3

📋 Ready to work on:
  P1 TASK-A1B2: Implement TaskBackend interface
  P2 TASK-C3D4: Add configuration system
  P2 TASK-E5F6: Update CLI commands
```

## Acceptance Criteria

- [ ] `/task-create` uses `backend.create()`
- [ ] `/task-work` uses `backend.list_ready()` and `backend.update()`
- [ ] `/task-complete` uses `backend.close()`
- [ ] `/task-status` shows backend info
- [ ] Auto-sync on completion for distributed backends
- [ ] Backward compatible with existing task files
- [ ] Integration tests for each command

## Testing

```python
# tests/commands/test_task_create_integration.py
def test_create_with_markdown_backend(temp_project):
    task = create_task("Test task", priority=1)
    assert task.id.startswith("TASK-")
    assert (temp_project / "tasks/backlog" / f"{task.id}.md").exists()

@pytest.mark.skipif(not BeadsBackend().is_available(), reason="bd not installed")
def test_create_with_beads_backend(temp_git_project):
    set_backend("beads", temp_git_project)
    task = create_task("Beads task", priority=1)
    assert task.id.startswith("bd-")
```

## Dependencies

- TASK-BI-004 (Backend registry)
- TASK-BI-005 (Configuration system)

## Notes

- Preserve backward compatibility for existing task files
- Consider deprecation warnings for direct task_utils usage
- ID generation delegated to backend
