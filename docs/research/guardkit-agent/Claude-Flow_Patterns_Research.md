# Claude-Flow Patterns Research for AutoBuild Integration

> **Purpose**: Extract proven patterns from claude-flow (10.6k ⭐) to accelerate AutoBuild development without reinventing the wheel.
> **Date**: December 2025

---

## Executive Summary

Claude-flow is an enterprise-grade orchestration platform for Claude with 64 specialized agents, 100+ MCP tools, and sophisticated coordination patterns. Several patterns are directly applicable to AutoBuild's adversarial cooperation model:

| Pattern | Claude-Flow Implementation | AutoBuild Application |
|---------|---------------------------|----------------------|
| **Blackboard** | SQLite `shared_state` table | Player/Coach coordination hints |
| **GOAP Planning** | Goal Module with A* pathfinding | Task sequencing with preconditions |
| **Consensus Gating** | `consensus_state` table for votes | Coach approval as consensus gate |
| **Event Audit Trail** | `events` table for all transitions | Trace logging for debugging |
| **Workflow Checkpointing** | `workflow_state` for resume | LangGraph checkpointing |

---

## 1. Blackboard Pattern (HIGH VALUE FOR AUTOBUILD)

### Claude-Flow Implementation

```
Claude Code ──(MCP client)──> Claude Flow MCP tools
     |                              |
     | hooks + policies             | orchestration API
     v                              v
pre/post scripts <── events ──> memory.db (SQLite)
      ^                            ├─ shared_state  (blackboard)
      |                            ├─ events        (audit)
      |                            ├─ workflow_state (checkpoints)
 artifacts panel                   ├─ consensus_state (votes)
                                   └─ performance_metrics (telemetry)
```

**Key Insight**: Agents write hints to `shared_state` and append actions to `events`. This decouples agents - they don't communicate directly, they communicate via the blackboard.

### Claude-Flow Usage

```javascript
// Agent writes coordination hint with TTL
await mcp__claude-flow__memory_usage({
  action: "store",
  key: "coord/hints",
  value: JSON.stringify({ next: "PRD then routes then tests" }),
  namespace: "shared",
  ttl: 1800  // 30 minute expiry
});

// Another agent reads the hint
const hints = await mcp__claude-flow__memory_usage({
  action: "search",
  namespace: "shared",
  query: "coord/*"
});
```

### AutoBuild Application

The blackboard pattern is **ideal** for Player/Coach coordination:

```python
# guardkit/orchestrator/blackboard.py
from typing import TypedDict, Optional
from datetime import datetime, timedelta

class BlackboardEntry(TypedDict):
    key: str
    value: dict
    namespace: str
    created_at: str
    expires_at: Optional[str]

class Blackboard:
    """
    Shared state for adversarial cooperation.
    
    Namespaces:
    - coordination: Player/Coach hints and current phase
    - artifacts: References to code changes (not full content)
    - feedback: Coach feedback for Player iteration
    - consensus: Approval/rejection decisions
    """
    
    def __init__(self, db_path: str = ".guardkit/blackboard.db"):
        self.db_path = db_path
        self._init_db()
    
    def write(
        self, 
        key: str, 
        value: dict, 
        namespace: str = "coordination",
        ttl_seconds: Optional[int] = None
    ) -> None:
        """Write a hint to the blackboard."""
        expires_at = None
        if ttl_seconds:
            expires_at = (datetime.utcnow() + timedelta(seconds=ttl_seconds)).isoformat()
        
        # SQLite upsert
        # ...
    
    def read(self, key: str, namespace: str = "coordination") -> Optional[dict]:
        """Read a value from the blackboard."""
        # Check TTL, return None if expired
        # ...
    
    def search(self, pattern: str, namespace: str = "coordination") -> list[dict]:
        """Search blackboard by key pattern (glob)."""
        # LIKE query with pattern
        # ...
    
    def sweep_expired(self) -> int:
        """Remove expired entries. Call in maintenance job."""
        # DELETE WHERE expires_at < NOW()
        # ...
```

**Usage in AutoBuild Orchestrator:**

```python
# Player writes its progress
blackboard.write(
    key="player/turn_3/report",
    value={
        "files_modified": ["src/auth.py"],
        "tests_written": ["test_auth"],
        "implementation_notes": "Added OAuth flow"
    },
    namespace="coordination"
)

# Coach reads Player's report
player_report = blackboard.read("player/turn_3/report", namespace="coordination")

# Coach writes feedback
blackboard.write(
    key="coach/turn_3/feedback",
    value={
        "decision": "feedback",
        "items": [{"file": "src/auth.py", "line": 42, "issue": "Missing null check"}]
    },
    namespace="feedback"
)

# Player reads feedback for next iteration
feedback = blackboard.read("coach/turn_3/feedback", namespace="feedback")
```

### Why This Is Better Than Direct State Passing

1. **Decoupling**: Player and Coach don't need to know each other's interfaces
2. **Observability**: All coordination is visible in one place
3. **Debugging**: Can inspect blackboard at any point to understand state
4. **Resume**: Blackboard persists - can resume from any point
5. **Extensibility**: Add new agents (e.g., Reviewer) that read/write same blackboard

---

## 2. GOAP Planning (Goal-Oriented Action Planning)

### Claude-Flow Implementation

From the Goal Module wiki:

```javascript
// GOAP action definitions
const TASK_ACTIONS = [
    { id: "analyze_requirements", pre: [], add: ["requirements_clear"] },
    { id: "design_schema", pre: ["requirements_clear"], add: ["schema_ready"] },
    { id: "implement_api", pre: ["schema_ready"], add: ["api_ready"] },
    { id: "write_tests", pre: ["api_ready"], add: ["tests_ready"] },
    { id: "integrate", pre: ["tests_ready"], add: ["feature_complete"] }
];

// A* planner finds action sequence
function goap_planner(current_state, goal_state) {
    // Backward chain from goal, selecting actions whose effects satisfy needs
    let plan = [];
    let needed = goal_state - current_state;
    
    while (needed.length > 0) {
        for (const action of TASK_ACTIONS) {
            if (action.effects.some(e => needed.includes(e))) {
                if (action.pre.every(p => current_state.includes(p))) {
                    plan.push(action.id);
                    current_state = [...current_state, ...action.effects];
                    needed = goal_state.filter(g => !current_state.includes(g));
                    break;
                }
            }
        }
    }
    return plan;
}
```

### AutoBuild Application

Use GOAP for feature-plan task sequencing:

```python
# guardkit/planning/goap.py
from dataclasses import dataclass
from typing import Set, List

@dataclass
class GOAPAction:
    id: str
    preconditions: Set[str]
    effects: Set[str]
    cost: int = 1

# Define actions for feature development
FEATURE_ACTIONS = [
    GOAPAction("analyze_requirements", set(), {"requirements_understood"}),
    GOAPAction("design_interface", {"requirements_understood"}, {"interface_designed"}),
    GOAPAction("implement_skeleton", {"interface_designed"}, {"skeleton_ready"}),
    GOAPAction("implement_logic", {"skeleton_ready"}, {"logic_implemented"}),
    GOAPAction("write_unit_tests", {"logic_implemented"}, {"unit_tests_ready"}),
    GOAPAction("write_integration_tests", {"unit_tests_ready"}, {"integration_tests_ready"}),
    GOAPAction("code_review", {"integration_tests_ready"}, {"code_reviewed"}),
    GOAPAction("merge", {"code_reviewed"}, {"feature_complete"}),
]

def plan_feature(current_state: Set[str], goal_state: Set[str]) -> List[str]:
    """
    A* backward chaining to find optimal action sequence.
    
    Example:
        current = set()
        goal = {"feature_complete"}
        plan = plan_feature(current, goal)
        # Returns: ["analyze_requirements", "design_interface", ...]
    """
    from heapq import heappush, heappop
    
    # A* search
    queue = [(0, frozenset(current_state), [])]
    visited = set()
    
    while queue:
        cost, state, plan = heappop(queue)
        
        if goal_state.issubset(state):
            return plan
        
        if state in visited:
            continue
        visited.add(state)
        
        for action in FEATURE_ACTIONS:
            if action.preconditions.issubset(state):
                new_state = state | action.effects
                new_plan = plan + [action.id]
                new_cost = cost + action.cost
                heappush(queue, (new_cost, frozenset(new_state), new_plan))
    
    return []  # No valid plan found
```

**Integration with Enhanced feature-plan:**

```python
# In feature-plan command
def generate_task_sequence(feature_description: str) -> List[Task]:
    # AI analyzes feature to determine what's already done
    current_state = analyze_codebase_state(feature_description)
    
    # Goal is always feature_complete
    goal_state = {"feature_complete"}
    
    # GOAP planner finds optimal sequence
    action_sequence = plan_feature(current_state, goal_state)
    
    # Convert actions to tasks
    tasks = []
    for action_id in action_sequence:
        task = create_task_for_action(action_id, feature_description)
        tasks.append(task)
    
    # Identify parallelizable tasks (same preconditions, no conflicts)
    parallel_groups = group_parallel_tasks(tasks, action_sequence)
    
    return tasks, parallel_groups
```

---

## 3. Consensus Gating

### Claude-Flow Implementation

Critical transitions require multiple votes:

```javascript
// Write consensus record
await mcp__claude-flow__memory_usage({
    action: "store",
    key: "consensus:auth_api:v3",
    value: JSON.stringify({
        decision: "merge",
        votes: ["Lead", "Impl", "QA"],
        timestamp: new Date().toISOString()
    }),
    namespace: "consensus"
});

// Gate on consensus
const consensus = await mcp__claude-flow__memory_usage({
    action: "search",
    namespace: "consensus",
    query: "consensus:auth_api:*"
});

if (consensus.votes.length >= QUORUM) {
    await merge();
}
```

### AutoBuild Application

In AutoBuild, the **Coach IS the consensus mechanism**. But we can extend this for:

1. **Multi-reviewer scenarios** (future: human + AI review)
2. **Escalation votes** (when to escalate to human)
3. **Quality gates** (must pass N checks before approval)

```python
# guardkit/orchestrator/consensus.py
from dataclasses import dataclass
from typing import List, Literal
from enum import Enum

class VoteType(Enum):
    APPROVE = "approve"
    REJECT = "reject"
    ABSTAIN = "abstain"

@dataclass
class Vote:
    voter: str  # "coach", "human", "linter", "tests"
    vote: VoteType
    rationale: str
    timestamp: str

@dataclass
class ConsensusGate:
    gate_id: str
    required_approvals: int
    votes: List[Vote]
    
    def is_passed(self) -> bool:
        approvals = sum(1 for v in self.votes if v.vote == VoteType.APPROVE)
        return approvals >= self.required_approvals
    
    def is_blocked(self) -> bool:
        rejections = sum(1 for v in self.votes if v.vote == VoteType.REJECT)
        # Any rejection blocks (for now)
        return rejections > 0

# Usage in orchestrator
async def execute_coach(state: AutoBuildState) -> dict:
    # ... coach validation ...
    
    # Record vote in consensus
    gate = ConsensusGate(
        gate_id=f"task:{state['task_id']}:turn:{state['turn_count']}",
        required_approvals=1,  # Just coach for now
        votes=[]
    )
    
    vote = Vote(
        voter="coach",
        vote=VoteType.APPROVE if approved else VoteType.REJECT,
        rationale=coach_feedback["rationale"],
        timestamp=datetime.utcnow().isoformat()
    )
    gate.votes.append(vote)
    
    # Write to blackboard
    blackboard.write(
        key=f"consensus/{gate.gate_id}",
        value=asdict(gate),
        namespace="consensus"
    )
    
    return {"coach_decision": "approve" if gate.is_passed() else "feedback"}
```

---

## 4. OODA Loop Integration

### Claude-Flow's OODA Mapping

```
Observe → query events, performance_metrics, and recent artifacts
Orient  → reduce to a bundle and compare to patterns
Decide  → write candidate record into consensus_state, gate on votes
Act     → orchestrate task and record event
```

### AutoBuild Application

Map OODA to the adversarial loop:

```python
# Each turn of the adversarial loop is an OODA cycle

class OODAPhase(Enum):
    OBSERVE = "observe"   # Gather context for this turn
    ORIENT = "orient"     # Analyze requirements + previous feedback
    DECIDE = "decide"     # Player implements OR Coach validates
    ACT = "act"           # Execute the decision

async def execute_turn(state: AutoBuildState, phase: str) -> dict:
    """
    OODA-structured turn execution.
    """
    if state["phase"] == "player_implementing":
        # OBSERVE: Query what's needed
        context = await observe_for_player(state)
        
        # ORIENT: Compare to patterns, reduce context
        oriented_context = orient_player_context(context, state["feedback_history"])
        
        # DECIDE: Generate implementation plan
        # (Player decides HOW to implement)
        
        # ACT: Execute implementation
        result = await execute_player(state, oriented_context)
        
        # Record event
        blackboard.write(
            key=f"event/turn_{state['turn_count']}/player",
            value=result,
            namespace="events"
        )
        
    elif state["phase"] == "coach_validating":
        # OBSERVE: Query player's work
        context = await observe_for_coach(state)
        
        # ORIENT: Compare to requirements
        oriented_context = orient_coach_context(context, state["requirements"])
        
        # DECIDE: Approve or provide feedback
        decision = await execute_coach(state, oriented_context)
        
        # ACT: Record decision in consensus
        blackboard.write(
            key=f"consensus/turn_{state['turn_count']}",
            value=decision,
            namespace="consensus"
        )
```

---

## 5. Event Audit Trail

### Claude-Flow Implementation

Every state transition is recorded:

```javascript
// Record event after any action
await mcp__claude-flow__memory_usage({
    action: "store",
    key: `events:${Date.now()}`,
    value: JSON.stringify({
        task: "auth",
        status: "complete",
        actor: "coder",
        transition: "implementing → testing"
    }),
    namespace: "events"
});
```

### AutoBuild Application

This maps directly to our tracing system but with richer structure:

```python
# guardkit/orchestrator/events.py
from dataclasses import dataclass, asdict
from typing import Optional, Any
from datetime import datetime
import json

@dataclass
class WorkflowEvent:
    event_id: str
    task_id: str
    event_type: str  # "player_start", "player_report", "coach_decision", etc.
    actor: str       # "player", "coach", "orchestrator"
    transition: str  # "implementing → validating"
    data: dict
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.utcnow().isoformat()

class EventLog:
    """Append-only event log for audit and replay."""
    
    def __init__(self, blackboard: Blackboard):
        self.blackboard = blackboard
    
    def record(self, event: WorkflowEvent) -> None:
        """Record an event to the log."""
        self.blackboard.write(
            key=f"event/{event.event_id}",
            value=asdict(event),
            namespace="events",
            ttl_seconds=2592000  # 30 days retention
        )
    
    def replay(self, task_id: str) -> list[WorkflowEvent]:
        """Replay all events for a task (for debugging)."""
        events = self.blackboard.search(f"event/*", namespace="events")
        return [
            WorkflowEvent(**e) for e in events 
            if e.get("task_id") == task_id
        ]
    
    def get_transition_history(self, task_id: str) -> list[str]:
        """Get sequence of phase transitions."""
        events = self.replay(task_id)
        return [e.transition for e in events if e.transition]
```

---

## 6. Memory Schema (Adapted for AutoBuild)

### Claude-Flow's 12 Tables

```sql
-- Core coordination tables
shared_state     -- Current hive status and configuration
events           -- Inter-agent communication logs
task_history     -- Completed tasks and outcomes
decision_tree    -- Decision-making patterns and rationale

-- Performance and learning tables
performance_metrics  -- Execution time, success rates
neural_patterns      -- Learned coordination patterns
code_patterns        -- Successful code implementations
error_patterns       -- Common mistakes and solutions

-- Project context tables
project_context  -- Current project state
file_changes     -- Tracked file modifications
dependencies     -- Project dependencies
documentation    -- Generated docs
```

### AutoBuild Simplified Schema

```sql
-- guardkit/orchestrator/schema.sql

-- Blackboard (shared state)
CREATE TABLE blackboard (
    key TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,
    value TEXT NOT NULL,  -- JSON
    created_at TEXT NOT NULL,
    expires_at TEXT,
    INDEX idx_namespace (namespace),
    INDEX idx_expires (expires_at)
);

-- Event log
CREATE TABLE events (
    event_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    actor TEXT NOT NULL,
    transition TEXT,
    data TEXT NOT NULL,  -- JSON
    timestamp TEXT NOT NULL,
    INDEX idx_task (task_id),
    INDEX idx_type (event_type)
);

-- Consensus gates
CREATE TABLE consensus (
    gate_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    required_approvals INTEGER NOT NULL,
    votes TEXT NOT NULL,  -- JSON array
    status TEXT NOT NULL,  -- "pending", "passed", "blocked"
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    INDEX idx_task (task_id),
    INDEX idx_status (status)
);

-- Workflow checkpoints (for resume)
CREATE TABLE checkpoints (
    checkpoint_id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL,
    state TEXT NOT NULL,  -- JSON serialized LangGraph state
    created_at TEXT NOT NULL,
    UNIQUE(task_id)  -- One checkpoint per task
);

-- Patterns learned (future: for optimization)
CREATE TABLE patterns (
    pattern_id TEXT PRIMARY KEY,
    pattern_type TEXT NOT NULL,  -- "success", "failure", "escalation"
    context TEXT NOT NULL,  -- JSON
    outcome TEXT NOT NULL,  -- JSON
    confidence REAL NOT NULL,
    created_at TEXT NOT NULL,
    INDEX idx_type (pattern_type)
);
```

---

## 7. Hooks System

### Claude-Flow's Hook Types

```json
{
  "hooks": {
    "PreToolUse": [{"command": "node", "args": ["scripts/build_bundle.js"]}],
    "PostToolUse": [{"command": "node", "args": ["scripts/persist_outcomes.js"]}],
    "SessionStart": [{"command": "node", "args": ["scripts/session_start.js"]}],
    "SessionEnd": [{"command": "node", "args": ["scripts/session_end.js"]}]
  }
}
```

### AutoBuild Application

We already have hooks via LangGraph nodes, but we can add explicit hook points:

```python
# guardkit/orchestrator/hooks.py
from typing import Callable, Dict, Any
from enum import Enum

class HookType(Enum):
    PRE_PLAYER = "pre_player"      # Before player executes
    POST_PLAYER = "post_player"    # After player reports
    PRE_COACH = "pre_coach"        # Before coach validates
    POST_COACH = "post_coach"      # After coach decision
    PRE_MERGE = "pre_merge"        # Before worktree merge
    POST_MERGE = "post_merge"      # After successful merge
    ON_ESCALATE = "on_escalate"    # When escalating to human

HookCallback = Callable[[Dict[str, Any]], Dict[str, Any]]

class HookRegistry:
    """Registry for workflow hooks."""
    
    def __init__(self):
        self._hooks: Dict[HookType, list[HookCallback]] = {
            hook_type: [] for hook_type in HookType
        }
    
    def register(self, hook_type: HookType, callback: HookCallback) -> None:
        """Register a hook callback."""
        self._hooks[hook_type].append(callback)
    
    async def execute(self, hook_type: HookType, context: dict) -> dict:
        """Execute all hooks of a type, passing context through chain."""
        for callback in self._hooks[hook_type]:
            context = await callback(context)
        return context

# Example usage
hooks = HookRegistry()

# Register quality gate hook
@hooks.register(HookType.PRE_MERGE)
async def quality_gate(context: dict) -> dict:
    """Run linting and type checking before merge."""
    result = await run_quality_checks(context["worktree_path"])
    if not result.passed:
        raise QualityGateError(result.errors)
    return context

# Register notification hook
@hooks.register(HookType.POST_COACH)
async def notify_on_decision(context: dict) -> dict:
    """Log coach decisions for observability."""
    logger.info(f"Coach decision: {context['decision']} for {context['task_id']}")
    return context
```

---

## 8. Topology Patterns

### Claude-Flow Topologies

- **Hierarchical**: Queen coordinator → specialized workers
- **Mesh**: All agents can communicate directly
- **Star**: Central coordinator, workers only talk to center
- **Ring**: Pass-through coordination

### AutoBuild Application

For now, we use a **fixed hierarchical** topology:

```
Orchestrator (Queen)
    ├── Player (Worker - Implementation)
    └── Coach (Worker - Validation)
```

Future expansion could add:

```
Orchestrator (Queen)
    ├── Player (Implementation)
    ├── Coach (Validation)
    ├── Linter (Quality - automated)
    ├── Tester (Test execution - automated)
    └── Human (Escalation)
```

---

## 9. Integration Recommendations

### What to Adopt from Claude-Flow

| Pattern | Priority | Effort | Value |
|---------|----------|--------|-------|
| **Blackboard for coordination** | P0 | Low | High - decouples agents |
| **Event audit trail** | P0 | Low | High - debugging essential |
| **SQLite persistence** | P0 | Low | High - resume capability |
| **GOAP for task planning** | P1 | Medium | Medium - better sequencing |
| **Consensus gates** | P1 | Low | Medium - extensibility |
| **Hook registry** | P2 | Low | Low - nice to have |
| **Namespace isolation** | P2 | Low | Low - cleaner organization |

### What NOT to Adopt

| Pattern | Reason |
|---------|--------|
| 64 agent types | Overkill - we have 2 agents (Player/Coach) |
| MCP tool server | Not needed - using Claude Agent SDK directly |
| Neural learning | Future consideration, not Phase 1 |
| Hive-mind topology | Fixed Player/Coach is sufficient |
| AgentDB vector search | Overkill for task coordination |

### Implementation Order

1. **Add Blackboard class** (1 day)
   - SQLite-backed shared state
   - Namespace support
   - TTL expiration

2. **Integrate with Orchestrator** (1 day)
   - Player writes reports to blackboard
   - Coach reads from blackboard
   - Replace direct state passing

3. **Add Event Log** (0.5 day)
   - Record all transitions
   - Enable replay for debugging

4. **Add Consensus Gates** (0.5 day)
   - Coach approval as consensus
   - Extensible for future reviewers

5. **GOAP for feature-plan** (2 days)
   - Action definitions
   - A* planner
   - Parallel group detection

---

## 10. Code Examples: Integrating Blackboard with AutoBuild

### Modified Orchestrator State

```python
# guardkit/orchestrator/state.py
from typing import TypedDict, Annotated, Literal, Optional, List

class AutoBuildState(TypedDict):
    # Task identification
    task_id: str
    feature_id: Optional[str]
    
    # Requirements (immutable)
    requirements: dict
    
    # Loop tracking
    turn_count: int
    max_turns: int
    
    # Phase (OODA-aligned)
    phase: Literal[
        "observing",      # Gathering context
        "orienting",      # Analyzing requirements/feedback
        "deciding",       # Player implementing OR Coach validating
        "acting",         # Executing decision
        "complete",
        "failed",
        "escalated"
    ]
    
    # Blackboard keys (references, not full data)
    player_report_key: Optional[str]   # "player/turn_3/report"
    coach_feedback_key: Optional[str]  # "coach/turn_3/feedback"
    consensus_key: Optional[str]       # "consensus/turn_3"
    
    # Outcome
    success: Optional[bool]
    failure_reason: Optional[str]
```

### Modified Player Node

```python
# guardkit/orchestrator/nodes.py

async def execute_player(state: AutoBuildState, blackboard: Blackboard) -> dict:
    """Run player with blackboard coordination."""
    task_id = state["task_id"]
    turn = state["turn_count"]
    
    # OBSERVE: Read previous feedback from blackboard (if any)
    feedback = None
    if state.get("coach_feedback_key"):
        feedback = blackboard.read(state["coach_feedback_key"], namespace="feedback")
    
    # ORIENT: Build minimal context bundle
    context = {
        "requirements": state["requirements"],
        "previous_feedback": feedback,
        "turn": turn
    }
    
    # DECIDE + ACT: Execute player
    session = await agent_wrapper.create_session(worktree_path)
    prompt = build_player_prompt(context)
    result = await agent_wrapper.execute(session, prompt)
    
    # Write report to blackboard
    report_key = f"player/turn_{turn}/report"
    blackboard.write(
        key=report_key,
        value=parse_player_output(result.output),
        namespace="coordination"
    )
    
    # Record event
    event_log.record(WorkflowEvent(
        event_id=f"{task_id}_player_{turn}",
        task_id=task_id,
        event_type="player_report",
        actor="player",
        transition="implementing → validating",
        data={"report_key": report_key}
    ))
    
    return {
        "player_report_key": report_key,
        "turn_count": turn + 1,
        "phase": "coach_validating"
    }

async def execute_coach(state: AutoBuildState, blackboard: Blackboard) -> dict:
    """Run coach with blackboard coordination."""
    task_id = state["task_id"]
    turn = state["turn_count"]
    
    # OBSERVE: Read player report from blackboard
    player_report = blackboard.read(
        state["player_report_key"], 
        namespace="coordination"
    )
    
    # ORIENT: Compare to requirements
    context = {
        "requirements": state["requirements"],
        "player_report": player_report,
        "turn": turn
    }
    
    # DECIDE + ACT: Execute coach
    session = await agent_wrapper.create_session(worktree_path)
    prompt = build_coach_prompt(context)
    result = await agent_wrapper.execute(session, prompt)
    
    coach_output = parse_coach_output(result.output)
    
    # Write feedback to blackboard
    feedback_key = f"coach/turn_{turn}/feedback"
    blackboard.write(
        key=feedback_key,
        value=coach_output,
        namespace="feedback"
    )
    
    # Record consensus
    consensus_key = f"consensus/turn_{turn}"
    blackboard.write(
        key=consensus_key,
        value={
            "decision": coach_output["decision"],
            "votes": [{"voter": "coach", "vote": coach_output["decision"]}],
            "rationale": coach_output["rationale"]
        },
        namespace="consensus"
    )
    
    # Record event
    event_log.record(WorkflowEvent(
        event_id=f"{task_id}_coach_{turn}",
        task_id=task_id,
        event_type="coach_decision",
        actor="coach",
        transition="validating → " + ("complete" if coach_output["decision"] == "approve" else "implementing"),
        data={"consensus_key": consensus_key}
    ))
    
    return {
        "coach_feedback_key": feedback_key,
        "consensus_key": consensus_key,
        "coach_decision": coach_output["decision"],
        "phase": "complete" if coach_output["decision"] == "approve" else "implementing"
    }
```

---

## References

- [Claude-Flow Repository](https://github.com/ruvnet/claude-flow) - 10.6k ⭐
- [Claude-Flow Wiki - Memory System](https://github.com/ruvnet/claude-flow/wiki/Memory-System)
- [Claude-Flow Wiki - Goal Module (GOAP)](https://github.com/ruvnet/claude-flow/wiki/Goal-Module)
- [Claude-Flow Playbook Gist](https://gist.github.com/ruvnet/9b066e77dd2980bfdcc5adf3bc082281)
- [Orkin's GOAP Paper (F.E.A.R.)](https://www.gamedevs.org/uploads/three-states-plan-ai-of-fear.pdf)
- [OODA Loop](https://en.wikipedia.org/wiki/OODA_loop)
