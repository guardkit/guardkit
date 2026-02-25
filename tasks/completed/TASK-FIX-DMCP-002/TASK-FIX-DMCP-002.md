---
id: TASK-FIX-DMCP-002
title: Fix Coach text matching to check requirements_addressed
status: completed
task_type: feature
created: 2026-02-24T16:00:00Z
updated: 2026-02-24T17:05:00Z
completed: 2026-02-24T17:05:00Z
completed_location: tasks/completed/TASK-FIX-DMCP-002/
previous_state: in_review
state_transition_reason: "All acceptance criteria verified, quality gates passed"
priority: critical
tags: [autobuild, bug-fix, coach-validator, criteria-matching]
complexity: 1
parent_review: TASK-REV-CECA
feature_id: FEAT-DMCP
wave: 1
implementation_mode: direct
dependencies: []
---

# Task: Fix Coach text matching to check requirements_addressed

## Description

The Coach validator's text matching fallback reads `requirements_met` from `task_work_results.json`, but the Player writes its data under `requirements_addressed`. The hybrid fallback correctly checks both field names, but the text matching path does not.

## Root Cause

At `coach_validator.py:1576-1579`:

```python
# Text matching path — only checks requirements_met (WRONG)
strategy = "text"
requirements_met = task_work_results.get("requirements_met", [])
validation = self._match_by_text(acceptance_criteria, requirements_met)
```

The hybrid fallback at line 1566-1568 correctly checks both:

```python
# Hybrid fallback — checks both names (CORRECT pattern)
requirements_addressed = task_work_results.get(
    "requirements_addressed",
    task_work_results.get("requirements_met", []),
)
```

## Fix

Replace line 1578:
```python
requirements_met = task_work_results.get("requirements_met", [])
```

With:
```python
requirements_met = task_work_results.get(
    "requirements_addressed",
    task_work_results.get("requirements_met", []),
)
```

This matches the existing hybrid fallback pattern at line 1566-1568.

## Acceptance Criteria

1. Coach text matching path checks `requirements_addressed` first, then `requirements_met` as fallback
2. Pattern matches existing hybrid fallback at line 1566-1568
3. Existing tests still pass
4. Backward compatible — `requirements_met` still works if present

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` — `_validate_requirements` method, text matching path

## Files NOT to Touch

- `guardkit/orchestrator/agent_invoker.py` — separate task
- `guardkit/orchestrator/autobuild.py`
