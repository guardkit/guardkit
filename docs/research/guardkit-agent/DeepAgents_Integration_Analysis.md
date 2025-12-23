# DeepAgents Integration Analysis for AutoBuild

> **Discovery**: LangChain's DeepAgents (5.8k ⭐) provides a pre-built agent harness with planning, filesystem, and subagent capabilities - exactly what AutoBuild needs.
> **Date**: December 2025
> **Recommendation**: **Adopt DeepAgents as foundation** - saves ~4.5 days and provides battle-tested infrastructure.

---

## Executive Summary

DeepAgents is an official LangChain package that implements the patterns we were planning to build from scratch:

| AutoBuild Component | DeepAgents Equivalent | Build vs Use |
|---------------------|----------------------|--------------|
| Agent SDK (F2) | Built into LangChain | **Use** |
| Blackboard (F7) | FilesystemMiddleware | **Use** |
| Player/Coach Agents | SubAgentMiddleware | **Adapt** |
| Planning | TodoListMiddleware | **Enhance** |
| HITL Approval | HumanInTheLoopMiddleware | **Use** |
| Orchestrator (F5) | create_deep_agent | **Extend** |

**Net impact**: Reduce implementation time by ~4.5 days while gaining battle-tested infrastructure from the LangChain team.

---

## What DeepAgents Provides

### Core Middleware Stack (Auto-attached)

```python
from deepagents import create_deep_agent

agent = create_deep_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[...],
    system_prompt="...",
    subagents=[...],
)
# Automatically includes:
# 1. TodoListMiddleware - Planning/task tracking
# 2. FilesystemMiddleware - Context offloading
# 3. SubAgentMiddleware - Isolated subagent delegation
# 4. SummarizationMiddleware - Auto-summarize at 170K tokens
# 5. HumanInTheLoopMiddleware - Tool-level approval gates
```

### 1. TodoListMiddleware (Planning)

```python
# Provides write_todos tool for task decomposition
# Agent can create, update, and track task lists
# Similar to our feature-plan but more dynamic
```

**Comparison with our Enhanced feature-plan (F1)**:
- DeepAgents: Runtime todo management
- Our plan: Upfront YAML feature file with dependencies

**Recommendation**: Keep our YAML format for structured features, use TodoListMiddleware for within-task planning.

### 2. FilesystemMiddleware (Context Management)

```python
# Provides: ls, read_file, write_file, edit_file, glob, grep
# Backends: StateBackend (ephemeral), StoreBackend (persistent), FilesystemBackend (real disk)
# Auto-saves large tool results (>20K tokens) to files

from deepagents.middleware import FilesystemMiddleware
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

# Hybrid: ephemeral + persistent /coordination/ path
backend = CompositeBackend(
    default=StateBackend(),
    routes={"/coordination/": StoreBackend(store)}
)
```

**This IS our Blackboard pattern!** The FilesystemMiddleware with CompositeBackend provides:
- Namespace isolation via path routing
- Persistent storage for coordination
- Ephemeral storage for working state

### 3. SubAgentMiddleware (Agent Spawning)

```python
# Define subagents with isolated context
player_subagent = {
    "name": "player",
    "description": "Implementation-focused agent",
    "system_prompt": PLAYER_INSTRUCTIONS,
    "tools": [implementation_tools],
    "model": "claude-3-5-haiku-20241022",  # Cost-efficient
}

coach_subagent = {
    "name": "coach", 
    "description": "Validation-focused agent",
    "system_prompt": COACH_INSTRUCTIONS,
    "tools": [validation_tools],
    "model": "claude-sonnet-4-5-20250929",  # Better reasoning
}

agent = create_deep_agent(
    subagents=[player_subagent, coach_subagent],
    ...
)
```

**Key Insight**: Player and Coach can be DeepAgents subagents with:
- Context isolation (clean context window for main orchestrator)
- Custom models per agent
- Custom tools per agent
- Custom middleware per subagent

### 4. HumanInTheLoopMiddleware (Approval Gates)

```python
agent = create_deep_agent(
    tools=[...],
    interrupt_on={
        "merge_worktree": {
            "allowed_decisions": ["approve", "edit", "reject"]
        },
        "complete_task": {
            "allowed_decisions": ["approve", "reject"]
        },
    }
)
```

**This replaces our Consensus Gates!** Native HITL support with:
- Tool-level interrupts
- Configurable decisions (approve/edit/reject)
- LangGraph checkpoint integration

---

## Architecture Comparison

### Original AutoBuild Architecture

```
┌─────────────────────────────────────────────────┐
│              AutoBuild Orchestrator             │
│                  (LangGraph)                    │
├─────────────────────────────────────────────────┤
│  ┌─────────┐    ┌─────────┐    ┌───────────┐   │
│  │  Player │◄──►│  Coach  │◄──►│ Blackboard│   │
│  │  Agent  │    │  Agent  │    │  (SQLite) │   │
│  └─────────┘    └─────────┘    └───────────┘   │
├─────────────────────────────────────────────────┤
│         Agent SDK Wrapper (Custom)              │
├─────────────────────────────────────────────────┤
│           Claude Agent SDK / LangGraph          │
└─────────────────────────────────────────────────┘
```

### DeepAgents-Based Architecture

```
┌─────────────────────────────────────────────────┐
│              create_deep_agent()                │
│                (DeepAgents)                     │
├─────────────────────────────────────────────────┤
│  Middleware Stack (Auto-attached):              │
│  ┌─────────────────────────────────────────┐   │
│  │ TodoListMiddleware (planning)           │   │
│  │ FilesystemMiddleware (blackboard)       │◄──┼── Replaces F7
│  │ SubAgentMiddleware (player/coach)       │◄──┼── Simplifies F3, F4
│  │ SummarizationMiddleware (context mgmt)  │   │
│  │ HumanInTheLoopMiddleware (consensus)    │   │
│  │ AdversarialLoopMiddleware (CUSTOM)      │◄──┼── Our addition
│  └─────────────────────────────────────────┘   │
├─────────────────────────────────────────────────┤
│    Subagents:                                   │
│    ┌─────────┐         ┌─────────┐             │
│    │ Player  │         │  Coach  │             │
│    │(haiku)  │         │(sonnet) │             │
│    └─────────┘         └─────────┘             │
├─────────────────────────────────────────────────┤
│           LangGraph + LangChain                 │
└─────────────────────────────────────────────────┘
```

---

## What We Still Need to Build

### Must Build (DeepAgents doesn't provide)

1. **AdversarialLoopMiddleware** - Custom middleware for Player ↔ Coach loop
2. **Enhanced feature-plan (F1)** - YAML feature files with dependencies
3. **Git Worktree Management** - Parallel task isolation
4. **GuardKit CLI (F6)** - User-facing commands
5. **Agent Instructions** - Player and Coach prompts

### Can Reuse from DeepAgents

1. ~~Agent SDK Wrapper (F2)~~ → SubAgentMiddleware
2. ~~Blackboard (F7)~~ → FilesystemMiddleware
3. ~~Consensus Gates~~ → HumanInTheLoopMiddleware
4. ~~Context Management~~ → SummarizationMiddleware
5. ~~Event Logging~~ → LangGraph tracing

---

## Revised Feature List

### Features to Keep (Modified)

| Feature | Original Effort | Revised Effort | Notes |
|---------|-----------------|----------------|-------|
| **F1: Enhanced feature-plan** | 2-3 days | 2-3 days | No change |
| **F2: Agent SDK** | 2-3 days | **0.5 days** | Just configure DeepAgents |
| **F3: Player Agent** | 1-2 days | **1 day** | SubAgent definition + prompt |
| **F4: Coach Agent** | 1-2 days | **1 day** | SubAgent definition + prompt |
| **F5: Orchestrator** | 2-3 days | 2-3 days | Custom middleware on DeepAgents |
| **F6: CLI** | 1-2 days | 1-2 days | No change |
| **F7: Blackboard** | 2 days | **0 days** | Use FilesystemMiddleware |

### New Component

| Component | Effort | Notes |
|-----------|--------|-------|
| **AdversarialLoopMiddleware** | 1-2 days | Custom middleware for Player/Coach loop |

### Timeline Comparison

**Original**: 12-17 days
**With DeepAgents**: 8-12 days
**Savings**: ~4-5 days

---

## Implementation Plan (Revised)

### Week 1 (5 days)

```
Day 1-2: F1 Enhanced feature-plan
├── YAML schema (unchanged)
├── DependencyAnalyzer
├── ComplexityAnalyzer
└── --structured flag

Day 3: DeepAgents Setup (replaces F2)
├── pip install deepagents
├── Configure FilesystemMiddleware backend
├── Set up CompositeBackend for coordination
└── Basic create_deep_agent working

Day 4-5: F3 + F4 Player and Coach
├── Player SubAgent definition
├── Player instructions (.md)
├── Coach SubAgent definition
├── Coach instructions (.md)
└── Test subagent invocation
```

### Week 2 (5 days)

```
Day 1-2: AdversarialLoopMiddleware (NEW)
├── Custom middleware extending AgentMiddleware
├── Loop state tracking
├── Player → Coach → Player routing
├── Max turns and escalation logic
└── Integration with FilesystemMiddleware

Day 3-4: F5 Orchestrator Integration
├── Wire AdversarialLoopMiddleware into create_deep_agent
├── Configure HITL for approval gates
├── Git worktree integration
└── End-to-end single task test

Day 5: F6 CLI
├── guardkit autobuild task
├── guardkit autobuild feature
├── Progress display
└── Resume capability
```

### Week 3 (2 days)

```
Day 1-2: Integration Testing + Polish
├── Full workflow tests
├── Error handling
├── Documentation
└── Demo preparation
```

---

## Code Examples

### DeepAgents-Based Orchestrator

```python
# guardkit/orchestrator/deepagent_orchestrator.py
from deepagents import create_deep_agent
from deepagents.middleware import FilesystemMiddleware
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend
from langgraph.store.memory import InMemoryStore

from guardkit.orchestrator.middleware import AdversarialLoopMiddleware
from guardkit.agents.player import PLAYER_INSTRUCTIONS, player_tools
from guardkit.agents.coach import COACH_INSTRUCTIONS, coach_tools

def create_autobuild_agent(store=None):
    """Create the AutoBuild orchestrator using DeepAgents."""
    
    if store is None:
        store = InMemoryStore()
    
    # Player subagent (cost-efficient model)
    player_subagent = {
        "name": "player",
        "description": "Implementation agent that writes code to satisfy requirements",
        "system_prompt": PLAYER_INSTRUCTIONS,
        "tools": player_tools,
        "model": "anthropic:claude-3-5-haiku-20241022",
    }
    
    # Coach subagent (better reasoning)
    coach_subagent = {
        "name": "coach",
        "description": "Validation agent that reviews implementation against requirements",
        "system_prompt": COACH_INSTRUCTIONS,
        "tools": coach_tools,
        "model": "anthropic:claude-sonnet-4-5-20250929",
    }
    
    # Custom filesystem backend with coordination namespace
    def backend_factory(runtime):
        return CompositeBackend(
            default=StateBackend(runtime),
            routes={
                "/coordination/": StoreBackend(runtime),  # Persistent
                "/artifacts/": StoreBackend(runtime),     # Persistent
            }
        )
    
    # Create the deep agent with our custom middleware
    agent = create_deep_agent(
        model="anthropic:claude-sonnet-4-5-20250929",
        tools=[],  # Orchestrator doesn't need tools - delegates to subagents
        system_prompt=ORCHESTRATOR_INSTRUCTIONS,
        subagents=[player_subagent, coach_subagent],
        store=store,
        middleware=[
            AdversarialLoopMiddleware(
                player_name="player",
                coach_name="coach",
                max_turns=5,
                coordination_path="/coordination/",
            ),
        ],
        interrupt_on={
            # Require approval before completing task
            "complete_task": {"allowed_decisions": ["approve", "reject"]},
            # Require approval before escalating
            "escalate": {"allowed_decisions": ["approve", "reject"]},
        },
    )
    
    return agent
```

### AdversarialLoopMiddleware

```python
# guardkit/orchestrator/middleware.py
from langchain.agents.middleware import AgentMiddleware
from typing import Any

class AdversarialLoopMiddleware(AgentMiddleware):
    """
    Custom middleware implementing the adversarial cooperation pattern.
    
    Routes tasks through Player → Coach → Player loop until:
    - Coach approves (success)
    - Max turns reached (failure/escalation)
    - Critical issue detected (escalation)
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
    def tools(self):
        """Provide adversarial loop control tools."""
        return [
            self.start_adversarial_task,
            self.get_loop_status,
            self.complete_task,
            self.escalate,
        ]
    
    def start_adversarial_task(
        self,
        task_id: str,
        requirements: dict,
    ) -> str:
        """
        Start an adversarial task loop.
        
        Args:
            task_id: Unique task identifier
            requirements: Task requirements from feature-plan
        
        Returns:
            Status message
        """
        # Initialize loop state in filesystem
        # This will be persisted via FilesystemMiddleware
        return f"Started adversarial task {task_id}"
    
    def get_loop_status(self, task_id: str) -> dict:
        """Get current status of an adversarial loop."""
        # Read from coordination filesystem
        pass
    
    def complete_task(self, task_id: str, summary: str) -> str:
        """
        Mark task as complete (requires HITL approval).
        
        This tool is configured with interrupt_on, so it will
        pause for human approval before executing.
        """
        pass
    
    def escalate(self, task_id: str, reason: str) -> str:
        """
        Escalate task to human (requires HITL approval).
        """
        pass
    
    def modify_model_request(self, request, runtime):
        """Inject adversarial loop instructions into system prompt."""
        adversarial_instructions = f"""
## Adversarial Task Execution

When executing a task, follow this pattern:

1. Call `start_adversarial_task` with the task requirements
2. Delegate to `{self.player_name}` subagent for implementation
3. Write player's report to {self.coordination_path}player/
4. Delegate to `{self.coach_name}` subagent for validation
5. Read coach's decision from {self.coordination_path}coach/
6. If approved: call `complete_task`
7. If feedback: repeat from step 2 (max {self.max_turns} turns)
8. If max turns reached: call `escalate`

CRITICAL: Player and Coach must NOT communicate directly.
All coordination happens through the filesystem at {self.coordination_path}.
"""
        # Append to system prompt
        request.system_prompt += adversarial_instructions
        return request
```

### Using FilesystemMiddleware as Blackboard

```python
# In Player subagent prompt:
"""
After implementing, write your report to:
/coordination/player/turn_{turn}/report.json

Format:
{
  "files_modified": ["path/to/file.py"],
  "tests_written": ["test_feature.py"],
  "implementation_notes": "...",
  "concerns": []
}
"""

# In Coach subagent prompt:
"""
Read the player's report from:
/coordination/player/turn_{turn}/report.json

After validation, write your decision to:
/coordination/coach/turn_{turn}/decision.json

Format:
{
  "decision": "approve" | "feedback",
  "rationale": "...",
  "feedback_items": [...]  # If decision is "feedback"
}
"""
```

---

## Risk Assessment

### Risks of Adopting DeepAgents

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| API changes in DeepAgents | Medium | Medium | Pin version, wrap in adapter |
| Middleware limitations | Low | Medium | Can extend/override middleware |
| Learning curve | Low | Low | Good documentation, same LangGraph base |
| Less control | Medium | Low | Can use individual middleware |
| Version coupling | Medium | Low | DeepAgents is from LangChain, stable |

### Risks of NOT Adopting DeepAgents

| Risk | Likelihood | Impact | Notes |
|------|------------|--------|-------|
| Reinventing the wheel | High | Medium | Building what already exists |
| More bugs | Medium | Medium | Less tested than DeepAgents |
| Missing features | Medium | Medium | No auto-summarization, etc. |
| Slower delivery | High | High | 4-5 extra days |

---

## Recommendation

### Adopt DeepAgents with Custom Extensions

**Confidence: High**

1. **Use `create_deep_agent`** as the foundation
2. **Use `FilesystemMiddleware`** with CompositeBackend for coordination (replaces Blackboard)
3. **Use `SubAgentMiddleware`** for Player and Coach (simplifies agent creation)
4. **Use `HumanInTheLoopMiddleware`** for approval gates (replaces Consensus)
5. **Build `AdversarialLoopMiddleware`** as custom extension (our innovation)
6. **Keep Enhanced feature-plan (F1)** unchanged (our structured YAML)
7. **Keep CLI (F6)** unchanged (GuardKit integration)

### Benefits

- **4-5 days saved** on infrastructure
- **Battle-tested middleware** from LangChain team
- **Free context summarization** (170K token handling)
- **Active maintenance** from LangChain
- **Same LangGraph foundation** we were planning to use

### What Makes This Different from "Just Using DeepAgents"

Our **Adversarial Cooperation pattern** is the innovation:
- DeepAgents provides the harness
- We add the Player/Coach adversarial loop
- We add structured YAML feature planning
- We add GuardKit integration

---

## Updated Document Dependencies

If we adopt DeepAgents, these documents need updates:

| Document | Change |
|----------|--------|
| FEATURE-002 | Replace with "DeepAgents Configuration" |
| FEATURE-003 | Simplify to SubAgent definition |
| FEATURE-004 | Simplify to SubAgent definition |
| FEATURE-005 | Add AdversarialLoopMiddleware |
| FEATURE-007 | **Delete** - replaced by FilesystemMiddleware |
| Kickoff | Update timeline and dependencies |
| Implementation Readiness | Update estimates |

---

## Next Steps

1. **Confirm** this approach with stakeholder
2. **Prototype** DeepAgents setup (2-4 hours)
   - Install deepagents
   - Create basic agent with subagents
   - Test FilesystemMiddleware coordination
3. **Update** feature documents if prototype succeeds
4. **Begin** implementation with new timeline

---

## References

- [DeepAgents GitHub](https://github.com/langchain-ai/deepagents) - 5.8k ⭐
- [DeepAgents Documentation](https://docs.langchain.com/oss/python/deepagents/overview)
- [DeepAgents Middleware](https://docs.langchain.com/oss/python/deepagents/middleware)
- [DeepAgents Quickstarts](https://github.com/langchain-ai/deepagents-quickstarts)
- [LangChain Middleware](https://docs.langchain.com/oss/python/langchain/middleware)
