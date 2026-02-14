# ADR-SP-008: Hash-Based Task IDs

- **Date**: 2025-10
- **Status**: Accepted

## Context

Sequential task IDs (TASK-001, TASK-002) create collisions in parallel development workflows, especially with Conductor.build's Git worktree isolation.

## Decision

Use hash-based task IDs: TASK-{4-char-hash} or TASK-{prefix}-{4-char-hash} (e.g., TASK-FIX-a3f8). Hash derived from task description for deterministic IDs.

## Consequences

**Positive:**
- Zero collisions in parallel workflows
- Conductor.build compatible
- Safe concurrent creation

**Negative:**
- Less human-readable than sequential
- Requires hash collision detection (extremely rare with 4 chars + prefix)
