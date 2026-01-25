# Feature 5: Adversarial Loop Orchestrator

> **Feature ID**: FEATURE-005
> **Priority**: P0 (Core workflow)
> **Estimated Effort**: 2-3 days
> **Dependencies**: FEATURE-002, FEATURE-003, FEATURE-004

---

## Summary

Create the LangGraph-based orchestrator that runs the adversarial cooperation loop. The orchestrator manages the Player → Coach → Feedback cycle until approval or turn limit is reached.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      ADVERSARIAL LOOP ORCHESTRATOR                      │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   ┌──────────┐     ┌──────────┐     ┌─────────────┐                    │
│   │Initialize│────▶│  Player  │────▶│    Coach    │                    │
│   └──────────┘     └──────────┘     └─────────────┘                    │
│                          ▲                 │                            │
│                          │                 │                            │
│                          │    ┌────────────┴────────────┐              │
│                          │    │                         │              │
│                          │    ▼                         ▼              │
│                    ┌──────────┐                  ┌──────────┐          │
│                    │ Feedback │                  │  Success │          │
│                    │  (loop)  │                  │  (exit)  │          │
│                    └──────────┘                  └──────────┘          │
│                                                                         │
│   Turn Limit: 10 (configurable)                                        │
│   Fresh Context: Each turn                                              │
│   State: Persisted (resumable)                                         │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## State Schema

```python
# guardkit/orchestrator/state.py
from typing import TypedDict, Annotated, Literal, Optional, List
from langgraph.graph import add_messages
from datetime import datetime

class TaskRequirements(TypedDict):
    """Immutable requirements for the task."""
    description: str
    acceptance_criteria: List[str]
    context_files: List[str]  # Files relevant to the task

class PlayerReport(TypedDict):
    """Report from player agent."""
    files_modified: List[str]
    files_created: List[str]
    tests_written: List[str]
    implementation_notes: str
    concerns: List[str]

class CoachFeedback(TypedDict):
    """Feedback from coach agent."""
    decision: Literal["approve", "feedback"]
    rationale: str
    feedback_items: List[dict]
    requirements_status: List[dict]

class AutoBuildState(TypedDict):
    """State for adversarial loop orchestrator."""
    
    # Task identification
    task_id: str
    feature_id: Optional[str]
    
    # Requirements (immutable during loop)
    requirements: TaskRequirements
    
    # Loop tracking
    turn_count: int
    max_turns: int  # Default 10
    started_at: str  # ISO timestamp
    
    # Current phase
    phase: Literal[
        "initializing",
        "player_implementing", 
        "coach_validating",
        "processing_feedback",
        "completed",
        "failed",
        "escalated"
    ]
    
    # Player state (updated each turn)
    player_report: Optional[PlayerReport]
    
    # Coach state (updated each turn)
    coach_feedback: Optional[CoachFeedback]
    coach_decision: Literal["pending", "approve", "feedback"]
    
    # Accumulated feedback history (for context)
    feedback_history: Annotated[List[CoachFeedback], lambda x, y: x + y]
    
    # Outcome
    success: Optional[bool]
    failure_reason: Optional[str]
    
    # Message history (for debugging, not passed to agents)
    messages: Annotated[List[dict], add_messages]
```

---

## Graph Structure

```python
# guardkit/orchestrator/graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.sqlite import SqliteSaver
from guardkit.orchestrator.state import AutoBuildState
from guardkit.orchestrator.nodes import (
    initialize_task,
    execute_player,
    execute_coach,
    process_feedback,
    finalize_success,
    finalize_failure,
    finalize_escalation
)
from guardkit.orchestrator.edges import route_coach_decision
from pathlib import Path

def build_autobuild_graph(
    checkpoint_path: str = ".guardkit/checkpoints/autobuild.db"
) -> StateGraph:
    """Build the adversarial loop graph."""
    
    # Ensure checkpoint directory exists
    Path(checkpoint_path).parent.mkdir(parents=True, exist_ok=True)
    
    # Create graph
    graph = StateGraph(AutoBuildState)
    
    # Add nodes
    graph.add_node("initialize", initialize_task)
    graph.add_node("player_turn", execute_player)
    graph.add_node("coach_turn", execute_coach)
    graph.add_node("process_feedback", process_feedback)
    graph.add_node("finalize_success", finalize_success)
    graph.add_node("finalize_failure", finalize_failure)
    graph.add_node("finalize_escalation", finalize_escalation)
    
    # Add edges
    graph.add_edge(START, "initialize")
    graph.add_edge("initialize", "player_turn")
    graph.add_edge("player_turn", "coach_turn")
    
    # Conditional routing after coach
    graph.add_conditional_edges(
        "coach_turn",
        route_coach_decision,
        {
            "approve": "finalize_success",
            "feedback": "process_feedback",
            "max_turns": "finalize_failure",
            "escalate": "finalize_escalation"
        }
    )
    
    # Feedback loops back to player
    graph.add_edge("process_feedback", "player_turn")
    
    # All finalizers go to END
    graph.add_edge("finalize_success", END)
    graph.add_edge("finalize_failure", END)
    graph.add_edge("finalize_escalation", END)
    
    # Compile with checkpointer for state persistence
    checkpointer = SqliteSaver.from_conn_string(checkpoint_path)
    
    return graph.compile(checkpointer=checkpointer)

def get_graph() -> StateGraph:
    """Get the singleton graph instance."""
    global _graph
    if _graph is None:
        _graph = build_autobuild_graph()
    return _graph

_graph = None
```

---

## Node Implementations

```python
# guardkit/orchestrator/nodes.py
from guardkit.orchestrator.state import AutoBuildState, PlayerReport, CoachFeedback
from guardkit.sdk.claude_wrapper import ClaudeAgentWrapper, AgentSession
from guardkit.sdk.worktrees import WorktreeManager
from guardkit.sdk.tracing import get_trace, save_trace
from guardkit.tasks import load_task
from datetime import datetime
from typing import Dict, Any

# Singleton instances
_agent_wrapper = ClaudeAgentWrapper()
_worktree_manager: WorktreeManager = None

def get_worktree_manager() -> WorktreeManager:
    global _worktree_manager
    if _worktree_manager is None:
        _worktree_manager = WorktreeManager(".")
    return _worktree_manager


async def initialize_task(state: AutoBuildState) -> Dict[str, Any]:
    """Load task requirements and set up initial state."""
    task_id = state["task_id"]
    
    # Load task from .guardkit/tasks/
    task = load_task(task_id)
    
    # Create worktree for isolated execution
    wtm = get_worktree_manager()
    worktree_path = wtm.create_worktree(task_id)
    
    # Initialize trace
    trace = get_trace(task_id)
    trace.log_event("orchestrator_start", {
        "task_id": task_id,
        "worktree": str(worktree_path)
    })
    
    return {
        "requirements": {
            "description": task.description,
            "acceptance_criteria": task.acceptance_criteria,
            "context_files": task.context_files or []
        },
        "turn_count": 0,
        "max_turns": state.get("max_turns", 10),
        "started_at": datetime.utcnow().isoformat(),
        "phase": "player_implementing",
        "coach_decision": "pending",
        "feedback_history": [],
        "messages": [{
            "role": "system",
            "content": f"Starting autobuild for {task_id}"
        }]
    }


async def execute_player(state: AutoBuildState) -> Dict[str, Any]:
    """Run player agent in isolated session."""
    task_id = state["task_id"]
    
    # Get worktree path
    wtm = get_worktree_manager()
    worktree_path = wtm.get_worktree_path(task_id)
    
    # Create agent session
    session = await _agent_wrapper.create_session(
        working_dir=str(worktree_path),
        session_id=f"player-{task_id}-{state['turn_count']}"
    )
    
    # Build player prompt
    prompt = build_player_prompt(
        requirements=state["requirements"],
        previous_feedback=state.get("coach_feedback"),
        turn_count=state["turn_count"]
    )
    
    # Execute player
    result = await _agent_wrapper.execute(session, prompt)
    
    # Log to trace
    trace = get_trace(task_id)
    trace.log_agent_invocation("player")
    trace.log_event("player_turn", {
        "turn": state["turn_count"] + 1,
        "output_length": len(result.output)
    })
    
    # Parse player output
    player_report = parse_player_output(result.output)
    
    return {
        "player_report": player_report,
        "turn_count": state["turn_count"] + 1,
        "phase": "coach_validating",
        "messages": [{
            "role": "assistant",
            "content": f"Player turn {state['turn_count'] + 1} complete"
        }]
    }


async def execute_coach(state: AutoBuildState) -> Dict[str, Any]:
    """Run coach agent to validate player work."""
    task_id = state["task_id"]
    
    # Get worktree path
    wtm = get_worktree_manager()
    worktree_path = wtm.get_worktree_path(task_id)
    
    # Create agent session
    session = await _agent_wrapper.create_session(
        working_dir=str(worktree_path),
        session_id=f"coach-{task_id}-{state['turn_count']}"
    )
    
    # Build coach prompt
    prompt = build_coach_prompt(
        requirements=state["requirements"],
        player_report=state["player_report"]
    )
    
    # Execute coach
    result = await _agent_wrapper.execute(session, prompt)
    
    # Log to trace
    trace = get_trace(task_id)
    trace.log_agent_invocation("coach")
    trace.log_event("coach_turn", {
        "turn": state["turn_count"],
        "output_length": len(result.output)
    })
    
    # Parse coach output
    coach_feedback = parse_coach_output(result.output)
    
    return {
        "coach_feedback": coach_feedback,
        "coach_decision": coach_feedback["decision"],
        "phase": "processing_feedback" if coach_feedback["decision"] == "feedback" else "completed",
        "messages": [{
            "role": "assistant",
            "content": f"Coach decision: {coach_feedback['decision']}"
        }]
    }


async def process_feedback(state: AutoBuildState) -> Dict[str, Any]:
    """Process coach feedback and prepare for next player turn."""
    return {
        "feedback_history": [state["coach_feedback"]],
        "phase": "player_implementing",
        "messages": [{
            "role": "system",
            "content": f"Feedback processed, starting turn {state['turn_count'] + 1}"
        }]
    }


async def finalize_success(state: AutoBuildState) -> Dict[str, Any]:
    """Mark task as successfully completed."""
    task_id = state["task_id"]
    
    # Merge worktree
    wtm = get_worktree_manager()
    merge_success = wtm.merge_worktree(task_id)
    
    # Save trace
    trace = get_trace(task_id)
    trace.log_event("orchestrator_success", {
        "turns": state["turn_count"],
        "merged": merge_success
    })
    save_trace(task_id)
    
    # Cleanup worktree
    if merge_success:
        wtm.cleanup_worktree(task_id)
    
    return {
        "phase": "completed",
        "success": True,
        "messages": [{
            "role": "system",
            "content": f"Task {task_id} completed in {state['turn_count']} turns"
        }]
    }


async def finalize_failure(state: AutoBuildState) -> Dict[str, Any]:
    """Mark task as failed after max turns."""
    task_id = state["task_id"]
    
    # Save trace (don't cleanup worktree - may want to inspect)
    trace = get_trace(task_id)
    trace.log_event("orchestrator_failure", {
        "turns": state["turn_count"],
        "reason": "max_turns_reached"
    })
    save_trace(task_id)
    
    return {
        "phase": "failed",
        "success": False,
        "failure_reason": f"Max turns ({state['max_turns']}) reached without approval",
        "messages": [{
            "role": "system",
            "content": f"Task {task_id} failed after {state['turn_count']} turns"
        }]
    }


async def finalize_escalation(state: AutoBuildState) -> Dict[str, Any]:
    """Mark task as requiring human intervention."""
    task_id = state["task_id"]
    
    # Save trace
    trace = get_trace(task_id)
    trace.log_event("orchestrator_escalation", {
        "turns": state["turn_count"],
        "reason": "human_review_required"
    })
    save_trace(task_id)
    
    return {
        "phase": "escalated",
        "success": None,  # Not success or failure - needs human
        "failure_reason": "Escalated for human review",
        "messages": [{
            "role": "system",
            "content": f"Task {task_id} escalated for human review"
        }]
    }


# Prompt builders (separate file in practice)

def build_player_prompt(
    requirements: dict,
    previous_feedback: dict | None,
    turn_count: int
) -> str:
    """Build prompt for player agent."""
    prompt_parts = [
        "## Task Requirements",
        requirements["description"],
        "",
        "## Acceptance Criteria",
        *[f"- {ac}" for ac in requirements["acceptance_criteria"]],
    ]
    
    if previous_feedback:
        prompt_parts.extend([
            "",
            "## Previous Coach Feedback (Address These Issues)",
            *[f"- {item['issue']}" for item in previous_feedback.get("feedback_items", [])]
        ])
    
    prompt_parts.extend([
        "",
        f"This is turn {turn_count + 1}. Implement the requirements and report your progress."
    ])
    
    return "\n".join(prompt_parts)


def build_coach_prompt(requirements: dict, player_report: dict) -> str:
    """Build prompt for coach agent."""
    return f"""## Task Requirements
{requirements["description"]}

## Acceptance Criteria
{chr(10).join(f"- {ac}" for ac in requirements["acceptance_criteria"])}

## Player Report
Files Modified: {player_report.get("files_modified", [])}
Tests Written: {player_report.get("tests_written", [])}
Notes: {player_report.get("implementation_notes", "")}

Validate the implementation against ALL requirements. Approve only if everything is met.
"""


def parse_player_output(output: str) -> PlayerReport:
    """Parse player output into structured report."""
    # Extract JSON from output
    # ... implementation
    return {
        "files_modified": [],
        "files_created": [],
        "tests_written": [],
        "implementation_notes": "",
        "concerns": []
    }


def parse_coach_output(output: str) -> CoachFeedback:
    """Parse coach output into structured feedback."""
    # Extract JSON from output
    # ... implementation
    return {
        "decision": "feedback",
        "rationale": "",
        "feedback_items": [],
        "requirements_status": []
    }
```

---

## Edge Routing

```python
# guardkit/orchestrator/edges.py
from guardkit.orchestrator.state import AutoBuildState

def route_coach_decision(state: AutoBuildState) -> str:
    """Route based on coach decision and turn count."""
    
    # Check for approval
    if state["coach_decision"] == "approve":
        return "approve"
    
    # Check turn limit
    if state["turn_count"] >= state["max_turns"]:
        return "max_turns"
    
    # Check for escalation triggers
    if should_escalate(state):
        return "escalate"
    
    # Continue with feedback
    return "feedback"


def should_escalate(state: AutoBuildState) -> bool:
    """Determine if task should be escalated to human."""
    
    # Escalate if same feedback repeated 3+ times
    if len(state["feedback_history"]) >= 3:
        recent = state["feedback_history"][-3:]
        if all_same_issues(recent):
            return True
    
    # Escalate if critical issues detected
    if state["coach_feedback"]:
        for item in state["coach_feedback"].get("feedback_items", []):
            if item.get("severity") == "critical":
                return True
    
    return False


def all_same_issues(feedbacks: list) -> bool:
    """Check if all feedbacks have the same issues (stuck in loop)."""
    if not feedbacks:
        return False
    
    first_issues = set(
        item["issue"] for item in feedbacks[0].get("feedback_items", [])
    )
    
    for feedback in feedbacks[1:]:
        issues = set(
            item["issue"] for item in feedback.get("feedback_items", [])
        )
        if issues != first_issues:
            return False
    
    return True
```

---

## Orchestrator Class

```python
# guardkit/orchestrator/orchestrator.py
from guardkit.orchestrator.graph import get_graph
from guardkit.orchestrator.state import AutoBuildState
from dataclasses import dataclass
from typing import Optional
import asyncio

@dataclass
class AutoBuildResult:
    """Result from autobuild execution."""
    task_id: str
    success: bool
    turns: int
    failure_reason: Optional[str] = None
    trace_path: Optional[str] = None

class AutoBuildOrchestrator:
    """High-level orchestrator for running autobuild."""
    
    def __init__(self):
        self.graph = get_graph()
    
    async def run_task(
        self, 
        task_id: str, 
        max_turns: int = 10,
        feature_id: Optional[str] = None
    ) -> AutoBuildResult:
        """Run autobuild on a single task."""
        
        initial_state: AutoBuildState = {
            "task_id": task_id,
            "feature_id": feature_id,
            "requirements": {},  # Will be populated by initialize
            "turn_count": 0,
            "max_turns": max_turns,
            "started_at": "",
            "phase": "initializing",
            "player_report": None,
            "coach_feedback": None,
            "coach_decision": "pending",
            "feedback_history": [],
            "success": None,
            "failure_reason": None,
            "messages": []
        }
        
        config = {"configurable": {"thread_id": task_id}}
        
        # Run the graph
        final_state = await self.graph.ainvoke(initial_state, config)
        
        return AutoBuildResult(
            task_id=task_id,
            success=final_state.get("success", False),
            turns=final_state.get("turn_count", 0),
            failure_reason=final_state.get("failure_reason"),
            trace_path=f".guardkit/traces/{task_id}.json"
        )
    
    async def run_parallel(
        self,
        task_ids: list[str],
        max_turns: int = 10
    ) -> dict[str, AutoBuildResult]:
        """Run multiple tasks in parallel."""
        
        tasks = [
            self.run_task(task_id, max_turns)
            for task_id in task_ids
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return {
            task_id: result if not isinstance(result, Exception) 
                     else AutoBuildResult(task_id, False, 0, str(result))
            for task_id, result in zip(task_ids, results)
        }
    
    def load_state(self, task_id: str) -> Optional[AutoBuildState]:
        """Load saved state for a task (for resume)."""
        config = {"configurable": {"thread_id": task_id}}
        return self.graph.get_state(config)
    
    async def resume(self, task_id: str) -> AutoBuildResult:
        """Resume an interrupted task."""
        config = {"configurable": {"thread_id": task_id}}
        
        # Resume from checkpoint
        final_state = await self.graph.ainvoke(None, config)
        
        return AutoBuildResult(
            task_id=task_id,
            success=final_state.get("success", False),
            turns=final_state.get("turn_count", 0),
            failure_reason=final_state.get("failure_reason")
        )
```

---

## File Structure

```
guardkit/
├── orchestrator/
│   ├── __init__.py
│   ├── state.py           # AutoBuildState TypedDict
│   ├── graph.py           # LangGraph construction
│   ├── nodes.py           # Node implementations
│   ├── edges.py           # Routing functions
│   ├── orchestrator.py    # AutoBuildOrchestrator class
│   └── prompts.py         # Prompt builders (optional split)
```

---

## Acceptance Criteria

- [ ] LangGraph state machine implemented with all nodes
- [ ] Player → Coach → (Feedback → Player)* → Complete flow works
- [ ] Turn limit enforced (default 10, configurable)
- [ ] Fresh context each turn (no pollution between turns)
- [ ] State persisted via SQLite checkpointer
- [ ] Resume capability works (`resume` method)
- [ ] Success case: task approved, worktree merged
- [ ] Failure case: max turns reached, worktree preserved
- [ ] Escalation case: human review triggered
- [ ] Trace captures full loop history
- [ ] Parallel execution via `run_parallel` method

---

## Testing Approach

### Unit Tests

```python
# tests/unit/test_orchestrator.py
from guardkit.orchestrator.edges import route_coach_decision, should_escalate

def test_route_approve():
    state = {"coach_decision": "approve", "turn_count": 1, "max_turns": 10}
    assert route_coach_decision(state) == "approve"

def test_route_max_turns():
    state = {"coach_decision": "feedback", "turn_count": 10, "max_turns": 10}
    assert route_coach_decision(state) == "max_turns"

def test_route_feedback():
    state = {"coach_decision": "feedback", "turn_count": 3, "max_turns": 10}
    assert route_coach_decision(state) == "feedback"

def test_escalate_repeated_issues():
    feedback = {"feedback_items": [{"issue": "same issue"}]}
    state = {"feedback_history": [feedback, feedback, feedback]}
    assert should_escalate(state) == True
```

### Integration Tests

```python
# tests/integration/test_orchestrator_e2e.py
@pytest.mark.integration
async def test_orchestrator_completes_simple_task():
    orchestrator = AutoBuildOrchestrator()
    result = await orchestrator.run_task("TEST-SIMPLE-001")
    
    assert result.success in [True, False]  # Completes either way
    assert result.turns > 0
    assert result.turns <= 10

@pytest.mark.integration
async def test_orchestrator_respects_max_turns():
    orchestrator = AutoBuildOrchestrator()
    result = await orchestrator.run_task("TEST-HARD-001", max_turns=3)
    
    assert result.turns <= 3

@pytest.mark.integration
async def test_orchestrator_resume():
    orchestrator = AutoBuildOrchestrator()
    
    # Interrupt somehow...
    # Then resume
    result = await orchestrator.resume("TEST-001")
    
    assert result.task_id == "TEST-001"
```

---

## References

- LangGraph: https://langchain-ai.github.io/langgraph/
- Adversarial Cooperation: Block AI Research paper
- Main spec: `AutoBuild_Product_Specification.md`
