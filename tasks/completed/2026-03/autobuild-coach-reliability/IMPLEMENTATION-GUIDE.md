# Implementation Guide: AutoBuild Coach Reliability and Graphiti Connection Resilience

## Feature Overview

Fix two compounding failures that make AutoBuild unreliable:
- **F2**: Coach criteria verification always returns 0/10 because Player output format doesn't match what `coach_validator.py` expects
- **F3**: FalkorDB/Graphiti asyncio corruption during parallel task execution causes connection errors

These failures interact in a doom loop: F3 degrades context -> Player times out -> synthetic report has no promises -> F2 returns 0/10 -> identical feedback -> repeat.

## Feature Spec

`docs/features/FEAT-AUTOBUILD-COACH-RELIABILITY-spec.md`

## Execution Strategy

**Approach**: Multi-layer sequential fix with parallel waves where safe
**Execution**: Auto-detected dependency waves (4 waves)
**Testing**: Standard quality gates with unit tests

## Wave Breakdown

### Wave 1: Foundation (3 tasks, parallel)

These are independent foundation tasks with no cross-dependencies.

| Task | Title | Complexity | Mode | Description |
|------|-------|-----------|------|-------------|
| TASK-ACR-001 | Propagate completion_promises | 3 | task-work | Fix standard task-work path to propagate promises + ensure task_id populated |
| TASK-ACR-003 | Diagnostic logging | 2 | direct | Add WARNING-level diagnostics when criteria verification is 0/N |
| TASK-ACR-005 | Store event loop with loaders | 3 | direct | Foundation: store asyncio event loop reference alongside thread loaders |

### Wave 2: Core Fixes (3 tasks, parallel)

Core F2 and F3 fixes that depend on Wave 1 foundations.

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| TASK-ACR-002 | Fuzzy text matching | 5 | task-work | TASK-ACR-001 |
| TASK-ACR-006 | Fix thread cleanup | 5 | task-work | TASK-ACR-005 |
| TASK-ACR-007 | Fix turn state capture | 4 | task-work | TASK-ACR-005 |

### Wave 3: Advanced Fixes (2 tasks, parallel)

Advanced fixes that build on core fixes.

| Task | Title | Complexity | Mode | Dependencies |
|------|-------|-----------|------|-------------|
| TASK-ACR-004 | Synthetic report git analysis | 6 | task-work | TASK-ACR-001, TASK-ACR-002 |
| TASK-ACR-008 | Graphiti circuit breaker | 5 | task-work | TASK-ACR-006, TASK-ACR-007 |

### Wave 4: Integration Validation

After all implementation waves complete, validate the combined fix:
- Re-run TASK-SFT-001 (complexity 2) via AutoBuild — should complete within 5 turns with criteria progress visible
- Verify zero asyncio errors in logs
- Verify clean shutdown without errors

## Dependency Graph

```
Wave 1 (parallel):
  TASK-ACR-001 ──┐
  TASK-ACR-003   │  (independent)
  TASK-ACR-005 ──┤
                 │
Wave 2 (parallel):
  TASK-ACR-002 ←─┤ (depends on ACR-001)
  TASK-ACR-006 ←─┤ (depends on ACR-005)
  TASK-ACR-007 ←─┘ (depends on ACR-005)
                 │
Wave 3 (parallel):
  TASK-ACR-004 ←─┤ (depends on ACR-001, ACR-002)
  TASK-ACR-008 ←─┘ (depends on ACR-006, ACR-007)
```

## Files Modified

| File | Tasks | Changes |
|------|-------|---------|
| `guardkit/orchestrator/agent_invoker.py` | ACR-001 | Propagate completion_promises, ensure task_id |
| `guardkit/orchestrator/quality_gates/coach_validator.py` | ACR-002, ACR-003 | Fuzzy matching fallback, diagnostic logging |
| `guardkit/orchestrator/autobuild.py` | ACR-004, ACR-005, ACR-006, ACR-007 | Synthetic report improvements, thread loader storage, cleanup fix, turn state fix |
| `guardkit/knowledge/graphiti_client.py` | ACR-008 | Health check, circuit breaker, is_healthy property |

## Test Files

| File | Tasks | Coverage |
|------|-------|----------|
| `tests/unit/test_coach_validator.py` | ACR-002, ACR-003 | Fuzzy matching, diagnostics, 0/N edge cases |
| `tests/unit/test_agent_invoker.py` | ACR-001 | Promise propagation for standard path |
| `tests/unit/test_autobuild_synthetic_report.py` | ACR-004 | Git-based promise generation |
| `tests/unit/test_autobuild_orchestrator.py` | ACR-005, ACR-006, ACR-007 | Thread loader storage, cross-thread cleanup, turn state |
| `tests/unit/test_graphiti_client.py` (new) | ACR-008 | Circuit breaker, health check |

## Success Criteria

1. After a successful Player turn, criteria verification shows > 0/N
2. Zero `RuntimeError: no running event loop` or `Lock is bound to a different event loop` errors
3. Clean shutdown: `_cleanup_thread_loaders()` completes without errors
4. Circuit breaker activates after 3 Graphiti failures and autobuild continues
5. TASK-SFT-001 completes within 5 turns with visible criteria progress
6. No false positives in criteria matching

## Risk Mitigations

- Fuzzy matching uses conservative 70% keyword threshold, logs strategy used
- Circuit breaker requires 3+ consecutive failures before tripping
- Git-based promises marked `evidence_type: "git_analysis"` with `status: "partial"`
- All changes are additive — existing consumers ignore unknown keys

## Review Reference

Original review: TASK-REV-B5C4
Feature spec: `docs/features/FEAT-AUTOBUILD-COACH-RELIABILITY-spec.md`
