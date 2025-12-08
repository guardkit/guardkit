# Beads-First Development: Implementation Plan for GuardKit

**Date:** December 8, 2025  
**Status:** Strategic Implementation Plan  
**Context:** Using Beads to build GuardKit's integration features while gaining memory capabilities

---

## Executive Summary

This document outlines a strategic approach to developing GuardKit's Beads and Backlog.md integration features **by using Beads itself during development**. This "dogfooding" approach proves the value while building it, provides immediate benefits through persistent memory and context, and creates authentic experience for documentation.

The key insight: **use Beads to provide memory and vision while building the very features that integrate Beads**.

---

## Background: What We Already Have

Based on existing project documentation, GuardKit already has:

1. **guardkit-unified-integration-architecture.md** - Defines the `TaskBackend` abstraction treating Beads and Backlog.md as interchangeable backends
2. **guardkit-beads-integration.md** - Detailed specification for Beads as a backend, including code examples
3. **LangGraph-Native_Orchestration_for_TaskWright** - Architecture for automated workflow execution
4. **Claude_Agent_SDK_True_End_to_End_Orchestrator.md** - Parallel task execution using `asyncio.gather()` with git worktrees

### Key Decisions Already Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| **Orchestration** | Claude Agent SDK | `asyncio.gather()` + git worktrees replaces Conductor |
| **Parallel execution** | Git worktrees | File conflict isolation |
| **Backend abstraction** | TaskBackend interface | Supports Beads, Backlog.md, future backends |
| **Human checkpoints** | 2 points | After feature-plan, before final merge |
| **MCP vs CLI** | CLI preferred | 1-2k tokens vs 10-50k for MCP schemas |

---

## Beads Overview (December 2025)

**Beads** (github.com/steveyegge/beads) is a lightweight memory system for coding agents, described as "a drop-in cognitive upgrade for your coding agent."

### Core Features

| Feature | Description |
|---------|-------------|
| **Graph-based tracking** | 4 dependency types: blocks, related, parent-child, discovered-from |
| **Git-backed storage** | JSONL source of truth, SQLite cache for queries |
| **Cross-session memory** | Survives compaction, persists across sessions |
| **Agent-driven compaction** | AI decides what to compress, no API keys required |
| **Ready work queue** | `bd ready` shows unblocked tasks automatically |
| **Distributed sync** | Each machine queries same "database" via git |

### Installation

```bash
# macOS (recommended)
brew install bd

# Or from source
go install github.com/steveyegge/beads/cmd/bd@latest
```

### Key Commands

```bash
bd init --quiet          # Initialize in project
bd create "Task" -t task # Create issue
bd ready                 # Show ready work
bd show <id>             # Full context
bd dep add <a> blocks <b> # Add dependency
bd close <id>            # Mark complete
bd compact --analyze     # Memory decay candidates
```

---

## Implementation Plan: "Beads-First Development"

### Phase 0: Bootstrap (2-4 hours)

**Goal:** Get Beads working with GuardKit locally so you have persistent memory while building.

```bash
# Install Beads
brew install bd

# Initialize in your GuardKit repo
cd ~/Projects/guardkit
bd init --quiet

# Run quickstart to understand the workflow
bd quickstart

# Create the "meta-epic" for this development
bd create "Beads + Backlog.md Integration for GuardKit" -t epic -p 1
```

**Key insight:** Start every session with `bd ready` to see what's next, and end every session with `bd close <id>` or notes on current state.

### Phase 1: Minimal Backend Abstraction (4-6 hours)

**Goal:** Create the `TaskBackend` interface that GuardKit uses, with Beads as the first "real" backend.

**Directory Structure:**
```
guardkit/
├── backends/
│   ├── __init__.py          # Backend registry + auto-detection
│   ├── base.py              # TaskBackend ABC
│   ├── markdown.py          # Current behavior (fallback)
│   └── beads.py             # Beads integration
```

**Auto-Detection Logic:**
```python
def get_backend() -> TaskBackend:
    """Auto-detect best available backend."""
    if shutil.which("bd") and Path(".beads").exists():
        return BeadsBackend()
    elif shutil.which("backlog"):
        return BacklogMdBackend()  # Future
    return MarkdownBackend()
```

**Track this work in Beads:**
```bash
bd create "Create TaskBackend abstraction" -t task -p 1
bd create "Implement BeadsBackend" -t task -p 1
bd create "Refactor CLI to use backend abstraction" -t task -p 1
bd dep add bd-xxx blocks bd-yyy  # Set dependencies
```

### Phase 2: Build Workflow Automation Using Beads (1-2 weeks)

**Goal:** Build the automated feature → tasks → parallel execution pipeline, tracking everything in Beads.

**Epic Structure in Beads:**
```
bd-a1b2: Beads + Backlog.md Integration for GuardKit (EPIC)
├── bd-a1b2.1: TaskBackend abstraction (task)
├── bd-a1b2.2: BeadsBackend implementation (task)  
├── bd-a1b2.3: CLI refactoring (task)
├── bd-a1b2.4: feature-plan command (task)
│   ├── bd-a1b2.4.1: Investigation phase
│   ├── bd-a1b2.4.2: Decomposition logic
│   └── bd-a1b2.4.3: Implementation guide generation
├── bd-a1b2.5: Parallel execution orchestrator (task)
│   ├── bd-a1b2.5.1: Git worktree management
│   ├── bd-a1b2.5.2: asyncio.gather() task runner
│   └── bd-a1b2.5.3: Merge coordination
└── bd-a1b2.6: BacklogMdBackend (future task)
```

**The workflow being built:**
```
feature-plan "Dark mode" 
    → Human reviews plan 
    → feature-work 
    → Auto parallel execution 
    → Human reviews final merge
```

### Phase 3: Common Abstraction for Public Release (3-4 hours)

**Goal:** Extract the backend abstraction into something reusable that others can adopt.

**TaskBackend Interface:**
```python
class TaskBackend(ABC):
    """Abstract interface for task storage backends."""
    
    @abstractmethod
    def create(self, task: Task) -> Task: ...
    
    @abstractmethod
    def get(self, task_id: str) -> Optional[Task]: ...
    
    @abstractmethod
    def update(self, task: Task) -> Task: ...
    
    @abstractmethod
    def list_ready(self) -> List[Task]: ...  # Unblocked tasks
    
    @abstractmethod
    def add_dependency(self, task_id: str, depends_on: str, dep_type: str): ...
```

**Value proposition:**
1. **Used internally by GuardKit** - Primary use case
2. **Published as standalone package** - `guardkit-backends` or similar
3. **Adopted by others** - Anyone wanting to support both Beads and Backlog.md

---

## Why This Order Makes Sense

| Phase | What You Gain |
|-------|---------------|
| **0: Bootstrap** | Immediate memory/context while building |
| **1: Abstraction** | Clean architecture, testable backends |
| **2: Workflow** | The automated feature you actually want |
| **3: Public** | Adoption, community, credibility |

### The Virtuous Cycle

```
┌────────────────────────────────────────────────────────────────────┐
│                                                                    │
│   Using Beads → Better memory → Better development experience      │
│         ↓                                                          │
│   Building integration → Proving the value → Documentation         │
│         ↓                                                          │
│   Public release → Others adopt → Community feedback → Improve     │
│         ↓                                                          │
│   Increased GuardKit adoption ← ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ┘│
│                                                                    │
└────────────────────────────────────────────────────────────────────┘
```

---

## Beads vs Backlog.md Comparison

| Dimension | Beads | Backlog.md |
|-----------|-------|------------|
| **Stars** | 2.8k | 4.1k |
| **Primary Focus** | Agent memory & dependency graph | Task visualization & project management |
| **Storage** | JSONL + SQLite cache | Plain markdown files |
| **CLI** | `bd` commands | `backlog` commands |
| **MCP Support** | Available (beads-mcp) | Native (v1.26+) |
| **Web UI** | Example monitor-webui | Full integrated browser UI |
| **ID System** | Hash-based (`bd-a1b2`) | Sequential (`task-10`) |
| **Dependency Tracking** | Full graph (4 types) | Basic (deps in frontmatter) |
| **Cross-session Memory** | Core feature | Standard git persistence |
| **Ready Work Queue** | `bd ready` built-in | Filter by status |

### When to Choose Each

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

## Recommended First Day

1. **Install Beads:** `brew install bd && bd init`
2. **Create the meta-epic:** Track this development work in Beads
3. **Start Phase 1:** Create `backends/base.py` with the TaskBackend ABC
4. **Use Beads while building:** Every task tracked as a Beads issue

This way, you're immediately benefiting from Beads' memory while building the integration. Every session starts with `bd ready` to see what's next, and every completion runs `bd close <id>`.

---

## Related Documents

- [guardkit-beads-integration.md](beads/guardkit-beads-integration.md) - Technical specification
- [guardkit-backlog-integration-analysis.md](backlog.md/guardkit-backlog-integration-analysis.md) - Backlog.md analysis
- [unified-integration-architecture.md](unified-integration-architecture.md) - Common abstraction design
- [Claude_Agent_SDK_True_End_to_End_Orchestrator.md](../../research/Claude_Agent_SDK_True_End_to_End_Orchestrator.md) - Workflow automation

---

## Summary

This plan leverages the strategic insight that **building with the tool you're integrating** provides:

1. **Immediate value** - Memory and context from day one
2. **Authentic experience** - Real usage informs design decisions
3. **Documentation material** - Genuine examples for users
4. **Proof of concept** - Demonstrate value before asking others to adopt

The investment in Phase 0 (bootstrap) pays dividends throughout the entire development process, making subsequent phases easier and better informed.
