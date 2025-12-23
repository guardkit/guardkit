# AutoBuild Phase 1: Kickoff Document

> **Purpose**: Focused requirements for `/feature-plan` consumption. Extracted from the full AutoBuild Product Specification.

---

## Overview

**Goal**: Add autonomous feature building to GuardKit using adversarial cooperation (player/coach agents) via Claude Agent SDK and LangGraph.

**Key Constraint**: GuardKit is a mix of Python code and Claude Code slash commands. Testing strategy must account for integration seams (see Testing Strategy in main spec).

---

## Feature 1: Enhanced feature-plan Command

### Current State
- `/feature-plan` analyzes a feature and creates tasks
- Tasks are created as markdown files in `.guardkit/tasks/`
- Human manually runs `/task-work` for each task

### Required Changes

**1.1 Output Structure Enhancement**

The feature-plan should output a structured feature file that can be consumed by the orchestrator:

```yaml
# .guardkit/features/FEAT-001.yaml
id: FEAT-001
name: "User Authentication"
description: "Add OAuth2 authentication flow"
created: 2025-01-15T10:30:00Z
status: planned  # planned | in_progress | completed | failed

complexity: 7  # 1-10 scale
estimated_tasks: 4

tasks:
  - id: TASK-001
    name: "Create auth service skeleton"
    complexity: 3
    dependencies: []
    status: pending
    
  - id: TASK-002  
    name: "Implement OAuth2 flow"
    complexity: 5
    dependencies: [TASK-001]
    status: pending
    
  - id: TASK-003
    name: "Add token refresh logic"
    complexity: 4
    dependencies: [TASK-002]
    status: pending
    
  - id: TASK-004
    name: "Integration tests"
    complexity: 3
    dependencies: [TASK-001, TASK-002, TASK-003]
    status: pending

orchestration:
  parallel_groups:
    - [TASK-001]           # Must complete first
    - [TASK-002, TASK-003] # Can run in parallel after TASK-001
    - [TASK-004]           # Final integration
```

**1.2 Dependency Analysis**

- Analyze task descriptions to identify dependencies
- Group independent tasks for parallel execution
- Output `parallel_groups` array showing execution order

**1.3 Complexity Scoring**

Each task should have complexity score (1-10) based on:
- Files likely to be modified
- Integration points
- Test requirements
- Risk factors

**1.4 Backward Compatibility**

- Existing `/feature-plan` behavior unchanged by default
- New `--structured` flag outputs YAML format
- Task markdown files still created for `/task-work` compatibility

### Acceptance Criteria

- [ ] `/feature-plan "description" --structured` outputs YAML feature file
- [ ] Feature file includes task dependencies
- [ ] Feature file includes parallel execution groups
- [ ] Each task has complexity score
- [ ] Existing task markdown files still created
- [ ] Feature file parseable by Python (pyyaml)

---

## Feature 2: Claude Agent SDK Infrastructure

### Purpose

Wrap Claude Agent SDK for use by player/coach agents and orchestrator. Handle async execution, worktree management, and session isolation.

### Components

**2.1 SDK Wrapper**

```python
# guardkit/sdk/claude_wrapper.py
from claude_code_sdk import query, ClaudeCodeOptions
from dataclasses import dataclass
from typing import Optional
import asyncio

@dataclass
class AgentSession:
    """Isolated agent session with its own working directory."""
    session_id: str
    working_dir: str
    options: ClaudeCodeOptions
    
class ClaudeAgentWrapper:
    """Wrapper for Claude Agent SDK with GuardKit integration."""
    
    async def create_session(
        self, 
        working_dir: str,
        session_id: Optional[str] = None
    ) -> AgentSession:
        """Create isolated agent session."""
        pass
    
    async def execute(
        self,
        session: AgentSession,
        prompt: str,
        timeout: int = 300
    ) -> AgentResult:
        """Execute prompt in agent session."""
        pass
    
    async def execute_parallel(
        self,
        sessions: list[AgentSession],
        prompts: list[str]
    ) -> list[AgentResult]:
        """Execute multiple prompts in parallel across sessions."""
        pass
```

**2.2 Worktree Manager**

```python
# guardkit/sdk/worktrees.py
from pathlib import Path
import subprocess

class WorktreeManager:
    """Manage git worktrees for parallel task execution."""
    
    def __init__(self, repo_path: str):
        self.repo_path = Path(repo_path)
        self.worktrees_dir = self.repo_path / ".guardkit" / "worktrees"
    
    def create_worktree(self, task_id: str, branch: str) -> Path:
        """Create isolated worktree for task."""
        pass
    
    def cleanup_worktree(self, task_id: str) -> None:
        """Remove worktree after task completion."""
        pass
    
    def merge_worktree(self, task_id: str, target_branch: str = "main") -> bool:
        """Merge completed worktree back to target branch."""
        pass
    
    def list_active_worktrees(self) -> list[dict]:
        """List all active worktrees with status."""
        pass
```

**2.3 Result Types**

```python
# guardkit/sdk/types.py
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Any

class AgentResultStatus(Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    TIMEOUT = "timeout"
    ERROR = "error"

@dataclass
class AgentResult:
    status: AgentResultStatus
    output: str
    files_modified: list[str]
    tests_run: int
    tests_passed: int
    duration_seconds: float
    error: Optional[str] = None
    trace: Optional[dict] = None  # For contract verification
```

### Acceptance Criteria

- [ ] `ClaudeAgentWrapper` can create isolated sessions
- [ ] Sessions execute prompts via Claude Agent SDK
- [ ] `execute_parallel` runs multiple sessions concurrently
- [ ] `WorktreeManager` creates/cleans up git worktrees
- [ ] Worktrees can be merged back to main branch
- [ ] `AgentResult` captures output, files modified, test results
- [ ] Trace data captured for contract verification

---

## Feature 3: Player Agent

### Purpose

Implementation-focused agent that reads requirements and produces code. Does NOT self-validate success.

### Agent Definition

```yaml
# .claude/agents/autobuild-player.md frontmatter
---
name: autobuild-player
description: Implementation agent for AutoBuild adversarial loop
model: haiku  # Cost-efficient for implementation
triggers: []  # Only invoked by orchestrator
contracts:
  - must_call: guardkit.agents.player.start_implementation
  - must_call: guardkit.agents.player.report_progress
  - must_not: declare task complete without coach validation
---
```

### Player Instructions (Core)

```markdown
## Your Role: PLAYER (Implementation)

You implement features based on requirements. You do NOT validate your own work.

## Workflow

1. Read the task requirements
2. Analyze the codebase for patterns
3. Implement the solution
4. Write tests for your implementation
5. Report what you did (not whether it's correct)

## Critical Rules

- NEVER say "task complete" or "requirements met"
- NEVER self-validate success
- ALWAYS report what files you modified
- ALWAYS report what tests you wrote
- ALWAYS be specific about what you implemented

## Required Python Calls

You MUST call these functions:

```python
from guardkit.agents.player import start_implementation, report_progress

# At start of work
start_implementation(task_id, approach_summary)

# After implementation
report_progress(
    task_id=task_id,
    files_modified=["src/auth.py", "tests/test_auth.py"],
    tests_written=["test_login", "test_logout"],
    implementation_notes="Added OAuth2 flow with refresh token support"
)
```

## Output Format

End your work with:

```json
{
  "status": "implementation_complete",
  "files_modified": ["..."],
  "tests_written": ["..."],
  "notes": "What you implemented",
  "ready_for_validation": true
}
```
```

### Python Support Functions

```python
# guardkit/agents/player.py
from guardkit.sdk.types import AgentResult
from guardkit.tracing import get_trace

def start_implementation(task_id: str, approach: str) -> None:
    """Log start of implementation for tracing."""
    trace = get_trace(task_id)
    trace.log_event("player_start", {"approach": approach})

def report_progress(
    task_id: str,
    files_modified: list[str],
    tests_written: list[str],
    implementation_notes: str
) -> dict:
    """Report implementation progress for coach validation."""
    trace = get_trace(task_id)
    trace.log_event("player_report", {
        "files": files_modified,
        "tests": tests_written,
        "notes": implementation_notes
    })
    return {
        "status": "reported",
        "task_id": task_id
    }
```

### Acceptance Criteria

- [ ] Player agent instructions created in `.claude/agents/`
- [ ] Agent includes contract requirements (must_call/must_not)
- [ ] Python support functions implemented
- [ ] Player never declares success (coach does that)
- [ ] Player reports are structured for coach consumption
- [ ] Trace logging captures player actions

---

## Feature 4: Coach Agent

### Purpose

Validation-focused agent that evaluates player implementation against requirements. Only coach can approve completion.

### Agent Definition

```yaml
# .claude/agents/autobuild-coach.md frontmatter
---
name: autobuild-coach
description: Validation agent for AutoBuild adversarial loop
model: sonnet  # Better reasoning for validation
triggers: []  # Only invoked by orchestrator
contracts:
  - must_call: guardkit.agents.coach.validate_implementation
  - must_call: guardkit.agents.coach.record_decision
  - must_not: trust player self-report of success
---
```

### Coach Instructions (Core)

```markdown
## Your Role: COACH (Validation)

You validate implementations against requirements. You do NOT trust player self-reports.

## Workflow

1. Read the original requirements
2. Review what the player reports they did
3. INDEPENDENTLY verify the implementation
4. Run tests yourself
5. Check edge cases the player might have missed
6. Provide specific feedback OR approve

## Critical Rules

- NEVER trust "it works" from player
- ALWAYS run tests yourself
- ALWAYS check requirements against actual code
- Be SPECIFIC in feedback (file, line, issue)
- Only APPROVE when ALL requirements are met

## Required Python Calls

```python
from guardkit.agents.coach import validate_implementation, record_decision

# Perform validation
result = validate_implementation(
    task_id=task_id,
    requirements=requirements,
    player_report=player_report
)

# Record your decision
record_decision(
    task_id=task_id,
    decision="approve" | "feedback",
    rationale="Why you made this decision",
    feedback_items=[]  # If feedback, list specific issues
)
```

## Decision Criteria

APPROVE only when:
- [ ] All requirements have corresponding implementation
- [ ] All tests pass
- [ ] Edge cases are handled
- [ ] No obvious bugs or issues

FEEDBACK when:
- Missing requirement coverage
- Failing tests
- Edge cases not handled
- Code quality issues

## Output Format

```json
{
  "decision": "approve" | "feedback",
  "requirements_checked": ["req1", "req2"],
  "tests_verified": {"passed": 5, "failed": 0},
  "feedback_items": [
    {"file": "src/auth.py", "line": 42, "issue": "Missing null check"}
  ],
  "rationale": "Why this decision"
}
```
```

### Python Support Functions

```python
# guardkit/agents/coach.py
from guardkit.sdk.types import AgentResult
from guardkit.tracing import get_trace
from enum import Enum

class CoachDecision(Enum):
    APPROVE = "approve"
    FEEDBACK = "feedback"

def validate_implementation(
    task_id: str,
    requirements: list[str],
    player_report: dict
) -> dict:
    """Validate implementation against requirements."""
    trace = get_trace(task_id)
    trace.log_event("coach_validate", {
        "requirements_count": len(requirements),
        "player_files": player_report.get("files_modified", [])
    })
    # Returns validation context for coach to use
    return {
        "task_id": task_id,
        "requirements": requirements,
        "files_to_review": player_report.get("files_modified", [])
    }

def record_decision(
    task_id: str,
    decision: str,
    rationale: str,
    feedback_items: list[dict] = None
) -> dict:
    """Record coach decision for orchestrator."""
    trace = get_trace(task_id)
    trace.log_event("coach_decision", {
        "decision": decision,
        "rationale": rationale,
        "feedback_count": len(feedback_items) if feedback_items else 0
    })
    return {
        "task_id": task_id,
        "decision": decision,
        "rationale": rationale,
        "feedback_items": feedback_items or []
    }
```

### Acceptance Criteria

- [ ] Coach agent instructions created in `.claude/agents/`
- [ ] Agent includes contract requirements
- [ ] Python support functions implemented
- [ ] Coach independently verifies (doesn't trust player)
- [ ] Coach provides specific, actionable feedback
- [ ] Coach decisions are logged for tracing
- [ ] Only coach can approve task completion

---

## Feature 5: Adversarial Loop Orchestrator

### Purpose

LangGraph state machine that runs player/coach loop until approval or turn limit.

### State Schema

```python
# guardkit/orchestrator/state.py
from typing import TypedDict, Annotated, Literal
from langgraph.graph import add_messages

class AutoBuildState(TypedDict):
    # Task identification
    task_id: str
    feature_id: str
    
    # Requirements (immutable during loop)
    requirements: list[str]
    acceptance_criteria: list[str]
    
    # Loop tracking
    turn_count: int
    max_turns: int  # Default 10
    
    # Current phase
    phase: Literal["planning", "implementing", "validating", "complete", "failed"]
    
    # Player state
    player_report: dict | None
    files_modified: list[str]
    
    # Coach state  
    coach_decision: Literal["pending", "approve", "feedback"] 
    coach_feedback: list[dict]
    
    # Message history (for context, but fresh each turn)
    messages: Annotated[list, add_messages]
    
    # Outcome
    success: bool | None
    failure_reason: str | None
```

### Graph Structure

```python
# guardkit/orchestrator/graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver

def build_autobuild_graph() -> StateGraph:
    graph = StateGraph(AutoBuildState)
    
    # Nodes
    graph.add_node("initialize", initialize_task)
    graph.add_node("player_turn", execute_player)
    graph.add_node("coach_turn", execute_coach)
    graph.add_node("process_feedback", process_coach_feedback)
    graph.add_node("finalize_success", finalize_success)
    graph.add_node("finalize_failure", finalize_failure)
    
    # Edges
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "player_turn")
    graph.add_edge("player_turn", "coach_turn")
    
    # Conditional: coach decision
    graph.add_conditional_edges(
        "coach_turn",
        route_coach_decision,
        {
            "approve": "finalize_success",
            "feedback": "process_feedback",
            "max_turns": "finalize_failure"
        }
    )
    
    graph.add_edge("process_feedback", "player_turn")  # Loop back
    graph.add_edge("finalize_success", END)
    graph.add_edge("finalize_failure", END)
    
    return graph.compile(checkpointer=SqliteSaver.from_conn_string(":memory:"))
```

### Node Implementations

```python
# guardkit/orchestrator/nodes.py

async def initialize_task(state: AutoBuildState) -> dict:
    """Load task requirements and set up initial state."""
    task = load_task(state["task_id"])
    return {
        "requirements": task.requirements,
        "acceptance_criteria": task.acceptance_criteria,
        "turn_count": 0,
        "phase": "implementing",
        "coach_decision": "pending"
    }

async def execute_player(state: AutoBuildState) -> dict:
    """Run player agent in isolated session."""
    session = await agent_wrapper.create_session(
        working_dir=get_worktree_path(state["task_id"])
    )
    
    prompt = build_player_prompt(
        requirements=state["requirements"],
        previous_feedback=state["coach_feedback"]
    )
    
    result = await agent_wrapper.execute(session, prompt)
    
    return {
        "player_report": parse_player_output(result.output),
        "files_modified": result.files_modified,
        "turn_count": state["turn_count"] + 1
    }

async def execute_coach(state: AutoBuildState) -> dict:
    """Run coach agent to validate player work."""
    session = await agent_wrapper.create_session(
        working_dir=get_worktree_path(state["task_id"])
    )
    
    prompt = build_coach_prompt(
        requirements=state["requirements"],
        player_report=state["player_report"],
        files_modified=state["files_modified"]
    )
    
    result = await agent_wrapper.execute(session, prompt)
    coach_output = parse_coach_output(result.output)
    
    return {
        "coach_decision": coach_output["decision"],
        "coach_feedback": coach_output.get("feedback_items", []),
        "phase": "validating"
    }

def route_coach_decision(state: AutoBuildState) -> str:
    """Route based on coach decision and turn count."""
    if state["coach_decision"] == "approve":
        return "approve"
    if state["turn_count"] >= state["max_turns"]:
        return "max_turns"
    return "feedback"

async def finalize_success(state: AutoBuildState) -> dict:
    """Mark task as successfully completed."""
    return {
        "phase": "complete",
        "success": True
    }

async def finalize_failure(state: AutoBuildState) -> dict:
    """Mark task as failed after max turns."""
    return {
        "phase": "failed",
        "success": False,
        "failure_reason": f"Max turns ({state['max_turns']}) reached without approval"
    }
```

### Acceptance Criteria

- [ ] LangGraph state machine implemented
- [ ] Player → Coach → (Feedback → Player)* → Complete flow works
- [ ] Turn limit enforced (default 10)
- [ ] Fresh context each turn (no pollution)
- [ ] State persisted for resume capability
- [ ] Success/failure properly recorded
- [ ] Trace captures full loop history

---

## Feature 6: autobuild CLI Command

### Purpose

Command-line interface for running AutoBuild on features and tasks.

### Command Structure

```bash
# Run autobuild on a single task
guardkit autobuild task TASK-001

# Run autobuild on entire feature (all tasks)
guardkit autobuild feature FEAT-001

# Run with orchestrator mode (automated checkpoints)
guardkit autobuild feature FEAT-001 --orchestrate

# Show what would run (dry run)
guardkit autobuild feature FEAT-001 --dry-run

# Limit parallel execution
guardkit autobuild feature FEAT-001 --parallel=2

# Set turn limit
guardkit autobuild task TASK-001 --max-turns=5

# Resume interrupted run
guardkit autobuild resume FEAT-001
```

### Implementation

```python
# guardkit/cli/autobuild.py
import click
from guardkit.orchestrator import AutoBuildOrchestrator
from guardkit.sdk import WorktreeManager

@click.group()
def autobuild():
    """Autonomous feature building with adversarial cooperation."""
    pass

@autobuild.command()
@click.argument("task_id")
@click.option("--max-turns", default=10, help="Maximum player/coach turns")
@click.option("--dry-run", is_flag=True, help="Show what would run")
def task(task_id: str, max_turns: int, dry_run: bool):
    """Run autobuild on a single task."""
    orchestrator = AutoBuildOrchestrator()
    
    if dry_run:
        plan = orchestrator.plan_task(task_id)
        click.echo(f"Would run task {task_id}")
        click.echo(f"  Requirements: {len(plan.requirements)}")
        click.echo(f"  Max turns: {max_turns}")
        return
    
    result = orchestrator.run_task(task_id, max_turns=max_turns)
    
    if result.success:
        click.echo(f"✅ Task {task_id} completed in {result.turns} turns")
    else:
        click.echo(f"❌ Task {task_id} failed: {result.failure_reason}")

@autobuild.command()
@click.argument("feature_id")
@click.option("--orchestrate", is_flag=True, help="Automate human checkpoints")
@click.option("--parallel", default=1, help="Max parallel tasks")
@click.option("--dry-run", is_flag=True, help="Show execution plan")
def feature(feature_id: str, orchestrate: bool, parallel: int, dry_run: bool):
    """Run autobuild on all tasks in a feature."""
    orchestrator = AutoBuildOrchestrator()
    feature_plan = load_feature(feature_id)
    
    if dry_run:
        click.echo(f"Feature: {feature_plan.name}")
        click.echo(f"Tasks: {len(feature_plan.tasks)}")
        for group in feature_plan.parallel_groups:
            click.echo(f"  Parallel group: {group}")
        return
    
    # Execute task groups in order
    for group in feature_plan.parallel_groups:
        if len(group) == 1 or parallel == 1:
            # Sequential
            for task_id in group:
                result = orchestrator.run_task(task_id)
                report_result(task_id, result)
        else:
            # Parallel
            results = orchestrator.run_parallel(group[:parallel])
            for task_id, result in results.items():
                report_result(task_id, result)

@autobuild.command()
@click.argument("feature_id")
def resume(feature_id: str):
    """Resume an interrupted autobuild run."""
    orchestrator = AutoBuildOrchestrator()
    state = orchestrator.load_state(feature_id)
    
    if not state:
        click.echo(f"No saved state for {feature_id}")
        return
    
    click.echo(f"Resuming {feature_id} from task {state.current_task}")
    result = orchestrator.resume(feature_id)
```

### Acceptance Criteria

- [ ] `guardkit autobuild task TASK-ID` runs single task
- [ ] `guardkit autobuild feature FEAT-ID` runs all tasks in feature
- [ ] `--parallel` controls concurrent execution
- [ ] `--dry-run` shows plan without executing
- [ ] `--max-turns` configurable
- [ ] `resume` continues interrupted runs
- [ ] Progress displayed during execution
- [ ] Final summary shows success/failure per task

---

## Testing Approach (Per Main Spec)

**Remember**: Bugs live in the integration seams, not the logic.

### For Each Feature

1. **Unit tests** for Python logic (will pass easily)
2. **Contract verification** in agent instructions
3. **Trace logging** from day one
4. **Integration smoke tests** that actually run commands

### Key Integration Tests

```python
# tests/integration/test_autobuild_e2e.py

@pytest.mark.integration
async def test_autobuild_task_completes():
    """Actually run autobuild on a test task."""
    result = await run_cli(["autobuild", "task", "TEST-001"])
    assert result.exit_code == 0
    assert "completed" in result.output or "failed" in result.output

@pytest.mark.integration  
async def test_player_coach_loop_executes():
    """Verify player and coach both run."""
    result = await run_autobuild_task("TEST-001")
    trace = load_trace("TEST-001")
    
    assert "player_start" in trace.events
    assert "coach_decision" in trace.events

@pytest.mark.integration
async def test_coach_feedback_reaches_player():
    """Verify feedback loop works."""
    # Use a task that requires iteration
    result = await run_autobuild_task("TEST-NEEDS-ITERATION")
    trace = load_trace("TEST-NEEDS-ITERATION")
    
    assert trace.turn_count > 1  # Had to iterate
    assert trace.events[-1]["type"] == "coach_decision"
```

---

## Implementation Order

```
Week 1:
├── Feature 1: Enhanced feature-plan (2-3 days)
│   └── Enables: Structured feature files for orchestrator
│
└── Feature 2: Agent SDK Infrastructure (2-3 days)
    └── Enables: All subsequent features

Week 2:
├── Feature 3: Player Agent (1-2 days)
│   └── Enables: Implementation capability
│
├── Feature 4: Coach Agent (1-2 days)
│   └── Enables: Validation capability
│
└── Feature 5: Orchestrator (2-3 days)
    └── Enables: Adversarial loop

Week 3:
└── Feature 6: autobuild CLI (1-2 days)
    └── Enables: User-facing command
```

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Task completion rate (autobuild) | ≥70% without human intervention |
| Average turns per task | ≤4 |
| Coach approval accuracy | No false positives (approving incomplete) |
| Integration test coverage | 100% of seams tested |
| Time to complete feature | <3 weeks |

---

## References

- Full spec: `AutoBuild_Product_Specification.md`
- Testing strategy: Section "Testing Strategy for Hybrid Architecture"
- Adversarial cooperation: Block AI Research paper
- LangGraph: https://langchain-ai.github.io/langgraph/
