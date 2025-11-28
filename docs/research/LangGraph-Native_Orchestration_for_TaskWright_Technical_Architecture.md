# LangGraph-Native Orchestration for TaskWright: Technical Architecture

**LangGraph provides an excellent architectural fit for TaskWright's 7-phase workflow**, offering native support for human-in-the-loop checkpoints, complexity-based routing, and long-running workflow persistence. The framework's `interrupt()` function maps directly to TaskWright's approval gates, while `StateGraph` naturally models the phase-to-phase transitions. Key quick wins include a **2-3 day implementation** of the core Phase 2→Phase 5 flow with SQLite persistence, enabling design-first workflows to persist across days between design approval and implementation.

---

## TaskWright Phases Map Cleanly to LangGraph Nodes

TaskWright's workflow translates to a LangGraph `StateGraph` where each phase becomes a node and transitions become edges (conditional or fixed). The architecture preserves TaskWright's design-first philosophy while adding persistence, time-travel debugging, and formalized human checkpoints.

```
                    ┌─────────────────────────────────────────────────────────────────┐
                    │                    TaskWright StateGraph                         │
                    └─────────────────────────────────────────────────────────────────┘
                                                 │
                                            [START]
                                                 │
                    ┌────────────────────────────┴────────────────────────────┐
                    │                     micro_task_check                     │
                    │            (Route: micro_task → full_workflow)           │
                    └────────────────────────────┬────────────────────────────┘
                                    ┌────────────┴────────────┐
                              [micro_task]              [full_workflow]
                                    │                         │
                              ┌─────┴─────┐            ┌──────┴──────┐
                              │ Phase 2   │            │  Phase 2    │
                              │ Planning  │            │  Planning   │
                              │ (simple)  │            │  (full)     │
                              └─────┬─────┘            └──────┬──────┘
                                    │                         │
                               [END]                   ┌──────┴──────┐
                                                       │ Phase 2.5B  │
                                                       │ Arch Review │
                                                       └──────┬──────┘
                                                              │
                                                       ┌──────┴──────┐
                                                       │ Phase 2.7   │
                                                       │ Complexity  │
                                                       └──────┬──────┘
                                                              │
                                    ┌─────────────────────────┼─────────────────────────┐
                                    │                         │                         │
                             [AUTO_PROCEED]           [QUICK_OPTIONAL]          [FULL_REQUIRED]
                             complexity 1-3            complexity 4-6           complexity 7+
                                    │                         │                         │
                                    │                  ┌──────┴──────┐          ┌──────┴──────┐
                                    │                  │ Phase 2.8   │          │ Phase 2.8   │
                                    │                  │ Quick Review│          │ Full Review │
                                    │                  │ (interrupt) │          │ (interrupt) │
                                    │                  └──────┬──────┘          └──────┬──────┘
                                    │                         │                         │
                                    └─────────────────────────┼─────────────────────────┘
                                                              │
                                    ┌─────────────────────────┴─────────────────────────┐
                                    │                    Phase 3                         │
                                    │              Implementation Agent                  │
                                    │    (routes to stack-specific specialist)           │
                                    └─────────────────────────┬─────────────────────────┘
                                                              │
                                    ┌─────────────────────────┴─────────────────────────┐
                                    │                   Phase 4/4.5                      │
                                    │              Testing + Enforcement                 │
                                    │           (retry loop, max 3 attempts)             │
                                    └─────────────────────────┬─────────────────────────┘
                                                              │
                                    ┌─────────────────────────┴─────────────────────────┐
                                    │                   Phase 5/5.5                      │
                                    │               Review + Plan Audit                  │
                                    └─────────────────────────┬─────────────────────────┘
                                                              │
                                                           [END]
```

### Key Architectural Mapping

| TaskWright Concept | LangGraph Equivalent |
|-------------------|---------------------|
| Phase node | `builder.add_node("phase_2", planning_node)` |
| Phase transition | `builder.add_edge("phase_2", "phase_2_5b")` |
| Complexity routing | `builder.add_conditional_edges()` with routing function |
| Human checkpoint | `interrupt()` function with `Command(resume=...)` |
| Test retry loop | Conditional edge looping back to same node |
| Design-first workflow | Checkpoint persistence + `--resume` flag |
| Agent context | TypedDict state schema with agent_context field |

---

## Complexity-Based Routing with Conditional Edges

Phase 2.8's three-tier approval system (AUTO_PROCEED, QUICK_OPTIONAL, FULL_REQUIRED) maps directly to LangGraph's conditional edge routing combined with the `interrupt()` function for human checkpoints.

```python
from typing import Literal, TypedDict, Annotated
from langgraph.graph import StateGraph, START, END
from langgraph.types import interrupt, Command
from langgraph.graph.message import add_messages
from enum import Enum

class ApprovalLevel(Enum):
    AUTO_PROCEED = "auto"        # Complexity 1-3: proceed automatically
    QUICK_OPTIONAL = "optional"  # Complexity 4-6: optional quick review
    FULL_REQUIRED = "required"   # Complexity 7+: mandatory full review

class TaskWrightState(TypedDict):
    """Core state schema for TaskWright workflow."""
    # Task metadata
    task_id: str
    description: str
    
    # Planning outputs
    implementation_plan: dict
    architectural_notes: str
    complexity_score: int  # 1-10 scale
    approval_level: ApprovalLevel
    
    # Approval state
    design_approved: bool
    approval_notes: str
    
    # Implementation outputs  
    code_changes: list[dict]
    test_results: dict
    test_attempt_count: int
    
    # Review outputs
    review_score: float
    review_feedback: str
    
    # Agent coordination
    selected_agent: str
    agent_context: dict
    messages: Annotated[list, add_messages]
    
    # Documentation level propagation
    documentation_level: Literal["minimal", "standard", "comprehensive"]

def complexity_router(state: TaskWrightState) -> Literal["auto_proceed", "quick_review", "full_review"]:
    """Route based on complexity score to appropriate approval path."""
    score = state["complexity_score"]
    
    if score <= 3:
        return "auto_proceed"
    elif score <= 6:
        return "quick_review"
    else:
        return "full_review"

def human_checkpoint_node(state: TaskWrightState) -> Command[Literal["implement", "revise", "abort"]]:
    """Human approval gate with complexity-aware behavior."""
    level = state["approval_level"]
    
    if level == ApprovalLevel.AUTO_PROCEED:
        # No interrupt - auto-approve
        return Command(
            update={"design_approved": True, "approval_notes": "Auto-approved (low complexity)"},
            goto="implement"
        )
    
    elif level == ApprovalLevel.QUICK_OPTIONAL:
        # Quick review - show summary, optional feedback
        decision = interrupt({
            "type": "quick_review",
            "summary": state["implementation_plan"].get("summary"),
            "complexity": state["complexity_score"],
            "message": "Quick review (optional). Press Enter to approve or provide feedback.",
            "timeout_default": "approve"  # External timeout handling
        })
        
        if decision.get("action") == "reject":
            return Command(
                update={"design_approved": False, "approval_notes": decision.get("feedback")},
                goto="revise"
            )
        return Command(
            update={"design_approved": True, "approval_notes": decision.get("feedback", "")},
            goto="implement"
        )
    
    else:  # FULL_REQUIRED
        # Full review - mandatory approval with detailed plan display
        decision = interrupt({
            "type": "full_review",
            "plan": state["implementation_plan"],
            "architecture": state["architectural_notes"],
            "complexity": state["complexity_score"],
            "message": "Full review required. Approve, request revisions, or abort.",
            "options": ["approve", "revise", "abort"]
        })
        
        action = decision.get("action", "abort")
        if action == "approve":
            return Command(
                update={"design_approved": True, "approval_notes": decision.get("feedback", "")},
                goto="implement"
            )
        elif action == "revise":
            return Command(
                update={"design_approved": False, "approval_notes": decision.get("feedback")},
                goto="revise"
            )
        else:
            return Command(
                update={"design_approved": False, "approval_notes": "Aborted by user"},
                goto="abort"
            )
```

---

## Test Enforcement Loop Implements Retry Pattern

Phase 4.5's test enforcement with maximum 3 attempts maps to a conditional edge that loops back to the implementation node when tests fail, with a counter tracking attempts.

```python
MAX_TEST_ATTEMPTS = 3

def test_enforcement_node(state: TaskWrightState) -> dict:
    """Run tests and capture results."""
    test_results = run_tests(state["code_changes"])
    
    return {
        "test_results": test_results,
        "test_attempt_count": state.get("test_attempt_count", 0) + 1
    }

def test_result_router(state: TaskWrightState) -> Literal["review", "retry_implement", "max_attempts_failed"]:
    """Route based on test results and attempt count."""
    results = state["test_results"]
    attempts = state["test_attempt_count"]
    
    if results.get("all_passed"):
        return "review"
    elif attempts >= MAX_TEST_ATTEMPTS:
        return "max_attempts_failed"
    else:
        return "retry_implement"

def retry_implementation_node(state: TaskWrightState) -> dict:
    """Re-implement with test failure context."""
    # Pass test failures to agent for informed retry
    return {
        "agent_context": {
            **state.get("agent_context", {}),
            "test_failures": state["test_results"].get("failures"),
            "retry_attempt": state["test_attempt_count"],
            "instruction": "Fix failing tests based on the error messages provided."
        }
    }

# Graph construction for test loop
builder.add_node("test", test_enforcement_node)
builder.add_node("retry_implement", retry_implementation_node)
builder.add_node("implementation", implementation_node)
builder.add_node("max_attempts_handler", max_attempts_handler)

builder.add_conditional_edges(
    "test",
    test_result_router,
    {
        "review": "review",
        "retry_implement": "retry_implement",
        "max_attempts_failed": "max_attempts_handler"
    }
)
builder.add_edge("retry_implement", "implementation")
```

---

## Design-First Workflow Uses Checkpoint Persistence

The `--design-only` and `--implement-only` flags map naturally to LangGraph's checkpoint/resume pattern. A workflow started with `--design-only` completes Phase 2.8 and stops; `--implement-only` resumes from that checkpoint.

```python
from langgraph.checkpoint.sqlite import SqliteSaver
from pathlib import Path

class TaskWrightCLI:
    def __init__(self, db_path: Path = Path(".taskwright/workflows.db")):
        db_path.parent.mkdir(exist_ok=True)
        self.checkpointer = SqliteSaver.from_conn_string(str(db_path))
        self.graph = self._build_graph()
    
    def _build_graph(self):
        builder = StateGraph(TaskWrightState)
        # ... add all nodes and edges ...
        return builder.compile(checkpointer=self.checkpointer)
    
    def plan(self, task_id: str, description: str, design_only: bool = False):
        """Run planning workflow, optionally stopping after design approval."""
        config = {"configurable": {"thread_id": task_id}}
        
        initial_state = {
            "task_id": task_id,
            "description": description,
            "design_approved": False,
            "test_attempt_count": 0,
        }
        
        if design_only:
            # Run until we hit the design checkpoint, then stop
            for chunk in self.graph.stream(initial_state, config, stream_mode="updates"):
                node_name = list(chunk.keys())[0]
                print(f"✓ {node_name}")
                
                # Stop after design approval
                if node_name == "human_checkpoint":
                    state = self.graph.get_state(config)
                    if state.values.get("design_approved"):
                        print("\n📋 Design approved and saved. Run with --implement-only to continue.")
                        return state.values
        else:
            # Full workflow
            return self.graph.invoke(initial_state, config)
    
    def implement(self, task_id: str):
        """Resume workflow from design checkpoint (--implement-only)."""
        config = {"configurable": {"thread_id": task_id}}
        
        # Check if design was approved
        state = self.graph.get_state(config)
        if not state.values:
            raise ValueError(f"No saved design found for task {task_id}")
        
        if not state.values.get("design_approved"):
            raise ValueError(f"Design not approved for task {task_id}")
        
        print(f"▶️ Resuming implementation for {task_id}...")
        
        # Resume from checkpoint - graph continues from saved state
        return self.graph.invoke(None, config)
    
    def get_pending_reviews(self) -> list[dict]:
        """List all workflows pending human review."""
        # Query checkpointer for interrupted workflows
        pending = []
        # Implementation depends on checkpointer storage schema
        return pending
```

**Days-long persistence** works automatically with SQLite/Postgres checkpointers—state is saved after every node execution and can be resumed from any machine with database access.

---

## Agent Selection with Supervisor Pattern

TaskWright's stack-specific agents (python-api-specialist, react-state-specialist, dotnet-domain-specialist) map to LangGraph's supervisor pattern, where a router node selects the appropriate specialist based on task analysis.

```python
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import tool

# Define specialist agents
SPECIALISTS = {
    "python_api": {
        "capabilities": ["fastapi", "django", "flask", "sqlalchemy", "async"],
        "agent": create_react_agent(
            llm,
            tools=[python_repl, api_tester, db_query],
            prompt="You are a Python API specialist. Focus on FastAPI, async patterns, and clean API design."
        )
    },
    "react_state": {
        "capabilities": ["react", "hooks", "redux", "zustand", "nextjs", "typescript"],
        "agent": create_react_agent(
            llm,
            tools=[npm_runner, lint_tool, bundle_analyzer],
            prompt="You are a React state management specialist. Focus on hooks, context, and state patterns."
        )
    },
    "dotnet_domain": {
        "capabilities": ["csharp", "dotnet", "entityframework", "ddd", "aspnet"],
        "agent": create_react_agent(
            llm,
            tools=[dotnet_cli, nuget_tool],
            prompt="You are a .NET domain specialist. Focus on DDD, clean architecture, and Entity Framework."
        )
    }
}

def agent_selector_node(state: TaskWrightState) -> dict:
    """Select appropriate specialist based on task analysis."""
    
    # Extract stack indicators from plan
    plan = state["implementation_plan"]
    stack_hints = plan.get("tech_stack", [])
    file_patterns = plan.get("affected_files", [])
    
    # Score each specialist
    scores = {}
    for name, spec in SPECIALISTS.items():
        score = sum(1 for cap in spec["capabilities"] 
                   if any(cap.lower() in hint.lower() for hint in stack_hints))
        scores[name] = score
    
    # Select highest scoring specialist
    selected = max(scores, key=scores.get) if max(scores.values()) > 0 else "python_api"
    
    return {
        "selected_agent": selected,
        "agent_context": {
            "stack": stack_hints,
            "files": file_patterns,
            "plan": plan,
            "documentation_level": state.get("documentation_level", "standard")
        }
    }

def implementation_node(state: TaskWrightState) -> dict:
    """Execute implementation with selected specialist agent."""
    agent_name = state["selected_agent"]
    agent = SPECIALISTS[agent_name]["agent"]
    context = state["agent_context"]
    
    # Build agent prompt with context
    task_prompt = f"""
    Implement the following based on the approved plan:
    
    ## Plan
    {context['plan']}
    
    ## Documentation Level: {context['documentation_level']}
    
    ## Files to modify
    {context['files']}
    """
    
    result = agent.invoke({"messages": [("user", task_prompt)]})
    
    return {
        "code_changes": extract_code_changes(result),
        "messages": result["messages"]
    }
```

---

## Claude-Flow Patterns Enhance the Architecture

Three patterns from claude-flow translate particularly well to TaskWright's LangGraph implementation:

### 1. Blackboard Shared State

Use the TypedDict state as a shared blackboard where all agents read/write coordination hints:

```python
class BlackboardState(TypedDict):
    # Coordination namespace (claude-flow pattern)
    coordination_hints: dict  # {"next": "tests → review", "blockers": [...]}
    
    # Artifacts namespace (permanent)
    artifacts: Annotated[list[dict], operator.add]  # Code, docs, test files
    
    # Consensus namespace (approval tracking)
    consensus: dict  # {"design_v1": {"approved": True, "by": "human"}}
    
    # Events namespace (audit trail)
    events: Annotated[list[dict], operator.add]  # All decisions logged
```

### 2. GOAP-Style Planning

For complex tasks, add a planning node that sequences sub-tasks using preconditions/effects:

```python
TASK_ACTIONS = [
    {"id": "analyze_requirements", "pre": [], "effects": ["requirements_clear"]},
    {"id": "design_schema", "pre": ["requirements_clear"], "effects": ["schema_ready"]},
    {"id": "implement_api", "pre": ["schema_ready"], "effects": ["api_ready"]},
    {"id": "write_tests", "pre": ["api_ready"], "effects": ["tests_ready"]},
    {"id": "integrate", "pre": ["tests_ready"], "effects": ["feature_complete"]}
]

def goap_planner(current_state: set, goal_state: set) -> list[str]:
    """A* search to find action sequence reaching goal."""
    # Backward chain from goal, selecting actions whose effects satisfy needs
    plan = []
    needed = goal_state - current_state
    
    while needed:
        for action in TASK_ACTIONS:
            if any(effect in needed for effect in action["effects"]):
                if all(pre in current_state for pre in action["pre"]):
                    plan.append(action["id"])
                    current_state.update(action["effects"])
                    needed = goal_state - current_state
                    break
    return plan
```

### 3. Consensus Checkpoints

Implement multi-stakeholder approval for high-complexity tasks:

```python
def consensus_checkpoint(state: TaskWrightState) -> Command:
    """Gate requiring multiple approvals for complexity 9-10 tasks."""
    if state["complexity_score"] < 9:
        return Command(goto="implement")
    
    # Collect multiple reviews
    votes = interrupt({
        "type": "consensus_review",
        "required_approvers": ["tech_lead", "architect"],
        "threshold": 0.7,  # 70% must approve
        "plan": state["implementation_plan"]
    })
    
    approve_ratio = sum(1 for v in votes.values() if v == "approve") / len(votes)
    
    if approve_ratio >= 0.7:
        return Command(
            update={"consensus": {**state.get("consensus", {}), "design": votes}},
            goto="implement"
        )
    return Command(goto="revise")
```

---

## CLI Integration Pattern for Production Use

TaskWright's CLI commands map to graph invocations with thread-based persistence:

```python
import click
from langgraph.types import Command
from langgraph.checkpoint.sqlite import SqliteSaver

@click.group()
def cli():
    """TaskWright - AI-powered development workflow."""
    pass

@cli.command()
@click.argument('task_id')
@click.option('--design-only', is_flag=True, help='Stop after design approval')
@click.option('--implement-only', is_flag=True, help='Resume from approved design')
def plan(task_id: str, design_only: bool, implement_only: bool):
    """Plan and optionally implement a task."""
    
    with SqliteSaver.from_conn_string(".taskwright/db.sqlite") as checkpointer:
        graph = build_taskwright_graph(checkpointer)
        config = {"configurable": {"thread_id": task_id}}
        
        if implement_only:
            # Resume from design checkpoint
            state = graph.get_state(config)
            if not state.values.get("design_approved"):
                click.echo("❌ Design not approved. Run without --implement-only first.")
                return
            result = graph.invoke(None, config)
        else:
            # Start or continue workflow
            result = run_with_interrupts(graph, task_id, config, stop_after_design=design_only)
        
        display_result(result)

def run_with_interrupts(graph, task_id, config, stop_after_design=False):
    """Run graph, handling interrupts interactively."""
    
    result = graph.invoke({"task_id": task_id}, config)
    
    while "__interrupt__" in result:
        interrupt_data = result["__interrupt__"][0].value
        
        # Display interrupt request
        click.echo(f"\n⏸️  {interrupt_data.get('type', 'Review Required')}")
        if "plan" in interrupt_data:
            click.echo(format_plan(interrupt_data["plan"]))
        
        # Get human decision
        if interrupt_data.get("type") == "quick_review":
            decision = click.prompt("Press Enter to approve, or type feedback", default="")
            response = {"action": "approve"} if not decision else {"action": "reject", "feedback": decision}
        else:
            choice = click.prompt("Decision", type=click.Choice(["approve", "revise", "abort"]))
            feedback = click.prompt("Notes (optional)", default="") if choice != "approve" else ""
            response = {"action": choice, "feedback": feedback}
        
        # Resume with decision
        result = graph.invoke(Command(resume=response), config)
        
        # Stop after design if requested
        if stop_after_design and result.get("design_approved"):
            click.echo("\n✅ Design approved. Run with --implement-only to continue.")
            return result
    
    return result
```

---

## State Schema Design for TaskWright Workflow

The complete state schema captures all information flowing through TaskWright's phases:

```python
from typing import TypedDict, Annotated, Literal, Optional
from langgraph.graph.message import add_messages
from datetime import datetime
import operator

class ImplementationPlan(TypedDict):
    summary: str
    affected_files: list[str]
    tech_stack: list[str]
    estimated_complexity: int
    steps: list[dict]
    risks: list[str]
    test_strategy: str

class TestResult(TypedDict):
    all_passed: bool
    passed_count: int
    failed_count: int
    failures: list[dict]
    coverage: float

class ReviewResult(TypedDict):
    score: float  # 0-10
    feedback: str
    issues: list[dict]
    approved: bool

class TaskWrightState(TypedDict):
    """Complete state schema for TaskWright LangGraph workflow."""
    
    # === Task Metadata ===
    task_id: str
    description: str
    created_at: str
    
    # === Phase 2: Planning ===
    implementation_plan: ImplementationPlan
    
    # === Phase 2.5B: Architectural Review ===
    architectural_notes: str
    architecture_approved: bool
    
    # === Phase 2.7: Complexity Evaluation ===
    complexity_score: int  # 1-10
    complexity_factors: list[str]
    approval_level: Literal["auto", "optional", "required"]
    
    # === Phase 2.8: Human Checkpoint ===
    design_approved: bool
    approval_timestamp: Optional[str]
    approval_notes: str
    
    # === Phase 3: Implementation ===
    selected_agent: str
    agent_context: dict
    code_changes: Annotated[list[dict], operator.add]  # Accumulate changes
    
    # === Phase 4/4.5: Testing ===
    test_results: TestResult
    test_attempt_count: int
    
    # === Phase 5/5.5: Review ===
    review_result: ReviewResult
    final_status: Literal["complete", "failed", "aborted"]
    
    # === Cross-cutting ===
    messages: Annotated[list, add_messages]  # Conversation history
    documentation_level: Literal["minimal", "standard", "comprehensive"]
    events: Annotated[list[dict], operator.add]  # Audit trail
    
    # === Micro-task shortcut ===
    is_micro_task: bool
    micro_task_result: Optional[str]
```

---

## Quick Wins Versus Building from Scratch

| Approach | Timeline | Scope | Effort |
|----------|----------|-------|--------|
| **Quick win: Core workflow** | 2-3 days | Phase 2→2.8→3→4→5 linear flow with SQLite persistence | Low |
| **Quick win: Design-first** | +1 day | Add `--design-only` / `--implement-only` checkpoint pattern | Low |
| **Quick win: Complexity routing** | +1 day | Conditional edges for AUTO/QUICK/FULL approval levels | Low |
| **Medium: Test retry loop** | +2 days | Phase 4.5 enforcement with max attempts counter | Medium |
| **Medium: Agent selection** | +3 days | Supervisor routing to stack-specific specialists | Medium |
| **Advanced: GOAP planning** | +5 days | Goal-oriented task sequencing for complex features | High |
| **Advanced: Multi-agent swarm** | +1 week | Parallel specialist agents with blackboard coordination | High |

**Recommended starting point:** Implement the core 5-node graph (plan → arch_review → complexity → checkpoint → implement) with SQLite persistence. This delivers the design-first workflow with human approval in under a week, providing a foundation to layer on test loops and agent specialization.

---

## Production Deployment Considerations

### For CLI-First Tools Like TaskWright

1. **Use SqliteSaver** for single-user local persistence—workflows survive CLI restarts and can resume days later
2. **Store thread_id in project config** (e.g., `.taskwright/current_task.json`) for seamless `--resume` behavior
3. **Implement streaming** for long operations using `graph.stream(stream_mode="updates")` to show progress
4. **Add retry policies** to LLM nodes to handle transient API failures gracefully
5. **Test with InMemorySaver + FakeListLLM** for deterministic, fast unit tests

### For Team/Server Deployment

1. **Upgrade to PostgresSaver** for multi-user concurrent workflows
2. **Implement external timeout handling** for QUICK_OPTIONAL approvals (LangGraph doesn't have built-in timeouts)
3. **Add FastAPI endpoints** for webhook-based approval UIs
4. **Consider Redis** for sub-millisecond checkpoint performance at scale

The LangGraph architecture enables TaskWright to maintain its lightweight CLI-first philosophy while gaining enterprise-grade persistence, debugging (time-travel), and human-in-the-loop capabilities without requiring a separate orchestration server.

---

## Related Documents

- [TaskWright LangGraph Orchestration: Build Strategy](./TaskWright_LangGraph_Orchestration_Build_Strategy.md)
- [TaskWright Integration with Claude-Flow Orchestration: Feasibility Analysis](./TaskWright_Integration_with_Claude-Flow_Orchestration_Feasibility_Analysis.md)

---

*Generated: November 2025*
*Context: Technical architecture for adding LangGraph-based agent orchestration to TaskWright*
