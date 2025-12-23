# Feature 2: Claude Agent SDK Infrastructure

> **Feature ID**: FEATURE-002
> **Priority**: P0 (Foundation for all agent features)
> **Estimated Effort**: 2-3 days
> **Dependencies**: None

---

## Summary

Create infrastructure to wrap Claude Agent SDK for use by player/coach agents and orchestrator. Handle async execution, worktree management, session isolation, and result capture.

---

## Purpose

The Claude Agent SDK provides the low-level capability to run Claude Code programmatically. This feature creates a higher-level abstraction that:

1. Manages isolated sessions (one per agent/task)
2. Handles git worktrees for parallel execution
3. Captures structured results (files modified, tests run, etc.)
4. Provides async execution for parallelism
5. Enables tracing for contract verification

---

## Components

### 2.1 SDK Wrapper

```python
# guardkit/sdk/claude_wrapper.py
from claude_code_sdk import query, ClaudeCodeOptions
from dataclasses import dataclass, field
from typing import Optional, List
import asyncio
import uuid

@dataclass
class AgentSession:
    """Isolated agent session with its own working directory."""
    session_id: str
    working_dir: str
    options: ClaudeCodeOptions
    created_at: float = field(default_factory=lambda: time.time())
    
    @classmethod
    def create(cls, working_dir: str, session_id: Optional[str] = None) -> "AgentSession":
        return cls(
            session_id=session_id or str(uuid.uuid4())[:8],
            working_dir=working_dir,
            options=ClaudeCodeOptions(cwd=working_dir)
        )

class ClaudeAgentWrapper:
    """Wrapper for Claude Agent SDK with GuardKit integration."""
    
    def __init__(self, default_timeout: int = 300):
        self.default_timeout = default_timeout
        self.active_sessions: dict[str, AgentSession] = {}
    
    async def create_session(
        self, 
        working_dir: str,
        session_id: Optional[str] = None
    ) -> AgentSession:
        """Create isolated agent session."""
        session = AgentSession.create(working_dir, session_id)
        self.active_sessions[session.session_id] = session
        return session
    
    async def execute(
        self,
        session: AgentSession,
        prompt: str,
        timeout: Optional[int] = None
    ) -> "AgentResult":
        """Execute prompt in agent session."""
        timeout = timeout or self.default_timeout
        
        try:
            result = await asyncio.wait_for(
                query(prompt=prompt, options=session.options),
                timeout=timeout
            )
            return AgentResult.from_sdk_result(result, session)
        except asyncio.TimeoutError:
            return AgentResult.timeout(session, timeout)
        except Exception as e:
            return AgentResult.error(session, str(e))
    
    async def execute_parallel(
        self,
        sessions: List[AgentSession],
        prompts: List[str],
        timeout: Optional[int] = None
    ) -> List["AgentResult"]:
        """Execute multiple prompts in parallel across sessions."""
        if len(sessions) != len(prompts):
            raise ValueError("Sessions and prompts must have same length")
        
        tasks = [
            self.execute(session, prompt, timeout)
            for session, prompt in zip(sessions, prompts)
        ]
        
        return await asyncio.gather(*tasks)
    
    def cleanup_session(self, session_id: str) -> None:
        """Remove session from tracking."""
        self.active_sessions.pop(session_id, None)
    
    def get_active_sessions(self) -> List[AgentSession]:
        """List all active sessions."""
        return list(self.active_sessions.values())
```

### 2.2 Worktree Manager

```python
# guardkit/sdk/worktrees.py
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, List
import subprocess
import shutil

@dataclass
class WorktreeInfo:
    task_id: str
    path: Path
    branch: str
    created_at: float
    status: str  # "active" | "merged" | "abandoned"

class WorktreeManager:
    """Manage git worktrees for parallel task execution."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.worktrees_dir = self.repo_path / ".guardkit" / "worktrees"
        self.worktrees_dir.mkdir(parents=True, exist_ok=True)
    
    def create_worktree(
        self, 
        task_id: str, 
        base_branch: str = "main"
    ) -> Path:
        """Create isolated worktree for task."""
        worktree_path = self.worktrees_dir / task_id
        branch_name = f"autobuild/{task_id}"
        
        if worktree_path.exists():
            raise ValueError(f"Worktree for {task_id} already exists")
        
        # Create branch and worktree
        subprocess.run(
            ["git", "worktree", "add", "-b", branch_name, str(worktree_path), base_branch],
            cwd=self.repo_path,
            check=True,
            capture_output=True
        )
        
        return worktree_path
    
    def cleanup_worktree(self, task_id: str) -> None:
        """Remove worktree after task completion."""
        worktree_path = self.worktrees_dir / task_id
        branch_name = f"autobuild/{task_id}"
        
        if worktree_path.exists():
            # Remove worktree
            subprocess.run(
                ["git", "worktree", "remove", str(worktree_path), "--force"],
                cwd=self.repo_path,
                capture_output=True
            )
        
        # Delete branch (optional, may want to keep for history)
        subprocess.run(
            ["git", "branch", "-D", branch_name],
            cwd=self.repo_path,
            capture_output=True
        )
    
    def merge_worktree(
        self, 
        task_id: str, 
        target_branch: str = "main",
        squash: bool = True
    ) -> bool:
        """Merge completed worktree back to target branch."""
        branch_name = f"autobuild/{task_id}"
        
        try:
            # Checkout target branch
            subprocess.run(
                ["git", "checkout", target_branch],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            # Merge (squash by default for clean history)
            merge_args = ["git", "merge"]
            if squash:
                merge_args.append("--squash")
            merge_args.append(branch_name)
            
            subprocess.run(
                merge_args,
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            if squash:
                # Commit the squashed changes
                subprocess.run(
                    ["git", "commit", "-m", f"feat: {task_id} (autobuild)"],
                    cwd=self.repo_path,
                    check=True,
                    capture_output=True
                )
            
            return True
            
        except subprocess.CalledProcessError as e:
            # Merge conflict or other error
            subprocess.run(
                ["git", "merge", "--abort"],
                cwd=self.repo_path,
                capture_output=True
            )
            return False
    
    def list_active_worktrees(self) -> List[WorktreeInfo]:
        """List all active worktrees with status."""
        result = subprocess.run(
            ["git", "worktree", "list", "--porcelain"],
            cwd=self.repo_path,
            capture_output=True,
            text=True
        )
        
        worktrees = []
        # Parse porcelain output
        # ... implementation details
        
        return worktrees
    
    def get_worktree_path(self, task_id: str) -> Optional[Path]:
        """Get path for task's worktree if it exists."""
        path = self.worktrees_dir / task_id
        return path if path.exists() else None
```

### 2.3 Result Types

```python
# guardkit/sdk/types.py
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Any
import time

class AgentResultStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"

@dataclass
class AgentResult:
    """Result from agent execution."""
    status: AgentResultStatus
    session_id: str
    output: str
    files_modified: List[str] = field(default_factory=list)
    tests_run: int = 0
    tests_passed: int = 0
    tests_failed: int = 0
    duration_seconds: float = 0.0
    error: Optional[str] = None
    trace: Optional[dict] = None  # For contract verification
    
    @classmethod
    def from_sdk_result(cls, result: Any, session: "AgentSession") -> "AgentResult":
        """Parse SDK result into AgentResult."""
        # Extract structured data from result
        output = str(result)
        
        return cls(
            status=AgentResultStatus.SUCCESS,
            session_id=session.session_id,
            output=output,
            files_modified=cls._extract_files(output),
            tests_run=cls._extract_test_count(output, "run"),
            tests_passed=cls._extract_test_count(output, "passed"),
            tests_failed=cls._extract_test_count(output, "failed"),
            duration_seconds=time.time() - session.created_at
        )
    
    @classmethod
    def timeout(cls, session: "AgentSession", timeout: int) -> "AgentResult":
        return cls(
            status=AgentResultStatus.TIMEOUT,
            session_id=session.session_id,
            output="",
            error=f"Execution timed out after {timeout} seconds"
        )
    
    @classmethod
    def error(cls, session: "AgentSession", error_msg: str) -> "AgentResult":
        return cls(
            status=AgentResultStatus.ERROR,
            session_id=session.session_id,
            output="",
            error=error_msg
        )
    
    @staticmethod
    def _extract_files(output: str) -> List[str]:
        """Extract modified files from output."""
        # Pattern matching for file paths
        # ... implementation
        return []
    
    @staticmethod
    def _extract_test_count(output: str, count_type: str) -> int:
        """Extract test counts from output."""
        # Pattern matching for test results
        # ... implementation
        return 0
    
    @property
    def is_success(self) -> bool:
        return self.status == AgentResultStatus.SUCCESS
    
    @property
    def tests_all_passed(self) -> bool:
        return self.tests_failed == 0 and self.tests_run > 0
```

### 2.4 Tracing Infrastructure

```python
# guardkit/sdk/tracing.py
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import json
import time
from pathlib import Path

@dataclass
class TraceEvent:
    timestamp: float
    event_type: str
    data: Dict[str, Any]
    
    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp,
            "type": self.event_type,
            "data": self.data
        }

@dataclass
class WorkflowTrace:
    """Trace of workflow execution for debugging and contract verification."""
    task_id: str
    started_at: float = field(default_factory=time.time)
    events: List[TraceEvent] = field(default_factory=list)
    python_calls: List[str] = field(default_factory=list)
    agent_invocations: Dict[str, int] = field(default_factory=dict)
    
    def log_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Log an event to the trace."""
        self.events.append(TraceEvent(
            timestamp=time.time(),
            event_type=event_type,
            data=data
        ))
    
    def log_python_call(self, function_name: str) -> None:
        """Log a Python function call."""
        self.python_calls.append(function_name)
        self.log_event("python_call", {"function": function_name})
    
    def log_agent_invocation(self, agent_name: str) -> None:
        """Log an agent invocation."""
        self.agent_invocations[agent_name] = self.agent_invocations.get(agent_name, 0) + 1
        self.log_event("agent_invocation", {"agent": agent_name})
    
    def verify_contract(self, expected_calls: List[str]) -> bool:
        """Verify all expected Python calls were made."""
        return all(call in self.python_calls for call in expected_calls)
    
    def save(self, path: Optional[Path] = None) -> Path:
        """Save trace to file."""
        if path is None:
            path = Path(".guardkit") / "traces" / f"{self.task_id}.json"
        
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, "w") as f:
            json.dump({
                "task_id": self.task_id,
                "started_at": self.started_at,
                "duration": time.time() - self.started_at,
                "events": [e.to_dict() for e in self.events],
                "python_calls": self.python_calls,
                "agent_invocations": self.agent_invocations
            }, f, indent=2)
        
        return path
    
    @classmethod
    def load(cls, task_id: str) -> Optional["WorkflowTrace"]:
        """Load trace from file."""
        path = Path(".guardkit") / "traces" / f"{task_id}.json"
        if not path.exists():
            return None
        
        with open(path) as f:
            data = json.load(f)
        
        trace = cls(task_id=data["task_id"], started_at=data["started_at"])
        trace.python_calls = data["python_calls"]
        trace.agent_invocations = data["agent_invocations"]
        # Reconstruct events...
        
        return trace

# Global trace registry
_traces: Dict[str, WorkflowTrace] = {}

def get_trace(task_id: str) -> WorkflowTrace:
    """Get or create trace for task."""
    if task_id not in _traces:
        _traces[task_id] = WorkflowTrace(task_id=task_id)
    return _traces[task_id]

def save_trace(task_id: str) -> Path:
    """Save and clear trace for task."""
    trace = _traces.pop(task_id, None)
    if trace:
        return trace.save()
    raise ValueError(f"No trace found for {task_id}")
```

---

## File Structure

```
guardkit/
├── sdk/
│   ├── __init__.py
│   ├── claude_wrapper.py    # ClaudeAgentWrapper
│   ├── worktrees.py         # WorktreeManager
│   ├── types.py             # AgentResult, AgentResultStatus
│   └── tracing.py           # WorkflowTrace, TraceEvent
```

---

## Acceptance Criteria

- [ ] `ClaudeAgentWrapper` can create isolated sessions
- [ ] Sessions execute prompts via Claude Agent SDK
- [ ] `execute_parallel` runs multiple sessions concurrently
- [ ] `WorktreeManager` creates git worktrees for tasks
- [ ] Worktrees are isolated (changes don't affect main)
- [ ] Worktrees can be merged back to main branch
- [ ] Merge conflicts are detected and reported
- [ ] `AgentResult` captures output, files modified, test results
- [ ] Trace data captured for contract verification
- [ ] Traces can be saved and loaded
- [ ] All async operations properly handle timeouts

---

## Testing Approach

### Unit Tests

```python
# tests/unit/test_worktrees.py
def test_worktree_creation(tmp_git_repo):
    manager = WorktreeManager(tmp_git_repo)
    path = manager.create_worktree("TASK-001")
    
    assert path.exists()
    assert (path / ".git").exists()

def test_worktree_isolation(tmp_git_repo):
    manager = WorktreeManager(tmp_git_repo)
    path = manager.create_worktree("TASK-001")
    
    # Create file in worktree
    (path / "new_file.py").write_text("# test")
    
    # File should not exist in main repo
    assert not (Path(tmp_git_repo) / "new_file.py").exists()

def test_worktree_merge(tmp_git_repo):
    manager = WorktreeManager(tmp_git_repo)
    path = manager.create_worktree("TASK-001")
    
    # Create and commit file in worktree
    (path / "feature.py").write_text("# feature")
    subprocess.run(["git", "add", "."], cwd=path)
    subprocess.run(["git", "commit", "-m", "feat"], cwd=path)
    
    # Merge back
    success = manager.merge_worktree("TASK-001")
    
    assert success
    assert (Path(tmp_git_repo) / "feature.py").exists()
```

### Integration Tests

```python
# tests/integration/test_sdk_wrapper.py
@pytest.mark.integration
async def test_execute_simple_prompt():
    wrapper = ClaudeAgentWrapper()
    session = await wrapper.create_session("/tmp/test-project")
    
    result = await wrapper.execute(session, "echo 'hello'")
    
    assert result.is_success
    assert "hello" in result.output

@pytest.mark.integration
async def test_execute_parallel():
    wrapper = ClaudeAgentWrapper()
    
    sessions = [
        await wrapper.create_session("/tmp/test-1"),
        await wrapper.create_session("/tmp/test-2")
    ]
    
    results = await wrapper.execute_parallel(
        sessions,
        ["echo 'one'", "echo 'two'"]
    )
    
    assert len(results) == 2
    assert all(r.is_success for r in results)
```

---

## References

- Claude Agent SDK: https://docs.anthropic.com/en/docs/claude-code/sdk
- Git worktrees: https://git-scm.com/docs/git-worktree
- Main spec: `AutoBuild_Product_Specification.md` (Testing Strategy section)
