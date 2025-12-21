# FEATURE-007: Blackboard Coordination Infrastructure

> **Status**: ⚠️ SUPERSEDED by DeepAgents FilesystemMiddleware
> **Superseded Date**: December 2025
> **See Instead**: [FEATURE-002: DeepAgents Infrastructure](./FEATURE-002-agent-sdk-infrastructure.md)

---

## Supersession Notice

This feature has been **superseded** by the adoption of LangChain's DeepAgents framework.

### What We Planned
- Custom SQLite-backed blackboard for agent coordination
- 5 namespaces: coordination, feedback, consensus, events, checkpoints
- EventLog for audit trail
- ConsensusManager for approval gates

### What DeepAgents Provides Instead

**FilesystemMiddleware** with **CompositeBackend** gives us:

```python
from deepagents.backends import CompositeBackend, StateBackend, StoreBackend

# Path-based routing = namespace isolation
backend = CompositeBackend(
    default=StateBackend(),  # Ephemeral working state
    routes={
        "/coordination/": StoreBackend(store),  # Persistent - Player/Coach comms
        "/artifacts/": StoreBackend(store),     # Persistent - Output files
    }
)
```

This provides:
- ✅ Namespace isolation via path routing
- ✅ Persistent storage for coordination
- ✅ Ephemeral storage for working state
- ✅ Battle-tested implementation from LangChain

### Approval Gates

**HumanInTheLoopMiddleware** replaces our ConsensusManager:

```python
agent = create_deep_agent(
    interrupt_on={
        "complete_task": {"allowed_decisions": ["approve", "reject"]},
        "escalate_task": {"allowed_decisions": ["approve", "reject"]},
    }
)
```

### Event Logging

LangGraph's built-in tracing and checkpointing handles audit trails.

---

## Research Value

The research done for this feature informed our understanding of coordination patterns and validated that DeepAgents' FilesystemMiddleware is the right approach. See:

- [Claude-Flow Patterns Research](../Claude-Flow_Patterns_Research.md)
- [DeepAgents Integration Analysis](../DeepAgents_Integration_Analysis.md)

---

## Time Saved

| What | Original Effort | With DeepAgents |
|------|-----------------|-----------------|
| Blackboard implementation | 2 days | 0 days |
| Event logging | 0.5 days | 0 days |
| Consensus gates | 0.5 days | 0 days |
| **Total** | **3 days** | **0 days** |

The research time was well spent - it helped us recognize that DeepAgents already solved this problem.
