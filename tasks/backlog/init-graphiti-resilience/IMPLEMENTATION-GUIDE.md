# Implementation Guide: Init + Graphiti Resilience

**Feature ID**: FEAT-IGR
**Parent Review**: TASK-REV-21D3
**Total Tasks**: 7
**Estimated Effort**: ~6.75 hours

## Wave Breakdown

### Wave 1: Core Fixes (P1) — 4 tasks, ~3.75 hours

These tasks can be executed in parallel. No dependencies between them.

| Task | Title | Mode | Effort | Parallel Group |
|------|-------|------|--------|---------------|
| TASK-IGR-001 | Suppress noisy loggers | task-work | 30 min | wave1 |
| TASK-IGR-002 | Add retry with backoff | task-work | 2 hrs | wave1 |
| TASK-IGR-003 | Reuse client in template sync | task-work | 1 hr | wave1 |
| TASK-IGR-004 | FalkorDB MAX_QUEUED_QUERIES | direct | 15 min | wave1 |

**Dependencies**: None between Wave 1 tasks.

**Conductor workspace names**:
- `init-graphiti-resilience-wave1-1` (TASK-IGR-001)
- `init-graphiti-resilience-wave1-2` (TASK-IGR-002)
- `init-graphiti-resilience-wave1-3` (TASK-IGR-003)

TASK-IGR-004 is infrastructure (Synology config) — not a code task.

### Wave 2: DX Improvements (P2/P3) — 3 tasks, ~2.5 hours

| Task | Title | Mode | Effort | Depends On |
|------|-------|------|--------|------------|
| TASK-IGR-005 | Episode progress indicator | task-work | 30 min | TASK-IGR-001 |
| TASK-IGR-006 | Unify constants groups | task-work | 1 hr | None |
| TASK-IGR-007 | Document group ID scoping | direct | 1 hr | None |

**Dependencies**: TASK-IGR-005 depends on TASK-IGR-001 (log suppression must be in place before adding progress output, otherwise progress is buried in noise).

## Verification Plan

After all Wave 1 tasks complete:
1. Run `guardkit init fastapi-python -n test-project --copy-graphiti-from ~/Projects/appmilla_github/guardkit`
2. Verify: Init output is ~50 lines (not ~650)
3. Verify: No "Max pending queries exceeded" errors
4. Verify: Step 2.5 template sync succeeds (no "incomplete results" warning)
5. Verify: `guardkit init --verbose` still shows full debug output

After Wave 2:
6. Verify: Episode progress indicator shows N/M with elapsed times
7. Verify: `constants.py` and `graphiti_client.py` share group definitions
8. Verify: Documentation covers system vs project group scoping
