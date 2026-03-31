# Implementation Guide: Direct Mode Synthetic Report Fix

**Feature ID**: FEAT-DM-FIX
**Parent Review**: TASK-REV-F248
**Priority**: Critical (blocks RequireKit FEAT-498F re-run)

## Problem Statement

Direct mode tasks with acceptance criteria always stall because the synthetic report path in `agent_invoker.py` produces reports with empty `requirements_met`, no `completion_promises`, and no `_synthetic` flag. The Coach validator falls through to text matching against an empty list, resulting in 0/N criteria verified on every turn.

## Wave Breakdown

### Wave 1: Core Fix (TASK-FIX-D1A3)

**Single task, must complete before Wave 2.**

Unify the two divergent synthetic report builders into a shared module and ensure direct mode produces reports that Coach can verify.

| Task | Description | Complexity | Mode |
|------|-------------|-----------|------|
| TASK-FIX-D1A3 | Unify synthetic report builders | 6 | task-work |

**Key files**:
- NEW: `guardkit/orchestrator/synthetic_report.py`
- MODIFY: `guardkit/orchestrator/agent_invoker.py`
- MODIFY: `guardkit/orchestrator/autobuild.py`

### Wave 2: Guards + Tests (TASK-FIX-D1A4, TASK-TEST-D1A5)

**Two independent tasks, can run in parallel after Wave 1.**

| Task | Description | Complexity | Mode |
|------|-------------|-----------|------|
| TASK-FIX-D1A4 | Mode assignment AC guard | 3 | task-work |
| TASK-TEST-D1A5 | Integration tests for Q1 path | 4 | task-work |

## Execution Strategy

```
Wave 1: TASK-FIX-D1A3 (sequential, critical path)
         ↓
Wave 2: TASK-FIX-D1A4 + TASK-TEST-D1A5 (parallel)
```

**Estimated total effort**: 2-3 days

## Quick Workaround (Unblocks Re-Run Now)

While the proper fix is implemented, change TASK-RK01-003's `implementation_mode` from `direct` to `task-work` in the RequireKit feature YAML and re-run FEAT-498F. This is a 5-minute config change.

## Verification

After implementing all tasks:
1. Run `pytest tests/unit/test_synthetic_report.py -v`
2. Run `pytest tests/unit/test_direct_mode_criteria_matching.py -v`
3. Run `pytest tests/unit/test_autobuild*.py tests/unit/test_coach_validator*.py -v` (regression)
4. Re-run FEAT-498F with TASK-RK01-003 in direct mode — should now approve
