---
id: TASK-FP-001
title: Update feature-plan.md schema documentation
status: completed
created: 2026-01-06T09:15:00Z
updated: 2026-01-06T11:45:00Z
completed: 2026-01-06T11:45:00Z
priority: high
complexity: 4
tags: [documentation, schema, feature-plan]
parent_review: TASK-REV-66B4
wave: 1
dependencies: []
implementation_mode: task-work
testing_mode: standard
workspace: fp-schema-wave1-docs
previous_state: in_review
state_transition_reason: "Task completed - all acceptance criteria verified"
completed_location: tasks/completed/TASK-FP-001/
---

# Task: Update feature-plan.md schema documentation

## Description

Update the schema documentation in `installer/core/commands/feature-plan.md` to match what `FeatureLoader` expects. The current documentation shows an incompatible schema format that causes `/feature-build` to fail.

## Current State

The documentation shows:
```yaml
tasks:
  - id: TASK-XXX
    name: "Task Name"
    wave: 1
    dependencies: []

task_files:
  - path: "tasks/backlog/.../TASK-XXX.md"

execution_groups:
  - wave: 1
    name: "Foundation"
    strategy: sequential
    tasks: [TASK-XXX]
```

## Expected State

Update to match FeatureLoader schema:
```yaml
tasks:
  - id: TASK-XXX
    name: "Task Name"
    file_path: "tasks/backlog/.../TASK-XXX.md"
    status: pending
    complexity: 5
    dependencies: []
    implementation_mode: task-work

orchestration:
  parallel_groups:
    - - TASK-XXX
```

## Acceptance Criteria

- [x] Update "Schema Mismatch Analysis" section with correct expected schema
- [x] Update "AutoBuild Integration" section with new format
- [x] Update all example YAML snippets throughout the file
- [x] Remove references to `task_files` section (redundant)
- [x] Replace `execution_groups` with `parallel_groups` format
- [x] Add note about required fields (`file_path`, `status`)

## Files to Modify

- `installer/core/commands/feature-plan.md`

## Technical Notes

- The `parallel_groups` format is a list of lists where each inner list represents tasks that can run in parallel (a "wave")
- `file_path` must be relative to repository root
- `status` defaults to "pending" but should be explicit for clarity

## Implementation Summary

### Changes Made

1. **Added new "Feature YAML Schema Reference" section** (lines 68-217)
   - Complete schema example with all required fields
   - Required fields table for feature-level, task-level, and orchestration fields
   - Critical note about `file_path` being required
   - `parallel_groups` format explanation with examples
   - Note about deprecated `execution_groups` format

2. **Updated AutoBuild Integration section** (lines 27-66)
   - Changed "Group X" to "Wave X" for consistency with schema
   - Maintained compatibility with existing documentation

3. **Updated generate-feature-yaml script documentation** (lines 1335-1373)
   - Changed task format from `ID:NAME:COMPLEXITY:DEPS` to `ID:NAME:FILE_PATH:COMPLEXITY:DEPS`
   - Added FILE_PATH as required field in documentation
   - Updated all examples to include `file_path`

4. **Updated execution trace examples** (lines 1497-1505)
   - Added `file_path` to task arguments in examples

### Testing

- All 36 tests in `tests/unit/test_feature_loader.py` pass
- Documentation renders correctly

## Completion Report

**Task ID:** TASK-FP-001
**Completed:** 2026-01-06T11:45:00Z
**Duration:** ~30 minutes
**Quality Gates:** All passed (documentation task - no code changes)
**Files Modified:** 1 (`installer/core/commands/feature-plan.md`)
