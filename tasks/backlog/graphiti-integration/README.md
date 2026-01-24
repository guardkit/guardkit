# Graphiti Integration Feature

## Overview

This feature set integrates Graphiti (temporal knowledge graph) into GuardKit to solve the **memory/context problem** where Claude Code sessions lose track of:
- What GuardKit is and how it works
- Architectural decisions made in previous sessions
- What patterns worked or failed

## Strategic Context

The Claude Code markdown-based GuardKit is a stepping stone toward **Deep Agents GuardKit** (LangChain/LangGraph). We're not over-investing in Claude Code GuardKit, but we need it working well enough to build Deep Agents GuardKit.

The frustrating experience building `/feature-build` exposed exactly what context and memory systems are needed for multi-session agentic workflows.

**See**: [Unified Data Architecture Decision](../../docs/research/knowledge-graph-mcp/unified-data-architecture-decision.md) for full strategic context.

## Tasks

| ID | Task | Priority | Dependencies | Status |
|----|------|----------|--------------|--------|
| [TASK-GI-001](./TASK-GI-001-core-infrastructure.md) | Graphiti Core Infrastructure | Critical | None | Pending |
| [TASK-GI-002](./TASK-GI-002-system-context-seeding.md) | System Context Seeding | Critical | GI-001 | Pending |
| [TASK-GI-003](./TASK-GI-003-session-context-loading.md) | Session Context Loading | Critical | GI-001, GI-002 | Pending |
| [TASK-GI-004](./TASK-GI-004-adr-lifecycle.md) | ADR Lifecycle Management | High | GI-001 | Pending |
| [TASK-GI-005](./TASK-GI-005-episode-capture.md) | Episode Capture (Outcomes) | High | GI-001 | Pending |
| [TASK-GI-006](./TASK-GI-006-template-agent-sync.md) | Template/Agent Sync | Medium | GI-001 | Pending |
| [TASK-GI-007](./TASK-GI-007-adr-discovery.md) | ADR Discovery from Code | Medium | GI-001, GI-004 | Pending |

## Implementation Order

```
TASK-GI-001: Core Infrastructure (foundation)
    |
    v
TASK-GI-002: System Context Seeding (seed knowledge)
    |
    v
TASK-GI-003: Session Context Loading (USE the knowledge) <- THE ACTUAL FIX
    |
    v
TASK-GI-004: ADR Lifecycle (capture new decisions)
    |
    v
TASK-GI-005: Episode Capture (learn from outcomes)
    |
    v
TASK-GI-006: Template/Agent Sync (keep templates queryable)
    |
    v
TASK-GI-007: ADR Discovery (discover implicit decisions)
```

**Tasks 1-3 are the critical path** to fixing the memory problem.
**Tasks 4-7 make the system learn and improve** over time.

## What We're NOT Building

| Dropped Capability | Reason |
|-------------------|--------|
| Task Entity Storage | Markdown tasks work fine |
| Feature Entity Storage | YAML features work fine |
| Task/Feature/ADR CLI Commands | Using Claude Code, not CLI |
| Migration Tooling | Nothing to migrate |
| ADR Conflict Detection | Nice-to-have, add later |

## Feature File

- **Feature YAML**: `.guardkit/features/FEAT-GI.yaml`
- **AutoBuild ready**: `/feature-build FEAT-GI`

## Related Documents

- [Unified Data Architecture Decision](../../docs/research/knowledge-graph-mcp/unified-data-architecture-decision.md) - Strategic context
- [Graphiti System Context Seeding](../../docs/research/knowledge-graph-mcp/graphiti-system-context-seeding.md) - Seeding details
- [Graphiti Prototype Integration Plan](../../docs/research/knowledge-graph-mcp/graphiti-prototype-integration-plan.md) - Original plan
- [Feature-Build Crisis Memory Analysis](../../docs/research/knowledge-graph-mcp/feature-build-crisis-memory-analysis.md) - Problem analysis
