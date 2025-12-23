# FEATURE-005: Adversarial Orchestrator (DeepAgents + Custom Middleware)

> **Status**: Updated to use DeepAgents with custom AdversarialLoopMiddleware
> **Effort**: 2-3 days (unchanged - middleware is our core innovation)
> **Dependencies**: F2 (DeepAgents Infrastructure), F3 (Player), F4 (Coach)
> **Enables**: F6 (CLI)

---

## Overview

The Adversarial Orchestrator manages the Player↔Coach loop using DeepAgents as the foundation. Our custom `AdversarialLoopMiddleware` implements the adversarial cooperation pattern on top of DeepAgents' built-in capabilities.

**What DeepAgents provides**:
- `create_deep_agent()` - Agent factory
- `FilesystemMiddleware` - Coordination filesystem (our blackboard)
- `SubAgentMiddleware` - Player/Coach spawning
- `HumanInTheLoopMiddleware` - Approval gates

**What we add**:
- `AdversarialLoopMiddleware` - Custom middleware for Player↔Coach loop control

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   AutoBuild Orchestrator                    │
│                   (create_deep_agent)                       │
├────────────────────────────────────────────────────────────┤
│  Middleware Stack:                                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ TodoListMiddleware          (planning)               │  │
│  │ FilesystemMiddleware        (coordination/blackboard)│  │
│  │ SubAgentMiddleware          (player/coach spawning)  │  │
│  │ SummarizationMiddleware     (context management)     │  │
│  │ AdversarialLoopMiddleware   (OUR CUSTOM)             │◄─┼── Our innovation
│  │ HumanInTheLoopMiddleware    (approval gates)         │  │
│  └──────────────────────────────────────────────────────┘  │
├────────────────────────────────────────────────────────────┤
│  SubAgents:                                                 │
│  ┌─────────────────┐       ┌─────────────────┐            │
│  │     Player      │       │      Coach      │            │
│  │    (Haiku)      │       │    (Sonnet)     │            │
│  └─────────────────┘       └─────────────────┘            │
└────────────────────────────────────────────────────────────┘
```

---

## AdversarialLoopMiddleware

This is our core innovation - a custom LangChain middleware that implements the adversarial cooperation pattern.

```python
# guardkit/orchestrator/middleware.py
from langchain.agents.middleware import AgentMiddleware
from langchain_core.tools import tool
from typing import Any, Literal
import json

class AdversarialLoopMiddleware(AgentMiddleware):
    """
    Custom middleware implementing the adversarial cooperation pattern.
    
    Provides tools for:
    - Starting adversarial task loops
    - Tracking loop state (turns, status)
    - Routing between Player and Coach
    - Completing or escalating tasks
    
    Communication happens via FilesystemMiddleware at /coordination/.
    """
    
    def __init__(
        self,
        player_name: str = "player",
        coach_name: str = "coach",
        max_turns: int = 5,
        coordination_path: str = "/coordination/",
    ):
        super().__init__()
        self.player_name = player_name
        self.coach_name = coach_name
        self.max_turns = max_turns
        self.coordination_path = coordination_path
    
    @property
    def name(self) -> str:
        return "AdversarialLoopMiddleware"
    
    @property
    def tools(self) -> list:
        """Provide adversarial loop control tools."""
        return [
            self._create_start_task_tool(),
            self._create_get_status_tool(),
            self._create_complete_task_tool(),
            self._create_escalate_tool(),
        ]
    
    def _create_start_task_tool(self):
        @tool
        def start_adversarial_task(
            task_id: str,
            requirements: str,
            acceptance_criteria: list[str],
        ) -> str:
            """
            Start an adversarial task loop.
            
            This initializes the loop state and prepares for Player execution.
            
            Args:
                task_id: Unique task identifier (e.g., "TASK-001")
                requirements: Task requirements description
                acceptance_criteria: List of acceptance criteria
            
            Returns:
                Instructions for proceeding with the loop
            """
            # Write initial state to coordination filesystem
            state = {
                "task_id": task_id,
                "current_turn": 1,
                "max_turns": self.max_turns,
                "status": "in_progress",
                "requirements": requirements,
                "acceptance_criteria": acceptance_criteria,
                "history": [],
            }
            
            return f"""
Adversarial task {task_id} initialized.

NEXT STEP: Delegate to the "{self.player_name}" subagent with these instructions:

"Implement task {task_id}. Requirements: {requirements}

Acceptance criteria:
{chr(10).join(f'- {c}' for c in acceptance_criteria)}

After implementation, write your report to {self.coordination_path}player/turn_1/report.json"

After player completes, delegate to "{self.coach_name}" subagent to review.
"""
        return start_adversarial_task
    
    def _create_get_status_tool(self):
        @tool
        def get_loop_status(task_id: str) -> str:
            """
            Get current status of an adversarial loop.
            
            Args:
                task_id: Task identifier
            
            Returns:
                Current loop state as JSON
            """
            # Read from coordination filesystem
            return f"Read status from {self.coordination_path}state/{task_id}.json"
        return get_loop_status
    
    def _create_complete_task_tool(self):
        @tool
        def complete_task(task_id: str, summary: str) -> str:
            """
            Mark task as successfully completed.
            
            This should only be called after Coach approves.
            Note: This tool requires human approval (HITL).
            
            Args:
                task_id: Task identifier
                summary: Summary of completed work
            
            Returns:
                Completion confirmation
            """
            return f"Task {task_id} marked as complete. Summary: {summary}"
        return complete_task
    
    def _create_escalate_tool(self):
        @tool
        def escalate_task(
            task_id: str,
            reason: str,
            severity: Literal["minor", "major", "critical"] = "major",
        ) -> str:
            """
            Escalate task to human intervention.
            
            Use when:
            - Max turns reached without approval
            - Critical issues discovered
            - Requirements are unclear
            
            Note: This tool requires human approval (HITL).
            
            Args:
                task_id: Task identifier
                reason: Why escalation is needed
                severity: Issue severity
            
            Returns:
                Escalation confirmation
            """
            return f"Task {task_id} escalated ({severity}). Reason: {reason}"
        return escalate_task
    
    def modify_model_request(self, request, runtime):
        """Inject adversarial loop instructions into system prompt."""
        adversarial_instructions = f"""
## Adversarial Task Execution Protocol

When executing a task using the adversarial pattern:

### Starting a Task
1. Call `start_adversarial_task` with task details
2. Follow the returned instructions

### The Adversarial Loop
For each turn (max {self.max_turns} turns):

1. **Player Turn**: Delegate to "{self.player_name}" subagent
   - Player implements code
   - Player writes report to {self.coordination_path}player/turn_N/report.json

2. **Coach Turn**: Delegate to "{self.coach_name}" subagent  
   - Coach reads player's report
   - Coach validates implementation
   - Coach writes decision to {self.coordination_path}coach/turn_N/decision.json

3. **Decision Routing**:
   - If Coach approves → Call `complete_task`
   - If Coach gives feedback → Start next turn with Player
   - If max turns reached → Call `escalate_task`

### Communication Rules
- Player and Coach NEVER communicate directly
- All coordination happens through {self.coordination_path}
- Read reports/decisions before proceeding

### Current Limits
- Max turns: {self.max_turns}
- Player model: Cost-efficient (Haiku)
- Coach model: Better reasoning (Sonnet)
"""
        # Append to existing system prompt
        if hasattr(request, 'system_prompt'):
            request.system_prompt = (request.system_prompt or "") + adversarial_instructions
        return request
```

---

## Orchestrator Factory

```python
# guardkit/orchestrator/factory.py
from deepagents import create_deep_agent
from deepagents.middleware import FilesystemMiddleware
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore
from langgraph.checkpoint.sqlite import SqliteSaver

from guardkit.orchestrator.middleware import AdversarialLoopMiddleware
from guardkit.orchestrator.config import AutoBuildConfig
from guardkit.agents.player import create_player_subagent
from guardkit.agents.coach import create_coach_subagent

ORCHESTRATOR_INSTRUCTIONS = """
# AutoBuild Orchestrator

You are the AutoBuild orchestrator. Your job is to coordinate the implementation of tasks using the adversarial cooperation pattern.

## Your Role
- Receive tasks from the user
- Coordinate Player and Coach agents
- Track progress and handle decisions
- Report results

## Available SubAgents
- **player**: Implementation-focused agent (writes code, tests)
- **coach**: Validation-focused agent (reviews, approves/rejects)

## Workflow
1. User provides task details
2. You start the adversarial loop
3. Player implements, Coach validates
4. Loop continues until approval or max turns
5. You report the final result

Always use the adversarial pattern for implementation tasks.
"""


def create_autobuild_orchestrator(
    config: AutoBuildConfig = None,
    store: InMemoryStore = None,
    checkpointer: SqliteSaver = None,
):
    """
    Create the AutoBuild orchestrator using DeepAgents.
    
    Args:
        config: AutoBuild configuration
        store: LangGraph store for persistence
        checkpointer: SQLite checkpointer for resume capability
    
    Returns:
        Configured DeepAgents agent graph
    """
    if config is None:
        config = AutoBuildConfig()
    
    if store is None:
        store = InMemoryStore()
    
    # Create subagents
    player_subagent = create_player_subagent(model=config.player_model)
    coach_subagent = create_coach_subagent(model=config.coach_model)
    
    # Create filesystem backend with coordination namespaces
    def backend_factory(runtime):
        return CompositeBackend(
            default=StateBackend(runtime),
            routes={
                config.coordination_path: StoreBackend(runtime),
                config.artifacts_path: StoreBackend(runtime),
            }
        )
    
    # Create the orchestrator
    orchestrator = create_deep_agent(
        model=config.orchestrator_model,
        tools=[],  # Orchestrator delegates to subagents
        system_prompt=ORCHESTRATOR_INSTRUCTIONS,
        subagents=[player_subagent, coach_subagent],
        store=store,
        backend=backend_factory,
        middleware=[
            AdversarialLoopMiddleware(
                player_name="player",
                coach_name="coach",
                max_turns=config.max_turns,
                coordination_path=config.coordination_path,
            ),
        ],
        interrupt_on={
            "complete_task": {
                "allowed_decisions": ["approve", "reject"],
            },
            "escalate_task": {
                "allowed_decisions": ["approve", "reject"],
            },
        },
        checkpointer=checkpointer,
    )
    
    return orchestrator
```

---

## Orchestrator Class Wrapper

```python
# guardkit/orchestrator/orchestrator.py
from dataclasses import dataclass
from typing import Optional
import asyncio

from guardkit.orchestrator.factory import create_autobuild_orchestrator
from guardkit.orchestrator.config import AutoBuildConfig
from guardkit.orchestrator.worktrees import WorktreeManager
from guardkit.orchestrator.types import TaskResult
from langgraph.checkpoint.sqlite import SqliteSaver


@dataclass
class AutoBuildOrchestrator:
    """
    High-level orchestrator for AutoBuild tasks.
    
    Wraps the DeepAgents-based orchestrator with GuardKit-specific
    functionality like worktree management and result handling.
    """
    
    config: AutoBuildConfig = None
    worktrees: WorktreeManager = None
    checkpointer: SqliteSaver = None
    _agent: any = None
    
    def __post_init__(self):
        if self.config is None:
            self.config = AutoBuildConfig()
        if self.worktrees is None:
            self.worktrees = WorktreeManager(self.config.worktree_base)
        if self.checkpointer is None:
            self.checkpointer = SqliteSaver.from_conn_string(".guardkit/checkpoints.db")
        
        self._agent = create_autobuild_orchestrator(
            config=self.config,
            checkpointer=self.checkpointer,
        )
    
    async def run_task(
        self,
        task_id: str,
        requirements: str,
        acceptance_criteria: list[str],
        use_worktree: bool = True,
    ) -> TaskResult:
        """
        Run a single task through the adversarial loop.
        
        Args:
            task_id: Task identifier
            requirements: Task requirements
            acceptance_criteria: List of acceptance criteria
            use_worktree: Whether to use isolated git worktree
        
        Returns:
            TaskResult with outcome details
        """
        import time
        start_time = time.time()
        
        # Create worktree if enabled
        worktree = None
        if use_worktree and self.config.use_worktrees:
            worktree = self.worktrees.create(task_id)
        
        # Format the task message
        message = f"""
Execute task {task_id} using the adversarial pattern.

Requirements:
{requirements}

Acceptance Criteria:
{chr(10).join(f'- {c}' for c in acceptance_criteria)}

Working directory: {worktree.path if worktree else 'current directory'}
"""
        
        # Run the orchestrator
        try:
            result = await self._agent.ainvoke({
                "messages": [{"role": "user", "content": message}],
            })
            
            # Parse result to determine outcome
            # (Implementation depends on how DeepAgents returns results)
            status = self._parse_status(result)
            turns_used = self._count_turns(result)
            
            return TaskResult(
                task_id=task_id,
                status=status,
                turns_used=turns_used,
                final_decision=None,  # Extract from coordination filesystem
                worktree_path=worktree.path if worktree else None,
                merge_status="pending" if worktree else None,
                summary=self._extract_summary(result),
                duration_seconds=time.time() - start_time,
            )
            
        except Exception as e:
            return TaskResult(
                task_id=task_id,
                status="failed",
                turns_used=0,
                final_decision=None,
                worktree_path=worktree.path if worktree else None,
                merge_status=None,
                summary=f"Error: {str(e)}",
                duration_seconds=time.time() - start_time,
            )
    
    def run_task_sync(self, *args, **kwargs) -> TaskResult:
        """Synchronous wrapper for run_task."""
        return asyncio.run(self.run_task(*args, **kwargs))
    
    async def resume(self, task_id: str) -> TaskResult:
        """Resume an interrupted task from checkpoint."""
        # LangGraph checkpointer handles state restoration
        # We just need to re-invoke with the same thread_id
        pass
    
    def _parse_status(self, result) -> str:
        """Parse completion status from agent result."""
        # Check last message for completion/escalation
        messages = result.get("messages", [])
        if not messages:
            return "failed"
        
        last_message = messages[-1].content if hasattr(messages[-1], 'content') else str(messages[-1])
        
        if "complete" in last_message.lower():
            return "completed"
        elif "escalat" in last_message.lower():
            return "escalated"
        else:
            return "failed"
    
    def _count_turns(self, result) -> int:
        """Count how many turns were used."""
        # Count player report files in coordination
        return 1  # Placeholder
    
    def _extract_summary(self, result) -> str:
        """Extract summary from result."""
        messages = result.get("messages", [])
        if messages:
            return str(messages[-1].content)[:500]
        return "No summary available"
```

---

## File Structure

```
guardkit/
├── orchestrator/
│   ├── __init__.py
│   ├── config.py              # AutoBuildConfig (from F2)
│   ├── backends.py            # Backend setup (from F2)
│   ├── worktrees.py           # WorktreeManager (from F2)
│   ├── types.py               # Result types (from F2)
│   ├── middleware.py          # AdversarialLoopMiddleware ← NEW
│   ├── factory.py             # create_autobuild_orchestrator ← NEW
│   └── orchestrator.py        # AutoBuildOrchestrator wrapper ← NEW
```

---

## Coordination Flow

```
Turn 1:
  ┌─────────────┐     ┌────────────────────────────────────┐
  │ Orchestrator│────►│ start_adversarial_task(TASK-001)   │
  └─────────────┘     └────────────────────────────────────┘
         │
         ▼
  ┌─────────────┐     ┌────────────────────────────────────┐
  │   Player    │────►│ /coordination/player/turn_1/       │
  │  (subagent) │     │   report.json                      │
  └─────────────┘     └────────────────────────────────────┘
         │
         ▼
  ┌─────────────┐     ┌────────────────────────────────────┐
  │    Coach    │◄────│ Read player report                 │
  │  (subagent) │────►│ /coordination/coach/turn_1/        │
  └─────────────┘     │   decision.json                    │
         │            └────────────────────────────────────┘
         ▼
  ┌─────────────┐
  │ Orchestrator│──── If approve: complete_task()
  └─────────────┘     If feedback: Start Turn 2
```

---

## Testing

### Unit Tests

```python
# tests/unit/orchestrator/test_middleware.py
import pytest
from guardkit.orchestrator.middleware import AdversarialLoopMiddleware

def test_middleware_has_required_tools():
    middleware = AdversarialLoopMiddleware()
    tool_names = [t.name for t in middleware.tools]
    
    assert "start_adversarial_task" in tool_names
    assert "get_loop_status" in tool_names
    assert "complete_task" in tool_names
    assert "escalate_task" in tool_names

def test_middleware_injects_instructions():
    middleware = AdversarialLoopMiddleware(max_turns=3)
    
    class MockRequest:
        system_prompt = "Base prompt"
    
    request = MockRequest()
    modified = middleware.modify_model_request(request, None)
    
    assert "Adversarial Task Execution" in modified.system_prompt
    assert "max 3 turns" in modified.system_prompt
```

### Integration Tests

```python
# tests/integration/orchestrator/test_orchestrator.py
import pytest
from guardkit.orchestrator.orchestrator import AutoBuildOrchestrator
from guardkit.orchestrator.config import AutoBuildConfig

@pytest.mark.integration
async def test_orchestrator_runs_simple_task():
    """Test that orchestrator can run a simple task."""
    config = AutoBuildConfig(
        max_turns=2,
        use_worktrees=False,  # Skip worktrees for testing
    )
    
    orchestrator = AutoBuildOrchestrator(config=config)
    
    result = await orchestrator.run_task(
        task_id="TEST-001",
        requirements="Create a function that returns 'hello world'",
        acceptance_criteria=["Function exists", "Returns correct string"],
    )
    
    assert result.task_id == "TEST-001"
    assert result.status in ["completed", "failed", "escalated"]
    assert result.turns_used >= 1


@pytest.mark.integration
async def test_player_coach_both_invoked():
    """Verify both Player and Coach are invoked."""
    config = AutoBuildConfig(max_turns=1, use_worktrees=False)
    orchestrator = AutoBuildOrchestrator(config=config)
    
    result = await orchestrator.run_task(
        task_id="TEST-002",
        requirements="Simple test task",
        acceptance_criteria=["Basic check"],
    )
    
    # Check coordination filesystem for evidence of both agents
    # (This would read from the filesystem middleware)
    pass
```

---

## Acceptance Criteria

- [ ] `AdversarialLoopMiddleware` provides required tools
- [ ] Middleware injects adversarial instructions into system prompt
- [ ] `create_autobuild_orchestrator()` returns configured agent
- [ ] Orchestrator can invoke Player and Coach subagents
- [ ] Coordination happens through filesystem at `/coordination/`
- [ ] HITL gates work for `complete_task` and `escalate_task`
- [ ] `AutoBuildOrchestrator` wrapper provides sync/async interface
- [ ] Worktree integration works
- [ ] Checkpointing enables resume
- [ ] Unit tests pass
- [ ] Integration tests pass

---

## Migration Notes

### What Changed from Original Design

| Original | DeepAgents-Based |
|----------|------------------|
| Custom LangGraph StateGraph | Use `create_deep_agent()` |
| Custom nodes for Player/Coach | SubAgents via middleware |
| Custom blackboard (F7) | `FilesystemMiddleware` |
| Custom consensus gates | `HumanInTheLoopMiddleware` |
| Custom state management | LangGraph built-in |

### What We Build

- `AdversarialLoopMiddleware` - Our core innovation
- `create_autobuild_orchestrator()` - Factory function
- `AutoBuildOrchestrator` - High-level wrapper
- Integration with worktrees

---

## References

- [DeepAgents Custom Middleware](https://docs.langchain.com/oss/python/langchain/middleware)
- [LangChain AgentMiddleware](https://reference.langchain.com/python/langchain/middleware)
- [FEATURE-002: DeepAgents Infrastructure](./FEATURE-002-agent-sdk-infrastructure.md)
- [FEATURE-003: Player Agent](./FEATURE-003-player-agent.md)
- [FEATURE-004: Coach Agent](./FEATURE-004-coach-agent.md)
- [Adversarial Cooperation Paper](../adversarial-cooperation-in-code-synthesis.pdf)
