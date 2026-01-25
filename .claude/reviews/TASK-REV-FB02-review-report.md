# Review Report: TASK-REV-fb02

**Task-Work Results Not Found Despite Fixes - Decision Analysis**

## Executive Summary

The feature-build command continues to fail with "Task-work results not found" despite implementing all fixes from TASK-REV-FB01. **Root cause identified**: Task-work delegation is **not enabled by default** in the AutoBuildOrchestrator. The `AgentInvoker` defaults to legacy direct SDK invocation, which doesn't write `task_work_results.json`.

**Severity**: Critical - Complete blocker for AutoBuild feature
**Root Cause**: Configuration gap, not code bug
**Fix Complexity**: 1-2 (simple configuration change)

---

## Review Details

| Field | Value |
|-------|-------|
| **Mode** | Decision Analysis |
| **Depth** | Standard |
| **Duration** | ~30 minutes |
| **Reviewer** | Decision analysis workflow |

---

## Findings

### Finding 1: Task-Work Delegation Disabled by Default

**Severity**: Critical
**Evidence**: `agent_invoker.py:41`

The environment variable `GUARDKIT_USE_TASK_WORK_DELEGATION` defaults to `"false"`, meaning:
- Direct SDK invocation is used (legacy mode)
- Player agent writes to `player_turn_N.json` directly
- `task_work_results.json` is **never created**

### Finding 2: AutoBuildOrchestrator Does Not Override Default

**Severity**: Critical
**Evidence**: `autobuild.py:636-640`, `autobuild.py:654-658`, `autobuild.py:1878-1882`

All three locations where `AgentInvoker` is instantiated are missing `use_task_work_delegation=True`.

### Finding 3: TASK-FB-RPT1 Fix Was Correct But Never Reached

The fix in TASK-FB-RPT1 correctly implemented `_create_player_report_from_task_work()` but this code path only executes when `self.use_task_work_delegation` is `True`.

---

## Root Cause Summary

1. AutoBuildOrchestrator creates AgentInvoker WITHOUT `use_task_work_delegation=True`
2. AgentInvoker defaults to `USE_TASK_WORK_DELEGATION` env var (defaults "false")
3. `invoke_player()` uses direct SDK invocation (legacy mode)
4. Player agent doesn't write `task_work_results.json`
5. CoachValidator fails with "Task-work results not found"

---

## Recommendation

**Option A (Recommended)**: Add `use_task_work_delegation=True` to all AgentInvoker instantiations in `autobuild.py` (3 locations).

**Effort**: 1-2 hours | **Risk**: Low

---

## Implementation Task

**TASK-FB-DEL1**: Enable Task-Work Delegation in AutoBuildOrchestrator

Files to modify:
- `guardkit/orchestrator/autobuild.py` lines 636, 654, 1878

Acceptance Criteria:
- AgentInvoker created with `use_task_work_delegation=True`
- Unit tests verify delegation is enabled
- Coach validation succeeds in feature-build
