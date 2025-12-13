---
id: TASK-BI-003
title: Implement BeadsBackend with CLI integration
status: backlog
priority: 1
created_at: 2025-12-13T00:00:00Z
parent_id: TASK-REV-BEADS
implementation_mode: task-work
wave: 2
conductor_workspace: wave2-1
complexity: 6
estimated_hours: 4-5
tags:
  - backend
  - beads
  - cli
  - phase-2
blocking_ids:
  - TASK-BI-001
---

# Implement BeadsBackend

## Objective

Create `BeadsBackend` class that integrates with the Beads CLI (`bd`) to provide persistent cross-session memory, full dependency graphs, and distributed sync capabilities.

## Context

Beads (v0.20.1) is a git-based issue tracker designed for AI coding agents. It uses hash-based IDs matching GuardKit's format, making integration natural.

## Implementation Details

### Location

Create: `installer/core/backends/beads.py`

### Beads CLI Integration

```python
import subprocess
import shutil
import json
from pathlib import Path
from typing import List, Optional
from .base import TaskBackend, Task, TaskStatus, TaskType, DependencyType, ReadyWorkOptions

class BeadsBackend(TaskBackend):
    """
    Optional backend using Beads (bd) for persistent memory.
    Provides distributed sync, full dependency graphs, and cross-session memory.
    """

    BEADS_DIR = ".beads"
    GUARDKIT_LABEL = "guardkit"

    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self._bd_path = None

    @property
    def backend_name(self) -> str:
        return "beads"

    @property
    def supports_dependencies(self) -> bool:
        return True  # Full 4-type dependency support

    @property
    def supports_distributed(self) -> bool:
        return True  # Git-synced across machines

    @property
    def supports_web_ui(self) -> bool:
        return False  # Example monitor only

    @property
    def supports_mcp(self) -> bool:
        return True  # beads-mcp available

    def _find_bd(self) -> Optional[str]:
        """Find bd executable."""
        if self._bd_path:
            return self._bd_path
        self._bd_path = shutil.which("bd")
        return self._bd_path

    def _run_bd(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run bd command with JSON output."""
        cmd = [self._find_bd()] + args
        if "--json" not in args and args[0] not in ["init", "sync"]:
            cmd.append("--json")
        return subprocess.run(
            cmd,
            cwd=self.project_root,
            capture_output=True,
            text=True
        )

    def is_available(self) -> bool:
        """Check if bd CLI is installed."""
        return self._find_bd() is not None

    def initialize(self) -> bool:
        """Initialize Beads if not already present."""
        if not self._find_bd():
            return False

        beads_dir = self.project_root / self.BEADS_DIR
        if not beads_dir.exists():
            result = self._run_bd(["init", "--quiet"])
            return result.returncode == 0
        return True

    def create(self, task: Task) -> Task:
        """Create task in Beads."""
        labels = [self.GUARDKIT_LABEL]
        if task.labels:
            labels.extend(task.labels)

        args = [
            "create", task.title,
            "-t", self._map_task_type(task.task_type),
            "-p", str(task.priority),
            "-l", ",".join(labels)
        ]

        if task.description:
            args.extend(["-d", task.description])

        result = self._run_bd(args)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to create task: {result.stderr}")

        bd_issue = json.loads(result.stdout)
        task.id = bd_issue["id"]
        task.created_at = bd_issue.get("created_at")

        # Store GuardKit metadata in notes
        self._update_notes(task)

        # Handle discovered-from dependency
        if task.discovered_from_id:
            self.add_dependency(task.id, task.discovered_from_id,
                              DependencyType.DISCOVERED_FROM)

        return task

    def get(self, task_id: str) -> Optional[Task]:
        """Retrieve task from Beads."""
        result = self._run_bd(["show", task_id])
        if result.returncode != 0:
            return None

        bd_issue = json.loads(result.stdout)
        return self._bd_to_task(bd_issue)

    def update(self, task: Task) -> Task:
        """Update task in Beads."""
        args = ["update", task.id]

        if task.status:
            args.extend(["--status", self._map_status_to_bd(task.status)])
        if task.priority is not None:
            args.extend(["--priority", str(task.priority)])

        result = self._run_bd(args)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to update task: {result.stderr}")

        self._update_notes(task)
        return task

    def close(self, task_id: str, reason: str) -> Task:
        """Close task in Beads."""
        result = self._run_bd(["close", task_id, "--reason", reason])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to close task: {result.stderr}")

        return self.get(task_id)

    def list_ready(self, options: ReadyWorkOptions = None) -> List[Task]:
        """List ready work from Beads using bd ready."""
        options = options or ReadyWorkOptions()

        args = ["ready", f"--limit={options.limit}"]
        args.extend(["--label", self.GUARDKIT_LABEL])

        if options.priority_max is not None:
            args.extend(["--priority-max", str(options.priority_max)])

        result = self._run_bd(args)
        if result.returncode != 0:
            return []

        bd_issues = json.loads(result.stdout)
        return [self._bd_to_task(issue) for issue in bd_issues]

    def add_dependency(self, task_id: str, depends_on_id: str,
                       dep_type: DependencyType = DependencyType.BLOCKS) -> bool:
        """Add dependency in Beads (supports all 4 types)."""
        type_map = {
            DependencyType.BLOCKS: "blocks",
            DependencyType.RELATED: "related",
            DependencyType.PARENT_CHILD: "parent-child",
            DependencyType.DISCOVERED_FROM: "discovered-from"
        }
        args = ["dep", "add", task_id, depends_on_id,
                "--type", type_map[dep_type]]
        result = self._run_bd(args)
        return result.returncode == 0

    def create_child(self, parent_id: str, task: Task) -> Task:
        """Create child task with hierarchical ID."""
        task.parent_id = parent_id
        created = self.create(task)
        self.add_dependency(created.id, parent_id, DependencyType.PARENT_CHILD)
        return created

    def sync(self) -> bool:
        """Sync Beads state with git."""
        result = self._run_bd(["sync"])
        return result.returncode == 0

    def move_to_state(self, task_id: str, new_status: TaskStatus) -> Task:
        """Update task status in Beads."""
        args = ["update", task_id, "--status", self._map_status_to_bd(new_status)]
        result = self._run_bd(args)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to move task: {result.stderr}")
        return self.get(task_id)

    # Private helper methods

    def _map_task_type(self, task_type: TaskType) -> str:
        return task_type.value

    def _map_status_to_bd(self, status: TaskStatus) -> str:
        mapping = {
            TaskStatus.BACKLOG: "open",
            TaskStatus.IN_PROGRESS: "in_progress",
            TaskStatus.IN_REVIEW: "in_progress",  # Beads doesn't have in_review
            TaskStatus.BLOCKED: "blocked",
            TaskStatus.COMPLETED: "closed",
            TaskStatus.REVIEW_COMPLETE: "closed",
            TaskStatus.DESIGN_APPROVED: "open"
        }
        return mapping.get(status, "open")

    def _map_status_from_bd(self, bd_status: str) -> TaskStatus:
        mapping = {
            "open": TaskStatus.BACKLOG,
            "in_progress": TaskStatus.IN_PROGRESS,
            "blocked": TaskStatus.BLOCKED,
            "closed": TaskStatus.COMPLETED
        }
        return mapping.get(bd_status, TaskStatus.BACKLOG)

    def _bd_to_task(self, bd_issue: dict) -> Task:
        """Convert Beads issue to GuardKit Task."""
        labels = bd_issue.get("labels", [])
        guardkit_labels = [l for l in labels if l != self.GUARDKIT_LABEL]

        # Parse notes for GuardKit metadata
        notes = bd_issue.get("notes", "")
        metadata = self._parse_notes(notes)

        return Task(
            id=bd_issue["id"],
            title=bd_issue["title"],
            description=bd_issue.get("description"),
            status=self._map_status_from_bd(bd_issue.get("status", "open")),
            task_type=TaskType(bd_issue.get("type", "task")),
            priority=bd_issue.get("priority", 2),
            labels=guardkit_labels,
            parent_id=bd_issue.get("parent_id"),
            blocking_ids=bd_issue.get("blocking_ids", []),
            quality_gate_results=metadata.get("quality_gate_results"),
            acceptance_criteria=metadata.get("acceptance_criteria"),
            spec_ref=metadata.get("spec_ref"),
            created_at=bd_issue.get("created_at"),
            updated_at=bd_issue.get("updated_at"),
            closed_at=bd_issue.get("closed_at"),
            close_reason=bd_issue.get("close_reason")
        )

    def _update_notes(self, task: Task):
        """Store GuardKit metadata in Beads notes field."""
        notes_parts = []

        if task.spec_ref:
            notes_parts.append(f"**Spec:** `{task.spec_ref}`")

        if task.acceptance_criteria:
            ac_list = "\n".join(f"- [ ] {ac}" for ac in task.acceptance_criteria)
            notes_parts.append(f"## Acceptance Criteria\n{ac_list}")

        if task.quality_gate_results:
            status = "Passed" if task.quality_gate_results.get("passed") else "Failed"
            notes_parts.append(f"**Quality Gates:** {status}")

        if task.implementation_notes:
            notes_parts.append(f"## Notes\n{task.implementation_notes}")

        if notes_parts:
            notes = "\n\n".join(notes_parts)
            self._run_bd(["update", task.id, "--notes", notes])

    def _parse_notes(self, notes: str) -> dict:
        """Parse GuardKit metadata from Beads notes."""
        metadata = {}

        if "**Spec:**" in notes:
            # Extract spec_ref
            pass

        # Additional parsing for acceptance_criteria, quality_gate_results

        return metadata
```

## Acceptance Criteria

- [ ] `BeadsBackend` implements all `TaskBackend` methods
- [ ] CLI wrapper handles all `bd` commands
- [ ] All 4 dependency types mapped correctly
- [ ] `bd ready` integration for list_ready()
- [ ] GuardKit metadata stored in notes field
- [ ] Graceful handling when `bd` not installed
- [ ] Unit tests (skipped if bd not available)

## Testing

```python
# tests/backends/test_beads.py
import pytest
from guardkit.backends.beads import BeadsBackend

@pytest.mark.skipif(not BeadsBackend().is_available(),
                    reason="bd not installed")
def test_create_and_get(temp_git_project):
    backend = BeadsBackend(temp_git_project)
    backend.initialize()

    task = Task(id="", title="Beads test task")
    created = backend.create(task)

    assert created.id.startswith("bd-")

    retrieved = backend.get(created.id)
    assert retrieved.title == "Beads test task"

@pytest.mark.skipif(not BeadsBackend().is_available(),
                    reason="bd not installed")
def test_dependency_types(temp_git_project):
    backend = BeadsBackend(temp_git_project)
    backend.initialize()

    parent = backend.create(Task(id="", title="Parent"))
    child = backend.create(Task(id="", title="Child"))

    assert backend.add_dependency(child.id, parent.id, DependencyType.DISCOVERED_FROM)
```

## Dependencies

- TASK-BI-001 (TaskBackend interface)
- Beads CLI (`bd`) installed for runtime functionality

## Notes

- CLI approach preferred over MCP (1-2k tokens vs 10-50k)
- ID format: `bd-a1b2` (hash-based, matches GuardKit style)
- Beads v0.20.1+ required for hash-based IDs
- Consider caching `bd ready` results
