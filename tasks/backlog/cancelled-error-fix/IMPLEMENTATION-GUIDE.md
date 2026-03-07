# Implementation Guide: CancelledError Exception Handling Fix

**Feature ID**: FEAT-CEF1
**Parent Review**: TASK-REV-C3F8

## Wave Breakdown

### Wave 1: Core Fixes (3 tasks, parallel)

These tasks have no file conflicts and can run in parallel.

| Task | File(s) | Mode |
|------|---------|------|
| TASK-CEF-001 | `feature_orchestrator.py` (lines 1514-1581) | task-work |
| TASK-CEF-002 | `agent_invoker.py` (lines 1279, 1933), `autobuild.py` (lines 3811, 3823), `feature_orchestrator.py` (line 1894) | task-work |
| TASK-CEF-003 | `coach_validator.py` (line ~1178) | direct |

**Note**: TASK-CEF-001 and TASK-CEF-002 both touch `feature_orchestrator.py` but at non-overlapping line ranges (1514-1581 vs 1894). Parallel execution is safe.

### Wave 2: Diagnostics (1 task)

| Task | File(s) | Mode |
|------|---------|------|
| TASK-CEF-004 | `feature_orchestrator.py` (near line 1499) | direct |

## Execution Strategy

```bash
# Wave 1 (parallel - 3 Conductor workspaces)
/task-work TASK-CEF-001    # Workspace: cancelled-error-fix-wave1-1
/task-work TASK-CEF-002    # Workspace: cancelled-error-fix-wave1-2
/task-work TASK-CEF-003    # Workspace: cancelled-error-fix-wave1-3

# Wave 2 (sequential - depends on Wave 1)
/task-work TASK-CEF-004    # Workspace: cancelled-error-fix-wave2-1
```

## Testing Strategy

- TASK-CEF-001: Unit test with mock CancelledError, TimeoutError, BaseException results
- TASK-CEF-002: Unit test each guard point with CancelledError injection
- TASK-CEF-003: Unit test ClaudeAgentOptions env parameter
- TASK-CEF-004: Integration test logging output
