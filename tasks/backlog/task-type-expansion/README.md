# Feature: Task Type Expansion

## Overview

Add missing `TESTING` and `REFACTOR` task types to the `TaskType` enum to align code with documentation and fix the feature build failure caused by invalid task_type values.

## Problem Statement

The `/feature-plan` documentation specifies `task_type: testing` and `task_type: refactor`, but these values don't exist in the `TaskType` enum. When CoachValidator encounters these invalid values, it returns feedback instead of approval, causing tasks to fail after exhausting max_turns.

**Evidence**: TASK-FHA-005 ("Set up testing infrastructure") failed in feature build FEAT-A96D because `task_type: testing` is not a valid enum value.

## Solution Approach

1. Add `TESTING` and `REFACTOR` enum values to `TaskType`
2. Define appropriate `QualityGateProfile` for each new type
3. Add testing-related keywords to the task type detector
4. Add unit test coverage for the new types
5. Verify existing tasks with these types now work

## Subtasks

| Task ID | Title | Mode | Wave | Dependencies | Status |
|---------|-------|------|------|--------------|--------|
| TASK-TT-001 | Add TESTING and REFACTOR to TaskType enum | task-work | 1 | - | ✅ COMPLETED |
| TASK-TT-002 | Add quality gate profiles for new types | task-work | 1 | TASK-TT-001 | ⏳ Ready (profiles already added in TT-001) |
| TASK-TT-003 | Add testing keywords to task_type_detector | task-work | 1 | - | 📋 BACKLOG |
| TASK-TT-004 | Add unit tests for new task types | task-work | 2 | TASK-TT-001, TASK-TT-002 | 📋 BACKLOG |
| TASK-TT-005 | Verify existing tasks pass with new types | direct | 2 | TASK-TT-001, TASK-TT-002 | 📋 BACKLOG |

## Acceptance Criteria

- [x] `TaskType.TESTING` and `TaskType.REFACTOR` exist in enum (TASK-TT-001)
- [x] Quality gate profiles defined for both new types (TASK-TT-001)
- [ ] Task type detector returns `TESTING` for test-related titles (TASK-TT-003)
- [ ] All unit tests pass (TASK-TT-004)
- [ ] Feature build with `task_type: testing` succeeds (TASK-TT-005)
- [ ] Existing tasks with invalid types now validate correctly (TASK-TT-005)

## Progress

**Feature Progress**: 20% (1/5 tasks completed)
**Wave 1 Progress**: 33% (1/3 tasks completed)

## Related

- **Parent Review**: TASK-REV-FB27
- **Root Cause**: Documentation-code mismatch in task type definitions
- **Affected Files**:
  - `guardkit/models/task_types.py`
  - `guardkit/lib/task_type_detector.py`
  - `guardkit/orchestrator/quality_gates/coach_validator.py`
