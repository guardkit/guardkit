---
id: TASK-BI-004
title: Create backend registry with auto-detection
status: backlog
priority: 1
created_at: 2025-12-13T00:00:00Z
parent_id: TASK-REV-BEADS
implementation_mode: task-work
wave: 2
conductor_workspace: wave2-2
complexity: 4
estimated_hours: 2-3
tags:
  - backend
  - registry
  - detection
  - phase-1
blocking_ids:
  - TASK-BI-001
  - TASK-BI-002
---

# Create Backend Registry with Auto-Detection

## Objective

Create a `BackendRegistry` class that automatically detects available backends and provides the appropriate one based on project configuration and environment.

## Context

The registry enables GuardKit to automatically use Beads when available while falling back to Markdown for standalone operation.

## Implementation Details

### Location

Create: `installer/core/backends/__init__.py`

### Registry Implementation

```python
from pathlib import Path
from typing import Optional, Dict, Type
from .base import TaskBackend
from .markdown import MarkdownBackend
from .beads import BeadsBackend

class BackendRegistry:
    """
    Registry for task backends with auto-detection.
    Prefers Beads when available, falls back to Markdown.
    """

    _backends: Dict[str, Type[TaskBackend]] = {
        "markdown": MarkdownBackend,
        "beads": BeadsBackend
    }

    @classmethod
    def register(cls, name: str, backend_class: Type[TaskBackend]):
        """Register a new backend type."""
        cls._backends[name] = backend_class

    @classmethod
    def get_backend(cls,
                    preferred: Optional[str] = None,
                    project_root: Path = None) -> TaskBackend:
        """
        Get appropriate backend with auto-detection.

        Priority:
        1. Explicitly preferred backend (if specified and available)
        2. Beads (if bd installed and .beads exists)
        3. Markdown (always available fallback)

        Args:
            preferred: Backend name to prefer ("beads", "markdown")
            project_root: Project root directory

        Returns:
            Initialized TaskBackend instance
        """
        project_root = project_root or Path.cwd()

        # If explicitly preferred
        if preferred and preferred in cls._backends:
            backend = cls._backends[preferred](project_root)
            if backend.is_available():
                return backend

        # Auto-detect: prefer Beads if available
        beads = BeadsBackend(project_root)
        if beads.is_available():
            beads_dir = project_root / ".beads"
            if beads_dir.exists():
                # Beads already initialized
                return beads
            # Check if we should initialize Beads
            if cls._should_init_beads(project_root):
                if beads.initialize():
                    return beads

        # Fallback to Markdown
        markdown = MarkdownBackend(project_root)
        markdown.initialize()
        return markdown

    @classmethod
    def _should_init_beads(cls, project_root: Path) -> bool:
        """
        Determine if we should auto-initialize Beads.

        Conditions:
        - bd CLI is available
        - Project is a git repository
        - No existing markdown tasks (fresh project or explicit switch)
        """
        # Check for git repo
        git_dir = project_root / ".git"
        if not git_dir.exists():
            return False

        # Check for existing tasks in tasks/ directory
        tasks_dir = project_root / "tasks"
        if tasks_dir.exists():
            # Has existing tasks - don't auto-switch
            # User must explicitly configure beads
            return False

        return True

    @classmethod
    def detect_current(cls, project_root: Path = None) -> str:
        """Detect which backend is currently in use."""
        project_root = project_root or Path.cwd()

        beads_dir = project_root / ".beads"
        tasks_dir = project_root / "tasks"

        if beads_dir.exists():
            return "beads"
        if tasks_dir.exists():
            return "markdown"
        return "none"

    @classmethod
    def list_available(cls, project_root: Path = None) -> Dict[str, bool]:
        """List all backends and their availability."""
        project_root = project_root or Path.cwd()
        return {
            name: cls._backends[name](project_root).is_available()
            for name in cls._backends
        }


# Convenience function for common usage
def get_backend(preferred: str = None, project_root: Path = None) -> TaskBackend:
    """Get the current task backend."""
    return BackendRegistry.get_backend(preferred, project_root)
```

### Package Exports

```python
# installer/core/backends/__init__.py

from .base import (
    TaskBackend,
    Task,
    TaskStatus,
    TaskType,
    DependencyType,
    ReadyWorkOptions
)
from .markdown import MarkdownBackend
from .beads import BeadsBackend
from .registry import BackendRegistry, get_backend

__all__ = [
    # Base classes
    "TaskBackend",
    "Task",
    "TaskStatus",
    "TaskType",
    "DependencyType",
    "ReadyWorkOptions",
    # Backends
    "MarkdownBackend",
    "BeadsBackend",
    # Registry
    "BackendRegistry",
    "get_backend"
]
```

## Acceptance Criteria

- [ ] `BackendRegistry` supports multiple backend types
- [ ] Auto-detection logic prefers Beads when available
- [ ] Falls back to Markdown if Beads unavailable
- [ ] `detect_current()` accurately identifies active backend
- [ ] `list_available()` shows all backends and status
- [ ] Convenience `get_backend()` function exported
- [ ] Unit tests for detection logic

## Testing

```python
# tests/backends/test_registry.py
def test_falls_back_to_markdown(temp_project):
    # No bd installed simulation (mock)
    backend = get_backend(preferred="markdown", project_root=temp_project)
    assert backend.backend_name == "markdown"

def test_detects_beads_when_available(temp_git_project):
    # Initialize beads
    (temp_git_project / ".beads").mkdir()

    detected = BackendRegistry.detect_current(temp_git_project)
    assert detected == "beads"

def test_list_available_backends(temp_project):
    available = BackendRegistry.list_available(temp_project)
    assert "markdown" in available
    assert available["markdown"] == True  # Always available
```

## Dependencies

- TASK-BI-001 (TaskBackend interface)
- TASK-BI-002 (MarkdownBackend)

## Notes

- BeadsBackend import should be conditional/lazy to avoid errors if beads module has issues
- Consider reading preference from config file (future task)
- Registry pattern allows easy extension for Backlog.md later
