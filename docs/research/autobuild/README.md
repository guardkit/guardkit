# AutoBuild - Autonomous Feature Implementation for GuardKit

> **Status**: Phase 1 Ready for Implementation
> **Technology**: LangChain DeepAgents + LangGraph
> **Timeline**: ~10 days (2 weeks)

---

## Overview

AutoBuild adds autonomous feature implementation to GuardKit using the **adversarial cooperation** pattern. Two AI agents work together:

- **Player Agent**: Implements code, writes tests
- **Coach Agent**: Validates implementation, provides feedback

They iterate until the Coach approves or max turns are reached.

---

## Architecture

```
┌────────────────────────────────────────────────────────────┐
│                   AutoBuild Orchestrator                    │
│                   (LangChain DeepAgents)                    │
├────────────────────────────────────────────────────────────┤
│  Built-in Middleware:                                       │
│  • TodoListMiddleware          (planning)                   │
│  • FilesystemMiddleware        (coordination)               │
│  • SubAgentMiddleware          (agent spawning)             │
│  • SummarizationMiddleware     (context management)         │
│  • HumanInTheLoopMiddleware    (approval gates)             │
│                                                             │
│  Custom Middleware:                                         │
│  • AdversarialLoopMiddleware   (our innovation)             │
├────────────────────────────────────────────────────────────┤
│  SubAgents:                                                 │
│  ┌─────────────────┐       ┌─────────────────┐             │
│  │     Player      │◄─────►│      Coach      │             │
│  │    (Haiku)      │       │    (Sonnet)     │             │
│  └─────────────────┘       └─────────────────┘             │
│           │                         │                       │
│           └────────/coordination/───┘                       │
└────────────────────────────────────────────────────────────┘
```

---

## Documentation

### Getting Started
- [Phase 1 Kickoff](./AutoBuild_Phase1_Kickoff.md) - Start here
- [Implementation Readiness Review](./Implementation_Readiness_Review.md) - Checklist

### Features
| Feature | Description | Doc |
|---------|-------------|-----|
| F1 | Enhanced feature-plan with YAML output | [FEATURE-001](./features/FEATURE-001-enhanced-feature-plan.md) |
| F2 | DeepAgents infrastructure setup | [FEATURE-002](./features/FEATURE-002-agent-sdk-infrastructure.md) |
| F3 | Player Agent (SubAgent definition) | [FEATURE-003](./features/FEATURE-003-player-agent.md) |
| F4 | Coach Agent (SubAgent definition) | [FEATURE-004](./features/FEATURE-004-coach-agent.md) |
| F5 | Orchestrator + AdversarialLoopMiddleware | [FEATURE-005](./features/FEATURE-005-adversarial-orchestrator.md) |
| F6 | autobuild CLI commands | [FEATURE-006](./features/FEATURE-006-autobuild-cli.md) |

### Research & Analysis
- [DeepAgents Integration Analysis](./DeepAgents_Integration_Analysis.md) - Why we chose DeepAgents
- [Claude-Flow Patterns Research](./Claude-Flow_Patterns_Research.md) - Coordination patterns
- [Adversarial Cooperation Research](./Adversarial_Cooperation_AutoBuild_Research.md) - Academic backing
- [Full Product Specification](./AutoBuild_Product_Specification.md) - Complete spec (4,300+ lines)

---

## Quick Start

### Usage (After Implementation)

```bash
# Plan a feature with structured output
guardkit feature-plan "Add OAuth2 authentication" --structured

# Run autobuild on a single task
guardkit autobuild task TASK-001

# Run autobuild on entire feature
guardkit autobuild feature FEAT-001 --parallel 2

# Resume interrupted run
guardkit autobuild resume FEAT-001
```

### How It Works

1. **Plan**: `/feature-plan` creates structured YAML with tasks and dependencies
2. **Execute**: `autobuild` runs tasks through Player→Coach loop
3. **Iterate**: Coach provides feedback, Player refines
4. **Approve**: Coach approves or escalates to human
5. **Merge**: Approved changes merged to main branch

---

## Technology Stack

| Component | Technology | Purpose |
|-----------|------------|---------|
| Agent Framework | DeepAgents | Agent harness with middleware |
| Orchestration | LangGraph | State management, checkpointing |
| Coordination | FilesystemMiddleware | Blackboard pattern |
| Approval Gates | HumanInTheLoopMiddleware | Human review points |
| Player Model | Claude 3.5 Haiku | Cost-efficient implementation |
| Coach Model | Claude Sonnet 4.5 | Better reasoning for validation |

---

## Implementation Timeline

```
Week 1 (5 days):
├── F1: Enhanced feature-plan      (2-3 days)
├── F2: DeepAgents setup           (0.5 days)
├── F3: Player Agent               (1 day)
└── F4: Coach Agent                (1 day)

Week 2 (5 days):
├── F5: Orchestrator + Middleware  (2-3 days)
└── F6: CLI + Integration          (1-2 days)

Total: ~10 days
```

---

## Key Innovation

Our **AdversarialLoopMiddleware** implements the adversarial cooperation pattern on top of DeepAgents' infrastructure:

```python
class AdversarialLoopMiddleware(AgentMiddleware):
    """Custom middleware for Player↔Coach loop control."""
    
    @property
    def tools(self):
        return [
            start_adversarial_task,
            get_loop_status,
            complete_task,   # HITL gated
            escalate_task,   # HITL gated
        ]
```

This is what makes AutoBuild unique - the adversarial pattern ensures higher quality output than single-agent approaches.

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Task completion rate | ≥70% without human intervention |
| Average turns per task | ≤4 |
| Coach approval accuracy | No false positives |
| Time to complete Phase 1 | ≤2 weeks |

---

## References

- [DeepAgents](https://github.com/langchain-ai/deepagents) - 5.8k ⭐ LangChain agent harness
- [LangGraph](https://langchain-ai.github.io/langgraph/) - State management
- [Adversarial Cooperation Paper](./adversarial-cooperation-in-code-synthesis.pdf) - Academic research
