# ADR-001: Graphiti Integration Scope - Context Loading Focus

**Status**: Accepted  
**Date**: 2026-01-11  
**Decision Makers**: Rich Woollcott  
**Context**: Defining scope for Graphiti integration into Claude Code GuardKit

---

## Context

### The Problem We're Solving

Claude Code sessions working on GuardKit (particularly `/feature-build`) lose context about:
- What GuardKit IS (a quality gate system, not just task management)
- How commands flow together (`/feature-plan` → `/feature-build` → `/task-work`)
- Architectural decisions made in previous sessions (SDK vs subprocess, worktree paths)
- What failed before and why

This causes sessions to make locally-optimal decisions that break the overall system design. The `/feature-build` command development has been particularly affected - multiple attempts failed because sessions didn't know about prior decisions.

### Strategic Context

**Claude Code GuardKit may become a legacy project.** The motivations for building a Deep Agents (LangChain/LangGraph) version of GuardKit are:

1. **Subscription Cost Risk**: Exit strategy from Claude Max subscription if Anthropic raises prices significantly

2. **Enterprise Data Security**: Work projects require private LLMs for data security - either running locally or on platforms like Amazon Bedrock where data stays within the organization

3. **Learning Experience**: Gaining agentic development experience with LangChain/LangGraph ecosystem, which is more portable across LLM providers

4. **Model Agnostic Future**: Deep Agents version can work with Claude, GPT-4, local models, or whatever becomes the best option

### Current User Base

Rich is currently the only active user of GuardKit, using it on:
- MyDrive .NET Mobile app
- GuardKit repository itself  
- RequireKit repository

This means we don't need to support migration paths for other users or maintain backward compatibility for external consumers.

### The Learning Journey

The experience building `/feature-build` with the Claude Agents SDK has been valuable despite frustrations. Key learnings:
- Context loss between sessions is the #1 blocker
- Markdown files alone don't preserve "why" decisions were made
- AI sessions make reasonable-looking choices that conflict with prior decisions
- The Player-Coach adversarial pattern works conceptually but needs persistent memory

These learnings directly inform what we need from Graphiti and will transfer to the Deep Agents implementation.

---

## Decision

### What We Will Build

**Graphiti integration focused on solving context loss**, not on replacing existing task/feature storage.

**7 Features:**

| # | Feature | Purpose |
|---|---------|---------|
| 1 | Graphiti Core Infrastructure | Foundation - Docker, client, connectivity |
| 2 | System Context Seeding | Seed "what GuardKit is" knowledge |
| 3 | Session Context Loading | Inject context at session start - **THE FIX** |
| 4 | ADR Lifecycle Management | Capture decisions so they persist |
| 5 | Episode Capture (Outcomes) | Record what worked/didn't |
| 6 | Template/Agent Sync | Keep template knowledge queryable |
| 7 | ADR Discovery from Code | Extract implicit decisions from code analysis |

### What We Will NOT Build

| Excluded | Reason |
|----------|--------|
| Task Entity Storage in Graphiti | Markdown tasks work fine, not worth investment |
| Feature Entity Storage in Graphiti | YAML features work fine |
| Task CLI Commands | Using Claude Code, not CLI |
| Feature CLI Commands | Using Claude Code, not CLI |
| ADR CLI Commands | Can query via Claude Code sessions |
| Migration Tooling | No migration needed - keeping markdown/YAML |
| Beads Integration | Superseded by Graphiti, would add complexity |

### Investment Principle

> "Good enough to build Deep Agents GuardKit confidently"

We're not trying to make Claude Code GuardKit perfect. We're trying to:
1. Fix the context loss problem that blocks `/feature-build`
2. Learn patterns that transfer to Deep Agents version
3. Avoid over-investing in potentially-legacy codebase

---

## Consequences

### Positive

1. **Focused scope**: 7 features instead of 14, faster to implement
2. **Solves actual problem**: Context loss is addressed directly
3. **Transferable patterns**: Graphiti integration patterns work in Deep Agents too
4. **No migration burden**: Existing tasks/features stay in markdown/YAML
5. **Learning opportunity**: Real experience with knowledge graphs for AI agents

### Negative

1. **No unified data store**: Tasks remain in markdown, knowledge in Graphiti (acceptable fragmentation)
2. **No CLI for tasks**: Must use Claude Code or edit markdown directly (acceptable for single user)
3. **Limited querying**: Can't do cross-domain queries like "tasks with similar outcomes" (defer to Deep Agents version)

### Risks

1. **Graphiti complexity**: Adding infrastructure (Docker, FalkorDB) for potentially-legacy project
   - Mitigation: Keep scope minimal, patterns transfer to Deep Agents

2. **Context loading overhead**: Session startup may be slower
   - Mitigation: Load selectively based on command being run

---

## Alternatives Considered

### Alternative 1: Full Graphiti Integration (Tasks + Features + Knowledge)

Store everything in Graphiti - tasks, features, and knowledge in one unified graph.

**Rejected because**: Over-investment in potentially-legacy project. Markdown tasks work fine for current needs.

### Alternative 2: Beads Integration for Tasks + Graphiti for Knowledge

Use Beads for task graph, Graphiti for knowledge - two specialized systems.

**Rejected because**: Adds complexity without solving the core context loss problem. Three data stores (markdown + Beads + Graphiti) is worse than two (markdown + Graphiti).

### Alternative 3: Skip Graphiti, Improve Markdown Loading

Enhance how Claude Code loads context from markdown files - bigger CLAUDE.md, more rules files.

**Rejected because**: Doesn't solve the "lost decisions" problem. Markdown files capture "what" but not "why" or "what we tried before". Also doesn't scale - context window limits.

### Alternative 4: Wait for Deep Agents Version

Skip Graphiti in Claude Code GuardKit, implement directly in Deep Agents version.

**Rejected because**: We need working `/feature-build` to BUILD the Deep Agents version. Can't skip the bridge.

---

## Implementation Priority

```
Feature 1: Core Infrastructure ──┐
                                 ├── Foundation (Week 1)
Feature 2: System Context Seeding┘
                                 
Feature 3: Session Context Loading ── THE FIX (Week 1-2)

Feature 4: ADR Lifecycle ────────┐
                                 ├── Learning Loop (Week 2-3)
Feature 5: Episode Capture ──────┘

Feature 6: Template/Agent Sync ──┐
                                 ├── Enhancement (Week 3-4)
Feature 7: ADR Discovery ────────┘
```

Features 1-3 are **critical path** - they directly fix the memory problem.
Features 4-7 make the system **improve over time**.

---

## Success Criteria

1. **Feature-build works**: Can successfully build a multi-task feature without context loss breaking the implementation

2. **Decisions persist**: ADRs created during one session are available to future sessions

3. **Sessions start informed**: Claude Code sessions working on GuardKit have relevant context loaded automatically

4. **Patterns transfer**: The Graphiti integration patterns are documented well enough to inform Deep Agents implementation

---

## References

- `docs/research/knowledge-graph-mcp/unified-data-architecture-decision.md` - Full analysis of data architecture options
- `docs/research/knowledge-graph-mcp/graphiti-system-context-seeding.md` - Seeding script with ~67 episodes
- `docs/research/knowledge-graph-mcp/feature-build-crisis-memory-analysis.md` - Analysis of feature-build failures as memory problem
- `docs/research/knowledge-graph-mcp/graphiti-prototype-integration-plan.md` - Technical integration approach

---

## Changelog

| Date | Change | Author |
|------|--------|--------|
| 2026-01-11 | Initial decision | Rich Woollcott |
