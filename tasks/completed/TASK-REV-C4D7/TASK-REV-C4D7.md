---
id: TASK-REV-C4D7
title: "Review: Feature-Build State Analysis Post SDK_MAX_TURNS Fix"
status: completed
created: 2026-01-25T18:00:00Z
updated: 2026-01-25T19:45:00Z
completed: 2026-01-25T19:45:00Z
completed_location: tasks/completed/TASK-REV-C4D7/
priority: high
task_type: review
review_mode: architectural
review_depth: standard
tags: [feature-build, regression, analysis, direct-mode, sdk-max-turns, autobuild]
complexity: 6
related_tasks:
  - TASK-REV-BB80
implementation_task: TASK-FIX-C4D8
review_results:
  mode: architectural
  depth: standard
  score: 95
  findings_count: 5
  recommendations_count: 4
  decision: implement
  report_path: .claude/reviews/TASK-REV-C4D7-review-report.md
  completed_at: 2026-01-25T19:30:00Z
organized_files:
  - TASK-REV-C4D7.md
  - review-report.md
---

# Task: Review Feature-Build State Analysis Post SDK_MAX_TURNS Fix

## Overview

Following the TASK-REV-BB80 fix that addressed the SDK `max_turns` regression, the feature-build command shows **partial recovery**:

| Feature | Status | Details |
|---------|--------|---------|
| **App Infrastructure (FEAT-FHE)** | ✅ WORKING | 2 tasks, 2 waves, both approved in 1 turn each |
| **OpenAPI Documentation (FEAT-F392)** | ❌ BROKEN | 6 tasks, 3 waves, all 3 Wave 1 tasks failed with "Player report missing" |

This review must **analyze the evidence files** to identify the specific differences between the working and broken features.

## Evidence Summary

### Working: App Infrastructure (FEAT-FHE)

**Source**: `docs/reviews/feature-build/app_infrastructure_after_SDK_MAX_TURNS_regression_fix.md`

**Key Evidence**:
- Feature: "Create FastAPI app with health endpoint" (2 tasks, 2 waves)
- **TASK-FHE-001**: Approved in 1 turn, "0 files created, 0 modified, 0 tests (passing)"
- **TASK-FHE-002**: Approved in 1 turn, "0 files created, 0 modified, 0 tests (passing)"
- Invocation path: `Invoking Player via task-work delegation`
- SDK config: `Max turns: 50`, `SDK timeout: 900s`
- Message counts: `total=139, assistant=72, tools=61` (TASK-FHE-001), `total=223, assistant=116, tools=101` (TASK-FHE-002)
- Duration: 49m 47s total
- Result: **SUCCESS** - Both tasks completed

### Broken: OpenAPI Documentation (FEAT-F392)

**Source**: `docs/reviews/feature-build/open_api_docs_after_SDK_MAX_TURNS_regression_fix.md`

**Key Evidence**:
- Feature: "Comprehensive API Documentation" (6 tasks, 3 waves)
- Wave 1 tasks (TASK-DOC-001, TASK-DOC-002, TASK-DOC-005) ran in **parallel** (3 concurrent)
- Invocation path: `Routing to direct Player path for {task_id} (implementation_mode=direct)`
- SDK invocation: `Invoking Player via direct SDK`
- **Critical Error Pattern**:
  ```
  INFO:guardkit.orchestrator.agent_invoker:Wrote direct mode results to .../task_work_results.json
  INFO:guardkit.orchestrator.agent_invoker:Wrote direct mode player report to .../player_turn_1.json
  ⚠ Player report missing - attempting state recovery
  ```
- State recovery fails: "No work detected"
- Duration: 54 seconds (vs 49 minutes for working feature)
- Result: **FAILED** - 0/6 tasks completed, 3 failed in Wave 1

## Key Observations

### 1. Different Invocation Paths

| Aspect | FEAT-FHE (Working) | FEAT-F392 (Broken) |
|--------|--------------------|--------------------|
| **Routing Log** | "Invoking Player via task-work delegation" | "Routing to direct Player path (implementation_mode=direct)" |
| **Invocation** | `_invoke_task_work_implement` | `_invoke_player_direct` |
| **SDK max_turns** | `TASK_WORK_SDK_MAX_TURNS=50` | `self.max_turns_per_agent` (**likely 5**) |

### 2. The `_invoke_with_role` Bug

Looking at `agent_invoker.py:1221`:
```python
options = ClaudeAgentOptions(
    cwd=str(self.worktree_path),
    allowed_tools=allowed_tools,
    permission_mode=permission_mode,
    max_turns=self.max_turns_per_agent,  # BUG: Uses 5, not 50
    model=model,
    setting_sources=["project"],
)
```

The `_invoke_with_role` method (used by direct mode) still uses `self.max_turns_per_agent` (5), while `_invoke_task_work_implement` was fixed to use `TASK_WORK_SDK_MAX_TURNS` (50).

### 3. The "Player Report Missing" Paradox

The logs show:
```
INFO: Wrote direct mode player report to .../player_turn_1.json
⚠ Player report missing - attempting state recovery
```

This appears contradictory - the file is written but then not found. Possible causes:
1. Race condition with file write and read
2. The orchestrator is looking for a different file format
3. The file path mismatch between write and read

### 4. Timing Difference

- Working feature: 49m 47s for 2 tasks
- Broken feature: 54s for 3 tasks (immediate failure)

This 50x speed difference confirms tasks aren't actually executing - they're failing almost immediately.

## TASK-REV-BB80 Fix Analysis

### What Was Fixed

**Commit**: `14327137` introduced the bug by changing `max_turns=50` to `self.max_turns_per_agent` (5) in `_invoke_task_work_implement`.

The fix added `TASK_WORK_SDK_MAX_TURNS = 50` constant and used it in `_invoke_task_work_implement`:

```python
# Line 2268 (FIXED)
max_turns=TASK_WORK_SDK_MAX_TURNS,  # task-work needs ~50 internal turns
```

### What Was NOT Fixed

The `_invoke_with_role` method at line 1221 still uses:
```python
max_turns=self.max_turns_per_agent,  # Still uses 5!
```

This method is called by `_invoke_player_direct` (direct mode), which explains why direct mode tasks fail while task-work delegation tasks succeed.

## Root Cause Hypothesis

**Direct mode SDK max_turns is still 5, causing Player to run out of turns before completing implementation.**

The fix for TASK-REV-BB80 only fixed the `_invoke_task_work_implement` path, but `_invoke_with_role` (used by direct mode) still has the same bug.

## Acceptance Criteria

- [ ] Confirm the `max_turns` value used in `_invoke_with_role` is the root cause
- [ ] Verify message/tool counts for direct mode vs task-work delegation
- [ ] Analyze why "Player report missing" occurs after "Wrote direct mode player report"
- [ ] Determine if direct mode should use `TASK_WORK_SDK_MAX_TURNS` or a separate constant
- [ ] Recommend fix (likely: use same constant or create `DIRECT_MODE_SDK_MAX_TURNS`)
- [ ] Check for any other code paths using `self.max_turns_per_agent` for SDK invocations

## Files to Review

- [agent_invoker.py:1170-1244](guardkit/orchestrator/agent_invoker.py#L1170) - `_invoke_with_role` method
- [agent_invoker.py:1833-1890](guardkit/orchestrator/agent_invoker.py#L1833) - `_invoke_player_direct` method
- [agent_invoker.py:2191-2320](guardkit/orchestrator/agent_invoker.py#L2191) - `_invoke_task_work_implement` method (fixed version)
- [autobuild.py](guardkit/orchestrator/autobuild.py) - Orchestrator calling paths

## Evidence Files

- SUCCESS: `docs/reviews/feature-build/app_infrastructure_after_SDK_MAX_TURNS_regression_fix.md`
- FAILURE: `docs/reviews/feature-build/open_api_docs_after_SDK_MAX_TURNS_regression_fix.md`
- Previous Review: `.claude/reviews/TASK-REV-BB80-review-report.md`
- Previous Task: `tasks/completed/TASK-REV-BB80-feature-build-regression-analysis.md`

## Review Depth

**Standard** (1-2 hours) - Code analysis and evidence correlation required.

## Notes

The TASK-REV-BB80 fix was **partially correct** - it fixed the task-work delegation path but missed the direct mode path. This is a classic case of incomplete fix scope.

The "Player report missing" paradox needs investigation - the file is being written but not found, suggesting a structural issue in how direct mode reports are validated.
