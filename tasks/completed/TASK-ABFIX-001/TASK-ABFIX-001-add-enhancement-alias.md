---
id: TASK-ABFIX-001
title: Add enhancement as task_type alias for feature
task_type: feature
parent_review: TASK-REV-A17A
feature_id: FEAT-CD4C
wave: 1
implementation_mode: task-work
complexity: 2
dependencies: []
autobuild:
  enabled: true
  max_turns: 3
  mode: tdd
status: completed
priority: critical
tags: [autobuild, orchestrator, task-type, fix]
---

# Task: Add enhancement as task_type alias for feature

## Description

Add `enhancement` as an alias for `TaskType.FEATURE` in both the Coach validator and AutoBuild orchestrator alias tables. This is the simplest fix for the TASK-INST-012 deterministic stall — the task had `task_type: enhancement` which is not in the enum or alias table.

## Review Reference

From TASK-REV-A17A Finding 2, Recommendation 2a:
> Add `enhancement` as alias for `feature` in `TASK_TYPE_ALIASES` in both `coach_validator.py:68-75` and `autobuild.py:3800-3806`

## Requirements

1. Add `"enhancement": TaskType.FEATURE` to `TASK_TYPE_ALIASES` dict in `guardkit/orchestrator/quality_gates/coach_validator.py` (around line 68-75)
2. Add the same alias in `guardkit/orchestrator/autobuild.py` (around line 3800-3806) if a separate alias table exists there
3. Add tests verifying `_resolve_task_type("enhancement")` returns `TaskType.FEATURE`
4. Add tests verifying Coach validation succeeds for tasks with `task_type: enhancement`

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` — add alias
- `guardkit/orchestrator/autobuild.py` — add alias (if separate table)
- `tests/` — add/extend tests for task_type resolution

## Acceptance Criteria

- [ ] `enhancement` resolves to `TaskType.FEATURE` via alias
- [ ] Coach validator does not return `invalid_task_type` feedback for `enhancement`
- [ ] All existing tests pass
- [ ] New tests cover the alias resolution
