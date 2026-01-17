# Graphiti Integration Features

## Overview

This feature set integrates Graphiti (temporal knowledge graph) into GuardKit to solve the **memory/context problem** where Claude Code sessions lose track of:
- What GuardKit is and how it works
- Architectural decisions made in previous sessions
- What patterns worked or failed

## Strategic Context

The Claude Code markdown-based GuardKit is a stepping stone toward **Deep Agents GuardKit** (LangChain/LangGraph). We're not over-investing in Claude Code GuardKit, but we need it working well enough to build Deep Agents GuardKit.

The frustrating experience building `/feature-build` exposed exactly what context and memory systems are needed for multi-session agentic workflows.

**See**: [Unified Data Architecture Decision](../research/knowledge-graph-mcp/unified-data-architecture-decision.md) for full strategic context.

## Features

| ID | Feature | Priority | Dependencies | Status |
|----|---------|----------|--------------|--------|
| [FEAT-GI-001](./FEAT-GI-001-core-infrastructure.md) | Graphiti Core Infrastructure | Critical | None | Draft |
| [FEAT-GI-002](./FEAT-GI-002-system-context-seeding.md) | System Context Seeding | Critical | GI-001 | Draft |
| [FEAT-GI-003](./FEAT-GI-003-session-context-loading.md) | Session Context Loading | Critical | GI-001, GI-002 | Draft |
| [FEAT-GI-004](./FEAT-GI-004-adr-lifecycle.md) | ADR Lifecycle Management | High | GI-001 | Draft |
| [FEAT-GI-005](./FEAT-GI-005-episode-capture.md) | Episode Capture (Outcomes) | High | GI-001 | Draft |
| [FEAT-GI-006](./FEAT-GI-006-template-agent-sync.md) | Template/Agent Sync | Medium | GI-001 | Draft |
| [FEAT-GI-007](./FEAT-GI-007-adr-discovery.md) | ADR Discovery from Code | Medium | GI-001, GI-004 | Draft |

## Implementation Order

```
FEAT-GI-001: Core Infrastructure (foundation)
    ↓
FEAT-GI-002: System Context Seeding (seed knowledge)
    ↓
FEAT-GI-003: Session Context Loading (USE the knowledge) ← THE ACTUAL FIX
    ↓
FEAT-GI-004: ADR Lifecycle (capture new decisions)
    ↓
FEAT-GI-005: Episode Capture (learn from outcomes)
    ↓
FEAT-GI-006: Template/Agent Sync (keep templates queryable)
    ↓
FEAT-GI-007: ADR Discovery (discover implicit decisions)
```

**Features 1-3 are the critical path** to fixing the memory problem.
**Features 4-7 make the system learn and improve** over time.

## What We're NOT Building

| Dropped Capability | Reason |
|-------------------|--------|
| Task Entity Storage | Markdown tasks work fine |
| Feature Entity Storage | YAML features work fine |
| Task/Feature/ADR CLI Commands | Using Claude Code, not CLI |
| Migration Tooling | Nothing to migrate |
| ADR Conflict Detection | Nice-to-have, add later |

## Usage

Once implemented, use `/feature-plan` to generate task breakdowns for each feature:

```bash
# In Claude Code
/feature-plan docs/features/graphiti-integration/FEAT-GI-001-core-infrastructure.md
```

## Related Documents

- [Unified Data Architecture Decision](../research/knowledge-graph-mcp/unified-data-architecture-decision.md) - Strategic context
- [Graphiti System Context Seeding](../research/knowledge-graph-mcp/graphiti-system-context-seeding.md) - Seeding details
- [Graphiti Prototype Integration Plan](../research/knowledge-graph-mcp/graphiti-prototype-integration-plan.md) - Original plan
- [Feature-Build Crisis Memory Analysis](../research/knowledge-graph-mcp/feature-build-crisis-memory-analysis.md) - Problem analysis
