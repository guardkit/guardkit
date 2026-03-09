---
id: TASK-RFX-7C63
title: Extended CoachValidator with runtime verification methods (CRV-9914)
status: completed
task_type: implementation
created: 2026-03-09T16:00:00Z
updated: 2026-03-09T22:00:00Z
completed: 2026-03-09T22:00:00Z
priority: medium
complexity: 6
wave: 4
implementation_mode: task-work
parent_review: TASK-REV-A8C6
feature_id: FEAT-RFX
tags: [autobuild, coach-validator, architecture]
dependencies: [TASK-RFX-F7F5]
original_task: TASK-CRV-9914
completed_location: tasks/completed/TASK-RFX-7C63/
---

# Task: Extended CoachValidator with Runtime Verification Methods

## Description

Architectural refactor to move runtime verification from the orchestrator (`autobuild.py:_execute_command_criteria()`) into the CoachValidator. This creates a cleaner separation of concerns where the Coach owns all verification -- file-content, command-execution, and manual criteria.

This is the original TASK-CRV-9914 from the coach-runtime-verification feature (Wave 3). Dependencies (CRV-412F and CRV-537E) are now complete.

## Acceptance Criteria

- [x] CoachValidator has a `verify_command_criteria()` method that executes runtime commands
- [x] Command execution logic moved from `autobuild.py:_execute_command_criteria()` to Coach
- [x] CoachValidator uses failure classifier from TASK-RFX-F7F5 for result categorisation
- [x] Orchestrator passes worktree path to Coach for command execution context
- [x] Backward compatible: existing quality gate profiles continue to work
- [x] Unit tests for CoachValidator command verification
- [x] Integration test: Coach executes and evaluates command criteria in same pipeline as file_content

## Implementation Summary

### Files Created
- `guardkit/orchestrator/quality_gates/command_models.py` - Shared types/constants module breaking circular imports
- `tests/unit/test_coach_command_verification.py` - 23 tests for verify_command_criteria

### Files Modified
- `guardkit/orchestrator/quality_gates/coach_validator.py` - Added `verify_command_criteria()` method
- `guardkit/orchestrator/autobuild.py` - Replaced inline logic with delegation to Coach; re-exports for backward compatibility
- `guardkit/orchestrator/quality_gates/__init__.py` - Added CommandExecutionResult/CommandVerificationResult exports
- `tests/unit/test_command_failure_classifier.py` - Updated patch targets for new import paths

### Architecture
- Coach now owns all verification: file-content, command-execution, and manual criteria
- Orchestrator delegates to Coach and handles report injection only
- Backward compatibility preserved via re-exports from autobuild.py
- Circular imports avoided via shared command_models.py module

### Test Results
- 96 tests passing (38 + 23 + 35 across 3 test files)
- Code review: APPROVED

## Implementation Notes

See `tasks/backlog/coach-runtime-verification/TASK-CRV-9914-extended-coach-validator.md` for original specification.
