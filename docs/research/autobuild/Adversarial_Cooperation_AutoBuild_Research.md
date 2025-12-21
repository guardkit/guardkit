# AutoBuild: Adversarial Cooperation for Autonomous Feature Implementation

**Date:** December 19, 2025  
**Status:** Research Complete - Ready for Implementation  
**Based On:** Block AI Research paper "Adversarial Cooperation in Code Synthesis" (December 8, 2025)  
**Reference Implementation:** g3 (https://github.com/dhanji/g3)

---

## Executive Summary

This document captures research into **dialectical autocoding** - a proven approach to autonomous AI-assisted software development that uses a structured coach-player feedback loop. This approach directly addresses GuardKit's next evolution: automating feature implementation after `/feature-plan` generates subtasks.

**Key Finding:** The adversarial cooperation pattern (two agents in a bounded feedback loop) significantly outperforms single-agent "vibe coding" for completing complex tasks without human intervention.

**Recommended Name:** **AutoBuild** (alternative: CoachMode)

**Implementation Path:** LangGraph with multi-LLM support (Claude, Devstral 2, DeepSeek)

---

## The Problem AutoBuild Solves

### Current GuardKit Workflow

```
/feature-plan "dark mode for settings"
    ↓
Creates subtasks: TASK-001, TASK-002, TASK-003
    ↓
Developer MANUALLY runs /task-work on each task
    ↓
Developer reviews, iterates, completes each task
```

### AutoBuild Workflow

```
/feature-plan "dark mode for settings"
    ↓
Creates subtasks: TASK-001, TASK-002, TASK-003
    ↓
/autobuild                          ← NEW
    ↓
Autonomous implementation with coach-player loop
    ↓
Developer reviews completed feature
```

---

## Adversarial Cooperation: The Pattern

From Block AI Research's paper and g3 implementation:

### Two Specialized Agents

**Player Agent** - Focuses on implementation, creativity, and problem-solving:
- Reads requirements and implements solutions
- Writes code, creates harnesses, executes commands
- Responds to specific feedback with targeted improvements
- Optimized for code production and execution

**Coach Agent** - Focuses on analysis, critique, and validation:
- Validates implementations against requirements
- Tests compilation and functionality
- Provides specific, actionable feedback
- Optimized for evaluation and guidance

### The Dialectical Loop

```
┌─────────────────────────────────────────────────────────────────┐
│                    DIALECTICAL LOOP                             │
│  ┌─────────────────┐          ┌─────────────────┐              │
│  │     PLAYER      │          │      COACH      │              │
│  │                 │ feedback │                 │              │
│  │  • Implement    │◄────────►│  • Review       │              │
│  │  • Create       │          │  • Test         │              │
│  │  • Execute      │          │  • Critique     │              │
│  │  • Iterate      │          │  • Approve      │              │
│  └─────────────────┘          └─────────────────┘              │
│            │                           │                        │
│            └───────────┬───────────────┘                        │
│                        │                                        │
│              SHARED WORKSPACE                                   │
│     ┌──────────────────┴──────────────────┐                    │
│     │  • Feature Plan (requirements)       │                    │
│     │  • Codebase (git worktree)          │                    │
│     │  • Quality Gates (test execution)    │                    │
│     └─────────────────────────────────────┘                    │
│                                                                 │
│     Bounds: Max Turns (10), Fresh Context, Requirements         │
└─────────────────────────────────────────────────────────────────┘
```

### Bounded Process

The adversarial process operates within carefully defined bounds:

| Bound | Purpose | Typical Value |
|-------|---------|---------------|
| **Turn Limits** | Prevents infinite loops | 10 turns |
| **Fresh Context** | Each turn starts with new agent instances to prevent context pollution | New LLM call per turn |
| **Requirements Contract** | Shared requirements doc provides consistent evaluation criteria | Feature plan |
| **Approval Gates** | Explicit approval from coach terminates successful runs | Quality gate pass |

---

## Why This Works Better Than Single-Agent

### Problems with "Vibe Coding" (Single Agent)

From the Block AI Research paper:

1. **Anchoring** - Limited ability to maintain coherency on larger tasks
2. **Refinement** - Systematic improvement is patchy, edge-case handling uneven
3. **Completion** - Success states are open-ended, require human instruction
4. **Complexity** - Weak ability to systematically approach multi-faceted problems
5. **Self-Declaration** - Agents often claim success prematurely

### Key Insight

> "The key insight in the adversarial dyad is to discard the implementing agent's self-report of success and have the coach perform an independent evaluation of compliance to requirements."

This aligns perfectly with GuardKit's philosophy: **implementation and testing are inseparable**.

### Fresh Context Each Turn

One of the surprising benefits is how this addresses context window limitations:

```python
# Traditional approach: single agent accumulates context until hitting limits

# Adversarial approach: fresh agent each turn
# - Player gets: requirements + last coach feedback
# - Coach gets: requirements + current implementation
# - No context pollution from previous attempts
```

Benefits:
- **Focus**: Each agent optimizes for its role and current conditions
- **Objectivity**: Coach reviews with fresh perspective each turn
- **Clarity**: Agents begin anew, avoiding context pollution
- **Scale**: System handles complex tasks by decomposition
- **Autonomy**: Push agent loop to hours, not ~5 minute turns

---

## Empirical Results from g3

### Case Study: Git TUI Application

Block AI compared g3 against leading platforms on building a Git repository TUI viewer:

| Platform | Completeness | Model | Observations |
|----------|--------------|-------|--------------|
| **g3 (adversarial)** | **5/5** | Claude-sonnet-4-5 + thinking | Meets all requirements, no crashes |
| Goose | 4.5/5 | Claude-sonnet-4-5 | Very functional, occasional crashes |
| Antigravity | 3/5 | Claude-sonnet-4-5 + thinking | Crashes, no side-by-side diff |
| OpenHands | 2/5 | Claude 3.5 Sonnet | Won't load branches |
| VSCode Codex | 1/5 | GPT-5.1-Codex-Max | Crashes on start |
| Cursor Pro | 1.5/5 | Claude-sonnet-4-5 + thinking | Unable to load repo |

### Ablation Study

When coach feedback was withheld from g3:
- Player went 4 rounds with missing feedback
- Spontaneously found things to improve
- **Final implementation was non-functional**
- Outcome comparable to OpenHands (code written, tests written, claimed success, but broken)

**Conclusion:** The adversarial feedback loop is essential, not optional.

### Time vs Quality Trade-off

- Goose: ~7 minutes (fastest, incomplete)
- g3: ~3 hours (slowest, fully complete)

> "The aim of running g3 in coach+player mode is to achieve autonomous coding. Thus emphasis is on one-shot implementation with no, or absolutely minimal user interaction."

---

## Multi-Model Support: The Cost Advantage

### Available Models for AutoBuild

| Model | SWE-bench | Price (input/output per M tokens) | Notes |
|-------|-----------|-----------------------------------|-------|
| Claude Sonnet 4 | ~50% | $3.00 / $15.00 | Current GuardKit default |
| **Devstral 2 (123B)** | **72.2%** | **$0.40 / $2.00** | Currently FREE via API |
| Devstral Small 2 (24B) | 68.0% | $0.10 / $0.30 | Runs locally on consumer hardware |
| DeepSeek R1 | ~65% | ~$0.14 / $0.28 | Open weights |

### Devstral 2 Highlights

Released December 9, 2025 by Mistral AI:

- **72.2% on SWE-bench Verified** - State-of-the-art for open-weight models
- **7x more cost-efficient** than Claude Sonnet on real-world tasks
- **256K context window** - Handles entire repositories
- **Modified MIT license** - Open source, permissively licensed
- **Currently free** via Mistral API

### The Cost Story

```
Claude Max subscription: $200/month
Devstral 2 API (estimated): ~$20-50/month for heavy use
Devstral Small 2 local: $0/month (runs on RTX 4090)

GuardKit with AutoBuild works with ALL of these.
```

---

## GuardKit AutoBuild Architecture

### Proposed Commands

```bash
# Option 1: Separate command
/feature-plan "dark mode for settings"
/autobuild

# Option 2: Flag on feature-plan
/feature-plan "dark mode for settings" --autobuild

# Option 3: Coach mode naming
/feature-plan "dark mode for settings" --coach
```

### LangGraph Implementation

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, Literal

class AutoBuildState(TypedDict):
    feature_plan: str           # The requirements contract
    tasks: list[str]            # Subtasks from feature plan
    current_task_index: int     # Which task we're on
    turn_number: int            # Current turn within task (max 10)
    player_output: str          # Last implementation attempt
    coach_feedback: str         # Last review/critique
    status: Literal["implementing", "reviewing", "approved", "failed", "next_task"]
    workspace_path: str         # Git worktree location
    model_config: dict          # Which LLM to use (Claude, Devstral, etc.)

def player_node(state: AutoBuildState) -> AutoBuildState:
    """Player: Implement based on requirements + coach feedback"""
    # Fresh LLM instance each turn (prevents context pollution)
    llm = get_llm(state["model_config"])
    
    current_task = state["tasks"][state["current_task_index"]]
    
    prompt = f"""
    Feature Requirements: {state['feature_plan']}
    Current Task: {current_task}
    Previous Feedback: {state['coach_feedback']}
    
    Implement this task, addressing all feedback from the coach.
    Run tests to verify your implementation works.
    """
    
    result = execute_implementation(llm, prompt, state["workspace_path"])
    
    return {
        **state, 
        "player_output": result, 
        "status": "reviewing"
    }

def coach_node(state: AutoBuildState) -> AutoBuildState:
    """Coach: Validate against requirements, not just compilation"""
    llm = get_llm(state["model_config"])  # Fresh instance
    
    current_task = state["tasks"][state["current_task_index"]]
    
    prompt = f"""
    Feature Requirements: {state['feature_plan']}
    Current Task: {current_task}
    Implementation: {state['player_output']}
    
    Validate this implementation against ALL requirements.
    Run the tests. Check edge cases. Be rigorous.
    
    Either:
    - APPROVED: All requirements for this task are met
    - FEEDBACK: Specific, actionable items that must be fixed
    
    Do NOT accept the player's self-report of success.
    Verify independently.
    """
    
    feedback, approved = execute_validation(llm, prompt, state["workspace_path"])
    
    if approved:
        next_status = "next_task" if state["current_task_index"] < len(state["tasks"]) - 1 else "approved"
    else:
        next_status = "implementing"
    
    return {
        **state, 
        "coach_feedback": feedback, 
        "status": next_status,
        "turn_number": state["turn_number"] + 1
    }

def should_continue(state: AutoBuildState) -> str:
    if state["status"] == "approved":
        return "complete"
    if state["status"] == "next_task":
        return "advance_task"
    if state["turn_number"] >= 10:
        return "failed"
    return "continue"

def advance_task_node(state: AutoBuildState) -> AutoBuildState:
    """Move to the next task in the feature plan"""
    return {
        **state,
        "current_task_index": state["current_task_index"] + 1,
        "turn_number": 0,
        "coach_feedback": "",
        "status": "implementing"
    }

# Build the graph
graph = StateGraph(AutoBuildState)
graph.add_node("player", player_node)
graph.add_node("coach", coach_node)
graph.add_node("advance_task", advance_task_node)

graph.set_entry_point("player")
graph.add_edge("player", "coach")
graph.add_conditional_edges("coach", should_continue, {
    "continue": "player",
    "advance_task": "advance_task",
    "complete": END,
    "failed": END
})
graph.add_edge("advance_task", "player")

autobuild_workflow = graph.compile()
```

### Integration with Existing GuardKit

```
┌─────────────────────────────────────────────────────────────────┐
│                      GuardKit CLI                               │
├─────────────────────────────────────────────────────────────────┤
│  /feature-plan                                                  │
│      │                                                          │
│      ├── Creates feature plan document                          │
│      ├── Generates subtasks (TASK-001, TASK-002, etc.)         │
│      └── [--autobuild flag triggers AutoBuild]                  │
│                          │                                      │
│                          ▼                                      │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    AutoBuild Engine                         ││
│  │  ┌─────────────┐                 ┌─────────────┐           ││
│  │  │   Player    │◄───feedback────►│    Coach    │           ││
│  │  │  (Claude/   │                 │  (Claude/   │           ││
│  │  │  Devstral/  │                 │  Devstral/  │           ││
│  │  │  DeepSeek)  │                 │  DeepSeek)  │           ││
│  │  └─────────────┘                 └─────────────┘           ││
│  │         │                               │                   ││
│  │         └───────────┬───────────────────┘                   ││
│  │                     ▼                                       ││
│  │            Shared Workspace (git worktree)                  ││
│  │            Quality Gates (existing)                         ││
│  └─────────────────────────────────────────────────────────────┘│
│                          │                                      │
│                          ▼                                      │
│  /task-complete (called automatically for each task)            │
└─────────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Basic Dialectical Loop (Week 1-2)

**Goal:** Prove the pattern works with GuardKit's feature plans

- [ ] LangGraph state machine for player-coach loop
- [ ] Integration with existing `/task-work` logic
- [ ] Single model (Claude) initially
- [ ] Sequential task execution
- [ ] Basic turn limits and failure handling

**Deliverable:** `/autobuild` command that completes a simple feature autonomously

**Content:** Blog post "Why Two Agents Beat One: Implementing Adversarial Cooperation"

### Phase 2: Multi-Model Support (Week 3)

**Goal:** Break vendor lock-in, demonstrate cost savings

- [ ] Abstract LLM interface (LangChain-style)
- [ ] Add Devstral 2 support via Mistral API
- [ ] Add DeepSeek R1 support
- [ ] Configuration for model selection
- [ ] Cost tracking and comparison

**Deliverable:** `--model devstral-2` flag, cost comparison benchmarks

**Content:** Blog post "GuardKit Goes Open: From $200/mo Claude to Free Devstral"

### Phase 3: Parallel Task Execution (Week 4-5)

**Goal:** Implement multiple tasks simultaneously

- [ ] Parallel worktrees for independent tasks
- [ ] Dependency-aware task scheduling
- [ ] Resource management (concurrent LLM calls)
- [ ] Progress tracking and UI feedback

**Deliverable:** Parallel feature implementation with Conductor-style visualization

**Content:** Demo video "Watch GuardKit auto-implement 5 tasks simultaneously"

### Phase 4: Human-in-the-Loop Refinements (Week 6+)

**Goal:** Add escape hatches and control points

- [ ] `--pause-after-task` for review between tasks
- [ ] Manual override capability mid-loop
- [ ] Checkpoint/resume for long-running builds
- [ ] Integration with Beads for task state tracking

**Deliverable:** Production-ready AutoBuild with full control options

---

## Comparison: AutoBuild vs Other Approaches

### Why Not Claude Agents SDK Alone?

The Claude Agents SDK is a viable path (see related research docs), but:

| Factor | Claude SDK | LangGraph + Multi-Model |
|--------|------------|------------------------|
| Time to MVP | ~1 week | ~2-3 weeks |
| Vendor lock-in | 100% Anthropic | None |
| Model flexibility | Claude only | Any LLM |
| Cost story | $200/mo minimum | $0 with local models |
| Learning value | Low (proprietary) | High (industry standard) |
| Content value | Good | Excellent |

**Recommendation:** Start with LangGraph. The extra 1-2 weeks pays off in flexibility and content opportunities.

### Why Not Full Multi-Agent Orchestration (Claude-Flow style)?

Swarm/hive systems (like Claude-Flow) are more complex:

| Aspect | AutoBuild (Dialectical) | Swarm Orchestration |
|--------|------------------------|---------------------|
| Agent count | 2 (player + coach) | Many (spawned dynamically) |
| Communication | Structured feedback loop | Message passing, shared memory |
| Complexity | Moderate | High |
| Debuggability | High (linear flow) | Low (emergent behavior) |
| Proven results | Yes (g3, Block AI paper) | Limited evidence |

**Recommendation:** Dialectical approach is simpler, proven, and sufficient for feature implementation.

---

## Content Strategy

| Week | Milestone | Content Piece |
|------|-----------|---------------|
| 1 | Basic loop working | Blog: "Adversarial Cooperation: Why Two AI Agents Beat One" |
| 2 | Full feature completion | Demo: "GuardKit AutoBuild: From Requirements to Implementation" |
| 3 | Devstral 2 integration | Blog: "Breaking Free from Claude Max: GuardKit with Open Models" |
| 4 | Cost benchmarks | Data post: "The Real Cost of AI Coding: Claude vs Devstral vs DeepSeek" |
| 5 | Parallel execution | Demo: "Watch 5 Features Get Built Simultaneously" |

---

## References

### Primary Sources

- Block AI Research Paper: "Adversarial Cooperation in Code Synthesis" (December 8, 2025)
- g3 Implementation: https://github.com/dhanji/g3
- Devstral 2 Announcement: https://mistral.ai/news/devstral-2-vibe-cli
- Mistral Vibe CLI: https://github.com/mistralai/mistral-vibe

### Benchmarks

- SWE-bench Verified: https://swebench.com/
- Terminal Bench: https://www.tbench.ai/leaderboard/terminal-bench/2.0

### Related GuardKit Research

- [Claude Agent SDK Integration Analysis](./claude_agent_sdk_integration_analysis.md)
- [Claude Agent SDK Fast Path](./Claude_Agent_SDK_Fast_Path_to_TaskWright_Orchestration.md)
- [Claude Agent SDK Two-Command Workflow](./Claude_Agent_SDK_Two_Command_Feature_Workflow.md)
- [LangGraph MCP Architecture](./agentecflow_langgraph_mcp_architecture_recommendation.md)

---

## Terminology Decision

After evaluation, the recommended name is **AutoBuild** because:

| Term | Verdict | Reasoning |
|------|---------|-----------|
| **AutoBuild** | ✅ Chosen | Clear purpose, action-oriented, not overloaded |
| CoachMode | ⚠️ Alternative | Good but emphasizes process over outcome |
| Dialectical Autocoding | ❌ | Too academic for developer marketing |
| Orchestration | ❌ | Overloaded with swarm/hive connotations |
| Auto-implement | ❌ | Generic, not distinctive |

**Usage:**
- Command: `/autobuild` or `/feature-plan --autobuild`
- Documentation: "GuardKit AutoBuild"
- Marketing: "Autonomous feature implementation with adversarial cooperation"

---

## Document History

| Date | Author | Changes |
|------|--------|---------|
| 2025-12-19 | Research session | Initial creation based on Block AI paper analysis and Devstral 2 evaluation |
