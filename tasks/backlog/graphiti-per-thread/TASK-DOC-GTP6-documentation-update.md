---
id: TASK-DOC-GTP6
title: Update Graphiti documentation for per-thread architecture
status: completed
created: 2026-02-09T14:00:00Z
updated: 2026-02-09T16:30:00Z
completed: 2026-02-09T16:30:00Z
priority: medium
tags: [documentation, graphiti, threading, architecture]
task_type: implementation
complexity: 4
feature: FEAT-C90E
depends_on: [TASK-FIX-GTP1, TASK-FIX-GTP2, TASK-FIX-GTP5]
test_results:
  status: pending
  coverage: null
  last_run: null
---

# Task: Update Graphiti Documentation for Per-Thread Architecture

## Description

Update all Graphiti documentation to reflect the migration from singleton to per-thread client factory pattern. The documentation must accurately describe the new threading model, client lifecycle, and usage patterns.

### Documents to Update

The following documents are listed in `docs/reviews/graphiti_baseline/graphiti_docs_index.md` and need review/update:

| Document | What Needs Updating |
|----------|-------------------|
| `docs/reviews/graphiti_baseline/graphiti-technical-reference.md` | Client initialization, singleton references, thread safety section |
| `docs/reviews/graphiti_baseline/graphiti-storage-theory.md` | Client lifecycle model if referenced |
| `docs/deep-dives/graphiti/episode-metadata.md` | Usage examples if they reference `get_graphiti()` |
| `docs/guides/graphiti-integration-guide.md` | Integration patterns, initialization guide, threading model |
| `docs/architecture/graphiti-architecture.md` | Architecture diagrams, client lifecycle, factory pattern |
| `docs/architecture/ADR-GBF-001-unified-episode-serialization.md` | Check if singleton is referenced |
| `docs/deep-dives/graphiti/episode-upsert.md` | Usage examples |

### Additional Documents

| Document | What Needs Updating |
|----------|-------------------|
| `.claude/rules/graphiti-knowledge.md` | Client initialization rules, threading guidance |
| `CLAUDE.md` | If Graphiti usage patterns are referenced |

### Key Changes to Document

1. **Threading Model**: Explain why per-thread clients are needed (Neo4j driver + event loop binding)
2. **Client Factory**: Document `GraphitiClientFactory`, `create_client()`, `get_thread_client()`
3. **Migration Guide**: How to update code that uses `get_graphiti()` directly
4. **Backward Compatibility**: Explain that `get_graphiti()` still works (returns thread-local client)
5. **AutoBuild Context**: How parallel task execution creates per-thread clients
6. **Lessons Learned**: Cross-loop async issues, graphiti-core `asyncio.gather()` limitation

## Acceptance Criteria

- [ ] All 7 documents from `graphiti_docs_index.md` reviewed and updated where needed
- [ ] `.claude/rules/graphiti-knowledge.md` updated with threading guidance
- [ ] Singleton references replaced with factory pattern descriptions
- [ ] Threading model documented (why per-thread clients, event loop binding)
- [ ] `GraphitiClientFactory` API documented with usage examples
- [ ] Backward compatibility of `get_graphiti()` clearly explained
- [ ] No documentation references stale singleton pattern without clarification
- [ ] Architecture diagrams updated if they show singleton lifecycle

## Key Files

### Must Review and Update
- `docs/reviews/graphiti_baseline/graphiti-technical-reference.md`
- `docs/reviews/graphiti_baseline/graphiti-storage-theory.md`
- `docs/deep-dives/graphiti/episode-metadata.md`
- `docs/guides/graphiti-integration-guide.md`
- `docs/architecture/graphiti-architecture.md`
- `docs/architecture/ADR-GBF-001-unified-episode-serialization.md`
- `docs/deep-dives/graphiti/episode-upsert.md`
- `.claude/rules/graphiti-knowledge.md`

### Reference
- `.claude/reviews/TASK-REV-2AA0-review-report.md` — Root cause analysis, threading model explanation
- `docs/reviews/graphiti_baseline/graphiti_docs_index.md` — Document inventory
- `guardkit/knowledge/graphiti_client.py` — New factory implementation (from GTP1)

## Context

- Depends on: TASK-FIX-GTP1, TASK-FIX-GTP2, TASK-FIX-GTP5 (all implementation complete before docs)
- Last wave task — documentation reflects final implementation
- The TASK-REV-2AA0 review report contains detailed threading analysis that should inform the docs
- ADR-GBF-001 may need a new section or companion ADR for the threading model decision

## Implementation Notes

### Documentation Tone

The docs should explain:
- **What changed**: Singleton → factory with thread-local storage
- **Why it changed**: Cross-loop event loop binding in Neo4j async driver
- **What callers need to know**: `get_graphiti()` still works, but parallel code should use factory
- **What's the same**: `GraphitiClient` API, `GraphitiConfig`, graceful degradation

### Consider Adding

An ADR (Architecture Decision Record) for the threading model change, similar to `ADR-GBF-001`. This would document:
- Decision: Per-thread Graphiti clients instead of singleton
- Context: graphiti-core's async internals bound to event loop
- Consequences: Slightly more memory (one client per thread), but correct parallel behavior

## Test Execution Log

[Automatically populated by /task-work]
