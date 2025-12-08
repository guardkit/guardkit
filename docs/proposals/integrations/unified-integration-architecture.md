# GuardKit Unified Integration Architecture

## Beads + Backlog.md: A Common Abstraction Layer

**Date:** December 6, 2025  
**Status:** Design Proposal  
**Context:** Synthesizing integration approaches from previous conversations

---

## Executive Summary

After reviewing the detailed integration analyses for both Beads and Backlog.md, a clear pattern emerges: **both tools solve the same fundamental problem for GuardKit** (task persistence and tracking) but with different strengths. Rather than maintaining two separate integration codepaths, GuardKit should implement a **unified TaskBackend abstraction** that treats both systems as interchangeable backends.

**Key Insight:** GuardKit owns *task workflow and quality gates*, external tools own *memory and visualization*. The integration boundary is clean: GuardKit orchestrates task execution and enforces quality gates; backends persist task state and provide querying capabilities.

---

## Tool Ecosystem Clarification

GuardKit is part of a broader ecosystem of complementary tools:

| Tool | Domain | Core Function |
|------|--------|---------------|
| **GuardKit** | guardkit.ai | Task workflow, quality gates, agent orchestration |
| **RequireKit** | requirekit.ai | EARS specifications, Gherkin/BDD scenarios (optional) |
| **Beads** | github.com/steveyegge/beads | Agent memory, dependency graphs, cross-session persistence |
| **Backlog.md** | github.com/MrLesk/Backlog.md | Visual task management, Kanban boards, web UI |

### Relationship Model

```
┌─────────────────────────────────────────────────────────────┐
│                    RequireKit (Optional)                     │
│         EARS specs, Gherkin scenarios, requirements          │
│                      requirekit.ai                           │
└─────────────────────────┬───────────────────────────────────┘
                          │ (spec_ref links)
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                        GuardKit                              │
│     Task workflow, quality gates, agent orchestration        │
│                       guardkit.ai                            │
│                                                              │
│  Task metadata:                                              │
│  - id, title, description, status, priority                  │
│  - assignee, labels, methodology_mode                        │
│  - quality_gate_results                                      │
│  - spec_ref (→ RequireKit file, optional)                   │
│  - implementation_notes, acceptance_criteria                 │
└─────────────────────────┬───────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   TaskBackend Interface                      │
│  create() | get() | update() | close() | list_ready()       │
└─────────────────────────┬───────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        ↓                 ↓                 ↓
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Markdown   │  │    Beads     │  │  Backlog.md  │
│  (Default)   │  │  (Optional)  │  │  (Optional)  │
└──────────────┘  └──────────────┘  └──────────────┘
```

**Key Point:** EARS specifications and Gherkin scenarios live in RequireKit, not GuardKit. GuardKit tasks may reference RequireKit specs via a `spec_ref` field, but the specification content itself is managed separately.

---

## Comparison: Beads vs Backlog.md

| Dimension | Beads | Backlog.md |
|-----------|-------|------------|
| **Stars** | 2.8k | 4.1k |
| **Primary Focus** | Agent memory & dependency graph | Task visualization & project management |
| **Storage** | JSONL + SQLite cache | Plain markdown files |
| **CLI** | `bd` commands | `backlog` commands |
| **MCP Support** | Available (beads-mcp) | Native (v1.26+) |
| **Web UI** | Example monitor-webui | Full integrated browser UI |
| **ID System** | Hash-based (`bd-a1b2`) | Sequential (`task-10`) |
| **Dependency Tracking** | Full graph (blocks, related, parent-child, discovered-from) | Basic (deps in frontmatter) |
| **Cross-session Memory** | Core feature (survives compaction) | Standard markdown persistence |
| **Multi-agent Coordination** | Git-synced + Agent Mail option | Git-synced |
| **Ready Work Queue** | `bd ready` built-in | Filter by status |
| **Memory Decay** | Agent-driven compaction | Manual archive |

### Strengths by Use Case

**Choose Beads when:**
- Multi-agent workflows are common
- Long-horizon tasks span multiple sessions
- Dependency graphs are complex (epic → features → tasks → subtasks)
- Agent amnesia is a real problem
- You need `bd ready` for automatic work selection

**Choose Backlog.md when:**
- Visual task management is important
- Non-technical stakeholders need visibility
- Rich web UI is preferred
- Simpler setup (npm install, immediate use)
- Kanban workflow fits your process

---

## Unified Abstraction Design

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         GuardKit Core Layer                              │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────────┐   │
│  │    Quality    │  │     Agent     │  │      Task Workflow         │   │
│  │     Gates     │  │ Orchestration │  │   (task-create/work/       │   │
│  │ (Test/Lint)   │  │  (sub-agents) │  │    complete)               │   │
│  └───────────────┘  └───────────────┘  └───────────────────────────┘   │
│                              │                                          │
│                              ▼                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                   TaskBackend Interface                           │  │
│  │  create() | get() | update() | close() | list_ready() | sync()   │  │
│  │  add_dependency() | create_child() | search()                    │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                              │                                          │
└──────────────────────────────┼──────────────────────────────────────────┘
                               │
         ┌─────────────────────┼─────────────────────┐
         │                     │                     │
         ▼                     ▼                     ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  MarkdownBackend │  │   BeadsBackend  │  │ BacklogMdBackend│
│    (Default)     │  │   (Optional)    │  │   (Optional)    │
│                  │  │                 │  │                 │
│ .guardkit/tasks/ │  │  .beads/*.db    │  │   /backlog/     │
│ Zero deps        │  │  bd CLI         │  │  backlog CLI    │
│ Single machine   │  │  Multi-machine  │  │  Web UI         │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

### The TaskBackend Interface

```python
# guardkit/backends/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from enum import Enum

class TaskStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    BLOCKED = "blocked"
    DONE = "done"

class TaskType(Enum):
    EPIC = "epic"
    TASK = "task"
    BUG = "bug"
    FEATURE = "feature"
    SUBTASK = "subtask"

class MethodologyMode(Enum):
    STANDARD = "standard"
    TDD = "tdd"
    BDD = "bdd"

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
    status: TaskStatus = TaskStatus.OPEN
    task_type: TaskType = TaskType.TASK
    priority: int = 2  # 0=highest, 4=lowest
    methodology_mode: MethodologyMode = MethodologyMode.STANDARD
    labels: List[str] = None
    assignee: Optional[str] = None
    parent_id: Optional[str] = None
    blocking_ids: List[str] = None
    discovered_from_id: Optional[str] = None
    
    # GuardKit-specific metadata
    quality_gate_results: Optional[Dict[str, Any]] = None
    acceptance_criteria: Optional[List[str]] = None
    implementation_notes: Optional[str] = None
    
    # Optional RequireKit reference (when RequireKit is used)
    spec_ref: Optional[str] = None  # e.g., "specs/auth.ears" or "specs/auth.feature"
    
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
    assignee: Optional[str] = None

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

### Backend Capability Matrix

| Capability | Markdown | Beads | Backlog.md |
|------------|----------|-------|------------|
| `backend_name` | "markdown" | "beads" | "backlog.md" |
| `supports_dependencies` | ✅ (basic) | ✅ (full graph) | ✅ (basic) |
| `supports_distributed` | ❌ | ✅ | ✅ |
| `supports_web_ui` | ❌ | ⚡ (example) | ✅ (integrated) |
| `supports_mcp` | ❌ | ✅ | ✅ |
| Ready work queue | Manual filter | `bd ready` native | Filter by status |
| Memory decay | ❌ | ✅ (compaction) | Manual archive |

---

## Field Mapping Strategy

GuardKit's task metadata is lightweight — the heavy specification content lives in RequireKit when used. This simplifies backend mapping:

### GuardKit Task Fields

| Field | Purpose | Backend Storage |
|-------|---------|-----------------|
| `id` | Unique identifier | Native to each backend |
| `title` | Task name | Direct mapping |
| `description` | Brief description | Direct mapping |
| `status` | Workflow state | Map to backend status values |
| `priority` | 0-4 scale | Direct or mapped |
| `labels` | Categorization | Direct mapping |
| `assignee` | Owner | Direct mapping |
| `methodology_mode` | standard/tdd/bdd | Label: `guardkit:bdd` |
| `quality_gate_results` | Test/lint results | Notes field (JSON) |
| `acceptance_criteria` | Done criteria | Native (Backlog.md) or notes |
| `implementation_notes` | Work log | Notes field |
| `spec_ref` | RequireKit file path | Notes field or custom field |
| `blocking_ids` | Dependencies | Native dependency system |

### Beads Mapping

```python
def _task_to_beads(task: Task) -> dict:
    """Convert GuardKit task to Beads format."""
    labels = ["guardkit", f"mode:{task.methodology_mode.value}"]
    if task.labels:
        labels.extend(task.labels)
    
    # Build notes from GuardKit metadata
    notes_parts = []
    if task.spec_ref:
        notes_parts.append(f"**Spec:** `{task.spec_ref}`")
    if task.acceptance_criteria:
        ac_list = "\n".join(f"- [ ] {ac}" for ac in task.acceptance_criteria)
        notes_parts.append(f"## Acceptance Criteria\n{ac_list}")
    if task.quality_gate_results:
        status = "✅ Passed" if task.quality_gate_results.get("passed") else "❌ Failed"
        notes_parts.append(f"**Quality Gates:** {status}")
    if task.implementation_notes:
        notes_parts.append(f"## Notes\n{task.implementation_notes}")
    
    return {
        "title": task.title,
        "description": task.description,
        "type": task.task_type.value,
        "priority": task.priority,
        "labels": labels,
        "notes": "\n\n".join(notes_parts) if notes_parts else None
    }
```

### Backlog.md Mapping

```python
def _task_to_backlog_md(task: Task) -> dict:
    """Convert GuardKit task to Backlog.md format."""
    labels = [f"guardkit:{task.methodology_mode.value}"]
    if task.labels:
        labels.extend(task.labels)
    
    # Build notes
    notes_parts = []
    if task.spec_ref:
        notes_parts.append(f"**Spec:** `{task.spec_ref}`")
    if task.quality_gate_results:
        status = "✅ Passed" if task.quality_gate_results.get("passed") else "❌ Failed"
        notes_parts.append(f"**Quality Gates:** {status}")
    if task.implementation_notes:
        notes_parts.append(task.implementation_notes)
    
    return {
        "title": task.title,
        "description": task.description,
        "status": _map_status_to_backlog(task.status),
        "priority": _map_priority_to_backlog(task.priority),
        "labels": labels,
        "assignee": task.assignee,
        "acceptance_criteria": task.acceptance_criteria or [],
        "notes": "\n\n".join(notes_parts) if notes_parts else None,
        "dependencies": task.blocking_ids or []
    }
```

---

## RequireKit Integration (Optional)

When RequireKit is used alongside GuardKit, tasks can reference specification files:

```yaml
# Example task with RequireKit reference
id: GK-0042
title: Implement OAuth2 Authentication
status: in_progress
methodology_mode: bdd
spec_ref: specs/features/auth/oauth2.feature  # RequireKit file

acceptance_criteria:
  - OAuth2 flow works with Google
  - OAuth2 flow works with GitHub
  - Token refresh handles expiry

quality_gate_results:
  passed: false
  coverage: 78%
  failing_scenarios: 2
```

The `spec_ref` field points to RequireKit-managed files. GuardKit doesn't parse or validate these — it simply maintains the reference for traceability.

---

## Benefits Overview: Why Integrate?

### For GuardKit Users

| Benefit | With Beads | With Backlog.md |
|---------|------------|-----------------|
| **Visual Management** | Basic (monitor-webui) | Full Kanban board + web UI |
| **Team Visibility** | Git-synced state | Shareable board exports |
| **Cross-session Memory** | Native (survives compaction) | Standard git persistence |
| **Dependency Graph** | Full 4-type system | Basic blocking deps |
| **Ready Work Queue** | `bd ready` automatic | Filter by status |
| **Multi-agent Support** | Agent Mail for real-time | Git-based sync |
| **Memory Decay** | Semantic compaction | Manual archive |
| **MCP Integration** | beads-mcp server | Native MCP server |

### Value Proposition by User Type

**Solo Developer:**
- Native markdown is sufficient for simple projects
- Beads adds long-horizon task memory
- Backlog.md adds visual progress tracking

**Small Team (2-5):**
- Backlog.md's web UI enables non-technical visibility
- Git-synced state keeps everyone aligned
- Quality gates ensure consistent output

**Larger Team (5+):**
- Beads' multi-agent coordination prevents conflicts
- Backlog.md's Kanban supports sprint planning
- Both integrate with existing workflows via MCP

**OSS Maintainer:**
- Backlog.md's board export creates shareable status
- Beads' audit trail helps track contributor work
- Native markdown keeps barrier to entry low

---

## Decision Framework

```
┌─────────────────────────────────────────────────────────────────┐
│                    Which backend should I use?                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
              ┌───────────────────────────────┐
              │ Do you need visual Kanban UI? │
              └───────────────────────────────┘
                      │              │
                     YES            NO
                      │              │
                      ▼              ▼
         ┌─────────────────┐  ┌─────────────────────────┐
         │  Backlog.md     │  │ Complex dependency graph?│
         │  Full web UI    │  │ Multi-session tasks?     │
         │  Board exports  │  └─────────────────────────┘
         └─────────────────┘          │           │
                                     YES          NO
                                      │           │
                                      ▼           ▼
                            ┌──────────────┐ ┌──────────────┐
                            │    Beads     │ │   Markdown   │
                            │ Agent memory │ │   (Default)  │
                            │ bd ready     │ │   Zero deps  │
                            └──────────────┘ └──────────────┘
```

---

## Implementation Strategy

### Phase 1: Core Abstraction (4-5 hours)
1. Define `TaskBackend` interface
2. Implement `MarkdownBackend` (extract from existing)
3. Create `BackendRegistry` with detection
4. Add configuration support

### Phase 2: Beads Backend (4-5 hours)
1. Implement `BeadsBackend` class
2. Handle metadata mapping (notes field)
3. Map dependency types
4. Add `bd ready` integration
5. Test with/without bd installed

### Phase 3: Backlog.md Backend (4-5 hours)
1. Implement `BacklogMdBackend` class
2. Support both MCP and CLI modes
3. Map status values and priorities
4. Handle acceptance criteria sync
5. Test with backlog CLI

### Phase 4: Integration & Testing (3-4 hours)
1. Update CLI commands to use abstraction
2. Add migration tooling between backends
3. Update AGENTS.md templates
4. End-to-end testing

**Total Estimate: 15-19 hours**

---

## Priority Recommendation

### Tier 1: Foundation (P0)

| Component | Effort | Notes |
|-----------|--------|-------|
| TaskBackend Interface | 2-3 hrs | Abstract base class |
| Markdown Backend | 2-3 hrs | Zero-dependency default |
| Backend Registry | 1-2 hrs | Auto-detection logic |

### Tier 2: Enhanced Backends (P1)

| Integration | Effort | User Benefit |
|-------------|--------|--------------|
| **Beads Backend** | 4-5 hrs | Agent memory, `bd ready`, complex deps |
| **Backlog.md Backend** | 4-5 hrs | Visual Kanban, web UI, team visibility |

### Recommendation

**Start with Beads** because:
1. More technically aligned with GuardKit's agent-centric focus
2. Solves real problem (agent amnesia) that affects quality
3. `bd ready` directly supports the `task-work` workflow
4. Steve Yegge's influence means good tool design and momentum

**Then add Backlog.md** for:
1. Broader market appeal (visual management)
2. Non-technical stakeholder visibility
3. Stronger web UI story
4. Larger existing community (4.1k vs 2.8k stars)

---

## Conclusion

The unified `TaskBackend` abstraction enables GuardKit to:

1. **Work standalone** with zero dependencies (Markdown backend)
2. **Gain agent memory** with Beads for complex, long-horizon work
3. **Add visual management** with Backlog.md for team visibility
4. **Stay future-proof** for additional integrations (Linear, Jira, etc.)

The key principle: **GuardKit owns task workflow and quality gates; RequireKit owns specifications; backends own persistence and visualization.** This clean separation allows users to choose the right tools for their workflow while maintaining consistent development practices.
