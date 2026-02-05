---
id: TASK-REV-AB04
title: Analyse AgentInvoker _ensure_design_approved_state error after TASK-FIX-AB01-AB03 fixes
status: review_complete
created: 2026-02-05T18:00:00Z
updated: 2026-02-05T19:00:00Z
priority: high
tags: [autobuild, debugging, agent-invoker, feature-build]
task_type: review
complexity: 4
related_tasks: [TASK-FIX-AB01, TASK-FIX-AB02, TASK-FIX-AB03, TASK-REV-5796]
related_feature: FEAT-CR01
review_results:
  mode: architectural
  depth: standard
  score: 95
  findings_count: 5
  recommendations_count: 3
  decision: implement
  report_path: .claude/reviews/TASK-REV-AB04-review-report.md
---

# Task: Analyse AgentInvoker _ensure_design_approved_state Error

## Problem Statement

After implementing fixes from TASK-FIX-AB01 (context param), TASK-FIX-AB02 (git serialization), and TASK-FIX-AB03 (recovery_count rename), a fresh run of `guardkit autobuild feature FEAT-CR01 --fresh --sdk-timeout 900` reveals a **new** error:

```
'AgentInvoker' object has no attribute '_ensure_design_approved_state'
```

This error affects **task-work delegation mode** tasks only (TASK-CR-001, TASK-CR-002). The direct SDK mode task (TASK-CR-003) completed successfully (approved in 1 turn), confirming the direct path works correctly.

## Error Log Reference

Full error log: `docs/reviews/graphiti_enhancement/agent_invoker_error.md`

## Observed Errors

### Error 1: Missing `_ensure_design_approved_state` method (PRIMARY BLOCKER)

**Location**: `AgentInvoker` class during task-work delegation path

```
Player failed: Unexpected error: 'AgentInvoker' object has no attribute '_ensure_design_approved_state'
```

This error occurs on every Player invocation via the task-work delegation path:
- Line 72: `INFO:guardkit.orchestrator.agent_invoker:Invoking Player via task-work delegation for TASK-CR-002 (turn 1)`
- Line 81: `✗ Player failed: Unexpected error: 'AgentInvoker' object has no attribute '_ensure_design_approved_state'`

The direct SDK path works correctly:
- Line 73: `INFO:guardkit.orchestrator.agent_invoker:Routing to direct Player path for TASK-CR-003 (implementation_mode=direct)`
- Line 74: `INFO:guardkit.orchestrator.agent_invoker:Invoking Player via direct SDK for TASK-CR-003 (turn 1)`
- Line 480: `✓ 1 files created, 1 modified, 1 tests (passing)`

### Error 2: Cascading task_work_results.json not found

Same cascading pattern as TASK-REV-5796 Finding 4 - since Player never executes via task-work delegation, no results file is produced.

## Positive Observations

1. **TASK-FIX-AB01 (context param) is FIXED** - No more `TypeError: invoke_player() got unexpected keyword argument 'context'`
2. **TASK-FIX-AB02 (git serialization) appears FIXED** - No `index.lock` errors despite 3 parallel tasks
3. **Direct SDK mode works** - TASK-CR-003 completed successfully (approved turn 1)
4. **AutoBuild infrastructure is functional** - Checkpointing, Coach validation, state recovery all working

## Context

- This is the second FEAT-CR01 run, after applying the TASK-FIX-AB01/AB02/AB03 fixes
- The previous error (`context=context_prompt` TypeError) is resolved
- The `_ensure_design_approved_state` method was previously present in the codebase (it was referenced in the successful FEAT-0F4A build logs)
- This suggests the TASK-FIX-AB01 changes may have accidentally removed or renamed this method, OR the method was not properly ported during the fix

## Acceptance Criteria

- [x] Root cause identified: commit `b8a827a6` inserted `detect_rate_limit()` at module level inside the class body, orphaning 15 methods including `_ensure_design_approved_state`
- [x] Check `AgentInvoker` class for the method (exists in source at line 2817 but orphaned inside `detect_rate_limit` scope - only 25/40 methods on class)
- [x] Determine if the method was renamed - NOT renamed, it's a scope/indentation issue
- [x] Verify the task-work delegation code path in `invoke_player()` - calls `_ensure_design_approved_state` at line 681, fails because method is not on class
- [x] Provide fix recommendation - IMPLEMENTED: moved `detect_rate_limit()` after class end, restored all 40 methods
- [x] Verify git lock fix (TASK-FIX-AB02) is working - CONFIRMED: no index.lock errors in logs

## Investigation Areas

1. **AgentInvoker class** - Check for `_ensure_design_approved_state` method or similar naming
2. **TASK-FIX-AB01 diff** - Did the fix accidentally remove this method?
3. **Task-work delegation path** - How does `invoke_player()` route between task-work and direct SDK modes?
4. **Pre-fix vs post-fix comparison** - `git diff` of agent_invoker.py before and after TASK-FIX-AB01
5. **State bridge module** - The successful FEAT-0F4A logs show `state_bridge` handling design_approved transitions - is this still intact?
