---
id: TASK-ACR-001
title: "Propagate completion_promises in task_work_results writer"
status: completed
created: 2026-02-15T10:00:00Z
updated: 2026-02-15T17:00:00Z
completed: 2026-02-15T17:00:00Z
priority: high
task_type: feature
parent_review: TASK-REV-B5C4
feature_id: FEAT-F022
wave: 1
implementation_mode: task-work
complexity: 3
dependencies: []
tags: [autobuild, coach, criteria-verification, f2-fix]
test_results:
  status: passed
  coverage: null
  last_run: 2026-02-15T17:00:00Z
---

# Task: Propagate completion_promises in task_work_results writer

## Description

Fix the standard task-work path in `agent_invoker.py` to propagate `completion_promises` from the Player's SDK output into `task_work_results.json`. The direct mode path already has this fix (TASK-FIX-ACA7b at line ~2435) — apply the same pattern to `_write_task_work_results()`.

Also ensure `task_id` is always populated (never empty string) so `_load_completion_promises()` can locate player reports on disk as a fallback.

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` — `_write_task_work_results()` (~line 3599)
- `guardkit/orchestrator/agent_invoker.py` — `_create_player_report_from_task_work()` (~line 1418)
- `guardkit/orchestrator/autobuild.py` — `_build_synthetic_report()` (~line 2168) — ensure task_id populated by caller

## Acceptance Criteria

- [x] AC-001: `_write_task_work_results()` includes `completion_promises` from Player SDK output when available
- [x] AC-002: `task_id` is never empty string in `task_work_results.json` (set by all writers)
- [x] AC-003: `_create_player_report_from_task_work()` propagates `completion_promises` into `player_turn_N.json`
- [x] AC-004: Synthetic report caller fills `task_id` before writing
- [x] AC-005: Existing direct mode promise propagation (TASK-FIX-ACA7b) remains unchanged
- [x] AC-006: Unit tests verify promise propagation for standard task-work path

## Implementation Notes

Reference the direct mode fix pattern at `_write_direct_mode_results()` line ~2435:
```python
completion_promises = player_report.get("completion_promises", [])
if completion_promises:
    results["completion_promises"] = completion_promises
```

Apply equivalent pattern to `_write_task_work_results()`, extracting promises from the Player SDK invocation result rather than from the parsed task-work output.
