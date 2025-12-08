# GuardKit: Optional Beads Integration Specification

**Version**: 1.0  
**Date**: December 2024  
**Status**: Implementation Ready

---

## Executive Summary

GuardKit should function as a standalone methodology framework while optionally integrating with Beads for enhanced memory, dependency tracking, and multi-agent coordination. When Beads is available, GuardKit gains persistent cross-session memory; when absent, GuardKit continues working with its native markdown-based state.

---

## Architecture: Backend Adapter Pattern

```
┌─────────────────────────────────────────────────────────────────┐
│                     GuardKit CLI Layer                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │task-create │  │ task-work  │  │task-complete│                │
│  └─────┬──────┘  └─────┬──────┘  └──────┬─────┘                │
│        │               │                │                       │
│        └───────────────┼────────────────┘                       │
│                        ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              GuardKit Core (Methodology)                  │  │
│  │  • EARS validation      • Agent orchestration            │  │
│  │  • BDD generation       • Quality gates                  │  │
│  │  • Template system      • Stack detection                │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│                           ▼                                     │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              TaskBackend (Abstract Interface)             │  │
│  │  create() | get() | update() | close() | list_ready()    │  │
│  └────────────────────────┬─────────────────────────────────┘  │
│                           │                                     │
│            ┌──────────────┴──────────────┐                     │
│            ▼                              ▼                     │
│  ┌──────────────────┐          ┌──────────────────┐            │
│  │  MarkdownBackend │          │   BeadsBackend   │            │
│  │  (Default)       │          │   (Optional)     │            │
│  │                  │          │                  │            │
│  │ .guardkit/tasks/ │          │ .beads/*.db      │            │
│  │ Local markdown   │          │ Git-synced       │            │
│  │ Single machine   │          │ Multi-machine    │            │
│  └──────────────────┘          └──────────────────┘            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Backend Interface Definition

```python
# guardkit/backends/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum

class TaskStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    CLOSED = "closed"

class TaskType(Enum):
    EPIC = "epic"
    TASK = "task"
    BUG = "bug"
    FEATURE = "feature"

class MethodologyMode(Enum):
    STANDARD = "standard"
    TDD = "tdd"
    BDD = "bdd"

@dataclass
class Task:
    """Unified task representation across backends."""
    id: str
    title: str
    description: Optional[str] = None
    status: TaskStatus = TaskStatus.OPEN
    task_type: TaskType = TaskType.TASK
    priority: int = 2  # 0=highest, 4=lowest
    methodology_mode: MethodologyMode = MethodologyMode.STANDARD
    labels: List[str] = None
    parent_id: Optional[str] = None
    blocking_ids: List[str] = None
    discovered_from_id: Optional[str] = None
    
    # GuardKit-specific metadata
    ears_spec: Optional[str] = None
    gherkin_scenarios: Optional[str] = None
    quality_gate_results: Optional[dict] = None
    
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
    methodology_mode: Optional[MethodologyMode] = None
    labels: Optional[List[str]] = None

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
        """Close a task with a reason."""
        pass
    
    @abstractmethod
    def list_ready(self, options: ReadyWorkOptions = None) -> List[Task]:
        """List tasks ready to work on (no blockers)."""
        pass
    
    @abstractmethod
    def add_dependency(self, task_id: str, depends_on_id: str, 
                       dep_type: str = "blocks") -> bool:
        """Add a dependency between tasks."""
        pass
    
    @abstractmethod
    def create_child(self, parent_id: str, task: Task) -> Task:
        """Create a child task under a parent."""
        pass
    
    @abstractmethod
    def sync(self) -> bool:
        """Sync state (relevant for distributed backends)."""
        pass
    
    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Human-readable backend name."""
        pass
    
    @property
    @abstractmethod
    def supports_dependencies(self) -> bool:
        """Whether this backend supports dependency tracking."""
        pass
    
    @property
    @abstractmethod
    def supports_distributed(self) -> bool:
        """Whether this backend supports multi-machine sync."""
        pass
```

---

## Markdown Backend (Default - Standalone Mode)

```python
# guardkit/backends/markdown.py
import os
import json
import yaml
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from .base import TaskBackend, Task, TaskStatus, ReadyWorkOptions

class MarkdownBackend(TaskBackend):
    """
    Default backend using local markdown files.
    Works standalone without any external dependencies.
    """
    
    TASKS_DIR = ".guardkit/tasks"
    STATE_FILE = ".guardkit/state.json"
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self.tasks_dir = self.project_root / self.TASKS_DIR
        self.state_file = self.project_root / self.STATE_FILE
        self._counter = 0
    
    def initialize(self) -> bool:
        """Create .guardkit directory structure."""
        self.tasks_dir.mkdir(parents=True, exist_ok=True)
        if not self.state_file.exists():
            self._save_state({"counter": 0, "tasks": {}})
        return True
    
    def is_available(self) -> bool:
        """Always available - no external dependencies."""
        return True
    
    @property
    def backend_name(self) -> str:
        return "markdown"
    
    @property
    def supports_dependencies(self) -> bool:
        return True  # Basic support via metadata
    
    @property
    def supports_distributed(self) -> bool:
        return False  # Single machine only
    
    def create(self, task: Task) -> Task:
        """Create task as markdown file with YAML frontmatter."""
        state = self._load_state()
        state["counter"] += 1
        task_id = f"GK-{state['counter']:04d}"
        task.id = task_id
        task.created_at = datetime.utcnow().isoformat()
        
        # Write markdown file
        self._write_task_file(task)
        
        # Update state index
        state["tasks"][task_id] = {
            "status": task.status.value,
            "priority": task.priority,
            "blocking_ids": task.blocking_ids or [],
            "parent_id": task.parent_id
        }
        self._save_state(state)
        
        return task
    
    def get(self, task_id: str) -> Optional[Task]:
        """Read task from markdown file."""
        task_file = self.tasks_dir / f"{task_id}.md"
        if not task_file.exists():
            return None
        return self._read_task_file(task_file)
    
    def update(self, task: Task) -> Task:
        """Update task markdown file."""
        task.updated_at = datetime.utcnow().isoformat()
        self._write_task_file(task)
        
        # Update state index
        state = self._load_state()
        if task.id in state["tasks"]:
            state["tasks"][task.id].update({
                "status": task.status.value,
                "priority": task.priority,
                "blocking_ids": task.blocking_ids or []
            })
            self._save_state(state)
        
        return task
    
    def close(self, task_id: str, reason: str) -> Task:
        """Close task with reason."""
        task = self.get(task_id)
        if not task:
            raise ValueError(f"Task {task_id} not found")
        
        task.status = TaskStatus.CLOSED
        task.close_reason = reason
        task.closed_at = datetime.utcnow().isoformat()
        return self.update(task)
    
    def list_ready(self, options: ReadyWorkOptions = None) -> List[Task]:
        """List tasks with no open blockers."""
        options = options or ReadyWorkOptions()
        state = self._load_state()
        
        ready_tasks = []
        for task_id, meta in state["tasks"].items():
            # Skip closed tasks
            if meta["status"] == "closed":
                continue
            
            # Check blockers
            blocking_ids = meta.get("blocking_ids", [])
            has_open_blocker = False
            for blocker_id in blocking_ids:
                blocker_meta = state["tasks"].get(blocker_id, {})
                if blocker_meta.get("status") != "closed":
                    has_open_blocker = True
                    break
            
            if not has_open_blocker:
                task = self.get(task_id)
                if task:
                    # Apply filters
                    if options.priority_max and task.priority > options.priority_max:
                        continue
                    if options.methodology_mode and task.methodology_mode != options.methodology_mode:
                        continue
                    ready_tasks.append(task)
        
        # Sort by priority, then created date
        ready_tasks.sort(key=lambda t: (t.priority, t.created_at or ""))
        return ready_tasks[:options.limit]
    
    def add_dependency(self, task_id: str, depends_on_id: str, 
                       dep_type: str = "blocks") -> bool:
        """Add dependency to task metadata."""
        task = self.get(task_id)
        if not task:
            return False
        
        if task.blocking_ids is None:
            task.blocking_ids = []
        
        if depends_on_id not in task.blocking_ids:
            task.blocking_ids.append(depends_on_id)
            self.update(task)
        
        return True
    
    def create_child(self, parent_id: str, task: Task) -> Task:
        """Create child task with parent reference."""
        task.parent_id = parent_id
        return self.create(task)
    
    def sync(self) -> bool:
        """No-op for local backend."""
        return True
    
    # Private helpers
    
    def _write_task_file(self, task: Task):
        """Write task to markdown file with YAML frontmatter."""
        task_file = self.tasks_dir / f"{task.id}.md"
        
        frontmatter = {
            "id": task.id,
            "title": task.title,
            "status": task.status.value,
            "type": task.task_type.value,
            "priority": task.priority,
            "methodology_mode": task.methodology_mode.value,
            "labels": task.labels or [],
            "parent_id": task.parent_id,
            "blocking_ids": task.blocking_ids or [],
            "discovered_from_id": task.discovered_from_id,
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "closed_at": task.closed_at,
            "close_reason": task.close_reason
        }
        
        content = f"""---
{yaml.dump(frontmatter, default_flow_style=False)}---

# {task.title}

{task.description or ""}

## EARS Specification

{task.ears_spec or "_Not yet defined_"}

## Gherkin Scenarios

{task.gherkin_scenarios or "_Not yet defined_"}

## Quality Gate Results

{json.dumps(task.quality_gate_results, indent=2) if task.quality_gate_results else "_Not yet run_"}
"""
        task_file.write_text(content)
    
    def _read_task_file(self, task_file: Path) -> Task:
        """Read task from markdown file."""
        content = task_file.read_text()
        
        # Parse YAML frontmatter
        if content.startswith("---"):
            _, frontmatter, body = content.split("---", 2)
            meta = yaml.safe_load(frontmatter)
        else:
            return None
        
        return Task(
            id=meta["id"],
            title=meta["title"],
            description=self._extract_section(body, "# " + meta["title"]),
            status=TaskStatus(meta.get("status", "open")),
            task_type=TaskType(meta.get("type", "task")),
            priority=meta.get("priority", 2),
            methodology_mode=MethodologyMode(meta.get("methodology_mode", "standard")),
            labels=meta.get("labels", []),
            parent_id=meta.get("parent_id"),
            blocking_ids=meta.get("blocking_ids", []),
            discovered_from_id=meta.get("discovered_from_id"),
            ears_spec=self._extract_section(body, "## EARS Specification"),
            gherkin_scenarios=self._extract_section(body, "## Gherkin Scenarios"),
            created_at=meta.get("created_at"),
            updated_at=meta.get("updated_at"),
            closed_at=meta.get("closed_at"),
            close_reason=meta.get("close_reason")
        )
    
    def _extract_section(self, body: str, header: str) -> Optional[str]:
        """Extract content under a markdown header."""
        lines = body.split("\n")
        in_section = False
        section_lines = []
        
        for line in lines:
            if line.startswith(header):
                in_section = True
                continue
            if in_section:
                if line.startswith("## ") or line.startswith("# "):
                    break
                section_lines.append(line)
        
        content = "\n".join(section_lines).strip()
        return content if content and content != "_Not yet defined_" else None
    
    def _load_state(self) -> dict:
        if self.state_file.exists():
            return json.loads(self.state_file.read_text())
        return {"counter": 0, "tasks": {}}
    
    def _save_state(self, state: dict):
        self.state_file.write_text(json.dumps(state, indent=2))
```

---

## Beads Backend (Optional - Enhanced Mode)

```python
# guardkit/backends/beads.py
import subprocess
import json
import shutil
from pathlib import Path
from typing import List, Optional
from .base import TaskBackend, Task, TaskStatus, TaskType, MethodologyMode, ReadyWorkOptions

class BeadsBackend(TaskBackend):
    """
    Optional backend using Beads (bd) for persistent memory.
    Provides distributed sync, dependency tracking, and cross-session memory.
    """
    
    BEADS_DIR = ".beads"
    GUARDKIT_LABEL = "guardkit"
    
    def __init__(self, project_root: Path = None):
        self.project_root = project_root or Path.cwd()
        self._bd_path = None
    
    def initialize(self) -> bool:
        """Initialize Beads if not already present."""
        if not self._find_bd():
            return False
        
        beads_dir = self.project_root / self.BEADS_DIR
        if not beads_dir.exists():
            result = self._run_bd(["init", "--quiet"])
            return result.returncode == 0
        return True
    
    def is_available(self) -> bool:
        """Check if bd CLI is installed and .beads exists or can be created."""
        return self._find_bd() is not None
    
    @property
    def backend_name(self) -> str:
        return "beads"
    
    @property
    def supports_dependencies(self) -> bool:
        return True  # Full dependency support
    
    @property
    def supports_distributed(self) -> bool:
        return True  # Git-synced across machines
    
    def create(self, task: Task) -> Task:
        """Create task in Beads."""
        labels = [self.GUARDKIT_LABEL]
        labels.append(f"mode:{task.methodology_mode.value}")
        if task.labels:
            labels.extend(task.labels)
        
        args = [
            "create", task.title,
            "-t", self._map_task_type(task.task_type),
            "-p", str(task.priority),
            "-l", ",".join(labels),
            "--json"
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
        if task.ears_spec or task.gherkin_scenarios:
            self._update_notes(task)
        
        # Handle discovered-from dependency
        if task.discovered_from_id:
            self.add_dependency(task.id, task.discovered_from_id, "discovered-from")
        
        return task
    
    def get(self, task_id: str) -> Optional[Task]:
        """Retrieve task from Beads."""
        result = self._run_bd(["show", task_id, "--json"])
        if result.returncode != 0:
            return None
        
        bd_issue = json.loads(result.stdout)
        return self._bd_to_task(bd_issue)
    
    def update(self, task: Task) -> Task:
        """Update task in Beads."""
        args = ["update", task.id, "--json"]
        
        if task.status:
            args.extend(["--status", self._map_status_to_bd(task.status)])
        if task.priority is not None:
            args.extend(["--priority", str(task.priority)])
        
        result = self._run_bd(args)
        if result.returncode != 0:
            raise RuntimeError(f"Failed to update task: {result.stderr}")
        
        # Update notes with GuardKit metadata
        self._update_notes(task)
        
        return task
    
    def close(self, task_id: str, reason: str) -> Task:
        """Close task in Beads."""
        result = self._run_bd(["close", task_id, "--reason", reason, "--json"])
        if result.returncode != 0:
            raise RuntimeError(f"Failed to close task: {result.stderr}")
        
        return self.get(task_id)
    
    def list_ready(self, options: ReadyWorkOptions = None) -> List[Task]:
        """List ready work from Beads."""
        options = options or ReadyWorkOptions()
        
        args = ["ready", "--json", f"--limit={options.limit}"]
        
        # Filter by guardkit label
        args.extend(["--label", self.GUARDKIT_LABEL])
        
        if options.methodology_mode:
            args.extend(["--label", f"mode:{options.methodology_mode.value}"])
        
        if options.priority_max is not None:
            args.extend(["--priority-max", str(options.priority_max)])
        
        result = self._run_bd(args)
        if result.returncode != 0:
            return []
        
        bd_issues = json.loads(result.stdout)
        return [self._bd_to_task(issue) for issue in bd_issues]
    
    def add_dependency(self, task_id: str, depends_on_id: str, 
                       dep_type: str = "blocks") -> bool:
        """Add dependency in Beads."""
        args = ["dep", "add", task_id, depends_on_id, "--type", dep_type]
        result = self._run_bd(args)
        return result.returncode == 0
    
    def create_child(self, parent_id: str, task: Task) -> Task:
        """Create child task - Beads auto-assigns hierarchical ID."""
        task.parent_id = parent_id
        created = self.create(task)
        
        # Add parent-child dependency
        self.add_dependency(created.id, parent_id, "parent-child")
        
        return created
    
    def sync(self) -> bool:
        """Sync Beads state with git."""
        result = self._run_bd(["sync"])
        return result.returncode == 0
    
    # Private helpers
    
    def _find_bd(self) -> Optional[str]:
        """Find bd executable."""
        if self._bd_path:
            return self._bd_path
        
        self._bd_path = shutil.which("bd")
        return self._bd_path
    
    def _run_bd(self, args: List[str]) -> subprocess.CompletedProcess:
        """Run bd command."""
        return subprocess.run(
            [self._find_bd()] + args,
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
    
    def _map_task_type(self, task_type: TaskType) -> str:
        """Map GuardKit task type to Beads type."""
        return task_type.value  # Same values
    
    def _map_status_to_bd(self, status: TaskStatus) -> str:
        """Map GuardKit status to Beads status."""
        mapping = {
            TaskStatus.OPEN: "open",
            TaskStatus.IN_PROGRESS: "in_progress",
            TaskStatus.BLOCKED: "blocked",
            TaskStatus.CLOSED: "closed"
        }
        return mapping.get(status, "open")
    
    def _map_status_from_bd(self, bd_status: str) -> TaskStatus:
        """Map Beads status to GuardKit status."""
        mapping = {
            "open": TaskStatus.OPEN,
            "in_progress": TaskStatus.IN_PROGRESS,
            "blocked": TaskStatus.BLOCKED,
            "closed": TaskStatus.CLOSED
        }
        return mapping.get(bd_status, TaskStatus.OPEN)
    
    def _bd_to_task(self, bd_issue: dict) -> Task:
        """Convert Beads issue to GuardKit Task."""
        labels = bd_issue.get("labels", [])
        
        # Extract methodology mode from labels
        mode = MethodologyMode.STANDARD
        guardkit_labels = []
        for label in labels:
            if label.startswith("mode:"):
                mode_str = label.split(":")[1]
                mode = MethodologyMode(mode_str)
            elif label != self.GUARDKIT_LABEL:
                guardkit_labels.append(label)
        
        # Parse notes for GuardKit metadata
        notes = bd_issue.get("notes", "")
        ears_spec, gherkin = self._parse_notes(notes)
        
        return Task(
            id=bd_issue["id"],
            title=bd_issue["title"],
            description=bd_issue.get("description"),
            status=self._map_status_from_bd(bd_issue.get("status", "open")),
            task_type=TaskType(bd_issue.get("type", "task")),
            priority=bd_issue.get("priority", 2),
            methodology_mode=mode,
            labels=guardkit_labels,
            parent_id=bd_issue.get("parent_id"),
            blocking_ids=bd_issue.get("blocking_ids", []),
            ears_spec=ears_spec,
            gherkin_scenarios=gherkin,
            created_at=bd_issue.get("created_at"),
            updated_at=bd_issue.get("updated_at"),
            closed_at=bd_issue.get("closed_at"),
            close_reason=bd_issue.get("close_reason")
        )
    
    def _update_notes(self, task: Task):
        """Store GuardKit metadata in Beads notes field."""
        notes_content = []
        
        if task.ears_spec:
            notes_content.append(f"## EARS Specification\n\n{task.ears_spec}")
        
        if task.gherkin_scenarios:
            notes_content.append(f"## Gherkin Scenarios\n\n{task.gherkin_scenarios}")
        
        if task.quality_gate_results:
            notes_content.append(
                f"## Quality Gate Results\n\n```json\n{json.dumps(task.quality_gate_results, indent=2)}\n```"
            )
        
        if notes_content:
            notes = "\n\n".join(notes_content)
            self._run_bd(["update", task.id, "--notes", notes])
    
    def _parse_notes(self, notes: str) -> tuple:
        """Parse GuardKit metadata from Beads notes."""
        ears_spec = None
        gherkin = None
        
        # Simple section extraction
        if "## EARS Specification" in notes:
            start = notes.index("## EARS Specification") + len("## EARS Specification")
            end = notes.find("##", start) if "##" in notes[start:] else len(notes)
            ears_spec = notes[start:end].strip()
        
        if "## Gherkin Scenarios" in notes:
            start = notes.index("## Gherkin Scenarios") + len("## Gherkin Scenarios")
            end = notes.find("##", start) if "##" in notes[start:] else len(notes)
            gherkin = notes[start:end].strip()
        
        return ears_spec, gherkin
```

---

## Backend Registry and Auto-Detection

```python
# guardkit/backends/__init__.py
from pathlib import Path
from typing import Optional
from .base import TaskBackend
from .markdown import MarkdownBackend
from .beads import BeadsBackend

class BackendRegistry:
    """
    Registry for task backends with auto-detection.
    Prefers Beads when available, falls back to Markdown.
    """
    
    _backends = {
        "markdown": MarkdownBackend,
        "beads": BeadsBackend
    }
    
    @classmethod
    def get_backend(cls, 
                    preferred: Optional[str] = None,
                    project_root: Path = None) -> TaskBackend:
        """
        Get appropriate backend with auto-detection.
        
        Priority:
        1. Explicitly preferred backend (if specified and available)
        2. Beads (if bd is installed and .beads exists or can be initialized)
        3. Markdown (always available fallback)
        """
        project_root = project_root or Path.cwd()
        
        # If explicitly preferred
        if preferred and preferred in cls._backends:
            backend = cls._backends[preferred](project_root)
            if backend.is_available():
                return backend
        
        # Auto-detect: prefer Beads
        beads = BeadsBackend(project_root)
        if beads.is_available():
            beads_dir = project_root / ".beads"
            if beads_dir.exists():
                # Beads already initialized
                return beads
            # Check if we should initialize Beads
            if cls._should_init_beads(project_root):
                beads.initialize()
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
        - No .guardkit/tasks directory exists (fresh project)
        """
        # Check for git repo
        git_dir = project_root / ".git"
        if not git_dir.exists():
            return False
        
        # Check for existing GuardKit markdown tasks
        guardkit_dir = project_root / ".guardkit" / "tasks"
        if guardkit_dir.exists() and any(guardkit_dir.glob("*.md")):
            # Has existing markdown tasks - don't switch
            return False
        
        return True
    
    @classmethod
    def detect_current(cls, project_root: Path = None) -> str:
        """Detect which backend is currently in use."""
        project_root = project_root or Path.cwd()
        
        beads_dir = project_root / ".beads"
        guardkit_dir = project_root / ".guardkit"
        
        if beads_dir.exists():
            return "beads"
        if guardkit_dir.exists():
            return "markdown"
        return "none"


def get_backend(preferred: str = None) -> TaskBackend:
    """Convenience function to get the current backend."""
    return BackendRegistry.get_backend(preferred)
```

---

## Configuration System

```python
# guardkit/config.py
import json
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class GuardKitConfig:
    """GuardKit configuration."""
    
    # Backend preference
    backend: str = "auto"  # "auto", "beads", "markdown"
    
    # Methodology defaults
    default_methodology_mode: str = "standard"
    
    # Quality gate settings
    min_test_coverage: float = 90.0
    require_ears_spec: bool = True
    require_gherkin_for_bdd: bool = True
    
    # Agent settings
    enabled_agents: List[str] = field(default_factory=lambda: [
        "requirements-analyst",
        "test-orchestrator",
        "code-reviewer"
    ])
    
    # Beads-specific settings
    beads_auto_sync: bool = True
    beads_labels: List[str] = field(default_factory=list)
    
    @classmethod
    def load(cls, project_root: Path = None) -> "GuardKitConfig":
        """Load config from .guardkit/config.json or defaults."""
        project_root = project_root or Path.cwd()
        config_file = project_root / ".guardkit" / "config.json"
        
        if config_file.exists():
            data = json.loads(config_file.read_text())
            return cls(**data)
        
        return cls()
    
    def save(self, project_root: Path = None):
        """Save config to .guardkit/config.json."""
        project_root = project_root or Path.cwd()
        config_dir = project_root / ".guardkit"
        config_dir.mkdir(parents=True, exist_ok=True)
        
        config_file = config_dir / "config.json"
        config_file.write_text(json.dumps(self.__dict__, indent=2))
```

---

## Updated CLI Commands

```python
# guardkit/cli/commands.py
import click
from pathlib import Path
from ..backends import get_backend, BackendRegistry
from ..backends.base import Task, TaskType, MethodologyMode, ReadyWorkOptions
from ..config import GuardKitConfig

@click.group()
@click.pass_context
def cli(ctx):
    """GuardKit - AI-powered software engineering methodology."""
    ctx.ensure_object(dict)
    config = GuardKitConfig.load()
    ctx.obj["config"] = config
    ctx.obj["backend"] = get_backend(
        preferred=config.backend if config.backend != "auto" else None
    )

@cli.command()
@click.option("--backend", type=click.Choice(["auto", "beads", "markdown"]),
              default="auto", help="Task storage backend")
@click.pass_context
def init(ctx, backend: str):
    """Initialize GuardKit in current project."""
    project_root = Path.cwd()
    
    # Detect existing state
    current = BackendRegistry.detect_current(project_root)
    if current != "none":
        click.echo(f"GuardKit already initialized with {current} backend")
        return
    
    # Initialize with specified backend
    if backend == "auto":
        be = get_backend()
    else:
        be = get_backend(preferred=backend)
    
    be.initialize()
    
    # Save config
    config = GuardKitConfig(backend=backend)
    config.save()
    
    click.echo(f"✅ GuardKit initialized with {be.backend_name} backend")
    
    if be.backend_name == "beads":
        click.echo("   📦 Using Beads for distributed memory")
        click.echo("   🔗 Dependency tracking enabled")
        click.echo("   🌍 Multi-machine sync via git")
    else:
        click.echo("   📝 Using local markdown files")
        click.echo("   💡 Install 'bd' for enhanced features: https://github.com/steveyegge/beads")

@cli.command("task-create")
@click.argument("title")
@click.option("--mode", type=click.Choice(["standard", "tdd", "bdd"]),
              default="standard", help="Methodology mode")
@click.option("--type", "task_type", type=click.Choice(["epic", "task", "bug", "feature"]),
              default="task", help="Task type")
@click.option("--priority", "-p", type=int, default=2, help="Priority (0-4)")
@click.option("--description", "-d", help="Task description")
@click.option("--discovered-from", help="Parent task ID (for discovered work)")
@click.option("--json", "output_json", is_flag=True, help="JSON output")
@click.pass_context
def task_create(ctx, title, mode, task_type, priority, description, 
                discovered_from, output_json):
    """Create a new task."""
    backend = ctx.obj["backend"]
    
    task = Task(
        id="",  # Will be assigned by backend
        title=title,
        description=description,
        task_type=TaskType(task_type),
        priority=priority,
        methodology_mode=MethodologyMode(mode),
        discovered_from_id=discovered_from
    )
    
    created = backend.create(task)
    
    if output_json:
        click.echo(json.dumps({
            "id": created.id,
            "title": created.title,
            "backend": backend.backend_name,
            "mode": created.methodology_mode.value
        }))
    else:
        click.echo(f"✅ Created {created.id}: {created.title}")
        click.echo(f"   Mode: {created.methodology_mode.value}")
        click.echo(f"   Backend: {backend.backend_name}")
        
        if discovered_from:
            click.echo(f"   Discovered from: {discovered_from}")

@cli.command("task-work")
@click.argument("task_id", required=False)
@click.option("--json", "output_json", is_flag=True, help="JSON output")
@click.pass_context
def task_work(ctx, task_id, output_json):
    """Start working on a task (or pick from ready queue)."""
    backend = ctx.obj["backend"]
    
    if not task_id:
        # Pick from ready queue
        ready = backend.list_ready(ReadyWorkOptions(limit=1))
        if not ready:
            click.echo("No ready tasks found")
            return
        task = ready[0]
        click.echo(f"📋 Selected: {task.id} - {task.title}")
    else:
        task = backend.get(task_id)
        if not task:
            click.echo(f"Task {task_id} not found")
            return
    
    # Update status to in_progress
    task.status = TaskStatus.IN_PROGRESS
    backend.update(task)
    
    if output_json:
        click.echo(json.dumps({
            "id": task.id,
            "title": task.title,
            "mode": task.methodology_mode.value,
            "ears_spec": task.ears_spec,
            "gherkin_scenarios": task.gherkin_scenarios
        }))
    else:
        click.echo(f"\n🔨 Working on: {task.id}")
        click.echo(f"   Title: {task.title}")
        click.echo(f"   Mode: {task.methodology_mode.value}")
        
        if task.ears_spec:
            click.echo(f"\n📋 EARS Specification:\n{task.ears_spec}")
        
        if task.gherkin_scenarios:
            click.echo(f"\n🥒 Gherkin Scenarios:\n{task.gherkin_scenarios}")

@cli.command("task-complete")
@click.argument("task_id")
@click.option("--reason", "-r", default="Completed", help="Completion reason")
@click.option("--skip-quality-gates", is_flag=True, help="Skip quality gate checks")
@click.option("--json", "output_json", is_flag=True, help="JSON output")
@click.pass_context
def task_complete(ctx, task_id, reason, skip_quality_gates, output_json):
    """Complete a task with quality gate verification."""
    backend = ctx.obj["backend"]
    config = ctx.obj["config"]
    
    task = backend.get(task_id)
    if not task:
        click.echo(f"Task {task_id} not found")
        return
    
    # Run quality gates (unless skipped)
    if not skip_quality_gates:
        gate_results = run_quality_gates(task, config)
        task.quality_gate_results = gate_results
        
        if not gate_results.get("passed"):
            click.echo("❌ Quality gates failed:")
            for gate, result in gate_results.get("gates", {}).items():
                status = "✅" if result["passed"] else "❌"
                click.echo(f"   {status} {gate}: {result['message']}")
            
            if not click.confirm("Close anyway?"):
                return
    
    # Close the task
    closed = backend.close(task_id, reason)
    
    # Sync if using Beads
    if backend.supports_distributed:
        backend.sync()
    
    if output_json:
        click.echo(json.dumps({
            "id": closed.id,
            "status": "closed",
            "reason": reason,
            "quality_gates": task.quality_gate_results
        }))
    else:
        click.echo(f"✅ Closed {closed.id}: {reason}")

@cli.command("ready")
@click.option("--limit", "-n", default=10, help="Max results")
@click.option("--mode", type=click.Choice(["standard", "tdd", "bdd"]), help="Filter by mode")
@click.option("--json", "output_json", is_flag=True, help="JSON output")
@click.pass_context
def ready(ctx, limit, mode, output_json):
    """Show tasks ready to work on."""
    backend = ctx.obj["backend"]
    
    options = ReadyWorkOptions(
        limit=limit,
        methodology_mode=MethodologyMode(mode) if mode else None
    )
    
    tasks = backend.list_ready(options)
    
    if output_json:
        click.echo(json.dumps([{
            "id": t.id,
            "title": t.title,
            "priority": t.priority,
            "mode": t.methodology_mode.value
        } for t in tasks]))
    else:
        if not tasks:
            click.echo("No ready tasks")
            return
        
        click.echo(f"📋 Ready tasks ({len(tasks)}):\n")
        for task in tasks:
            mode_badge = {"standard": "📝", "tdd": "🧪", "bdd": "🥒"}.get(
                task.methodology_mode.value, "📝"
            )
            click.echo(f"  P{task.priority} {mode_badge} {task.id}: {task.title}")

@cli.command("status")
@click.pass_context
def status(ctx):
    """Show GuardKit status."""
    backend = ctx.obj["backend"]
    config = ctx.obj["config"]
    
    click.echo("🛡️ GuardKit Status\n")
    click.echo(f"Backend: {backend.backend_name}")
    click.echo(f"  Distributed: {'✅' if backend.supports_distributed else '❌'}")
    click.echo(f"  Dependencies: {'✅' if backend.supports_dependencies else '❌'}")
    
    click.echo(f"\nMethodology Mode: {config.default_methodology_mode}")
    click.echo(f"Quality Gates:")
    click.echo(f"  Min Coverage: {config.min_test_coverage}%")
    click.echo(f"  Require EARS: {'✅' if config.require_ears_spec else '❌'}")
    
    # Show task counts
    ready = backend.list_ready(ReadyWorkOptions(limit=100))
    click.echo(f"\nReady Tasks: {len(ready)}")


def run_quality_gates(task: Task, config: GuardKitConfig) -> dict:
    """Run quality gate checks."""
    results = {"passed": True, "gates": {}}
    
    # Coverage check (would invoke test-orchestrator)
    results["gates"]["coverage"] = {
        "passed": True,  # Would actually check
        "message": f"Coverage meets {config.min_test_coverage}% threshold"
    }
    
    # EARS spec check
    if config.require_ears_spec and task.methodology_mode != MethodologyMode.STANDARD:
        has_ears = bool(task.ears_spec)
        results["gates"]["ears_spec"] = {
            "passed": has_ears,
            "message": "EARS specification present" if has_ears else "Missing EARS specification"
        }
        if not has_ears:
            results["passed"] = False
    
    # Gherkin check for BDD mode
    if config.require_gherkin_for_bdd and task.methodology_mode == MethodologyMode.BDD:
        has_gherkin = bool(task.gherkin_scenarios)
        results["gates"]["gherkin"] = {
            "passed": has_gherkin,
            "message": "Gherkin scenarios present" if has_gherkin else "Missing Gherkin scenarios"
        }
        if not has_gherkin:
            results["passed"] = False
    
    return results


if __name__ == "__main__":
    cli()
```

---

## AGENTS.md Integration

```markdown
# GuardKit Agent Instructions

## Task Management

GuardKit uses a pluggable backend for task management:

### Detecting Backend

Check which backend is active:
```bash
guardkit status
```

### When Using Beads Backend

GuardKit automatically uses Beads when available. Benefits:
- Cross-session memory (survives compaction)
- Dependency tracking with `bd dep`
- Multi-agent coordination via git sync
- Ready work queue via `bd ready`

### When Using Markdown Backend

Without Beads, tasks are stored in `.guardkit/tasks/*.md`.
- Single machine only
- Basic dependency tracking via YAML frontmatter
- Consider installing Beads for enhanced features

## Discovered Work Protocol

When you notice bugs, TODOs, or follow-up work during implementation:

### With Beads Backend:
```bash
guardkit task-create "Discovered issue" --discovered-from <current-task-id>
```
This automatically:
- Creates the issue in Beads
- Links it via `discovered-from` dependency
- Preserves context for future sessions

### With Markdown Backend:
```bash
guardkit task-create "Discovered issue" --discovered-from <current-task-id>
```
Creates task with parent reference in frontmatter.

## Session End Protocol

Before ending a session:

1. **File discovered work** - Create tasks for anything noticed
2. **Update task status** - Mark progress
3. **Sync state** (Beads only):
   ```bash
   guardkit sync  # Or: bd sync
   ```
4. **Commit changes** - Include task files

## Quality Gates

All `task-complete` invocations run quality gates:
- Test coverage check
- EARS specification validation (TDD/BDD modes)
- Gherkin scenario check (BDD mode)

Skip with `--skip-quality-gates` if needed.
```

---

## Migration Path

For projects with existing GuardKit markdown tasks:

```python
# guardkit/cli/migrate.py
import click
from pathlib import Path
from ..backends import MarkdownBackend, BeadsBackend

@click.command()
@click.option("--dry-run", is_flag=True, help="Preview migration")
def migrate_to_beads(dry_run):
    """Migrate from Markdown to Beads backend."""
    project_root = Path.cwd()
    
    # Check Beads availability
    beads = BeadsBackend(project_root)
    if not beads.is_available():
        click.echo("❌ Beads (bd) not installed")
        click.echo("   Install: curl -fsSL https://raw.githubusercontent.com/steveyegge/beads/main/scripts/install.sh | bash")
        return
    
    # Load existing markdown tasks
    markdown = MarkdownBackend(project_root)
    tasks_dir = project_root / ".guardkit" / "tasks"
    
    if not tasks_dir.exists():
        click.echo("No existing tasks to migrate")
        return
    
    task_files = list(tasks_dir.glob("*.md"))
    click.echo(f"Found {len(task_files)} tasks to migrate\n")
    
    if dry_run:
        for tf in task_files:
            task = markdown._read_task_file(tf)
            click.echo(f"  Would migrate: {task.id} - {task.title}")
        return
    
    # Initialize Beads
    beads.initialize()
    
    # Migrate each task
    id_mapping = {}  # old_id -> new_id
    
    for tf in task_files:
        task = markdown._read_task_file(tf)
        old_id = task.id
        task.id = ""  # Let Beads assign new ID
        
        new_task = beads.create(task)
        id_mapping[old_id] = new_task.id
        
        click.echo(f"  ✅ {old_id} → {new_task.id}")
    
    # Re-establish dependencies with new IDs
    for tf in task_files:
        task = markdown._read_task_file(tf)
        if task.blocking_ids:
            new_id = id_mapping.get(task.id)
            for old_blocker_id in task.blocking_ids:
                new_blocker_id = id_mapping.get(old_blocker_id)
                if new_id and new_blocker_id:
                    beads.add_dependency(new_id, new_blocker_id)
    
    # Update config
    from ..config import GuardKitConfig
    config = GuardKitConfig.load()
    config.backend = "beads"
    config.save()
    
    click.echo(f"\n✅ Migrated {len(task_files)} tasks to Beads")
    click.echo("   Old tasks preserved in .guardkit/tasks/")
    click.echo("   Remove manually when ready: rm -rf .guardkit/tasks/")
```

---

## Testing Strategy

```python
# tests/test_backends.py
import pytest
from pathlib import Path
from guardkit.backends import MarkdownBackend, BeadsBackend, get_backend
from guardkit.backends.base import Task, TaskType, MethodologyMode

@pytest.fixture
def temp_project(tmp_path):
    """Create temporary project directory."""
    return tmp_path

class TestMarkdownBackend:
    def test_create_and_get(self, temp_project):
        backend = MarkdownBackend(temp_project)
        backend.initialize()
        
        task = Task(
            id="",
            title="Test task",
            description="Description",
            methodology_mode=MethodologyMode.TDD
        )
        
        created = backend.create(task)
        assert created.id.startswith("GK-")
        
        retrieved = backend.get(created.id)
        assert retrieved.title == "Test task"
        assert retrieved.methodology_mode == MethodologyMode.TDD
    
    def test_list_ready_respects_blockers(self, temp_project):
        backend = MarkdownBackend(temp_project)
        backend.initialize()
        
        # Create blocker
        blocker = backend.create(Task(id="", title="Blocker"))
        
        # Create blocked task
        blocked = backend.create(Task(id="", title="Blocked"))
        backend.add_dependency(blocked.id, blocker.id)
        
        ready = backend.list_ready()
        ready_ids = [t.id for t in ready]
        
        assert blocker.id in ready_ids
        assert blocked.id not in ready_ids
        
        # Close blocker
        backend.close(blocker.id, "Done")
        
        ready = backend.list_ready()
        ready_ids = [t.id for t in ready]
        assert blocked.id in ready_ids

class TestBeadsBackend:
    @pytest.mark.skipif(not BeadsBackend().is_available(), 
                        reason="bd not installed")
    def test_create_and_get(self, temp_project):
        # Initialize git repo (required for Beads)
        (temp_project / ".git").mkdir()
        
        backend = BeadsBackend(temp_project)
        backend.initialize()
        
        task = Task(
            id="",
            title="Beads test task",
            methodology_mode=MethodologyMode.BDD
        )
        
        created = backend.create(task)
        assert created.id.startswith("bd-")
        
        retrieved = backend.get(created.id)
        assert retrieved.title == "Beads test task"

class TestBackendRegistry:
    def test_falls_back_to_markdown(self, temp_project):
        # No bd installed simulation
        backend = get_backend(preferred="markdown")
        assert backend.backend_name == "markdown"
    
    def test_prefers_beads_when_available(self, temp_project):
        if BeadsBackend().is_available():
            (temp_project / ".git").mkdir()
            backend = get_backend()
            # Would prefer Beads in git repo
```

---

## Implementation Phases

### Phase 1: Core Backend Abstraction (3-4 hours)
- [ ] Create `backends/base.py` with `TaskBackend` interface
- [ ] Implement `backends/markdown.py` (extract from current code)
- [ ] Create `backends/__init__.py` with registry
- [ ] Add basic tests

### Phase 2: Beads Backend (4-5 hours)
- [ ] Implement `backends/beads.py`
- [ ] Handle metadata mapping (notes field)
- [ ] Implement dependency methods
- [ ] Add Beads-specific tests (skipped if bd not installed)

### Phase 3: CLI Integration (3-4 hours)
- [ ] Update CLI commands to use backend abstraction
- [ ] Add `--backend` option to init
- [ ] Add `status` command
- [ ] Update `--json` output for all commands

### Phase 4: Migration & Polish (2-3 hours)
- [ ] Implement `migrate-to-beads` command
- [ ] Update AGENTS.md template
- [ ] Documentation
- [ ] End-to-end testing

**Total Estimate: 12-16 hours**

---

## Summary

This design gives GuardKit:

1. **Standalone functionality** - Works with markdown backend, no dependencies
2. **Optional Beads integration** - Automatic when bd is available
3. **Clean abstraction** - Easy to add future backends (e.g., Linear, Jira)
4. **Migration path** - Existing users can upgrade smoothly
5. **Methodology preservation** - EARS, BDD, quality gates work with either backend

The key insight: GuardKit owns *methodology*, Beads owns *memory*. Together they're more powerful than either alone.
