---
id: TASK-FIX-7537
title: Add pre-flight feature validation before autobuild feature execution
task_type: feature
parent_review: TASK-REV-7535
feature_id: FEAT-CF57
wave: 1
implementation_mode: task-work
complexity: 4
dependencies: []
status: completed
completed: 2026-03-03T00:00:00Z
updated: 2026-03-03T00:00:00Z
previous_state: in_review
state_transition_reason: "All quality gates passed - task completed"
completed_location: tasks/completed/TASK-FIX-7537/
autobuild:
  enabled: true
  max_turns: 5
  mode: tdd
---

# Task: Add Pre-Flight Feature Validation Before AutoBuild Feature Execution

## Description

The FEAT-CF57 run_2 failure (`Invalid task_type value: enhancement`) could have been caught before any SDK invocations if `guardkit feature validate` had run automatically. This task adds a pre-flight validation step to `guardkit autobuild feature` that validates all task frontmatter before execution begins.

## Context

From TASK-REV-7535 lessons learned:
> Running `guardkit feature validate` before `guardkit autobuild feature` would have caught the `task_type: enhancement` issue before spending SDK turns. Consider making this automatic or at least prompting.

## Requirements

### 1. Pre-flight validation in feature_orchestrator.py

Add a validation step in `_setup_phase()` (after loading the feature but before creating/resuming the worktree) that:

1. Iterates all tasks in the feature YAML
2. Loads each task file
3. Validates `task_type` against `VALID_TASK_TYPES` from `guardkit/models/task_types.py`
4. Validates required frontmatter fields (id, title, task_type, complexity)
5. Reports all validation errors at once (don't fail on first error)

### 2. Error reporting

On validation failure:
```
================================================================
PRE-FLIGHT VALIDATION FAILED
================================================================

2 task(s) have invalid frontmatter:

  TASK-INST-012: Invalid task_type 'enhancement'
    Valid values: scaffolding, feature, infrastructure, integration, documentation, testing, refactor
    Valid aliases: implementation, bug-fix, bug_fix, benchmark, research, enhancement

  TASK-INST-005: Missing required field 'complexity'

Fix these issues and retry.
================================================================
```

### 3. Skip option

Add `--skip-validation` flag to bypass pre-flight checks (for cases where validation is too strict or user wants to proceed despite warnings).

### 4. Alias suggestion

When an alias is detected (e.g., `enhancement`), suggest the canonical value rather than just flagging as invalid:
```
  TASK-INST-012: task_type 'enhancement' is a legacy alias
    Suggestion: Change to 'feature' (canonical value)
    Note: Alias will work at runtime, but canonical values are preferred
```

## Acceptance Criteria

- [x] Pre-flight validation runs automatically before feature execution
- [x] Invalid task_type values are caught before any SDK invocations
- [x] All validation errors reported at once (batch, not fail-fast)
- [x] `--skip-validation` flag available to bypass
- [x] Alias values produce suggestion rather than hard failure
- [x] Unit tests cover: valid features pass, invalid task_type caught, missing fields caught, alias suggestion

## File Location

- `guardkit/orchestrator/feature_orchestrator.py` (add validation step)
- `guardkit/orchestrator/feature_validator.py` (new: validation logic)

## Test Location

- `tests/orchestrator/test_feature_validator.py`

## Implementation Summary

### Files Created
- `guardkit/orchestrator/feature_validator.py` - Core validation module with `validate_feature_preflight()`, `format_preflight_report()`, `PreFlightValidationResult`, `ValidationIssue` dataclasses
- `tests/orchestrator/test_feature_validator.py` - 22 test cases (99% coverage)

### Files Modified
- `guardkit/orchestrator/feature_orchestrator.py` - Added `skip_validation` param to `__init__`, integrated pre-flight call in `_setup_phase()` after structural validation
- `guardkit/cli/autobuild.py` - Added `--skip-validation` Click flag, passed through to `FeatureOrchestrator`
- `guardkit/orchestrator/__init__.py` - Exported new public symbols

### Quality Gates
- Tests: 22/22 passed (100%)
- Coverage: 99% line, 97% branch
- Regressions: 0 (159 existing tests still passing)
- Code review: Approved
