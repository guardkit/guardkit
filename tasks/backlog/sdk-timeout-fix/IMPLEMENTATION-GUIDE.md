# Implementation Guide: SDK Timeout Fix (TASK-REV-A327)

## Problem Statement

FEAT-E4F5 run 1 failed because TASK-SAD-002 timed out after 2340s despite completing all work in ~480s. Root cause analysis identified **three bugs at three technology seams** that contributed to the failure.

## Source Review

[TASK-REV-A327 Review Report](../../.claude/reviews/TASK-REV-A327-review-report.md)

## Wave Execution Plan

### Wave 1: Critical Fixes (P0) — 2 tasks, parallel

These fix the active failure. Both are independent and can execute in parallel.

| Task | Title | Complexity | Files Changed | Method |
|------|-------|-----------|---------------|--------|
| TASK-FIX-1206 | Break after ResultMessage in all SDK paths | 2 | agent_invoker.py | task-work |
| TASK-FIX-01FC | Player report test fallback in state recovery | 2 | state_tracker.py | task-work |

**After Wave 1**: The "completed-but-timed-out" failure class is eliminated, and state recovery correctly reports test results.

### Wave 2: High Priority Fix (P1) — 1 task

Depends on nothing from Wave 1 but is lower priority.

| Task | Title | Complexity | Files Changed | Method |
|------|-------|-----------|---------------|--------|
| TASK-FIX-DFCB | Cross-platform subprocess cleanup (macOS) | 4 | agent_invoker.py | task-work |

**After Wave 2**: Zombie subprocess accumulation on macOS is prevented.

### Wave 3: Improvements (P2/P3) — 3 tasks, parallel

These improve resilience but are not critical fixes. All are independent.

| Task | Title | Complexity | Files Changed | Method |
|------|-------|-----------|---------------|--------|
| TASK-FIX-F053 | Increase recovery test timeout | 2 | coach_verification.py, state_detection.py | task-work |
| TASK-FIX-8595 | Scope recovery tests to task files | 3 | autobuild.py | task-work |
| TASK-FIX-F0E3 | Add task_id to SDK log | 1 | agent_invoker.py | direct |

**Note**: TASK-FIX-8595 depends on TASK-FIX-01FC (Wave 1) being complete first.

## Dependency Graph

```
Wave 1 (parallel):
  TASK-FIX-1206 ──────────────────────────────────┐
  TASK-FIX-01FC ──────────┬───────────────────────┤
                          │                       │
Wave 2:                   │                       │
  TASK-FIX-DFCB ──────────┤ (no dep)             │
                          │                       │
Wave 3 (parallel):        │                       │
  TASK-FIX-F053 ──────────┤ (no dep)             │
  TASK-FIX-8595 ◄─────────┘ (depends on 01FC)   │
  TASK-FIX-F0E3 ─────────────────────────────────┘ (no dep)
```

## Files Affected

| File | Tasks | Changes |
|------|-------|---------|
| `guardkit/orchestrator/agent_invoker.py` | FIX-1206, FIX-DFCB, FIX-F0E3 | Break after ResultMessage, macOS cleanup, log improvement |
| `guardkit/orchestrator/state_tracker.py` | FIX-01FC | Player report test fallback |
| `guardkit/orchestrator/coach_verification.py` | FIX-F053 | Configurable test timeout |
| `guardkit/orchestrator/state_detection.py` | FIX-F053 | Pass timeout to CoachVerifier |
| `guardkit/orchestrator/autobuild.py` | FIX-8595 | Extract test_paths from player report |

## Risk Assessment

| Wave | Risk | Mitigation |
|------|------|-----------|
| 1 | Very Low — adding `break` and fallback logic | Existing tests + new unit tests |
| 2 | Medium — new platform-specific cleanup code | psutil with fallback, feature flag possible |
| 3 | Very Low — parameter changes and log improvements | Backward compatible changes |

## Validation

After all waves complete, validate by:
1. Re-running FEAT-E4F5 with `guardkit autobuild feature FEAT-E4F5 --resume`
2. Verifying TASK-SAD-002 completes without timeout
3. Checking no zombie processes remain after feature run (`ps aux | grep claude`)
