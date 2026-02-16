# Implementation Guide: Graphiti Event Loop Lifecycle Fix

## Feature Overview

Fix the Graphiti/FalkorDB async event loop lifecycle issues identified in AutoBuild Run 4 review ([TASK-REV-50E1](.claude/reviews/TASK-REV-50E1-review-report.md)). All root causes have been traced to specific source code locations with HIGH confidence.

## Execution Waves

### Wave 1: Quick Wins (parallel, ~1 hour)

These are trivial fixes that together eliminate ~31 of ~53 errors.

| Task | Description | Complexity | Mode | Files |
|------|-------------|-----------|------|-------|
| TASK-GLF-001 | Add `enable_context` guard | 2 | direct | `autobuild.py` |
| TASK-GLF-002 | Add `shutting_down` flag | 2 | direct | `autobuild.py` |

**Verification**: After Wave 1, re-run AutoBuild on a small feature. Episode creation warnings and shutdown errors should be eliminated.

### Wave 2: Core Fixes (parallel, requires Wave 1)

| Task | Description | Complexity | Mode | Files |
|------|-------------|-----------|------|-------|
| TASK-GLF-003 | Lazy Graphiti client init | 6 | task-work | `graphiti_client.py`, `autobuild.py` |
| TASK-GLF-004 | Direct mode report fix | 5 | task-work | `agent_invoker.py` |

**Verification**: After Wave 2, re-run AutoBuild. All Lock affinity errors and "report not found" errors should be eliminated.

### Wave 3: Hardening (requires Wave 2)

| Task | Description | Complexity | Mode | Files |
|------|-------------|-----------|------|-------|
| TASK-GLF-005 | Lightweight health check | 4 | task-work | `feature_orchestrator.py`, `graphiti_client.py` |

**Verification**: Full AutoBuild run should produce zero Graphiti-related errors.

## Key Files

| File | Change | Task(s) |
|------|--------|---------|
| `guardkit/orchestrator/autobuild.py` | Add `enable_context` check (line 2895), add `shutting_down` flag | GLF-001, GLF-002 |
| `guardkit/knowledge/graphiti_client.py` | Lazy init pattern in `get_thread_client()` (lines 1627-1632), add `is_initialized` flag | GLF-003 |
| `guardkit/orchestrator/agent_invoker.py` | Extract SDK results before `_load_agent_report` (line 2509) | GLF-004 |
| `guardkit/orchestrator/feature_orchestrator.py` | Lightweight health check (lines 930-1001) | GLF-005 |

## Dependency Graph

```
Wave 1 (parallel):
  GLF-001 ─┐
  GLF-002 ─┤
           │
Wave 2 (parallel, after Wave 1):
  GLF-003 ─┤
  GLF-004 ─┤
           │
Wave 3 (after Wave 2):
  GLF-005 ─┘
```

## Risk Mitigations

| Risk | Mitigation |
|------|-----------|
| Lazy init changes Graphiti timing | Test with FalkorDB both available and unavailable |
| Direct mode report extraction breaks existing flow | Preserve fallback to `_retry_with_backoff` if extraction fails |
| Health check split misses connectivity issues | Keep original health check as fallback if lightweight ping unavailable |

## Success Criteria

1. AutoBuild run produces 0 Graphiti-related error lines
2. All existing tests pass (no regressions)
3. Direct mode tasks complete in 1 turn (no wasted recovery turns)
4. Health check correctly detects FalkorDB availability/unavailability
5. `enable_context=False` fully suppresses all Graphiti operations
