# FEATURE-002: DeepAgents Infrastructure

> **Status**: Updated to use LangChain DeepAgents
> **Effort**: 0.5 days (down from 2-3 days)
> **Dependencies**: None
> **Enables**: F3 (Player), F4 (Coach), F5 (Orchestrator)

---

## Overview

This feature configures the DeepAgents framework as the foundation for AutoBuild. DeepAgents is an official LangChain package (5.8k ⭐) that provides battle-tested infrastructure for long-horizon agent tasks.

**What DeepAgents provides**:
- `create_deep_agent()` - Agent factory with middleware stack
- `FilesystemMiddleware` - Virtual filesystem for coordination (our blackboard)
- `SubAgentMiddleware` - Isolated subagent spawning (Player/Coach)
- `TodoListMiddleware` - Planning and task tracking
- `SummarizationMiddleware` - Auto-summarize at 170K tokens
- `HumanInTheLoopMiddleware` - Tool-level approval gates

**What we add**:
- `AdversarialLoopMiddleware` - Custom middleware for Player↔Coach loop
- Git worktree management for parallel execution
- GuardKit integration layer

---

## Installation

```bash
# Add to pyproject.toml
pip install deepagents langgraph pyyaml rich
```

Dependencies:
- `deepagents>=0.2.7` - Agent harness
- `langgraph>=0.2.0` - Graph execution (transitive)
- `langchain>=0.3.0` - Core framework (transitive)
- `pyyaml>=6.0` - Feature file parsing
- `rich>=13.0` - CLI progress display

---

## Components

### 2.1 DeepAgents Configuration

```python
# guardkit/orchestrator/config.py
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class AutoBuildConfig:
    """Configuration for AutoBuild orchestrator."""
    
    # Model configuration
    orchestrator_model: str = "anthropic:claude-sonnet-4-5-20250929"
    player_model: str = "anthropic:claude-3-5-haiku-20241022"
    coach_model: str = "anthropic:claude-sonnet-4-5-20250929"
    
    # Loop configuration
    max_turns: int = 5
    require_approval_on_complete: bool = True
    require_approval_on_escalate: bool = True
    
    # Filesystem paths (for coordination)
    coordination_path: str = "/coordination/"
    artifacts_path: str = "/artifacts/"
    working_path: str = "/working/"
    
    # Git worktree settings
    use_worktrees: bool = True
    worktree_base: str = ".guardkit/worktrees"
    
    # Timeout settings
    player_timeout: int = 300  # 5 minutes
    coach_timeout: int = 120   # 2 minutes
```

### 2.2 Filesystem Backend Setup

```python
# guardkit/orchestrator/backends.py
from deepagents.backends import (
    CompositeBackend,
    StateBackend,
    StoreBackend,
    FilesystemBackend,
)
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.sqlite import SqliteSaver
from typing import Optional
import os

def create_coordination_backend(
    store: Optional[InMemoryStore] = None,
    persistent: bool = True,
    db_path: str = ".guardkit/coordination.db",
):
    """
    Create filesystem backend with coordination namespaces.
    
    Namespaces:
    - /coordination/ - Player/Coach communication (persistent)
    - /artifacts/    - Build outputs (persistent)
    - /working/      - Ephemeral working state
    
    Args:
        store: LangGraph store for persistence
        persistent: Whether to persist coordination data
        db_path: Path to SQLite database for checkpoints
    
    Returns:
        Backend factory function for FilesystemMiddleware
    """
    if store is None:
        store = InMemoryStore()
    
    def backend_factory(runtime):
        if persistent:
            return CompositeBackend(
                default=StateBackend(runtime),
                routes={
                    "/coordination/": StoreBackend(runtime),
                    "/artifacts/": StoreBackend(runtime),
                }
            )
        else:
            # All ephemeral for testing
            return StateBackend(runtime)
    
    return backend_factory


def create_checkpointer(db_path: str = ".guardkit/checkpoints.db"):
    """Create SQLite checkpointer for workflow resume."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    return SqliteSaver.from_conn_string(db_path)
```

### 2.3 Git Worktree Manager

```python
# guardkit/orchestrator/worktrees.py
import subprocess
import os
import shutil
from dataclasses import dataclass
from typing import Optional
import uuid

@dataclass
class Worktree:
    """Represents an isolated git worktree for a task."""
    task_id: str
    path: str
    branch: str
    created_at: str
    
    @property
    def exists(self) -> bool:
        return os.path.exists(self.path)


class WorktreeManager:
    """
    Manages git worktrees for parallel task isolation.
    
    Each task gets its own worktree with a dedicated branch,
    allowing multiple tasks to run in parallel without conflicts.
    """
    
    def __init__(self, base_path: str = ".guardkit/worktrees"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
    
    def create(self, task_id: str) -> Worktree:
        """
        Create a new worktree for a task.
        
        Args:
            task_id: Task identifier (e.g., "TASK-001")
        
        Returns:
            Worktree instance with path and branch info
        """
        branch_name = f"autobuild/{task_id}"
        worktree_path = os.path.join(self.base_path, task_id)
        
        # Create branch if it doesn't exist
        try:
            subprocess.run(
                ["git", "branch", branch_name],
                capture_output=True,
                check=False,  # OK if branch exists
            )
        except subprocess.CalledProcessError:
            pass
        
        # Create worktree
        subprocess.run(
            ["git", "worktree", "add", worktree_path, branch_name],
            capture_output=True,
            check=True,
        )
        
        return Worktree(
            task_id=task_id,
            path=worktree_path,
            branch=branch_name,
            created_at=subprocess.run(
                ["date", "-Iseconds"],
                capture_output=True,
                text=True,
            ).stdout.strip(),
        )
    
    def get(self, task_id: str) -> Optional[Worktree]:
        """Get existing worktree for a task."""
        worktree_path = os.path.join(self.base_path, task_id)
        if not os.path.exists(worktree_path):
            return None
        
        # Get branch name
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=worktree_path,
            capture_output=True,
            text=True,
        )
        
        return Worktree(
            task_id=task_id,
            path=worktree_path,
            branch=result.stdout.strip(),
            created_at="",  # Could parse from git log
        )
    
    def merge(self, task_id: str, target_branch: str = "main") -> bool:
        """
        Merge worktree changes back to target branch.
        
        Args:
            task_id: Task identifier
            target_branch: Branch to merge into
        
        Returns:
            True if merge succeeded, False otherwise
        """
        worktree = self.get(task_id)
        if not worktree:
            return False
        
        try:
            # Switch to main repo and merge
            subprocess.run(
                ["git", "checkout", target_branch],
                check=True,
            )
            subprocess.run(
                ["git", "merge", worktree.branch, "--no-ff", 
                 "-m", f"Merge {task_id} from AutoBuild"],
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False
    
    def cleanup(self, task_id: str):
        """Remove worktree and optionally delete branch."""
        worktree_path = os.path.join(self.base_path, task_id)
        
        if os.path.exists(worktree_path):
            subprocess.run(
                ["git", "worktree", "remove", worktree_path, "--force"],
                capture_output=True,
            )
    
    def list_active(self) -> list[Worktree]:
        """List all active worktrees."""
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            capture_output=True,
            text=True,
        )
        
        worktrees = []
        current_path = None
        current_branch = None
        
        for line in result.stdout.split("\n"):
            if line.startswith("worktree "):
                current_path = line[9:]
            elif line.startswith("branch "):
                current_branch = line[7:]
                if current_path and self.base_path in current_path:
                    task_id = os.path.basename(current_path)
                    worktrees.append(Worktree(
                        task_id=task_id,
                        path=current_path,
                        branch=current_branch,
                        created_at="",
                    ))
                current_path = None
                current_branch = None
        
        return worktrees
```

### 2.4 Agent Result Types

```python
# guardkit/orchestrator/types.py
from dataclasses import dataclass, field
from typing import Optional, Literal
from datetime import datetime

@dataclass
class PlayerReport:
    """Report from Player agent after implementation attempt."""
    task_id: str
    turn: int
    files_modified: list[str]
    tests_written: list[str]
    implementation_notes: str
    concerns: list[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class CoachDecision:
    """Decision from Coach agent after validation."""
    task_id: str
    turn: int
    decision: Literal["approve", "feedback"]
    rationale: str
    feedback_items: list[str] = field(default_factory=list)
    severity: Literal["minor", "major", "critical"] = "minor"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class TaskResult:
    """Final result of an AutoBuild task."""
    task_id: str
    status: Literal["completed", "failed", "escalated"]
    turns_used: int
    final_decision: Optional[CoachDecision]
    worktree_path: Optional[str]
    merge_status: Optional[Literal["merged", "pending", "conflict"]]
    summary: str
    duration_seconds: float
```

---

## File Structure

```
guardkit/
├── orchestrator/
│   ├── __init__.py
│   ├── config.py          # AutoBuildConfig
│   ├── backends.py        # Filesystem backend setup
│   ├── worktrees.py       # Git worktree management
│   ├── types.py           # PlayerReport, CoachDecision, TaskResult
│   └── middleware.py      # AdversarialLoopMiddleware (see F5)
```

---

## Usage Example

```python
from guardkit.orchestrator.config import AutoBuildConfig
from guardkit.orchestrator.backends import (
    create_coordination_backend,
    create_checkpointer,
)
from guardkit.orchestrator.worktrees import WorktreeManager
from deepagents import create_deep_agent

# Configure
config = AutoBuildConfig(
    max_turns=5,
    use_worktrees=True,
)

# Create infrastructure
backend = create_coordination_backend(persistent=True)
checkpointer = create_checkpointer()
worktrees = WorktreeManager(config.worktree_base)

# Create task worktree
worktree = worktrees.create("TASK-001")

# Agent creation happens in F5 (Orchestrator)
# This module provides the infrastructure
```

---

## Testing

### Unit Tests

```python
# tests/unit/test_backends.py
import pytest
from guardkit.orchestrator.backends import create_coordination_backend

def test_backend_factory_returns_callable():
    backend = create_coordination_backend(persistent=False)
    assert callable(backend)

def test_coordination_paths_are_persistent():
    # Test that /coordination/ routes to StoreBackend
    pass


# tests/unit/test_worktrees.py
import pytest
from guardkit.orchestrator.worktrees import WorktreeManager

@pytest.fixture
def worktree_manager(tmp_path):
    return WorktreeManager(str(tmp_path / "worktrees"))

def test_create_worktree(worktree_manager):
    # Requires git repo context
    pass

def test_list_active_worktrees(worktree_manager):
    pass
```

### Integration Tests

```python
# tests/integration/test_deepagents_setup.py
import pytest
from deepagents import create_deep_agent
from guardkit.orchestrator.backends import create_coordination_backend

@pytest.mark.integration
def test_deepagent_creates_successfully():
    """Verify DeepAgents setup works."""
    agent = create_deep_agent(
        model="anthropic:claude-3-5-haiku-20241022",
        tools=[],
        system_prompt="Test agent",
    )
    assert agent is not None

@pytest.mark.integration
def test_filesystem_middleware_coordination():
    """Test that coordination paths work."""
    backend = create_coordination_backend(persistent=False)
    
    agent = create_deep_agent(
        model="anthropic:claude-3-5-haiku-20241022",
        tools=[],
        backend=backend,
    )
    
    # Invoke and check filesystem operations work
    result = agent.invoke({
        "messages": [{"role": "user", "content": "Write 'test' to /coordination/test.txt"}]
    })
    assert result is not None
```

---

## Acceptance Criteria

- [ ] `deepagents` package installed and importable
- [ ] `create_coordination_backend()` returns working backend factory
- [ ] `/coordination/` path routes to persistent storage
- [ ] `/working/` path routes to ephemeral storage
- [ ] `WorktreeManager.create()` creates isolated worktree
- [ ] `WorktreeManager.merge()` merges changes back
- [ ] `WorktreeManager.cleanup()` removes worktree
- [ ] `create_checkpointer()` returns SQLite checkpointer
- [ ] Type definitions (`PlayerReport`, `CoachDecision`, `TaskResult`) are complete
- [ ] Unit tests pass
- [ ] Integration test with DeepAgents passes

---

## Migration Notes

### What Changed from Original Design

| Original | DeepAgents-Based |
|----------|------------------|
| Custom `ClaudeAgentWrapper` | Use `create_deep_agent()` |
| Custom `AgentSession` | DeepAgents handles session |
| Custom async execution | DeepAgents async support |
| 2-3 days effort | 0.5 days effort |

### What We Keep

- Git worktree management (unique to our use case)
- Type definitions (for type safety)
- Configuration structure (GuardKit-specific)

---

## References

- [DeepAgents Documentation](https://docs.langchain.com/oss/python/deepagents/overview)
- [DeepAgents Middleware](https://docs.langchain.com/oss/python/deepagents/middleware)
- [LangGraph Checkpointing](https://langchain-ai.github.io/langgraph/concepts/persistence/)
- [Git Worktrees](https://git-scm.com/docs/git-worktree)
