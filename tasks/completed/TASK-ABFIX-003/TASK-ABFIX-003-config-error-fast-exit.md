---
id: TASK-ABFIX-003
title: Add configuration error flag and fast-exit for config errors in autobuild loop
task_type: feature
parent_review: TASK-REV-A17A
feature_id: FEAT-CD4C
wave: 1
implementation_mode: task-work
complexity: 5
dependencies: []
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
status: completed
completed: 2026-03-02T00:00:00Z
priority: critical
tags: [autobuild, orchestrator, error-handling, pollution-detection]
---

# Task: Add configuration error flag and fast-exit for config errors in autobuild loop

## Description

Add an `is_configuration_error` flag to `CoachValidationResult` so the AutoBuild loop can distinguish configuration errors (like invalid `task_type`) from code errors. When a configuration error is detected, exit the loop immediately with a clear error instead of entering the feedback loop (which is futile since the Player cannot fix task frontmatter).

Also update pollution detection (checkpoint creation) to not count configuration errors as test failures.

## Review Reference

From TASK-REV-A17A Finding 2, Recommendations 2c and 2d:
> 2c: Add `is_configuration_error` flag to `CoachValidationResult`. When `category="invalid_task_type"`, mark it as configuration rather than code. In `autobuild._loop_phase`, check this flag and exit immediately.
> 2d: Don't count Coach configuration errors in pollution detection. Check if feedback category is `invalid_task_type` and either skip checkpoint creation or mark as `tests_passed=True`.

## Requirements

1. Add `is_configuration_error: bool = False` field to `CoachValidationResult` (or equivalent result dataclass)
2. In `coach_validator.py:588-605`, when `category="invalid_task_type"`, set `is_configuration_error=True`
3. In `autobuild.py._loop_phase` (around line 1472-1708), check `is_configuration_error` on feedback:
   - If True: log a clear error message and return immediately with `"configuration_error"` decision
   - Do NOT enter the feedback/retry loop
4. In checkpoint creation (around `autobuild.py:1648`), when `is_configuration_error=True`:
   - Skip checkpoint creation OR mark `tests_passed=True` (since tests were never run)
5. Add tests verifying:
   - Configuration errors trigger immediate exit (not 3-turn stall)
   - Pollution detection ignores configuration errors
   - Non-configuration feedback still enters the normal feedback loop

## Files to Modify

- `guardkit/orchestrator/quality_gates/coach_validator.py` — add flag to result, set on config errors
- `guardkit/orchestrator/autobuild.py` — check flag, fast-exit, skip checkpoint
- `tests/` — add tests for config error path

## Expected Interface

When `autobuild._loop_phase` encounters `is_configuration_error=True`:
```
ERROR: Configuration error for TASK-INST-012: Invalid task_type 'enhancement'.
       Valid values: scaffolding, feature, infrastructure, integration, documentation, testing, refactor
       Aliases: implementation, bug-fix, bug_fix, benchmark, research, enhancement
       This is a task file configuration issue — the Player cannot fix it.
       Fix the task_type in the task .md file and retry.
```

## Acceptance Criteria

- [ ] `is_configuration_error` flag exists on Coach validation result
- [ ] AutoBuild loop exits immediately on configuration error (no feedback loop)
- [ ] Pollution detection does not count configuration errors as test failures
- [ ] Error message is actionable (lists valid values and how to fix)
- [ ] Normal feedback loop still works for code errors
- [ ] All existing tests pass
