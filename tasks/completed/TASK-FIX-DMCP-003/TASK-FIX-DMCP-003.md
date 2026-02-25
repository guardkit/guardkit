---
id: TASK-FIX-DMCP-003
title: Propagate _synthetic flag in _write_player_report_for_direct_mode
status: completed
task_type: feature
created: 2026-02-24T16:00:00Z
updated: 2026-02-24T18:05:00Z
completed: 2026-02-24T18:05:00Z
previous_state: in_review
state_transition_reason: "All acceptance criteria met, tests passing"
completed_location: tasks/completed/TASK-FIX-DMCP-003/
priority: high
tags: [autobuild, bug-fix, direct-mode, synthetic-report]
complexity: 1
parent_review: TASK-REV-CECA
feature_id: FEAT-DMCP
wave: 1
implementation_mode: direct
dependencies: []
---

# Task: Propagate _synthetic flag in _write_player_report_for_direct_mode

## Description

`_write_player_report_for_direct_mode` in `agent_invoker.py` rebuilds the report dict with explicit fields but does not include the `_synthetic` flag. This prevents the Coach's synthetic fast-path from activating on turns where the SDK doesn't produce a report.

## Root Cause

At `agent_invoker.py:2914-2950`, the method constructs a new report dict and copies specific fields (including `completion_promises`) but omits `_synthetic`:

```python
report: Dict[str, Any] = {
    "task_id": task_id,
    # ... other fields ...
    "implementation_mode": "direct",
}
# completion_promises copied (line 2934-2937) -- OK
# _synthetic NOT copied -- BUG
```

`_write_direct_mode_results` at line 2871-2873 correctly propagates `_synthetic`:
```python
if player_report.get("_synthetic"):
    results["_synthetic"] = True
```

But it never fires because the loaded report (round-tripped through `_write_player_report_for_direct_mode`) already lost the flag.

## Fix

After the completion_promises block (~line 2937), add:

```python
# Propagate _synthetic flag (mirrors _write_direct_mode_results pattern)
if player_report.get("_synthetic"):
    report["_synthetic"] = True
```

## Acceptance Criteria

1. `_write_player_report_for_direct_mode` copies `_synthetic` flag from input report
2. Flag absent when Player report is not synthetic (no false positives)
3. Existing tests still pass
4. Round-trip through write/load preserves _synthetic flag

## Files to Modify

- `guardkit/orchestrator/agent_invoker.py` — `_write_player_report_for_direct_mode` method

## Files NOT to Touch

- `guardkit/orchestrator/quality_gates/coach_validator.py`
- `guardkit/orchestrator/synthetic_report.py`
